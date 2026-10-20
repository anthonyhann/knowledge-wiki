# 可信度分级与人审闭环规则（trust-rules）

> **本文件是 confidence 三级分级 + reviewed 人审闭环的唯一权威源。**
>
> 与 `graph-model.md`（边数据形状）、`pending-edges-rules.md`（队列结构）互补：本文件定义**治理语义与人审铁律**。
>
> 核心命题：结构边走权威直通车，推断边走 pending 人审闸门，AMBIGUOUS 边永不作硬结论。

---

## confidence 三级模型

### 边来源 × confidence × reviewed 处理表

| 边来源 | confidence | reviewed（默认） | 落点 | 入权威遍历？ | Phase 3 从哪来 |
|--------|-----------|:---:|------|:---:|------|
| **人工 `[[slug]]`**（frontmatter related） | `EXTRACTED` | `true` | graph.json `links` | ✅ 是 | Phase 2 已产，Phase 3 不变 |
| **相似度涌现推荐** | `INFERRED` | `false` | `.pending-edges.yaml` | ❌ 否（须人审升级） | 手造/注入入队（生成器留 Phase 7） |
| **跨文档语义推断** | `AMBIGUOUS` | `false` | `.pending-edges.yaml` | ❌ **永不作硬结论**（守 C1） | 手造/注入入队（生成器留 Phase 7） |

### 三级本质区分表

| 维度 | EXTRACTED | INFERRED | AMBIGUOUS |
|------|-----------|----------|-----------|
| **本质** | 确定性抽取（人写或机械结构派生） | 算法推荐（相似度高，"可能相关"） | 语义推断（跨文档，"或有关联"） |
| **来源信号** | frontmatter `[[slug]]` 物理存在 | 相似度分数 ≥ 阈值（Phase 7 算） | LLM 语义判断（Phase 7 算） |
| **确定性** | 同输入同输出，可复现 | 算法可复现但语义需人确认 | **不确定，必须人确认** |
| **能否作结论** | 是（权威） | 人审后是 | **永远不能作硬结论**（仅提示） |

### 三级 source_location 语义差异表

| confidence | source_location 形态 | 示例 |
|-----------|---------------------|------|
| `EXTRACTED` | 行级/字段级（Phase 2 已定，冒号分隔） | `.knowledge/ops/print-timeout.md:18` 或 `...:frontmatter:related` |
| `INFERRED` | **来源对 + 算法依据**（pending 队列条目里记，不在 graph.json） | `similarity:ops/a.md↔ops/b.md:0.83`（Phase 7 生成器填） |
| `AMBIGUOUS` | **来源对 + 推断依据**（pending 队列条目里记） | `semantic:design/x.md↔flows/y.md:跨文档语义`（Phase 7 生成器填） |

**Phase 3 无生成器时**：手造/注入边的 `source_location` 统一用 `manual:<说明>` 标注人工注入来源——**仍非空、仍守 C1**。生成器（相似度/语义依据）是 Phase 7。

---

## reviewed 人审状态机

### 状态机（单向 false → true）

```
                  人审 approve（health edge-review）
   reviewed=false ──────────────────────────────────► reviewed=true
   （pending 队列里的推断边）  写回文档 frontmatter        （下次 graph-build 派生为 EXTRACTED 权威边）
        │                     related 补 [[slug]]
        │  人审 reject
        ▼
   从 pending 移入 reviewed_history（decision=reject，不入图）
```

### 三条铁律

1. **单向不可逆**：`reviewed` 只能 `false → true`，不可逆。撤销 = 删该边的文档 frontmatter `[[slug]]` 再重建，不存在 `true → false`。
2. **无批量升级**：升级唯一路径 = `health edge-review` 单条人审 approve。**禁止 `--auto-approve` 类批量开关**（SC#2 明确禁止，never）。
3. **升级动作守 SSOT**：approve 的落地不是"把 pending 边标 reviewed=true 塞进 graph.json"，而是**写回源文档 frontmatter `related` 补 `[[slug]]`**，再 graph-build 派生为 EXTRACTED 边（见下方 §SSOT 写回机制）。

### 什么边默认 reviewed=false vs 恒 true

| 边类型 | reviewed 默认 | 依据 |
|--------|:---:|------|
| **结构边**（人工 `[[slug]]`，EXTRACTED） | **恒 `true`** | 直接来自人写 frontmatter，本身即"人已声明"，无需再审（Phase 2 已定，Phase 3 不变） |
| **INFERRED 边**（相似度推荐） | **`false`** | 机器推荐，须人确认"这关系是否成立" |
| **AMBIGUOUS 边**（语义推断） | **`false`** | 机器猜测，须人确认且**即便审过也永不作硬结论**（见 §AMBIGUOUS 遍历护栏） |

> **为什么结构边恒 reviewed=true 不算"绕过人审"**：结构边的"人审"发生在**录入文档时**——作者/AI 在 frontmatter 写 `[[slug]]` 这个动作本身就是人的声明（C7 逐条问询 + draft→audit 已守过一道）。Phase 3 的 edge-review 人审针对的是**机器产的 INFERRED/AMBIGUOUS 边**。

---

## 权威边谓词（Phase 4/5 遍历消费，Phase 3 定义）

**权威边谓词（authoritative edge predicate）**——Phase 3 定义的核心契约：

```
is_authoritative(edge) := edge.confidence == "EXTRACTED" && edge.reviewed == true
```

### 边状态 × is_authoritative × 遍历行为

| 边状态 | confidence | reviewed | is_authoritative | 遍历行为（Phase 4 实现，Phase 3 声明） |
|--------|-----------|:---:|:---:|------|
| 结构边 | EXTRACTED | true | ✅ | 默认遍历，作结论 |
| 已审推断边（已回流为结构边） | EXTRACTED | true | ✅ | 默认遍历（它已是结构边了） |
| 未审 INFERRED | INFERRED | false | ❌ | 默认排除；`--include-inferred` 显式开启 + 标「未审·INFERRED」 |
| 未审 AMBIGUOUS | AMBIGUOUS | false | ❌ | **永不进硬路径**（即便 `--include-inferred` 也只作"线索"提示） |

> Phase 3 **定义谓词 + 在规则文档声明**，但**不实现遍历器**（Phase 4）。因为 graph.json `links` 里**只有 EXTRACTED && reviewed=true 的边**（`graph-model.md` §3.4 架构决策），所以谓词在 Phase 3 阶段对 graph.json 永真——它真正发挥过滤作用是在 Phase 4 引入 `--include-inferred` 把 pending 边临时叠加进遍历时。

---

## SSOT 写回机制（approve 落地路径，核心 D1）

### 张力的本质

人审 approve 后，"这条边被认可了"这个结论必须存在某处。三个候选存储位置对比：

| 候选 | 人审结果存哪 | 是否引入第二真理源 | 守 SSOT |
|------|-------------|:---:|:---:|
| **① 写回文档 frontmatter（锁定）** | 源文档 `related` 补 `[[slug]]` | **否**——结论回到文档 SSOT，graph 仍是纯派生 | ✅ |
| ② 写 `.pending-edges.yaml` 标 reviewed=true | pending 队列条目 reviewed 字段 | **是**——"哪些边审过"成了独立于文档的真理 | ❌ |
| ③ 直接 patch graph.json 标 reviewed=true | graph.json links | **是**——图被直接编辑，违反"无 mutate 接口" | ❌❌ |

### 锁定方案 ①：写回源文档 frontmatter related

**approve 的落地动作 = 在源文档 frontmatter `related` 补 `[[target-slug]]`**（复用 backlink-consume 的"安全追加 related"写文件逻辑 + 上限 15 裁剪），再提示/触发 graph-build 重新派生为 EXTRACTED 边。

### 完整闭环 6 步

```
1. 人 approve pending 边 (source=A, target=B, relation=references)
2. edge-review 在 A 的源文档 frontmatter related 追加 [[B]]
   （复用 backlink-consume 的"安全追加 related"写文件逻辑 + 上限 15 裁剪）
3. 将该 pending 条目标 decision=approve / reviewed=true / reviewed_at / reviewed_by，
   移入 reviewed_history（队列里它已完成使命）
4. 写 C6 操作日志（见 §C6 操作日志）
5. 提示：「已写回 A.md 的 related，运行 health graph-build --incremental 派生为权威边」
   （提示驱动，不自动跑 graph-build——守"录入/审阅不自动触发重算"+ 与 Phase 2 Step 11 一致）
6. 下次 graph-build：collect_edges 从 A 的 related 读到 [[B]] →
   派生出 EXTRACTED + reviewed=true 边 A→B，进 graph.json links
```

### 四点论证（方案 ① 为什么是唯一守 SSOT 的解）

1. **图永远是文档的纯函数派生物**——approve 后 graph.json 里出现 A→B 边，是因为**文档 A 的 related 现在真的有 [[B]] 了**（不是因为 pending 队列说审过了）。
2. **单一真理源**——"这条关系成立"这个事实只存在文档 frontmatter 一处。pending 队列的 `reviewed=true` 只是"流程已走完"的审计标记，不是"边是否权威"的真理（真理在文档）。
3. **与 Phase 7 设计完全一致**——ROADMAP Phase 7 SC#2：「reviewed=true 后提示人工在 L0 对应文档补 `[[slug]]`，下次 graph-build 派生为 EXTRACTED 权威边」。Phase 3 先把这条路径在少量边上跑通。
4. **推断边"升级"的本质是"转化为结构边"**——approve 不是"让 INFERRED 边变权威"，而是"人认可后，把它转写成一条真正的结构边"。升级后它在 graph.json 里的 confidence 是 **EXTRACTED**（因为它现在来自 frontmatter `[[slug]]`），不是"reviewed=true 的 INFERRED"——**graph.json 里永远不存在 reviewed=true 的 INFERRED 边**。

### approve 后不自动 graph-build（提示驱动）

approve 后提示用户：「已写回 N 篇文档 related，建议运行 `health graph-build --incremental` 派生权威边」。不自动跑——守"录入/审阅不自动触发重算"（与 Phase 2 Step 11 staleness 提示一致）。

### 增量重建天然免疫覆盖人审

因为人审结果存文档而非存图，graph.json 可被任意次重建覆盖而不丢任何人审信息——人审信息全在文档 frontmatter 里，重建只是忠实地从文档重新派生。**如果当初选了方案 ②③（人审结果存 pending/graph），就会有"重建覆盖人审"的真实风险**——这反过来佐证了方案 ① 的正确性。

---

## AMBIGUOUS 遍历护栏（TRUST-04，核心 D6）

### 三层落地

| 层 | Phase 3 能落地的部分 | 备注 |
|----|---------------------|------|
| **数据层** | 推断边带 `confidence=AMBIGUOUS` 标记（pending 队列条目里） | Phase 3 手造验证 |
| **规则层** | 本文件声明遍历谓词：**AMBIGUOUS 边永不进硬路径** | Phase 3 写规则声明 |
| **遍历层** | Phase 4/5 ask graph/path 实现：默认排除 AMBIGUOUS | Phase 4/5 实现，Phase 3 不实现 |

### AMBIGUOUS 的特殊性

INFERRED 边 approve → 回写文档 `[[slug]]` → 派生为 EXTRACTED 权威边（它本就是"可能相关"，人认可后就是确定关系）。

**但 AMBIGUOUS 边 approve 的语义不同**——AMBIGUOUS 是"跨文档语义推断，本质不确定"，approve 只表示"承认有这条线索"，**不应升级为可作硬结论的 EXTRACTED 边**。

### 机制级硬约束（D6）

**Phase 3 阶段 AMBIGUOUS 边在 `health edge-review` 里只支持 reject 或 skip，不可 approve。**

尝试 approve 时强制提示：

> 「AMBIGUOUS 边不能直接 approve 为权威边；若你确认这是某种明确关系，请在文档里手写对应 `[[slug]]` 并指明关系。」

这把"AMBIGUOUS 永不作硬结论"做成**机制级硬约束**而非措辞约束——比 Phase 4 渲染层更早守住 C1。

---

## C6 操作日志（人审留痕，SC#3）

人审升级**必须**写 C6 操作日志（复用 `log-rules.md` 通道，不另起，action=`edge-review`），仿 backlink-consume 日志格式：

### 日志样例

```markdown
## [2026-06-11T15:05:00+08:00] @alice | edge-review | 批量人审
  detail: {"reviewed": 3, "approved": 2, "rejected": 1, "approved_edges": ["ops/print-timeout→flows/fallback-strategy (INFERRED→EXTRACTED)", "design/x→flows/y (INFERRED→EXTRACTED)"], "docs_updated": ["ops/print-timeout.md", "design/x.md"]}
```

### 审计字段

- **谁** = `@{user-id}`（log 行首，复用 `resolve_user_id`）
- **何时** = ISO 8601 时间戳
- **哪条边** = `source→target (confidence)` + `false→true`（reviewed 状态迁移）
- **落地** = `docs_updated`（写回了哪篇文档的 related）

reject 也写日志（detail 含 `rejected` 计数），保证"否决"也可追溯。

---

## 边界声明

本文件**不定义**：

- ❌ `health edge-review` 命令的脚本/交互实现（属 03-02 + `health-rules.md`）
- ❌ `.pending-edges.yaml` 完整 schema（属 `pending-edges-rules.md`）
- ❌ 遍历器/渲染分级措辞（Phase 4/5）
- ❌ 相似度/语义生成器（Phase 7 `health discover`）
- ❌ `--auto-approve` 任何路径（**never**——机制级禁止）
