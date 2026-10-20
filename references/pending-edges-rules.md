# 待人审推断边队列规则（pending-edges-rules）

> `.knowledge/.pending-edges.yaml` 是待人审推断边（INFERRED/AMBIGUOUS）队列的唯一权威源。
>
> 与 `.pending-backlinks.yaml` **同构但职责分离**：复用其 schema 风格 / ID 生成 / 幂等去重 / consume 批量范式，但只装待人审的推断边。
>
> 由生成器（Phase 7 `health discover`）或手动/注入（Phase 3 验证）入队，由 `health edge-review` 单条人审消费。
>
> 与 `trust-rules.md`（治理语义）互补：本文件定义**队列结构与流程**。

---

## 设计原则

1. **推断边不进权威图**：推断边只在队列暂存，绝不进 graph.json `links`（守 `graph-model.md` §3.4 方案 A：links 只放权威边）
2. **队列缓冲**：待人审边暂存此文件，它是建议暂存**非真理源**——真理只在文档 frontmatter
3. **幂等安全**：重复入队同一 `(source, target, relation)` 三元组不产生第二条
4. **人审闸门**：无 `--auto-approve` 批量开关，逐条 approve/reject/skip
5. **可追溯**：每条带 `source_location` 推断依据，守 C1 来源铁律（推断边也要有依据）

---

## 数据结构

### .pending-edges.yaml

```yaml
# .knowledge/.pending-edges.yaml
# 待人审的推断边队列（INFERRED/AMBIGUOUS）
# 与 .pending-backlinks.yaml 同构但职责分离：本文件只装"待人审的推断边"
# 放 .knowledge/ 根（与 .pending-backlinks.yaml 同级）

version: 1
pending:
  - id: pe-20260611143008-a1b2          # 唯一 ID（时间戳 + sha1[:4]）
    source: ops/print-timeout            # 边起点（slug，与 graph.json node id 对齐）
    target: flows/fallback-strategy      # 边终点（slug）
    relation: references                 # 建议的 relation 类型
    confidence: INFERRED                 # INFERRED | AMBIGUOUS（绝不 EXTRACTED——结构边直接入图不入队）
    source_location: "similarity:ops/print-timeout.md↔flows/fallback-strategy.md:0.83"
                                         # 推断依据（守 C1：可回溯"凭什么推断"）；
                                         # Phase 7 生成器填相似度/语义依据；Phase 3 手造填 "manual:<说明>"
    proposed_at: "2026-06-11T14:30:08+08:00"
    proposed_by: discover                # 来源：discover(Phase 7) | manual(Phase 3 手造/注入)
    reviewed: false                      # 默认 false（人审闸门核心）
    reviewed_at: null                    # 人审时间（approve/reject 时填）
    reviewed_by: null                    # 人审人 user-id（approve/reject 时填）
    decision: null                       # null（待审） | approve | reject

  - id: pe-20260611143010-c3d4
    source: design/print-arch
    target: db/order-table
    relation: references
    confidence: AMBIGUOUS
    source_location: "manual:注入验证闭环用"
    proposed_at: "2026-06-11T14:30:10+08:00"
    proposed_by: manual
    reviewed: false
    reviewed_at: null
    reviewed_by: null
    decision: null

reviewed_history: []                     # 已决策记录（approve/reject 各保留最近 200 条，审计用）
```

### ID 生成规则

```
id = "pe-" + {YYYYMMDDHHmmss} + "-" + sha1(source + "→" + target + "|" + relation)[:4]
例：pe-20260611143008-a1b2
```

保证同一 `(source, target, relation)` 三元组在短时间内不重复入队（幂等键）。

### 字段语义表

| 字段 | 类型 | 语义 | 与 backlink 对应 |
|------|------|------|------------------|
| `id` | string | 唯一 ID（幂等用） | 同 `bl-*` 范式 |
| `source` / `target` | string | 边端点（slug，与 graph.json node `id` 对齐） | 类比 `target`/`from` |
| `relation` | string | 建议 relation（references/depends_on/...） | 新增（边特有） |
| `confidence` | string | `INFERRED` \| `AMBIGUOUS`（**绝不 EXTRACTED**——结构边直接入图不入队） | 新增（边特有） |
| `source_location` | string | **推断依据**（守 C1，非空） | 新增（边特有） |
| `proposed_at` | string | 入队时间（ISO 8601） | 同 `created_at` |
| `proposed_by` | string | `discover`(Phase 7) \| `manual`(Phase 3) | 新增 |
| `reviewed` | bool | 默认 `false`，approve/reject 后标 `true` | 类比 `consumed` |
| `reviewed_at` | string \| null | 人审时间 | 类比 `consumed_at` |
| `reviewed_by` | string \| null | 人审人 user-id | 新增 |
| `decision` | string \| null | `null`(待审) \| `approve` \| `reject` | 新增（人审特有） |

顶层结构 `version / pending[] / reviewed_history[]` 与 `.pending-backlinks.yaml` 的 `version / pending[] / consumed_history[]` **同构**。

---

## 入队接口（Phase 3 契约，Phase 7 挂生成器）

### 入队方式

| 入队方式 | Phase | 机制 |
|---------|:---:|------|
| **手动/注入入队**（Phase 3 验证用） | 3 | 直接编辑 `.pending-edges.yaml` 追加 pending 条目，或用最小入队 helper（`proposed_by: manual`） |
| **生成器入队** | 7 | `health discover` 算相似度 → 高相似无连接对 → 调同一入队接口（`proposed_by: discover`） |

### 入队幂等去重键：`(source, target, relation)`

入队前**三检查**：

1. 该三元组是否已在 `graph.json.links`（已是权威边）→ **跳过**（已存在无需推荐）
2. 该三元组是否已在 `pending[]`（未消费）→ **跳过**（幂等，不重复入队）
3. 该三元组是否在 `reviewed_history` 且 `decision=reject`（曾被拒）→ **跳过或降级提示**（不反复推同一被拒边）

### 入队 SSOT 守卫

入队**不修改 graph.json、不修改文档**——只往 `.pending-edges.yaml` 追加候选。pending 队列是"建议暂存"，**不是真理源**。

---

## 队列消费（health edge-review 单条人审）

### 命令形态

- **`/knowledge-wiki health edge-review`**——逐条人审待审推断边。
- **`health edge-review --dry-run`**——仅展示待审列表、不做决策（可选调试模式）。

> **这是 AI 解释型 health 子命令**（与 `backlink-consume` 同载体，由本规则文档 + `health-rules.md` 驱动 AI 执行，**非 python 脚本**）。

### 消费命令

`health edge-review`——**非批量自动**，与 backlink-consume 的自动批量对比：

| 维度 | `health backlink-consume` | `health edge-review` |
|------|--------------------------|---------------------|
| 消费模式 | 自动批量（全部消费） | **逐条人审**（approve/reject/skip） |
| 人工干预 | 无（自动追加 related） | **每条都要人决策** |
| 批量开关 | N/A | **禁止 `--auto-approve`**（SC#2 never） |

### 逐条审阅交互范式

读取 `.pending-edges.yaml` → 过滤 `reviewed==false` 条目 → **逐条**展示 + 人决策。

**展示格式**（每条）：

```
📋 待审推断边 [1/N]
  source: ops/print-timeout → target: flows/fallback-strategy
  relation: references | confidence: INFERRED
  推断依据: similarity:ops/print-timeout.md↔flows/fallback-strategy.md:0.83
  proposed_by: discover | proposed_at: 2026-06-11T14:30:08+08:00

  [a]approve  [r]reject  [s]skip
```

**无「全部 approve」批量开关**——逐条问询是人审闸门的核心保障（SC#2）。

### 单条消费流程

```
1. 读取 .pending-edges.yaml
2. 过滤 reviewed==false 的条目
3. 若无待审 → 静默输出"无待人审的推断边"
4. 逐条展示 → 人 [a]approve / [r]reject / [s]skip：

   ── approve（仅 INFERRED 可 approve，严格按 trust-rules.md §SSOT 写回 6 步）──
   a. 定位 source 文档实际路径（rg 搜索 .knowledge/ 业务目录，仿 backlink-consume Step 1）
   b. 二次幂等检查：source 文档 related 是否已包含 [[target]]
      - 已包含 → 标 decision=approve 移入 reviewed_history，跳过文件修改
      - 未包含 → 继续下一步
   c. 复用 backlink-consume「安全追加 related + 上限 15 裁剪」写文件逻辑，
      在 source 文档 frontmatter related 追加 [[target]]
   d. 标 decision=approve / reviewed=true / reviewed_at={ISO8601} / reviewed_by={user-id}
   e. 将该条目移入 reviewed_history
   f. 写 C6 操作日志（action=edge-review，见下方 §C6 日志格式）
   g. 提示「已写回 {source}.md 的 related，运行 health graph-build --incremental 派生为权威边」
      （提示驱动，不自动跑 graph-build）
   h. 下次 graph-build：collect_edges 从 source 的 related 读到 [[target]] →
      派生出 EXTRACTED + reviewed=true 边 → 进 graph.json links

   ── reject ──
   a. 标 decision=reject / reviewed=true / reviewed_at / reviewed_by
   b. 移入 reviewed_history
   c. 不写任何文档、不入图
   d. 写 C6 操作日志（detail 含 rejected 计数）
   e. 该三元组进 reviewed_history 供入队幂等「不反复推同一被拒边」

   ── skip ──
   a. 保留在 pending[]，reviewed 仍 false，待下次审

5. AMBIGUOUS 边机制级禁 approve（D6）：
   对 confidence==AMBIGUOUS 的条目，只展示 [r]reject [s]skip，不提供 approve 选项。
   若用户强行 approve，强制拒绝并提示：
   「AMBIGUOUS 边不能直接 approve 为权威边；若你确认这是某种明确关系，
     请在文档里手写对应 [[slug]] 并指明关系。」
   （指向 trust-rules.md §AMBIGUOUS 护栏）

6. reviewed_history FIFO 截断：保留最近 200 条，超出丢弃最早（仿 consumed_history）
7. 更新 .pending-edges.yaml
8. 输出摘要
```

### 输出摘要示例

```
✅ 推断边人审完成

reviewed: 5 条
  ✅ approve: 3 条
    ops/print-timeout → flows/fallback-strategy (INFERRED→EXTRACTED)
    design/x → flows/y (INFERRED→EXTRACTED)
    ...
  ❌ reject: 1 条
    design/print-arch → db/order-table (AMBIGUOUS, reject)
  ⏭️ skip: 1 条

docs_updated: ops/print-timeout.md, design/x.md
建议：运行 health graph-build --incremental 派生为权威边
```

### C6 日志格式

复用 `log-rules.md` 通道（action=`edge-review`），仿 backlink-consume 同构格式：

```markdown
## [2026-06-11T15:05:00+08:00] @alice | edge-review | 批量人审
  detail: {"reviewed": 3, "approved": 2, "rejected": 1, "approved_edges": ["ops/print-timeout→flows/fallback-strategy (INFERRED→EXTRACTED)", "design/x→flows/y (INFERRED→EXTRACTED)"], "docs_updated": ["ops/print-timeout.md", "design/x.md"]}
```

审计字段：

- **谁** = `@{user-id}`（log 行首，复用 `resolve_user_id`）
- **何时** = ISO 8601 时间戳
- **哪条边** = `source→target (confidence)` + `false→true`（reviewed 状态迁移，满足 SC#3「谁/何时/哪条边 false→true」）
- **落地** = `docs_updated`（写回了哪篇文档的 related）

reject 也写日志（detail 含 `rejected` 计数），保证"否决"也可追溯。

---

## 入队 helper（手动/注入，Phase 3 验证入口）

### 入队方式

Phase 3 唯一入队方式：**直接编辑 `.pending-edges.yaml`** 追加 pending 条目（`proposed_by: manual`）。

Phase 7 的 `health discover` 生成器将调同一入队接口（`proposed_by: discover`），**Phase 3 把接口契约定义好但不实现生成器**。

### 入队字段要求

每条新增 pending 条目必须包含：

| 字段 | Phase 3 手造填法 | 说明 |
|------|------------------|------|
| `id` | `pe-{YYYYMMDDHHmmss}-{sha1[:4]}` | 唯一 ID |
| `source` | slug（与 graph.json node id 对齐） | 边起点 |
| `target` | slug | 边终点 |
| `relation` | `references` / `depends_on` / `derived_from` / `term_of` | 建议 relation |
| `confidence` | `INFERRED` \| `AMBIGUOUS` | **绝不 EXTRACTED**——结构边直接入图不入队 |
| `source_location` | `manual:<说明>`（非空，守 C1） | 推断依据 |
| `proposed_at` | ISO 8601 | 入队时间 |
| `proposed_by` | `manual` | Phase 3 手造固定 |
| `reviewed` | `false` | 默认待审 |
| `reviewed_at` | `null` | 待审时为 null |
| `reviewed_by` | `null` | 待审时为 null |
| `decision` | `null` | 待审时为 null |

### 入队幂等三检查

入队前执行三检查（防重复推荐）：

1. 该 `(source, target, relation)` 三元组是否已在 `graph.json.links`（已是权威边）→ **跳过**
2. 该三元组是否已在 `pending[]`（未消费）→ **跳过**（幂等）
3. 该三元组是否在 `reviewed_history` 且 `decision=reject`（曾被拒）→ **跳过**（不反复推同一被拒边）

### 入队 SSOT 守卫

入队**不修改 graph.json、不修改文档**——只往 `.pending-edges.yaml` 追加候选。pending 队列是"建议暂存"，**不是真理源**。

### Phase 7 生成器接口预留

Phase 7 `health discover` 调同一入队逻辑，区别仅：

- `proposed_by: discover`
- `source_location: "similarity:{a}↔{b}:{score}"` 或 `"semantic:{a}↔{b}:{reasoning}"`
- 同样须通过幂等三检查

---

## edge-review 安全保障（仿 backlink-consume）

### 写回文档前的安全检查

edge-review 开始前（仿 backlink-consume 并发安全保障）：

```bash
# 1. 确认工作区干净（无未提交更改）
git diff --quiet
if [ $? -ne 0 ]; then
  echo "⚠️ 工作区有未提交的更改，请先 commit 或 stash 后再执行 edge-review"
  exit 1
fi

# 2. git pull 确保最新
git pull --rebase
```

### 消费后的自动 commit

消费完成后（有 approve 写回文档时），自动 commit 所有变更：

```bash
git add .knowledge/.pending-edges.yaml
git add .knowledge/{所有被修改的 source 文件}
git commit -m "[kb] edge-review: 人审 N 条推断边"
```

commit message 符合 `commit-msg.sh` hook 的 `[kb]` 前缀规范。

### 异常恢复

| 异常场景 | 处理 | 依据 |
|---------|------|------|
| 目标 source 文档被外部删除 | 跳过该条 + WARNING + 标 decision=reject（防无限重试） | 仿 backlink-consume 异常恢复 |
| `.pending-edges.yaml` 不存在 | 静默退出"无待人审的推断边" | 保证队列不存在时命令无副作用 |
| related 已包含 `[[target]]` | 标 approve 移入 history，跳过文件修改（幂等） | 二次幂等检查 |
| related 已达 15 条上限 | 执行裁剪逻辑（复用 backlink-rules.md 上限裁剪算法）再追加 | 守 related 上限 |

---

## 与 graph.json 的隔离（守单向派生）

- pending 边**绝不进 graph.json `links`**——`links` 只放权威边（`is_authoritative` 永真）
- `graph-build` **不读也不写 `.pending-edges.yaml`**——队列是 `edge-review` 的领地，与引擎物理隔离
- `.pending-edges.yaml` 须加入 graph-build 的 `ROOT_FILE_BLACKLIST`（与 `.pending-backlinks.yaml` 同，03-02 落地）
- graph-build 任意次重建**不影响** pending 队列里的待审条目

---

## 与 deprecate 的联动

当 `health deprecate <slug>` 执行时：

1. 扫描 `.pending-edges.yaml`
2. 将所有 `source == <slug>` 或 `target == <slug>` 的未审 pending 标记 `decision=reject`、`reviewed=true`
3. 移入 `reviewed_history`（原因：端点已废弃，推断边无意义）
4. 守"废弃文档不再参与任何推断边人审"——避免 edge-review 时处理已无意义的候选

> 仿 `backlink-rules.md`「与 deprecate 的联动」：backlink 的步骤 2/3 是"来源/目标 deprecated 则标 consumed=true"，pending-edges 对应"来源/目标 deprecated 则标 reject 移入 history"。

---

## 与回退/零破坏的关系

- `.pending-edges.yaml` 放 `.knowledge/` 根（与 `.pending-backlinks.yaml` **同级**），**不放 `.graph/` 下**
- 理由：删 `.graph/` 回退到纯文档库后，pending 队列里「待回写文档的关系建议」仍有意义（与 backlink 队列同性质，服务文档治理不服务图），故应存活
- lint 对 `.pending-edges.yaml` 不存在时**静默跳过**（不报错、不计数）——保证"删 pending 文件 = 队列清空"无副作用
- 删 `.knowledge/.pending-edges.yaml` = 清空待审队列（已审历史丢失可接受，文档 frontmatter 是真理源）
