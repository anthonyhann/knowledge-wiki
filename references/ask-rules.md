# 查询（ask）详细规则

> 由 `/knowledge-wiki ask` 使用。SKILL.md 仅保留入口与索引，本文件是唯一权威源。

---

## ask 子命令分发（graph / explain / test）[Phase 4 新增，test 为 v2.1.0 新增]

ask 收到用户输入后，**先判分发路由**（六路）：

| 用户输入形式                           | 分发目标 | 处理逻辑 |
|----------------------------------|---------|---|
| `ask graph "X"`                  | → graph 分支 | 调 `graph_query.py neighbors <slug> --kb-root .knowledge --hops 1 --budget 60 [--include-inferred]` |
| `ask explain "X"`                | → explain 分支 | 调 `graph_query.py node <slug> --kb-root .knowledge [--include-inferred]` |
| `ask test "<模块/场景>" [--level unit|integration|api|e2e]` | → test 聚合分支 | **不走 graph_query，走 test.idx.md 聚合流程**（见下方「ask test 测试知识包」节） |
| `ask links <slug>`               | → 既有 links 分支 | **不变**（见下方「links / refs」节） |
| `ask refs <slug>`                | → 既有 refs 分支 | **不变**（见下方「links / refs」节） |
| `ask "X"`（裸）                     | → **既有四层检索**（Layer -1/0/0.5/1） | 一字不改，见下方「检索策略」节 |
| `ask path "A" "B"`               | → path 分支 | 调 `graph_query.py path <A> <B> --kb-root .knowledge [--include-inferred] [--include-deprecated] [--include-expired] [--max-hops N]` |

**调用方式**（仿 graph_build.py 范式）：

```bash
uv run .knowledge/.graph/scripts/graph_query.py <sub> <slug> --kb-root .knowledge [--hops N] [--budget N] [--include-inferred]
# [Phase 5 新增] path 双参数调用（A→B 多跳桥接知识链）：
uv run .knowledge/.graph/scripts/graph_query.py path <A> <B> --kb-root .knowledge [--include-inferred] [--include-deprecated] [--include-expired] [--max-hops N]
```

**自然语言入参定位 slug**：ask graph/explain/path 收到自然语言时（非精确 slug），可**先走既有四层检索定位到 slug**（复用成熟关键词逻辑），再用精确 slug 喂 graph_query.py，避免与四层检索打架。path 收到自然语言 A/B 时，**对 A、B 各走一次既有四层检索定位 slug**，再用精确 slug 喂 `graph_query.py path`。

---

### graph / explain 分支：图层探测 + 降级

**图层探测**：探测 `.knowledge/.graph/graph.json` 是否存在（或凭 graph_query 输出 `degraded` 字段判断）。

**凭 degraded 字段（非退出码）分支**（退出码 0 含降级场景，禁止凭退出码判断）：

| degraded 值 | 含义 | 处理 |
|------------|------|------|
| `"graph_missing"` | 图层不存在或损坏 | 输出「⚠️ 未编译图谱，建议 `/knowledge-wiki health graph-build`」+ **降级到裸 ask 四层检索处理 "X"**（不崩溃） |
| `"node_not_found"` | 节点未命中 | 如实告知「图谱中无此节点 X」+ 建议检查 slug 或录入（**不脑补**，守 C1） |
| `"ambiguous"` | 多候选命中 | 列出 `candidates[]` 让用户选择（不取 Top1，不代为决策） |
| `null` | 正常 | 按下方「分级渲染骨架」输出 |

---

### 分级渲染骨架（EXTRACTED 权威 vs INFERRED/AMBIGUOUS 推断）[Phase 4 新增]

AI 读 graph_query JSON 的 `confidence` / `origin` / `authoritative` 字段决定措辞——脚本只给数据字段，**措辞约束在本节**。

#### 分级措辞表

| confidence | origin | authoritative | 渲染措辞 |
|-----------|--------|:---:|---------|
| `EXTRACTED` | `links` | ✅ true | 正常陈述 + `[来源: {source_location}]` |
| `INFERRED` | `pending` | ❌ false | `⚠️ 推断边·未经人审：` 前缀 + 正常描述 + `[依据: {source_location}]` |
| `AMBIGUOUS` | `pending` | ❌ false | `⚠️ 推断边·仅线索（AMBIGUOUS，不作结论）：` 前缀 + 描述 + `[依据: {source_location}]`（**永不写成肯定句**，守 C1） |

#### 视觉区分原则

- 推断边（INFERRED/AMBIGUOUS）必带 ⚠️ + 「未经人审」/「仅线索」字样，**不混入权威结论段落**
- `deprecated` 节点渲染标「（已废弃）」——图里可遍历但渲染降权（沿 status 优先级精神）
- `--include-inferred` 未传入时，推断边整段不出现（默认仅展示权威边）

#### ask graph 输出骨架

```
🕸️ 知识图谱·关系子图：{center.title}

中心节点：{center.title}（{center.type}，{center.status}）

权威关联（{authoritative_count} 条）：
  • {neighbor.title} ─[{edge.relation}]─ [来源: {edge.source_location}]
  • ...

（仅 --include-inferred 时显示）
⚠️ 推断关联（未经人审，{inferred_count} 条）：
  • ⚠️ 推断边·未经人审：{neighbor.title} ─[{edge.relation}]─ [依据: {edge.source_location}]
  • ⚠️ 推断边·仅线索（AMBIGUOUS，不作结论）：{neighbor.title} ─[{edge.relation}]─ [依据: {edge.source_location}]

{truncated 时}⚠️ 子图共 {total} 条边，受 budget 限制仅展示 {budget_used} 条
来源：.knowledge/.graph/graph.json（编译产物，非文档原文）
```

#### ask explain 输出骨架

```
🔍 知识图谱·节点解释：{center.title}

基本信息：
  类型：{center.type} | 状态：{center.status} | 时效：{时效状态}
  文档：.knowledge/{center.path}

引用了（出边，{out_count} 条）：
  • ─[{relation}]→ {target.title} [来源: {source_location}]
  • ...

被引用（入边，{in_count} 条）：
  • {source.title} ─[{relation}]→ [来源: {source_location}]
  • ...

（仅 --include-inferred 时显示）
⚠️ 推断关联（未经人审）：
  • ⚠️ 推断边·未经人审：... ─[{relation}]─ [依据: {source_location}]
  • ⚠️ 推断边·仅线索（AMBIGUOUS，不作结论）：... [依据: {source_location}]

连接小结：{center.title} 共有 {total_edges} 条关联（权威 {auth_count} + 推断 {inferred_count}），在知识图谱中处于 {连接度描述} 位置。
来源：.knowledge/.graph/graph.json（编译产物，非文档原文）
```

> **时效状态**复用既有「时效状态」计算规则（FRESH/WARNING/EXPIRED），见下方「标准回答格式 → 时效状态」。

#### ask path 输出骨架 [Phase 5 新增]

**设计原则**（比 neighbors 更严的整链诚实）：

- 每跳标可信度 + 来源（链逐跳可追溯，守 C1）。
- 含 INFERRED 软边 → **整链强制⚠️警告**（`has_inferred_edge==true` 时链顶整链级警告，非仅该跳——path 是链式结论，一环不牢整链存疑）。
- **AMBIGUOUS 永不出现在 path 渲染**（机制层已排除，path 骨架不需要 AMBIGUOUS 措辞——与 graph/explain 不同）。
- no_path 诚实措辞：绝不脑补中间节点、绝不说「可能通过…连接」。

**正常路径输出骨架（权威链）**：

```
🔗 知识链：{from.title} → {to.title}（{path_length} 跳，权威链）

  [[{node_0.id}]]（{node_0.type}·{node_0.status}）
    │ {edge_0.relation}  [来源: {edge_0.source_location}]
    ▼
  [[{node_1.id}]]（{node_1.type}·{node_1.status}）
    │ {edge_1.relation}  [来源: {edge_1.source_location}]
    ▼
  [[{node_2.id}]]（{node_2.type}·{node_2.status}）

链路小结：{path_length} 跳全程权威边（EXTRACTED·已审），可作结论。
来源：.knowledge/.graph/graph.json（编译产物，非文档原文）
```

**含推断软边输出骨架（--include-inferred，整链强制警告）**：

```
⚠️ 此知识链含未审推断边（INFERRED），非权威知识链，仅供参考——推断边需经人审升级方可作结论。

🔗 知识链（含推断）：{from.title} → {to.title}（{path_length} 跳）

  [[{node_0.id}]]（{node_0.type}·{node_0.status}）
    │ {edge_0.relation}  [来源: {edge_0.source_location}]（权威）
    ▼
  [[{node_1.id}]]（{node_1.type}·{node_1.status}）
    │ ⚠️ 推断边·未经人审  {edge_1.relation}  [依据: {edge_1.source_location}]
    ▼
  [[{node_2.id}]]（{node_2.type}·{node_2.status}）

链路小结：{path_length} 跳中含 {inferred_count} 跳未审推断边——整链不可作硬结论（守 C1）。
建议：人审相关推断边（/knowledge-wiki health edge-review）后再采信。
来源：.knowledge/.graph/graph.json + .pending-edges.yaml（推断边）
```

**无路径输出骨架（守 C1 不脑补）**：

```
🔗 知识链：{from.title} ⇏ {to.title}

知识库中无连接「{from.title}」与「{to.title}」的已知关联路径。

（不脑补、不编造中间节点——两节点在当前权威图谱中不连通。）

{filtered_out.deprecated_excluded 或 expired_excluded 时追加}
💡 提示：本次默认排除了 deprecated/EXPIRED 节点。若需经由废弃/过期知识查找桥接，可试：
   ask path "{from.title}" "{to.title}" --include-deprecated --include-expired
来源：.knowledge/.graph/graph.json
```

**边界措辞速查**：

| 场景 | 措辞要点 |
|------|---------|
| A==B（path_length=0） | 「起点与终点是同一节点 [[X]]，无需桥接。」 |
| degraded=node_not_found | 「图谱中无节点『X』」+ 标明是起点（from）还是终点（to）+ 建议查 slug/录入（不脑补） |
| degraded=ambiguous | 列 candidates（标 from/to），「你说的『X』是指以下哪个？」 |
| degraded=graph_missing | 「⚠️ 未编译图谱，建议 health graph-build」+ path 无文档级兜底，如实告知图层缺失（path 不降级四层检索） |

---

### path 分支：图层探测 + A/B 双定位 + 治理过滤 [Phase 5 新增]

**图层探测**：同 graph/explain，凭 graph_query 输出 `degraded` 字段判断（非退出码）。

**凭 degraded 字段 + no_path 字段分支**（path 是两节点间关系链查询，分支逻辑如下）：

| degraded / 字段 | 含义 | 处理 |
|----------------|------|------|
| `degraded=="graph_missing"` | 图层不存在或损坏 | 输出「⚠️ 未编译图谱，path 需要图层，建议 `/knowledge-wiki health graph-build`」——**path 不降级到四层检索**（path 是关系链查询，裸 ask 四层检索是单主题检索，无对应语义，强行降级会答非所问；这是 path 相对 graph/explain 降级路径的唯一差异） |
| `degraded=="node_not_found"` | A 或 B 未命中 | 如实告知**哪个端点**（from/to）未命中 + 建议检查 slug 或录入（**不脑补**，守 C1）；据 `candidates[]` 中 `endpoint` 字段标明是 A（from）还是 B（to）；一次只报一个端点问题（先 A 后 B） |
| `degraded=="ambiguous"` | A 或 B 多候选命中 | 列出 `candidates[]`（据 `endpoint` 字段标明是 A 还是 B 的候选），「你说的『X』是指以下哪个？」（不取 Top1，不代为决策） |
| `no_path==true`（degraded=null） | 两端命中但治理子图上无路径 | **如实告知「A 与 B 之间无已知关联路径」，绝不脑补中间节点**（守 C1）；据 `filtered_out` 诚实提示（见下） |
| `degraded==null && no_path==false` | 正常 | 按下方「ask path 输出骨架」渲染 |

**filtered_out 诚实提示**（守 C1，区分「真无路径」vs「被治理过滤切断」）：

`no_path==true` 且 `filtered_out.deprecated_excluded==true` 或 `filtered_out.expired_excluded==true` 时，追加提示：
> 💡 本次默认排除了 deprecated/EXPIRED 节点。若需经由废弃/过期知识查找桥接，可加 `--include-deprecated --include-expired` 重试。

**EXPIRED 措辞复用**：链上节点 EXPIRED（仅 `--include-expired` 时可能出现）时，复用下方「时效状态」既有 EXPIRED 措辞标注（「⚠️ 此条知识已过期」）。

**操作日志复用（C6）**：path 复用既有 ask 日志通道（`.logs/personal/{user-id}.md`），detail 的 `layer` 字段标 `path`，可加 `from`/`to`/`path_length`/`no_path`/`has_inferred`，**不另起日志通道**：

```markdown
## [2026-06-15T10:30:00+08:00] @alice | ask | a1b2c3d4
  detail: {"layer": "path", "from": "print-timeout", "to": "delivery-flow", "path_length": 2, "no_path": false, "has_inferred": false}
```

---

### 操作日志（graph/explain）[Phase 4 新增]

graph/explain 也写 ask 类日志（复用「操作日志记录」通道），detail 的 `layer` 字段标 `graph` 或 `explain`（不另起日志通道，守 C6）：

```markdown
## [2026-06-15T10:30:00+08:00] @alice | ask | a1b2c3d4
  detail: {"hit": "ops/print-timeout", "status": "FRESH", "docs_read": 0, "layer": "graph", "edges": 3}
```

---

### ask test 测试知识包（聚合分支）[v2.1.0 新增]

> 面向 QA Agent 场景的**单点聚合消费入口**：按模块/场景过滤 tests/ 知识，输出结构化测试知识包，可直接注入 Agent QA 上下文。区别于裸 ask（找单篇文档）与 ask graph（查关系）——ask test 是**知识包聚合**，目标是让 QA Agent 一次取齐某模块的全部测试知识。

**前置条件**：`.knowledge/.index/test.idx.md` 存在（不存在时按 Layer -1 退化规则跳过 Index 层，转 rg 搜索 `.knowledge/tests/`；目录也不存在则如实告知无记录，守 C1）。

**执行步骤**：

```
1. 读取 .knowledge/.index/test.idx.md 全表（单文件，无图谱依赖）
2. 过滤：
   a. 模块/场景关键词匹配 scope + tags + title + TL;DR 列（global 条目恒命中）
   b. --level unit|integration|api|e2e 时：保留 test_level == 指定值或 all 的条目。
      语义区分（互不互换）：e2e = 端到端链路对账类测试（如内部 e2e 链路对账工具，request_id 链路追踪）；
      api = API HTTP 接口测试（如内部单测工具的接口测试层，走 Controller 链路验证接口契约）。查询互不兼容：
      --level e2e 不命中 test_level=api 的文档，反之亦然
   c. status 过滤：canonical > active > draft，deprecated 剔除（守既有优先级）
3. 命中条目逐篇读全文（.knowledge/tests/{slug}.md）
4. 按 test_kind 五分组整理（一篇多 kind 时按主 kind 归组，其余组交叉引用）：
   ① 运行环境与命令（env）——**置顶**，QA Agent 首要消费
   ② 规则与规范（rules）
   ③ 检查清单（checklist）
   ④ 坑点与经验（experience）
   ⑤ 测试数据准备（data）
5. 输出知识包（见下方骨架）
6. 记录操作日志（复用 ask 通道，detail.layer = "test"，含 matched_slugs/kind_dist/level）
```

**输出骨架**：

```
🧪 测试知识包：{模块/场景}{--level 时追加「（{level} 层）」}

① 运行环境与命令（{n} 条）
  • {命令/Bootstrap 要点} — [来源: tests/{slug}]（{status}，{时效状态}）

② 规则与规范（{n} 条）
  • {规则} — [来源: tests/{slug}]

③ 检查清单（{n} 条）
  • [ ] {验证点} — [来源: tests/{slug}]

④ 坑点与经验（{n} 条）
  • ⚠ {坑点}（触发：{条件}；规避：{方法}）— [来源: tests/{slug}]

⑤ 测试数据准备（{n} 条）
  • {数据构造方法} — [来源: tests/{slug}]

小结：命中 {N} 篇（{status 分布}），覆盖 kind：{kind 分布}。
```

**核心约束**：

- 每条必带 `[来源: tests/{slug}]`，守 C1 可追溯
- EXPIRED 条目照常展示但标注「⚠️ 此条知识已过期，建议：/knowledge-wiki health audit <slug>」（与裸 ask 时效规则一致）
- 0 命中时输出「该模块/场景无测试知识记录」+ 建议 `/knowledge-wiki in <测试知识>`，**禁止用模型知识填补**（守 C1）
- 命中 ≤3 篇时全量输出；>3 篇时每组取最相关条目，末尾提示「另有 {N} 篇未展开，`ask refs {slug}` 逐篇追溯」
- 本分支**不触发回流提示**（ask test 输出本身就是聚合，非跨文档新结论）

---

## 检索策略（三层：Index 预筛选 → rg 关键词 → 语义筛选）

### Layer -1 [NEW]：Index 分段预筛选（调用上限 1 轮，可选跳过）

在 Layer 0 之前插入的轻量级预筛选层。**核心目标：缩小 rg 搜索范围，减少噪声候选。** 详见 `references/index-rules.md`「读取规则」。

```
1. 从用户问题中提取关键词特征（同 Layer 0 的关键词提取逻辑）
2. 根据问题特征推断最可能的 1-2 个 idx 文件（见下方「idx 选择策略」表）
3. 读取对应 idx 文件的 title / tags / TL;DR 列（仅 1-2 个文件，非全部 9 个）
4. 在 idx 表格中做子串匹配（title + tags + TL;DR 三列）
5. 命中 ≥1 行 → 提取这些 slug 作为 Layer 0 的"优先范围"
6. 命中 0 行或无法推断 idx → **跳过本层**，直接进入 Layer 0（退化为原有行为）
```

**idx 选择策略**（从问题推断用哪个 idx）：

| 问题特征                                           | 优先读取的 idx | 备选 idx |
|------------------------------------------------|--------------|---------|
| 含"是什么"/"定义"/"术语"                               | `glossary.idx.md` | — |
| 含"架构"/"系统设计"/"拓扑"                              | `design.idx.md` | — |
| 含"流程"/"步骤"/"规则"/"怎么做的"                         | `flows.idx.md` | `case.idx.md` |
| 含"接口"/"API"/"字段"/"请求"                          | `apis.idx.md` | — |
| 含"表"/"模型"/"存储"/"数据库"                           | `db.idx.md` | — |
| 含"运维"/"告警"/"超时"/"配置"/"部署"                      | `ops.idx.md` | — |
| 含"需求"/"PRD"/"验收"                               | `requirements.idx.md` | — |
| 含"故障"/"复盘"/"踩坑"/"反例"                           | `case.idx.md` | `flows.idx.md` |
| 含"测试"/"用例"/"回归"/"QA"/"单测"/"集成测试"/"API测试"/"E2E" | `test.idx.md` | `case.idx.md` |
| 含"综合"/"对比分析"/"关联发现"/"回流"                       | `synthesis.idx.md` | — |
| 无法推断                                           | **跳过 Index 层**，直接进 Layer 0 | — |

**Index 命中后的效果**：Layer 0 的 rg 搜索增加路径约束，限定在 idx 命中的 type 对应目录内搜索。

### Layer 0：rg 关键词匹配（调用上限 3 轮）

```bash
rg "<关键词>" .knowledge/ -l --type md
```

**关键词提取**：去掉停用词（的/是/了/多少/什么/吗/呢/怎么），提取名词和动词原形，保留专业术语原样。

**重试层级**（任一轮命中 ≥1 文件即进入 Layer 1）：

| 轮次 | 策略 | 示例（查询："配送超时怎么配置"） |
|------|------|---------|
| Round 1 | 原始关键词 2-4 个并行搜索 | rg "配送超时" / rg "配送" / rg "超时" |
| Round 2 | 拆词为词根 + 同义词扩展 | + rg "timeout" / rg "delivery" |
| Round 3 | 拼音 + 只查 frontmatter title/tags | rg -i "^title:.*(配送\|delivery)" |

3 轮后仍 0 命中 → 进入 Layer 0.5 兜底；Layer 0.5 仍 0 命中 → 输出「知识库无记录」模板，不猜测。

> **注意**：若 Layer -1 已返回候选 slug 列表，Layer 0 的 rg 搜索应限定在这些 slug 所在的目录范围内（通过路径前缀约束），大幅减少噪声。

### Layer 0.5：frontmatter 模糊兜底（最后一搏，1 轮）

仅在 Layer 0 三轮全部 0 命中时执行，目标是抓回「关键词偏但主题相近」的文档：

```bash
# 拆查询为单字符级 fuzzy 模式，只扫 frontmatter 的 title 和 tags
rg -i "^(title|tags):" .knowledge/ --type md
```

匹配规则：
1. 提取查询中所有 ≥2 字的连续中文片段 + 所有英文单词
2. 对每个片段做大小写不敏感的子串匹配（不要求词边界）
3. 命中 ≥1 个片段的文件即视为候选，进入 Layer 1
4. 候选 > 5 时按 frontmatter `status` 优先级（canonical > active > draft）取 Top 5
5. 仍 0 命中 → 走「无记录」分支

**铁律**：本层不放宽「不用模型训练知识填补」原则，只是把搜索范围扩到 frontmatter；正文未命中绝不脑补。

### Layer 1：Claude 语义筛选

读取命中文件的 frontmatter + TL;DR，选出最相关 1-3 篇，读全文生成回答。若语义筛选后仍无明确中的 → 输出「知识库无记录」模板。

**status 优先级**：`canonical > active > draft > deprecated`（deprecated 禁止引用）

---

## 标准回答格式

```
回答：打印服务超时阈值为 30s，超时后 fallback 到本地缓存，不直接报错。

来源：.knowledge/ops/print-timeout.md（第 12 行）
录入：@alice，2026-05-12
状态：FRESH（距过期还有 82 天）

被引用：[[order-flow-design]]（1 处）
引用了：[[fallback-strategy]]（1 处）
```

### Ask 图谱轻提示 [Phase 4 新增]（可选，条件触发）

裸 ask 命中并选定某 slug 后（收尾阶段），调一次 `graph_query.py count <slug> --kb-root .knowledge` 读 `authoritative_edge_count`。

在标准回答末尾追加可选行：

```
💡 该词在知识图谱有 N 个关联，试 `ask graph "X"`
```

**显示条件（全满足才显示，否则整行不出现）**：

1. 裸 ask 命中并选定 slug
2. 图层存在（count 未 degraded，即 `degraded != "graph_missing"`）
3. `authoritative_edge_count ≥ 1`

三条件任一不满足 → 整行消失（与图层从未存在一致，守零破坏）。

**零侵入保证**：不改检索结果、不改路由、不改回答主体——只在末尾纯追加一行（D-Q2 唯一叠加）；图层不存在 / N==0 时整行消失。

**触发时机**：count 在裸 ask 四层检索**命中收尾后**调一次（不在 rg 检索热路径，不增 rg 轮次，守 QUERY-05 四层检索逻辑零改）；count 只 json 加载 + 线性扫边，毫秒级无感知负担。

**与回流提示关系**：两者同为「条件触发追加行」（见下方「Ask 回流提示」节），可同时出现各占一行，模式一致互不冲突。

### 时效状态

| 状态 | 条件 | 计算示例 |
|------|------|---------|
| FRESH | 距 expires > 30 天，或 never | created=2026-05-12, expires=2026-08-12, 今日=2026-05-13 → 90 天 → FRESH |
| WARNING | 距 expires ≤ 30 天且未过期 | 今日=2026-07-20, expires=2026-08-12 → 23 天 → WARNING |
| EXPIRED | 已超过 expires | 今日=2026-09-01, expires=2026-08-12 → 已过 20 天 → EXPIRED |

EXPIRED 文档引用时，末尾追加：

```
⚠️ 此条知识已过期，建议：/knowledge-wiki health audit <slug>
```

---

## 知识库无记录时

```
知识库中无相关记录。
搜索范围：.knowledge/**/*.md（共 47 篇）

建议：
  /knowledge-wiki in <描述>           手工录入
  /knowledge-wiki health scan         检查外部源是否有相关文档
```

**核心约束：不用模型训练知识填补，不说"通常情况下"。**

---

## links / refs（追溯）

```bash
# 反向追溯：谁引用了这篇
/knowledge-wiki ask links <slug>
→ rg "\[\[<slug>\]\]" .knowledge/ -l --type md

# 正向追溯：这篇引用了谁
/knowledge-wiki ask refs <slug>
→ rg "\[\[.*\]\]" .knowledge/<对应文件>.md
```

输出：文件路径 + 行号，说明"更新此文档时，以上关联文档可能需要同步检查"。


---

## 操作日志记录 [NEW]

每次 `ask` 执行完成后（无论是否命中），**必须**追加一条记录到 `.logs/personal/{user-id}.md`。

### 记录格式

详见 `references/log-rules.md`「日志条目格式」的 **ask 类型**：

```markdown
## [2026-05-26T14:40:15+08:00] @alice | ask | a1b2c3d4
  detail: {"hit": "ops/print-timeout.md", "status": "FRESH", "docs_read": 1, "layer": "L0-R1"}
```

**关键：ask 的 title 字段使用 `sha1(原始问题)[:8]` 而非问题原文，保护用户隐私。**

### 命中与未命中均记录

| 场景 | detail 内容 |
|------|------------|
| 命中（有答案） | `{"hit": "<slug>", "status": "FRESH\|WARNING\|EXPIRED", "docs_read": N, "layer": "L-1/L0/L0.5/L1"}` |
| 未命中 | `{"hit": "none", "docs_scanned": N, "reason": "L0 全失败 + L0.5 兜底无结果"}` |

---

## Ask 回流提示 [NEW]（可选，条件触发）

当满足以下**所有条件**时，在标准回答末尾追加回流提示：

```
💡 此回答综合了 ≥2 篇文档的知识，是否录入为新的知识条目？
  /knowledge-wiki in --from-answer "{用户问题的简短描述}"
```

### 触发条件（全部满足才显示）

1. Layer 1 语义筛选时读取了 **≥2 篇文档**并做了综合
2. 回答长度 **>300 词**（短回答通常不值得独立成篇）
3. 回答内容包含**跨文档的对比、分析或关联发现**（非简单引用单篇）

### 不触发的情况

- 命中了 synthesis 类型文档 → synthesis 本身就是派生知识，禁止二次回流
- 用户问题为简单事实查询（如"XX 的超时配置是多少"）
- 回答来源为单一文档

### --from-answer 处理

`in --from-answer` 将当前 AI 对话中的回答内容作为输入源，走正常 `in` 结构化流程：
- type 直接设为 `synthesis`（无需走 type 推断，因为回流内容本身就是综合分析）
- sources 标注为：`"由 /knowledge-wiki ask '{question}' 综合生成，{YYYY-MM-DD}"`
- `derived_from`：自动填充为当前 ask 回答中引用的所有文档 slug
- `derived_question`：原始问题原文
- 质量门禁：来源文档 ≥2 篇且均非 deprecated（见 `_registry.yaml` synthesis 的 quality_gate）
- 模板：按 `references/templates/synthesis.md` 骨架生成正文