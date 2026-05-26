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

## 目录树（9 个业务目录 + 4 个根文件 + 3 个系统目录）

```
.knowledge/
├── # ===== 根文件（4 个）=====
├── README.md               ← 双受众入口（顶部给 AI，底部给人类）
├── CLAUDE.md               ← AI 协作契约 + 禁止行为 + 黄金原则
├── AGENTS.md               ← AI 地图（≤50 行）
├── .sources.yaml           ← 外部知识源注册表
│
├── # ===== 业务目录（9 个）=====
├── glossary/               ← L1 术语词典（全局唯一锚点，最先写）
├── design/                 ← L1/L2 架构/技术方案/决策（type 字段区分）
├── requirements/           ← L1 需求文档、PRD、验收标准
├── flows/                  ← L2 核心业务流程 SOP（含业务规则与计算逻辑）
├── case/                   ← L2 反向示例 / 问题汇总 / 故障复盘（反例 Use Case）
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
│   ├── apis.idx.md         ←   apis/ 索引
│   ├── db.idx.md           ←   db/ 索引
│   ├── ops.idx.md          ←   ops/ 索引
│   └── synthesis.idx.md    ←   synthesis/ 索引
│
├── .logs/                  ← 操作日志（按人分文件，解决 git 并发冲突）
│   ├── _config.yaml        ←   日志配置（归档阈值/脱敏规则/digest 配置）
│   ├── personal/           ←   每人私有日志（{mis-id}.md）
│   │   ├── hanqiang.md     ←     @hanqiang 的操作记录
│   │   └── ...
│   ├── archive/            ←   归档日志（只读，按季度）
│   │   └── ...
│   └── digest.md           ←   团队聚合摘要（health 自动生成，建议 .gitignore）
│
└── .pending-backlinks.yaml ← 待消费的反向引用队列（backlink 延迟回写缓冲）
```

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
L2（执行）flows/ case/ design/(solution)
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
#     tracked_by: "@hanqiang"
#     last_hash: ""
#     last_synced: ""
#     status: active           # active | stale | error
#     related_docs:
#       - apis/print-api.md
```

---

## 创建顺序（init Step 1-2 内部使用）

1. 在仓库根 `mkdir -p .knowledge/{glossary,design,requirements,flows,apis,db,ops,case,synthesis}`
2. 创建系统目录：`mkdir -p .knowledge/.index .knowledge/.logs/personal .knowledge/.logs/archive`
3. 写入 4 个根文件：README.md / CLAUDE.md / AGENTS.md / .sources.yaml（内容如上）
4. 写入系统配置文件（从模板复制并替换 `${TODAY}` 为当日日期）：
   - `.index/_meta.yaml` ← 模板：`references/templates/_meta.yaml.tpl`
   - `.logs/_config.yaml` ← 模板：`references/templates/_logs_config.yaml.tpl`
   - `.pending-backlinks.yaml` ← 模板：`references/templates/_pending_backlinks.yaml.tpl`
5. 创建 9 个空的 idx 文件（从通用模板生成，替换 `${TYPE_DISPLAY}` 和 `${TODAY}`）：
   - 模板：`references/templates/_idx_empty.md.tpl`
   - 9 个实例：glossary / design / requirements / flows / case / apis / db / ops / synthesis
   - `${TYPE_DISPLAY}` 映射：glossary→"glossary", design→"design (architecture|solution|adr)", 其余→idx 文件名去 `.idx.md`