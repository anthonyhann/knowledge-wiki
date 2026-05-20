# Changelog

本文件记录 `knowledge-wiki` skill 的所有重要变更。版本号采用语义化版本（MAJOR.MINOR.PATCH），日期为 UTC+8。

变更类型说明：
- **Added** 新增功能
- **Changed** 已有功能调整
- **Refactored** 重构（不改变外部行为）
- **Fixed** 缺陷修复
- **Removed** 移除

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

- `916f7f5` D3+D5: check-deps.sh 扩充 5 个浏览器工具 + --install-browser 一键装组 + SKILL.md 三组工具表

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

- URL 处理章节加入"工具选型决策树"，按目标系统类型分流到不同浏览器工具（Browser Use / Page-Agent / Browser Harness / Agent-Browser / Playwright）。
- `health scan` 子命令按域名路由：所有 URL 统一走浏览器工具。

### Commit

- `dfb441d` D5+D8: URL 处理加入工具选型铁律

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

## 评分演进

| 版本 | 综合评分 | 关键改进 |
|------|---------|---------|
| 0.1.0 | ~78 | 基线发布 |
| 0.2.x | ~88 | D5/D6/D7/D8 多轮补强 |
| 0.3.0 | ~92 | URL 工具选型决策树 |
| 0.4.0 | ~94 | SKILL.md 重构 -53% + Step 0 工具门 |
| 0.5.0 | 95.8 | Group B 浏览器生态 + 一键装组 + bash 3.2 兼容 |
| 0.6.0 | **预期 97+** | type 级模板库 + 8.5 质量门禁 + 与 GSD Taxonomy 对齐 |

---

## 版本号约定

- **MAJOR**：破坏性变更（目录结构调整、frontmatter 字段重命名等需要迁移的改动）
- **MINOR**：新增子命令、新增工具组、新增 references 文档
- **PATCH**：缺陷修复、文案调整、脚本兼容性修复

未发布的开发中变更可写在文件顶部 `## [Unreleased]` 区块。

