# 维护（health）详细规则

> 由 `/knowledge-wiki health` 使用。SKILL.md 仅保留入口与索引，本文件是唯一权威源。

---

## 综合报告（health）

```
📊 知识库健康报告（2026-05-12）

文档总数：47 篇（active: 32  draft: 10  deprecated: 5）
  ├─ glossary: 12  design: 8  requirements: 3  flows: 15
  ├─ case: 5  apis: 2  db: 1  ops: 0  synthesis: 1
  └─ 近 30 天活跃：ingest 15 | ask 28 | health 5

[腐烂检测]  EXPIRED 3 篇 | WARNING 5 篇
[覆盖率]    未覆盖模块：goods / queue / redis3
[外部源]    3 个源，上次扫描 22 天前
[一致性]    ⚠️ 2 条 WARNING（运行 health lint 查看详情）
[反向引用]  📋 5 条 pending（运行 health backlink-consume 消费）
[索引状态]  ✅ 正常（上次重建 5 天前；超过 30 天提示重建）
[操作日志]  digest 已重建（最近 50 条），ask 未命中高频：2 个主题

/knowledge-wiki health rot       查看过期详情
/knowledge-wiki health scan      检查外部源
/knowledge-wiki health coverage  查看覆盖率（含问答缺口）
/knowledge-wiki health lint      一致性检查
/knowledge-wiki health backlink-consume  消费反向引用
/knowledge-wiki health index-rebuild     重建索引
```

### 综合报告生成流程

`health`（无子命令）执行时按以下顺序：

```
1. [digest 重建] 重新生成 .logs/digest.md（详见下方 §digest 重建）
2. [统计] 扫描 10 个业务目录，统计各 type 文档数 + status 分布
3. [rot 快速摘要] 检查 EXPIRED/WARNING 数量（不做批量决策询问）
4. [coverage 快速摘要] 列出未覆盖模块名（不做详细报告）
5. [外部源] 读取 .sources.yaml，计算 last_synced 距今天数
6. [lint 快速摘要] 仅检查 L7（pending 积压）+ L9（过期数）+ 索引年龄
7. [反向引用] 统计 .pending-backlinks.yaml 中 consumed==false 的条目数
8. [索引状态] 读取 _meta.yaml.last_full_rebuild，判断是否超 30 天
9. [日志摘要] 从 digest.md 提取：近 30 天操作统计 + ask 未命中高频数
10. [输出] 按上方模板格式输出综合报告
11. [操作日志] 追加一条 health 记录到 personal log
```

### 输出模式选项

```bash
/knowledge-wiki health              # 默认：人类可读格式（emoji + 文本）
/knowledge-wiki health --json       # JSON 格式供外部工具消费
/knowledge-wiki health --verbose    # 含 ASCII 图表的详细模式
```

#### --json 输出格式

```json
{
  "generated_at": "2026-05-26T15:00:00+08:00",
  "summary": {
    "total_docs": 47,
    "by_status": {"active": 32, "draft": 10, "deprecated": 5},
    "by_type": {"glossary": 12, "design": 8, "requirements": 3, "flows": 15, "case": 5, "apis": 2, "db": 1, "ops": 0, "synthesis": 1}
  },
  "rot": {"expired": 3, "warning": 5},
  "coverage": {"uncovered_modules": ["goods", "queue", "redis3"]},
  "sources": {"total": 3, "oldest_sync_days": 22},
  "lint_quick": {"warnings": 2, "errors": 0},
  "backlinks": {"pending": 5},
  "index": {"last_rebuild_days": 5, "needs_rebuild": false},
  "digest": {"recent_count": 50, "ask_miss_topics": 2}
}
```

> `--json` 模式下不输出 emoji/文本/子命令提示，纯 JSON 输出到 stdout。适用于：
> - CI 集成（定期 cron 检查健康度）
> - 外部看板工具拉取数据
> - 脚本自动判断是否需要维护

#### --verbose 输出（含 ASCII 图表）

在默认输出基础上，追加以下可视化段落：

```
📊 知识库健康报告（2026-05-12）
...（标准报告内容）...

─── 文档分布（按 type）──────────────────────────────
glossary     ████████████ 12
flows        ███████████████ 15
design       ████████ 8
case         █████ 5
requirements ███ 3
apis         ██ 2
db           █ 1
synthesis    █ 1
ops          ░ 0

─── 状态分布 ─────────────────────────────────────────
active       ████████████████████████████████ 32 (68%)
draft        ██████████ 10 (21%)
deprecated   █████ 5 (11%)

─── 近 30 天操作趋势 ─────────────────────────────────
ingest ■■■■■■■■■■■■■■■ 15
ask    ■■■■■■■■■■■■■■■■■■■■■■■■■■■■ 28
health ■■■■■ 5
```

> `--verbose` 适合人工快速定位知识库短板（哪些 type 文档太少、哪些模块未覆盖）。

---

## rot（腐烂扫描）

扫描所有文档 `expires` 字段，FRESH 静默，仅输出 EXPIRED / WARNING：

| 状态 | 条件 | 建议动作 |
|------|------|---------|
| EXPIRED | 超过 expires | `health audit` 或 `health deprecate` |
| WARNING | 距 expires ≤ 30 天 | 尽快确认 |

**无过期文档时：完全静默。**

### 批量决策入口（输出 EXPIRED 列表后询问）

```
发现 {N} 篇过期文档。选择处理方式：
[1] 逐篇 audit（交互式进入 audit 流程，逐个确认 有效/更新/废弃）
[2] 批量延期 90 天（仅推迟 expires，status 不变，sources 追加「批量延期 @who YYYY-MM-DD」）
[3] 批量标记 deprecated（由用户二次确认 slug 列表后，逐篇检查引用后变更）
[4] 仅列表不处理
```

- 选 [2] 需输入原因说明（"代码未变" / "推迟重评"等），写入 sources
- 选 [3] 走 deprecate 标准流程（必须逐篇检查引用、不可跳过）

### rot 附带：related 悬空链接清理

`rot` 执行时**顺带**扫描所有文档的 `related` 字段，检测以下两类问题：

| 异常类型 | 检测逻辑 | 自动动作 |
|---------|---------|---------|
| **deprecated 引用** | related 中的 `[[slug]]` 对应文档 status=deprecated | 自动移除该 related 条目 + 追加注释 `# removed: [[slug]] (deprecated since YYYY-MM-DD)` |
| **悬空链接** | related 中的 `[[slug]]` 对应的 .md 文件不存在 | 标记 WARNING，不自动移除（可能是 slug 重命名未同步，需人工确认） |

```
[related 清理]（rot 附带）
  🗑️ flows/order-process.md: 移除 [[old-config]]（deprecated 2025-12-01）
  🗑️ apis/print-api.md: 移除 [[legacy-timeout]]（deprecated 2025-10-15）
  ⚠️ ops/fallback.md: 悬空引用 [[non-exist-slug]]（文件不存在）

已自动清理 2 条 deprecated 引用；1 条悬空链接需人工确认
```

**与 lint L2/L3 的关系**：rot 做轻量级 related 清理（自动移除 deprecated）；lint L2/L3 做全量检测（含报告但默认不修改，需 `--fix`）。两者互补不冲突。

---

## scan（外部源扫描）

> **工具路由**：scan 中每个外部源 URL 严格遵循「URL 处理」铁律——内部文档平台 URL 必走 internal-docs skill，其他走 agent-browser。详见 `url-handling.md`。

完整流程见 `url-handling.md` 末尾「scan 中的路由」节。

---

## coverage（覆盖率）

### 项目根检测

按以下优先级定位根目录：
1. `git rev-parse --show-toplevel` （优先以 git 根为准）
2. 向上查找包含 `.knowledge/` 的最近祖先目录
3. 该 path 不是当前 PWD → 提示："检测到项目根为 {root}，在该路径下扫描。"并以其为扫描起点
4. 未找到（项目外）→ 中止："未在当前路径及祖先目录找到 .knowledge/，请在项目根运行。"

### 扫描流程

```
1. 以项目根为起点扫描顶层目录（排除 node_modules/vendor/.git/.knowledge/dist/build/.next/__pycache__），提取目录名作为模块列表
2. 读取 .knowledge/ 下所有 .md 的 tags + title，提取已覆盖模块
3. 比对：目录名 ∉ 已覆盖模块 → 标记为未覆盖
4. 输出：未覆盖模块列表 + 建议的 /knowledge-wiki in 命令
```

仅建议，不阻断任何操作。

---

## audit `<slug>`（确认有效）

```
展示：title / TL;DR / 当前 expires
询问：[1] 确认有效  [2] 需要更新  [3] 已废弃

选 [1]：
  status → active
  expires → 按 type 分支处理（见下方「expires 续期分支」）
  sources 追加："人工确认 @who YYYY-MM-DD"

选 [2]：跳转 /knowledge-wiki in --update <slug>
选 [3]：跳转 /knowledge-wiki health deprecate <slug>
```

### expires 续期分支

| 文档当前 type / expires | audit 选 [1] 后的处理 |
|------------------------|----------------------|
| `type: glossary` 且 `expires: never` | **保持 never**（术语长期有效，不续期为日期）；询问可选 `[1a] 维持 never  [1b] 改为 +365 天` |
| `type: adr` 且 `expires: never` | 同上保持 never（决策快照，不过期） |
| 其他 type 或 `expires` 是日期 | `expires → 今日 + 该 type 的 expires_days`（从 `_registry.yaml` 读取，不再写死 90 天） |

> 续期天数从 `references/templates/_registry.yaml` 的 `expires_days` 字段读取，避免与录入时的过期日期不一致。

---

## deprecate `<slug>`（标记废弃）

```
1. rg 查找所有引用该 slug 的文档
2. 列出引用处，确认后：
   - status → deprecated
   - 引用处追加：<!-- deprecated: [[<slug>]] 已废弃，请更新引用 -->
```

废弃前必须处理引用，防止悬空链接。

---

## lint [NEW]（一致性检查）

> **完整规则见 `references/lint-rules.md`**。本节为入口摘要和与 health 其他子命令的联动说明。

### 用法

```bash
/knowledge-wiki health lint           # 只报告，不修改任何文件
/knowledge-wiki health lint --fix     # 安全自动修复（仅 L3 + L8）
```

### 检查项速查

| # | 检查项 | 级别 | --fix 可修复 |
|---|--------|------|------------|
| L1 | 数值/状态矛盾 | ERROR/WARNING | ❌ |
| L2 | 悬空引用（文件不存在） | ERROR | ❌ |
| L3 | 废弃引用未标记 | WARNING | ✅ 自动加 ~~~~ |
| L4 | 孤儿文档（无 idx 条目） | WARNING | ❌（用 index-rebuild） |
| L5 | 孤儿索引（无对应文件） | ERROR | ❌ |
| L6 | related 膨胀（>12 条） | WARNING | ❌ |
| L7 | pending 队列积压（>7 天） | WARNING | ❌（用 backlink-consume） |
| L8 | idx status 不一致 | WARNING | ✅ 自动同步 |
| L9 | 过期未处理 | EXPIRED 类 | ❌（用 rot/audit/deprecate） |

### 在综合报告中的角色

`health`（无子命令）执行时：
1. 先运行 **快速摘要模式**：检查 L7（pending 积压）+ L9（过期数）+ 索引年龄 → 填入报告的「一致性」「反向引用」「索引状态」三行
2. 不做完整的 L1-L9 检测（耗时较长），仅在报告中提示 `health lint`

### [Phase 2 新增] 图 lint（L-graph-orphan-edge / L-graph-drift）

`health lint` 执行 L1-L9 后，**若 `.knowledge/.graph/graph.json` 存在**，额外加载它跑两个图 lint：

| 图 lint | 检测内容 | 级别 |
|---------|---------|------|
| L-graph-orphan-edge | 扫描 graph.json 中 `source_location` 为 null/空的边 | ERROR |
| L-graph-drift | 扫描 graph.json 边在源文档 frontmatter `related` 中找不到对应来源的漂移边 | ERROR |
| L-graph-unreviewed-in-links [Phase 3] | links 出现 confidence!=EXTRACTED 或 reviewed!=true 的边 | ERROR |
| L-pending-edge-reviewed-residue [Phase 3] | .pending-edges.yaml 的 pending[] 已批准未移入 history | WARNING |
| L-pending-edge-no-source [Phase 3] | .pending-edges.yaml 的 pending 边缺 source_location | ERROR |

结果汇总进同一份一致性报告（完整规则见 `references/lint-rules.md`）。

**图层不存在（未 graph-build 或已删 .graph/）时这两个图 lint 完全静默跳过——不报错、不计数、报告里不出现图 lint 段**，保证「删 .graph/ 后 health lint 行为与图层从未存在时一致」（守零破坏 GRAPH-05，是基线快照回归硬要求）。

**[Phase 3 补充]** `L-graph-unreviewed-in-links` 依赖 `graph.json`；`L-pending-edge-*` 两项依赖 `.knowledge/.pending-edges.yaml`——**对应文件不存在则该 lint 静默跳过**（不报错/不计数/报告不出现），与 Phase 2 图 lint 同纪律（守零破坏 GRAPH-05）。完整规则见 `references/lint-rules.md`。

两个图 lint 均 ERROR 级、均不支持 --fix（修复 = `health graph-build` 重建）。

---

## backlink-consume [NEW]（反向引用队列消费）

> **完整规则见 `references/backlink-rules.md`**。本节为入口摘要。

### 用法

```bash
/knowledge-wiki health backlink-consume
```

### 行为

1. 读取 `.pending-backlinks.yaml`
2. 过滤 `consumed == false` 的记录
3. 对每条记录：将 `[[from]]` 追加到 target 文档的 related 字段（上限控制 15 条）
4. 标记已消费，更新 yaml
5. 自动 git commit

### 输出示例

```
🔗 反向引用消费完成

已处理：3 条
  ✅ flows/fallback-strategy.md ← 追加 [[print-timeout]]
  ✅ glossary/timeout.md ← 追加 [[print-timeout]]
  ⏭️ ops/timeout-v1.md ← 已存在，跳过

队列剩余：0 条
```

### 安全保障

- 消费前检查工作区是否干净（`git diff --quiet`）
- 消费前 `git pull --rebase` 确保最新
- 消费后自动 commit

---

## edge-review [Phase 3 新增]（推断边逐条人审）

> **完整规则见 `references/pending-edges-rules.md` + `references/trust-rules.md`**。本节为入口摘要。edge-review 是 **AI 解释型 health 子命令**（与 backlink-consume 同载体，由规则文档驱动 AI 执行，**无独立 python 脚本**）。

### 用法

```bash
/knowledge-wiki health edge-review              # 逐条人审 .pending-edges.yaml 未审条目
/knowledge-wiki health edge-review --dry-run    # 仅展示待审列表不决策（可选）
```

### 行为

1. 读取 `.knowledge/.pending-edges.yaml`，过滤 `reviewed==false` 的条目；**队列文件不存在或 pending 为空则提示「无待审推断边」优雅退出**（不报错，守零破坏）。
2. **逐条**展示（边方向 `source→target` / confidence / 推断依据 `source_location` / `proposed_by`），逐条给出决策选项 `[a]approve [r]reject [s]skip`——**无批量 auto-approve**（守 C7 逐条问询 / SC#2 人审不可绕过）。
3. **approve（仅 INFERRED 边）**：在源文档 frontmatter `related` 追加 `[[target]]`（复用 backlink-consume 安全追加逻辑，上限控制 15 条）→ 标 `decision=approve` / `reviewed=true` → 移入 `reviewed_history` → 写 C6 操作日志 → 提示「运行 `health graph-build --incremental` 派生为权威边」**不自动跑 graph-build**。
4. **AMBIGUOUS 边只展示 `[r]reject [s]skip`，机制级禁止 approve**（指向 `trust-rules.md` §AMBIGUOUS 护栏：AMBIGUOUS 永不作硬结论、永不进 links）。
5. **reject**：标 `decision=reject` 移入 `reviewed_history`，不写文档不入图。
6. **收尾**：更新队列文件 + `reviewed_history` FIFO 截断 200 条。

### 输出示例

```
🔍 推断边人审（edge-review）

待审：3 条（INFERRED 2 | AMBIGUOUS 1）

[1/3] INFERRED: print-timeout → fallback-strategy
      source_location: flows/print-timeout.md:12:related 注释
      proposed_by: manual
      → [a]approve  [r]reject  [s]skip
      选择：a
      ✅ approved → flows/print-timeout.md 追加 [[fallback-strategy]]

[2/3] AMBIGUOUS: order-table → delivery-config
      source_location: manual:语义推测
      proposed_by: manual
      → [r]reject  [s]skip（AMBIGUOUS 禁止 approve）
      选择：r
      ❌ rejected

[3/3] INFERRED: timeout-config → print-api
      ...skip

────────────────────
完成：reviewed 3 | approved 1 | rejected 1 | skipped 1
docs_updated: 1（flows/print-timeout.md）
提示：运行 health graph-build --incremental 将已批准边派生为权威边
```

### 安全保障

- 写回文档前 `git diff --quiet` 检查工作区干净 + `git pull --rebase` 确保最新
- 写回后自动 `git commit -m "[kb] edge-review: 人审 N 条推断边"`
- **目标文档被删** → 跳过 + WARNING + 标 `decision=reject`（防无限重试）

**关键约束**：approve 唯一落地 = **写回源文档 frontmatter `related`**（守 SSOT，不直接 patch graph.json）；AMBIGUOUS 永不作硬结论（仅 reject/skip）。

---

## index-rebuild [NEW]（全量重建分段索引）

> **完整规则见 `references/index-rules.md`**。本节为入口摘要。

### 用法

```bash
/knowledge-wiki health index-rebuild
```

### 行为

1. 扫描 `.knowledge/` 下所有 10 个业务目录中的 .md 文件
2. 提取 frontmatter + TL;DR
3. 按 type 分组，覆写对应 idx 文件
4. 清理废弃 >180 天的条目
5. 更新 `_meta.yaml`
6. 附带一致性校验（L4 孤儿文档 + L5 孤儿索引 + L8 status 不一致）

### 触发时机

- 手动执行
- `_meta.yaml.last_full_rebuild` 距今 > 30 天时，`health` 综合报告自动提示

---

## coverage 增强版 [NEW]（含问答缺口分析）

原有覆盖率逻辑不变（目录映射），新增基于 log 数据的问答缺口分析。

### 新增段落输出

```
[问答缺口]（近 30 天，基于操作日志）
  高频未答（去重后 ≥3 次）：
    1. "配送超时配置" — 5 次未命中 → 建议 in
    2. "队列消费失败处理" — 3 次未命中 → 建议 in
  已解决（后来录入了）：
    ✓ "打印服务架构" — 原 4 次未命中，已于 05-20 录入
```

### 数据来源与过滤

详见 `references/log-rules.md`「coverage 缺口分析」：

- 数据源：`.logs/personal/*.md` 中近 7 天的 ask 未命中记录
- 过滤：排除编码问题、排查请求、个人事务等噪声
- 匿名：聚合报告不显示 @who 信息
- 条件：至少积累 7 天数据才分析；同类去重后 ≥3 次才算缺口

---

## digest 重建 [NEW]

`health`（无子命令，即综合报告模式）执行时，在生成报告前**自动重建** `.logs/digest.md`：

```
执行时机：health 综合报告开头，在各检查项运行之前
执行逻辑：详见 references/log-rules.md「digest.md 团队聚合」节
  1. grep -h "^## \[" .logs/personal/*.md
  2. 按时间倒序排序
  3. 取最近 50 条 + 统计段落
  4. 覆写 .logs/digest.md
```

> 注意：仅 `health`（无子命令）触发 digest 重建；`health lint`/`health rot`/其他子命令不触发。

---

## distill [NEW]（认知蒸馏）

> 借鉴 知识自动进化思路，为 knowledge-wiki 提供结构化的知识去重、合并与低质量清理能力。与 `lint` 互补——lint 侧重语义矛盾与引用一致性，distill 侧重内容重复与信息密度。

### 用法

```bash
/knowledge-wiki health distill           # 预览模式（只报告不修改）
/knowledge-wiki health distill --execute # 执行蒸馏（需用户确认）
```

### 设计原则

1. **不自动修改**——默认预览模式，`--execute` 模式下每步操作前均需用户确认
2. **同 type 范围内检测**——仅在同一 type 目录内做相似度比较（跨 type 语义差异大，误报率高）
3. **保护 canonical 与 active**——status=canonical 的文档不参与合并（仅参与相似度报告）；status=active 的文档合并前必须明确提示风险
4. **与现有流程联动**——合并/废弃后自动触发 deprecate 标准流程 + idx 更新 + pending-backlinks 清理

### 蒸馏三步

#### Step 1：重复检测（Jaccard 相似度）

**相似度算法**：

```python
def extract_words(text: str) -> set:
    """提取中文 bigram + 英文词汇（≥2 字符），用于 Jaccard 计算。"""
    # 中文 bigram：相邻 2 字滑窗（提升区分度，无需 jieba）
    chinese_bigrams = [text[i:i+2] for i in range(len(text)-1)
                       if all('\u4e00' <= c <= '\u9fff' for c in text[i:i+2])]
    # 英文：连续字母数字（≥2 字符），统一小写
    english = re.findall(r"[a-zA-Z0-9]{2,}", text.lower())
    return set(chinese_bigrams + english)

def jaccard_similarity(text_a: str, text_b: str) -> float:
    words_a, words_b = extract_words(text_a), extract_words(text_b)
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)
```

**比较文本**：取每篇文档的 `title + TL;DR + tags（用空格连接）+ 正文前 500 字`（不含 frontmatter）作为比较输入。

**阈值与判定**：

| Jaccard 相似度 | 判定 | 动作 |
|---------------|------|------|
| > 0.80 | 高度重复 | 候选合并（预览 + 用户决策） |
| 0.60 ~ 0.80 | 疑似相关 | 仅报告，建议检查是否需要关联 related |
| < 0.60 | 无关 | 忽略 |

**性能控制**：
- 仅在同一 type 目录内做两两比较
- 单目录文档数 > 100 时，按 created 降序取最近 100 篇参与比较
- 总比较对数上限 5000（超出时随机采样）

#### Step 2：低质量检测

扫描所有文档，以下条件**全部满足**时标记为低质量候选：

| 条件 | 说明 |
|------|------|
| 正文（不含 frontmatter）< 50 字 | 信息密度过低 |
| status = draft | 仅清理草稿，不动已确认文档 |
| created 距今 > 30 天 | 长期未补充的草稿 |
| 非 glossary stub | 排除 Step 2.7 自动创建的占位符（sources 含"自动抽取"字样的 glossary） |

#### Step 3：孤立知识检测

扫描所有文档，以下条件**全部满足**时标记为孤立候选：

| 条件 | 说明 |
|------|------|
| related 字段为空数组 `[]` | 无任何关联 |
| 无任何文档在其 related 中引用该 slug | 完全孤立 |
| status = draft | 仅提示草稿 |
| created 距今 > 14 天 | 给予新文档 2 周建立关联的缓冲期 |

### 预览输出模板

```
🧪 认知蒸馏预览

[重复检测]（同 type 目录内 Jaccard > 0.80）
  ① ops/print-timeout.md ↔ ops/printer-timeout-config.md
     相似度：0.87 | 建议：合并（title/TL;DR 高度重叠）
  ② flows/order-cancel.md ↔ flows/cancel-order-process.md
     相似度：0.82 | 建议：合并（仅表述差异）

[疑似相关]（Jaccard 0.60~0.80，仅提示）
  ③ design/print-arch.md ↔ design/printer-service-design.md
     相似度：0.65 | 建议：检查 related 是否已关联

[低质量]（正文 <50 字 + draft + 超 30 天）
  ④ glossary/channel-fee.md — 正文 28 字，创建于 2026-04-01
  ⑤ ops/temp-fix.md — 正文 15 字，创建于 2026-03-20

[孤立知识]（无 related + 无被引用 + draft + 超 14 天）
  ⑥ case/timeout-issue.md — 创建于 2026-04-15，无任何关联

统计：重复对 2 | 疑似相关 1 | 低质量 2 | 孤立 1
执行蒸馏：/knowledge-wiki health distill --execute
```

### --execute 执行流程

执行时逐组展示并等待用户决策：

**重复对处理**（逐对询问）：

```
重复对 ①：ops/print-timeout.md ↔ ops/printer-timeout-config.md
  A：print-timeout — 创建 2026-05-01，正文 320 字，active
  B：printer-timeout-config — 创建 2026-04-15，正文 180 字，draft

选择：
[1] 合并到 A（保留 A，B 标记 deprecated，B 的独有内容追加到 A）
[2] 合并到 B（保留 B，A 标记 deprecated，A 的独有内容追加到 B）
[3] 均保留，仅互加 related（判定为不同视角）
[4] 跳过
```

**低质量处理**（批量询问）：

```
低质量候选（2 篇）：
  ④ glossary/channel-fee.md — 28 字
  ⑤ ops/temp-fix.md — 15 字

选择：
[1] 批量标记 deprecated（走 deprecate 标准流程）
[2] 逐个处理（对每篇选择 deprecate / 保留并提醒补充 / 跳过）
[3] 全部跳过
```

**孤立知识处理**（批量询问）：

```
孤立知识候选（1 篇）：
  ⑥ case/timeout-issue.md

选择：
[1] 推荐关联（AI 扫描相关文档，建议 related 列表并追加）
[2] 标记 deprecated
[3] 跳过
```

### 执行后联动

蒸馏 `--execute` 完成后自动执行：

| 动作 | 触发条件 | 执行内容 |
|------|---------|---------|
| deprecate 标准流程 | 文档被标记废弃时 | rg 查引用 → 标记 deprecated → 引用处追加注释 |
| idx 更新 | 文档 status 变更时 | 更新对应 .index/{type}.idx.md 中的 status 列 |
| pending-backlinks 清理 | 文档被 deprecated 时 | 清理 .pending-backlinks.yaml 中涉及该 slug 的条目 |
| _meta.yaml 更新 | 任何蒸馏执行后 | 写入 `last_distill: YYYY-MM-DDTHH:MM` |
| 操作日志 | 始终 | 追加 health/distill 记录到 personal log |

### 蒸馏完成输出

```
🧪 认知蒸馏完成

合并：2 对（4 篇 → 2 篇）
废弃：1 篇低质量 + 2 篇重复源
新增关联：1 篇孤立文档追加 related
当前总量：45 篇（active: 32  draft: 8  deprecated: 5）

下次蒸馏建议：知识库文档数增长 20% 或距上次蒸馏 >30 天时
```

### 与 lint 的关系

| 检测项 | lint | distill | 说明 |
|--------|------|---------|------|
| 语义矛盾 | L1 ✅ | ❌ | lint 专属 |
| 悬空引用 | L2 ✅ | ❌ | lint 专属 |
| 内容重复 | ❌ | ✅ | distill 专属 |
| 低质量 | ❌ | ✅ | distill 专属 |
| 孤立知识 | L4（孤儿 idx） ✅ | ✅（无 related） | 视角不同：lint 查索引孤儿，distill 查关联孤岛 |
| related 膨胀 | L6 ✅ | ❌ | lint 专属 |

### 在综合报告中的角色

`health`（无子命令）执行时：在 Step 6（lint 快速摘要）后、Step 7（反向引用）前，新增 **Step 6.5 进化建议**：

- 快速扫描：仅取每个 type 目录前 20 篇文档做 Jaccard 抽样 + 低质量计数 + 孤立计数
- 填入报告的「进化建议」行
- 不做完整蒸馏（耗时较长），仅在报告中提示 `health distill`

---

## evolve（进化建议）[NEW]

> 嵌入综合报告的主动进化指标，帮助用户识别知识库可优化的方向。不作为独立子命令，而是综合报告的一个段落。

### 综合报告新增输出段落

在 `[一致性]` 和 `[反向引用]` 之间插入：

```
[进化建议]
  🔄 疑似重复：{N} 对文档高度相似（运行 health distill 查看）
  📉 低活跃：{M} 篇 draft 超 30 天未审核
  🔗 孤立知识：{K} 篇无任何关联
  📊 覆盖不均：{type_max}/ {count_max} 篇 vs {type_min}/ {count_min} 篇
```

### 各指标计算

| 指标 | 计算方式 | 显示条件 |
|------|---------|---------|
| 疑似重复 | 每个 type 目录取前 20 篇做 Jaccard 抽样，计 > 0.80 的对数 | 对数 > 0 |
| 低活跃 | 统计 status=draft 且 created 距今 >30 天的文档数 | 数量 > 0 |
| 孤立知识 | 统计 related=[] 且无被引用 且 created 距今 >14 天 的文档数 | 数量 > 0 |
| 覆盖不均 | 比较各 type 文档数，展示最多 vs 最少的 type | 最多/最少比值 > 5 |

全部指标为 0 时，该段落整体不输出（静默放行原则）。

---

## 操作日志记录 [NEW]

每次 `health` 及其子命令执行完成后，**必须**追加一条记录到 `.logs/personal/{user-id}.md`。

详见 `references/log-rules.md`「日志条目格式」的 **health 类型**。

---

## 异常恢复（修改性子命令）

| 子命令 | 失败场景 | 恢复策略 |
|--------|---------|---------|
| `backlink-consume` | git commit 失败（脏工作区/合并冲突） | `git stash` → 重试 commit → 仍失败则中止并输出 `git stash pop` 恢复命令 |
| `backlink-consume` | 目标文件被外部删除（写入时 .md 不存在） | 跳过该条目 + WARNING + 标记 consumed（防止无限重试） |
| `index-rebuild` | 覆写中断（磁盘满/权限不足） | 保留部分写入的 idx（不删除已成功的文件），输出恢复命令：`/knowledge-wiki health index-rebuild`（幂等，可安全重跑） |
| `lint --fix` | 文件写入失败 | 单文件失败不影响其他文件，输出失败清单 + 手动修复建议 |
| 通用 | `.knowledge/` 目录不存在 | 中止 + 提示 `/knowledge-wiki init` |

---

## graph-build [Phase 1 新增]（全量编译图谱）

> 从 `.knowledge/{10 业务目录}/*.md` 全量编译出可被 networkx 整体加载的 `graph.json`（node-link schema）。**完整规则见 `references/graph-build-rules.md`**，本节为入口摘要。

### 用法

```bash
/knowledge-wiki health graph-build          # 全量编译图谱 graph.json + 摘要
/knowledge-wiki health graph-build --full   # 全量重建兜底（与默认行为一致，显式声明全量）
```

### 行为

仿 `index-rebuild` 范式（差异仅在「编译产物是 graph.json 而非 idx」），按以下顺序（完整 10 步见 `graph-build-rules.md` §2）：

1. 扫描 10 个业务目录的 *.md（排除 .index/.logs/.graph/ 系统目录与根文件）
2. 解析每篇 frontmatter（title/type/status/expires；缺失按 graph-model.md 容错降级，不中断）→ 建节点（glossary/ 标 `glossary_term`，其余 `document`）
3. 计算 `source_hash`：对全部业务 .md 的 (相对路径, mtime, size) 三元组排序求 sha256（Phase 1 仅存储不消费）
4. 原子写 graph.json：同盘 tempfile → flush + os.fsync → os.replace 覆盖（绝无半截 JSON）
5. networkx 自检：`nx.node_link_graph(payload, edges="links")` 加载回内存校验无悬空端点
6. 输出 GRAPH-03 摘要 + 追加 C6 操作日志到 `.logs/personal/{user-id}.md`

### 调用方式

AI 通过 `run_terminal_cmd` 执行（脚本由 `init` 复制到 `.knowledge/.graph/scripts/`，见 `references/directory-structure.md`）：

```bash
uv run .knowledge/.graph/scripts/graph_build.py --kb-root .knowledge [--full]
```

> 退出码：0 成功 / 1 kb-root 不存在 / 2 `.build.lock` 存在（并发）。首次 `uv run` 自动拉起隔离环境装 networkx==3.6.1，不污染全局；删 `.graph/` 即彻底回退。

### 摘要输出样例

```
🕸️ 图谱编译完成（full）

源文档：47 篇 → 节点：48（文档 47 + 术语 1）
边：0 条（Phase 1 地基，边模型见 Phase 2）
可信度分布：EXTRACTED 0 | INFERRED 0 | AMBIGUOUS 0
节点状态分布：canonical 2 | active 32 | draft 10 | deprecated 4
source_hash：sha256:ab12…（与上次一致 / 已变更）
产物：.knowledge/.graph/graph.json（128 KB）

下一步：Phase 2 将从 related/[[slug]] 派生有类型有向边
```

> 「可信度分布」即使 Phase 1 全为 0 也必须打印——它是 GRAPH-03 的明确验收字段。

### 触发时机

- **手动执行**（`health graph-build` / `--full`）。
- **Phase 1 不进 health 综合报告**：综合报告 11 步流程一字不改，图谱 staleness 提示（source_hash 漂移则提示重建）留给 Phase 2 增量阶段再加，以守住基线快照回归（GRAPH-05）。

---

## graph [Phase 6 新增]（涌现分析：社区检测 + 中心度 + 内聚度）

> 在 graph.json 上**非实时全量**跑 Louvain 社区检测 + 中心度（god nodes）+ 内聚度评分，结果落 `communities.json` + 回填 graph.json 的 `centrality`/`community` 预留字段。**仅 `health graph` 显式触发全量跑，绝不进 in/ask 热路径**（ANALYZE-05）。完整算法见 `references/scripts/graph_analyze.py`，本节为入口摘要。

### 用法

```bash
/knowledge-wiki health graph                  # 全量跑社区检测 + 中心度 + 内聚度 + 报告
/knowledge-wiki health graph --min-nodes 20   # 调小语料门槛（默认 10）
```

### 行为

引 `graph_analyze.py` 算法（本节不抄实现），按以下顺序：

1. 读 `.graph/graph.json`（不存在/损坏则降级，见下表）。
2. 有向转无向加权图（双向边累加 weight），跑 Louvain（`seed=42` + 社区 id 按成员最小 slug 重映射 → byte 级确定性）。
3. 算 degree / betweenness / pagerank 三中心度 + god node 业务校验（高 degree + 高 betweenness 且 `status∈{canonical,active}` 才是枢纽候选）+ 孤岛检测。
4. per-community 内聚度（内部边占比）+ 全局 modularity。
5. 小语料（节点数 < `--min-nodes`）跳过社区检测，仍输出中心度 / 孤岛（`skipped=true`）。
6. 写 `.graph/communities.json` + **原子回填** graph.json 节点的 `centrality`/`community`（不碰文档，不影响 source_hash）。
7. 追加 C6 操作日志到 `.logs/personal/{user-id}.md`（layer 标 `graph-analyze`）。

### 调用方式

AI 通过 `run_terminal_cmd` 执行（脚本由 `init` 复制到 `.knowledge/.graph/scripts/`，见 `references/directory-structure.md`）：

```bash
uv run .knowledge/.graph/scripts/graph_analyze.py --kb-root .knowledge --seed 42 --min-nodes 10 --json
```

> 退出码：0 成功（含小语料 skipped）/ 1 kb-root 或 graph.json 不存在或损坏 / 2 `.analyze.lock` 存在（并发）。`health graph` 优先用 `--json` 拿结构化结果渲染报告。

### 报告渲染骨架（AI 据 communities.json 渲染）

正常骨架：

```
🕸️ 图谱涌现分析（health graph · 非实时全量 · 不进 in/ask 热路径）

源图：48 节点 / 36 边（source_hash sha256:ab12…，与文档集一致）
算法：louvain-nx3.6.1@1.0 · seed 42 · 整图模块度 modularity 0.62

📚 知识章节（社区检测，5 个社区）——type 之外的正交视图
  ① 配送域（主导 flows，12 节点）  内聚度 0.78 ✅ 自洽
       delivery-flow / fallback-strategy / print-timeout …
  ② 术语域（主导 glossary，6 节点） 内聚度 0.31 ⚠️ 横切性强（术语天然外联多，正常）

⚡ 知识枢纽（中心度涌现提示，供人工判断）
  · [[delivery-flow]]（flows·active）degree 0.34 / betweenness 0.41 / pagerank 0.087
       ⚡ 涌现提示：高连接+高桥接且为 active 知识，可能是核心知识枢纽，供人工判断
  （注：高中心度但 deprecated 的节点不列为枢纽——避免把废弃知识误报为核心）

🏝️ 待连接（孤岛）
  · [[orphan-doc]]（ops·draft）无任何关联边 —— 待连接
  （建议：补 frontmatter related 或人审推断边 health edge-review）

来源：.knowledge/.graph/communities.json（图的派生分析，非文档原文，非真理源）
```

小语料跳过骨架：

```
⚠️ 语料过小（节点数 6 < 10），跳过社区检测——需更多节点形成有意义的社区。
⚡ 知识枢纽 … 仍输出
🏝️ 待连接 … 仍输出
```

### 渲染措辞铁律（守 C1）

1. 社区标「知识章节 / 涌现提示」「type 之外的正交视图」，不说「这就是知识结构」。
2. god node 强制「⚡ 涌现提示，供人工判断」；仅 `is_hub_candidate=true`（高中心度且高 status）才提示「可能是核心枢纽」；**deprecated 高中心度节点不列入枢纽榜**——避免把废弃知识误报为核心。
3. 孤岛「🏝️ 待连接」中性表述，非「坏文档」。
4. 低 cohesion 标「横切性强（正常）」，非「质量差」（术语域天然低 cohesion 是正常的）。
5. 来源明示「`communities.json` 是图的派生分析，非文档原文，非真理源」。

### 触发时机 + 不进综合报告

- **手动执行**（`health graph`）。
- **Phase 6 不进 health 综合报告**：综合报告 11 步流程一字不改；`health graph` 是独立重算法子命令，每次 health 都跑会违反非实时（ANALYZE-05）+ 破坏基线快照回归。综合报告最多加一行「图谱分析：运行 health graph」提示（本期保守不加，仿 graph-build 克制）。

### 降级（凭 graph_analyze.py 退出码 + communities.json skipped 字段，不自造判定）

| 场景 | 行为 | 退出码 |
|---|---|---|
| graph_analyze.py 不存在（删 .graph/ / Phase 6 未启用） | 「图分析未启用（Phase 6）；如需运行 `health graph-build` 后再 `health graph`」静默优雅退出 | 0 |
| graph.json 不存在（未 graph-build / 删 .graph/） | 「未编译图谱，请先运行 `/knowledge-wiki health graph-build`」 | 1 |
| 节点 < min-nodes（小语料） | 跳过社区检测，仍出中心度/孤岛，`skipped=true` | 0 |
| graph.json 损坏 | 「图谱损坏，建议重建 `health graph-build`」 | 1 |

> 删 `.graph/` 后 `health graph` 优雅提示「图分析未启用」退 0——行为与「Phase 6 从未存在」一致；`health` 综合报告不依赖 communities.json，故删 .graph/ 后 `health`/`health lint` 与图层从未存在完全一致（守基线快照）。

### C6 操作日志

复用既有 `write_c6_log` 通道，layer 标 `graph-analyze`（区别于 graph-build 的 `graph-build`），detail 记 `node_count`/`community_count`/`modularity`/`skipped`/`source_hash`。

### 🔍 可探索问题板块 [Phase 8 新增]

> 在拿到 `communities.json` 后，把图孤岛 / 低内聚社区 / 知识枢纽 + coverage 问答缺口融合成「可深挖」的**可探索问题**，让 `ask` 从「找文档」延伸到「找盲区」。**挂 `health graph` 同批输出**（D-05）——复用同批已加载图 + 已算社区/中心度/孤岛（零额外扫描），**绝不新建 `health explore` 子命令**。完整算法见 `references/scripts/explore_questions.py`，本块为渲染规则。

**第 8 步**（接在 §graph 行为第 7 步之后叠加，既有 7 步一字不改）：

8. [Phase 8] 在拿到 `communities.json` 后，调 `explore_questions.py` 生成可探索问题（融合图孤岛 / 低内聚社区 / 枢纽 + coverage 缺口 → 加权排序 + 三层去噪 + Top-N → `explorable-questions.json`），AI 据其渲染『🔍 可探索问题』板块。

#### 调用方式

AI 通过 `run_terminal_cmd` 执行（脚本由 `init` 复制到 `.knowledge/.graph/scripts/`，见 `references/directory-structure.md`）：

```bash
# 在 graph_analyze.py --json 拿到 communities.json 后追加调用：
uv run .knowledge/.graph/scripts/explore_questions.py --kb-root .knowledge --top-n 10 --json
# AI 从 health coverage「已解决（后来录入了）」分组取已解决缺口 hash，写临时文件传 --resolved-gaps（不重算 sha1）：
uv run .knowledge/.graph/scripts/explore_questions.py --kb-root .knowledge --top-n 10 --resolved-gaps /tmp/resolved.txt --json
```

> 退出码：0 成功（含空候选 / 小语料 skipped）/ 1 kb-root 或 communities.json 不存在或损坏 / 2 `.explore.lock` 存在（并发）。`health graph` 优先用 `--json` 拿结构化问题信号渲染板块。
> coverage 缺口候选（`--gaps-file`）与已解决 hash（`--resolved-gaps`）均由 AI 从 `health coverage` 的「高频未答」/「已解决」分组写临时文件传入——**脚本只消费结构化缺口，不重算 sha1**（守消费定位）。

#### 报告渲染骨架（AI 据 explorable-questions.json 渲染）

```
🔍 可探索问题（health graph 同批 · 非实时 · 源自图孤岛/低内聚社区/枢纽 + coverage 缺口）

  ① [island] 「孤儿文档」未与任何知识关联，它应该连到哪里？
       为何值得挖：结构孤岛，补连可让它被检索与遍历命中 | 来源 island:orphan-doc
  ② [coverage-gap] 团队近 7 天 5 次问及某主题但无记录，要不要录入？
       为何值得挖：高频未命中且未录入，录入消除检索盲区 | 来源 coverage-gap:a1b2c3d4
  ③ [god-node] 「配送主流程」是枢纽，改动它会影响哪些知识？
       为何值得挖：高连接+高桥接，牵连面大，值得先盘下游 | 来源 god-node:delivery-flow

（共 10 条，按信号强度×需求热度排序 · 去噪 deprecated 1/pending 2/已解决 1）
来源：.knowledge/.graph/explorable-questions.json（图+日志的派生分析，非文档原文，非真理源）
提示：问题是探索入口，落地走 /knowledge-wiki in 或 health edge-review（由你判断）
```

#### AI 渲染铁律（守 C1 / D-04）

1. 全用疑问 / 建议口吻，绝不替用户下结论（不说「这是坏文档」「必须拆分」）。
2. low-cohesion 不得断言「质量差」或「联系松散」，须标「横切性强（正常）」（对齐本节渲染措辞铁律第 4 条 / `graph_analyze.py` 内聚度注释，不用「可能正常」的暗示性措辞）。
3. 每条问题保留 source typed-tag（`island:` / `low-cohesion:` / `god-node:` / `coverage-gap:`）可回溯（守 C1 来源铁律）。
4. 问题是探索入口（导航），不替用户执行 `in` / 建边——落地由用户判断走既有 `in` / `health edge-review`。
5. 渲染只润色 `explore_questions.py` 已生成的 `question` 模板文案（不得改变语义），不自创结论；落盘 `explorable-questions.json` 全字段确定性，AI 润色只在报告渲染层。

#### 降级（凭 explore_questions.py 退出码，不自造判定）

| 场景 | 行为 | 退出码 |
|---|---|---|
| explore_questions.py 不存在（删 .graph/ / Phase 8 未启用） | 「可探索问题未启用（Phase 8）」静默优雅退出，不影响 §graph 三段报告 | 0 |
| communities.json 不存在（未 health graph） | 跳过可探索问题生成（无图分析产物可消费） | 1 |
| 无候选（去噪后空） | 「暂无可探索问题」 | 0 |

> 删 `.graph/` 后 `health graph` 整体行为与「Phase 8 从未存在」一致（守基线快照）——`explorable-questions.json` 是纯派生消费品，删除无副作用。

#### C6 + 不进综合报告

`explore_questions.py` 写 C6 操作日志 layer 标 `graph-explore`（区别于 `graph-analyze`），detail 记 `questions` / `island` / `low_cohesion` / `god_node` / `coverage_gap` / `filtered_*` / `source_hash`。可探索问题随 `health graph` 显式触发，**绝不进 `health` 综合报告 11 步**（守非实时 + 基线快照，与 Phase 6 graph 同纪律）。

---

## discover [Phase 7 新增]（涌现发现：跨域关联候选 + AI 语义裁决 + 入队人审）

> 在 graph.json + 文档集上发现「相似度高/结构接近但图谱中未连接」的**跨域**文档对，AI 语义裁决后生成 INFERRED/AMBIGUOUS 候选 append 既有 `.knowledge/.pending-edges.yaml` 队列，经既有 `health edge-review` 逐条人审。**discover 是 AI 解释型 health 子命令**（与 `edge-review`/`graph` 同载体，**prefilter 脚本 `discover_prefilter.py` 做确定性初筛，AI 做语义裁决 + 入队**，非纯 python 脚本）。队列结构 / 人审消费 / AMBIGUOUS 护栏 / approve 回流 / graph-build 派生**全部 Phase 3 现成**（见 `references/pending-edges-rules.md` + `references/trust-rules.md`），本节只接上 Phase 3 预留的 discover 生成器接口（`pending-edges-rules.md` §Phase 7 生成器接口预留）。完整初筛算法见 `references/scripts/discover_prefilter.py`，本节为入口 + AI 裁决 + 入队契约。

### 用法

```bash
/knowledge-wiki health discover              # 跑初筛 → AI 逐对语义裁决 → 完整三检查 → append pending
/knowledge-wiki health discover --dry-run    # 仅输出 AI 裁决结果表，不入队（仿 edge-review）
```

### 行为

引 `discover_prefilter.py` 确定性初筛 + AI 语义裁决，按以下顺序：

1. 调 `discover_prefilter.py --json` 拿候选 JSON（脚本只读初筛：跨 type Jaccard + 三角闭合 + 排除①② + Top-N，**脚本不入队、不碰文档、不碰 graph.json**）。
2. 脚本退出码降级判定（见降级表）；候选为空 → 「无新涌现关联候选」优雅退 0。
3. **AI 逐对语义裁决**（读候选对文档原文，按 §AI 语义裁决 prompt 骨架决策）。
4. **AI 入队前完整三检查**（含③reject-history，见 §入队前完整三检查）。
5. **AI append `.pending-edges.yaml` 的 `pending[]`**（填全 11 字段，`proposed_by: discover`，见 §入队字段填充表）。
6. 写 C6 操作日志（layer 标 `discover`，见 §C6 操作日志）。
7. 输出摘要（候选数 / 入队数 / INFERRED / AMBIGUOUS / 丢弃数 / 跳过数，见 §输出摘要）。

### 调用方式

AI 通过 `run_terminal_cmd` 执行（脚本由 `init` 复制到 `.knowledge/.graph/scripts/`，见 `references/directory-structure.md`）：

```bash
uv run .knowledge/.graph/scripts/discover_prefilter.py --kb-root .knowledge \
  --min-jaccard 0.30 --high-jaccard 0.45 --min-shared-neighbors 2 --top-n 20 --json
```

> 退出码：0 成功（含空候选）/ 1 kb-root 或 graph.json 不存在或损坏 / 2 `.discover.lock` 存在（并发）。`health discover` 优先用 `--json` 拿结构化候选给 AI 裁决。**建议先 `health graph-build --incremental` 确保图最新**（缓解 graph.json stale 导致排除②漏判，仿 edge-review approve 后的提示驱动）。

### 降级（凭 discover_prefilter.py 退出码，不自造判定）

| 场景 | 行为 | 退出码 |
|---|---|---|
| discover_prefilter.py 不存在（删 .graph/ / Phase 7 未启用） | 「候选发现未启用（Phase 7）；如需运行 `health graph-build` 后再 `health discover`」静默优雅退出 | 0 |
| graph.json 不存在（未 graph-build / 删 .graph/） | 「未编译图谱，请先运行 `health graph-build`」 | 1 |
| 空候选（无跨域高相似无连接对） | 「无新涌现关联候选」 | 0 |
| graph.json 损坏 | 「图谱损坏，建议重建 `health graph-build`」 | 1 |
| `.discover.lock` 存在（并发） | 「候选发现正在进行中」 | 2 |

> 删 `.graph/` 后 `discover_prefilter.py` 副本一并消失 → `health discover` 优雅提示「候选发现未启用」退 0——行为与「Phase 7 从未存在」一致。**`.pending-edges.yaml` 在 `.knowledge/` 根、不在 `.graph/` 下**（`pending-edges-rules.md` §与 graph.json 的隔离）——删 .graph/ 后已入队的待审边不丢（与 backlink 队列同性质，服务文档治理不服务图）。

### 触发时机 + 不进综合报告

- **手动执行**（`health discover`）。
- **Phase 7 不进 health 综合报告**：综合报告 11 步流程一字不改；`health discover` 是独立重计算子命令（跑两两 Jaccard + 全图邻居运算，与社区检测同类），每次 health 都跑会违反非实时 + 破坏基线快照回归。
- **绝不进 in/ask 热路径**：discover 仅 `health discover` 显式触发跑（仿 `health graph` 措辞），守性能约束（「社区检测/中心度仅在 health 时跑（非实时）」精神）。

### AI 语义裁决

裁决在 `health discover` 命令体内**由 AI 执行（非脚本）**。AI 读 prefilter 输出的候选 JSON（`candidates[]` 含 `source`/`target`/`content_jaccard`/`struct_jaccard`/`shared_neighbors`/`signal`/`tier`/`source_location`），逐对读候选文档原文做语义裁决。**token 成本控制**：AI 先看候选对的 title/TL;DR 摘要，仅对摸不准的对读全文；候选量大时可调小 `--top-n`。

> **方法论母版**：graphify `semantically_similar_to` 语义判断范式 + 诚实铁律「if unsure, use AMBIGUOUS」。**适配 knowledge-wiki 治理**：不产数值 confidence（无 embedding/无数值结论），改为离散二级 INFERRED/AMBIGUOUS；relation 落 knowledge-wiki 取值集；产出直接对齐 `.pending-edges.yaml` 入队字段。

**四步决策骨架**（对每个候选对）：

- **(a) 是否真正相关？**——它们是否描述同一问题域、互为依赖、一个引用另一个的概念？
  - 否（仅共享通用词 / 巧合相似）→ **丢弃该对，不入队**。
- **(b) 若相关，relation 类型 + 方向（取值仅限）**：
  - `term_of` —— A 使用/从属于 B（B 是术语锚点 glossary）
  - `depends_on` —— A 依赖 B 实现/澄清（A 是 requirement 类）
  - `derived_from` —— A 派生/依据于 B（A 是 design/architecture/solution/adr/synthesis）
  - `references` —— 一般引用（**兜底**）
  - 方向 = source → target。**拿不准方向或类型 → 退 `references`（最中性）**。（类型推断可参考 `graph_build.py` 的 `infer_relation` 结构映射作先验，但以语义为准）
- **(c) 可信度分级**：
  - 关系明确、可一句话阐述「A 因何关联 B」→ **INFERRED**（可被人审 approve）
  - 仅「似乎相关」说不清确切关系 → **AMBIGUOUS**（机制级禁 approve，仅 reject/skip）
  - **绝不输出 EXTRACTED**（结构边直接入图不入队，由 graph-build 从 related 派生）
  - **不确定时一律降级 AMBIGUOUS，绝不拔高**（守 C1 不脑补）
- **(d) reasoning（写入 source_location，守 C1 来源铁律）**：一句话说明「凭什么推断这条关系」（≤40 字）。

**裁决纪律**：

1. **逐对独立判断**（仿 C7 逐条精神），不批量拍脑袋。
2. **宁可判 AMBIGUOUS 或丢弃，绝不为凑数拔高到 INFERRED**——下游 edge-review 对 AMBIGUOUS 禁 approve，错判 INFERRED 会污染可 approve 池。
3. `--dry-run`：仅输出 AI 裁决结果表（候选对 / relation / confidence / reasoning），**不入队**（仿 edge-review `--dry-run`）。

### 入队前完整三检查

对每条通过 AI 裁决 (a) 的候选 `(source, target, relation)`，入队前**逐项复用 Phase 3 入队幂等三检查**（`pending-edges-rules.md` §入队幂等三检查）：

1. 三元组已在 `graph.json.links`（已是权威边）→ **跳过**。
2. 三元组已在 `pending[]`（未消费）→ **跳过**（幂等，不重复入队）。
3. 三元组在 `reviewed_history` 且 `decision=reject`（曾被拒）→ **跳过**（不反复推同一被拒边）。

幂等键 = `(source, target, relation)` 三元组（与 id 生成的 sha1 输入一致，天然一致）。

> **③reject 是脚本未做的层**：prefilter 已做①②（信任 graph.json，`G.has_edge` 双向查），但**队列归 AI 管，AI 入队前必做完整三检查、尤其③**——脚本不读 `.pending-edges.yaml`，若 AI 遗漏③会反复推被拒边、淹没 edge-review 队列。

### 入队字段填充表

入队 = 直接 append `.pending-edges.yaml` 的 `pending[]` 一条（**无需新建入队 helper**，与 Phase 3 手造 `proposed_by: manual` 同一 append 动作，仅 `proposed_by: discover` + source_location 用相似度/语义格式）。每条 append 填全 11 字段（`pending-edges-rules.md` §入队字段要求 + §Phase 7 生成器接口预留）：

| 字段 | discover 填法 |
|------|--------------|
| `id` | `pe-{YYYYMMDDHHmmss}-{sha1(source+"→"+target+"\|"+relation)[:4]}` |
| `source` | slug（与 graph.json node id 对齐），AI 定方向起点 |
| `target` | slug，方向终点 |
| `relation` | AI 推断（`references`/`depends_on`/`derived_from`/`term_of`），拿不准退 `references` |
| `confidence` | `INFERRED` \| `AMBIGUOUS`（**绝不 EXTRACTED**） |
| `source_location` | `"similarity:{a}↔{b}:{score}"`（Jaccard 候选，score=prefilter `signal`）或 `"semantic:{a}↔{b}:{reasoning}"`（AI 裁决依据），**非空守 C1** |
| `proposed_at` | ISO 8601 入队时间 |
| `proposed_by` | **`discover`** |
| `reviewed` | `false` |
| `reviewed_at` | `null` |
| `reviewed_by` | `null` |
| `decision` | `null` |

### 入队 SSOT 守卫

discover 入队**只 append `pending[]`**（`pending-edges-rules.md` §入队 SSOT 守卫 + §与 graph.json 的隔离）：

- **绝不碰 `reviewed_history[]`**——那是 edge-review 的领地。
- **绝不修改 graph.json**——候选是 INFERRED/AMBIGUOUS，永不进 `links`（`links` 只放权威边）。
- **绝不修改任何 L0 文档**——approve 后由 edge-review 写回源文档 `related` 补 `[[target]]`，discover 阶段文档保持不变。
- **不触发 graph-build**——提示驱动（仿 approve 后不自动 build）。pending 是「建议暂存」非真理源；`.pending-edges.yaml` 已在 graph-build 的 `ROOT_FILE_BLACKLIST`，队列与引擎物理隔离。

### C6 操作日志

复用既有 `write_c6_log` 通道，layer 标 `discover`（区别于 graph-build/graph-analyze），detail 记 `candidates_found` / `enqueued` / `inferred` / `ambiguous` / `top_n` / `source_hash` + **丢弃计数 `discarded`** + **跳过计数 `skipped`**（三检查命中），保证「凭什么入了这批边」可追溯（守 C6，仿 edge-review reject 也写日志）。日志行示例（仿 `pending-edges-rules.md` §C6 日志格式 + `graph_analyze.py` write_c6_log）：

```markdown
## [2026-06-16T15:05:00+08:00] @alice | health | discover
  detail: {"candidates_found": 9, "enqueued": 4, "inferred": 3, "ambiguous": 1, "discarded": 3, "skipped": 2, "top_n": 20, "source_hash": "sha256:ab12…"}
```

### 输出摘要

```
🔍 涌现发现（health discover · 非实时 · 不进 in/ask 热路径）

候选：9 个（高信号 3 | 中信号 6，source_hash sha256:ab12…）
AI 裁决：入队 4（INFERRED 3 | AMBIGUOUS 1）· 丢弃 3（不相关）· 跳过 2（三检查命中）

  ✅ INFERRED: print-timeout → fallback-strategy
       relation: references | semantic:print-timeout↔fallback-strategy:超时回退同一链路
  ⚠️ AMBIGUOUS: order-table → delivery-config
       relation: references | similarity:order-table↔delivery-config:0.32

提示：运行 health edge-review 逐条人审这批候选（AMBIGUOUS 禁 approve，仅 reject/skip）
```

> `--dry-run` 时只展示上方 AI 裁决结果表（候选对 / relation / confidence / reasoning），**不 append pending[]、不写 C6 日志**。

---

## graph export [Phase 9 新增]（可视化导出：知识网络静态 HTML / Obsidian Canvas / GraphML）

> 读 `graph.json`（+ 可选 `communities.json`）→ 按标志生成 1~3 个可视化产物到 `.graph/exports/`，供浏览器 / Obsidian / Gephi 直接打开。**只读派生，唯一写路径 = `.graph/exports/`，绝不回填/不碰文档/不重算社区**（单向派生铁律，D-10）。**仅显式 `graph export` 触发，绝不进 health 综合报告 11 步**（守非实时 + 基线快照，与 Phase 6/7/8 同纪律）。完整实现见 `references/scripts/graph_export.py`，本节为入口摘要。
>
> **命令前缀**：顶层 `graph export`（R1 裁定）。AI 可经 health 路由调同一 `graph_export.py`；与 `health graph-build`/`health graph` 同风格，指向唯一引擎。

### 用法

```bash
/knowledge-wiki graph export            # 默认导出 HTML（Cytoscape.js 静态交互图）
/knowledge-wiki graph export --html     # 显式 HTML
/knowledge-wiki graph export --canvas   # Obsidian Canvas (.canvas JSON)
/knowledge-wiki graph export --graphml  # GraphML（Gephi/yEd）
/knowledge-wiki graph export --html --canvas --graphml  # 三格式同时导出（D-09 可组合）
/knowledge-wiki graph export --include-inferred         # 叠加推断边（⚠️ 未经人审，仅可选查看）
```

### 行为

1. 读 `.graph/graph.json`（不存在/损坏则降级，见降级表）。
2. 可选读 `.graph/communities.json`（缺失则着色降级为 status/type，不报错）。
3. 可选读 `.knowledge/.pending-edges.yaml`（仅 `--include-inferred` 时，**只读**，解析 INFERRED/AMBIGUOUS 推断边注入视图）。
4. 按 `--html/--canvas/--graphml` 标志路由渲染函数（可组合，默认 `--html`）。
5. 原子写产物到 `.graph/exports/`（`mkdir exist_ok=True`，首次运行自动建目录）。
6. 追加 C6 操作日志到 `.logs/personal/{user-id}.md`（layer 标 `graph-export`）。
7. 输出摘要骨架（见下）。

### 调用方式

AI 通过 `run_terminal_cmd` 执行（脚本由 `init` 复制到 `.knowledge/.graph/scripts/`，见 `references/directory-structure.md`）：

```bash
uv run .knowledge/.graph/scripts/graph_export.py --kb-root .knowledge [--html] [--canvas] [--graphml] [--include-inferred] [--json]
```

> 退出码：0 成功（含着色降级/超限警告）/ 1 kb-root 或 graph.json 不存在或损坏 / 2 `.export.lock` 存在（并发）。首次 `uv run` 自动拉起隔离环境装 networkx==3.6.1，不污染全局；删 `.graph/` 即彻底回退（含 `exports/` 零残留）。

### 报告渲染骨架（AI 据摘要 JSON 渲染）

```
🎨 知识网络可视化导出

源图：48 节点 / 36 边（source_hash sha256:ab12…）
产物：
  · graph.html    （Cytoscape 交互图，浏览器打开 .graph/exports/graph.html）
  · graph.canvas  （Obsidian Canvas，48 节点 5 社区分组）
  · graph.graphml （Gephi/yEd，节点/边带 status/confidence/community 属性）
着色：默认 community（HTML 内可切 status/type）｜边线型：实线=EXTRACTED / 虚线=INFERRED / 点线=AMBIGUOUS⚠️
来源：源自 graph.json 派生·非文档原文·非真理源·生成时间 {ts}   ← D-16 页脚措辞
```

### 降级（凭 graph_export.py 退出码，不自造判定）

| 场景 | 行为 | 退出码 |
|---|---|---|
| graph_export.py 不存在（删 .graph/ / Phase 9 未启用） | 「可视化导出未启用（Phase 9）；如需先 `health graph-build`」静默优雅退出 | 0 |
| graph.json 不存在（未 graph-build / 删 .graph/） | 「未编译图谱，请先运行 `health graph-build`」 | 1 |
| graph.json 损坏 | 「图谱损坏，建议重建 `health graph-build`」 | 1 |
| communities.json 不存在（未 health graph） | 仍导出，**着色降级**为 status/type（community 全 null），不报错 | 0 |
| 节点 ≥2000（D-13） | 警告超限 + 建议 Canvas/GraphML（HTML 跳过），Canvas/GraphML 仍导出 | 0 |
| `.export.lock` 存在（并发） | 「可视化导出正在进行中」 | 2 |

### 渲染措辞铁律（守 C1，仿 §graph）

1. 页脚必含「源自 graph.json 派生·非文档原文·非真理源」（D-16）；生成时间透传 graph.json `generated_at`（非 export 时 wall-clock）。
2. AMBIGUOUS/未审边点线+警示色+「?未审」视觉，**不等同权威边**（D-14）。
3. 边 hover 显 `source_location`（守 C1 来源铁律）；Canvas/GraphML 治理基因跨格式不丢（D-17）。
4. HTML 图层勾选开关（推断边 checkbox）默认隐藏推断边视图——保持默认视图干净（D-06）。

### 触发时机 + 不进综合报告

- **手动执行**（`graph export [标志]`）。
- **Phase 9 不进 health 综合报告**：综合报告 11 步流程一字不改；`graph export` 是独立只读导出子命令，每次 health 都跑会产生不必要写操作 + 违反基线快照。综合报告最多加「可视化：运行 graph export」提示（本期保守不加）。

### C6 操作日志

复用既有 `write_c6_log` 通道，layer 标 **`graph-export`**（区别于 graph-build/graph-analyze/graph-explore/discover），detail 记 `formats`（导出了哪几格式）/ `node_count` / `edge_count` / `include_inferred` / `source_hash` / `oversized`（是否超阈值）。