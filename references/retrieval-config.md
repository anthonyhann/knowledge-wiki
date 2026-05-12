# 检索与分块配置

## RAG 分块规则

- TL;DR 独立成块（~80 token）— 高优先级召回
- 定义章节独立成块（~300 token）— 完整概念
- 示例代码独立成块（保持完整，不截断）
- 相邻 chunk 20% 重叠
- 父子分块：子块（精准匹配）+ 父块（上下文补充）

## 持久化检索配置（SCHEMA.md）

```yaml
retrieval:
  threshold: 0.65        # 相关度阈值（默认 0.6）
  top_k: 8               # 召回数量（默认 5）
  default_mode: hybrid   # hybrid / bm25 / dense / graph
  faq_exact_match: true  # FAQ 页面优先精确匹配
  context_window: 3      # 多轮对话保留历史轮数
```

**优先级：** 命令行参数 > SCHEMA.md 配置 > 内置默认值

## FAQ 知识库类型

`type: faq` 专为高频重复问答优化，使用 Q&A 对结构，RAG 召回时优先精确匹配问题文本。

**与 concept/entity 区别：** 内容为问答对列表 / 每 Q&A 单独成块 / 问题文本精确匹配优先

**FAQ 召回规则：**
```
Layer 0（优先）：在 faq 页中精确匹配问题文本
  → rg -l "Q:.*XXX" pages/ → 命中直接返回，置信度 high
Layer 1：退化到标准四路召回
```
