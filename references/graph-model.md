# graph.json schema 契约（graph-model.md）

> **本文件是 `.knowledge/.graph/graph.json` 的唯一 schema 权威源**。定义「数据长什么样」——顶层元信息字段、节点 schema、边 schema 与全部硬不变量。
>
> 与 `graph-build-rules.md` 互补：本文件定义**数据形状**（model），后者定义**引擎行为**（怎么编译/锁/原子写/回退）。两者一字段一职责，不交叉。
>
> 图是文档 SSOT 的纯函数派生物：`graph = compile(documents)`。本 schema 描述派生产物的结构，**不描述派生算法**（算法属 `graph-build-rules.md` 与 01-02 的 `graph_build.py`）。
>
> 字段权威来源：Phase 1 Research `01-RESEARCH.md` §2 决策 1（完整 jsonc schema）、§4.2（frontmatter 字段映射）、§4.3（glossary 方案 A）、§4.4（档位 1）。

---

## 0. 设计总览

`graph.json` 采用 **node-link JSON** 格式，键名为 `nodes` / `links`，直接对齐 `networkx.node_link_data()` / `node_link_graph()` 的默认 schema（见 §6）。一个文件即一张完整图，可被 `nx.node_link_graph(json.load(f), edges="links")` 一行加载回内存。

schema **一次性预留全 9 阶段所需字段**，Phase 1 只填其中的地基子集，后续阶段（Phase 2 建边、Phase 3 confidence 升级、Phase 6 中心度/社区）只**填值不改结构**（呼应 PITFALLS Pitfall 6「schema 预留分层」）。

整体形状（jsonc 示例，仅展示字段形状，**不含引擎逻辑**）：

```jsonc
{
  // ── 顶层元信息（见 §1）──
  "schema_version": "1.0",
  "generated_at": "2026-06-10T15:00:00+08:00",
  "generator": "knowledge-wiki/graph-build@1.0",
  "source_hash": "sha256:ab12...",
  "doc_count": 47,
  "node_count": 48,
  "edge_count": 0,                            // Phase 1 恒 0（档位 1）
  "build_mode": "full",                       // Phase 1 恒 full

  // ── 节点（见 §2）──
  "nodes": [
    {
      "id": "print-timeout",                  // ★ slug，全图唯一主键
      "type": "ops",                          // ★ 9 类 type 之一
      "status": "active",                     // ★ canonical|active|draft|deprecated
      "expires": "2026-08-19",                // ★ 日期 或 "never"
      "title": "打印服务超时机制",
      "path": ".knowledge/ops/print-timeout.md",
      "node_kind": "document",                // document | glossary_term
      "source_mtime": 1718000000,
      "centrality": null,                     // Phase 6 回填，Phase 1 写 null
      "community": null                       // Phase 6 回填，Phase 1 写 null
    }
  ],

  // ── 边（见 §3）——Phase 1 采档位 1，links 恒为空数组 ──
  "links": []
}
```

---

## 1. 顶层元信息字段

graph.json 顶层 8 个元信息字段，全部必填非空。

| 字段 | 类型 | Phase 1 取值 | 语义 |
|------|------|-------------|------|
| `schema_version` | string | `"1.0"` | 语义化版本号。schema 结构演进时 bump（如新增字段语义不兼容时）。加载方据此判断兼容性 |
| `generated_at` | string | ISO 8601 带时区，如 `"2026-06-10T15:00:00+08:00"` | 本次编译完成时间戳。带时区，便于跨机器 diff 与 staleness 判断 |
| `generator` | string | `"knowledge-wiki/graph-build@1.0"` | 生成器标识 + 版本。区分人工编辑（禁止）与引擎派生（唯一合法来源） |
| `source_hash` | string | `"sha256:<hex>"` | `.knowledge/` 文档集指纹（算法见 `graph-build-rules.md` §source_hash）。供 Phase 2 增量重建 / staleness 判断。Phase 1 仅计算并存储，不消费 |
| `doc_count` | int | 编译时扫到的文档数 | **仅 `node_kind==document` 的节点数**（glossary_term 不计入 doc_count） |
| `node_count` | int | **node_count == 源 .md 文件数** | **源 .md 文件数**（业务目录下所有 .md，含 glossary_term 与 document）。存在 glossary_term 时 `node_count > doc_count` |
| `edge_count` | int | **恒 0**（Phase 1 档位 1） | 边总数。Phase 1 为 0；Phase 2 建边后为实际边数。GRAPH-03 摘要的「边数」字段来源 |
| `build_mode` | string | **恒 `"full"`**（Phase 1 只全量） | `full` \| `incremental`。Phase 1 只做全量编译；增量推迟到 Phase 2（GRAPH-04） |

> **取值锁定**：Phase 1 `edge_count` 恒 0、`build_mode` 恒 `"full"`、`schema_version` 恒 `"1.0"`。这三项是 Phase 1 的不可变量（见 §7）。

---

## 2. 节点 schema 字段

节点位于顶层 `nodes` 数组。每个节点 10 个字段，分三组：① 4 个治理字段（必填非空，GRAPH-02 验收点）；② 4 个辅助字段；③ 2 个后续阶段预留字段（Phase 1 写 `null`）。

### 2.1 治理字段（必填非空，GRAPH-02 验收点）

| 字段 | 类型 | 取值 | 说明 |
|------|------|------|------|
| `id` | string | slug | **★ 全图唯一主键**。恒为 slug = 文档 basename 去 `.md`，与既有 `.index/` 的 idx `slug` 列同源（见 `index-rules.md`「idx 条目格式」slug 列）。不会缺失 |
| `type` | string | 9 类之一：`glossary` \| `architecture` \| `solution` \| `adr` \| `requirement` \| `flow` \| `api` \| `db` \| `ops` \| `synthesis` | **★ 必填非空**。来源 frontmatter `type:`；缺失时按目录推断（见 §4），**仍不得为空** |
| `status` | string | `canonical` > `active` > `draft` > `deprecated`（检索优先级降序） | **★ 必填非空**。来源 frontmatter `status:`；缺失时默认 `draft`（守 C3，草稿优先，**不擅自升级**） |
| `expires` | string | 日期（如 `"2026-08-19"`）或字符串 `"never"` | **★ 必填非空**。来源 frontmatter `expires:`；缺失时默认 `"never"`（保守，不让 build 失败） |

> 「必填非空」的硬约束：上述 4 个字段任一为空或缺失即视为节点非法。引擎层通过「缺失降级填默认值」保证它们永远非空（见 §4），故 graph.json 落盘后 4 字段恒非空——这是 GRAPH-02 的核心验收点。

### 2.2 辅助字段

| 字段 | 类型 | 取值 | 说明 |
|------|------|------|------|
| `title` | string | 文档标题 | 来源 frontmatter `title:`；缺失时用 `id`（slug）占位。便于 diff 可读与后续渲染，**非主键** |
| `path` | string | 相对仓库根的 `.md` 路径，如 `.knowledge/ops/print-timeout.md` | 回源定位（守 C1 来源精神，每个节点可溯源到源文档）。不会缺失 |
| `node_kind` | string | `document` \| `glossary_term`（取值集见 §5） | 区分普通文档节点与术语节点。方案 A 下 `glossary/` 目录文档标 `glossary_term`，其余标 `document` |
| `source_mtime` | int | 源文档文件系统 mtime（Unix 时间戳） | 预留增量判断（Phase 2 用）。不会缺失 |

### 2.3 后续阶段预留字段（Phase 1 写 `null`）

| 字段 | 类型 | Phase 1 取值 | 由哪个 Phase 填充 |
|------|------|-------------|------------------|
| `centrality` | float \| null | **`null`** | **Phase 6**（ANALYZE-*）回填中心度（betweenness / pagerank） |
| `community` | int/string \| null | **`null`** | **Phase 6**（ANALYZE-*）回填社区检测（Louvain）结果 |

> 这两个字段 Phase 1 **预留但不赋有效值**，固定写 `null`，避免 Phase 6 回头改 schema（PITFALLS Pitfall 6）。

---

## 3. 边 schema 字段（Phase 1 采档位 1：links 为空数组）

### 3.1 档位决策（锁定）

**Phase 1 锁定档位 1（最小）：`links` 恒为空数组 `[]`，不建任何真边。**（来源 `01-RESEARCH.md` §4.4）

理由：
1. **REQ 归属清晰**——真正建边（relation 分类 + source_location 必填 + 单向派生 lint）全部挂 **Phase 2（EDGE-01/02/03）**，塞进 Phase 1 是 scope 越界。
2. **source_location 铁律风险**——边级 schema 强制 source_location 非空、缺失即拒绝入图（PITFALLS Pitfall 3），这套校验属 Phase 2 硬验收。Phase 1 草率建边却不强制校验 = 先污染再补救。
3. **地基价值是 schema 稳定**——只要 `links` 字段与边的 6 个属性在 schema 里预留好，Phase 2 填充即可，无需改 schema。

> 档位 2（派生 `related` → references 骨架边）已评估并**推迟**：好处是 Phase 2 有真实数据回归，坏处是把部分 Phase 2 工作前移且需提前实现 source_location 校验。Phase 1 取极简稳固路线，把建边完整留给 Phase 2 一次做对。

**Phase 2 解锁：links 产出结构派生真边。** Phase 2 从每篇文档 frontmatter `related` 的 `[[slug]]` 派生有向边，**纯结构推定、无 AI 语义推理、无 confidence 分级**（分级是 Phase 3）。边的 relation 由 `infer_relation(source_node, target_node)` 纯函数机械决定（映射表见 §3.3），每条边强制携带 `source_location`（行级优先降级字段级，见 §3.5）。Phase 2 产出的全部边恒 `confidence="EXTRACTED"` + `reviewed=true`（结构边=人写 frontmatter 声明，非机器推断）。

**Phase 3 解锁：confidence 三级分级成立 + reviewed 人审闭环。** Phase 3 让 confidence 三级（EXTRACTED / INFERRED / AMBIGUOUS）与 reviewed 人审**机制成立**，但**结构边仍恒 `confidence="EXTRACTED"` + `reviewed=true`**（Phase 2 行为不变——这是三级中的第一级，本就该恒值）。

- **推断边双通道**：INFERRED（相似度推荐）/ AMBIGUOUS（语义推断）边默认 `reviewed=false`，**只存在于 `.knowledge/.pending-edges.yaml` 队列，绝不进 graph.json `links`**（详见 §3.4 权威边谓词与架构决策 + `trust-rules.md` / `pending-edges-rules.md`）。
- **关键澄清**：graph.json 的 `confidence` 字段在 Phase 3 仍只会出现 `EXTRACTED`——**分级体现在「边在哪个文件 + 走哪条通道」，而非「graph.json 里 confidence 字段的多样性」**（推断边在 pending 队列不在 links）。
- **生成器留 Phase 7**：往队列灌候选边的生成器（`health discover`）是 Phase 7 交付；Phase 3 用手造/注入边验证闭环（不在本 schema 范围）。

### 3.2 边字段定义（一次预留 6 字段，Phase 2/3 填充）

虽然 Phase 1 `links: []` 不产出任何边，但 schema **一次性预留**边的 6 个字段。Phase 2/3 据此填充，**不改结构**。

| 字段 | 类型 | 取值集 / 形状 | 由哪个 Phase 填充 |
|------|------|--------------|------------------|
| `source` | string | 端点 = 某节点 `id` | **Phase 2**（建边时产出） |
| `target` | string | 端点 = 某节点 `id` | **Phase 2**（建边时产出） |
| `relation` | string | `references` \| `depends_on` \| `derived_from` \| `conflicts_with` \| `term_of` \| `ast_calls` \| `ast_imports` | **Phase 2**（relation 分类）；`ast_*` 取值留给 v2+ AST 边 |
| `confidence` | string | `EXTRACTED` \| `INFERRED` \| `AMBIGUOUS` | **Phase 3** 定义三级语义；**graph.json links 里恒 `EXTRACTED`**（推断边在 `.pending-edges.yaml`） |
| `source_location` | string | 回源定位，如 `.knowledge/ops/print-timeout.md:frontmatter:related` | **Phase 2**（强制非空，缺失即拒绝入图——守 C1 来源铁律） |
| `reviewed` | bool | `true` \| `false` | **Phase 3** 定义人审状态机；**graph.json links 里恒 `true`**（权威边谓词） |

边字段形状示例（jsonc，**仅展示字段形状，Phase 1 不产出此类边**）：

```jsonc
// Phase 2+ 填充后的单条边形状（Phase 1 的 links 数组恒为空）
{
  "source": "print-timeout",
  "target": "fallback-strategy",
  "relation": "references",                                          // Phase 2 填
  "confidence": "EXTRACTED",                                         // Phase 3 填
  "source_location": ".knowledge/ops/print-timeout.md:frontmatter:related",  // Phase 2 填，强制非空
  "reviewed": true                                                   // Phase 3 填
}
```

### 3.3 relation 结构推定映射表（Phase 2，纯结构、无 AI）

relation 由 **source 文档的 `type` + target 节点的 `node_kind`** 机械决定，零语义推理。判定按优先级从上到下，**命中即停**：

| 优先级 | 条件（source.type / target） | relation | 方向语义 | 依据 |
|:---:|------|------|------|------|
| 1 | **target 节点 `node_kind == "glossary_term"`**（边指向 glossary/ 术语） | `term_of` | `A → 术语T`：A 使用/从属于术语 T | 术语是被引用的锚点（`ingestion-rules.md` Step 2.7 黄金原则） |
| 2 | **source.type == "glossary"**（术语文档主动引用他者） | `references` | `术语T → X`：术语顺带引用 X（非定义关系） | 术语指向非术语时无「依赖/派生」语义 |
| 3 | **source.type ∈ {architecture, solution, adr}**（design/ 目录三类） | `derived_from` | `设计D → X`：设计派生/依据于 X | design 类文档对他者的引用本质是「派生/参考」 |
| 4 | **source.type == "requirement"** | `depends_on` | `需求R → X`：需求依赖 X 实现/澄清 | requirements 引用的文档是其依赖 |
| 5 | **source.type == "synthesis"** | `derived_from` | `综合S → X`：S 由来源文档综合派生 | synthesis 的 `derived_from` frontmatter 本就是「派生自」语义 |
| 6 | 其余一切（flow / api / db / ops / case） | `references` | `X → Y`：一般引用 | 兜底，无特殊语义 |

映射表铁律：

1. **命中即停**——按优先级从上到下匹配，首个命中的行即为该边的 relation，不继续往下。
2. **优先级 1（term_of）> 优先级 5（derived_from）**——synthesis 引用 glossary 术语时判 `term_of`（指向术语锚点更精确稳定，符合「术语唯一锚点」不变量）。
3. **`infer_relation(source_node, target_node)` 纯函数**——不读文件、不调 AI、同输入恒同输出（守 PITFALLS Pitfall 4 确定性）。
4. **Phase 2 产出集**：`references` | `depends_on` | `derived_from` | `term_of`。`conflicts_with` 与 `ast_*` 为 schema 合法取值但 Phase 2 **不产出**（conflicts_with 无确定性结构来源；ast_* 待 v2+ AST 边）。

### 3.4 有向性 + 去重 + 悬空/自引用 + confidence/reviewed（Phase 2）

**有向性**：`A.related` 含 `[[B]]` ⟹ 有向边 `A→B`（source=A 声明端、target=B 被指向端）。双向引用（A 引 B 且 B 引 A）⟹ 两条独立有向边各带自己 `source_location`（分别溯源到 A、B 的文档）。

**去重键**：`(source, target, relation)` 三元组唯一。Phase 2 同对恒推出单一 relation（`infer_relation` 纯函数），三元组为 Phase 3 同对多 relation 预留。

**悬空与自引用**：

| 情况 | 处理 |
|------|------|
| 悬空 `[[slug]]`（target 不在 nodes） | **丢弃 + warning**（不报错不中断，文档侧由 L2 lint 负责） |
| 自引用（`A.related` 含 `[[A]]`） | **丢弃 + warning** |
| deprecated target | **仍入图**（遍历过滤是 Phase 4 职责） |

**confidence / reviewed（Phase 3 三级分级 + 人审闭环）**：

**第一通道：结构边（Phase 2 行为不变）**

- `confidence` 恒 `"EXTRACTED"`——结构确定性抽取，非推断。
- `reviewed` 恒 `true`——结构边直接来自人写 frontmatter `related`，本身即「人已声明」，无需人审。
- 结构边是三级分级中的第一级，Phase 2 产出的边 Phase 3 不动——它们本就恒 EXTRACTED+reviewed=true。

**confidence 三级语义（Phase 3 定义）**

| 级别 | 本质 | 来源信号 | 确定性 | 能否作结论 |
|------|------|---------|--------|-----------|
| `EXTRACTED` | 确定性抽取（人写 `[[slug]]` 或机械结构派生） | frontmatter `[[slug]]` 物理存在 | 同输入同输出，可复现 | **是（权威）** |
| `INFERRED` | 算法推荐（相似度高，「可能相关」） | 相似度分数 ≥ 阈值（Phase 7 算） | 算法可复现但语义需人确认 | 人审后是 |
| `AMBIGUOUS` | 语义推断（跨文档，「或有关联」） | LLM 语义判断（Phase 7 算） | **不确定，必须人确认** | **永远不能作硬结论**（仅提示，守 C1） |

三级的 `source_location` 形态差异：EXTRACTED 为行级/字段级（Phase 2 已定）；INFERRED/AMBIGUOUS 为「来源对 + 推断依据」且**存在 `.pending-edges.yaml` 队列条目里、不在 graph.json**（详见 `trust-rules.md` §confidence 三级模型）。

**reviewed 人审状态机（Phase 3 定义）**

- `reviewed` 单向 `false → true` 不可逆；撤销 = 删该边的文档 frontmatter `[[slug]]` 再重建，不存在 `true → false`。
- 结构边恒 `reviewed=true`（人写 frontmatter 即声明，人审发生在录入文档时）。
- INFERRED/AMBIGUOUS 默认 `reviewed=false`，升级唯一路径 = 人审 approve（详见 `trust-rules.md`），**禁止 `--auto-approve` 类批量后门**。

**权威边谓词（核心契约，Phase 3 定义，Phase 4/5 遍历消费）**

```
is_authoritative(edge) := edge.confidence == "EXTRACTED" && edge.reviewed == true
```

Phase 3 **定义**此谓词并在规则文档声明，**不实现遍历器**（Phase 4）。因 graph.json `links` 里只有权威边，谓词对 `links` 永真——它真正发挥过滤作用是在 Phase 4 引入 `--include-inferred` 叠加 pending 边时。

**「links 只放权威边」架构决策（核心，D2）**

**graph.json `links` 永远只含满足 `is_authoritative` 的边（即恒 `confidence=="EXTRACTED"` && `reviewed==true`）**。INFERRED/AMBIGUOUS 推断边的唯一落点是 `.knowledge/.pending-edges.yaml`，绝不进 `links`。

理由：
1. **守单向派生 SSOT**——pending 边来自文档里还没有的 `[[slug]]`，进 `links` 即图领先于文档 = 双源。
2. **谓词对 `links` 永真，Phase 4 零负担**——遍历器对 graph.json 直接遍历即权威；推断边的叠加是额外读 pending 队列，与权威图物理隔离。
3. **Phase 2 摘要/不变量零改动**——`links` 的 confidence 分布仍恒 `EXTRACTED N | INFERRED 0 | AMBIGUOUS 0`。

人审 approve **不是**「把 pending 边搬进 links」，而是「回写源文档 frontmatter `related` 补 `[[target-slug]]` → graph-build 重新派生为 EXTRACTED 权威边」（详见 `trust-rules.md` §SSOT 写回机制）。

**conflicts_with 不主动产出**：schema 合法取值，但 Phase 2 `infer_relation` 不返回它，产出边里该 relation 计数恒 0（预留 Phase 3 人审/显式标注路径）。

### 3.5 source_location 三档降级格式（Phase 2，分隔符统一为冒号）

每条边的 `source_location` 按精度从高到低三档：

| 档位 | 格式 | 何时产出 |
|:---:|------|---------|
| **L1 行级（优先）** | `.knowledge/{dir}/{slug}.md:{N}`（N = `[[target]]` 在文件中的 1-based 实际行号） | 成功在 frontmatter related 块定位到该 `[[slug]]` 的物理行 |
| **L2 字段级（降级）** | `.knowledge/{dir}/{slug}.md:frontmatter:related` | 行号解析失败但确认来自此文档 related |
| —（拒绝） | 无 | 两档都无法确定来源 ⟹ **拒绝入图 + 报错**（对应 L-graph-orphan-edge） |

> **全库分隔符统一为冒号**（`:` 而非 `.`）——与行级 `:{N}` 的冒号分隔风格一致。行号解析降级规则详见 `graph-build-rules.md`「source_location 行号解析规则」。

---

## 4. 节点字段来源映射 + 容错原则

每篇业务文档 → 一个节点。字段从 frontmatter 抽取，来源映射与缺失容错如下（来源 `01-RESEARCH.md` §4.2，frontmatter 字段定义见 `ingestion-rules.md`「文档 frontmatter 通用格式」）：

| 节点字段 | frontmatter 来源 | 缺失容错 |
|---------|-----------------|---------|
| `id` | 文件 basename 去 `.md`（= slug，与 idx slug 列同源） | 不会缺 |
| `type` | `type:` | 缺 → **用目录推断**（`ops/` → `ops`、`flows/` → `flow` 等）；仍不得为空 |
| `status` | `status:` | 缺 → **默认 `draft`**（守 C3 草稿优先精神，不擅自升级） |
| `expires` | `expires:` | 缺 → **默认 `never`**（保守，不让 build 失败） |
| `title` | `title:` | 缺 → **用 `id`（slug）占位** |
| `path` | 相对仓库根的 `.md` 路径 | 不会缺 |
| `node_kind` | 按目录判定（`glossary/` → `glossary_term`，其余 → `document`） | 不会缺 |
| `source_mtime` | 文件系统 mtime | 不会缺 |

### 容错原则（单篇异常降级，不中断整体编译）

单篇文档 frontmatter 残缺或格式异常时，**降级填默认值 + 计入 warning，不中断整体编译**（仿既有 E2「idx 更新失败不阻断」）。编译鲁棒性 > 单篇严格——避免一篇坏文档把整图 build 搞挂。降级填值后，4 个治理字段（`id`/`type`/`status`/`expires`）仍恒非空，§2.1 不变量得以维持。

---

## 5. node_kind 决策：glossary 术语方案 A（锁定）

**Phase 1 锁定方案 A：`glossary/` 目录下每篇 `.md` 直接作为普通文档节点，仅 `node_kind="glossary_term"` 区分，不引入文档之外的任何新节点来源。**（来源 `01-RESEARCH.md` §4.3）

`node_kind` 取值集（共 2 个）：

| 取值 | 含义 | 判定 |
|------|------|------|
| `document` | 普通文档节点 | `glossary/` 之外 8 个业务目录的文档 |
| `glossary_term` | 术语文档节点 | `glossary/` 目录下的文档（术语=文档一一对应） |

方案对比与决策依据：

| 方案 | 含义 | 取舍 |
|------|------|------|
| **A（锁定）** | glossary/ 下每篇 .md 本就是术语文档，直接作普通文档节点，仅 `node_kind="glossary_term"` 标记 | 最简、零额外抽取、与 GRAPH-02「无新增数据源」完美契合。既有体系本就「术语唯一锚点在 glossary/，一术语一文件」 |
| B（推迟） | 额外扫描非 glossary 文档正文里的 `[[term]]` 内联引用，把未建文档的术语也建成**虚拟节点** | 会产出「文档里没有对应 .md 的虚拟节点」，逼近第二真理源边缘；Phase 1 不建边时这种节点是悬空孤儿。**违背最小边界，推迟**到 Phase 2 建边后再评估 |

> **结论**：`node_kind` 仅用于区分「这个文档节点是不是术语」，**不引入文档之外的新节点来源**，严格满足 GRAPH-02「无新增数据源」。方案 B 的「术语抽取入图」推迟。

---

## 6. 为什么用 `nodes` / `links` 键名

顶层节点数组键名为 `nodes`、边数组键名为 `links`，**直接对齐 `networkx.node_link_data()` / `node_link_graph()` 的默认 schema**。

理由：
- 加载时一行 `nx.node_link_graph(json.load(f), edges="links")` 即得内存图，无需自写适配层；
- networkx 只认 `id`（节点主键）/ `source`/`target`（边端点）三个键，其余字段作为节点/边属性透传——**字段语义由本文件控制**，networkx 不干预；
- 加载即自检：node_link_graph 会校验边端点必须落在 nodes 内，悬空端点直接暴露（Phase 1 `links: []` 天然无此风险，但 schema 已为 Phase 2 准备好）。

> 自定义 node-link JSON（手写序列化）作存储权威，NetworkX 仅作内存计算层、不作存储格式权威——这样字段命名与治理语义不被 networkx 版本绑定（来源 `01-RESEARCH.md` §2 决策 1）。

---

## 7. 不变量（硬约束清单）

graph.json 落盘后必须满足以下全部不变量。任一违反即视为非法产物。

1. **节点主键唯一**：`id` 全图唯一，恒为 slug = 文档 basename 去 `.md`，与 `.index/` idx `slug` 列同源。
2. **4 个治理字段必填非空**：每个节点的 `id` / `type` / `status` / `expires` 恒非空（GRAPH-02 验收点）。
3. **status 取值受限**：`status` ∈ `{canonical, active, draft, deprecated}`，检索优先级 `canonical > active > draft > deprecated`。
4. **expires 取值受限**：`expires` 为合法日期字符串或字面量 `"never"`。
5. **node_kind 取值受限**：`node_kind` ∈ `{document, glossary_term}`（方案 A）。
6. **node_count 一致性**：`node_count` == `nodes` 数组长度 == 源 .md 文件数；`doc_count` == `node_kind==document` 计数（**存在 glossary_term 时 node_count > doc_count**）。
7. **边由文档 `related` 单向派生**：Phase 1 `links == []`；**Phase 2 起 `edge_count` == `links` 实际边数**（≥0），每边满足不变量 11/12。
8. **`build_mode` ∈ {full, incremental}**：Phase 1 恒 `full`；**Phase 2 起解锁 `incremental`**（伪增量，见 `graph-build-rules.md` 增量规则）。
9. **schema_version 锁定**：`schema_version == "1.0"`。
10. **预留字段写 null**：节点 `centrality` / `community` Phase 1 恒 `null`（Phase 6 回填）。
11. **边端点完整性（Phase 2 已生效）**：任何边的 `source` / `target` 必须落在 `nodes` 的 `id` 集合内，无悬空端点。
12. **边来源铁律（Phase 2 已生效）**：任何边的 `source_location` 必须非空，缺失即拒绝入图（守 C1）。
13. **节点可溯源**：每个节点带 `path` 回源到源文档（守 C1 来源精神）。
14. **权威边谓词（Phase 3 生效）**：graph.json `links` 里每条边恒满足 `confidence=="EXTRACTED" && reviewed==true`（`is_authoritative` 永真）；`INFERRED`/`AMBIGUOUS` 边绝不出现在 `links`（它们只在 `.knowledge/.pending-edges.yaml`，见 `trust-rules.md` / `pending-edges-rules.md`）。

> 不变量 11/12 在 Phase 2 已生效：`collect_edges` 悬空边丢弃（守 11）+ `source_location` 非空强制（守 12）+ `nx.node_link_graph` 自检（最终断言防线）。不变量 14 在 Phase 3 生效：`links` 恒只含权威边（结构边恒 EXTRACTED+reviewed=true，推断边走 pending 通道绝不进 links）。

---

## 8. 边界声明（本文件不定义什么）

本文件只定义「字段长什么样」，**不定义「怎么算」**。以下内容明确**不在本文件范围**（属 `graph-build-rules.md` 与 Phase 2-6）：

- ❌ 派生算法（节点抽取/边建立/source_hash 计算逻辑）→ 见 `graph-build-rules.md`
- ❌ 边建立规则（relation 分类、source_location 校验）→ Phase 2
- ✅ confidence 三级语义 + reviewed 人审状态机 + 权威边谓词 `is_authoritative` 由本文件 §3.1/§3.4 定义；人审命令/队列/写回机制见 `trust-rules.md` + `pending-edges-rules.md`（Phase 3）；遍历器/渲染分级措辞 → Phase 4/5
- ❌ 增量重建（dirty-set 子图重算）→ Phase 2
- ❌ 中心度 / 社区检测计算 → Phase 6
- ❌ 完整 Python 脚本实现 → 01-02 的 `graph_build.py`

> 把后续阶段的实现细节写进本文件会越界到 Phase 2-6 且违反最小边界。本文件只是稳定的字段契约。
