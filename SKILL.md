---
name: knowledge-wiki
description: "团队知识库全生命周期管理工具（治理型知识图谱 v2.0.0），支持零门槛录入、索引加速查询、严格溯源问答、双向引用维护、一致性检查、操作日志追踪、代码文档化，并从已治理文档派生持久化知识图谱（关系查询/可信度治理/社区检测/可视化），让 ask 从『找文档』升级为『找关系』。另支持测试知识积累与聚合消费（test type + ask test，供 QA Agent 场景单点取齐测试知识包）。当用户需要录入知识、查询知识库、检查知识腐烂、扫描外部源变更、检查知识一致性、查看覆盖率或问答缺口、编译/查询知识图谱、问 X 和 Y 怎么连/改 X 影响什么/A 到 B 的知识链、导出可视化知识网、录入/查询测试知识（测试规范/回归清单/测试踩坑/测试环境）时使用。触发词：/knowledge-wiki、知识录入、知识库查询、知识库健康、查知识库、记录到知识库、知识沉淀、knowledge wiki、kb init、kb health、知识库初始化、帮我建知识库、把这个记到知识库、知识库里有没有、检查过期文档、知识库lint、索引重建、知识图谱、编译图谱、graph-build、ask graph、ask path、ask test、测试知识包、关系查询、涌现分析、知识网络可视化、graph export。明确指令：/knowledge-wiki（直接触发本 skill）。NOT for: 私域笔记/日记、实时聊天/群消息记录、与项目代码无关的会议纪要、临时草稿（用户本地剪贴板内容）。"
trigger: /knowledge-wiki
allowed-tools:
  - Read
  - Write
  - Edit
  - run_terminal_cmd
---

# /knowledge-wiki

团队知识库管理 skill（治理型知识图谱 v2.0.0），文档层 + 图谱层能力通过子命令路由：

> **图谱层核心流程链**：`health graph-build`（编译）→ `ask graph/path/explain`（关系查询）→ `health graph`（涌现分析）→ `health discover`（发现候选）→ `health edge-review`（人审推断边）→ `graph export`（可视化）

**前置检查**：除 `init` 外，所有子命令执行前先确认 `.knowledge/` 目录存在，不存在则提示：「知识库未初始化，请先运行 /knowledge-wiki init」，中止当前命令。

| 命令前缀 | 能力 | 详见 |
|---------|------|------|
| `init` | 初始化（依赖检查 + 目录 + hooks + 自检） | init 节 |
| `in` | 录入（URL / 文件 / 文本 → 结构化） | in 节 |
| `ask` | 查询（文档四层检索 + 图谱关系查询 + ask test 测试知识包聚合） | ask 节 |
| `docs` | 代码变更文档化 | docs 节 |
| `health` | 维护 + 图谱编译/分析/人审 | health 节 |
| `graph export` | 知识网络可视化导出 | graph export 节 |

## 资源索引（懒加载铁律）

> 所有详细规则**以 references/ 文件为唯一权威源**，SKILL.md 只承载命令骨架与执行原则。
> **懒加载铁律**：启动时仅加载本 SKILL.md，**禁止预读 references/**。执行到对应子命令时才按「何时用」列 Read 对应文件，单次子命令执行最多加载 2-3 个（例：`ask` → `ask-rules.md` + `index-rules.md`；`in <url>` → `ingestion-rules.md` + `url-handling.md`）。

| 路径 | 用途 | 何时用 |
|------|------|--------|
| `references/directory-structure.md` | `.knowledge/` 完整目录框架（.index/.logs/.pending-backlinks/.pending-edges）+ 根文件模板 | `init` |
| `references/scripts/check-deps.sh` | 工具依赖检查 + 一键安装 | `init` Step 0 |
| `references/templates/{_meta.yaml,_logs_config.yaml,_pending_backlinks.yaml,_pending_edges.yaml}.tpl` + `_idx_empty.md.tpl` | 系统配置 / 队列 / 空 idx 初始化模板 | `init` Step 2 |
| `references/scripts/{pre-commit,post-merge,pre-push,commit-msg,prepare-commit-msg}.sh` | 5 个 git hooks（L2 悬空引用 + L5 孤儿索引检测 <2s / 重建提示 / 过期阻断确认 / [kb] 标记 / 文档化提示） | `init` Step 3 |
| `references/ingestion-rules.md` | AI 结构化流程（type/slug 推断、模板加载、质量门禁、source 管理） | `in` 写入逻辑 |
| `references/url-handling.md` | URL 处理铁律（内部文档平台禁浏览器）+ 域名路由表 + scan 路由 | `in <url>` / `health scan` |
| `references/templates/_registry.yaml` + `references/templates/{type}.md` | 模板注册表（type → 模板 + 必填段 + 质量门禁）+ 10 类正文骨架 | `in` Step 2.5 / 5 / 8.5 |
| `references/index-rules.md` | 分段索引规则（按 type 分 idx 文件，写入/读取/重建） | `in` Step 9.5 / `ask` Layer -1 / `health index-rebuild` |
| `references/backlink-rules.md` | 双向 related 回写规则（pending 队列 / 延迟消费 / 上限控制） | `in` Step 9.6 / `health backlink-consume` / `deprecate` |
| `references/log-rules.md` | 操作日志规则（按人分文件 / 格式 / 归档 / digest 聚合） | 所有子命令写入 |
| `references/ask-rules.md` | 四层检索（含 Index Layer -1）+ 标准回答 + 时效计算 + links/refs + ask test 测试知识包聚合（v2.1.0） | `ask` |
| `references/docs-rules.md` | 代码文档化规则（分析引擎 + 变更分类 + 问询流程） | `docs` |
| `references/health-rules.md` | rot/scan/coverage/audit/deprecate/distill/graph/discover 流程 | `health` |
| `references/lint-rules.md` | L1-L9 一致性检查 + 图层/pending 队列附加检查 + `--fix` 安全边界 | `health lint` |
| `references/graph-model.md` | graph.json 节点/边 schema 契约 + 顶层元信息 | `health graph-build` 编译 |
| `references/graph-build-rules.md` | 派生引擎职责 + 编译流程 + 锁/原子写/source_hash + 零破坏回退红线 | `health graph-build` |
| `references/trust-rules.md` | confidence 三级分级（EXTRACTED/INFERRED/AMBIGUOUS）+ reviewed 人审闭环语义 | `health edge-review` / `discover` |
| `references/pending-edges-rules.md` | `.pending-edges.yaml` 队列结构 + 入队幂等三检查 + 消费流程 | `health edge-review` / `discover` |
| `references/scripts/graph_build.py` / `graph_query.py` / `graph_analyze.py` / `discover_prefilter.py` / `explore_questions.py` / `graph_export.py` | 图谱六引擎（均 PEP723 头、仅 networkx==3.6.1；`init` 复制到 .knowledge/ 后由各图谱命令调用；全部只读文档，仅 graph_build 写 .graph/、graph_export 写 .graph/exports/） | 图谱命令执行时 |

## 子命令详解

> 本节是**每个子命令行为（步骤 / 约束 / 产出）的唯一描述处**。通用铁律见文末「执行原则」C/E 表（正文以 C#/E# 指针引用，不重复展开），细则以资源索引对应文件为准。

### init

```
Step 0 依赖检查（check-deps.sh：rg/git）→ Step 1 创建目录（10 业务目录 + .index + .logs + .pending-backlinks）→ Step 2 根文件 + 系统配置（README/CLAUDE/AGENTS/.sources.yaml + _meta.yaml + _config.yaml + 10 空 idx + 空队列）→ Step 3 安装 5 hooks（cp references/scripts/*.sh .git/hooks/ && chmod +x；已存在时询问覆盖/追加/跳过；非 git 仓库跳过）→ Step 4 8 项自我校验（任一 ⚠️ 不阻断）；旧版库升级补齐 tests/ 见 directory-structure.md「存量库升级」
```

- 约束：Step 0 未通过时**禁止**进入 Step 1
- 产出：`✓ 知识库初始化完成` 安装摘要（目录/根文件/Hooks/索引/校验计数）+ 「下一步：/knowledge-wiki in <知识内容>」

### in（录入）

**输入路由**：`http(s)://` 开头 → URL 处理（内部文档平台走 internal-docs skill，其他走 agent-browser）；文件路径 → 文件处理（代码文件提炼设计知识，.md/.txt 直接处理）；其余 → 文本处理。
**护栏**：文件 >10MB / 文本 >100KB / URL 正文 >200KB 时中止或截断。

**14 步结构化**（三种输入殊途同归）：

```
1 提取 title → 2 推断 type → 2.5 加载 type 专属模板（_registry.yaml）→ 2.6 [仅 glossary] 去重前置检查 → 2.65 全类型相似检测前置 → 2.7 跨类型术语抽取 → 3 提取 tags（3-5 个）→ 4 生成 TL;DR（50-100 词必填）→ 5 按模板骨架整理正文（required_sections 不可缺）→ 6 rg 扫描推荐 related → 7 生成 slug → 8 目标已存在则询问覆盖/追加/中止 → 8.5 质量门禁（required_sections + quality_gate 缺失即中止写入）→ 9 写入 .knowledge/{dir}/{slug}.md → 9.5 更新分段索引 → 9.6 反向引用入队 .pending-backlinks.yaml → 10 追加操作日志（C6）→ 10.5 图谱感知（graph.json 存在时提示 health graph-build --incremental，不阻断）
```

- 产出：`✓ 已写入 .knowledge/{dir}/{slug}.md` + 标题/类型/过期/关联一行摘要 + draft 提示（C3：确认后 `health audit {slug}`）
- 变体：
  - `--update <slug>`：预览当前值（title/status/expires/TL;DR）→ 三选一 **[1] 覆盖**（保留 status/created/owner）/ **[2] 追加新版本节**（末尾 `## YYYY-MM-DD 更新`，原文不动）/ **[3] 中止** → updated=today、sources 末尾追加新来源
  - `--from-answer "{简短描述}"`：Ask 回流录入
  - `source add <url> [--name] / list / remove <id>`：`remove` 前必须 rg 查引用，有引用时三选一（仅删源 / 删源+追加移除标记 / 中止）

### ask（查询）

**四层检索**：Index 预筛（Layer -1）→ rg 关键词匹配（Layer 0，最多 3 轮）→ 模糊兜底（Layer 0.5）→ 语义筛选读全文（Layer 1）。

**产出格式**（5 元素必含）：

```
结论：{一句话回答}
来源：.knowledge/{dir}/{slug}.md
录入人：@{owner} | 时效：{FRESH|WARNING|EXPIRED}
引用链：[[slug-a]] → [[slug-b]]
---
无记录时：「知识库中未找到相关记录。建议：/knowledge-wiki in <描述> 录入」（C1 禁止脑补）
```

| 子命令                                                        | 行为 |
|------------------------------------------------------------|------|
| `ask "<问题>"`                                               | 四层检索 → 5 元素产出；status 优先级 `canonical > active > draft > deprecated`（deprecated 禁止引用） |
| `ask test "<模块/场景>" [--level unit\|integration\|api\|e2e]` | [v2.1.0] 测试知识包聚合：读 test.idx.md → scope/tags/test_level 过滤（`--level e2e` 与 `--level api` 互不兼容互不互换，见 ask-rules.md 语义说明） → 按 test_kind 五分组（① 运行环境与命令置顶 ② 规范 ③ 检查清单 ④ 坑点经验 ⑤ 测试数据）输出，每条带 `[来源: tests/{slug}]`；0 命中如实告知（C1）；不触发回流提示 |
| `ask links <slug>`                                         | 反向追溯：谁引用了这篇（C8：只含权威边） |
| `ask refs <slug>`                                          | 正向追溯：这篇引用了谁 |

**图谱查询**（前置：`health graph-build` 已编译 graph.json，缺失时按错误响应表中止，不降级文档检索）：

| 子命令 | 步骤 | 输出要点 |
|--------|------|---------|
| `ask graph "<问题>"` | slug 匹配中心节点 → graph_query.py neighbors → confidence 降序 top-20 | 每边含 direction/关系类型/对端/confidence；INFERRED 标「⚠️ 推断边未经人审」、AMBIGUOUS 标「⚠️ 模糊边仅参考」；社区/中心度缺失时标「未分析，运行 health graph 后可用」，不中止 |
| `ask explain "<slug>"` | 精确 slug 查找 → graph_query.py node → 展开全部入/出边 | 入边列表 + 出边列表；每边含 type/confidence/reviewed/source_location |
| `ask path "<A>" "<B>"` | slug 匹配两端 → graph_query.py path 最短路（C8：只走权威边；deprecated/EXPIRED 排除；AMBIGUOUS 永不入路径；`--max-hops` 可限跳数） | 每跳 A→B（slug/title/status）+ 每边 type/confidence；不可达时输出「权威路径不可达」+ `--include-inferred` 建议（⚠️ 推断边标注） |

### docs（代码文档化）

- **触发**：prepare-commit-msg hook 自动提示 或 手动运行（E7：仅提示不阻断 commit）
- **7 步引擎**：获取 diff → 过滤（排除测试/锁文件）→ 意图提取 → type 映射 → 已有文档匹配 → 影响度评分(0-1) → 生成建议列表
- **产出**：总览摘要 + 逐条问询（C7：[1]录入/更新 [2]跳过 [3]编辑后录入 [4]全部跳过）+ 完成总结；更新走 `in --update`，新增走标准 `in`，sources 记 `代码变更自动检测，commit {hash}（{date}）`
- **变体**：`--staged`（staged 文件）/ `--last <N>`（最近 N 次 commit）/ `--range <ref>..<ref>` / `--pending`（处理 .pending-docs.yaml 暂存项）/ `--dry-run`（仅输出分析）
- **边界**：分析结果 >10 条先展示 Top 5（按影响度）再问是否继续；`.pending-docs.yaml` 积压 >20 条时提示先处理

### health（维护）

**综合报告**（`health` 无子命令时）：顺序执行 10 步（digest 重建 → 统计 → rot → coverage → 外部源 → lint → 进化建议 → 反向引用 → 索引 → 日志）后输出格式化报告（`--json` 供 CI 消费 / `--verbose` 含 ASCII 图表）。

```
📊 知识库健康报告（{date}）
─────────────────────────────
总文档：{N} 篇 | active: {a} | draft: {d} | deprecated: {dp}
⏰ 过期：{expired} 篇 WARNING / {warning} 篇即将到期
🔗 悬空引用：{n} 处 | pending 队列：{m} 条待消费
📈 覆盖率：{x}%（{covered}/{total} 顶层目录）
🧹 Lint：L1×{n1} L2×{n2} ... | 建议：{actions}
─────────────────────────────
下一步：health rot → health lint --fix → health backlink-consume
```

**文档层子命令**：

| 子命令 | 行为与约束 |
|--------|-----------|
| `rot` | EXPIRED/WARNING 列表 + 批量决策入口（逐篇 / 批量延期 / 批量废弃 / 仅列表）；无问题时完全静默（E1） |
| `scan` | 遍历 `.sources.yaml` 中 active 源；按域名路由（内部文档平台走 internal-docs skill，其他走 agent-browser）；diff 提示三选一；**不自动更新**，变更由用户决策 |
| `coverage` | 以 git 根为锚点扫描顶层目录 + 问答缺口分析（基于 log 数据）；仅建议不阻断 |
| `audit <slug>` | 三选一：确认有效（→ active，expires 按 type 分支续期）/ 需要更新 / 已废弃 |
| `deprecate <slug>` | rg 查所有引用（E5）→ 确认后 status=deprecated + 引用处追加注释 + 清理 pending 队列 |
| `lint` | L1-L9 一致性全量检查（矛盾/悬空引用/废弃标记/孤儿/related 膨胀/pending 积压/status 不一致/过期未处理），**只报告不修改**；图层/队列存在时附加：`L-graph-orphan-edge`（边缺 source_location，ERROR）/ `L-graph-drift`（边无文档来源，ERROR）/ `L-graph-unreviewed-in-links`（links 只放权威边守门，ERROR）/ `L-pending-edge-reviewed-residue`（已批准残留，WARNING）/ `L-pending-edge-no-source`（推断边缺来源，ERROR），不存在则对应项静默跳过 |
| `lint --fix` | 仅安全自动修复：L3 废弃引用加删除线 + L8 idx status 同步；先 dry-run 展示变更预览清单，**等用户确认**后执行 |
| `backlink-consume` | 消费 `.pending-backlinks.yaml` 队列批量回写 related；执行前展示待消费条目数 + 影响文档列表，**等用户确认**；确认后修改 frontmatter 并自动 commit |
| `index-rebuild` | 全量重建所有 idx + 一致性校验（孤儿检测/status 同步）；执行前展示当前 idx 状态摘要，**等用户确认**后覆写 |
| `distill [--execute]` | 认知蒸馏：Jaccard 重复检测 + 低质量清理 + 孤立知识检测；默认预览不修改，`--execute` 逐步确认后执行合并/废弃/关联 |

**图谱层子命令**（数据物理隔离在 `.knowledge/.graph/`，删除即零破坏回退；E9：原子/只读操作，无需用户确认直接执行）：

| 子命令 | 步骤 | 要点 |
|--------|------|------|
| `graph-build [--full]` | 加锁防并发 → graph_build.py 遍历 9 目录抽节点/边 → 原子写 graph.json | 输出节点数/边数/可信度分布摘要；`--full` 全量重建兜底 |
| `graph-build --incremental` | 计算 source_hash → 与 graph.json 顶层 hash 比对 | 漂移才全量重建，一致则 exit 0 跳过；由 `in` 步骤 10.5 staleness 提示触发 |
| `graph` | graph_analyze.py 跑 Louvain 社区 + 中心度（god node 业务校验）+ 内聚度 → 落 communities.json + 回填节点 centrality/community 字段 | 高中心度且 canonical/active 才提示枢纽；孤岛提示待连接；低内聚度标横切性强（正常）；`--min-nodes` 调小语料门槛；非实时全量 |
| `discover [--dry-run]` | discover_prefilter.py 初筛跨域「相似度高/结构接近但未连接」候选 → AI 语义裁决（仅 INFERRED/AMBIGUOUS，**绝不 EXTRACTED**）→ 入 `.pending-edges.yaml`（过入队幂等三检查） | 候选边数 + 裁决表；`--dry-run` 仅报不入队；入队后经 edge-review 人审 |
| `edge-review` | 读 `.pending-edges.yaml` pending[] → 逐条展示（source→target + type + confidence + AI 摘要）→ 三选一：**[a] approve**（回写源文档 frontmatter related，提示 graph-build --incremental）/ **[r] reject**（status=rejected 不入图）/ **[s] skip**（本次跳过，下次仍出现） | AMBIGUOUS 仅 reject/skip（C8 禁止 approve）；全部处理完统一提示 graph-build --incremental |

### graph export（可视化导出）

- **前置**：graph.json 存在（缺失则中止，提示先 `health graph-build`）
- **步骤**：graph_export.py（+ communities.json 可选）渲染 → 写 `.knowledge/.graph/exports/graph-YYYYMMDD.{ext}`，输出「已导出：{路径}」
- **格式**：`--html`（默认，Cytoscape.js 交互式，浏览器分享）/ `--canvas`（Obsidian Canvas JSON）/ `--graphml`（Gephi/yEd 深度分析）
- **选项**：`--include-inferred` 含 INFERRED 推断边（⚠️ 未经人审标注）；默认只含权威边
- **回退**：删 `.graph/` 目录即零残留，不影响任何文档（只读操作）

## 错误响应（统一）

> 所有错误响应一律**单行 + 速查提示**，不执行任何 IO、不调用 rg。

| 错误形态 | 触发条件 | 响应 |
|---------|---------|------|
| 未知子命令 | 首段非 `init`/`in`/`ask`/`docs`/`health`/`graph` | 「未知子命令: {x}，可用：init / in / ask / docs / health / graph export」+ 速查表，不执行任何 IO |
| `ask` 缺参 | 无问题文本 | 「ask 需要查询内容，例：/knowledge-wiki ask "打印超时配置"」，中止 |
| `in --update` 缺 slug | 无 slug | 「--update 需要 slug，可用 `ls .knowledge/*/` 查看现有 slug」，中止 |
| `audit`/`deprecate` 缺 slug | 无 slug 参数 | 提示先用 `health rot` 或 `health` 查文档清单，中止 |
| `in source` 缺参 | `add` 缺 url / `remove` 缺 id | 各自输出对应 usage 一行，中止 |
| graph.json 不存在 | ask graph/explain/path 时 `.knowledge/.graph/graph.json` 缺失 | 「图谱未编译，请先运行 `/knowledge-wiki health graph-build`」，中止；**不降级到文档检索**（语义不同） |
| 图谱依赖缺失 | uv/Python 不可用或 networkx 安装失败 | 「graph_build.py 依赖异常：{错误摘要}，请运行 `uv pip install networkx==3.6.1`」，中止；不影响文档层命令（图层隔离） |
| communities.json 缺失 | ask graph 请求社区信息但 `health graph` 未运行 | ask graph 正常返回邻居；社区/中心度字段标「未分析，运行 health graph 后可用」；不中止 |
| `.pending-edges.yaml` 不存在 | edge-review/discover 读取队列文件缺失 | 等同空队列，「暂无待审推断边」静默退出；不报错 |

## 执行原则

### 🔴 核心不变量（违反即为 Bug，任何流程不可豁免）

| # | 原则 | 说明 |
|---|------|------|
| C1 | **无来源不写、不答** | sources 必填；ask 无记录时明确告知，不猜测 |
| C2 | **术语唯一** | 录入前检查 glossary/ 是否已存在同义定义 |
| C3 | **草稿优先** | 新录入一律 status=draft，由 health audit 升级到 active |
| C4 | **模板为合约** | 正文必须严格按 `references/templates/{type}.md` 骨架生成；AI 不允许增删一级标题，必填段不齐时 8.5 门禁拦截 |
| C5 | **内部文档平台禁浏览器** | docs.internal.example.com 必须调用 internal-docs skill，禁止 agent-browser / playwright（详见 `references/url-handling.md`） |
| C6 | **操作留痕** | 所有 in/ask/docs/health 操作写入 `.logs/personal/{user-id}.md`；ask 内容 hash 脱敏 |
| C7 | **逐条问询** | `docs` 子命令的交互确认必须逐条展示、逐条决策，禁止批量展示要求用户一次性决策 |
| C8 | **图谱可信度护栏** | AMBIGUOUS 边永不入 ask path 路径；ask links 只含权威边（EXTRACTED 或 reviewed=true）；INFERRED 边必须标注「⚠️ 推断边未经人审」；推断边须经 `health edge-review` approve 才升级权威边，**禁止跳过人审直接入图** |

### 🟡 扩展行为（可软降级，故障不阻断主流程）

| # | 原则 | 说明 | 降级策略 |
|---|------|------|---------|
| E1 | **静默放行** | hook / rot 无问题时完全不输出 | — |
| E2 | **索引辅助** | `.index/` 为 Layer -1 预筛选层，增强 rg 而非替代它 | idx 更新失败 → WARNING + 标记 stale，不阻断 in |
| E3 | **延迟回写** | 反向引用写入 `.pending-backlinks.yaml` 队列 | 队列写入失败 → WARNING，不阻断 in |
| E4 | **集中式 lint** | 矛盾检测只在 `health lint` 执行 | 不在 in/ask 流程中阻断 |
| E5 | **deprecate 必处理引用** | 废弃前 rg 查所有引用处 | — |
| E6 | **工具检查门** | `init` Step 0 必跑 check-deps.sh | 缺必需工具时中止 init |
| E7 | **docs 不阻断 commit** | prepare-commit-msg hook 仅提示，exit 0 不阻断 | hook 执行失败时静默退出 |
| E8 | **pending 缓存** | docs 分析结果可暂存到 `.pending-docs.yaml` | 写入失败不影响主流程 |
| E9 | **图谱操作即时执行** | `health graph-build/graph/discover` 和 `graph export` 为原子操作或只读操作，数据隔离在 `.knowledge/.graph/`，**无副作用于文档层，无需用户确认直接执行** | 脚本依赖缺失 → 提示安装命令，不阻断文档层命令 |

> **优先级**：当 C 级与 E 级冲突时，始终以 C 级为准。例如 idx 更新 (E2) 若引发 source 校验失败，则 C1 阻断。