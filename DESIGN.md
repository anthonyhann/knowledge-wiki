# knowledge-wiki 知识分层体系与架构设计（L1/L2/L3）

> knowledge-wiki skill 工程实现，系统阐述知识分层的设计哲学、目录框架映射与落地路径。

---

## 一、为什么需要知识分层

传统 AI 辅助开发面临一个根本性的认知困境：代码库被文档化为**扁平的文本块**，检索系统只优化语义相似度，却无法区分"决策意图"与"执行事实"的认知边界。

具体表现为 Agent 不知道三件事：

- **这归谁管**（决策路由）——需求应该由哪个服务处理？
- **怎么做**（执行编排）——标准流程是什么？失败怎么办？
- **用什么工具**（原子调用）——接口长什么样？SLA 是多少？

这三个问题混在一起，导致 AI 出码时频繁产生幻觉、方向错误，或者漫无边界地检索相似代码。

> **核心结论**：组织 AI 的瓶颈不在检索精度，而在**认知保真度**——即知识表征的分层能力、健康度标注能力、跨层引用完整性校验能力，以及对"组织不知道什么"的显式建模能力。

---

## 二、L1 / L2 / L3 三层认知架构

> **单一权威源**：每个 type 的 `layer` 字段以 `references/templates/_registry.yaml` 为准；本文件的 L1/L2/L3 映射表是它的概念视图。新增/调整 type 时**必须先改 yaml**，再同步本文档与 `references/ingestion-rules.md` 的映射表，三处保持一致。

### 总览

| 层级 | 别名 | 认知角色 | 核心问题 | 知识对象类型 |
|------|------|----------|----------|-------------|
| **L1 领域层** | 骨架 | 决策 | 这归谁管？能做什么？不能做什么？ | 边界 + 意图 + 状态机 + 协作拓扑 + 业务护栏 |
| **L2 执行层** | 分子 | SOP 编排 | 怎么做？什么顺序？失败怎么办？ | 触发绑定 + 执行步骤 DAG + 分支条件 + 人工节点 |
| **L3 能力层** | 原子 | 工具调用 | 用什么？接口长什么样？SLA 多少？ | 输入参数 + 输出结构 + 协议坐标 + 运行约束 |

---

### L1 — 领域层（骨架）

**认知角色**：决策。回答"这归谁管？能做什么？不能做什么？"

**设计定位**：L1 是整个知识体系的骨架，偏向业务知识和功能描述，与底层技术无强关联。它承诺了能力边界的确定性——一个领域如果 L1 缺失，AI 就无法做正确的决策路由，会把本属于 A 服务的需求错误地分配给 B 服务。

**包含内容**：

- 核心实体定义与业务边界
- 领域状态机（业务对象的生命周期）
- 协作拓扑（服务上下游关系）
- 业务护栏（不能做什么）
- 页面模块及其包含的埋点

**在 knowledge-wiki 中的映射**：

| 目录 | type | 承载的 L1 知识 |
|------|------|---------------|
| `glossary/` | `glossary` | 核心实体定义、术语唯一锚点（全局唯一，禁止在其他目录重复定义） |
| `design/` | `architecture` | 系统架构现状、服务协作拓扑（活文档，持续更新） |
| `design/` | `adr` | 架构决策记录——为什么这样选，业务护栏的来源 |
| `requirements/` | `requirement` | PRD、feature spec、验收标准（业务意图的书面化） |

**实验数据**：在 hic-spec 项目的多仓库扫描实践中，引入 L1 扫描后首次运行即发现 25 个代码子域中 8 个有意义的领域完全未建档——这些是传统代码检索根本触达不到的"组织不知道自己不知道"的盲区。

---

### L2 — 执行层（分子）

**认知角色**：SOP 编排。回答"怎么做？什么顺序？失败怎么办？"

**设计定位**：L2 承载编排确定性和矛盾状态的表征。它描述该领域下的具体能力或标准操作流程，是 L1 业务意图到 L3 原子能力之间的桥梁。**Use Case（典型案例）主要挂载在 L2 的 SOP 上**，作为动态驱动的上下文，帮助 AI 决策是否需要调用 L3 中的具体原子能力。

**包含内容**：

- 触发条件绑定（什么情况下走这个流程）
- 执行步骤 DAG（有向无环图，描述步骤顺序与依赖）
- 分支条件（if/else 的业务语义）
- 人工介入节点（哪些步骤需要人工确认）
- Use Case（从历史 PRD 和 PR 中抽取的典型改造案例）

**在 knowledge-wiki 中的映射**：

| 目录 | type | 承载的 L2 知识 |
|------|------|---------------|
| `flows/` | `flow` | 核心业务流程 SOP、时序图、分支判断逻辑、业务规则与计算公式 |
| `case/` | `case` | 反向示例 / 问题汇总 / 故障复盘（反例 Use Case，驱动 SOP 的防护措施） |
| `design/` | `solution` | 某需求的技术方案（时间点快照，是 L2 的决策记录） |

**Use Case 是成败关键**：如果不提供典型的改造案例，大模型会自行漫无边界地检索相似代码，极易产生幻觉。主动提供结构化的高质量 Use Case 约束，能将 AI 出码可用性从不稳定提升到 80%–90%。

---

### L3 — 能力层（原子）

**认知角色**：原子工具调用。回答"用什么？接口长什么样？SLA 多少？"

**设计定位**：L3 是最细粒度的原子能力，承载执行确定性和 SLA 约束。它涉及具体的技术栈、前后端交互 API、分支判断、通用查询、网络能力、DB 与缓存操作等。

**包含内容**：

- 接口定义（输入参数、输出结构、错误码）
- 协议坐标（服务地址、认证方式）
- 运行约束（超时阈值、限流配置、SLA）
- 数据模型（表结构、索引策略、Redis key 规范）
- 运维手册（告警规则、大促保障配置）

**在 knowledge-wiki 中的映射**：

| 目录 | type | 承载的 L3 知识 |
|------|------|---------------|
| `apis/` | `api` | 接口约定、字段映射、请求响应结构 |
| `db/` | `db` | 数据模型、存储设计、索引策略 |
| `ops/` | `ops` | 运维手册、告警阈值、大促保障、超时配置 |

---

## 三、目录框架完整映射表

> **目录树、目录职责速查、layer/type 完整映射表**统一维护在 [`references/directory-structure.md`](./references/directory-structure.md)（单一权威源）。本节不重复展开，避免漂移。
>
> 简略对应关系（详细见单一权威源「目录与 type 完整映射表」）：
>
> - **L1 领域层** → `glossary/`（glossary）、`design/`（architecture / adr）、`requirements/`（requirement）
> - **L2 执行层** → `flows/`（flow）、`case/`（case）、`design/`（solution）
> - **L3 能力层** → `apis/`（api）、`db/`（db）、`ops/`（ops）

---

## 四、三层体系解决的典型问题

### 问题一：AI 出码时术语对不齐，前后端语义割裂

**场景**：前端叫"动线区块"，后端接口叫 `section_module`，AI 在跨仓开发时无法建立映射，频繁产生幻觉。

**解法**：`glossary/` 是全局唯一锚点。录入 `dong-xian-qu-kuai.md` 并在 frontmatter 中同时标注业务名称和技术字段名，所有其他文档通过 `[[dong-xian-qu-kuai]]` 引用。AI 检索时自动获得完整的语义映射，不再猜测。

**对应层级**：L1 `glossary/`

---

### 问题二：业务规则散落在代码注释和口口相传中，AI 无法感知

**场景**："小费在配送完成后 T+1 结算，但如果配送商是自营则实时结算"——这类规则通常只存在于老员工的记忆里。AI 生成结算代码时按通用逻辑处理，产生错误。

**解法**：将这类业务规则作为「计算/判断逻辑」章节录入 `flows/`（例如 `flows/tip-settlement.md`）。AI 在生成结算相关代码时会检索到该流程文档并遵守其中的规则分支，避免按通用逻辑生成错误代码。

**对应层级**：L2 `flows/`（业务规则与业务流程同层级维护）

---

### 问题三：故障重复发生，历史教训无法沉淀给 AI

**场景**：配送队列堆积事故已发生过两次，但每次 AI 生成消费者代码时都不会主动加入防护措施。

**解法**：`case/` 不仅存储故障复盘，还包括反例代码、踩坑总结、问题汇总等反向示例，作为 Use Case 挂载在 L2 的 SOP 上。当 AI 下次处理类似场景时，会检索到历史案例记录，主动在方案中加入防护措施与反例规避。

**对应层级**：L2 Use Case `case/`

---

### 问题四：跨仓开发时 AI 识别服务准确率低

**场景**：需求涉及 11 个 API、8 个后端服务、跨 13 个仓库，AI 仅依赖代码仓库时识别服务准确率低且不稳定。

**解法**：构建极简版领域知识库（4 个核心文件）：领域术语表（`glossary/`）、服务角色说明（`design/architecture`）、领域能力边界（`design/adr`）、典型改造案例（`case/` + `flows/`）。渐进式匹配流程：输入需求 → 匹配领域术语 → 定位领域能力 → 匹配典型案例 → 产出概要设计 → 人工 Review → 出码。代码可用性达 80%–90%。

**对应层级**：L1 + L2 协同

---

### 问题五：知识腐烂，文档与代码现实脱节

**场景**：接口文档更新了，但知识库里的 `apis/` 还是旧版本，AI 按旧接口生成代码导致联调失败。

**解法**：`health rot` 通过 `expires` 字段扫描过期文档；`health scan` 追踪 `.sources.yaml` 中注册的外部源（飞书文档、ApiPost 接口文档）是否有变更，diff 出变更后提示人工决策是否同步，不自动覆盖。

**对应层级**：L3 `apis/` / `db/` + `health` 维护机制

---

## 五、知识渐进式加载原则

不要一次性暴露所有细节知识，按阶段按需加载，减少大模型上下文干扰：

```
阶段 1：先定业务能力（L1）
  → 匹配领域术语（glossary/）
  → 确认服务归属（design/architecture）

阶段 2：再定执行方案（L2）
  → 匹配业务流程与业务规则（flows/）
  → 检索典型案例与反例（case/）

阶段 3：最后调用原子能力（L3）
  → 查接口约定（apis/）
  → 查数据模型（db/）
  → 查运维配置（ops/）
```

---

## 六、知识保鲜与反馈闭环

### 文档生命周期

每篇知识文档有四个状态，形成从录入到废弃的完整生命周期：

| status | 含义 | AI 行为 | 升级方式 |
|--------|------|---------|---------|
| `draft` | 草稿，待确认 | 可参考，不作决策依据 | `/knowledge-wiki health audit <slug>` |
| `active` | 正式有效 | 正常检索引用 | 长期验证后人工升级 |
| `canonical` | 权威锁定 | 最高优先级，AI 禁止修改 | 人工标记 |
| `deprecated` | 已废弃 | 禁止引用 | `/knowledge-wiki health deprecate <slug>` |

检索优先级：`canonical > active > draft > deprecated`（deprecated 禁止引用）

### 健康维护子命令

| 子命令 | 触发时机 | 行为 |
|--------|---------|------|
| `health rot` | 定期或 pre-push 时 | 扫描 `expires` 字段，列出 EXPIRED / WARNING 文档，批量决策入口 |
| `health scan` | 外部源可能有更新时 | 遍历 `.sources.yaml`，diff 内容变更，提示人工决策是否同步 |
| `health coverage` | 新模块上线后 | 扫描项目顶层目录，比对 `.knowledge/` tags，输出未覆盖模块 |
| `health audit <slug>` | 人工确认某篇文档仍有效 | status → active；expires 按 type 分支：glossary/adr 保持 never，其他按 `_registry.yaml.expires_days` 续期 |
| `health deprecate <slug>` | 文档已过时 | rg 查所有引用 → 确认后 status → deprecated，引用处追加注释 |

### AIDLC 反馈闭环

从产品提需求到最终交付，所有过程数据（对话、PR 分析、代码 diff）都上报，经归因分析后沉淀为 Use Case，挂载到 L2 的 SOP 上，驱动知识体系的持续迭代：

```
需求输入
  → AI 出码（消费 L1/L2/L3 知识）
  → 代码 Review / 联调
  → PR 合并（触发 commit-msg hook，提示知识更新）
  → 故障/复盘/反例（录入 case/，更新 flows/）
  → 知识库健康检查（health rot / scan）
  → 知识升级（audit → active → canonical）
  → 下一次需求输入（更高质量的知识驱动）
```

---

## 七、落地步骤

**Step 1：初始化**

```bash
cd ~/your-project
/knowledge-wiki init
# → 自动检查工具依赖（rg / git / 浏览器工具）
# → 创建 11 个目录 + 4 个根文件
# → 安装 git hooks（pre-push + commit-msg）
```

**Step 2：优先建设 glossary（L1 地基）**

把团队内所有容易混淆的业务术语先录入，这是整个体系的地基：

```bash
/knowledge-wiki in "配送单是指商家通过平台发起的配送请求，对应数据库字段 delivery_order_id"
# → AI 自动推断 type: glossary
# → 加载 references/templates/glossary.md 作为正文骨架
# → 保证生成的 .knowledge/glossary/pei-song-dan.md 含同义词表、技术字段映射、使用场景、边界说明
```

**Step 3：按需录入，不追求一次完整**

遇到业务流程与业务规则录 `flows/`，遇到故障/反例/踩坑总结录 `case/`，遇到接口约定录 `apis/`，遇到表结构录 `db/`。新录入一律 `draft`，经人工 audit 后升级为 `active`：

```bash
/knowledge-wiki in https://xxx.feishu.cn/docx/xxx          # 飞书文档（走浏览器自动化）
/knowledge-wiki in ./docs/delivery-flow.md                  # 本地文件
/knowledge-wiki in "小费计算规则：配送完成后 T+1 结算..."   # 手工录入
```

**Step 4：注册外部知识源**

```bash
/knowledge-wiki in source add https://docs.apipost.net/docs/detail/xxx --name 配送接口文档
# → 写入 .sources.yaml，后续 health scan 自动追踪变更
```

**Step 5：日常通过 ask 消费知识**

```bash
/knowledge-wiki ask "配送超时阈值是多少"
# → 返回带来源、录入人、时效状态的标准回答
# → 如果返回"知识库无记录"，说明这块知识还没有沉淀，需要补录
```

**Step 6：定期维护**

```bash
/knowledge-wiki health        # 综合健康报告
/knowledge-wiki health rot    # 查看过期文档
/knowledge-wiki health scan   # 检查外部源变更
```

---

## 八、核心约束（铁律）

1. **无来源不写、不答** — `sources` 必填；`ask` 无知识库记录时明确告知，不用模型训练知识填补
2. **术语唯一** — 术语定义锚点在 `glossary/`，其他文档用 `[[slug]]` 引用，不重复定义
3. **草稿优先** — 新录入一律 `status: draft`，由 `health audit` 人工升级，不跳过确认
4. **按域名路由浏览器自动化** — 内部文档 URL 按域名路由到浏览器工具，未装时强制提示安装
5. **deprecate 必处理引用** — 废弃文档前用 rg 找出所有引用处，防止悬空链接
6. **前后端同库** — 同一业务领域的前后端知识放在同一个库中联合维护，避免语义割裂
7. **渐进式加载** — 按 L1 → L2 → L3 阶段按需加载，不一次性暴露所有细节
8. **模板为合约** — 录入正文严格按 `references/templates/{type}.md` 骨架生成；AI 不允许自行增删一级标题，必填段不齐时 8.5 门禁拦截

---

## 九、模板库机制（与 GSD 可类比的合约化产出）

### 为什么需要 type 级模板库

早期设计中，所有 type 共享一套「TL;DR + 详情」二段式。在落地中遇到三个问题：

- **glossary** 缺少同义词 / 技术字段名映射 → 前后端语义仍割裂
- **case**（反向示例 / 故障复盘）缺少时间线 / 5 Whys 根因 / 改进措施责任人 / 反例代码 → Use Case 无法反哺 AI
- **api** 缺少请求/响应字段表 / 错误码 / 超时限流 → AI 生代码时仍需重新推导

参考 GSD 的 **Artifact Taxonomy**（制品分类法，40+ 个模板覆盖不同阶段产出），knowledge-wiki 从 v下一版起按 type 提供专属骨架。

### 模板库的三个核心原件

```
references/templates/
├── _registry.yaml          ← 中央注册表：type → 文件 + 必填段 + 质量门禁 + 层级 + expires_days
├── glossary.md           ← 各 type 专属模板（含 synthesis 共 9 个），顶部 HTML 注释声明：
├── architecture.md             • 必填段
├── solution.md                 • 质量门禁
├── adr.md                      • 填写指南
├── requirement.md
├── flow.md
├── api.md
├── db.md
├── ops.md
└── case.md
```

### AI 选择模板的伪代码

```
1. type = infer_type(content)              # 12 级优先级推断
2. tpl  = registry.templates[type]         # 从 _registry.yaml 加载
3. body = render(tpl.file, content)        # 按模板骨架整理正文
4. validate(body, tpl.required_sections,   # 8.5 门禁
             tpl.quality_gate)
5. 不达标 → 返回用户 “缺失段：xxx” → 中止写入
6. 达标 → write(.knowledge/{tpl.target_dir}/{slug}.md)
```

### 与 GSD 模板体系的对应关系

| 维度 | GSD | knowledge-wiki |
|------|-----|---------------|
| 模板表形式 | XML 标签 + YAML frontmatter | HTML 注释 + Markdown 骨架 |
| 中央注册表 | `references/artifact-types.md` | `references/templates/_registry.yaml` |
| 质量门禁 | `must_haves` (truths/artifacts/key_links) | `required_sections` + `quality_gate` |
| 填写指南 | `<guidelines>` + `<anti-patterns>` | 顶部 HTML 注释 |
| 选择机制 | Workflow 动态路由下多个模板 | type 推断 → 注册表查查 → 唯一模板 |

### 新增 type 的标准流程

1. 在 `references/templates/_registry.yaml` 登记新条目（含 `required_sections` / `quality_gate` / `expires_days` / `target_dir` / `layer`）
2. 创建 `references/templates/{type}.md`，顶部 HTML 注释明确必填段与填写指南
3. 同步更新：
   - `references/ingestion-rules.md` 「type 推断规则」表与「type 映射表」
   - `SKILL.md` 资源索引表
   - `DESIGN.md` 本节（如变动影响层级归属）
4. CHANGELOG 中记录变更

---

*文档来源：knowledge-wiki skill references/ + GSD Artifact Taxonomy 参考*