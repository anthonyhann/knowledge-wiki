<div align="center">

# 📚 knowledge-wiki

**团队知识全生命周期管理 — 零门槛录入、严格溯源、持续维护。**

[![Version](https://img.shields.io/badge/version-0.6.0-blue.svg)](./CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Claude Skill](https://img.shields.io/badge/claude-skill-orange.svg)](./SKILL.md)
[![Requires](https://img.shields.io/badge/requires-ripgrep%20%7C%20git-lightgrey.svg)](#工具依赖)

将飞书、Apipost、代码、会议中散落的内容沉淀为结构化、可检索、严格溯源的本地知识库 — 直接集成在 Claude Code 工作流中。

[快速开始](#快速开始) · [命令](#命令) · [模板库](#模板库) · [设计原则](#设计原则) · [更新日志](./CHANGELOG.md) · [English](./README.md)

</div>

---

## 为什么用 knowledge-wiki？

大多数团队都面临同样的三个问题：

| 问题 | 现状 | 解决方式 |
|------|------|---------|
| **知识散落** | 文档分散在飞书、Notion、群聊和脑子里 | 统一 `.knowledge/` 目录，一条命令录入 |
| **知识腐烂** | 过期文档悄悄误导决策 | 90 天有效期 + push 前 git hook 自动警告 |
| **录入门槛高** | 模板复杂，没人愿意写文档 | 类型自动推断 + AI 结构化，直接粘贴即可 |

---

## 快速开始

```bash
# 1. 进入项目根目录
cd ~/your-project

# 2. 初始化（检查工具、创建 .knowledge/、安装 git hooks）
/knowledge-wiki init

# 3. 录入第一条知识
/knowledge-wiki in "打印服务超时阈值是 30s，超时后 fallback 到本地缓存"

# 4. 查询
/knowledge-wiki ask "打印服务超时"

# 5. 随时做健康检查
/knowledge-wiki health
```

> [!TIP]
> `/knowledge-wiki init` 会自动检测缺失工具并提供一键安装。详见[工具依赖](#工具依赖)。

---

## 命令

### 概览

| 命令 | 功能 |
|------|------|
| [`init`](#init) | 检查工具 · 创建 `.knowledge/` · 安装 git hooks |
| [`in`](#录入) | 零门槛录入文字、URL、文件或代码 |
| [`ask`](#查询) | 严格溯源问答 — 无记录不猜测 |
| [`health`](#维护) | 腐烂检测 · 外部源扫描 · 覆盖率报告 |

### `init`

```bash
/knowledge-wiki init
```

运行 `check-deps.sh`，创建目录结构，并安装两个 git hooks。如缺少必需工具（`rg`、`git`），提供三选一：自动安装 / 手动安装后重试 / 中止。

### 录入

```bash
/knowledge-wiki in <文字|URL|文件路径>       # 智能录入，支持任意来源
/knowledge-wiki in --update <slug>           # 更新已有条目

/knowledge-wiki in source add <url> [--name <标签>]   # 注册外部知识源
/knowledge-wiki in source list
/knowledge-wiki in source remove <id>
```

### 查询

```bash
/knowledge-wiki ask "<问题>"                 # 严格溯源回答
/knowledge-wiki ask links <slug>             # 反向追溯：谁引用了这篇？
/knowledge-wiki ask refs <slug>              # 正向追溯：这篇引用了谁？
```

### 维护

```bash
/knowledge-wiki health                       # 综合健康报告
/knowledge-wiki health rot                   # 过期 / 即将过期文档
/knowledge-wiki health scan                  # 外部源变更检测
/knowledge-wiki health coverage              # 知识覆盖率报告
/knowledge-wiki health audit <slug>          # 确认有效 → 升级为 active
/knowledge-wiki health deprecate <slug>      # 标记文档废弃
```

---

## 目录结构

`init` 后项目根目录会新增：

```
.knowledge/
├── README.md               ← 双受众入口（顶部给 AI，底部给人类）
├── CLAUDE.md               ← AI 协作契约 + 禁止行为
├── AGENTS.md               ← AI 导航地图（≤50 行）
├── .sources.yaml           ← 外部知识源注册表
│
├── glossary/               ← 术语词典 — 全局唯一定义锚点，优先写这里
├── design/                 ← 架构 · 技术方案 · ADR（由 `type` 字段区分）
├── requirements/           ← 需求文档、PRD、验收标准
├── flows/                  ← 核心业务流程
├── apis/                   ← 接口约定、字段映射
├── data/                   ← 数据模型、DDL、存储文档
├── ops/                    ← 运维手册、告警、大促保障
├── incidents/              ← 故障复盘
├── bizrules/               ← 业务规则（运营 + 技术共用）
├── meetings/               ← 会议记录
└── people/{user-id}/       ← 个人上下文（AI 只读）
```

`design/` 通过 frontmatter `type` 字段区分三类文档：

| `type` | 适用场景 |
|--------|---------|
| `architecture` | 系统架构现状（活文档，持续更新） |
| `solution` | 某需求的技术方案（时间点快照） |
| `adr` | 架构决策记录 — 记录"为什么这样选" |

<details>
<summary>完整目录规范与根文件模板 →</summary>

完整目录树、目录职责速查、`README.md`、`CLAUDE.md`、`AGENTS.md` 和 `.sources.yaml` 的初始模板，见 [`references/directory-structure.md`](references/directory-structure.md)。

</details>

---

## 模板库

> [!NOTE]
> **v0.6.0 新增** — 12 个知识类型现在各有专属正文骨架，录入时强制执行。

不再使用"TL;DR + 详情"的万能二段式，每个类型都有针对性的结构：

| 模板 | 层级 | 内容 |
|------|------|------|
| `glossary.md` | L1 | 术语 · 同义词 · 技术字段映射 · 边界 |
| `architecture.md` | L1 | 服务拓扑 · 模块职责 · 依赖关系 |
| `adr.md` | L1 | 备选方案 · 取舍分析 · 决策后果 |
| `requirement.md` | L1 | 用户故事 · 验收标准 |
| `solution.md` | L2 | 背景目标 · 详细设计 · 影响面 |
| `flow.md` | L2 | 触发条件 · 主流程 · 异常分支 |
| `incident.md` | L2 | 时间线 · 5 Whys · 带负责人的改进措施 |
| `bizrule.md` | L2 | 适用条件 · 计算公式 · 历史变更 |
| `api.md` | L3 | 请求 · 响应 · 错误码 |
| `data.md` | L3 | DDL · 字段 · 索引 |
| `ops.md` | L3 | 超时 · 告警 · 限流 |
| `meeting.md` | — | 讨论要点 · 结论 · Action Items |

录入流程新增**两个关键节点**：

- **Step 2.5 — 模板加载**：AI 推断出 type 后，读取 `_registry.yaml` 定位匹配骨架，写入前先按模板整理正文。
- **Step 8.5 — 质量门禁**：逐项校验 `required_sections`，运行 `quality_gate` 检查，不达标时拦截并返回缺失清单。

**示例质量门禁：**

| 类型 | 门禁规则 |
|------|---------|
| `glossary` | 必须包含 ≥1 个技术字段名映射（后端 / 数据库 / 前端） |
| `incident` | 每条改进措施须有负责人和截止日；根因不能停留在表面现象 |
| `api` | 请求/响应字段必须标注类型；至少 1 个错误码 |
| `bizrule` | 逻辑必须可被代码实现 — 需包含具体公式或判断分支 |

<details>
<summary>完整注册表与门禁规范 →</summary>

所有 type 定义和门禁规则见 [`references/templates/_registry.yaml`](references/templates/_registry.yaml)。

设计取舍与 GSD Artifact Taxonomy 的对比见 [`DESIGN.md`](./DESIGN.md) — 第九节「模板库机制」。

</details>

---

## 文档格式

每条知识条目使用 YAML frontmatter：

```yaml
---
title: 打印服务超时机制
type: ops
tags: [print, timeout, fallback]
owner: "@hanqiang"
created: 2026-05-12
expires: 2026-08-12        # 默认：创建后 90 天。填 "never" 表示永久有效。
status: draft              # draft | active | deprecated | canonical
sources:
  - "手工录入 @hanqiang 2026-05-12"
related:
  - "[[print-service-overview]]"
---
```

**status 生命周期：**

```
draft ──(health audit)──▶ active ──(health deprecate)──▶ deprecated
                               ╲
                                ──(手动晋升)──▶ canonical
```

| status | 含义 | AI 行为 |
|--------|------|---------|
| `draft` | 草稿，待确认 | 可参考，不作决策依据 |
| `active` | 正式有效 | 正常检索引用 |
| `deprecated` | 已废弃 | 禁止引用 |
| `canonical` | 权威锁定 | 最高优先级；AI 禁止修改 |

---

## Git Hooks

`/knowledge-wiki init` 自动安装两个 hook：

### `pre-push` — 阻断式

每次 `git push` 前运行，检查：

- 知识文档是否在 **7 天内**到期或已过期
- `.sources.yaml` 中的外部源是否超过 **30 天**未同步

发现问题时提示：

```
[1] 现在处理   [2] 跳过   [3] 中止 push
```

> [!IMPORTANT]
> Hook **无问题时完全静默** — 不会拖慢正常 push 流程。

### `commit-msg` — 非阻断提示

commit message 含 `[kb]` 标记时触发：

```bash
git commit -m "fix: 修复打印超时未重置问题 [kb]"
# → 提示：知识库中有 ops/print-timeout.md，建议更新
```

不阻断 commit，仅输出建议。

---

## 外部源管理

在 `.knowledge/.sources.yaml` 注册需要持续追踪的外部文档：

```yaml
sources:
  - id: print-api-doc
    name: 打印接口文档
    url: https://docs.apipost.net/docs/detail/xxx
    tracked_by: "@hanqiang"
    last_hash: ""
    last_synced: ""
    status: active          # active | stale | error
    related_docs:
      - apis/print-api.md
```

`/knowledge-wiki health scan` 拉取每个注册 URL，计算内容 hash，发现变更后提示处理 — **不自动覆盖**本地文档。

---

## 工具依赖

`/knowledge-wiki init` 在创建任何文件前自动检查依赖。

### Group A — 必需工具

| 工具 | 必需性 | 用途 |
|------|:------:|------|
| `rg`（ripgrep） | ✅ | 全文检索与反向追溯 |
| `git` | ✅ | Hook 安装 |
| `jq` | 可选 | Hook 脚本解析 frontmatter |

### Group B — 浏览器自动化（处理 URL 录入）

> [!NOTE]
> 全部可选。该组中任一工具已安装即可处理 URL 录入。

| 工具 | 适用场景 |
|------|---------|
| `agent-browser` | 通用 AI 原生首选（轻量、50+ 命令） |
| `browser-harness` | 选择器易变 / 动态渲染页面 |
| `playwright` | 流程固定的批量录入 / 扫描 |
| `browser-use` | 多步骤 LLM 自主决策 |
| `page-agent` | 中文网页站点 |

```bash
bash references/scripts/check-deps.sh                    # 仅检查
bash references/scripts/check-deps.sh --install          # 安装缺失的 Group A 工具
bash references/scripts/check-deps.sh --install-browser  # 安装全部 Group B 工具
```

自动选择当前系统的包管理器：`brew` · `apt` · `yum` · `npm` · `pipx`。

---

## 设计原则

1. **无来源不写、不答** — `sources` 必填；`ask` 无记录时明确告知，不猜测。
2. **术语唯一定义** — 定义锚点在 `glossary/`；所有文档通过 `[[slug]]` 引用，不重复定义。
3. **草稿优先** — 新条目默认 `status: draft`；由 `health audit` 人工晋升。
4. **rg 零索引追溯** — 正反向追溯直接扫描 Markdown，无需维护 JSON 索引文件。
5. **静默放行** — Hook 和 `health rot` 无问题时完全不输出，不干扰正常工作流。
6. **deprecate 必处理引用** — 废弃前用 `rg` 找出所有引用处，防止悬空链接。
7. **工具检查门** — `init` 缺必需工具时中止，不留部分初始化状态。
8. **模板即合约** *(v0.6.0)* — 录入正文严格按 `templates/{type}.md` 骨架生成；AI 不允许自行增删一级标题；Step 8.5 门禁强制校验必填段。

---

## 使用示例

<details>
<summary>录入示例</summary>

```bash
# 从飞书文档录入
/knowledge-wiki in https://xxx.feishu.cn/docx/xxx

# 从飞书知识库录入
/knowledge-wiki in https://xxx.feishu.cn/wiki/xxx

# 手工录入一条知识
/knowledge-wiki in "打印服务超时是 30s，超时后 fallback 到本地缓存"

# 从代码文件提炼设计知识
/knowledge-wiki in ./src/print/service.go

# 注册外部知识源（持续追踪变更）
/knowledge-wiki in source add https://docs.apipost.net/docs/detail/xxx --name "打印接口文档"
```

</details>

<details>
<summary>查询与追溯示例</summary>

```bash
# 提问 — 回答总会引用来源文档
/knowledge-wiki ask "打印服务的超时配置是多少？"

# 谁引用了这篇文档？
/knowledge-wiki ask links print-timeout

# 这篇文档引用了哪些？
/knowledge-wiki ask refs print-timeout
```

</details>

<details>
<summary>维护示例</summary>

```bash
# 检查外部源是否有更新
/knowledge-wiki health scan

# 查看过期或即将过期的文档
/knowledge-wiki health rot

# 确认文档仍有效（重置过期时间 +90 天）
/knowledge-wiki health audit print-timeout

# 废弃过期文档（先处理所有引用）
/knowledge-wiki health deprecate old-print-config
```

</details>

---

## 资源索引

| 文件 | 用途 |
|------|------|
| [`SKILL.md`](./SKILL.md) | Skill 主入口 — 工具表、子命令骨架、AI 调用规则 |
| [`DESIGN.md`](./DESIGN.md) | 架构取舍、分层模型、模板库设计原理 |
| [`references/directory-structure.md`](references/directory-structure.md) | `.knowledge/` 目录树 + 根文件模板 |
| [`references/ingestion-rules.md`](references/ingestion-rules.md) | 11 步录入流程、slug 规则、质量门禁 |
| [`references/ask-rules.md`](references/ask-rules.md) | 两层检索、回答格式、时效计算、links/refs |
| [`references/health-rules.md`](references/health-rules.md) | rot · scan · coverage · audit · deprecate 规范 |
| [`references/url-handling.md`](references/url-handling.md) | URL 路由规则、飞书子流程、scan 路由 |
| [`references/templates/_registry.yaml`](references/templates/_registry.yaml) | 中央类型注册表 → 模板 + 必填段 + 门禁 |
| [`references/scripts/check-deps.sh`](references/scripts/check-deps.sh) | 依赖检查 + 一键安装 |

---

## 更新日志

完整版本历史见 [`CHANGELOG.md`](./CHANGELOG.md)。

---

<div align="center">

为希望让知识保持活力、而不只是归档的团队而生。

</div>
