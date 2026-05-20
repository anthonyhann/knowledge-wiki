---
name: knowledge-wiki
description: "团队知识库全生命周期管理工具，支持零门槛录入、严格溯源问答、健康维护三大能力。当用户需要录入知识、查询知识库、检查知识腐烂、扫描外部源变更时使用。触发词：/knowledge-wiki、知识录入、知识库查询、知识库健康、查知识库、记录到知识库、知识沉淀。明确指令：/knowledge-wiki（直接触发本 skill）"
trigger: /knowledge-wiki
---

# /knowledge-wiki

团队知识库管理 skill，三个核心能力通过子命令路由：

**前置检查**：除 `init` 外，所有子命令执行前先确认 `.knowledge/` 目录存在，不存在则提示："知识库未初始化，请先运行 /knowledge-wiki init"，中止当前命令。

| 子命令前缀 | 能力 | 一句话说明 |
|-----------|------|------------|
| `init` | 初始化 | 工具检查 + 创建 .knowledge/ 目录 + 安装 git hooks |
| `in` | 录入 | 任意输入 → 结构化知识文档 |
| `ask` | 查询 | 严格溯源问答，无记录不猜测 |
| `health` | 维护 | 腐烂检测 + 外部源扫描 + 覆盖率 |

## 资源索引

> AI 注意：所有详细规则**以 references/ 文件为唯一权威源**。SKILL.md 只承载入口、铁律、子命令骨架；具体步骤、表格、模板严格照引用文件，禁止内联重述。

| 路径 | 用途 | 何时用 |
|------|------|------|
| `references/directory-structure.md` | `.knowledge/` 目录框架 + 4 个根文件模板 | `init` Step 1-2 |
| `references/url-handling.md` | URL 处理铁律 + 飞书文档/通用子流程 + scan 路由 | `in <url>` 与 `health scan` |
| `references/ingestion-rules.md` | AI 结构化 11 步 + slug + type + frontmatter + source 管理 | `in` 写入逻辑 |
| `references/templates/_registry.yaml` | 模板注册表（type → 模板文件 + 必填段 + 质量门禁） | `in` Step 2.5 / 8.5 |
| `references/templates/{type}.md` | 12 个 type 专属正文骨架模板 | `in` Step 5 正文生成 |
| `references/ask-rules.md` | 两层检索 + 标准回答 + 时效计算 + links/refs | `ask` 全部 |
| `references/health-rules.md` | rot/scan/coverage/audit/deprecate 流程 | `health` 全部 |
| `references/scripts/check-deps.sh` | 工具依赖检查 + 一键安装 | `init` Step 0 |
| `references/scripts/pre-push.sh` | git pre-push hook | `init` Step 3 |
| `references/scripts/commit-msg.sh` | git commit-msg hook | `init` Step 3 |

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

# 查询
/knowledge-wiki ask "<问题>"
/knowledge-wiki ask links <slug>        # 反向追溯：谁引用了这篇
/knowledge-wiki ask refs <slug>         # 正向追溯：这篇引用了谁

# 维护
/knowledge-wiki health                  # 综合健康报告
/knowledge-wiki health rot              # 扫描过期/即将过期文档
/knowledge-wiki health scan             # 检测外部知识源变更
/knowledge-wiki health coverage         # 知识覆盖率报告
/knowledge-wiki health audit <slug>     # 确认文档有效，升级为 active
/knowledge-wiki health deprecate <slug> # 标记文档废弃
```

---

## /knowledge-wiki init

初始化 `.knowledge/` 目录结构、检查工具依赖并安装 git hooks。**Step 0 工具检查未通过时禁止进入 Step 1**。

### Step 0：工具依赖检查（必跑）

执行 `bash references/scripts/check-deps.sh`，按退出码处理：

| 退出码 | 含义 | 动作 |
|------|------|------|
| 0 | 必需工具齐全（可选工具可缺） | 继续 Step 1 |
| 1 | 缺必需工具（如 rg / git） | 输出脚本提示的安装命令；询问 `[1] 一键安装（执行 check-deps.sh --install）  [2] 手动安装后重试  [3] 中止 init` |
| 其他 | 脚本异常 | 输出错误信息，中止 init |

**工具清单（三组）**：

**Group A — 核心工具**

| 工具 | 必需性 | 用途 | 缺失影响 |
|------|------|------|---------|
| `rg`（ripgrep） | REQUIRED | 关键词检索/追溯（ask/links/refs/deprecate） | 无法检索，init 中止 |
| `git` | REQUIRED | hook 安装与 commit-msg 触发 | 无法安装 hook，init 中止 |
| `jq` | OPTIONAL | hook 脚本解析 frontmatter | hook 部分功能降级，不阻断 |

**Group B — 浏览器自动化生态**（处理 URL；任选其一即可，全部缺失才警告）

| 工具 | 定位关键词 | 适用场景 | 安装命令（mac/linux） |
|------|----------|---------|---------|
| `agent-browser` | AI 工具调用的极速瑞士军刀（轻量·ref 引用·50+ 命令） | AI 调用首选；URL 抽取通用 | `npm i -g @aigc/agent-browser` |
| `browser-harness` | AI 编程助手的自愈浏览器手（Claude Code·自愈·动态页面） | 选择器易变 / 动态渲染页面 | `npm i -g @aigc/browser-harness` |
| `playwright` | 工程化测试的坚实基石（E2E·稳定·详细报告） | 流程固定的录入/扫描自动化 | `npm i -g playwright && npx playwright install chromium` |
| `browser-use` | LLM 自主操作的完整大脑（Python·规划·Deep Research） | 多步骤 LLM 自主决策录入 | `pipx install browser-use` |
| `page-agent` | 中文网页理解的领域专家（中文优化·多模态） | 中文网页站点 | `npm i -g page-agent` |

> Group B 全部为 OPTIONAL；脚本检测到「全部未装」时输出选型建议+安装清单，「至少一个已装」时主流程不阻断。

**一键安装命令**：

```bash
bash references/scripts/check-deps.sh                  # 仅检查
bash references/scripts/check-deps.sh --install        # 安装缺失的必需工具（Group A REQUIRED）
bash references/scripts/check-deps.sh --install-browser # 安装缺失的全部浏览器工具（Group B 整组）
```

脚本自动按当前 OS（macOS=brew / Linux=apt|yum / npm / pipx）选择安装命令。

### Step 1：创建目录结构

完整目录树、目录职责速查、4 个根文件模板见 **`references/directory-structure.md`**。

执行要点：
1. 在仓库根创建 11 个业务目录：`mkdir -p .knowledge/{glossary,design,requirements,flows,apis,data,ops,incidents,bizrules,meetings,people}`
2. `people/{user-id}/` 不预创建，按需生成
3. 业务目录与 type 字段一一对应（详见 `directory-structure.md`「目录职责速查」表）

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

若 hook 文件已存在，询问：`[1] 覆盖  [2] 追加  [3] 跳过`

| Hook | 行为 | 脚本路径 |
|------|------|---------|
| `pre-push` | 阻断式确认：检查 `expires` ≤7 天的文档 + `last_synced` >30 天的外部源；有问题三选一（处理/跳过/中止），无问题静默放行 | `references/scripts/pre-push.sh` |
| `commit-msg` | 非阻断：commit message 含 `[kb]` 时 rg 搜索知识库相关文档，输出更新建议 | `references/scripts/commit-msg.sh` |

复制方式：`cp references/scripts/{pre-push,commit-msg}.sh .git/hooks/ && chmod +x .git/hooks/{pre-push,commit-msg}`。

### Step 4：输出安装摘要

```
✓ 工具依赖检查通过（rg / git / agent-browser）
✓ .knowledge/ 目录结构已创建（11 个目录 + 4 个根文件）
✓ .git/hooks/pre-push 已安装
✓ .git/hooks/commit-msg 已安装

下一步：
  /knowledge-wiki in <内容>    开始录入知识
  /knowledge-wiki ask <问题>   查询知识库
  /knowledge-wiki health       检查知识库健康状态
```

---

## /knowledge-wiki in（录入）

### 输入类型判断

```
以 http:// 或 https:// 开头  → URL 处理（详见 references/url-handling.md）
以 ./ 或 / 开头，或文件路径存在  → 文件处理（路径不存在则提示"文件未找到: <path>"，中止）
其余                          → 文本处理
```

### URL 处理

| URL 域名 | 必走工具 |
|---------|---------|
| xxx.feishu.cn / feishu.cn / larkoffice.com | agent-browser |
| apipost.net | agent-browser（遍历目录树） |
| 其他公网 URL | agent-browser |

agent-browser goto + HTTP 状态/登录检测/选择器/去噪。完整子流程、错误码处理、选择器表、去噪规则见 **`references/url-handling.md`**。

### 文件处理

| 文件类型 | 处理方式 |
|---------|---------|
| .go / .php / .ts / .py 等代码文件 | 提炼设计知识（不复制代码原文） |
| .md / .txt | 直接处理正文 |
| 单文件 >10 MB | 中止，提示"文件过大（{size}），请拆分后重试或改用文本输入摘要" |

### AI 结构化流程（11 步，含模板加载与质量门禁）

URL / 文件 / 文本三种输入殊途同归，进入统一的 AI 结构化流程：

```
1. 提取 title
2. 推断 type（详见 references/ingestion-rules.md「type 推断规则」）
2.5 加载 type 专属模板（references/templates/_registry.yaml → templates/{type}.md）
3. 提取 tags（3-5 个）
4. 生成 TL;DR（50-100 词，必填）
5. 按模板骨架整理详情正文（required_sections 不可缺，optional_sections 视内容补充）
6. 扫描 .knowledge/ 推荐 related（rg 模板见 ingestion-rules.md）
7. 生成 slug（详见 ingestion-rules.md「slug 生成规则」）
8. 若目标文件已存在 → 询问：覆盖 / 追加 / 中止
8.5 质量门禁：校验 _registry.yaml 中 required_sections 与 quality_gate；缺失即返回用户补充
9. 写入 .knowledge/{对应目录}/{slug}.md
```

> **2.5 步为模板加载**：AI 读 `references/templates/_registry.yaml` 定位到 `templates/{type}.md`，按其 `required_sections` 与 `optional_sections` 骨架生成正文。**禁止**用「TL;DR + 详情」二段式覆盖所有 type。
>
> **8.5 步为质量门禁**：写入前逐项检查必填段是否齐备并运行 `quality_gate` 文本校验（如 "glossary 必含技术字段名映射"）。任一项不达标则中止写入。

**完整 type 推断 12 级优先级、slug 5 条规则、frontmatter 模板、录入确认输出**见 **`references/ingestion-rules.md`**；**12 个 type 的正文骨架**见 **`references/templates/`** 各个 `.md` 模板文件。

### --update <slug>

更新已有条目。变更预览三选一（覆盖/追加新版本节/中止）+ 字段保留规则见 `references/ingestion-rules.md`。

### source 管理

`source add` / `list` / `remove` 三个子命令。`remove` 前必须 rg 查找引用，有引用时三选一（仅删源/删源+追加移除标记/中止）。`.sources.yaml` 格式与示例见 `references/ingestion-rules.md`。

---

## /knowledge-wiki ask（查询）

### 检索两层（详见 references/ask-rules.md）

- **Layer 0**：rg 关键词匹配，最多 3 轮（原始关键词 → 词根+同义词 → 拼音+frontmatter）。3 轮 0 命中 → 输出「知识库无记录」模板，**禁止用模型训练知识填补**。
- **Layer 1**：Claude 语义筛选命中文件的 frontmatter+TL;DR，选 1-3 篇读全文生成回答。

**status 优先级**：`canonical > active > draft > deprecated`（deprecated 禁止引用）

### 标准回答格式（必含 5 元素）

```
回答：{核心结论一句话}
来源：.knowledge/<dir>/<slug>.md（第 N 行）
录入：@<owner>，YYYY-MM-DD
状态：FRESH | WARNING | EXPIRED（距过期 N 天）
被引用：[[slug-A]]（X 处）  引用了：[[slug-B]]（Y 处）
```

时效计算示例（FRESH/WARNING/EXPIRED）、无记录模板、links/refs 命令模板见 **`references/ask-rules.md`**。

---

## /knowledge-wiki health（维护）

### 综合报告

```
📊 知识库健康报告（YYYY-MM-DD）
文档总数：N 篇（active: X  draft: Y  deprecated: Z）
[腐烂检测]  EXPIRED N 篇 | WARNING N 篇
[覆盖率]    未覆盖模块：A / B / C
[外部源]    N 个源，上次扫描 N 天前
```

### 子命令矩阵

| 子命令 | 行为 | 详细规则 |
|------|------|---------|
| `rot` | 扫描过期文档；EXPIRED/WARNING 列表 + 批量决策入口（逐篇/批量延期/批量废弃/仅列表） | `references/health-rules.md` |
| `scan` | 遍历 `.sources.yaml` 中 active 源；按域名路由（详见 references/url-handling.md）；diff 提示三选一 | `references/url-handling.md` + `references/health-rules.md` |
| `coverage` | 以 git 根为锚点扫描顶层目录与 `.knowledge/` tags 比对，输出未覆盖模块 | `references/health-rules.md` |
| `audit <slug>` | 三选一：确认有效（→active+expires+90d）/ 需要更新 / 已废弃 | `references/health-rules.md` |
| `deprecate <slug>` | rg 查所有引用 → 确认后 status=deprecated + 引用处追加注释 | `references/health-rules.md` |[]()

> `rot` 无问题时**完全静默**；`scan` 不自动更新，所有变更由用户决策；`coverage` 仅建议不阻断。

---

## 执行原则

1. **无来源不写、不答** — sources 必填；ask 无记录时明确告知，不猜测
2. **术语唯一** — 录入时检查 glossary/ 是否已存在同义定义
3. **草稿优先** — 新录入一律 draft，由 health audit 升级
4. **静默放行** — hook 和 rot 无问题时完全不输出
5. **deprecate 必处理引用** — 废弃前用 rg 找出所有引用处
6. **rg 零索引** — 所有追溯直接扫描 Markdown，无需维护索引文件
7. **工具检查门** — `init` Step 0 必跑 check-deps.sh；缺必需工具时中止 init，不允许跳过
8. **模板为合约** — 录入正文必须严格按 `references/templates/{type}.md` 的骨架生成；AI 不允许自行增删一级标题，必填段不齐时 8.5 门禁拦截
