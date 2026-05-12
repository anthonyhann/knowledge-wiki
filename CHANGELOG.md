# CHANGELOG

本文档记录 knowledge-wiki skill 的所有重要变更。
格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [未发布]

### 重构

- **SKILL.md 渐进式披露重构**（1796 行 → 432 行，精简 76%）
  - 嵌入式脚本模板外移至 `references/scripts/`（5 个脚本，含 `kb-sync.sh`、`generate-dashboard.py`、`pre-push-hook.sh`、`check-all.sh` 等）
  - 详细规范、模板、数据结构外移至 9 个 `references/*.md` 文件：
    - `references/kb-structure.md` — 知识库目录结构详解
    - `references/doc-standards.md` — 文档规范（frontmatter / WikiLink / 分块规则）
    - `references/retrieval-config.md` — 检索配置详解
    - `references/agents-claude-spec.md` — AGENTS.md / CLAUDE.md 模板规范
    - `references/methodology.md` — 方法论来源
    - `references/ingest-pipeline.md` — Agent 处理流程 + 异常处理 + 代码提取规则
    - `references/output-templates.md` — 各命令输出格式示例
    - `references/data-schemas.md` — graph.json / sources.json / eval 数据集结构
    - `references/lint-rules.md` — lint 规则的自动修复建议
  - SKILL.md 仅保留命令清单、核心摘要、引用指针；细节按需读取 references/*
  - frontmatter `description` 扩展触发词列表
- **D3+D4 维度强化**：ingest 流程新增异常处理表格（超大文件/网络中断/格式解析失败/重复导入/graph.json 损坏）+ 检查点（Step 1 与 Step 4 后用户确认）；reason 流程新增推理中断机制和异常场景表格
- **D5+D8 维度强化**：ask 命令新增零结果 fallback 流程；lint 规则补全自动修复建议；export 补充 jsonl/qa-pairs/graphrag 三种格式输出示例；wiki / reason / init 补全详细输出格式示例

### 修复

- **W003**：README.md 在标题下方补充 `## 概述` 章节，符合 myt-skill-linter 规范

### 新增

- **test-prompts.json** — 评估测试用例集，覆盖 `init`、`ingest`、`ask` 三种典型场景

### 变更

- **`/knowledge-wiki init` 升级为三阶段初始化**，执行完成后知识库立即可用，无需手动运行任何脚本
  - Phase 1：创建结构与生成文件（目录结构 + 治理文件 + `.kb-meta/` 空 JSON 文件）
  - Phase 2：安装脚本（5 个脚本全部写入并 `chmod +x` + 安装 `.git/hooks/pre-push`）
  - Phase 3：首次执行（立即运行 `generate-docs.sh`、`generate-dashboard.py`、`check-all.sh`）
  - 新增 init 完成摘要输出（目录状态、脚本清单、生成文件状态、健康报告、下一步引导）

- **`docs/` 目录重构为按项目生命周期分区**（方案 B）
  - `requirements/` — 需求阶段（PRD、需求文档、UI 设计图）
  - `design/` — 设计阶段（技术方案、流程图、PUML 图）
  - `implementation/` — 开发阶段（ADR、接口约定）
  - `quality/` — 质量保障（测试方案、用例、验收文档）
  - `release/` — 上线阶段（上线文档、回滚方案）
  - `exec-plans/` — 执行计划（active/completed/tech-debt-tracker）
  - `domain/` — 业务领域知识（按领域子目录）
  - `generated/` — CI 自动生成（db-schema/api-changelog/dependency-graph）

- **pre-push hook 升级为三步流程**
  - 步骤 0（新增）：自动生成 — 刷新 `docs/generated/` 和 `dashboard.md`，变更文件自动暂存
  - 步骤 1：同步源陈旧检测（原有）
  - 步骤 2：代码变更 → 文档映射（原有）

### 新增

- **四个缺失脚本模板补齐**（均内嵌于 SKILL.md，init 时写入）
  - `generate-dashboard.py` — 从 `.kb-meta/stats.json` + `sources.json` + `eval-results.json` 渲染 `dashboard.md`
  - `generate-docs.sh` — 生成 `docs/generated/db-schema.md`（SQL migration 文件）和 `api-changelog.md`（git diff 接口文件）
  - `check-all.sh` — frontmatter 校验、行数超限、WikiLink 断链，自动跳过 `generated/` 和 `.kb-meta/`
  - `install-hooks.sh` — 手动安装 pre-push hook 的备用路径

### 新增
- **`/knowledge-wiki source`** — 持久化同步源管理
  - `source add <url>` — 注册同步源，支持学城/飞书/Apipost/普通 URL
  - `source list` — 查看所有源状态（active/stale/error/paused）
  - `source sync [id]` — 增量同步（hash 对比，内容无变化自动跳过）
  - `source remove <id>` — 移除注册（不删除已生成页面）
  - `source status` — 聚合健康状态视图
  - 注册表存储：`.kb-meta/sources.json`（含 id/url/type/recursive/tags/last_hash/last_synced/status/page_count）

- **pre-push hook 双检查机制** — 在原有"代码变更→文档映射"检查基础上新增"同步源陈旧检测"
  - 检查一：扫描 `sources.json`，标记 `stale`（>7天）或 `error` 状态的源
  - 检查二：调用 `kb-sync.sh` 分析 git diff
  - 两个检查独立运行，不短路，用户一次看到所有待处理事项
  - 交互从三选一升级为四选一：source sync / wiki 更新 / 两者都做 / 跳过

- **在线平台文档导入**（`/knowledge-wiki ingest <url>`）
  - 学城（km.sankuai.com）：heading/cell/textbox 结构提取，需美团内网登录态
  - 飞书文档（larkoffice.com）：list/heading 目录树提取，需飞书登录态
  - Apipost 文档（docs.apipost.net）：目录树遍历 + 接口 entity 页生成，公开访问无需登录
  - 登录态检测逻辑：检测到跳转登录页时自动中止并提示用户
  - 新增 `--recursive` 参数：递归抓取整个文档树
  - 新增 `--url-file` 参数：批量导入多个 URL

- **FAQ 知识库类型**（`type: faq`）
  - 使用问答对结构（`### Q:` / `**A:**`），每个 Q&A 独立成块
  - RAG 召回新增 Layer 0：先在 faq 页精确匹配问题文本，命中直接返回（置信度 high）
  - ingest 时自动检测"Q:"/"常见问题"模式，建议使用 faq 格式
  - 与 concept/entity 对比：分块策略不同，召回优先级不同

- **持久化检索配置**（SCHEMA.md `retrieval:` 块）
  - 支持 6 个参数：threshold / top_k / default_mode / rerank / faq_exact_match / context_window
  - 优先级：命令行参数 > SCHEMA.md 配置 > 内置默认值
  - `source_stale_days` 参数：控制同步源 stale 判定天数（默认 7）

### 计划中
- `references/` llms.txt 格式约定与自动同步机制
- `people/` CODEOWNERS 文件自动生成
- `/knowledge-wiki sync` 变更映射规则可配置化（支持自定义规则文件）
- 同步源定时自动刷新（cron 模式）

---

## [1.0.0] - 2026-05-07

首次发布。基于与用户的完整需求问询和多轮迭代设计，融合内网 AI-DLC 框架、Zettelkasten、GraphRAG、ReACT 等领域最佳实践。

### 新增 — 三大核心能力

- **RAG 快速问答** (`/knowledge-wiki ask`)
  - BM25 稀疏召回 + Dense 稠密召回 + GraphRAG 图谱增强 + 父子分块四路混合检索
  - 检索阈值调节（`--threshold`、`--top-k`、`--mode bm25/dense/graph`）
  - 多轮上下文感知，话题切换时自动重置检索范围
  - 每次回答后基于知识图谱自动生成 3 条推荐问题
  - 输出含置信度（high/medium/low）和参考来源标注

- **ReACT 智能推理** (`/knowledge-wiki reason`)
  - Thought → Action → Observation 渐进式多步推理循环
  - 自主编排内置工具（kb_search、kb_read、kb_write、kb_graph_neighbors）
  - 自动发现并调用已安装的 MCP 工具
  - 网络搜索兜底，结果自动提示入库
  - 推理深度控制（`--max-steps`、`--no-web`、`--no-mcp`、`--verbose`）

- **Wiki 自动生成** (`/knowledge-wiki wiki`)
  - `--enable/--disable` 开关控制是否在 ingest 后自动触发
  - 草稿写入 `inbox/`，通过质量门控后升级为 stable
  - 质量门控：TL;DR 必填、至少 1 个入站链接、无断链、sources 非空
  - 72 小时决策入库规则：Agent 发现决策点时自动提示

### 新增 — 知识库初始化

- **`/knowledge-wiki init`** — 一键初始化完整知识库
  - 生成 `CLAUDE.md`（AI 协作契约 + 禁止行为清单，Agent 每次必读）
  - 生成 `AGENTS.md`（AI 专用导航地图，硬限 100 行，超限拆分至 AGENT-ROUTING.md）
  - 生成 `AGENT-ROUTING.md`（各 Agent 身份的可读/可写/禁止写三列路由表）
  - 生成 `CONTRIBUTING.md`（人类参与指南，AI 无需读取）
  - 生成 `README.md`（双受众入口，顶部给 AI，底部给人类）
  - 自动安装 `.git/hooks/pre-push`（push 前知识库同步检查）
  - 自动生成 `processes/scripts/kb-sync.sh`（变更分析脚本）
  - 两个脚本模板内嵌于 SKILL.md，init 时直接读取写入，无外部依赖

### 新增 — 文档导入

- **`/knowledge-wiki ingest`** — 支持 11 种格式
  - Markdown、PDF、Word (.docx)、TXT、HTML/URL、图片（OCR）
  - CSV/Excel、PPT (.pptx)、JSON、代码目录、对话记录
  - 自动识别文档类型，提取核心概念、实体、流程步骤、决策点
  - 代码目录提取：模块/包 → entity 页，关键注释 → synthesis 草稿
  - `--update` 增量模式：只处理新增/变更文件

### 新增 — 知识图谱可视化

- **`/knowledge-wiki graph`** — 生成零依赖本地 HTML
  - D3.js v7 力导向布局，节点大小按 backlink_count 缩放
  - 类型着色：concept 蓝 / entity 绿 / process 橙 / source 灰
  - `canonical` 节点金色边框，`deprecated` 节点半透明
  - 交互：点击高亮邻居、悬停显示 TL;DR、搜索框实时过滤、类型筛选器
  - `graph.json` 数据结构：nodes（id/label/type/tags/status/backlink_count/tldr）+ links（source/target/relation）

### 新增 — 质量保障

- **`/knowledge-wiki lint`** — 10 项检查
  - ERROR：断链、frontmatter 缺失、deprecated 文档被引用
  - WARNING：孤立页面、TL;DR 缺失、unverified 标注未处理、last-reviewed > 90 天
  - CI ERROR：单文件超 800 行
  - INFO：循环依赖检测
- **`/knowledge-wiki eval`** — 端到端评测
  - 检索层：召回命中率、精确率、平均召回延迟
  - 生成层：BLEU-4、ROUGE-L、幻觉率
  - 全链路：P50/P95 端到端延迟
  - 输出 Top 3 失败案例分析和改进建议
- CI pre-commit hook：硬性阻断 frontmatter 错误、断链、deprecated 引用、超行数

### 新增 — Git 集成

- **`/knowledge-wiki sync`** — push 前知识库同步检查
  - 分析 `git diff` 变更文件，按规则映射到 `.knowledge/` 对应文档
  - 映射规则：`<skill>/SKILL.md` → `pages/entities/<skill>.md` 等 5 类规则
  - 三选一交互：立即更新 / 有补充内容 / 跳过直接推送
  - 退出码 0 = 无需同步，1 = 有待同步文档
  - `git push --no-verify` 临时跳过

### 新增 — 数据导出（AI-DLC 友好）

- **`/knowledge-wiki export jsonl`** — RAG embedding 就绪分块数据
- **`/knowledge-wiki export qa-pairs`** — Instruction Tuning 问答对（Agent 自动生成）
- **`/knowledge-wiki export graphrag`** — GraphRAG 社区摘要格式
- **`/knowledge-wiki export llms-txt`** — references/ llms.txt 友好版本

### 新增 — 状态监控

- **`/knowledge-wiki status`** — 统计/健康/RAG 就绪度/最新评测一屏展示

### 新增 — 目录结构与治理

- **双受众分离**：CLAUDE.md（AI 契约）+ CONTRIBUTING.md（人类指南）职责隔离
- **`status: canonical`** 权威锁定，AI 禁止修改
- **`status: deprecated`** 自动降权，禁止引用，强制转向 `links.supersedes`
- **生成文件物理隔离**：graph.json、graph.html、dashboard.md、.kb-meta/、docs/generated/ 均标注「CI 生成，禁止手动编辑」
- **exec-plans 状态分区**：`active/` 进行中 + `completed/` 只读归档
- **AGENTS.md 防膨胀**：超 100 行强制拆分至 AGENT-ROUTING.md

### 新增 — people/ 层

- `people/{user-id}/context.md` — 角色、技能图谱、负责模块、当前迭代焦点、跨团队协作接口、阻塞事项
- `people/{user-id}/decisions.md` — 个人决策日志（append-only，禁止修改历史条目）
- `people/{user-id}/prefs.md` — Agent 协作偏好（回答风格、上下文缩写、禁止行为）
- Agent 使用场景：任务分配推理、周报生成、代码 review 归属
- 权限：CODEOWNERS 限制只有本人可写，AI 只读

### 新增 — 文档规范

- 标准 frontmatter 11 个字段（title/type/status/created/updated/last-reviewed/owner/tags/sources/confidence/links）
- WikiLink 三种语法（`[[page]]`、`[[page|alias]]`、`[[page#section]]`）
- AI-DLC 约束 6 条：TL;DR 独立成块、平坦化结构、显式引用、术语一致性、代码可运行、结构化数据块
- RAG 分块规则：TL;DR（~80 token）/ 定义（~300 token）/ 代码块（完整不截断）/ 20% 重叠

### 设计决策

- **pre-push hook 模板内嵌**：两个脚本模板内嵌于 SKILL.md，init 时从 SKILL.md 读取写入目标路径，新项目无需外部依赖
- **AGENTS.md 100 行上限**：防止导航地图膨胀失效，超限强制拆分到 AGENT-ROUTING.md
- **三模式路由**：ask（精准快速）/ reason（复杂推理）/ wiki（知识沉淀）针对不同任务复杂度，避免用一种策略硬撑所有场景
- **草稿优先**：所有自动生成内容一律写入 inbox/，人工确认后升级，防止低质量内容污染 stable 知识库
