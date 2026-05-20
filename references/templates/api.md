<!--
模板：api（接口约定）
位置：.knowledge/apis/{slug}.md
层级：L3（原子能力）
必填段：TL;DR / 接口概述 / 请求参数 / 响应结构 / 错误码
质量门禁：请求参数与响应结构必须完整列出字段类型；错误码至少 1 个

填写指南：
- 字段名优先使用代码中的真实命名（snake_case 或 camelCase 保持一致）
- 字段说明若涉及业务术语，必须用 [[glossary-slug]] 引用
- 接口变更必须 --update 而非新建，保留历史诠证
-->
---
title: {接口名称}                              # 例：配送发单接口 / OPEN-API 回调
type: api
tags: [{3-5 个标签}]
owner: "@{mis-id}"
created: {YYYY-MM-DD}
expires: {YYYY-MM-DD}                          # 默认 90 天
status: draft
sources:
  - "{ApiPost / 飞书文档 / 代码路径}"
related:
  - "[[{关联术语 slug}]]"
  - "[[{关联流程 slug}]]"
---

## TL;DR

{50-100 词，"这个接口做什么 + 谁调用谁 + 关键约束"}

## 接口概述

| 项 | 值 |
|----|----|
| 协议 | HTTP / RPC / gRPC |
| 方法 | GET / POST / PUT / DELETE |
| 路径 | `/api/v1/xxx` |
| 鉴权 | {Token / Sign / 内网调用} |
| 服务方 | {appkey / 服务名} |
| 调用方 | {上游服务名} |

## 请求参数

### Header
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `Authorization` | string | 是 | Bearer Token |

### Query / Body
| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `order_id` | string | 是 | [[order-id]] 订单号 | `"ORD20260520001"` |
| `merchant_id` | int64 | 是 | 商家 ID | `12345` |
| `extra` | object | 否 | 扩展字段 | `{"tag":"vip"}` |

## 响应结构

### 成功响应（HTTP 200）
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "delivery_id": "DLV20260520001",
    "status": "dispatched"
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 业务码，0 表示成功 |
| `data.delivery_id` | string | [[delivery-order]] 配送单号 |
| `data.status` | string | 状态枚举：dispatched / delivering / done |

## 错误码

| code | message | 含义 | 建议处理 |
|------|---------|------|---------|
| 1001 | invalid_param | 参数校验失败 | 检查请求字段 |
| 1002 | merchant_not_found | 商家不存在 | 确认 merchant_id |
| 5000 | internal_error | 服务异常 | 重试或告警 |

## 调用示例（可选）

```bash
curl -X POST "https://api.example.com/api/v1/delivery" \
  -H "Authorization: Bearer xxx" \
  -d '{"order_id":"ORD20260520001","merchant_id":12345}'
```

## 限流与超时（可选）

- 客户端超时：{N 秒}
- 服务端 SLA：P99 < {N} ms
- 限流：{QPS 阈值 / 用户级 / 接口级}
- 重试策略：{次数 / 间隔 / 幂等保证}

## 字段映射（可选，跨系统时使用）

| 本接口字段 | 上游字段 | 下游字段 | 数据库字段 |
|----------|---------|---------|-----------|
| `delivery_id` | `dispatch_no` | `dlv_id` | `delivery_order.id` |

