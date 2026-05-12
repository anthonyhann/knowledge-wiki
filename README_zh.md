<h1 align="center">📚 knowledge-wiki</h1>

<p align="center">
  <strong>将散落文档转化为结构化、可检索、Agent 可推理的知识库</strong>
</p>

<p align="center">
  <a href="./README.md">English</a> ·
  <a href="./CHANGELOG.md">更新日志</a> ·
  <a href="./SKILL.md">Skill 规范</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/触发-%2Fknowledge--wiki-blue" alt="trigger" />
  <img src="https://img.shields.io/badge/格式-11%2B-green" alt="formats" />
  <img src="https://img.shields.io/badge/平台-学城%20%7C%20飞书%20%7C%20Apipost-orange" alt="platforms" />
  <img src="https://img.shields.io/badge/检索-BM25%20%2B%20Dense%20%2B%20GraphRAG-purple" alt="retrieval" />
</p>

---

## 解决什么问题？

团队的知识散落在学城文档、飞书、Apipost 接口文档、代码注释、会议记录里。每次有人问"这个接口怎么用"、"上次为什么这么设计"，要么翻文档半天，要么问同事，要么靠记忆。新人入职没有自学入口，老人离职知识随之流失。

**knowledge-wiki 把这些散落的知识统一沉淀到一个结构化知识库**，让 AI Agent 能直接检索、推理和回答。

| 痛点 | 解决方式 |
|------|----------|
| 🔍 **查不到** — 文档在各个平台，检索要切换好几个工具 | 统一知识库 + 四路混合检索（BM25 + Dense + GraphRAG + 父子分块） |
| 🕰️ **过时了** — 学城文档更新了，本地没同步，AI 基于旧信息回答 | 持久化同步源 + push 前自动感知变更 |
| 🧠 **沉淀不住** — 每次代码变更，相关文档没有人更新，知识腐化 | Pre-push Hook 自动检测陈旧文档并提示更新 |

---

## ✨ 核心能力

| 能力 | 解决什么问题 | 命令 |
|------|------------|------|
| **RAG 快速问答** | "这个接口参数是什么？" 类即时查询 | `/knowledge-wiki ask` |
| **Agent 智能推理** | "结合历史 ADR 分析这个方案的风险" 类复杂推理 | `/knowledge-wiki reason` |
| **Wiki 自动生成** | 从学城/飞书/代码自动生成结构化知识页面 | `/knowledge-wiki wiki` |
| **持久化同步源** | 学城文档更新后自动感知，push 前提示同步 | `/knowledge-wiki source` |

---

## 🚀 快速开始

### 1. 初始化知识库

```bash
/knowledge-wiki init
# ✓ 创建 .knowledge/ 目录结构（含 docs/ 七个子目录）
# ✓ 生成治理文件（CLAUDE.md / AGENTS.md / CONTRIBUTING.md）
# ✓ 安装 5 个脚本（kb-sync.sh / generate-dashboard.py 等，均 chmod +x）
# ✓ 安装 .git/hooks/pre-push（push 前自动检查 + 生成文档）
# ✓ 立即生成初始 docs/generated/ 和 dashboard.md
# ✓ 输出初始健康报告
```

### 2. 导入已有文档

```bash
# 从学城导入（需美团内网登录）
/knowledge-wiki ingest https://km.sankuai.com/collabpage/2760577321

# 从飞书导入（需飞书登录）
/knowledge-wiki ingest https://bytedance.larkoffice.com/docx/PW6PdvVPFoNwgjxgRPWcwBrknmc

# 从 Apipost 递归抓取整个文档树（公开，无需登录）
/knowledge-wiki ingest "https://docs.apipost.net/docs/detail/5347b5d25884000" --recursive

# 从代码目录提取模块文档
/knowledge-wiki ingest ./src/ --type code

# 导入本地 PDF 技术方案
/knowledge-wiki ingest ./docs/technical-spec.pdf
```

### 3. 注册持久化同步源

```bash
/knowledge-wiki source add https://km.sankuai.com/collabpage/2760577321 \
  --name "AI-DLC框架" --tags "ai,framework"

/knowledge-wiki source list
# ID       名称                  状态    上次同步
# src-001  AI-DLC框架            active  2026-05-07
```

### 4. 开始使用

```bash
# 日常问答
/knowledge-wiki ask "API 网关的限流策略有哪些？"

# 复杂推理（自动调用知识库 + MCP 工具 + 网络搜索）
/knowledge-wiki reason "结合历史 ADR 和当前架构，分析限流误伤的根因并给出优化方案"

# 查看知识图谱（浏览器双击打开）
/knowledge-wiki graph
```

---

## 📖 使用场景示例

### 新人入职快速上手

```bash
/knowledge-wiki ask "麦芽田开放平台的渠道侧和配送侧接口有什么区别？"

# 输出：
# 渠道侧接口（/channel/）负责商家侧消息接收，主要参数包括 Tag 字段做路由...
# 配送侧接口（/delivery/）负责配送状态推送，使用 Command 字段路由，鉴权方式不同...
# 参考来源：[[api-gateway]] [[myt-adapter-architecture]]（相关度 ⭐⭐⭐⭐）
# 置信度：high
#
# 💡 相关推荐：
# 1. 渠道接入的完整流程是什么？
# 2. send 和 receive 服务的日志格式有什么区别？
```

### 代码 Push 前自动提醒更新文档

```bash
$ git push origin feature/rate-limiter

━━━ 知识库同步分析 (.knowledge/) ━━━
📦 本次变更文件：
  internal/gateway/rate_limiter.go
  internal/gateway/config.go

📝 建议更新以下知识库文档：
  pages/entities/api-gateway.md  [已存在，需更新]

检测到知识库有待处理事项，如何继续？
  [1] 先同步知识源  [2] 先更新文档页面  [3] 两者都做  [4] 跳过直接推送
```

### 复杂多步推理

```bash
/knowledge-wiki reason \
  "doudian 渠道在大促期间经常出现 5xx，结合现有架构和历史 ADR，给出排查思路"

# Agent 自动执行：
# Thought: 需要了解当前架构和历史决策
# Action: kb_search("doudian 5xx 限流")
# Observation: 找到 pages/entities/doudian-adapter.md、docs/implementation/rate-limiter-v2-adr.md
# Thought: 查看具体接口实现
# Action: kb_read("doudian-adapter")
# ...
# Final Answer: 排查思路：1. 确认是 send 还是 receive 侧 → 2. 检查 Tag 路由配置...
```

### 学城文档更新后自动感知

```bash
# push 时 hook 自动检测陈旧源：
⏰ 发现未同步的知识源：
  ⏰ [src-001] AI-DLC框架 (stale, 上次同步: 2026-04-30)
  建议运行：/knowledge-wiki source sync

# 手动触发增量同步：
/knowledge-wiki source sync src-001

# 同步报告：
src-001  AI-DLC框架  ↑ 已更新（章节"三、各层说明"有变更）→ 重新导入了 1 页
  ✓ pages/entities/ai-dlc-framework.md 已更新
```

---

## 🗂 目录结构

```
.knowledge/
├── CLAUDE.md              # AI 协作契约（Agent 每次必读）
├── AGENTS.md              # AI 专用导航地图（≤100 行）
├── dashboard.md           # 【CI 生成】知识库看板
├── graph.html             # 【CI 生成】知识图谱可视化
├── strategy/              # 团队黄金原则（低频，负责人维护）
├── docs/                  # 项目文档（按生命周期分区）
│   ├── requirements/      # 需求文档、PRD、UI 设计图
│   ├── design/            # 技术方案、流程图、PUML
│   ├── implementation/    # ADR、接口约定
│   ├── quality/           # 测试方案、验收文档
│   ├── release/           # 上线文档、回滚方案
│   ├── exec-plans/        # 执行计划（active/completed）
│   ├── domain/            # 业务领域知识
│   └── generated/         # 【CI 生成】db-schema、api-changelog
├── people/{user-id}/      # 个人上下文（AI 只读）
├── playbooks/             # 锁定版任务契约（canonical，AI 禁止修改）
├── pages/                 # Wiki 主页面（AI 自动生成）
└── inbox/                 # 待处理草稿
```

---

## 📋 全部命令

```
/knowledge-wiki init [path]               # 初始化知识库（三阶段：创建→安装脚本→立即执行）
/knowledge-wiki ingest <source>           # 导入文档（11+ 格式 + 学城/飞书/Apipost）
/knowledge-wiki ask "<问题>"              # RAG 快速问答（BM25+Dense+GraphRAG+父子分块）
/knowledge-wiki reason "<复杂问题>"       # ReACT 智能推理（自主编排工具和搜索）
/knowledge-wiki wiki [--enable|--disable] # Wiki 模式开关 & 自动生成/更新页面
/knowledge-wiki graph [path]              # 生成本地知识图谱 HTML（零依赖，双击即开）
/knowledge-wiki search <query>            # 混合检索（不生成回答，看原始召回结果）
/knowledge-wiki lint [path]               # 检查断链、孤立页面、frontmatter 缺失
/knowledge-wiki eval [path]               # 端到端评测（召回率、BLEU-4、ROUGE-L、幻觉率）
/knowledge-wiki export <format>           # 导出为 jsonl / qa-pairs / graphrag
/knowledge-wiki status                    # 知识库健康状态一屏总览
/knowledge-wiki sync [base_ref]           # push 前变更分析（pre-push 自动调用）
/knowledge-wiki source add <url> [opts]   # 注册持久化同步源
/knowledge-wiki source list               # 查看所有源（含状态和上次同步时间）
/knowledge-wiki source sync [id]          # 增量同步（hash 对比，无变化自动跳过）
/knowledge-wiki source remove <id>        # 移除源（不删除已生成页面）
```

---

## 📄 支持的文档格式

**本地文件：** Markdown · PDF · Word (.docx) · TXT · 图片（OCR）· CSV/Excel · PPT (.pptx) · JSON · 代码目录 · 对话记录

**在线平台：**

| 平台 | 访问前提 | 特点 |
|------|---------|------|
| 学城 `km.sankuai.com` | 美团内网登录 | heading/table/code 完整提取 |
| 飞书 `larkoffice.com` | 飞书已登录 | 目录树 + 正文分层提取 |
| Apipost `docs.apipost.net` | 公开，无需登录 | 接口参数自动转 entity 页面 |
| 普通网页 `https://...` | 公开页面 | 提取正文，去导航噪声 |

---

## 🔬 检索架构

`/knowledge-wiki ask` 采用四层混合检索：

| 层级 | 方式 | 作用 |
|------|------|------|
| 1. BM25 | ripgrep 全文扫描 pages/ | 精确关键词匹配 |
| 2. Dense | .kb-meta/chunks.jsonl top-K | 语义向量相似度 |
| 3. GraphRAG | graph.json 1-hop 邻居 | 补充关联上下文 |
| 4. 父子分块 | 子块命中→补充父块 | 防语义截断 |

**融合排序规则：** backlink_count 高优先 → canonical 最高优先级 → deprecated 自动降权

---

## 🧪 端到端评测

```bash
/knowledge-wiki eval

# 输出示例：
# 检索层  召回命中率: 0.87  精确率: 0.79
# 生成层  BLEU-4: 0.43  ROUGE-L: 0.61  幻觉率: 4.8%
# 全链路  P50: 1.2s  P95: 2.8s
```

---

## 🏗 方法论来源

knowledge-wiki 融合以下领域最佳实践：

- **AI-DLC 框架**（内部）— 目录分层、AGENTS.md 规范、CI 门禁、generated/ 隔离
- **Zettelkasten** — 原子化笔记 + 显式链接网络
- **GraphRAG（Microsoft）** — 社区检测 + 图谱摘要 + 层级检索
- **ReACT 框架** — Thought-Action-Observation 渐进式推理循环
- **Obsidian WikiLink** — 双向链接和 backlink 追踪
- **RAG 最佳实践** — 语义分块 + 父子分块 + BM25/Dense 混合

详见 [`references/methodology.md`](./references/methodology.md)。

---

## 📐 工程结构（渐进式披露）

`SKILL.md` 作为导航入口只保留核心命令和摘要，细节在按需读取的 `references/` 中：

| 文件 | 内容 | 何时读取 |
|------|------|---------|
| `references/kb-structure.md` | 知识库目录结构详解 | init / 调整目录时 |
| `references/doc-standards.md` | frontmatter / WikiLink / 分块规则 | ingest / wiki 写页前 |
| `references/retrieval-config.md` | 检索参数详解（threshold/top_k/mode 等） | 调优召回质量时 |
| `references/agents-claude-spec.md` | AGENTS.md / CLAUDE.md 模板规范 | init 生成治理文件时 |
| `references/methodology.md` | 6 大方法论来源详解 | 深入理解设计哲学时 |
| `references/ingest-pipeline.md` | Agent 处理流程 + 异常处理 + 代码提取 | ingest 执行时 |
| `references/output-templates.md` | 各命令输出格式示例 | 需要示例时 |
| `references/data-schemas.md` | graph.json / sources.json / eval 数据集结构 | 读写元数据时 |
| `references/lint-rules.md` | lint 规则的自动修复建议 | lint 报错时 |
| `references/scripts/` | 5 个脚本模板（init 写入项目） | init 阶段读取 |

---

## 📜 许可证

内部工具 — 美团麦芽田团队

