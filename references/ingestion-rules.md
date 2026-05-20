# 录入结构化规则（in 子命令使用）

> 由 `/knowledge-wiki in` 文本/URL/文件三类输入共享。SKILL.md 仅保留入口与索引，本文件是唯一权威源。

---

## AI 结构化流程（11 步，含模板加载与质量门禁）

```
1. 提取 title
2. 推断 type（见下方 type 推断规则）
2.5 加载 type 专属模板（references/templates/_registry.yaml → templates/{type}.md）
3. 提取 tags（3-5 个，从正文提取核心实体词）
4. 生成 TL;DR（50-100 词，必填，回答"这是什么+核心结论"）
5. 按模板骨架整理详情正文（必填段不可缺，可选段视内容补充）
6. 扫描 .knowledge/ 推荐 related（rg 命令见下，结果取交集 ≥1 即推荐）
7. 生成 slug（规则见下）
8. 若目标文件已存在 → 询问：覆盖 / 追加 / 中止
8.5 质量门禁：校验 _registry.yaml 中 required_sections 与 quality_gate；缺失即返回用户补充
9. 写入 .knowledge/{对应目录}/{slug}.md
```

> **2.5 步：模板加载**——AI 必须读取 `references/templates/_registry.yaml`，按 `templates[type]` 定位到对应 `.md` 模板文件，按其骨架整理正文。**禁止**用统一的「TL;DR + 详情」二段式覆盖所有 type。
>
> **8.5 步：质量门禁**——写入前对照 `_registry.yaml` 的 `required_sections` 列表逐项检查，并运行 `quality_gate` 文本校验（如 "glossary 必须含技术字段名映射"）。任一项不满足时**禁止**写入，向用户返回缺失清单。

### Step 6 — related 推荐 rg 模板

对每个 tag 并行搜索：

```bash
rg -l "^tags:.*\b<tag>\b" .knowledge/ --type md
# 取所有 tag 命中文件的并集，再保留至少命中 2 个 tag 的文件作为 related
# 提取目标文件 frontmatter 中的 slug（通常即 basename 去 .md），生成 [[slug]] 引用
```

### Step 7 — slug 生成规则

1. 中文 → 拼音（不带声调），用 `-` 连接：`打印服务超时机制` → `da-yin-fu-wu-chao-shi-ji-zhi`；若英文术语已在 title 中出现，优先用英文：`打印服务超时机制(print timeout)` → `print-timeout`
2. 英文 → 全小写，空格/下划线/标点 → `-`
3. 仅保留 `[a-z0-9-]`，连续 `-` 折叠为一个，去首尾 `-`
4. 长度 ≤ 50 字符；超长按词截断到最近的 `-`
5. 与 `.knowledge/` 已存在文件冲突时，依次追加 `-2`、`-3`，并在录入确认中提示用户考虑改用 `--update`

---

## type 推断规则

按以下优先级从高到低匹配，命中即停：

| 优先级 | 判定条件 | type |
|--------|---------|------|
| 1 | 内容是单个术语/概念的定义或解释 | `glossary` |
| 2 | 含"架构"/"系统设计"/"整体方案"且描述当前状态 | `architecture` |
| 3 | 含"方案"/"实现"/"技术选型"且针对某需求 | `solution` |
| 4 | 含"决策"/"为什么选"/"ADR"/"取舍" | `adr` |
| 5 | 含"需求"/"PRD"/"验收"/"用户故事" | `requirement` |
| 6 | 含"流程"/"时序"/"步骤"且描述业务流转 | `flow` |
| 7 | 含"接口"/"API"/"字段"/"请求响应" | `api` |
| 8 | 含"表"/"模型"/"存储"/"索引"且描述数据结构 | `data` |
| 9 | 含"运维"/"告警"/"大促"/"保障"/"超时"/"阈值"/"配置" | `ops` |
| 10 | 含"故障"/"复盘"/"事故"/"根因" | `incident` |
| 11 | 含"规则"/"策略"/"计算"/"扣费"且为业务规则 | `bizrule` |
| 12 | 含"会议"/"讨论"/"对齐"/"评审" | `meeting` |
| 兜底 | 无法匹配时 | `ops` |

## type 映射表（type → 写入目录 + 专属模板）

> **唯一权威源**：`references/templates/_registry.yaml`。下表为速查，字段语义与 expires 默认值以注册表为准。

| type | 写入目录 | 模板文件 | 层级 | 默认 expires |
|------|---------|---------|------|--------------|
| glossary | glossary/ | `templates/glossary.md` | L1 | never |
| architecture | design/ | `templates/architecture.md` | L1 | 180 天 |
| solution | design/ | `templates/solution.md` | L2 | 90 天 |
| adr | design/ | `templates/adr.md` | L1 | never |
| requirement | requirements/ | `templates/requirement.md` | L1 | 90 天 |
| flow | flows/ | `templates/flow.md` | L2 | 90 天 |
| api | apis/ | `templates/api.md` | L3 | 90 天 |
| data | data/ | `templates/data.md` | L3 | 90 天 |
| ops | ops/ | `templates/ops.md` | L3 | 90 天 |
| incident | incidents/ | `templates/incident.md` | L2 | 365 天 |
| bizrule | bizrules/ | `templates/bizrule.md` | L2 | 180 天 |
| meeting | meetings/ | `templates/meeting.md` | 辅助 | 180 天 |

---

## 文档 frontmatter 通用格式

所有 type 共享同一份 frontmatter 字段；正文骨架由各 type 模板定义。

```yaml
---
title: 打印服务超时机制
type: ops
tags: [print, timeout, fallback]
owner: "@hanqiang"
created: 2026-05-12
expires: 2026-08-12        # 由 _registry.yaml 中该 type 的 expires_days 决定；填 never 表示长期有效
status: draft              # 新录入默认 draft
sources:
  - "手工录入 @hanqiang 2026-05-12"
  # URL 来源："https://xxx.feishu.cn/docx/xxx（同步于 2026-05-12）"
related:
  - "[[print-service-overview]]"
---

# 正文骨架严格按 references/templates/{type}.md 填写
# 每个模板顶部 HTML 注释列出了：必填段、质量门禁、填写指南
```

### 模板库使用要点

1. **不允许编造模板段**——AI 必须按模板的 `required_sections` 顺序与命名生成章节，不允许自行增删一级标题
2. **可选段按内容判断**——optional_sections 仅在内容确实涵盖时填写，无内容时整段省略（不留空骨架）
3. **必填段为空时不允许写入**——8.5 质量门禁会拦截，返回 "缺失段：xxx" 让用户补充
4. **新增 type 流程**——先在 `_registry.yaml` 登记 → 再创建 `templates/{type}.md` → 同步更新本文件 type 推断规则与映射表

---

## 录入确认输出模板

```
✓ 已写入 .knowledge/ops/print-timeout.md

标题：打印服务超时机制 | 类型：ops | 过期：2026-08-12
关联：[[print-service-overview]]

当前为 draft，确认准确后运行：
  /knowledge-wiki health audit print-timeout
```

---

## --update <slug>：变更预览三选一

```
将更新：.knowledge/{dir}/{slug}.md
  原 title：... | 新 title：...
  原 sources：3 条 | 新增 1 条
  正文变更：-{old_lines} +{new_lines}

[1] 覆盖正文（保留 created/owner，更新 updated，追加 sources）
[2] 追加为新版本节（原正文下方添加 `## 修订 YYYY-MM-DD` 标题并追加新内容）
[3] 中止
```

- 选 [1]：保留 `created` / `owner`，更新 `updated` 为今日，正文覆盖，`sources` 追加新来源
- 选 [2]：适用于保留历史诠证场景（如决策复盘、不同时期阐述差异）

---

## source 管理

**source remove `<id>`**：删除前先 rg 查找该 source 被哪些文档引用（检查 frontmatter `sources:` 字段包含该 url）。

有引用时询问：

```
检测到 {N} 个文档引用了该源：
  - apis/print-api.md
  - flows/print-fallback.md
[1] 仅删源，保留文档中的来源记录（安全，不丢弃历史诠证）
[2] 删源 + 在引用文档 sources 末尾追加："原源已移除 YYYY-MM-DD"
[3] 中止
```

无引用时直接删除。

`.knowledge/.sources.yaml` 格式：

```yaml
sources:
  - id: print-api-doc
    name: 打印接口文档
    url: https://docs.apipost.net/docs/detail/xxx
    tracked_by: "@hanqiang"
    last_hash: ""
    last_synced: ""
    status: active           # active | stale | error
    related_docs:
      - apis/print-api.md

