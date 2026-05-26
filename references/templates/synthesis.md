<!--
  synthesis 模板 — Ask 回流综合分析文档
  由 /knowledge-wiki ask 触发回流时使用（--from-answer 或自动生成）
  target_dir: synthesis/
  layer: L2
  expires_days: 60
-->

# {title}

> **类型**：synthesis（综合分析）| **状态**：{status} | **过期**：{expires}
> **来源**：Ask 回流，综合了 {N} 篇原始文档 | **触发问题**："{derived_question}"

---

## TL;DR

{50-100 词综合结论。回答"这个分析的核心发现是什么 + 关键结论一句话"。}

## 综合问题

{描述本次综合分析要解决的核心问题。通常是用户在 ask 中提出的原始问题，或 AI 在回答过程中发现的跨文档关联问题。}

## 来源文档

**必须 ≥2 篇，且均非 deprecated。**

| # | 文档路径 | 类型 | 贡献要点 |
|---|---------|------|---------|
| 1 | `[[slug-a]]` | {type-a} | {这篇文档提供了什么关键信息} |
| 2 | `[[slug-b]]` | {type-b} | {这篇文档提供了什么关键信息} |
| 3 | `[[slug-c]]` | {type-c} | （如有第 3 篇） |

## 综合结论

{核心分析结果。必须有明确论点，不能是原文的简单拼接。应包含：
- 跨文档的关联发现
- 对比或矛盾的分析
- 可操作的建议或结论
- 如有数据支撑，引用具体数值}

### 对比分析（可选）

{如果涉及多文档之间的对比（如不同版本的参数差异、不同模块的行为对比），在此展开表格化对比。}

### 关联发现（可选）

{在综合过程中发现的意外关联——如 A 文档提到的配置在 B 文档中有冲突值、两个流程文档描述的步骤顺序不一致等。这些发现可能指向需要进一步调查的问题。}

### 局限与假设（可选）

{声明本分析的边界条件：
- 基于哪些文档、未参考哪些文档
- 做了哪些简化假设
- 哪些结论需要人工验证
- 原始文档的时效性（是否已接近过期）}

---

## Frontmatter 模板（写入时使用）

```yaml
---
title: "{综合分析标题}"
type: synthesis
tags: [{从来源文档提取的关键词}, {3-5个}]
owner: "@{mis-id}"
created: {YYYY-MM-DD}
expires: {created + 60 天}
status: draft                  # synthesis 一律 draft，由 health audit 升级
sources:
  - "由 /knowledge-wiki ask '{derived_question}' 自动生成，综合了以下文档："
  - "  - [[slug-a]] ({type-a})"
  - "  - [[slug-b]] ({type-b})"
derived_from:                    # 必填：记录所有被综合的原始文档
  - slug: "slug-a"
    title: "{原文标题}"
  - slug: "slug-b"
    title: "{原文标题}"
derived_question: "{触发此综合分析的原始用户问题}"  # 必填
related:
  - "[[slug-a]]"
  - "[[slug-b]]"
---
```

### synthesis 特殊约束

1. **禁止二次回流**：当 `ask` 命中 synthesis 类型文档时，**不显示**回流提示（`💡 此回答...`）。synthesis 本身就是派生知识，再次回流会导致知识套娃。
2. **derived_from 必填**：每篇 synthesis 必须记录所有被综合的原始文档 slug，便于后续追溯和级联过期的判断。
3. **短过期**：expires_days = 60 天（比普通 type 的 90 天更短），因为 synthesis 是派生知识，其有效性依赖于原始文档的有效性。
4. **独立目录**：synthesis 文档存放在 `.knowledge/synthesis/` 目录下，作为第 9 个业务目录独立管理。