<!--
模板：data（数据模型）
位置：.knowledge/data/{slug}.md
层级：L3（原子能力——存储）
必填段：TL;DR / 数据模型 / 字段定义
质量门禁：字段定义必须包含类型、是否可空、业务含义

填写指南：
- 一个表/集合/Redis Key 一篇文档，便于 ask 精准命中
- DDL 优先贴真实建表语句（脱敏后），避免再次推导
- 字段中涉及业务术语必须 [[glossary-slug]] 引用
-->
---
title: {数据模型名称}                          # 例：配送单表 delivery_order
type: data
tags: [{3-5 个标签}]
owner: "@{mis-id}"
created: {YYYY-MM-DD}
expires: {YYYY-MM-DD}                          # 默认 90 天
status: draft
sources:
  - "{DDL 文件路径或代码 model 路径}"
related:
  - "[[{关联接口 slug}]]"
  - "[[{关联术语 slug}]]"
---

## TL;DR

{50-100 词，"存什么数据 + 谁读谁写 + 大致量级"}

## 数据模型

| 项 | 值 |
|----|----|
| 存储类型 | MySQL / MongoDB / Redis / ClickHouse / Doris |
| 库名 | `{db_name}` |
| 表名 | `{table_name}` |
| 大致行数 | {N} 万 / 亿 |
| 增长速率 | {每日 N 条} |

### DDL（如适用）
```sql
CREATE TABLE `{table_name}` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  -- ... 完整 DDL（脱敏后）
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 字段定义

| 字段 | 类型 | 可空 | 默认值 | 业务含义 | 示例 |
|------|------|------|--------|---------|------|
| `id` | bigint | 否 | AUTO | 主键 | `1001` |
| `order_id` | varchar(64) | 否 | — | [[order-id]] 订单号 | `"ORD20260520001"` |
| `status` | tinyint | 否 | 0 | 状态枚举：0=待处理 1=进行中 2=完成 | `1` |
| `ctime` | int | 否 | 0 | 创建时间戳（秒） | `1716192000` |
| `utime` | int | 否 | 0 | 更新时间戳（秒） | `1716192000` |

## 索引策略（可选）

| 索引名 | 字段 | 类型 | 用途 |
|--------|------|------|------|
| `PRIMARY` | `id` | 主键 | — |
| `idx_order_id` | `order_id` | 唯一 | 按订单号查询 |
| `idx_status_ctime` | `status, ctime` | 普通 | 状态+时间范围查询 |

## 容量与分片（可选）

- 分库分表策略：{按 user_id hash / 按时间分表 / 单表}
- 容量规划：{单表上限 / 扩容方案}
- 归档策略：{N 个月前的数据归档到 xxx}

## Redis Key 命名（如适用）

| Key 模式 | 类型 | TTL | 用途 |
|---------|------|-----|------|
| `delivery:{order_id}` | String | 30s | 配送状态缓存 |
| `delivery:lock:{order_id}` | String | 10s | 分布式锁 |

## 关联模型（可选）

- 主从关系：本表 1:N → [[{relation-slug}]]
- 外键引用：`merchant_id` → [[merchant-table]]

