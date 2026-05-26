# knowledge-wiki

<div align="center">

**知识编译器** —— 将散落、腐烂、难以写入的知识，沉淀为结构化、可检索、严格溯源的本地知识库。

[![版本](https://img.shields.io/badge/版本-v1.1.0-blue.svg)](./CHANGELOG.md)
[![协议](https://img.shields.io/badge/协议-MIT-green.svg)](./LICENSE)
[![Lang](https://img.shields.io/badge/lang-English-blue.svg)](./README.md)

[English](./README.md) · [设计文档](./DESIGN.md) · [更新日志](./CHANGELOG.md) · [TODO](./TODO.md)

</div>

---

## 为什么需要 knowledge-wiki？

AI 辅助开发存在根本性的认知缺口：代码库被文档化为**扁平文本块**，检索系统只优化语义相似度，无法区分「决策意图」与「执行事实」。

AI 代理无法回答三个核心问题：

- **谁负责？**（决策路由）—— 这个需求应该由哪个服务处理？
- **怎么做？**（执行编排）—— 标准流程是什么？出错了怎么办？
- **用什么工具？**（原子调用）—— 接口长什么样？SLA 是多少？

> **核心结论**：瓶颈不是检索精度，而是**认知保真度** —— 能否分层表示知识、标注健康状态、验证跨层引用完整性，并显式建模「组织不知道自己不知道的事」。

---

## 目录

- [架构总览](#架构总览)
- [核心理念](#核心理念)
- [L1 / L2 / L3 三层认知架构](#l1--l2--l3-三层认知架构)
- [子命令速查](#子命令速查)
- [工具依赖](#工具依赖)
- [按域名路由浏览器自动化](#按域名路由浏览器自动化)
- [模板库](#模板库)
- [文档生命周期](#文档生命周期)
- [Frontmatter 格式](#frontmatter-格式)
- [Git Hooks](#git-hooks)
- [使用示例](#使用示例)
- [设计原则](#设计原则)
- [快速开始](#快速开始)
- [资源索引](#资源索引)

---

## 架构总览

```
                ┌──────────────────────┐
用户输入 ──────►│   in（14 步）         │
                └──┬───────────────────┘
                   ├── .knowledge/{dir}/{slug}.md     （写入）
                   ├── .index/{type}.idx.md           （Step 9.5 索引更新）
                   ├── .pending-backlinks.yaml        （Step 9.6 反向引用入队）
                   └── .logs/personal/{id}.md         （Step 10 日志）

                ┌──────────────────────┐
用户提问 ──────►│   ask（3 层）         │
                └──┬───────────────────┘
                   ├── Layer -1 : Index 预筛选
                   ├── Layer  0 : rg 关键词匹配
                   ├── Layer 0.5: frontmatter 兜底
                   ├── Layer  1 : 语义筛选 → 回答
                   └── .logs/personal/{id}.md         （日志）

                ┌─────────────────────────────────────┐
                │              health                  │
                ├─────────────────────────────────────┤
                │ rot / scan / coverage（增强）         │
                │ lint（L1–L9 一致性检查）              │
                │ backlink-consume（消费队列）           │
                │ index-rebuild（重建索引）              │
                │ distill（认知蒸馏）                   │  ← v1.1.0
                │ audit / deprecate                    │
                │ └→ .logs/personal/{id}.md + digest   │
                └─────────────────────────────────────┘
```

---

## 核心理念

> 从「知识存储」升级为「**知识编译**」—— 每次操作不仅存储知识，还让整个知识网络变得更密、更准、更有价值。

| 编译能力 | 说明 | 类比 |
|---|---|---|
| **分段索引** | 按 type 分 9 个 idx 文件，ask 时先读 index 预筛再 rg 精确搜索 | 从「每次从头搜索」→「先看目录再定位」 |
| **操作日志** | 按人分文件记录所有操作，hash 脱敏保护隐私，跨 session 可恢复上下文 | 从「无历史」→「知道最近做了什么」 |
| **双向引用** | 录入时反向入队，health 时批量回写 related，避免引用单向老化 | 从「只有新文档知道旧文档」→「旧文档也知道被引用了」 |
| **一致性检查** | 集中式 L1–L9 检测（矛盾/悬空引用/状态不一致），只在 health 时运行，不阻断主流程 | 从「有问题不知道」→「定期健康扫描自动发现」 |
| **Ask 回流** | 综合分析结果可录入为 `synthesis` 文档，避免高质量答案消失在聊天中 | 从「问答即弃」→「有价值发现可沉淀」 |
| **三层防护** `v0.9.0` | Index 准确性由 AI 实时写入 + health rebuild 最终一致 + pre-commit hook 拦截三层保证 | 从「写了就靠天」→「写→修→拦 全覆盖」 |
| **认知蒸馏** `v1.1.0` | Jaccard 相似度去重 + 低质量草稿清理 + 孤立知识检测，主动识别冗余 | 从「被动管理」→「主动进化」 |

---

## L1 / L2 / L3 三层认知架构

| 层级 | 别名 | 认知角色 | 核心问题 | 知识对象 |
|---|---|---|---|---|
| **L1 领域层** | 骨架 | 决策 | 谁负责？能做/不能做什么？ | 边界·意图·状态机·协作拓扑 |
| **L2 执行层** | 分子 | SOP 编排 | 怎么做？什么顺序？出错怎么办？ | 触发绑定·执行 DAG·分支条件·人工节点 |
| **L3 能力层** | 原子 | 工具调用 | 用什么工具？接口规格？SLA？ | 入参·出参结构·协议坐标·运行时约束 |

| 目录 | Type | 层级 |
|---|---|---|
| `glossary/` | glossary | L1 —— 核心实体定义，术语锚点 |
| `design/` | architecture / adr | L1 —— 系统架构、ADR |
| `requirements/` | requirement | L1 —— PRD、功能规格、验收标准 |
| `flows/` | flow | L2 —— 业务流程 SOP、业务规则 |
| `case/` | case | L2 —— 反向示例、故障复盘 |
| `design/` | solution | L2 —— 技术方案快照 |
| `synthesis/` | synthesis | L2 —— Ask 回流综合分析文档 |
| `apis/` | api | L3 —— 接口约定、字段映射 |
| `db/` | db | L3 —— 数据模型、存储设计 |
| `ops/` | ops | L3 —— 运维手册、告警阈值 |

> 完整目录树、type 映射、L1/L2/L3 定义统一维护在 [`references/directory-structure.md`](./references/directory-structure.md)（单一权威源）。设计哲学见 [`DESIGN.md`](./DESIGN.md)。

---

## 子命令速查

```bash
# 初始化（含工具依赖检查 + 安装 4 个 git hooks）
/knowledge-wiki init

# 录入
/knowledge-wiki in <文字/URL/文件路径>
/knowledge-wiki in --update <slug>
/knowledge-wiki in source add <url> [--name <名称>]
/knowledge-wiki in source list
/knowledge-wiki in source remove <id>
/knowledge-wiki in --from-answer "<简短描述>"   # Ask 回流

# 查询
/knowledge-wiki ask "<问题>"
/knowledge-wiki ask links <slug>        # 反向追溯：谁引用了这篇
/knowledge-wiki ask refs  <slug>        # 正向追溯：这篇引用了谁

# 维护
/knowledge-wiki health                  # 综合报告
/knowledge-wiki health --json           # JSON 格式输出          [v0.9.0]
/knowledge-wiki health --verbose        # 含 ASCII 图表的详细模式 [v0.9.0]
/knowledge-wiki health rot              # 扫描过期/即将过期文档
/knowledge-wiki health scan             # 检测外部知识源变更
/knowledge-wiki health coverage         # 覆盖率 + 问答缺口分析
/knowledge-wiki health audit <slug>     # 确认文档有效，升级为 active
/knowledge-wiki health deprecate <slug> # 标记文档废弃
/knowledge-wiki health lint             # 一致性检查 L1–L9
/knowledge-wiki health lint --fix       # 安全自动修复（L3+L8）
/knowledge-wiki health backlink-consume # 消费反向引用队列
/knowledge-wiki health index-rebuild    # 全量重建分段索引
/knowledge-wiki health distill          # 认知蒸馏预览            [v1.1.0]
/knowledge-wiki health distill --execute # 执行蒸馏（需用户逐步确认）
```

---

## 工具依赖

`/knowledge-wiki init` 在创建目录前先调用 `references/scripts/check-deps.sh`。

### Group A —— 核心工具（必须）

| 工具 | 必需性 | 用途 |
|---|---|---|
| `rg`（ripgrep） | **REQUIRED** | 关键词检索/追溯 |
| `git` | **REQUIRED** | hook 安装与触发 |
| `jq` | OPTIONAL | hook 脚本解析 frontmatter |

### Group B —— 浏览器自动化（任选其一）

| 工具 | 定位 | 适用场景 |
|---|---|---|
| `agent-browser` | AI 工具调用的极速瑞士军刀 | AI 调用首选；通用首选 |
| `browser-harness` | AI 编程助手的自愈浏览器手 | 选择器易变 / 动态渲染页面 |
| `playwright` | 工程化测试的坚实基石 | 流程固定的批量录入/扫描 |
| `browser-use` | LLM 自主操作的完整大脑 | 多步骤 LLM 自主决策 |
| `page-agent` | 中文网页理解的领域专家 | 中文/阿里系站点 |

> Group B 全部 OPTIONAL；任一已装即可处理内部文档 URL。

### 一键安装

```bash
bash references/scripts/check-deps.sh                   # 仅检查
bash references/scripts/check-deps.sh --install         # 安装缺失的必需工具（Group A）
bash references/scripts/check-deps.sh --install-browser # 安装缺失的浏览器工具（Group B）
```

脚本自动按当前 OS（macOS → brew / Linux → apt|yum / npm / pipx）选择安装命令。

---

## 按域名路由浏览器自动化

涉及内部文档 URL（飞书、Apipost 等）时，按域名路由到浏览器自动化工具。未装时强制提示安装。

```
URL 域名                              工具
──────────────────────────────────────────────────────────
feishu.cn / larkoffice.com      →   agent-browser / browser-harness / …
apipost.net                     →   agent-browser（遍历目录树）
其他公网 URL                     →   任一 Group B 工具
```

完整工具选型矩阵见 [`references/url-handling.md`](./references/url-handling.md)。

---

## 模板库

为 **9 个 type** 各提供专属正文骨架（v0.8.0 新增 `synthesis`）：

```
references/templates/
├── _registry.yaml      ← 中央注册表（type → 模板 + 必填段 + 质量门禁）
├── glossary.md         ← L1  术语定义
├── architecture.md     ← L1  架构现状
├── adr.md              ← L1  架构决策记录
├── requirement.md      ← L1  需求文档 / PRD
├── flow.md             ← L2  业务流程 SOP
├── solution.md         ← L2  技术方案
├── case.md             ← L2  反向示例 / 故障复盘
├── synthesis.md        ← L2  综合分析（Ask 回流）  [v0.8.0]
├── api.md              ← L3  接口约定
├── db.md               ← L3  数据模型
└── ops.md              ← L3  运维手册
```

**关键流程节点**（共 15 步）：

| 步骤 | 名称 | 说明 |
|---|---|---|
| 2.5 | 模板加载 | 读 `_registry.yaml` 定位到 `templates/{type}.md`，按骨架整理正文 |
| 2.65 | 相似检测 `v1.1.0` | Jaccard 快速匹配（>0.70 提示走 `--update`）。不阻断 |
| 8.5 | 质量门禁 | 写入前逐项检查 `required_sections` 并运行 `quality_gate` 文本校验 |
| 9.5 | 索引更新 | 写入成功后立即更新 `.index/` 对应 idx 文件（失败仅 WARNING） |
| 9.6 | 反向引用入队 | `related ≥ 1` 且目标非 deprecated 且队列 < 15 时，写入 `.pending-backlinks.yaml` |
| 10 | 操作日志 | 所有操作留痕到 `.logs/personal/{mis-id}.md` |

---

## 文档生命周期

| status | 含义 | AI 行为 |
|---|---|---|
| `draft` | 草稿，待确认 | 可参考，不作决策依据 |
| `active` | 正式有效 | 正常检索引用 |
| `deprecated` | 已废弃 | **禁止**引用 |
| `canonical` | 权威锁定 | 最高优先级，AI 禁止修改 |

检索优先级：`canonical > active > draft`（deprecated 被排除）

---

## Frontmatter 格式

```yaml
---
title: 打印服务超时机制
type: ops
tags: [print, timeout, fallback]
owner: "@hanqiang"
created: 2026-05-12
expires: 2026-08-12        # 默认 90 天；填 never 表示长期有效
status: draft              # draft | active | deprecated | canonical
sources:
  - "手工录入 @hanqiang 2026-05-12"
related:
  - "[[print-service-overview]]"
---
```

---

## Git Hooks

`/knowledge-wiki init` 安装 **4 个** git hooks：

| Hook | 触发时机 | 行为 |
|---|---|---|
| `pre-commit` `v0.9.0` | staged `.knowledge/` 文件 | 检查 L2 悬空引用 + L5 孤儿索引。ERROR 阻断；WARNING 不阻断 |
| `post-merge` `v0.9.0` | merge 后 | 变更 >3 篇或 rebuild >30 天 → 提示 `health index-rebuild`。不自动执行 |
| `pre-push` | push 前 | 检测即将过期（≤7 天）或已过期文档 + 外部源未同步（>30 天）。提示 `[1] 现在处理  [2] 跳过  [3] 中止` |
| `commit-msg` | 含 `[kb]` 标记的 commit | 检查知识库是否有相关文档，建议更新或新建。不阻断 |

---

## 使用示例

```bash
# 从飞书文档录入（走浏览器自动化工具）
/knowledge-wiki in https://xxx.feishu.cn/docx/xxx

# 手工录入一条知识
/knowledge-wiki in "打印服务超时阈值是 30s，超了会 fallback 到本地缓存"

# 从代码文件提炼设计知识
/knowledge-wiki in ./src/print/service.go

# 查询知识库
/knowledge-wiki ask "打印服务的超时配置是多少？"

# 反向追溯：谁引用了 print-timeout 这篇文档
/knowledge-wiki ask links print-timeout

# 注册外部知识源（持续追踪变更）
/knowledge-wiki in source add https://docs.apipost.net/docs/detail/xxx --name 打印接口文档

# 检查外部源是否有更新
/knowledge-wiki health scan

# 查看过期文档
/knowledge-wiki health rot

# 人工确认某篇文档仍有效（重置过期时间 +90 天）
/knowledge-wiki health audit print-timeout
```

---

## 设计原则

1. **无来源不写、不答** —— `sources` 必填；ask 无知识库记录时明确告知，不猜测
2. **术语唯一** —— 术语定义锚点在 `glossary/`，其他文档用 `[[slug]]` 引用，不重复定义
3. **草稿优先** —— 新录入一律 `status: draft`，由 `health audit` 人工升级
4. **静默放行** —— hook 和 rot 扫描无问题时完全不输出，不干扰正常工作流
5. **deprecate 必处理引用** —— 废弃前用 `rg` 找出所有引用处，防止悬空链接
6. **索引辅助检索** `v0.8.0` —— `.index/` 分段索引作为 Layer -1 预筛选层
7. **操作留痕** `v0.8.0` —— 所有操作均写入日志；ask 内容 hash 脱敏保护隐私
8. **延迟回写** `v0.8.0` —— 反向引用写入队列，由 health 批量安全消费
9. **集中式 lint** `v0.8.0` —— 矛盾检测只在 `health lint` 时执行，不阻断 in/ask 流程
10. **按域名路由浏览器自动化** —— 内部文档 URL 按域名路由到浏览器工具，未装时强制提示
11. **工具检查门** —— `init` Step 0 必跑 `check-deps.sh`，缺必需工具中止 init
12. **模板为合约** —— 录入正文严格按 `references/templates/{type}.md` 骨架生成
13. **二次回流禁止** `v0.8.0` —— `synthesis` 文档不能再通过 ask 回流生成新 synthesis（防止套娃）
14. **三层数据防护** `v0.9.0` —— AI 实时写入 + health rebuild + pre-commit hook 拦截三层保证
15. **认知蒸馏** `v1.1.0` —— `health distill` 扫描重复/低质量/孤立知识，默认预览不修改
16. **录入前防重** `v1.1.0` —— Step 2.65 Jaccard 快速匹配（>0.70 提示），降低知识重复率

---

## 快速开始

```bash
# 1. 进入项目根目录
cd ~/your-project

# 2. 初始化（自动检查工具依赖）
/knowledge-wiki init
# 缺必需工具时三选一：[1] 一键安装  [2] 手动安装后重试  [3] 中止
# 通过后创建 .knowledge/ 目录 + 安装 git hooks

# 3. 录入第一条知识
/knowledge-wiki in "打印服务超时阈值 30s"

# 4. 查询验证
/knowledge-wiki ask "打印服务超时"

# 5. 定期维护
/knowledge-wiki health
```

---

## 资源索引

| 路径 | 用途 |
|---|---|
| `SKILL.md` | skill 主入口 —— 工具表 + 子命令骨架 |
| `DESIGN.md` | L1/L2/L3 分层架构 + 模板库机制设计 |
| `TODO.md` | 待实现能力清单 + 版本规划 |
| `references/directory-structure.md` | `.knowledge/` 完整目录框架 + 根文件模板 |
| `references/url-handling.md` | URL 处理铁律 + 域名路由子流程 + scan 路由 |
| `references/ingestion-rules.md` | AI 结构化录入流程（14 步） |
| `references/index-rules.md` | 分段索引规则（三层数据准确性保证） |
| `references/log-rules.md` | 操作日志规则（按人分文件 / 归档 / digest） |
| `references/backlink-rules.md` | 双向 related 回写规则（pending 队列 / 延迟消费） |
| `references/lint-rules.md` | 一致性检查规则（L1–L9 / --fix 安全边界） |
| `references/templates/_registry.yaml` | 模板注册表（9 个 type）+ 必填段 + 质量门禁 |
| `references/templates/{type}.md` | 9 个 type 专属正文骨架模板 |
| `references/templates/_meta.yaml.tpl` | 索引元数据初始化模板 `v0.8.1` |
| `references/templates/_logs_config.yaml.tpl` | 日志配置初始化模板 `v0.8.1` |
| `references/templates/_pending_backlinks.yaml.tpl` | 空队列初始化模板 `v0.8.1` |
| `references/templates/_idx_empty.md.tpl` | 通用 idx 表头模板 `v0.8.1` |
| `references/ask-rules.md` | 三层检索 + log 记录 + ask 回流提示 |
| `references/health-rules.md` | 综合报告 + 所有 health 子命令 |
| `references/scripts/check-deps.sh` | 工具依赖检查 + 一键安装 |
| `references/scripts/pre-commit.sh` | git pre-commit hook `v0.9.0` |
| `references/scripts/post-merge.sh` | git post-merge hook `v0.9.0` |
| `references/scripts/pre-push.sh` | git pre-push hook |
| `references/scripts/commit-msg.sh` | git commit-msg hook |

完整版本变更记录见 [`CHANGELOG.md`](./CHANGELOG.md)

---

## 协议

[MIT](./LICENSE)
