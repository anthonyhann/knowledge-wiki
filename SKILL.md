---
name: knowledge-wiki
description: "结构化知识库构建工具，支持 RAG 问答、Agent 智能推理和 Wiki 自动生成。当用户需要构建结构化知识库、RAG 问答、Agent 智能推理、Wiki 自动生成或知识图谱可视化时使用。触发词：/knowledge-wiki、知识库、RAG、问答、推理、wiki生成、知识图谱、文档导入、知识沉淀。明确指令：/knowledge-wiki（直接触发本 skill，进入知识库构建流程）"
trigger: /knowledge-wiki
---

# /knowledge-wiki

将原始文档转化为结构化、可检索、Agent 可推理的知识库，自动生成相互关联的 Wiki 页面与可视化知识图谱。

**三大核心能力：**
- **RAG 快速问答** — 混合检索（BM25 + Dense + GraphRAG）精准回答日常知识查询
- **Agent 智能推理** — ReACT 渐进式多步推理，自主编排知识检索、MCP 工具与网络搜索
- **Wiki 模式** — Agent 驱动从原始文档自动生成并维护结构化、相互链接的 Markdown 知识库与可视化知识图谱

---

## 子命令速查

```
/knowledge-wiki init [path]              # 初始化知识库结构
/knowledge-wiki ingest <source>          # 导入文档（支持 10+ 格式）
/knowledge-wiki ask "<问题>"             # RAG 快速问答
/knowledge-wiki reason "<复杂问题>"      # ReACT 智能推理（多步 Agent）
/knowledge-wiki wiki [--enable|--disable] # Wiki 模式开关 & 生成/更新 Wiki 页面
/knowledge-wiki graph [path]             # 生成本地知识图谱 HTML 可视化
/knowledge-wiki search <query>           # 混合检索（不生成回答）
/knowledge-wiki lint [path]              # 检查孤立页面、断链、元数据缺失
/knowledge-wiki eval [path]              # 端到端评测（召回率、BLEU/ROUGE）
/knowledge-wiki export <format>          # 导出为 jsonl/qa-pairs/graphrag
/knowledge-wiki status                   # 知识库健康状态
/knowledge-wiki sync [base_ref]          # 分析变更并建议需要更新的文档（pre-push 自动调用）
/knowledge-wiki source <add|list|sync|remove>  # 持久化同步源管理
```

---

## 知识库目录结构

> 详见 `references/kb-structure.md`。核心路径：`pages/`（Wiki主页面）、`inbox/`（草稿）、`.kb-meta/`（CI索引）、`docs/`（按生命周期分区）

---

## /knowledge-wiki init

初始化知识库：创建目录结构 → 安装脚本 → 首次执行。

### 三阶段执行

| Phase | 步骤 | 产出 |
|-------|------|------|
| 1【创建】 | 目录结构 + 8 份治理文件（CLAUDE/AGENTS/AGENT-ROUTING/CONTRIBUTING/SCHEMA/index/strategy/.kb-meta） | 完整目录树 |
| 2【安装】 | 将 `references/scripts/` 写入 `processes/scripts/` + chmod +x；安装 `.git/hooks/pre-push`（已存在→询问覆盖/追加/跳过） | 5 个可执行脚本 + hook |
| 3【执行】 | `generate-docs.sh --all` → `generate-dashboard.py` → `check-all.sh` | `docs/generated/` + `dashboard.md` + 健康报告 |

### 脚本清单

| 脚本 | 用途 | 入参 | 输出 |
|------|------|------|------|
| `generate-docs.sh` | 生成 db-schema / api-changelog | `--all` 或 `--type {name}` | `docs/generated/*.md` |
| `generate-dashboard.py` | 生成知识库看板 | 无 | `dashboard.md` |
| `check-all.sh` | 健康检查总入口 | 无 | stdout 报告 |
| `kb-sync.sh` | 代码变更→文档映射 | `--base-ref {git_ref}` | stdout 变更建议 |
| `pre-push-hook.sh` | pre-push 钩子 | 由 git 自动调用 | 放行/中止 push |
| `install-hooks.sh` | 安装 git hooks | 无 | `.git/hooks/pre-push` |

> **init 输出摘要模板详见** `references/output-templates.md`

---

## /knowledge-wiki ingest

从多种来源导入文档，自动结构化并生成草稿 Wiki 页面。

### 支持的格式

**本地文件：** Markdown / PDF / Word / TXT / 图片(OCR) / CSV·Excel / PPT / JSON / 代码目录 / 对话记录

**在线平台：**

| 平台 | URL 格式 | 访问前提 | 提取策略 |
|------|---------|---------|---------|
| 学城 | `km.sankuai.com/collabpage/<id>` | 美团内网登录 | heading/table/code 全量提取 |
| 飞书 | `*.larkoffice.com/docx/<id>` | 飞书已登录 | 目录树 + 正文分层 |
| Apipost | `docs.apipost.net/docs/detail/<id>` | 公开，无需登录 | 遍历目录树，接口字段→entity 页面 |
| 普通网页 | `https://...` | 公开页面 | 提取正文，去导航噪声 |

### 命令示例

```bash
/knowledge-wiki ingest https://km.sankuai.com/collabpage/2760577321
/knowledge-wiki ingest https://km.sankuai.com/collabpage/2760577321 --recursive
/knowledge-wiki ingest https://bytedance.larkoffice.com/docx/PW6PdvVPFoNwgjxgRPWcwBrknmc
/knowledge-wiki ingest "https://docs.apipost.net/docs/detail/5347b5d25884000" --recursive
/knowledge-wiki ingest ./src/ --type code
/knowledge-wiki ingest --url-file sources.txt
```

### 登录态检测

```
1. agent-browser goto <url>
2. agent-browser get title → 检查是否含"登录"/"Login"/"Sign in"
   - 命中 → 中止，提示用户先登录
   - 正常 → 继续提取
```

### Agent 处理流程

> 详见 `references/ingest-pipeline.md`。四步流程摘要：
> 1. **内容分析** — heading 分段 + 类型识别（entity/adr/faq/process/concept）+ WikiLink 候选
> 2. **草稿生成** — 写入 `inbox/{slug}.md`，含 frontmatter + TL;DR + 标准模板
> 3. **链接发现** — grep pages/ 匹配 → 插入 `[[WikiLink]]` 或 `<!-- suggested -->`→ 更新 backlinks.json
> 4. **索引更新** — graph.json 追加 nodes/links + index.md 新入口

### 异常处理

> 详见 `references/ingest-pipeline.md`。覆盖场景：超大文件拆分 / 网络中断重试 / 格式无解 / 重复导入 / graph.json 损坏 / .kb-meta 重建

### 检查点（ingest 用户确认）

多文件/多页 ingest 时，在以下节点暂停等用户确认：

1. **Step 1 完成后** — 展示分析结果：
   ```
   📋 内容分析完成：
     - 识别出 {N} 个概念/实体
     - 文档类型：{type}
     - 将生成 {M} 个草稿页
   继续生成？[Y/n]
   ```
2. **Step 4 完成后** — 展示生成摘要：
   ```
   ✓ 已写入 inbox/：{文件列表}
   ✓ graph.json 新增 {X} nodes, {Y} links
   是否立即运行 lint 检查？[Y/n]
   ```

> **单文件快速模式**：仅导入 1 个文件且 < 100KB 时，跳过确认直接执行全流程。

---

## /knowledge-wiki ask

**RAG 快速问答**，适合日常知识查询。

### 检索策略（四层混合召回）

| Layer | 方式 | 作用 |
|-------|------|------|
| 1. BM25 | ripgrep 全文扫描 pages/ | 精确关键词匹配 |
| 2. Dense | .kb-meta/chunks.jsonl top-K | 语义向量相似度 |
| 3. GraphRAG | graph.json 1-hop 邻居 | 补充关联上下文 |
| 4. 父子分块 | 子块命中→补充父块 | 防语义截断 |

**融合排序规则：** backlink_count 高优先 → canonical 最高优先级 → deprecated 自动降权

### 检索参数

```bash
/knowledge-wiki ask "问题" --threshold 0.7   # 严格模式（默认 0.6）
/knowledge-wiki ask "问题" --top-k 10         # 扩大召回（默认 5）
/knowledge-wiki ask "问题" --mode bm25|dense|graph  # 指定模式
```

### 输出格式

> 详见 `references/output-templates.md#ask-输出`。核心字段：回答 / 参考来源 + 相关度 / 置信度 / 相关问题推荐

### 零结果 fallback

> 详见 `references/output-templates.md#零结果-fallback`。降级链：放宽 threshold →0.4 → grep 候选 → 建议改写 → 空库提示 ingest

### 多轮上下文

- 前 N 轮压缩为上下文摘要，后续优先在已召回范围检索
- 检测到话题切换时重置检索范围

---

## /knowledge-wiki reason

**ReACT 智能推理**，适合复杂多步任务。

### 推理循环

```
Thought → Action → Observation → ... → Final Answer
```

### 可调用工具集

| 类别 | 工具 | 说明 |
|------|------|------|
| 内置 | `kb_search(query, mode)` | 知识库检索 |
| 内置 | `kb_read(page_slug)` | 读取 Wiki 页面 |
| 内置 | `kb_write(slug, content)` | 写入 inbox/ |
| 内置 | `kb_graph_neighbors(slug, depth)` | 图谱邻居 |
| MCP | 自动发现环境中已安装的 MCP servers | 按需调用 |
| 网络 | `web_search(query)` | 知识库无答案时补充 |

### 参数控制

```bash
/knowledge-wiki reason "问题" --max-steps 5   # 最多推理步数（默认 8）
/knowledge-wiki reason "问题" --no-web        # 禁止网络搜索
/knowledge-wiki reason "问题" --no-mcp        # 禁止 MCP 工具
/knowledge-wiki reason "问题" --verbose       # 显示完整推理链
```

### 输出格式

> 详见 `references/output-templates.md#reason-输出`。核心结构：【Thought】→【Action】→【Observation】→【Final Answer】+ 来源与步数统计

### 检查点与异常处理

**推理中断机制：**
- 每 3 步（Action-Observation）后暂停，展示当前推理进度并询问：`继续推理？[Y/跳到结论/中止]`
- 用户选择"跳到结论" → 基于已有 Observation 生成最终回答
- 用户选择"中止" → 输出已收集的中间结果，不生成最终回答

**异常场景：**

| 场景 | 处理方式 |
|------|----------|
| 达到 max-steps 仍无结论 | 输出"⚠ 推理未收敛"+ 当前最佳中间结果 + 建议拆分问题 |
| MCP 工具调用失败 | 跳过该工具，记录原因，尝试用 kb_search 替代 |
| web_search 超时 | 标注"网络补充缺失"，仅基于本地知识库回答 |
| 循环检测（连续 2 步相同 Action） | 强制跳到 Final Answer，标注"检测到推理循环" |

---

## /knowledge-wiki wiki

**Wiki 模式开关 + 自动生成/更新 Wiki 页面。**

### 开关控制

```bash
/knowledge-wiki wiki --enable      # 开启（后续 ingest 自动触发生成）
/knowledge-wiki wiki --disable     # 关闭（仅存储原始文档）
/knowledge-wiki wiki               # 手动触发：处理 inbox/ 中的所有草稿
/knowledge-wiki wiki --update <slug>   # 更新指定页面
/knowledge-wiki wiki --approve-all     # 批量升级 inbox/ 草稿
```

### Wiki 质量门控（draft → stable）

- [ ] TL;DR 存在且 ≤ 100 词
- [ ] 至少 1 个入站链接
- [ ] 所有 WikiLink 目标存在（无断链）
- [ ] `sources` 字段非空
- [ ] 无未处理 `<!-- suggested -->` 链接
- [ ] `<!-- unverified: -->` 已人工确认

### 输出格式

> 详见 `references/output-templates.md#wiki-输出`。两类：手动触发 Wiki 生成报告 / --update 更新输出

### 72 小时决策入库规

重要决策发生后 72 小时内，Agent 自动提示创建 ADR：
```
发现决策点：[摘要]  →  建议创建：docs/design-docs/[主题]-adr.md
```

---

## /knowledge-wiki graph

生成本地知识图谱可视化 `graph.html`（零依赖，双击即开）。

### 可视化要求

1. D3.js v7 力导向布局，节点大小按 `backlink_count` 缩放
2. 颜色方案：concept→蓝 / entity→绿 / process→橙 / source→灰 / canonical→金色边框 / deprecated→半透明
3. 交互：点击高亮邻居 / 双击显示路径 / 悬停 TL;DR tooltip / 搜索框过滤 / 类型筛选 / 缩放平移

> **graph.json 结构详见** `references/data-schemas.md`

---

## /knowledge-wiki eval

端到端评测：检索 + 生成全链路。

### 评测指标

> **数据集格式详见** `references/data-schemas.md`

| 指标 | 说明 |
|------|------|
| 召回命中率 | 命中的期望页面 / 期望总数 |
| 精确率 | 命中页面 / 实际召回数 |
| BLEU-4 | n-gram 重叠 |
| ROUGE-L | 最长公共子序列覆盖率 |
| 幻觉率 | 无依据陈述比例 |
| 响应延迟 | P50 / P95 |

---

## /knowledge-wiki lint

扫描知识库健康状态，为每个问题输出自动修复建议。

| 检查类型 | 级别 | 条件 |
|----------|------|------|
| 断裂链接 | ERROR | `[[target]]` 不存在 |
| 缺失 frontmatter | ERROR | 任意遗漏 |
| deprecated 仍被引用 | ERROR | 任意 |
| 文件行数超限 | ERROR | > 800 行 |
| 孤立页面 | WARNING | 无入站链接 |
| 缺失 TL;DR | WARNING | stable 页面 |
| last-reviewed 过期 | WARNING | > 90 天 |

> **自动修复建议详见** `references/lint-rules.md`

---

## /knowledge-wiki source

**持久化同步源管理** — 将"关注文档更新"持久化，支持增量同步。

### 子命令

```bash
/knowledge-wiki source add <url> [--name <别名>] [--recursive] [--tags <tag1,tag2>]
/knowledge-wiki source list
/knowledge-wiki source sync [source-id]    # 省略则同步所有
/knowledge-wiki source remove <source-id>  # 不删除已生成页面
```

### 增量同步逻辑

```
sync 执行：
  1. 读取 .kb-meta/sources.json → 遍历 status=active 的源
  2. agent-browser goto <url> → 提取内容
  3. 计算 hash 与 last_hash 对比
     hash 相同 → 跳过 | hash 不同 → 触发 ingest --update
  4. 更新 last_synced / last_hash
```

> **sources.json 结构 + stale 判定详见** `references/data-schemas.md`

---

## /knowledge-wiki sync

**Push 前知识库同步检查**，由 pre-push hook 自动触发。

### 变更映射规则

| 变更文件模式 | 建议更新的知识库文档 |
|------------|-------------------|
| `<skill>/SKILL.md` | `pages/entities/<skill>.md` |
| `<skill>/README.md` | `pages/entities/<skill>.md` |
| `<dir>/*.go\|py\|ts\|js\|php` | `pages/entities/<dir>.md` |
| `processes/**` | `pages/processes/workflow.md` |

### pre-push hook 行为

```
git push → pre-push hook
  ├─ 检查一：同步源陈旧检测（sources.json 中 stale/error）
  ├─ 检查二：代码变更→文档映射（kb-sync.sh）
  └─ 两者无问题 → 放行 ✓
     有问题 → 四选一：[1]同步源 [2]更新文档 [3]都做 [4]跳过直接推送
```

---

## 文档规范（AI-DLC 友好格式）

> 详见 `references/doc-standards.md`。要点：
> - **Frontmatter 必填：** title / type / status / created / tags / sources
> - **status 行为：** canonical=最高优先级/AI禁改 | active=正常参考 | draft=不作决策依据 | deprecated=禁引用
> - **WikiLink 强制：** 新页面至少 1 个入站链接，在 `index.md` 注册
> - **页面模板：** TL;DR → 定义 → 核心属性 → 示例 → 相关页面 → 引用来源

---

## AGENTS.md / CLAUDE.md 规范

> 详见 `references/agents-claude-spec.md`。要点：
> - **CLAUDE.md 禁止行为：** 修改 canonical / archives / .kb-meta / generated / graph.* / dashboard.md；引用 deprecated；未 lint 即升级 draft
> - **写入规则：** 新内容 → inbox/ → 人工确认后升级
> - **读取优先级：** canonical > active > draft > deprecated
> - **AGENTS.md ≤100 行**，超限移至 AGENT-ROUTING.md
> - **people/ 层：** Agent 只读，仅本人可写，不记录主观评价

---

## 检索与分块配置

> 详见 `references/retrieval-config.md`。要点：
> - **分块：** TL;DR ~80 token 独立成块 | 定义 ~300 token | 示例代码完整不截断 | 相邻 20% 重叠
> - **检索优先级：** 命令行参数 > SCHEMA.md 配置 > 内置默认值
> - **FAQ 优先精确匹配：** Layer 0 精确匹配问题文本 → Layer 1 标准四路召回

---

## /knowledge-wiki export

```bash
/knowledge-wiki export jsonl       # RAG embedding 就绪的 chunks
/knowledge-wiki export qa-pairs    # Instruction Tuning 问答对
/knowledge-wiki export graphrag    # GraphRAG 社区摘要格式
```

> **三种格式输出示例详见** `references/output-templates.md#export-输出格式`

---

## 执行原则

1. **先读 CLAUDE.md** — 进入知识库后首先读取协作契约
2. **先读后写** — ingest 前先 status，避免重复导入
3. **草稿优先** — 自动生成一律放入 inbox/，确认后升级
4. **溯源强制** — 所有页面必须标注 sources
5. **canonical 不可变** — AI 禁止修改
6. **deprecated 禁引用** — 自动提示替换
7. **生成文件不可手动编辑** — CI 自动刷新会覆盖
8. **lint 优先** — wiki 生成前先 lint
9. **增量更新** — ingest --update 只处理变更
10. **AGENTS.md 防膨胀** — 超 100 行时移至 AGENT-ROUTING.md

---

## 方法论来源

> 详见 `references/methodology.md`。核心：AI-DLC 框架 / Zettelkasten / GraphRAG / ReACT / RAG 最佳实践
