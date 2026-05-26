# 分段索引规则（index）

> 由 `/knowledge-wiki in`（写入时更新）和 `/knowledge-wiki ask`（查询时读取）共享。
> `health` 负责索引重建与一致性校验。SKILL.md 仅保留入口，本文件为唯一权威源。

---

## 设计原则

1. **按 type 分段**：每个 idx 文件只索引对应 type 的文档，减少单文件体积和冲突面
2. **懒加载**：ask 时先推断可能属于哪个 idx，只读那一个，不读全部
3. **append-only 写入**：in 时追加一行；update/deprecate 时标记行状态，不删除
4. **health 重建**：定期全量重建保证一致性

---

## 目录结构

```
.knowledge/
├── .index/
│   ├── _meta.yaml              # 元数据：各 idx 最后更新时间 + 条目数
│   ├── glossary.idx.md         # 索引 glossary/
│   ├── design.idx.md           # 索引 design/ (architecture | solution | adr)
│   ├── requirements.idx.md     # 索引 requirements/
│   ├── flows.idx.md            # 索引 flows/
│   ├── case.idx.md             # 索引 case/
│   ├── apis.idx.md             # 索引 apis/
│   ├── db.idx.md               # 索引 db/
│   ├── ops.idx.md              # 索引 ops/
│   └── synthesis.idx.md       # 索引 synthesis/
```

### type → idx 文件映射表

| idx 文件 | 覆盖 type | 覆盖目录 |
|---------|----------|---------|
| `glossary.idx.md` | `glossary` | `glossary/` |
| `design.idx.md` | `architecture` / `solution` / `adr` | `design/` |
| `requirements.idx.md` | `requirement` | `requirements/` |
| `flows.idx.md` | `flow` | `flows/` |
| `case.idx.md` | `case` | `case/` |
| `apis.idx.md` | `api` | `apis/` |
| `db.idx.md` | `db` | `db/` |
| `ops.idx.md` | `ops` | `ops/` |
| `synthesis.idx.md` | `synthesis` | `synthesis/` |

---

## _meta.yaml 格式

```yaml
# .knowledge/.index/_meta.yaml
# 由 health index-rebuild 自动生成，禁止手动编辑

version: 1
last_full_rebuild: "2026-05-26"
rebuild_threshold_days: 30        # 超过此天数未重建时 health 提示

indexes:
  glossary:
    file: glossary.idx.md
    entries: 12
    last_updated: "2026-05-26"
  design:
    file: design.idx.md
    entries: 8
    last_updated: "2026-05-25"
  requirements:
    file: requirements.idx.md
    entries: 3
    last_updated: "2026-05-20"
  flows:
    file: flows.idx.md
    entries: 15
    last_updated: "2026-05-26"
  case:
    file: case.idx.md
    entries: 5
    last_updated: "2026-05-24"
  apis:
    file: apis.idx.md
    entries: 20
    last_updated: "2026-05-26"
  db:
    file: db.idx.md
    entries: 7
    last_updated: "2026-05-23"
  ops:
    file: ops.idx.md
    entries: 10
    last_updated: "2026-05-26"
  synthesis:
    file: synthesis.idx.md
    entries: 0
    last_updated: "2026-05-26"

total_entries: 80
```

---

## idx 条目格式

每个 idx 文件为 markdown 表格格式：

```markdown
# {type} 索引

> 最后更新：2026-05-26 | 条目数：12 | 由 health index-rebuild 或 in 自动维护

| slug | title | tags | status | expires | TL;DR（一句话） | created |
|------|-------|------|--------|---------|----------------|---------|
| print-timeout | 打印服务超时机制 | print,timeout,ops | active | 2026-08-19 | 打印服务超时30s后fallback到本地缓存 | 2026-05-22 |
| delivery-order | 配送单定义 | order,delivery,glossary | canonical | never | 三方配送业务的核心单据实体 | 2026-05-10 |
```

### 字段说明

| 字段 | 来源 | 说明 |
|------|------|------|
| `slug` | 文件名（去 `.md`） | 唯一标识 |
| `title` | frontmatter `title` | 显示标题 |
| `tags` | frontmatter `tags` | 逗号分隔，用于快速过滤 |
| `status` | frontmatter `status` | canonical / active / draft / deprecated |
| `expires` | frontmatter `expires` | 过期日期或 `never` |
| `TL;DR` | 正文 `## TL;DR` 段落 | 截取前 80 字符（遇句号截断），超长省略号 |
| `created` | frontmatter `created` | 录入日期 |

### 已废弃条目的处理

**不删除行**，在 `status` 列标记 `deprecated` 并追加 `~~删除线~~` 到 title：

```
| old-config | ~~旧配置方案~~ | config | deprecated | 2025-12-01 | 已被新方案替代 | 2025-09-15 |
```

原因：
- 保留历史记录，防止 slug 被复用后混淆
- `ask links` / `ask refs` 追溯时仍可定位到废弃条目
- 下次 health 全量重建时会清理已废弃超过 180 天的行

---

## 写入时机与规则

### `/knowledge-wiki in` — 追加条目

在 Step 9（写入 wiki 文档）之后、Step 10（log 追加）之前执行：

```
1. 根据 type 定位目标 idx 文件（见上方映射表）
2. 按上述表格格式生成一行条目
3. 追加到对应 idx 文件的表格末尾（在最后一行 `` 之后）
4. 更新 _meta.yaml 中该 idx 的 entries +1 和 last_updated
```

**注意**：
- 若 idx 文件不存在（首次使用该 type），先创建文件头（含表头）
- 若 `.index/` 目录不存在，先创建目录（init 时应已创建）
- 不检查重复（同一 slug 可能因 --update 而出现两次，由 health rebuild 去重）

### `/knowledge-wiki in --update` — 标记旧条目

```
1. 在对应 idx 文件中找到 slug 匹配的行
2. 整行替换为新内容（title/tags/status/expires/TL;DR 均刷新）
3. 不新增行（保持条目数不变）
4. 更新 _meta.yaml last_updated
```

找不到匹配行时不报错（可能是 idx 还未同步），由下次 health rebuild 补齐。

### `/knowledge-wiki health deprecate <slug>` — 标记废弃

```
1. 遍历所有 idx 文件找到该 slug 行
2. 将 status 改为 deprecated，title 加删除线
3. 不删除行
```

### `/knowledge-wiki health audit <slug>` — 升级 active

```
1. 找到该 slug 行
2. 将 status 从 draft 改为 active
3. 刷新 expires 为续期后的新日期
```

---

## 读取规则（ask 使用）

### Layer -1：Index 快速定位（新增检索层）

在现有 Layer 0（rg 关键词匹配）之前插入 Index 层：

```
Layer -1：Index 预筛选
  1. 从用户问题中提取关键词（同 Layer 0 的关键词提取逻辑）
  2. 推断最可能的 1-2 个 idx 文件（基于关键词匹配 type 名称或 tags）
  3. 读取对应 idx 文件（仅 1-2 个，非全部 9 个）
  4. 在 idx 表格的 title / tags / TL;DR 列做子串匹配
  5. 命中 ≥1 行 → 将这些 slug 作为 Layer 0 rg 搜索的"优先范围"（加路径前缀限制）
  6. 命中 0 行 → 直接进入 Layer 0（退化为原有行为，无额外开销）
```

### idx 选择策略（从问题推断用哪个 idx）

| 问题特征 | 优先读取的 idx | 备选 idx |
|---------|--------------|---------|
| 含"是什么"/"定义"/"术语" | `glossary.idx.md` | — |
| 含"架构"/"系统设计"/"拓扑" | `design.idx.md` | — |
| 含"流程"/"步骤"/"规则"/"怎么做的" | `flows.idx.md` | `case.idx.md` |
| 含"接口"/"API"/"字段"/"请求" | `apis.idx.md` | — |
| 含"表"/"模型"/"存储"/"数据库" | `db.idx.md` | — |
| 含"运维"/"告警"/"超时"/"配置"/"部署" | `ops.idx.md` | — |
| 含"需求"/"PRD"/"验收" | `requirements.idx.md` | — |
| 含"故障"/"复盘"/"踩坑"/"反例" | `case.idx.md` | `flows.idx.md` |
| 含"综合"/"对比分析"/"关联发现"/"回流" | `synthesis.idx.md` | — |
| 无法推断 | **跳过 Index 层**，直接进 Layer 0 | — |

**关键优化**：无法推断时跳过 Index 层，保证不会比原来更慢。

### Index 命中后的 Layer 0 增强

当 Index 返回候选 slug 列表时，Layer 0 的 rg 搜索增加路径约束：

```bash
# 原来：全局搜索
rg "<关键词>" .knowledge/ -l --type md

# Index 命中后：限定路径搜索（大幅减少噪声）
rg "<关键词>" .knowledge/{ops,flows}/ -l --type md  # 假设 Index 推断是 ops 或 flows
```

---

## health 子命令：index-rebuild

### 用途

全量重建所有 idx 文件，保证与实际 `.knowledge/` 目录一致。

### 触发条件

- 手动执行：`/knowledge-wiki health index-rebuild`
- 自动提示：_meta.yaml 中 `last_full_rebuild` 距今 > `rebuild_threshold_days`（默认 30 天）时，`health` 综合报告末尾追加提示
- 强制触发：任何 idx 文件丢失或损坏时

### 重建流程

```
1. 扫描 .knowledge/ 下所有 9 个业务目录中的 .md 文件
2. 对每个文件提取 frontmatter（title/type/tags/status/expires/created）和正文 TL;DR
3. 按 type 分组，分别写入对应的 idx 文件（完全覆写，不是追加）
4. 清理废弃超过 180 天的条目（从 idx 中彻底移除，不再保留行）
5. 重新生成 _meta.yaml
6. 输出摘要：
   ✓ 索引重建完成
   总条目：N（+X 新增 / -Y 移除 / Z 更新）
   各 idx 详情：...
```

### 一致性校验（rebuild 附带）

重建过程中同时检测以下异常并报告：

| 异常类型 | 检测逻辑 | 报告级别 |
|---------|---------|---------|
| 孤儿文档 | .md 文件存在但无对应 idx 条目 | WARNING（rebuild 会自动补上） |
| 孤儿索引 | idx 有条目但 .md 文件不存在 | ERROR（悬空引用，需人工确认） |
| 状态不一致 | idx status ≠ frontmatter status | WARNING（以 frontmatter 为准修正） |
| 类型错位 | 文件所在目录 ≠ type 应在的目录 | ERROR（数据异常） |

---

## init 集成

`/knowledge-wiki init` Step 1 创建目录结构时，同时创建：

```bash
mkdir -p .knowledge/.index
```

并写入初始 `_meta.yaml`（version: 1, last_full_rebuild: 当日日期, 所有 indexes entries: 0）。

创建 9 个空的 idx 文件（仅含表头 + "暂无条目"注释），方便后续 append。