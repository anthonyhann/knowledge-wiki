<!--
模板：test（测试场景知识 / 经验 / 规则）
位置：.knowledge/tests/{slug}.md
层级：L2（执行编排——测试怎么做、怎么验证、坑点规避）
必填段：TL;DR / 测试对象与场景 / 测试要点与规则 / 验证方式
质量门禁：test_kind 必填（列表，值域 env|rules|checklist|experience|data）；按 kind 分支校验：
  checklist→≥3 条可执行验证点；rules→≥1 条规则+适用范围；experience→≥1 坑点+触发条件+规避方法；
  env→≥1 条可执行命令；data→≥1 条数据构造方法；必须标注 scope（适用模块）或 test_level

适用场景（面向 QA Agent 消费，是项目测试知识的通用化积累）：
- 测试环境与运行方式（env）：Bootstrap 机制、运行命令、覆盖率命令、测试框架配置
- 测试编写规范（rules）：Mock 策略、命名规范、框架惯例（如单例重置、多租户绕过）
- 回归/验收检查清单（checklist）：某模块发版前必测点、AI 出码后必验点
- 测试踩坑经验（experience）：历史踩过的测试坑、易误判的断言、数据路由陷阱
- 测试数据准备（data）：构造特定状态数据的 SQL/接口调用方式

消歧（NOT test）：
- 纯基础设施（测试服 IP/DB 账号）→ ops/
- 故障复盘型踩坑（信号"事故/复盘/根因"）→ case/
- 测试策略决策（如"为什么三层分层"）→ design/ (adr)
- 被测系统表结构知识 → db/（本文档只写坑点 + [[slug]] 引用）

填写指南：
- slug 建议格式：test-{level}-{模块}-{主题}，如 test-unit-mock-strategy、test-order-regression-checklist
  level 取值 unit|integration|e2e|api；跨层通用可省略，如 test-three-layer-selection
  语义区分：e2e = 链路对账/端到端验证类测试（如内部 e2e 链路对账工具，request_id 链路追踪）；
  api = API HTTP 接口测试（如内部单测工具的接口测试层，走 Controller 链路验证接口契约）
- test_kind 是列表：单一规范文档常混合多形态（如 Mock 策略+运行命令），允许 [rules, env] 多值
- 「Use Case 价值」段是 AI QA 反哺的关键，**强烈建议**填满（Agent 何时必须检索本文档）
-->
---
title: {测试知识标题}                         # 例：SaaS 单元测试 Mock 策略与命名规范 / 订单模块回归测试清单
type: test
test_kind: [{kind 列表}]                      # 必填：env | rules | checklist | experience | data（可多值）
test_level: {unit|integration|e2e|api|all}     # 可选，默认 all；e2e=端到端链路对账类，api=API HTTP 接口测试类
scope: [{模块 tag 列表}]                      # 必填之一：适用模块（如 order/delivery/print），跨模块用 global
tags: [{3-5 个标签}]
owner: "@{user-id}"
created: {YYYY-MM-DD}
expires: {YYYY-MM-DD}                         # 默认 180 天
status: draft
sources:
  - "{规范文档 / 测试指南 URL / 手工总结}"
related:
  - "[[{关联流程 slug}]]"
  - "[[{关联接口或术语 slug}]]"
---

## TL;DR

{50-100 词，"覆盖什么测试场景 + 核心规则或坑点 + QA 如何使用"}

## 测试对象与场景

{测的是什么：模块/类/接口清单，适用的测试层（unit/integration/e2e/api），
什么情况下 QA / AI 出码后必须参照本文档。}

## 测试要点与规则

### 规则与规范（rules 类必填）

| # | 规则 | 适用范围 | 约束来源 |
|---|------|---------|---------|
| 1 | {如：setUp() 中反射重置 BaseModel 单例} | {适用类/层} | {框架机制/规范文档} |
| 2 | {如：文件名 {ClassName}Test.php} | {全部} | {规范} |

### 检查清单（checklist 类必填，≥3 条可执行验证点）

- [ ] {验证点 1：可执行的检查动作，含预期结果}
- [ ] {验证点 2}
- [ ] {验证点 3}

## 验证方式

{如何确认测试通过：运行命令 + 预期输出，或断言方式。
coverage/断言覆盖率要求如有。}

## 已知坑点与经验（experience 类必填）

| # | 坑点 | 触发条件 | 规避方法 |
|---|------|---------|---------|
| 1 | {如：订单 ID 未超过归档阈值导致路由到归档表} | {什么场景会踩} | {如何避免} |
| 2 | {...} | {...} | {...} |

## 测试数据准备（data 类必填）

{构造特定状态数据的方法：SQL / 接口调用 / fixtures，
特殊 ID 段、必填字段等约束。}

## 运行环境与命令（env 类必填）

```bash
# {运行/覆盖率/单文件执行命令，必须可直接复制执行}
```

- Bootstrap 机制：{测试如何初始化应用环境}
- 特殊模式：{如 IS_DEBUGGING 等模式开关及其影响}

## 边界与异常场景（可选）

{多租户/归档路由/异步队列等需要特殊处理的边界，
每个场景标注触发条件与处理方式。}

## 关联流程与接口（可选）

- [[{被测流程 slug}]]：被测业务流程
- [[{关联术语 slug}]]：本文档涉及的领域术语

## Use Case 价值（可选，强烈建议）

> **AI QA / 出码时如何应用本文档？**

- **场景识别**：当 AI 执行 {QA/编码场景} 时，必须主动检索本文档
- **强制约束**：在生成 {测试代码/验证步骤} 时，必须包含 {防护措施}
- **反例提示**：禁止 {错误模式}，因为会导致 {后果}

