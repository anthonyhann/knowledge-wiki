<!--
模板：meeting（会议记录）
位置：.knowledge/meetings/{slug}.md
层级：辅助
必填段：TL;DR / 会议信息 / 讨论要点 / 结论与 Action
质量门禁：结论与 Action 必须有责任人，至少 1 项

填写指南：
- slug 建议：YYYY-MM-DD-{主题}，如 2026-05-20-delivery-arch-review
- 重要的架构/技术决策会议，结论应另外提炼为 [[adr-xxx]] 形式持久化
- 会议本身的价值递减很快，expires 默认 180 天，过期后大多自动废弃
-->
---
title: {会议主题}                              # 例：配送架构评审会
type: meeting
tags: [{3-5 个标签}]
owner: "@{mis-id}"
created: {YYYY-MM-DD}
expires: {YYYY-MM-DD}                          # 默认 180 天
status: draft
sources:
  - "{飞书会议 / 飞书文档 URL}"
related:
  - "[[{相关方案 slug}]]"
---

## TL;DR

{50-100 词，"会议主题 + 主要结论 + 关键 Action"}

## 会议信息

| 项 | 值 |
|----|----|
| 时间 | {YYYY-MM-DD HH:MM} |
| 时长 | {N 分钟} |
| 主持人 | @{mis-id} |
| 记录人 | @{mis-id} |
| 类型 | 评审 / 对齐 / 复盘 / 同步 |

## 参会人（可选）

- 业务方：@{mis-id} / @{mis-id}
- 技术方：@{mis-id} / @{mis-id}
- 产品方：@{mis-id}

## 讨论要点

### 议题 1：{议题}
- 现状：{讨论的现状描述}
- 分歧：{各方观点}
- 共识：{达成的一致}

### 议题 2：{议题}
- ...

## 结论与 Action

| # | 结论 / Action | 责任人 | 截止日 | 状态 |
|---|--------------|-------|--------|------|
| 1 | {决策结论或具体动作} | @{mis-id} | {YYYY-MM-DD} | TODO |
| 2 | ... | @{mis-id} | {YYYY-MM-DD} | TODO |

## 待跟进项（可选）

- {未达成共识、需要后续会议讨论的事项}
- {依赖外部确认的事项}

## 关联文档（可选）

- [[{adr-slug}]]：本次会议沉淀为 ADR
- [[{solution-slug}]]：本次会议讨论的方案

