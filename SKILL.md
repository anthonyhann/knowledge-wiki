---
name: knowledge-wiki
description: "团队知识库全生命周期管理工具（知识编译器 v1.0.0），支持零门槛录入、索引加速查询、严格溯源问答、双向引用维护、一致性检查、操作日志追踪六大编译能力。当用户需要录入知识、查询知识库、检查知识腐烂、扫描外部源变更、检查知识一致性、查看覆盖率或问答缺口时使用。触发词：/knowledge-wiki、知识录入、知识库查询、知识库健康、查知识库、记录到知识库、知识沉淀、knowledge wiki、kb init、kb health、知识库初始化、帮我建知识库、把这个记到知识库、知识库里有没有、检查过期文档、知识库lint、索引重建。明确指令：/knowledge-wiki（直接触发本 skill）。NOT for: 私域笔记/日记、实时聊天/群消息记录、与项目代码无关的会议纪要、临时草稿（用户本地剪贴板内容）。"
trigger: /knowledge-wiki
allowed-tools:
  - Read
  - Write
  - Edit
  - run_terminal_cmd
---

# /knowledge-wiki

团队知识库管理 skill（知识编译器），六大核心能力通过子命令路由：

**前置检查**：除 `init` 外，所有子命令执行前先确认 `.knowledge/` 目录存在，不存在则提示："知识库未初始化，请先运行 /knowledge-wiki init"，中止当前命令。

| 子命令前缀 | 能力 | 一句话说明 |
|-----------|------|------------|
| `init` | 初始化 | 工具检查 + 创建 .knowledge/ 目录（含 .index/.logs/.pending-backlinks） + 安装 git hooks |
| `in` | 录入 | 任意输入 → 结构化知识文档 + 索引更新 + 日志记录 + 反向引用入队 |
| `ask` | 查询 | 索引预筛 + rg 关键词匹配 + 语义筛选，无记录不猜测 + 操作日志记录 |
| `health` | 维护 | 腐烂检测 + 外部源扫描 + 覆盖率 + **一致性检查(lint)** + **反向引用消费** + **索引重建** + **日志聚合** |

## 资源索引

> AI 注意：所有详细规则**以 references/ 文件为唯一权威源**。SKILL.md 只承载入口、铁律、子命令骨架；具体步骤、表格、模板严格照引用文件，禁止内联重述。

| 路径 | 用途 | 何时用 |
|------|------|------|
| `references/directory-structure.md` | `.knowledge/` 完整目录框架（含 .index/.logs/.pending-backlinks）+ 根文件模板 | `init` Step 1-2 |
| `references/url-handling.md` | URL 处理规则 + 飞书/公网子流程 + scan 路由 | `in <url>` 与 `health scan` |
| `references/ingestion-rules.md` | AI 结构化流程（含 index 更新/log 追加/backlink 入队步骤） | `in` 写入逻辑 |
| `references/index-rules.md` | 分段索引规则（按 type 分 idx 文件 / 写入/读取/重建） | `in` Step 9.5 / `ask` Layer -1 / `health index-rebuild` |
| `references/log-rules.md` | 操作日志规则（按人分文件 / 格式/归档/digest 聚合） | 所有子命令写入 / `health` 聚合 |
| `references/backlink-rules.md` | 双向 related 回写规则（pending 队列 / 延迟消费 / 上限控制） | `in` Step 9.5 入队 / `health backlink-consume` 消费 |
| `references/lint-rules.md` | 一致性检查规则（矛盾检测 L1-L9 / --fix 安全边界） | `health lint` |
| `references/templates/_registry.yaml` | 模板注册表（type → 模板文件 + 必填段 + 质量门禁） | `in` Step 2.5 / 8.5 |
| `references/templates/{type}.md` | 各 type 专属正文骨架模板（含 synthesis 共 9 个） | `in` Step 5 正文生成 |
| `references/ask-rules.md` | 三层检索（含 Index Layer -1）+ 标准回答 + 时效计算 + links/refs + log 记录 | `ask` 全部 |
| `references/health-rules.md` | rot/scan/coverage/audit/deprecate/lint/backlink-consume/index-rebuild 流程 | `health` 全部 |
| `references/templates/_meta.yaml.tpl` | 索引元数据初始化模板 | `init` Step 2 系统目录配置 |
| `references/templates/_logs_config.yaml.tpl` | 日志配置初始化模板 | `init` Step 2 系统目录配置 |
| `references/templates/_pending_backlinks.yaml.tpl` | 空队列初始化模板 | `init` Step 2 系统目录配置 |
| `references/templates/_idx_empty.md.tpl` | 通用 idx 表头模板 | `init` Step 2 创建空 idx 文件 |
| `references/scripts/check-deps.sh` | 工具依赖检查 + 一键安装 | `init` Step 0 |
| `references/scripts/pre-commit.sh` | pre-commit hook（L2 悬空引用 + L5 孤儿索引检测，<2s） | `init` Step 3 |
| `references/scripts/post-merge.sh` | post-merge hook（索引重建提示） | `init` Step 3 |
| `references/scripts/pre-push.sh` | pre-push hook（过期/外部源阻断确认） | `init` Step 3 |
| `references/scripts/commit-msg.sh` | commit-msg hook（[kb] 标记提示） | `init` Step 3 |

---

## 子命令速查

```bash
# 初始化
/knowledge-wiki init

# 录入
/knowledge-wiki in <任意输入>
/knowledge-wiki in --update <slug>
/knowledge-wiki in source add <url> [--name <>]
/knowledge-wiki in source list
/knowledge-wiki in source remove <id>
/knowledge-wiki in --from-answer "{简短描述}"    # [v0.8.0 新增] Ask 回流录入

# 查询
/knowledge-wiki ask "<问题>"
/knowledge-wiki ask links <slug>        # 反向追溯：谁引用了这篇
/knowledge-wiki ask refs <slug>         # 正向追溯：这篇引用了谁

# 维护
/knowledge-wiki health                  # 综合健康报告（含 lint 摘要 + pending 积压提示 + digest 重建）
/knowledge-wiki health --json           # JSON 格式输出（供 CI/外部工具消费）
/knowledge-wiki health --verbose        # 含 ASCII 图表的详细模式
/knowledge-wiki health rot              # 扫描过期/即将过期文档
/knowledge-wiki health scan             # 检测外部知识源变更
/knowledge-wiki health coverage         # 知识覆盖率报告（含问答缺口分析）
/knowledge-wiki health audit <slug>     # 确认文档有效，升级为 active
/knowledge-wiki health deprecate <slug> # 标记文档废弃
/knowledge-wiki health lint             # 一致性检查（矛盾/悬空引用/状态不一致等 L1-L9）
/knowledge-wiki health lint --fix       # lint 安全自动修复（仅 L3 废弃标记 + L8 idx 同步）
/knowledge-wiki health backlink-consume # 消费反向引用队列（批量回写 related）
/knowledge-wiki health index-rebuild    # 全量重建分段索引
/knowledge-wiki health distill          # [v0.9.0 新增] 认知蒸馏预览（重复检测+低质量+孤立知识）
/knowledge-wiki health distill --execute # 执行蒸馏（需用户确认）
```

### 未知/缺参兜底（统一错误响应）

| 错误形态 | 触发条件 | 响应 |
|---------|---------|------|
| 未知子命令 | 首段非 `init`/`in`/`ask`/`health` | 输出「未知子命令: {x}，可用：init / in / ask / health」+ 速查表，不执行任何 IO |
| `ask` 缺参 | `/knowledge-wiki ask` 后无问题文本 | 输出「ask 需要查询内容，例：/knowledge-wiki ask "打印超时配置"」，中止 |
| `in --update` 缺 slug | `/knowledge-wiki in --update` 无 slug | 输出「--update 需要 slug，可用 `ls .knowledge/*/` 查看现有 slug」，中止 |
| `health audit/deprecate` 缺 slug | 无 slug 参数 | 同上，提示先用 `health rot` 或 `health` 查文档清单 |
| `in source` 子命令缺参 | `add` 缺 url / `remove` 缺 id | 各自输出对应 usage 一行，中止 |

> 所有错误响应一律单行 + 速查链接，不调用任何 rg / 文件读写。

---

## /knowledge-wiki init

初始化 `.knowledge/` 目录结构、检查工具依赖并安装 git hooks。**Step 0 工具检查未通过时禁止进入 Step 1**。

### Step 0：工具依赖检查（必跑）

执行 `bash references/scripts/check-deps.sh`，按退出码处理：

| 退出码 | 动作 |
|------|------|
| 0 | 继续 Step 1 |
| 1（缺必需工具） | Interactive: 四选一（一键安装/手动重试/中止/跳过hook仅创建目录）；Non-interactive: 中止 |
| 其他 | 中止 init |

**交互模式**：TTY 且非 CI → Interactive（等用户选择）；`CI=true` / `NONINTERACTIVE=1` → Non-interactive（走最安全选项）。

**工具两组**：A 核心（rg REQUIRED + git REQUIRED + jq OPTIONAL）；B 浏览器（agent-browser 等任选一，飞书/公网 URL 均走浏览器自动化）。

> 完整工具清单、一键安装命令、各组详细说明见 `references/scripts/check-deps.sh` 内注释。

### Step 1：创建目录结构

完整目录树、目录职责速查、4 个根文件模板见 **`references/directory-structure.md`**。

执行要点：
1. 在仓库根创建 8 个业务目录 + 1 个 synthesis 目录：`mkdir -p .knowledge/{glossary,design,requirements,flows,apis,db,ops,case,synthesis}`
2. 业务目录与 type 字段一一对应（详见 `directory-structure.md`「目录职责速查」表）

### Step 2：写入根文件模板

按 `references/directory-structure.md` 中「根文件模板」节的内容，生成 4 个文件并写入仓库根：

| 文件 | 用途 |
|------|------|
| `.knowledge/README.md` | 双受众入口（AI 导航 + 人类指引） |
| `.knowledge/CLAUDE.md` | AI 协作契约（黄金原则 + 禁止行为） |
| `.knowledge/AGENTS.md` | AI 地图（≤50 行精简版） |
| `.knowledge/.sources.yaml` | 外部知识源注册表（初始 `sources: []`） |

> 模板内容**严格照抄** `references/directory-structure.md`，不在本 SKILL.md 中重复内联，避免漂移。

### Step 3：安装 git hooks

**前置检测**：执行 `git rev-parse --git-dir 2>/dev/null`：
- 返回非零 → 当前不在 git 仓库，跳过 hook 安装，输出提示："检测到当前目录不是 git 仓库，hook 安装跳过。后续在项目中运行 `git init` 后可手动复制 references/scripts/ 下脚本。"
- 返回零 → 继续安装

若 hook 文件已存在：Interactive 模式询问 `[1] 覆盖  [2] 追加  [3] 跳过`；Non-interactive 模式默认 `[3] 跳过`（保护用户既有 hook 不被覆盖）。

| Hook | 行为 | 脚本路径 |
|------|------|---------|
| `pre-push` | 阻断式确认：检查 `expires` ≤7 天的文档 + `last_synced` >30 天的外部源；有问题三选一（处理/跳过/中止），无问题静默放行 | `references/scripts/pre-push.sh` |
| `commit-msg` | 非阻断：commit message 含 `[kb]` 时 rg 搜索知识库相关文档，输出更新建议 | `references/scripts/commit-msg.sh` |
| `pre-commit` | 轻量 lint（<2s）：仅检查 L2 悬空引用 + L5 孤儿索引；ERROR 阻断，WARNING 仅提示 | `references/scripts/pre-commit.sh` |
| `post-merge` | 非阻断提示：合并后检测知识库变更数，建议 index-rebuild（变更 >3 个文档或索引 >30 天） | `references/scripts/post-merge.sh` |

复制方式：`cp references/scripts/{pre-push,commit-msg,pre-commit,post-merge}.sh .git/hooks/ && chmod +x .git/hooks/{pre-push,commit-msg,pre-commit,post-merge}`。

### Step 4：自我校验 + 输出安装摘要

init 完成后自动执行 8 项校验（目录/文件/配置/hooks），任一项失败输出 WARNING（不中止）。

**校验脚本实现规范**：遍历时**必须用 Bash 数组**（`dirs=(glossary design ...)`），禁止字符串变量 + `for d in $dirs`；路径用相对仓库根。

> 完整 8 项校验清单 + 通过/失败输出模板见 `references/directory-structure.md`「init 校验」节。

---

## /knowledge-wiki in（录入）

### 输入类型判断

```
以 http:// 或 https:// 开头  → URL 处理（详见 references/url-handling.md）
以 ./ 或 / 开头，或文件路径存在  → 文件处理（路径不存在则提示"文件未找到: <path>"，中止）
其余                          → 文本处理
```

**输入大小护栏**（任一输入类型）：

| 输入类型 | 阈值 | 动作 |
|---------|------|------|
| 文件 | > 10 MB | 中止，提示"文件过大（{size}），请拆分后重试或改用文本输入摘要" |
| 文本 | > 100 KB（约 5 万字） | 中止，提示"文本输入过长（{size}），请压到 100KB 以内或改用文件输入（< 10MB）" |
| URL 抽取后正文 | > 200 KB | 截断到 200 KB（保留头部），在 sources 字段追加"原始正文已截断至 200KB，YYYY-MM-DD" |

### URL 处理（按域名路由浏览器自动化）

| URL 域名 | 必走工具 |
|---------|---------|
| larkoffice.com / feishu.cn | agent-browser |
| apipost.net | agent-browser（遍历目录树） |
| 其他公网 URL | agent-browser |

飞书 URL：agent-browser goto + HTTP 状态/登录检测/选择器/去噪。完整子流程、错误码处理、选择器表、去噪规则见 **`references/url-handling.md`**。

### 文件处理

| 文件类型 | 处理方式 |
|---------|---------|
| .go / .php / .ts / .py 等代码文件 | 提炼设计知识（不复制代码原文） |
| .md / .txt | 直接处理正文 |

> 文件大小限制由上方「输入大小护栏」表统一管理，本节不重复。

### AI 结构化流程（14 步，含模板加载、质量门禁、索引、日志、反向引用）

URL / 文件 / 文本三种输入殊途同归，进入统一的 AI 结构化流程：

```
1. 提取 title
2. 推断 type（详见 references/ingestion-rules.md「type 推断规则」）
2.5 加载 type 专属模板（references/templates/_registry.yaml → templates/{type}.md）
2.6 [仅当 type=glossary] 去重前置检查（详见 ingestion-rules.md「Step 2.6」）
2.65 [所有 type 均执行] 全类型相似检测前置（详见 ingestion-rules.md「Step 2.65」）[v0.9.0]
2.7 [所有 type 均执行] 跨类型术语抽取（详见 ingestion-rules.md「Step 2.7」）
3. 提取 tags（3-5 个）
4. 生成 TL;DR（50-100 词，必填）
5. 按模板骨架整理详情正文（required_sections 不可缺，optional_sections 视内容补充）
6. 扫描 .knowledge/ 推荐 related（rg 模板见 ingestion-rules.md）
7. 生成 slug（详见 ingestion-rules.md「slug 生成规则」）
8. 若目标文件已存在 → 询问：覆盖 / 追加 / 中止
8.5 质量门禁：校验 _registry.yaml 中 required_sections 与 quality_gate；缺失即返回用户补充
9. 写入 .knowledge/{对应目录}/{slug}.md
9.5 [NEW] 更新分段索引：追加条目到 .index/{type}.idx.md（详见 index-rules.md）
9.6 [NEW] 反向引用入队：若 related ≥1，将回写请求写入 .pending-backlinks.yaml（详见 backlink-rules.md）
10 [NEW] 追加操作日志：写入 .logs/personal/{mis-id}.md（详见 log-rules.md）
```

> 各步骤详细规则（模板加载 / 相似检测 / 术语抽取 / 质量门禁）见 `references/ingestion-rules.md`。核心约束：**禁止**用统一二段式替代 type 模板；8.5 门禁不达标则**中止写入**。

**完整 type 推断优先级、slug 5 条规则、frontmatter 模板、录入确认输出**见 **`references/ingestion-rules.md`**；**各 type（含 synthesis）的正文骨架**见 **`references/templates/`** 各个 `.md` 模板文件。

### --update <slug>

更新已有条目。变更预览三选一（覆盖/追加新版本节/中止）+ 字段保留规则见 `references/ingestion-rules.md`。

### source 管理

`source add` / `list` / `remove` 三个子命令。`remove` 前必须 rg 查找引用，有引用时三选一（仅删源/删源+追加移除标记/中止）。`.sources.yaml` 格式与示例见 `references/ingestion-rules.md`。

---

## /knowledge-wiki ask（查询）

### 检索三层（详见 references/ask-rules.md）

- **Layer -1** [NEW]：Index 预筛选——从问题推断最可能的 1-2 个 idx 文件，读取后做 title/tags/TL;DR 子串匹配；命中则限定 Layer 0 的 rg 搜索范围；未命中或无法推断时跳过（退化为原有行为）。详见 `references/index-rules.md`「读取规则」。
- **Layer 0**：rg 关键词匹配，最多 3 轮（原始关键词 → 词根+同义词 → 拼音+frontmatter）；若 Layer -1 已限定范围，rg 仅在对应目录内搜索。
- **Layer 0.5**（兜底，1 轮）：Layer 0 全失败时再做一次 frontmatter title/tags 子串模糊匹配；仍 0 命中 → 输出「知识库无记录」模板，**禁止用模型训练知识填补**。
- **Layer 1**：Claude 语义筛选命中文件的 frontmatter+TL;DR，选 1-3 篇读全文生成回答。

**status 优先级**：`canonical > active > draft > deprecated`（deprecated 禁止引用）

**[NEW] 操作日志**：每次 ask 完成后自动追加一条记录到 `.logs/personal/{mis-id}.md`（ask 内容做 hash 脱敏）。详见 `references/log-rules.md`。

### 标准回答、时效计算、无记录拒答

回答必含 5 元素（结论 + 来源路径 + 录入人 + 时效状态 + 引用链）。无记录时按 C1 约束拒答，**禁止用模型知识填补**。

> 标准回答格式、时效计算公式（FRESH/WARNING/EXPIRED）、无记录拒答模板、links/refs 命令详见 `references/ask-rules.md`。

---

## /knowledge-wiki health（维护）

### 综合报告（`health` 无子命令时执行）

顺序执行 10 步（digest重建 → 统计 → rot → coverage → 外部源 → lint → 进化建议 → 反向引用 → 索引 → 日志）后输出格式化报告。

> 完整 10 步流程 + 输出模板（含真实数据示例）详见 `references/health-rules.md`「综合报告」。

### 子命令矩阵

| 子命令 | 行为 | 详细规则 |
|------|------|---------|
| `rot` | 扫描过期文档；EXPIRED/WARNING 列表 + 批量决策入口（逐篇/批量延期/批量废弃/仅列表） | `references/health-rules.md` |
| `scan` | 遍历 `.sources.yaml` 中 active 源；按域名路由浏览器自动化；diff 提示三选一 | `references/url-handling.md` + `references/health-rules.md` |
| `coverage` | 以 git 根为锚点扫描顶层目录 + **问答缺口分析**（基于 log 数据） | `references/health-rules.md` + `references/log-rules.md` |
| `audit <slug>` | 三选一：确认有效（→active；expires 按 type 分支续期）/ 需要更新 / 已废弃 | `references/health-rules.md` |
| `deprecate <slug>` | rg 查所有引用 → 确认后 status=deprecated + 引用处追加注释 + 清理 pending 队列 | `references/health-rules.md` + `references/backlink-rules.md` |
| **`lint`** [NEW] | **L1-L9 一致性全量检查：矛盾检测/悬空引用/废弃标记/孤儿/related 膨胀/pending 积压/status 不一致/过期未处理** | `references/lint-rules.md` |
| **`lint --fix`** [NEW] | **安全自动修复：L3 废弃引用加删除线 + L8 idx status 同步**；先 dry-run 展示变更预览清单（文件路径 + 修改内容摘要），**等用户确认**后执行 | `references/lint-rules.md` |
| **`backlink-consume`** [NEW] | **消费 .pending-backlinks.yaml 队列，批量回写 related 到目标文档**；执行前展示待消费条目数 + 影响文档列表，**等用户确认** | `references/backlink-rules.md` |
| **`index-rebuild`** [NEW] | **全量重建所有 .index/*.idx.md + 一致性校验（孤儿检测/status 同步）**；执行前展示当前 idx 状态摘要，**等用户确认** | `references/index-rules.md` |
| **`distill`** [NEW v0.9.0] | **认知蒸馏：Jaccard 重复检测 + 低质量清理 + 孤立知识检测**；默认预览不修改，`--execute` 逐步确认后执行合并/废弃/关联 | `references/health-rules.md` |

> `rot` 无问题时**完全静默**；`scan` 不自动更新，所有变更由用户决策；`coverage` 仅建议不阻断；`lint` 只报告不修改（除 `--fix`）；`backlink-consume` 确认后修改 wiki 文件的 frontmatter 并自动 commit；`index-rebuild` 确认后覆写所有 idx 文件；`distill` 默认只预览，`--execute` 需逐步确认。

### 异常恢复（修改性子命令）

| 子命令 | 失败场景 | 恢复策略 |
|--------|---------|---------|
| `backlink-consume` | git commit 失败（脏工作区/合并冲突） | `git stash` → 重试 commit → 仍失败则中止并输出 `git stash pop` 恢复命令 |
| `backlink-consume` | 目标文件被外部删除（写入时 .md 不存在） | 跳过该条目 + WARNING + 标记 consumed（防止无限重试） |
| `index-rebuild` | 覆写中断（磁盘满/权限不足） | 保留部分写入的 idx（不删除已成功的文件），输出恢复命令：`/knowledge-wiki health index-rebuild`（幂等，可安全重跑） |
| `lint --fix` | 文件写入失败 | 单文件失败不影响其他文件，输出失败清单 + 手动修复建议 |
| 通用 | `.knowledge/` 目录不存在 | 中止 + 提示 `/knowledge-wiki init` |

### lint / coverage 详细模板

> lint L1-L9 检查项表格、输出格式、`--fix` dry-run 预览模板 → 详见 **`references/lint-rules.md`**
>
> coverage 输出模板（含模块覆盖 + 问答缺口分析）→ 详见 **`references/health-rules.md`**「coverage 增强版」

---

## 执行原则

### 🔴 核心不变量（违反即为 Bug，任何流程不可豁免）

| # | 原则 | 说明 |
|---|------|------|
| C1 | **无来源不写、不答** | sources 必填；ask 无记录时明确告知，不猜测 |
| C2 | **术语唯一** | 录入前检查 glossary/ 是否已存在同义定义 |
| C3 | **草稿优先** | 新录入一律 status=draft，由 health audit 升级到 active |
| C4 | **模板为合约** | 正文必须严格按 `references/templates/{type}.md` 骨架生成；AI 不允许增删一级标题，必填段不齐时 8.5 门禁拦截 |
| C5 | **操作留痕** | 所有 in/ask/health 操作写入 `.logs/personal/{mis-id}.md`；ask 内容 hash 脱敏 |

### 🟡 扩展行为（可软降级，故障不阻断主流程）

| # | 原则 | 说明 | 降级策略 |
|---|------|------|---------|
| E1 | **静默放行** | hook / rot 无问题时完全不输出 | — |
| E2 | **索引辅助** | `.index/` 为 Layer -1 预筛选层，增强 rg 而非替代它 | idx 更新失败 → WARNING + 标记 stale，不阻断 in |
| E3 | **延迟回写** | 反向引用写入 `.pending-backlinks.yaml` 队列 | 队列写入失败 → WARNING，不阻断 in |
| E4 | **集中式 lint** | 矛盾检测只在 `health lint` 执行 | 不在 in/ask 流程中阻断 |
| E5 | **deprecate 必处理引用** | 废弃前 rg 查所有引用处 | — |
| E6 | **工具检查门** | `init` Step 0 必跑 check-deps.sh | 缺必需工具时中止 init |

> **优先级**：当 C 级与 E 级冲突时，始终以 C 级为准。例如 idx 更新 (E2) 若引发 source 校验失败，则 C1 阻断。