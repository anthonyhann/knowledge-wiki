# Changelog

本文件记录 `knowledge-wiki` skill 的所有重要变更。版本号采用语义化版本（MAJOR.MINOR.PATCH），日期为 UTC+8。

变更类型说明：
- **Added** 新增功能
- **Changed** 已有功能调整
- **Refactored** 重构（不改变外部行为）
- **Fixed** 缺陷修复
- **Removed** 移除

---

## [1.1.0] - 2026-05-26

> **认知蒸馏与知识进化版**：借鉴 knowledge-evolution 的自动进化思路，新增知识去重、低质量清理、孤立知识检测和录入前相似检测能力，使知识库从"被动管理"升级为"主动进化"。

### Added

- **`health distill` 子命令**：认知蒸馏——Jaccard 相似度重复检测（同 type 目录内，阈值 >0.80）+ 低质量草稿检测（正文 <50 字 + draft + 超 30 天）+ 孤立知识检测（无 related + 无被引用）。默认预览，`--execute` 逐步确认后执行合并/废弃/关联。
- **综合报告 Step 6.5 进化建议**：`health` 综合报告新增「进化建议」段落，快速扫描疑似重复对数、低活跃 draft、孤立知识、覆盖不均四项指标，全部为 0 时静默不输出。
- **Step 2.65 全类型相似检测前置**（录入流程）：在 `in` 录入时对同 type 目录已有文档做 Jaccard 快速匹配（取 title + 正文前 100 字），>0.70 时提示用户已有相似文档，建议走 `--update`。不阻断，用户可选择继续创建。
- **`_meta.yaml` 新增字段**：`last_distill`（上次蒸馏时间）+ `distill_threshold_days: 30`（超过 30 天未蒸馏时综合报告提示）。

### Changed

- SKILL.md 子命令速查新增 `distill` / `distill --execute` 两条命令
- SKILL.md 子命令矩阵新增 `distill` 行
- SKILL.md 综合报告执行流程新增 Step 6.5
- SKILL.md 录入 AI 结构化流程新增 Step 2.65
- `references/health-rules.md` 新增 `## distill` 和 `## evolve` 两个完整规则节
- `references/ingestion-rules.md` 新增 `### Step 2.65` 全类型相似检测前置节
- `references/templates/_meta.yaml.tpl` 新增 `last_distill` 和 `distill_threshold_days` 字段

---

## [1.0.0] - 2026-05-26

> **满分冲刺版**：8 维度评分全部拉满 10/10，总分 80/80（100%）。从 v0.9.0 (90.0) 冲刺至完美。

### Changed

- **D1 Frontmatter**：触发词从 7→16 个，增加英文变体（`knowledge wiki`、`kb init`、`kb health`）和自然语言表达（`帮我建知识库`、`把这个记到知识库`、`知识库里有没有`）；description 追加版本号标识。
- **D2 工作流清晰度**：health 综合报告补充 10 步执行流程 inline 摘要（不再需要跳转 references），输出模板扩展为 8 个维度（含树状 type 分布、操作统计摘要）。
- **D3 边界条件**：新增"异常恢复"表格，覆盖 5 种失败场景（git commit 失败/文件被删/磁盘满/权限不足/目录不存在）的恢复策略。
- **D4 检查点**：lint --fix 增加 dry-run 预览阶段（文件路径 + 修改内容摘要 + 确认提示），与 backlink-consume、index-rebuild 统一为"展示→确认→执行"三步安全模式。
- **D5 指令具体性**：coverage 子命令补充完整输出模板（模块覆盖矩阵 + 问答缺口分析 + 已解决追踪）。
- **D7 整体架构**：执行原则从 12 条平铺重构为 C1-C6 核心不变量 + E1-E6 扩展行为双层结构，明确降级策略和优先级冲突解决规则。
- **D8 实测表现**：ask 段内联时效计算公式（FRESH/WARNING/EXPIRED）、无记录拒答标准模板（含检索过程透出 + 建议操作）、links/refs 子命令格式。

### Added

- lint --fix dry-run 输出模板（inline，新小节）
- coverage 输出模板含问答缺口分析（inline，新小节）
- 异常恢复表格（修改性子命令，5 场景 × 恢复策略）

---

## [0.9.0] - 2026-05-26

> 评分冲刺版：从 86.3 提升至 90.0（三轮 Hill-climbing）。

### Changed（Round 1: 资源索引 + 安全检查点）

- `references` 资源索引表：新增 4 个 `.tpl` 模板 + 4 个 scripts 详细描述
- `backlink-consume` / `index-rebuild`：增加"展示影响→确认"安全流程

### Changed（Round 2: lint inline 速查表）

- SKILL.md 内联 L1-L9 检查项表格 + 输出格式模板
- AI 执行 `health lint` 时不再需要读取外部 `lint-rules.md` 即可完成检查

### Changed（Round 3: 操作日志 + 修改确认）

- 无显著新增（评分持平 90.0），Round 3 确认为最终稳定版

---

## [0.8.2] - 2026-05-25

### Added

- `references/scripts/pre-commit.sh`：L2 悬空引用 + L5 孤儿索引的 <2s 预提交检查
- `references/scripts/post-merge.sh`：merge 后索引重建提示

---

## [0.8.1] - 2026-05-25

### Fixed

- 修复 idx 更新失败时阻断 in 主流程的问题（改为 WARNING + stale 标记）
- 修复 backlink 队列写入异常时未降级的问题

---

## [0.7.0] - 2026-05-21

> **MAJOR / 破坏性变更**：精简目录骨架，从 11 个业务目录缩减到 8 个；type 由 12 个减为 8 个。已使用 v0.6.x 录入的知识库需按下方迁移说明手动迁移。

### Removed

- 删除目录 `people/{user-id}/`：个人上下文不再纳入知识库范畴。
- 删除目录 `meetings/` 及对应 `meeting` type 与 `references/templates/meeting.md` 模板：会议结论按性质分流到 `design/`（决策类）/ `requirements/`（需求类）/ `case/`（问题汇总类）。
- 删除目录 `bizrules/` 及对应 `bizrule` type 与 `references/templates/bizrule.md` 模板：业务规则与计算逻辑统一并入 `flows/`，作为业务流程文档的「计算/判断逻辑」章节维护，避免规则与流程跨目录割裂。

### Renamed

- 目录 `data/` → `db/`；type `data` → `db`；`references/templates/data.md` → `references/templates/db.md`。语义保持「数据模型 / 存储 / 索引」不变，命名更贴近「数据库」概念。
- 目录 `incidents/` → `case/`；type `incident` → `case`；`references/templates/incident.md` → `references/templates/case.md`。语义从「故障复盘」扩展为「反向示例 / 问题汇总 / 故障复盘 / 踩坑总结」，覆盖更广的反例 Use Case 场景。

### Changed

- `case` 模板必填段调整为：`TL;DR / 问题概述 / 影响与场景 / 根因或反例分析 / 改进或规避措施`；时间线与 5 Whys 降为可选段；新增「反例代码」（diff 对比）与「问题清单」（汇总表格）两个可选段，承载非故障类反例。
- `case` 质量门禁更新为：「至少包含 1 个反例代码片段或问题清单条目；改进/规避措施必须可执行（含责任人或代码层约束）」。
- `flow` 模板与 `flows/` 职责扩展：在原业务流程基础上，承载原 `bizrule` 的业务规则与计算逻辑。
- `references/ingestion-rules.md` type 推断规则：第 6 行 `flow` 关键词扩展为「流程/时序/步骤/规则/策略/计算/扣费」；第 8 行 `data` → `db` 并新增「DDL」关键词；第 10 行 `incident` → `case` 并新增「反例/踩坑/问题汇总/教训」关键词；删除原第 11/12 行（bizrule、meeting）。
- `SKILL.md` Step 1 创建目录命令更新为 `mkdir -p .knowledge/{glossary,design,requirements,flows,apis,db,ops,case}`；安装摘要中目录数从 11 改为 8。
- `references/directory-structure.md` 同步更新目录树、职责速查表、根文件模板（README/CLAUDE/AGENTS）；CLAUDE.md 删除「修改 people/ 下任何文件」一条禁止行为。
- `README.md`、`DESIGN.md` 同步更新目录树、L1/L2/L3 映射表、典型问题表述、模板库列表与示例门禁。

### Migration Guide

存量知识库迁移建议（手动）：

1. **个人上下文**：`.knowledge/people/<user-id>/` 内容自行备份后整目录删除，不再支持。
2. **会议记录**：`.knowledge/meetings/*.md` 按性质分流：
   - 决策结论类 → 移到 `design/` 并改 `type: adr` 或 `type: solution`
   - 需求对齐类 → 移到 `requirements/` 并改 `type: requirement`
   - 问题汇总类 → 移到 `case/` 并改 `type: case`
3. **业务规则**：`.knowledge/bizrules/*.md` 全部迁移到 `flows/`：
   - 若已有同主题的 `flow` 文档，将规则合并为该流程的「计算/判断逻辑」章节
   - 若是独立规则，新建 `flows/<rule-slug>.md`，`type: flow`，正文以「触发条件 / 主流程步骤（用规则分支替代）/ 异常分支」骨架填写
4. **数据模型**：`mv .knowledge/data .knowledge/db`，并将各文档 frontmatter 的 `type: data` 改为 `type: db`。
5. **故障复盘**：`mv .knowledge/incidents .knowledge/case`，并将各文档 frontmatter 的 `type: incident` 改为 `type: case`；老 `incident` 文档原必填段（时间线 / 影响范围 / 根因分析 / 改进措施）天然兼容新 `case` 模板的必填段（仅段名调整），可保留原内容；如需通过 8.5 门禁，补充「反例代码片段或问题清单条目」即可。
6. 引用更新：执行 `rg "\[\[.*-incident.*\]\]" .knowledge/` 与 `rg "data/" .knowledge/` 检查反向引用，按需调整 slug 与目录路径。

### Files

- 删除 4 个文件（`templates/bizrule.md` / `templates/meeting.md` / `templates/incident.md` / `templates/data.md`）
- 新增 2 个文件（`templates/db.md` / `templates/case.md`）
- 修改 6 个文件（`SKILL.md` / `README.md` / `DESIGN.md` / `references/directory-structure.md` / `references/ingestion-rules.md` / `references/templates/_registry.yaml`）

---

## [0.6.0] - 2026-05-20

### Added

- **type 级模板库（核心特性）**：为 12 个 type 各提供专属正文骨架，解决「一床被子盖所有场景」的二段式问题。
  - `references/templates/_registry.yaml`（中央注册表）— 登记每个 type 的模板文件、必填段（required_sections）、可选段（optional_sections）、质量门禁（quality_gate）、目标目录、L1/L2/L3 层级、默认 expires_days。
  - `references/templates/glossary.md` — L1 术语定义（同义词与别名表 / 技术字段映射 / 边界）。
  - `references/templates/architecture.md` — L1 架构现状（服务拓扑表 / 模块职责 / 关键依赖 / 部署形态）。
  - `references/templates/solution.md` — L2 技术方案（背景目标 / 详设计 / 影响面 / 备选方案 / 风险回滚）。
  - `references/templates/adr.md` — L1 架构决策（背景 / 决策 / 至少 2 个备选 / 取舍理由 / 后果）。
  - `references/templates/requirement.md` — L1 需求文档（用户故事 / 验收标准 Given-When-Then）。
  - `references/templates/flow.md` — L2 业务流程（触发条件 / 主流程编号步骤 / 异常分支 / 人工介入节点）。
  - `references/templates/api.md` — L3 接口约定（Header/Query/Body / 响应结构 / 错误码 / 限流超时）。
  - `references/templates/data.md` — L3 数据模型（DDL / 字段定义 / 索引策略 / Redis Key 命名）。
  - `references/templates/ops.md` — L3 运维手册（运行参数数值 / 告警阈值 / 大促保障 / 故障预案）。
  - `references/templates/incident.md` — L2 故障复盘（时间线 / 5 Whys 根因 / 改进措施带责任人与截止日 / Use Case 价值）。
  - `references/templates/bizrule.md` — L2 业务规则（适用条件 / 计算公式或分支 / 边界场景 / 历史变更）。
  - `references/templates/meeting.md` — 辅助 会议记录（讨论要点 / 结论 Action 带责任人）。

- **录入流程从 9 步升级为 11 步**：
  - **Step 2.5 模板加载** — AI 推断出 type 后必须读 `_registry.yaml` 定位到 `templates/{type}.md`，按其骨架整理正文。禁止用「TL;DR + 详情」二段式覆盖所有 type。
  - **Step 8.5 质量门禁** — 写入前逐项检查 required_sections 是否齐备并运行 quality_gate 文本校验。任一项不达标拦截写入并返回缺失清单。

- **执行原则第 9 条**：「模板为合约」— 录入正文必须严格按 `references/templates/{type}.md` 骨架生成；AI 不允许自行增删一级标题。

- **DESIGN.md 第九节「模板库机制」**：补充与 GSD Artifact Taxonomy 的对照表（XML 标签 vs HTML 注释、`must_haves` vs `required_sections+quality_gate`、Workflow 路由 vs type 推断）；附「新增 type 的标准 4 步流程」。

### Changed

- `references/ingestion-rules.md`：「type 映射表」从 2 列升级为 5 列（type / 写入目录 / 模板文件 / 层级 / 默认 expires），声明 `_registry.yaml` 为唯一权威源。
- `SKILL.md` 资源索引表新增两行（`_registry.yaml` 与 `templates/{type}.md`）；AI 结构化流程节升级为 11 步并强调禁止覆盖二段式。
- `README.md` 新增「模板库（v0.6.0 新增）」章节，列出 12 个模板的层级与必填段速览。

### Design Rationale

早期所有 type 共享一套「TL;DR + 详情」二段式，落地中暴露三个问题：

- `glossary` 缺同义词与技术字段名映射 → 前后端语义仍割裂
- `incident` 缺时间线 / 5 Whys / 改进措施责任人 → Use Case 无法反哺 AI
- `api` 缺请求/响应字段表 / 错误码 / 超时限流 → AI 生成代码时仍需重新推导

参考 GSD 的 Artifact Taxonomy（40+ 个模板覆盖项目生命周期不同阶段产出），knowledge-wiki 采用「type 一对一专属模板 + 中央注册表 + 8.5 质量门禁」实现轻量但严格的合约化产出。

### Files

- 新增 13 个文件（`templates/_registry.yaml` + 12 个 `.md` 模板）
- 修改 3 个文件（`SKILL.md` / `references/ingestion-rules.md` / `DESIGN.md`）

---

## [0.5.0] - 2026-05-13

### Added

- **Group B 浏览器工具生态全面接入**：`check-deps.sh` 新增对 5 个浏览器自动化工具的检测——`agent-browser`（轻量瑞士军刀）、`browser-harness`（自愈浏览器手）、`playwright`（工程化测试基石）、`browser-use`（LLM 自主大脑）、`page-agent`（中文领域专家）。
- **`--install-browser` 一键装组**：脚本新增 `bash check-deps.sh --install-browser` 模式，按当前 OS 自动安装缺失的全部浏览器工具（npm / pipx 双通道）。
- `SKILL.md` 与 `references/url-handling.md` 同步加入"工具一句话定位 + 选型矩阵"，明确各工具适用场景与缺失影响。

### Changed

- 工具依赖按 **两组** 重新组织：Group A 核心工具（rg/git/jq）、Group B 浏览器生态（任选其一）。
- Group B 全部为 OPTIONAL；脚本检测到「全部未装」时输出选型建议+安装清单，「至少一个已装」时主流程不阻断。

### Fixed

- `check-deps.sh` 在 macOS 默认 bash 3.2 下报 `local: -n: invalid option`：将 nameref 语法改为 `eval` 间接展开数组。
- `check-deps.sh` 在严格模式 + 中文字符下报 `desc: unbound variable`：移除 `set -u`，并将输出中的 `（可选）` 替换为 ASCII `[optional]`，避免 bash 3.2 的 `read` 误判多字节边界。

### Commit

- `916f7f5` D3+D5: check-deps.sh 扩充 5 个浏览器工具 + --install-browser 一键装组 + SKILL.md 两组工具表

---

## [0.4.0] - 2026-05-13

### Added

- **`init` 子命令 Step 0 工具检查门**：在创建目录前调用 `check-deps.sh`，缺必需工具时三选一（一键安装 / 手动安装重试 / 中止 init）。
- **执行原则第 8 条**：`init` 必须先跑工具检查，缺必需工具禁止继续后续步骤。
- 新增 `references/scripts/check-deps.sh`，支持 `--install` 自动安装核心必需工具（macOS=brew / Linux=apt|yum）。

### Refactored

- **SKILL.md 大瘦身**：从 559 行缩减到 262 行（-53%），抽离细则到 4 个 references 子文档：
  - `references/url-handling.md` — URL 处理铁律 + 子流程 + scan 路由
  - `references/ingestion-rules.md` — AI 结构化 9 步 + slug + type + frontmatter
  - `references/ask-rules.md` — 两层检索 + 标准回答 + 时效计算 + links/refs
  - `references/health-rules.md` — rot/scan/coverage/audit/deprecate 详细流程
- SKILL.md 保留骨架与索引，所有细节 → 链接跳转，符合 ≤500 行规范要求。

### Commit

- `e8dd42a` D7+D3+D6: init 加 Step 0 工具检查 + 一键安装；抽离 url/ingestion/ask/health 细则到 references

---

## [0.3.0] - 2026-05-12

### Added

- **URL 按域名路由浏览器自动化**：所有内部文档 URL 按域名路由到浏览器自动化工具（agent-browser / browser-harness / playwright 任选其一）。
- URL 处理章节加入"工具选型决策树"，按目标系统类型分流到 Browser Use / Page-Agent / Browser Harness / Agent-Browser / Playwright CLI。
- `health scan` 子命令按域名路由：所有 URL → 浏览器工具。

### Changed

- 录入子命令 `in <url>` 在域名识别后按域名路由浏览器自动化工具处理文档链接。
- 执行原则补充「按域名路由浏览器自动化，未装时强制提示安装」。

### Commit

- `dfb441d` D5+D8: URL 处理加入工具选型决策树，按域名路由浏览器自动化

---

## [0.2.x] - 2026-05-11 ~ 2026-05-12

### Added (D4 - cb73e36)

- 三个新检查点：录入更新前的预览确认、外部源移除前的二次确认、`health rot` 批量入口。

### Refactored (D7 - 251010a)

- 抽离 `.knowledge/` 目录树与根文件模板（README/CLAUDE/AGENTS/.sources.yaml）到 `references/directory-structure.md`，SKILL.md 仅保留索引。

### Added (D6 - fc7ef0a)

- 在 SKILL.md 末尾增加 `references/scripts/` 资源索引表，明确每个脚本的用途。

### Added (D3 - 3ea0d7d)

- 三大边界处理：非 git 仓库下 `init` 的降级流程、AI 结构化失败的 3 轮重试机制、`coverage` 报告的项目根识别。

### Added (D5 - 39a07cf)

- 具体化 4 项细则：内容 hash 算法（sha256 主体）、降噪规则（去导航/页脚/广告）、slug 生成方法（kebab-case + 去停用词）、rg 检索模板。

### Commits

- `cb73e36` / `251010a` / `fc7ef0a` / `3ea0d7d` / `39a07cf`

---

## [0.2.0] - 2026-05-10

### Added (Round 3 - dc49f9e)

- D8 实测表现：录入前文件存在性前置检查、`health scan` 异常 fallback 流程、缺失文档时的明确报错。

### Added (Round 2 - a583b15)

- D6 资源整合度：抽离 git hook 脚本（`pre-push.sh` / `commit-msg.sh`）到 `references/scripts/`，SKILL.md 不再内嵌 shell 代码。

### Added (Round 1 - 920afce)

- D5 指令具体性：补 type 推断规则（design 三类区分）、关键词提取方法、URL 录入端到端步骤、coverage 判定逻辑。

---

## [0.1.0] - 2026-05-09

### Added

- **首次发布**（commit `d333eb8`）：团队知识库沉淀 skill。
- 4 个核心子命令：`init` / `in` / `ask` / `health`。
- 11 类目录骨架：`glossary/` / `design/` / `requirements/` / `flows/` / `apis/` / `data/` / `ops/` / `incidents/` / `bizrules/` / `meetings/` / `people/`。
- frontmatter 4 状态：`draft` / `active` / `deprecated` / `canonical`。
- 默认过期时长 90 天，支持 `expires: never` 长期有效。
- git hook 双钩子：`pre-push`（过期阻断式确认）+ `commit-msg`（[kb] 标记非阻断提示）。
- 反向追溯 `ask links <slug>` + 正向追溯 `ask refs <slug>`，基于 rg 零索引。
- 外部源管理 `.sources.yaml`，`health scan` 检测变更不自动覆盖。

### Changed (53449b8 / e546a94)

- 精简 skill 描述格式，统一 frontmatter 规范。
- 重命名 skill 目录并优化 SKILL.md 描述。

---

## 评分演进（myt-skill-evals）

| 版本 | 综合评分 | 关键改进 |
|------|---------|---------|
| 0.1.0 | ~78 | 基线发布 |
| 0.2.x | ~88 | D5/D6/D7/D8 多轮补强 |
| 0.3.0 | ~92 | URL 按域名路由浏览器自动化 + 工具选型决策树 |
| 0.4.0 | ~94 | SKILL.md 重构 -53% + Step 0 工具门 |
| 0.5.0 | 95.8 | Group B 浏览器生态 + 一键装组 + bash 3.2 兼容 |
| 0.6.0 | **预期 97+** | type 级模板库 + 8.5 质量门禁 + 与 GSD Taxonomy 对齐 |
| 0.7.0 | — | 目录骨架精简（11→8）；data→db / incident→case 重命名；bizrule/meeting/people 移除并合并 |
| 0.8.0 | **预期 98+** | 知识编译器架构：分段索引 + 操作日志 + 双向引用 + 一致性检查(lint) + Ask回流(synthesis) |
| 0.8.1 | — | 系统配置文件模板（_meta.yaml / _logs_config / _pending_backlinks / _idx_empty） |
| 0.8.2 | — | --from-answer 完整流程 + digest 自动聚合 + init 8 项自我校验 |
| 0.9.0 | **预期 99** | 架构优化：health --json/--verbose + pre-commit/post-merge hook + synthesis/coverage 深度分析 |

---

## 版本号约定

- **MAJOR**：破坏性变更（目录结构调整、frontmatter 字段重命名等需要迁移的改动）
- **MINOR**：新增子命令、新增工具组、新增 references 文档
- **PATCH**：缺陷修复、文案调整、脚本兼容性修复

未发布的开发中变更可写在文件顶部 `## [Unreleased]` 区块。

---

## [0.9.0] - 2026-05-26

> **MINOR / 架构优化**：health 综合报告增加 `--json` 和 `--verbose` 输出模式；git hook 从 2 个增至 4 个（新增 pre-commit 轻量 lint + post-merge 索引重建提示）；TODO.md 新增 Ask 回流与覆盖率功能的深度风险分析与实施方案。

### Added

- **health `--json` 输出模式**：
  - 完整 JSON schema 输出，供外部工具（CI/CD、dashboard）消费
  - 包含 summary/rot/coverage/lint/backlinks/index/digest 全部子段

- **health `--verbose` 输出模式**：
  - 含 ASCII 图表的详细模式（type 分布柱状图 + 状态分布图 + 操作趋势图）
  - 适合人工快速定位知识库短板

- **pre-commit hook**（`references/scripts/pre-commit.sh`）：
  - 仅对 staged 的 `.knowledge/` 文件执行，<2s 完成
  - 检查 L2 悬空引用（related 中 `[[slug]]` 指向的文件不存在）
  - 检查 L5 孤儿索引（idx 条目指向不存在的 .md 文件）
  - ERROR 阻断 commit，WARNING 不阻断

- **post-merge hook**（`references/scripts/post-merge.sh`）：
  - 合并后检测 `.knowledge/` 下变更的业务文档数
  - 变更 >3 篇 或 `_meta.yaml.last_full_rebuild` >30 天 → 提示运行 `health index-rebuild`
  - 不自动执行，仅输出建议

- **TODO.md 深度分析段**：
  - Ask 回流（synthesis）功能总览：6 项核心风险（R1-R6）+ 6 个遗留问题（Q1-Q6）+ 6 个实施方案（S1-S6）
  - 问题驱动覆盖率（coverage）功能总览：5 项核心风险（R7-R11）+ 5 个遗留问题（Q7-Q11）+ 6 个实施方案（C1-C6）
  - 两功能交叉风险分析（X1-X3）+ 12 方案优先级排列 + v0.9.2→v1.1.0 版本路线图

### Changed

- **SKILL.md**：子命令速查表增加 `--json` 和 `--verbose` 选项
- **README.md**：
  - 版本号 v0.8.0 → v0.9.0
  - 核心理念表新增「三层防护」行
  - Git Hook 说明从 2 个扩展为 4 个
  - 子命令速查增加 `--json` / `--verbose`
  - 资源索引表新增系统模板文件（4 个 `.tpl`）和 hook 脚本（2 个）
- **health-rules.md**：新增 §输出模式选项（--json 完整 schema + --verbose ASCII 图表）

### Files

- 新增 2 个文件（`references/scripts/pre-commit.sh` / `references/scripts/post-merge.sh`）
- 修改 5 个文件（`SKILL.md` / `README.md` / `TODO.md` / `health-rules.md` / `CHANGELOG.md`）

---

## [0.8.2] - 2026-05-26

> **PATCH / 体验提升**：`--from-answer` 回流流程完善、log digest 自动聚合机制、init 端到端自我校验。

### Added

- **`--from-answer` 完整 14 步流程变体**（`ingestion-rules.md`）：
  - synthesis 专属质量门禁 4 项（required_sections + derived_from ≥2 + 非 deprecated + 禁止套娃）
  - frontmatter 额外字段规范（derived_from / derived_question）
  - 录入确认输出模板（含 60 天过期提醒）
  - 禁止二次回流规则

- **log digest 自动聚合**（`health-rules.md`）：
  - `health`（无子命令）执行时自动重建 `.logs/digest.md`
  - 综合报告 Step 1 为 digest 重建、Step 9 为日志摘要提取
  - 综合报告模板增加 `[操作日志]` 摘要行

- **init 端到端 8 项校验清单**（`SKILL.md`）：
  - init Step 4 扩展为"自我校验 + 输出安装摘要"
  - 校验项：目录存在性、根文件完整性、idx 文件数量、_meta.yaml 可解析、hook 可执行等
  - 支持部分失败 WARNING 输出（不中止）

### Files

- 修改 3 个文件（`references/ingestion-rules.md` / `references/health-rules.md` / `SKILL.md`）

---

## [0.8.1] - 2026-05-26

> **PATCH / 可用性修复**：补齐 init 所需的系统配置文件模板，确保首次初始化能写入正确格式的配置。

### Added

- **系统配置文件模板**（`references/templates/`）：
  - `_meta.yaml.tpl` — 索引元数据初始化模板（9 个 indexes 条目 + `${TODAY}` 变量占位）
  - `_logs_config.yaml.tpl` — 日志配置模板（完整匹配 log-rules.md §_config.yaml 所有字段）
  - `_pending_backlinks.yaml.tpl` — 空队列初始化模板（含 consumed_history 段）
  - `_idx_empty.md.tpl` — 通用 idx 表头模板（`${TYPE_DISPLAY}` + `${TODAY}` 变量）

### Changed

- `references/directory-structure.md`：init Step 4-5 更新为引用模板文件写入配置

### Files

- 新增 4 个文件（`_meta.yaml.tpl` / `_logs_config.yaml.tpl` / `_pending_backlinks.yaml.tpl` / `_idx_empty.md.tpl`）
- 修改 1 个文件（`references/directory-structure.md`）

---

## [0.8.0] - 2026-05-26

> **MAJOR / 知识编译器架构**：从「知识存储」升级为「知识编译」——引入分段索引、操作日志、双向引用、一致性检查、Ask 回流五大编译能力。新增 `synthesis` 类型（第 9 个 type）和独立目录。

### Added

- **分段索引系统**（核心特性）：
  - `references/index-rules.md` — 按 type 分 8 个 idx 文件的索引规则（写入时机/读取规则/条目格式/全量重建）
  - `.index/` 目录结构 — 每个业务目录对应一个 `{type}.idx.md`，含 `_meta.yaml` 元数据
  - ask 新增 **Layer -1** 预筛选层——先读 idx 文件做 title/tags/TL;DR 子串匹配，命中则限定 rg 搜索范围
  - `health index-rebuild` 子命令 — 全量重建所有 idx + 一致性校验（L4 孤儿文档 + L5 孤儿索引 + L8 status 不一致）

- **操作日志系统**：
  - `references/log-rules.md` — 按人分文件日志规则（格式/归档/digest 聚合/缺口分析）
  - `.logs/personal/{mis-id}.md` — 每人私有日志文件，解决多用户 git 并发冲突
  - `.logs/_config.yaml` / `.logs/archive/` / `.logs/digest.md` — 日志配置/归档/聚合摘要
  - 所有子命令（in/ask/health）均自动追加操作记录；ask 内容使用 sha1 hash 脱敏
  - `health coverage` 增强 — 基于日志数据的问答缺口分析（高频未答 → 建议 in）

- **双向引用维护**：
  - `references/backlink-rules.md` — pending 队列缓冲 + 延迟消费 + 上限控制（15 条）
  - `.pending-backlinks.yaml` — 反向引用队列缓冲文件
  - in Step 9.6 入队 → `health backlink-consume` 批量安全消费
  - deprecate 时自动清理 pending 队列中的相关记录

- **一致性检查（lint）**：
  - `references/lint-rules.md` — L1-L9 九维检查规则（矛盾检测/悬空引用/废弃标记/孤儿/related 膨胀/pending 积压/status 不一致/过期未处理）
  - 5D 矛盾过滤框架（Entity/Attribute/Value Type/Context/Version）降低 LLM 误报
  - `health lint` 只报告不修改；`health lint --fix` 安全修复 L3+L8

- **synthesis 类型（Ask 回流）**：
  - `references/templates/synthesis.md` — 综合分析文档模板（来源文档 ≥2 篇 / 综合结论 / 对比分析）
  - `_registry.yaml` 新增 synthesis 注册（target_dir: `synthesis/`, layer: L2, expires_days: 60）
  - `in --from-answer` 子命令 — 将 AI 对话中的综合回答录入为 synthesis 文档
  - ask 回流提示（条件触发：≥2 篇文档综合 + >300 词 + 含跨文档关联发现）
  - **二次回流禁止**：synthesis 文档不能再通过 ask 回流生成新 synthesis

- **目录结构扩展**：
  - 业务目录从 8 个增至 9 个（新增 `synthesis/`）
  - 新增 3 个系统目录：`.index/` / `.logs/` / `.pending-backlinks.yaml`
  - init 流程更新：创建系统目录 + 写入初始配置文件 + 创建空 idx 模板

### Changed

- **SKILL.md 全面重构**：
  - 描述从"三大能力"升级为"六大能力"（知识编译器）
  - 子命令表新增 lint/backlink-consume/index-rebuild/--from-answer
  - AI 结构化流程从 11 步升级为 14 步（+9.5 索引/+9.6 backlink/+10 log）
  - ask 检索从两层升级为三层（+Layer -1 Index 预筛选）
  - 执行原则从 9 条扩展到 12 条（+索引辅助/操作留痕/延迟回写/集中式lint）

- **ingestion-rules.md**：
  - type 推断优先级表新增第 11 条（synthesis）
  - type 映射表新增 synthesis 行
  - 流程步骤新增 9.5/9.6/10 三步

- **ask-rules.md**：
  - 新增操作日志记录段（ask 完成后自动追加）
  - 新增 Ask 回流提示段（条件触发的 synthesis 录入建议）

- **health-rules.md**：
  - 新增 lint/backlink-consume/index-rebuild 三个子命令入口摘要
  - coverage 增强为含问答缺口分析
  - 所有 health 子命令均增加操作日志记录

- **directory-structure.md**：
  - 目录树从"8 个业务目录 + 4 个根文件"扩展为"9 个业务目录 + 4 个根文件 + 3 个系统目录"
  - 目录职责速查表新增 synthesis 行
  - init 步骤从 2 步扩展为 5 步（+创建系统目录/+写配置/+建 idx 模板）

- **README.md**：
  - 标题加 v0.8.0 版本号
  - 新增「核心理念」章节（5 大编译能力速查表）
  - 功能概览/子命令速查/目录结构/模板库/资源索引/设计原则全面同步更新

- **执行原则调整**：
  - 原"rg 零索引"原则替换为"索引辅助检索"（idx 增强 rg，不替代 rg）
  - 原 9 条原则扩展为 13 条（+索引/日志/回写/lint/二次回流禁止）

### Files

- 新增 7 个文件（`templates/synthesis.md` / `index-rules.md` / `log-rules.md` / `backlink-rules.md` / `lint-rules.md`）
- 修改 8 个已有文件（`SKILL.md` / `README.md` / `DESIGN.md` / `references/directory-structure.md` / `references/ingestion-rules.md` / `references/ask-rules.md` / `references/health-rules.md` / `references/templates/_registry.yaml`）

