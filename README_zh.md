<div align="center">

# 🧠 knowledge-wiki

### 给 AI 编程 Agent 用的治理型知识图谱 skill

团队知识，**编译**——不只是存储。12 个类型化模板 · 14 步录入管线 · 4 层检索 · 3 级边可信度模型。每个回答都带来源，没有记录就老实说"没有"。

[![version](https://img.shields.io/badge/version-v2.1.0-blue?style=flat-square)](CHANGELOG.md)
[![license](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![agents](https://img.shields.io/badge/agents-Claude%20Code%20%C2%B7%20Codex%20%C2%B7%20Cursor-purple?style=flat-square)](#-快速开始)
[![install](https://img.shields.io/badge/install-npx%20skills%20add-black?style=flat-square)](#-快速开始)
[![stars](https://img.shields.io/github/stars/anthonyhann/knowledge-wiki?style=flat-square)](https://github.com/anthonyhann/knowledge-wiki/stargazers)

[快速开始](#-快速开始) · [核心能力](#-核心能力) · [触发词](#-触发词) · [目录结构](#-目录结构) · [什么时候别用](#-什么时候别用它) · [CHANGELOG](CHANGELOG.md) · [English](README.md)

</div>

## 你的 AI 是不是也这样？

- 凭**模型记忆**回答，而不是凭你们团队真实的决策——自信地错
- 昨天刚复盘完的故障，今天生成代码时又踩了同一个坑
- 能*找到文档*，但答不上 **「改了 X 会炸掉什么」**
- 与此同时 wiki 在悄悄腐烂——没人知道哪篇文档已经过期

本 skill 用一条机制根治：**文档是唯一真理源（SSOT），知识图谱是文档的纯函数派生物**（`graph = compile(documents)`）。删掉 `.knowledge/.graph/` 即零破坏回退到纯文档库——图能力是叠加，不是替换。

## 一个回答长什么样

```
$ /knowledge-wiki ask "打印服务的超时配置是多少？"

回答：打印服务超时阈值为 30s，超时后 fallback 到本地缓存，不直接报错。
来源：.knowledge/ops/print-timeout.md（第 12 行）
录入：@alice，2026-05-12
状态：FRESH（距过期还有 82 天）
被引用：[[order-flow-design]]（1 处）
```

没有记录？它会直说——并且拒绝用训练数据脑补填坑（核心不变量 C1）。

## 🚀 快速开始

**给人用**——3 步：

```bash
# 1. 安装 skill
npx skills add anthonyhann/knowledge-wiki

# 2. 在你的 AI 编程 Agent（Claude Code / Codex / Cursor …）里运行：
/knowledge-wiki init

# 3. 录入第一条知识
/knowledge-wiki in 打印服务超时阈值 30s，超了会 fallback 到本地缓存
```

`init` 会先检查工具依赖（`rg`/`git`），创建 `.knowledge/` 骨架（10 个业务目录 + 索引/日志/队列系统目录），并安装 5 个 git hooks。

**给 AI Agent 用**——把这句话粘贴给你的 Agent：

> 帮我安装 knowledge-wiki 这个 skill：https://github.com/anthonyhann/knowledge-wiki（可以 git clone 到我的 skills 目录，或用 `npx skills add anthonyhann/knowledge-wiki`），然后阅读它的 SKILL.md，并在我的项目里运行 `/knowledge-wiki init`。

## ✨ 核心能力

| 场景 | 你说 | 它做 |
|---|---|---|
| 零门槛录入 | `in <文字 / URL / 文件 / 代码>` | 14 步管线：type 推断 → 类型专属模板 → 质量门禁 → 分段索引 → 反向引用入队 → 操作日志 |
| 带来源的问答 | `ask "<问题>"` | 4 层检索（索引预筛 → ripgrep → 模糊兜底 → 语义筛选）；5 元素回答：结论/来源/录入人/时效/引用链 |
| **找关系** | `ask graph "X"` · `ask explain "X"` · `ask path "A" "B"` | 关系子图、节点全连接解释、多跳桥接知识链——默认只走权威边，推断边强制标注 ⚠️ |
| 测试知识包 | `ask test "<模块>"` | 按模块聚合测试环境/规范/检查清单/坑点/测试数据五分组，供 QA Agent 单点消费 |
| 代码 → 文档 | `docs --staged` | 分析本次 diff，**逐条问询**确认是否沉淀，绝不阻断 commit |
| 保鲜与治理 | `health` / `rot` / `scan` / `lint` / `distill` | 过期扫描、外部源变更追踪、14 项一致性检查、去重与孤立知识检测 |
| 看见整张知识网 | `health graph-build` → `graph export --html` | 从文档编译出 `graph.json`；导出交互式 HTML / Obsidian Canvas / GraphML |
| 可信度治理 | `health discover` → `health edge-review` | AI 推断的边**必须人审**；批准的边先回写文档 frontmatter 再重新派生入图。无批量自动批准后门 |

## 🗣️ 触发词

说出这些话时本 skill 会被触发：

| 当你说… | 触发 |
|---|---|
| "把这个记到知识库" / "知识沉淀" | `in` |
| "知识库里有没有…" / "查一下" | `ask` |
| "X 和 Y 怎么连" / "改 X 影响什么" / "A 到 B 的知识链" | `ask graph` / `ask path` |
| "知识库健康" / "检查过期文档" | `health` |
| "把这次提交文档化" | `docs` |

## 📊 凭什么信它

全部数字都可以在本仓库里数出来：

- **12 个类型化模板**，每种 type 有专属必填段 + 质量门禁——拒绝"TL;DR + 详情"一床被子盖所有场景
- **14 篇规则文档**（[`references/`](references/)），覆盖录入、检索、索引、引用、日志、lint、图谱、可信度
- **12 个脚本**：6 个 PEP 723 图谱引擎（仅依赖 `networkx`，uv 隔离运行）+ 5 个 git hooks + 1 个依赖检查器
- **14 项一致性检查**（L1–L9 + 5 项图谱/队列 lint）集中运行，绝不阻断主流程
- **8 条核心不变量（C1–C8）** + **9 条可降级扩展行为（E1–E9）**——例如 C1：无来源不写、不答
- **3 级边可信度模型**（EXTRACTED / INFERRED / AMBIGUOUS）+ 人审闸门；AMBIGUOUS 边机制级永远不能成为硬结论
- 按 **9 个带门禁的 phase** 串行交付（v0.1.0 → v2.1.0），每个 phase 有验收矩阵——见 [CHANGELOG.md](CHANGELOG.md)

## 📂 目录结构

```
knowledge-wiki/
├── SKILL.md                  # 入口：子命令骨架 + C1–C8 核心不变量 + E1–E9 扩展行为
├── DESIGN.md                 # L1/L2/L3 三层认知架构 + 模板库机制设计
├── CHANGELOG.md              # 完整版本史（v0.1.0 → v2.1.0）
├── TODO.md                   # 路线图与设计决策备忘录
├── test-prompts.json         # dry-run 评测 prompt（7 条：happy + edge）
└── references/               # 懒加载权威细则（用到才读，绝不预加载）
    ├── *.md                  # 14 篇规则：录入 / 查询 / 索引 / 反向引用 / 日志 / lint /
    │                         #   健康 / 文档化 / URL / 图模型 / 图编译 / 可信度 / 待审边队列
    ├── templates/            # 12 个类型模板 + 注册表 + 5 个系统配置模板
    └── scripts/              # 6 个图谱引擎（Python，PEP 723）+ 5 个 git hooks + check-deps.sh
```

`init` 会在*你的*项目里创建 `.knowledge/`：10 个业务目录（`glossary/ design/ requirements/ flows/ case/ tests/ apis/ db/ ops/ synthesis/`），按 L1 领域层 / L2 执行层 / L3 能力层组织——设计哲学见 [DESIGN.md](DESIGN.md)。

## ⚠️ 什么时候别用它

诚实边界——本 skill **不适合**：

- **私域笔记 / 日记 / 实时聊天记录 / 临时草稿**——它是为"与代码库绑定的团队知识"设计的
- **想要托管式多人实时协作 wiki 的团队**——它是本地 Markdown + git 方案：没有 server、没有 web UI、没有多人同时编辑
- **不愿维护 `sources` / `status` 纪律的团队**——C1 意味着没有记录时 Agent *拒绝回答*；这是特性，但确实需要习惯转变
- **需要向量检索的超大语料（万级文档以上）**——检索是 ripgrep + 分段索引，刻意不引入 embedding，换取完全可审查

## 🙋 关于作者

由 [@anthonyhann](https://github.com/anthonyhann) 在真实工程项目中日用打磨——CHANGELOG 里每个功能都对应一个真实工作流踩过的坑。如果它帮你的团队省下了一次"当时为什么这么搞"的考古，⭐ 一下，让下一个团队知道它真的能用。

## License

MIT © [anthonyhann](https://github.com/anthonyhann) — 见 [LICENSE](LICENSE)。
