# .knowledge/ 目录框架与根文件模板

> **本文件是 `.knowledge/` 目录结构与 L1/L2/L3 层级映射的唯一权威源**。SKILL.md / DESIGN.md / README.md 仅引用，不重复展开。
>
> 目录与 type 的层级（layer）字段以 `references/templates/_registry.yaml` 为准；本文件是它的概念视图。新增/调整 type 时**先改 yaml**，再同步本文件。

---

## L1 / L2 / L3 三层认知架构

| 层级 | 别名 | 认知角色 | 核心问题 | 知识对象类型 |
|------|------|----------|----------|-------------|
| **L1 领域层** | 骨架 | 决策 | 这归谁管？能做什么？不能做什么？ | 边界 + 意图 + 状态机 + 协作拓扑 + 业务护栏 |
| **L2 执行层** | 分子 | SOP 编排 | 怎么做？什么顺序？失败怎么办？ | 触发绑定 + 步骤 DAG + 分支条件 + 人工节点 + Use Case |
| **L3 能力层** | 原子 | 工具调用 | 用什么？接口长什么样？SLA 多少？ | 输入参数 + 输出结构 + 协议坐标 + 运行约束 |

- **L1（领域层 / 骨架）**：偏业务知识与功能边界，承诺**能力边界的确定性**。L1 缺失，AI 会把本属 A 服务的需求错配到 B 服务。承载实体定义、业务边界、状态机、协作拓扑、业务护栏。
- **L2（执行层 / 分子）**：承载**编排确定性**与矛盾状态表征，是 L1 业务意图到 L3 原子能力的桥梁。**Use Case（典型/反例案例）主要挂载在 L2 的 SOP 上**，作为动态上下文驱动 AI 决策。
- **L3（能力层 / 原子）**：最细粒度的原子能力，承载**执行确定性**与 SLA 约束。涉及具体技术栈、接口、数据模型、运维配置。

> 设计哲学详见 `DESIGN.md`「二、L1 / L2 / L3 三层认知架构」。

---

## 目录树（10 个业务目录 + 4 个根文件 + 3 个系统目录）

```
.knowledge/
├── # ===== 根文件（4 个）=====
├── README.md               ← 双受众入口（顶部给 AI，底部给人类）
├── CLAUDE.md               ← AI 协作契约 + 禁止行为 + 黄金原则
├── AGENTS.md               ← AI 地图（≤50 行）
├── .sources.yaml           ← 外部知识源注册表
│
├── # ===== 业务目录（10 个）=====
├── glossary/               ← L1 术语词典（全局唯一锚点，最先写）
├── design/                 ← L1/L2 架构/技术方案/决策（type 字段区分）
├── requirements/           ← L1 需求文档、PRD、验收标准
├── flows/                  ← L2 核心业务流程 SOP（含业务规则与计算逻辑）
├── case/                   ← L2 反向示例 / 问题汇总 / 故障复盘（反例 Use Case）
├── tests/                  ← [v2.1.0 新增] L2 测试场景知识/经验/规则（供 QA Agent 消费，ask test 单点聚合）
├── apis/                   ← L3 接口约定、字段映射
├── db/                     ← L3 数据模型、存储设计
├── ops/                    ← L3 运维、告警、大促保障
└── synthesis/              ← [v0.8.0 新增] L2 Ask 回流综合分析文档（独立目录，禁止二次回流）
│
├── # ===== 系统目录（AI 维护，禁止手动编辑）=====
├── .index/                 ← 分段索引（按 type 分 idx 文件）
│   ├── _meta.yaml          ←   索引元数据（条目数/更新时间）
│   ├── glossary.idx.md     ←   glossary/ 索引
│   ├── design.idx.md       ←   design/ (architecture|solution|adr) 索引
│   ├── requirements.idx.md ←   requirements/ 索引
│   ├── flows.idx.md        ←   flows/ 索引
│   ├── case.idx.md         ←   case/ 索引
│   ├── test.idx.md         ←   [v2.1.0] tests/ 索引
│   ├── apis.idx.md         ←   apis/ 索引
│   ├── db.idx.md           ←   db/ 索引
│   ├── ops.idx.md          ←   ops/ 索引
│   └── synthesis.idx.md    ←   synthesis/ 索引
│
├── .logs/                  ← 操作日志（按人分文件，解决 git 并发冲突）
│   ├── _config.yaml        ←   日志配置（归档阈值/脱敏规则/digest 配置）
│   ├── personal/           ←   每人私有日志（{user-id}.md）
│   │   ├── alice.md     ←     @alice 的操作记录
│   │   └── ...
│   ├── archive/            ←   归档日志（只读，按季度）
│   │   └── ...
│   └── digest.md           ←   团队聚合摘要（health 自动生成，建议 .gitignore）
│
├── .pending-backlinks.yaml ← 待消费的反向引用队列（backlink 延迟回写缓冲）
├── .pending-edges.yaml    ← [Phase 3 新增] 待人审推断边队列（INFERRED/AMBIGUOUS，由 health edge-review 单条人审消费；与 .graph/ 物理隔离，删 .graph/ 后仍存活）
└── .pending-docs.yaml      ← [v1.1.0 新增] 代码文档化待处理缓存（docs 子命令暂存分析结果）
```

### 派生层 `.graph/`（[Phase 1 新增] 可选叠加，删除即零破坏回退）

与 `.index/ .logs/ .pending-backlinks.yaml .pending-docs.yaml` **同级**的图谱派生层。由 `health graph-build` 生成、`init` 复制引擎脚本就位（见下方「创建顺序」Step 6）：

```
.knowledge/
└── .graph/                 ← 图谱派生层（整个目录是文档 SSOT 的派生物）
    ├── graph.json          ←   编译产物（node-link schema；唯一写入路径=graph_build.py 原子写）
    ├── scripts/            ←   引擎副本目录
    │   ├── graph_build.py  ←     init 复制的派生引擎（PEP 723，networkx==3.6.1）
    │   ├── graph_query.py  ←     [Phase 4 新增] init 复制的只读查询引擎（PEP 723，networkx==3.6.1；ask graph/explain 调用）
    │   ├── graph_analyze.py ←    [Phase 6 新增] init 复制的涌现分析引擎（PEP 723，networkx==3.6.1；health graph 调用）
    │   ├── discover_prefilter.py ← [Phase 7 新增] init 复制的候选发现引擎（PEP 723，networkx==3.6.1；health discover 调用，只读 graph.json 输出候选 JSON 绝不入队）
    │   ├── explore_questions.py ← [Phase 8 新增] init 复制的可探索问题预计算引擎（PEP 723，networkx==3.6.1；health graph 调用，只读 communities.json/graph.json + 读 .pending-edges.yaml 输出 explorable-questions.json，绝不回填 graph.json/不碰文档）
    │   └── graph_export.py  ← [Phase 9 新增] init 复制的可视化导出引擎（PEP 723，networkx==3.6.1；graph export 调用，只读 graph.json/communities.json + 读 .pending-edges.yaml，唯一写 .graph/exports/，绝不回填/不碰文档）
    ├── exports/             ← [Phase 9 新增] 可视化产物（graph.html/graph.canvas/graph.graphml；纯消费品，删 .graph/ 一并删，零残留回退）
    └── .build.lock         ←   编译锁（瞬态；finally 无条件释放，并发 build 时 exit 2）
```

> **`.graph/` 是可选派生层**：整个目录可随时 `rm -rf .knowledge/.graph/` 删除，删除后 init/in/ask/docs/health 基础功能全链路正常、行为与「图层从未存在」时完全一致（GRAPH-05 零破坏回退）。既有 5 子命令的任何路径都不读 graph.json，图层是叠加而非替换。
>
> **[Phase 3 补充]** `.pending-edges.yaml` 与 `.pending-backlinks.yaml` 同为 `.knowledge/` 根文件、**不在 `.graph/` 下**——删 `.graph/` 回退纯文档库后，pending-edges 队列里「待回写文档的关系建议」仍有意义（服务文档治理而非图），故应存活（见 `references/pending-edges-rules.md`）。

---

## 目录与 type 完整映射表

| 目录 | layer | type | 核心职责 | 典型内容举例 |
|------|-------|------|----------|-------------|
| `glossary/` | **L1** | `glossary` | 全局唯一术语锚点，所有文档用 `[[slug]]` 引用 | "配送单"、"follow_key"、"动线区块" 的业务定义与技术字段映射 |
| `design/` | **L1** | `architecture` | 系统架构现状（活文档，持续更新） | 整体服务拓扑图、模块职责说明 |
| `design/` | **L1** | `adr` | 架构决策记录（为什么这样选） | 选型 Redis vs MySQL 的决策记录 |
| `design/` | **L2** | `solution` | 某需求的技术方案（时间点快照） | 配送发单重构方案 |
| `requirements/` | **L1** | `requirement` | PRD、feature spec、验收标准 | 配送发单功能需求文档 |
| `flows/` | **L2** | `flow` | 核心业务流程 SOP，含分支、人工节点与业务规则 | 配送下单时序、小费计算规则、违约金扣除条件 |
| `case/` | **L2** | `case` | 反向示例 / 问题汇总 / 故障复盘，反例驱动 SOP 防护 | 队列堆积复盘、Pipeline 误用反例、踩坑总结 |
| `tests/` | **L2** [v2.1.0] | `test` | 测试场景知识/经验/规则，供 QA Agent 消费（`ask test` 单点聚合） | 单测 Mock 策略、Bootstrap 运行命令、回归检查清单、测试踩坑（订单 ID 归档路由）、测试数据构造 |
| `apis/` | **L3** | `api` | 接口约定、字段映射、请求响应结构 | 三方配送接口字段说明、open-api 回调协议 |
| `db/` | **L3** | `db` | 数据模型、存储设计、索引策略 | 订单表结构、Redis key 命名规范 |
| `ops/` | **L3** | `ops` | 运维手册、告警阈值、大促保障、超时配置 | 打印服务超时阈值 30s、大促限流配置 |
| `synthesis/` | **L2** [v0.8.0] | `synthesis` | Ask 回流综合分析文档（独立目录，禁止二次回流） | 跨文档对比分析、关联发现、综合结论 |

> `design/` 通过 frontmatter 的 `type` 字段区分三类文档（architecture / solution / adr），物理上同一目录、逻辑上分属 L1 与 L2。

---

## 根文件模板

### README.md

```markdown
# 知识库

> 双受众入口：顶部给 AI 检索，底部给人类阅读。

## AI 快速导航
- 术语查询 → glossary/（L1）
- 系统架构/方案/决策 → design/（L1/L2，type: architecture|solution|adr）
- 业务流程与业务规则 → flows/（L2）
- 反向示例 / 问题汇总 / 故障复盘 → case/（L2）
- 测试知识/经验/规则 → tests/（L2，`ask test` 单点聚合，供 QA Agent 消费）
- 需求文档 → requirements/（L1）
- 接口约定 → apis/（L3）
- 数据模型/存储 → db/（L3）
- 运维手册 → ops/（L3）

## 人类阅读指引

新人入职先读 glossary/ 和 design/architecture-*；日常通过 `/knowledge-wiki ask` 查询；
易踩坑场景与历史教训沉淀在 case/。
```

### CLAUDE.md

```markdown
# AI 协作契约

## 黄金原则
1. 所有知识必须有 sources 字段，无来源不写
2. 术语唯一锚点在 glossary/，其他文档用 [[slug]] 引用，不重复定义
3. AI 禁止修改 status: canonical 的文档
4. AI 写入一律放入对应目录，不新建目录结构
5. 渐进式加载：按 L1 → L2 → L3 阶段按需加载，不一次性暴露所有细节

## 禁止行为
- 引用 status: deprecated 的文档
- 在非 glossary/ 目录重复定义已有术语
- 在 SKILL 文档外内联生成 hook 脚本（必须复制 references/scripts/）

## 检索优先级
canonical > active > draft > deprecated（deprecated 禁引用）
```

### AGENTS.md（≤50 行）

```markdown
# 知识库 AI 地图

查询：/knowledge-wiki ask "<问题>"
录入：/knowledge-wiki in <内容>
维护：/knowledge-wiki health

## 知识分层
L1（领域）glossary/ design/(architecture|adr) requirements/
L2（执行）flows/ case/ design/(solution) tests/
L3（能力）apis/ db/ ops/

## 检索优先级
canonical > active > draft > deprecated（禁引用）

## 写入规则
新内容 → 对应目录，status: draft → 人工 /knowledge-wiki health audit 升级
术语 → 必须在 glossary/ 中唯一定义
```

### .sources.yaml

```yaml
sources: []
# 通过 /knowledge-wiki in source add <url> 添加，结构：
#   - id: print-api-doc
#     name: 打印接口文档
#     url: https://docs.apipost.net/docs/detail/xxx
#     tracked_by: "@alice"
#     last_hash: ""
#     last_synced: ""
#     status: active           # active | stale | error
#     related_docs:
#       - apis/print-api.md
```

---

## 创建顺序（init Step 1-2 内部使用）

1. 在仓库根 `mkdir -p .knowledge/{glossary,design,requirements,flows,apis,db,ops,case,synthesis,tests}`
2. 创建系统目录：`mkdir -p .knowledge/.index .knowledge/.logs/personal .knowledge/.logs/archive`
3. 写入 4 个根文件：README.md / CLAUDE.md / AGENTS.md / .sources.yaml（内容如上）
4. 写入系统配置文件（从模板复制并替换 `${TODAY}` 为当日日期）：
   - `.index/_meta.yaml` ← 模板：`references/templates/_meta.yaml.tpl`
   - `.logs/_config.yaml` ← 模板：`references/templates/_logs_config.yaml.tpl`
   - `.pending-backlinks.yaml` ← 模板：`references/templates/_pending_backlinks.yaml.tpl`
   - `.pending-edges.yaml` ← [Phase 3 新增] 模板：`references/templates/_pending_edges.yaml.tpl`（待人审推断边队列，init 复制就位为空队列 version=1/pending=[]/reviewed_history=[]）
   - `.pending-docs.yaml` ← 初始内容：`pending: []`（docs 子命令暂存用，详见 `references/docs-rules.md`）
5. 创建 10 个空的 idx 文件（从通用模板生成，替换 `${TYPE_DISPLAY}` 和 `${TODAY}`）：
   - 模板：`references/templates/_idx_empty.md.tpl`
   - 10 个实例：glossary / design / requirements / flows / case / test / apis / db / ops / synthesis
   - `${TYPE_DISPLAY}` 映射：glossary→"glossary", design→"design (architecture|solution|adr)", test→"test (env|rules|checklist|experience|data)", 其余→idx 文件名去 `.idx.md`
6. **[Phase 1 新增] 复制派生引擎**（仿既有 hook cp 范式，把引擎脚本复制到派生层）：

   ```bash
   mkdir -p .knowledge/.graph/scripts && cp references/scripts/{graph_build.py,graph_query.py,graph_analyze.py,discover_prefilter.py,explore_questions.py,graph_export.py} .knowledge/.graph/scripts/
   ```

   - **此步非阻断**：uv 缺失或复制失败**只输出 WARNING**，不影响纯文档功能 init 成功——图层是可选叠加（守研究 §7「图层优雅缺席」+ E6 边界）。
   - **不计入 init 的 8 项自我校验**：`.graph/` 缺失不应让 init 校验失败（它不是 init 必需校验项，仅是派生层就位的可选准备）。
   - 复制后即可用 `/knowledge-wiki health graph-build` 调用 `uv run .knowledge/.graph/scripts/graph_build.py --kb-root .knowledge [--full]`；`ask graph`/`ask explain` 调用 `uv run .knowledge/.graph/scripts/graph_query.py <sub> <slug> --kb-root .knowledge`；`health graph` 调用 `uv run .knowledge/.graph/scripts/graph_analyze.py --kb-root .knowledge [--seed 42] [--min-nodes 10]`；`health discover` 调用 `uv run .knowledge/.graph/scripts/discover_prefilter.py --kb-root .knowledge [--min-jaccard 0.30] [--top-n 20] --json`；`health graph` 同批调用 `uv run .knowledge/.graph/scripts/explore_questions.py --kb-root .knowledge [--top-n 10] [--cohesion-threshold 0.40] --json` 生成可探索问题；`health graph export` / `graph export` 调用 `uv run .knowledge/.graph/scripts/graph_export.py --kb-root .knowledge [--html --canvas --graphml] [--include-inferred]`（[Phase 9 新增]，唯一写 `.graph/exports/`，exports/ 目录由 graph_export.py 首次运行 mkdir(exist_ok=True) 创建，不必 init 预建）；删 `.graph/` 即一并删除引擎副本（含 discover_prefilter.py、explore_questions.py、graph_export.py）与 exports/ 产物，零残留回退。

> Step 6 的 `cp references/scripts/graph_build.py` 与既有 hook 复制（`cp references/scripts/{...}.sh .git/hooks/`）同范式。**init 复制步骤的唯一权威描述落点是本文件；SKILL.md 的 init Step 0-4 段不重复展开**（避免编辑面漂移）。

---

## 存量库升级（v2.1.0：为已 init 的知识库补齐 tests/）

> skill 升级到 v2.1.0 后，**已初始化的知识库**（init 于旧版本）需要幂等补齐 tests/ 目录与索引。全部步骤可安全重复执行（幂等），已存在的文件跳过。

```bash
# 1. 创建业务目录（幂等）
mkdir -p .knowledge/tests

# 2. 创建空 idx（若不存在）：从 _idx_empty.md.tpl 生成，
#    替换 ${TYPE_DISPLAY} 为 "test (env|rules|checklist|experience|data)"、${TODAY} 为当日日期
test -f .knowledge/.index/test.idx.md || <从模板生成>

# 3. _meta.yaml 追加 test 索引条目（若缺失）
#    test: {file: test.idx.md, entries: 0, last_updated: 当日}

# 4. 更新根文件导航：README.md AI 快速导航加 tests/ 行；AGENTS.md L2 行加 tests/

# 5. 重拷图谱引擎脚本副本（若 .knowledge/.graph/scripts/ 存在）
cp references/scripts/{graph_build.py,graph_analyze.py,discover_prefilter.py,explore_questions.py,graph_export.py} .knowledge/.graph/scripts/

# 6. 重建索引与图谱
#    /knowledge-wiki health index-rebuild
#    /knowledge-wiki health graph-build --full
```

- 步骤 5-6 仅在图层存在时执行；纯文档库跳过（守 GRAPH-05 零破坏回退）
- 升级后即可 `/knowledge-wiki in <测试知识>` 录入与 `/knowledge-wiki ask test "<模块/场景>"` 消费
