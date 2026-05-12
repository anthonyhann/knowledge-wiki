# 文档规范（AI-DLC 友好格式）

## Frontmatter 标准

```yaml
---
title: "页面标题"
type: concept|entity|process|source|synthesis|playbook|adr|faq
status: draft|active|deprecated|canonical
created: YYYY-MM-DD
updated: YYYY-MM-DD
owner: "负责人"
tags: [标签1, 标签2]
sources: [source-slug1]
confidence: high|medium|low
links: { supersedes: [], related: [] }
---
```

**status 行为：** canonical=最高优先级/AI禁改 | active=正常参考 | draft=不作决策依据 | deprecated=禁引用

## 标准页面模板

```markdown
## TL;DR（必填，50-100 词，RAG 首要召回）
## 定义 / 背景（200-400 词）
## 核心属性 / 关键步骤（结构化列表或表格）
## 示例（具体、可运行）
## 相关页面（[[WikiLink]] + 关系说明）
## 引用来源（[[source-xxx]]）
```

## WikiLink 规范

- `[[页面名称]]` / `[[页面名称|显示文字]]` / `[[页面名称#章节]]`
- **强制：** 新页面至少 1 个入站链接，在 `index.md` 注册

## AI-DLC 约束

1. TL;DR 独立成块 → 支持快速召回
2. 最多 3 级标题 → 平坦化结构
3. WikiLink 替代"如上所述" → 显式链接
4. 全库统一用词（SCHEMA.md 约束）
5. 代码示例必须含 import → 可独立运行

## people/ 层框架

个人上下文层（Agent 只读），含 `context.md`（角色/技能/负责模块/当前焦点）、`decisions.md`（决策日志，append-only）、`prefs.md`（协作偏好）。

**治理约束：** 只有本人可写 / Agent 禁写 / 不记录主观评价 / 迭代结束时更新 `updated` 字段
