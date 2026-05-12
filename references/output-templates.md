# 输出格式模板

## init 完成输出

```
✓ knowledge-wiki 初始化完成
路径：.knowledge/

📁 目录结构已创建
📄 治理文件已生成（CLAUDE.md / AGENTS.md / AGENT-ROUTING.md / CONTRIBUTING.md）
🔧 脚本已安装（5 个脚本，均已赋予执行权限）
🪝 pre-push hook 已安装：.git/hooks/pre-push

📊 首次生成
  ✓ docs/generated/db-schema.md
  ✓ docs/generated/api-changelog.md
  ✓ dashboard.md

🏥 初始健康检查
  总文档：1（index.md）  断链：0  孤立页面：0  frontmatter 缺失：0

💡 下一步
  1. 编辑 strategy/00_总纲.md 填写团队黄金原则
  2. 运行 /knowledge-wiki ingest <文档> 导入已有文档
  3. 运行 /knowledge-wiki source add <url> 注册在线同步源
```

## ask 输出

```
**回答：** [精准回答，引用来源标注]
**参考来源：** [[page-slug]] (相关度: ⭐⭐⭐⭐) - TL;DR 片段
**置信度：** high / medium / low
💡 相关问题推荐：[基于 WikiLink 网络自动生成 3 个]
```

### 零结果 fallback

```
1. 放宽 threshold 为 0.4 再检索一次（自动，不提示用户）
2. 仍无结果 → 检查是否有类似页面：
   rg -l "{query_keywords}" pages/ → 列出相关文件名
3. 返回格式：
   ❌ 未找到直接答案。
   💬 建议：
     - 尝试换个词问："{suggested_rewording}"
     - 相关页面（可能有帮助）：[[{related_slug}]]
     - 或使用 /knowledge-wiki reason 深度推理
4. 知识库完全为空时（pages/ = 0 文件）：
   ❌ 知识库尚未导入任何文档。
   💡 请先运行：/knowledge-wiki ingest <文档源>
```

## reason 输出

```
🧠 ReACT 推理（{current_step}/{max_steps}）

【Thought】需要了解当前架构和历史决策...
【Action】kb_search("doudian 5xx 限流")
【Observation】命中 2 页：[[doudian-adapter]] [[rate-limiter-v2-adr]]
...
【Final Answer】
  排查思路：1. 确认 send/receive 侧 → 2. 检查 Tag 路由...

**参考来源：** [[doudian-adapter]] [[rate-limiter-v2-adr]]
**推理步数：** 4/8 | **工具调用：** kb_search×2, kb_read×1
**网络补充：** 未使用
```

## wiki 输出

**手动触发（处理 inbox/）：**
```
📤 Wiki 生成报告：
  升级：inbox/api-gateway.md → pages/entities/api-gateway.md ✓
  跳过：inbox/draft-incomplete.md（原因：缺 TL;DR）
  新增 WikiLink：3 个 | graph.json +2 nodes +3 links
```

**--update 输出：**
```
✓ 已更新 pages/entities/{slug}.md
  变更：TL;DR 重写 | +2 WikiLink | sources 追加 1 条
  graph.json 已同步
```

## export 输出格式

**jsonl**（每行一个 chunk，写入 `.knowledge/exports/chunks.jsonl`）：
```jsonl
{"id":"api-gateway__tldr","text":"API 网关负责...","metadata":{"source":"pages/entities/api-gateway.md","type":"entity","section":"tldr","tokens":78}}
```

**qa-pairs**（写入 `.knowledge/exports/qa-pairs.jsonl`）：
```jsonl
{"instruction":"API 网关的限流策略有哪些？","output":"令牌桶 + 滑动窗口...","source":"pages/entities/api-gateway.md"}
```

**graphrag**（写入 `.knowledge/exports/graphrag/`）：
```
graphrag/
├── entities.csv      # id,name,type,description
├── relationships.csv # source,target,relation,weight
└── communities.json  # 社区检测结果 + 每社区摘要
```
