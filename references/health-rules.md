# 维护（health）详细规则

> 由 `/knowledge-wiki health` 使用。SKILL.md 仅保留入口与索引，本文件是唯一权威源。

---

## 综合报告（health）

```
📊 知识库健康报告（2026-05-12）

文档总数：47 篇（active: 32  draft: 10  deprecated: 5）
  ├─ glossary: 12  design: 8  requirements: 3  flows: 15
  ├─ case: 5  apis: 2  db: 1  ops: 0  synthesis: 1
  └─ 近 30 天活跃：ingest 15 | ask 28 | health 5

[腐烂检测]  EXPIRED 3 篇 | WARNING 5 篇
[覆盖率]    未覆盖模块：goods / queue / redis3
[外部源]    3 个源，上次扫描 22 天前
[一致性]    ⚠️ 2 条 WARNING（运行 health lint 查看详情）
[反向引用]  📋 5 条 pending（运行 health backlink-consume 消费）
[索引状态]  ✅ 正常（上次重建 5 天前；超过 30 天提示重建）
[操作日志]  digest 已重建（最近 50 条），ask 未命中高频：2 个主题

/knowledge-wiki health rot       查看过期详情
/knowledge-wiki health scan      检查外部源
/knowledge-wiki health coverage  查看覆盖率（含问答缺口）
/knowledge-wiki health lint      一致性检查
/knowledge-wiki health backlink-consume  消费反向引用
/knowledge-wiki health index-rebuild     重建索引
```

### 综合报告生成流程

`health`（无子命令）执行时按以下顺序：

```
1. [digest 重建] 重新生成 .logs/digest.md（详见下方 §digest 重建）
2. [统计] 扫描 9 个业务目录，统计各 type 文档数 + status 分布
3. [rot 快速摘要] 检查 EXPIRED/WARNING 数量（不做批量决策询问）
4. [coverage 快速摘要] 列出未覆盖模块名（不做详细报告）
5. [外部源] 读取 .sources.yaml，计算 last_synced 距今天数
6. [lint 快速摘要] 仅检查 L7（pending 积压）+ L9（过期数）+ 索引年龄
7. [反向引用] 统计 .pending-backlinks.yaml 中 consumed==false 的条目数
8. [索引状态] 读取 _meta.yaml.last_full_rebuild，判断是否超 30 天
9. [日志摘要] 从 digest.md 提取：近 30 天操作统计 + ask 未命中高频数
10. [输出] 按上方模板格式输出综合报告
11. [操作日志] 追加一条 health 记录到 personal log
```

### 输出模式选项

```bash
/knowledge-wiki health              # 默认：人类可读格式（emoji + 文本）
/knowledge-wiki health --json       # JSON 格式供外部工具消费
/knowledge-wiki health --verbose    # 含 ASCII 图表的详细模式
```

#### --json 输出格式

```json
{
  "generated_at": "2026-05-26T15:00:00+08:00",
  "summary": {
    "total_docs": 47,
    "by_status": {"active": 32, "draft": 10, "deprecated": 5},
    "by_type": {"glossary": 12, "design": 8, "requirements": 3, "flows": 15, "case": 5, "apis": 2, "db": 1, "ops": 0, "synthesis": 1}
  },
  "rot": {"expired": 3, "warning": 5},
  "coverage": {"uncovered_modules": ["goods", "queue", "redis3"]},
  "sources": {"total": 3, "oldest_sync_days": 22},
  "lint_quick": {"warnings": 2, "errors": 0},
  "backlinks": {"pending": 5},
  "index": {"last_rebuild_days": 5, "needs_rebuild": false},
  "digest": {"recent_count": 50, "ask_miss_topics": 2}
}
```

> `--json` 模式下不输出 emoji/文本/子命令提示，纯 JSON 输出到 stdout。适用于：
> - CI 集成（定期 cron 检查健康度）
> - 外部看板工具拉取数据
> - 脚本自动判断是否需要维护

#### --verbose 输出（含 ASCII 图表）

在默认输出基础上，追加以下可视化段落：

```
📊 知识库健康报告（2026-05-12）
...（标准报告内容）...

─── 文档分布（按 type）──────────────────────────────
glossary     ████████████ 12
flows        ███████████████ 15
design       ████████ 8
case         █████ 5
requirements ███ 3
apis         ██ 2
db           █ 1
synthesis    █ 1
ops          ░ 0

─── 状态分布 ─────────────────────────────────────────
active       ████████████████████████████████ 32 (68%)
draft        ██████████ 10 (21%)
deprecated   █████ 5 (11%)

─── 近 30 天操作趋势 ─────────────────────────────────
ingest ■■■■■■■■■■■■■■■ 15
ask    ■■■■■■■■■■■■■■■■■■■■■■■■■■■■ 28
health ■■■■■ 5
```

> `--verbose` 适合人工快速定位知识库短板（哪些 type 文档太少、哪些模块未覆盖）。

---

## rot（腐烂扫描）

扫描所有文档 `expires` 字段，FRESH 静默，仅输出 EXPIRED / WARNING：

| 状态 | 条件 | 建议动作 |
|------|------|---------|
| EXPIRED | 超过 expires | `health audit` 或 `health deprecate` |
| WARNING | 距 expires ≤ 30 天 | 尽快确认 |

**无过期文档时：完全静默。**

### 批量决策入口（输出 EXPIRED 列表后询问）

```
发现 {N} 篇过期文档。选择处理方式：
[1] 逐篇 audit（交互式进入 audit 流程，逐个确认 有效/更新/废弃）
[2] 批量延期 90 天（仅推迟 expires，status 不变，sources 追加「批量延期 @who YYYY-MM-DD」）
[3] 批量标记 deprecated（由用户二次确认 slug 列表后，逐篇检查引用后变更）
[4] 仅列表不处理
```

- 选 [2] 需输入原因说明（"代码未变" / "推迟重评"等），写入 sources
- 选 [3] 走 deprecate 标准流程（必须逐篇检查引用、不可跳过）

### rot 附带：related 悬空链接清理

`rot` 执行时**顺带**扫描所有文档的 `related` 字段，检测以下两类问题：

| 异常类型 | 检测逻辑 | 自动动作 |
|---------|---------|---------|
| **deprecated 引用** | related 中的 `[[slug]]` 对应文档 status=deprecated | 自动移除该 related 条目 + 追加注释 `# removed: [[slug]] (deprecated since YYYY-MM-DD)` |
| **悬空链接** | related 中的 `[[slug]]` 对应的 .md 文件不存在 | 标记 WARNING，不自动移除（可能是 slug 重命名未同步，需人工确认） |

```
[related 清理]（rot 附带）
  🗑️ flows/order-process.md: 移除 [[old-config]]（deprecated 2025-12-01）
  🗑️ apis/print-api.md: 移除 [[legacy-timeout]]（deprecated 2025-10-15）
  ⚠️ ops/fallback.md: 悬空引用 [[non-exist-slug]]（文件不存在）

已自动清理 2 条 deprecated 引用；1 条悬空链接需人工确认
```

**与 lint L2/L3 的关系**：rot 做轻量级 related 清理（自动移除 deprecated）；lint L2/L3 做全量检测（含报告但默认不修改，需 `--fix`）。两者互补不冲突。

---

## scan（外部源扫描）

> **工具路由**：scan 中每个外部源 URL 严格遵循「URL 处理」路由——按域名路由浏览器自动化。详见 `url-handling.md`。

完整流程见 `url-handling.md` 末尾「scan 中的路由」节。

---

## coverage（覆盖率）

### 项目根检测

按以下优先级定位根目录：
1. `git rev-parse --show-toplevel` （优先以 git 根为准）
2. 向上查找包含 `.knowledge/` 的最近祖先目录
3. 该 path 不是当前 PWD → 提示："检测到项目根为 {root}，在该路径下扫描。"并以其为扫描起点
4. 未找到（项目外）→ 中止："未在当前路径及祖先目录找到 .knowledge/，请在项目根运行。"

### 扫描流程

```
1. 以项目根为起点扫描顶层目录（排除 node_modules/vendor/.git/.knowledge/dist/build/.next/__pycache__），提取目录名作为模块列表
2. 读取 .knowledge/ 下所有 .md 的 tags + title，提取已覆盖模块
3. 比对：目录名 ∉ 已覆盖模块 → 标记为未覆盖
4. 输出：未覆盖模块列表 + 建议的 /knowledge-wiki in 命令
```

仅建议，不阻断任何操作。

---

## audit `<slug>`（确认有效）

```
展示：title / TL;DR / 当前 expires
询问：[1] 确认有效  [2] 需要更新  [3] 已废弃

选 [1]：
  status → active
  expires → 按 type 分支处理（见下方「expires 续期分支」）
  sources 追加："人工确认 @who YYYY-MM-DD"

选 [2]：跳转 /knowledge-wiki in --update <slug>
选 [3]：跳转 /knowledge-wiki health deprecate <slug>
```

### expires 续期分支

| 文档当前 type / expires | audit 选 [1] 后的处理 |
|------------------------|----------------------|
| `type: glossary` 且 `expires: never` | **保持 never**（术语长期有效，不续期为日期）；询问可选 `[1a] 维持 never  [1b] 改为 +365 天` |
| `type: adr` 且 `expires: never` | 同上保持 never（决策快照，不过期） |
| 其他 type 或 `expires` 是日期 | `expires → 今日 + 该 type 的 expires_days`（从 `_registry.yaml` 读取，不再写死 90 天） |

> 续期天数从 `references/templates/_registry.yaml` 的 `expires_days` 字段读取，避免与录入时的过期日期不一致。

---

## deprecate `<slug>`（标记废弃）

```
1. rg 查找所有引用该 slug 的文档
2. 列出引用处，确认后：
   - status → deprecated
   - 引用处追加：<!-- deprecated: [[<slug>]] 已废弃，请更新引用 -->
```

废弃前必须处理引用，防止悬空链接。

---

## lint [NEW]（一致性检查）

> **完整规则见 `references/lint-rules.md`**。本节为入口摘要和与 health 其他子命令的联动说明。

### 用法

```bash
/knowledge-wiki health lint           # 只报告，不修改任何文件
/knowledge-wiki health lint --fix     # 安全自动修复（仅 L3 + L8）
```

### 检查项速查

| # | 检查项 | 级别 | --fix 可修复 |
|---|--------|------|------------|
| L1 | 数值/状态矛盾 | ERROR/WARNING | ❌ |
| L2 | 悬空引用（文件不存在） | ERROR | ❌ |
| L3 | 废弃引用未标记 | WARNING | ✅ 自动加 ~~~~ |
| L4 | 孤儿文档（无 idx 条目） | WARNING | ❌（用 index-rebuild） |
| L5 | 孤儿索引（无对应文件） | ERROR | ❌ |
| L6 | related 膨胀（>12 条） | WARNING | ❌ |
| L7 | pending 队列积压（>7 天） | WARNING | ❌（用 backlink-consume） |
| L8 | idx status 不一致 | WARNING | ✅ 自动同步 |
| L9 | 过期未处理 | EXPIRED 类 | ❌（用 rot/audit/deprecate） |

### 在综合报告中的角色

`health`（无子命令）执行时：
1. 先运行 **快速摘要模式**：检查 L7（pending 积压）+ L9（过期数）+ 索引年龄 → 填入报告的「一致性」「反向引用」「索引状态」三行
2. 不做完整的 L1-L9 检测（耗时较长），仅在报告中提示 `health lint`

---

## backlink-consume [NEW]（反向引用队列消费）

> **完整规则见 `references/backlink-rules.md`**。本节为入口摘要。

### 用法

```bash
/knowledge-wiki health backlink-consume
```

### 行为

1. 读取 `.pending-backlinks.yaml`
2. 过滤 `consumed == false` 的记录
3. 对每条记录：将 `[[from]]` 追加到 target 文档的 related 字段（上限控制 15 条）
4. 标记已消费，更新 yaml
5. 自动 git commit

### 输出示例

```
🔗 反向引用消费完成

已处理：3 条
  ✅ flows/fallback-strategy.md ← 追加 [[print-timeout]]
  ✅ glossary/timeout.md ← 追加 [[print-timeout]]
  ⏭️ ops/timeout-v1.md ← 已存在，跳过

队列剩余：0 条
```

### 安全保障

- 消费前检查工作区是否干净（`git diff --quiet`）
- 消费前 `git pull --rebase` 确保最新
- 消费后自动 commit

---

## index-rebuild [NEW]（全量重建分段索引）

> **完整规则见 `references/index-rules.md`**。本节为入口摘要。

### 用法

```bash
/knowledge-wiki health index-rebuild
```

### 行为

1. 扫描 `.knowledge/` 下所有 9 个业务目录中的 .md 文件
2. 提取 frontmatter + TL;DR
3. 按 type 分组，覆写对应 idx 文件
4. 清理废弃 >180 天的条目
5. 更新 `_meta.yaml`
6. 附带一致性校验（L4 孤儿文档 + L5 孤儿索引 + L8 status 不一致）

### 触发时机

- 手动执行
- `_meta.yaml.last_full_rebuild` 距今 > 30 天时，`health` 综合报告自动提示

---

## coverage 增强版 [NEW]（含问答缺口分析）

原有覆盖率逻辑不变（目录映射），新增基于 log 数据的问答缺口分析。

### 新增段落输出

```
[问答缺口]（近 30 天，基于操作日志）
  高频未答（去重后 ≥3 次）：
    1. "配送超时配置" — 5 次未命中 → 建议 in
    2. "队列消费失败处理" — 3 次未命中 → 建议 in
  已解决（后来录入了）：
    ✓ "打印服务架构" — 原 4 次未命中，已于 05-20 录入
```

### 数据来源与过滤

详见 `references/log-rules.md`「coverage 缺口分析」：

- 数据源：`.logs/personal/*.md` 中近 7 天的 ask 未命中记录
- 过滤：排除编码问题、排查请求、个人事务等噪声
- 匿名：聚合报告不显示 @who 信息
- 条件：至少积累 7 天数据才分析；同类去重后 ≥3 次才算缺口

---

## digest 重建 [NEW]

`health`（无子命令，即综合报告模式）执行时，在生成报告前**自动重建** `.logs/digest.md`：

```
执行时机：health 综合报告开头，在各检查项运行之前
执行逻辑：详见 references/log-rules.md「digest.md 团队聚合」节
  1. grep -h "^## \[" .logs/personal/*.md
  2. 按时间倒序排序
  3. 取最近 50 条 + 统计段落
  4. 覆写 .logs/digest.md
```

> 注意：仅 `health`（无子命令）触发 digest 重建；`health lint`/`health rot`/其他子命令不触发。

---

## distill [NEW]（认知蒸馏）

> 借鉴 knowledge-evolution 的自动进化思路，为 knowledge-wiki 提供结构化的知识去重、合并与低质量清理能力。与 `lint` 互补——lint 侧重语义矛盾与引用一致性，distill 侧重内容重复与信息密度。

### 用法

```bash
/knowledge-wiki health distill           # 预览模式（只报告不修改）
/knowledge-wiki health distill --execute # 执行蒸馏（需用户确认）
```

### 设计原则

1. **不自动修改**——默认预览模式，`--execute` 模式下每步操作前均需用户确认
2. **同 type 范围内检测**——仅在同一 type 目录内做相似度比较（跨 type 语义差异大，误报率高）
3. **保护 canonical 与 active**——status=canonical 的文档不参与合并（仅参与相似度报告）；status=active 的文档合并前必须明确提示风险
4. **与现有流程联动**——合并/废弃后自动触发 deprecate 标准流程 + idx 更新 + pending-backlinks 清理

### 蒸馏三步

#### Step 1：重复检测（Jaccard 相似度）

**相似度算法**：

```python
def extract_words(text: str) -> set:
    """提取中文 bigram + 英文词汇（≥2 字符），用于 Jaccard 计算。"""
    # 中文 bigram：相邻 2 字滑窗（提升区分度，无需 jieba）
    chinese_bigrams = [text[i:i+2] for i in range(len(text)-1)
                       if all('\u4e00' <= c <= '\u9fff' for c in text[i:i+2])]
    # 英文：连续字母数字（≥2 字符），统一小写
    english = re.findall(r"[a-zA-Z0-9]{2,}", text.lower())
    return set(chinese_bigrams + english)

def jaccard_similarity(text_a: str, text_b: str) -> float:
    words_a, words_b = extract_words(text_a), extract_words(text_b)
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)
```

**比较文本**：取每篇文档的 `title + TL;DR + tags（用空格连接）+ 正文前 500 字`（不含 frontmatter）作为比较输入。

**阈值与判定**：

| Jaccard 相似度 | 判定 | 动作 |
|---------------|------|------|
| > 0.80 | 高度重复 | 候选合并（预览 + 用户决策） |
| 0.60 ~ 0.80 | 疑似相关 | 仅报告，建议检查是否需要关联 related |
| < 0.60 | 无关 | 忽略 |

**性能控制**：
- 仅在同一 type 目录内做两两比较
- 单目录文档数 > 100 时，按 created 降序取最近 100 篇参与比较
- 总比较对数上限 5000（超出时随机采样）

#### Step 2：低质量检测

扫描所有文档，以下条件**全部满足**时标记为低质量候选：

| 条件 | 说明 |
|------|------|
| 正文（不含 frontmatter）< 50 字 | 信息密度过低 |
| status = draft | 仅清理草稿，不动已确认文档 |
| created 距今 > 30 天 | 长期未补充的草稿 |
| 非 glossary stub | 排除 Step 2.7 自动创建的占位符（sources 含"自动抽取"字样的 glossary） |

#### Step 3：孤立知识检测

扫描所有文档，以下条件**全部满足**时标记为孤立候选：

| 条件 | 说明 |
|------|------|
| related 字段为空数组 `[]` | 无任何关联 |
| 无任何文档在其 related 中引用该 slug | 完全孤立 |
| status = draft | 仅提示草稿 |
| created 距今 > 14 天 | 给予新文档 2 周建立关联的缓冲期 |

### 预览输出模板

```
🧪 认知蒸馏预览

[重复检测]（同 type 目录内 Jaccard > 0.80）
  ① ops/print-timeout.md ↔ ops/printer-timeout-config.md
     相似度：0.87 | 建议：合并（title/TL;DR 高度重叠）
  ② flows/order-cancel.md ↔ flows/cancel-order-process.md
     相似度：0.82 | 建议：合并（仅表述差异）

[疑似相关]（Jaccard 0.60~0.80，仅提示）
  ③ design/print-arch.md ↔ design/printer-service-design.md
     相似度：0.65 | 建议：检查 related 是否已关联

[低质量]（正文 <50 字 + draft + 超 30 天）
  ④ glossary/channel-fee.md — 正文 28 字，创建于 2026-04-01
  ⑤ ops/temp-fix.md — 正文 15 字，创建于 2026-03-20

[孤立知识]（无 related + 无被引用 + draft + 超 14 天）
  ⑥ case/timeout-issue.md — 创建于 2026-04-15，无任何关联

统计：重复对 2 | 疑似相关 1 | 低质量 2 | 孤立 1
执行蒸馏：/knowledge-wiki health distill --execute
```

### --execute 执行流程

执行时逐组展示并等待用户决策：

**重复对处理**（逐对询问）：

```
重复对 ①：ops/print-timeout.md ↔ ops/printer-timeout-config.md
  A：print-timeout — 创建 2026-05-01，正文 320 字，active
  B：printer-timeout-config — 创建 2026-04-15，正文 180 字，draft

选择：
[1] 合并到 A（保留 A，B 标记 deprecated，B 的独有内容追加到 A）
[2] 合并到 B（保留 B，A 标记 deprecated，A 的独有内容追加到 B）
[3] 均保留，仅互加 related（判定为不同视角）
[4] 跳过
```

**低质量处理**（批量询问）：

```
低质量候选（2 篇）：
  ④ glossary/channel-fee.md — 28 字
  ⑤ ops/temp-fix.md — 15 字

选择：
[1] 批量标记 deprecated（走 deprecate 标准流程）
[2] 逐个处理（对每篇选择 deprecate / 保留并提醒补充 / 跳过）
[3] 全部跳过
```

**孤立知识处理**（批量询问）：

```
孤立知识候选（1 篇）：
  ⑥ case/timeout-issue.md

选择：
[1] 推荐关联（AI 扫描相关文档，建议 related 列表并追加）
[2] 标记 deprecated
[3] 跳过
```

### 执行后联动

蒸馏 `--execute` 完成后自动执行：

| 动作 | 触发条件 | 执行内容 |
|------|---------|---------|
| deprecate 标准流程 | 文档被标记废弃时 | rg 查引用 → 标记 deprecated → 引用处追加注释 |
| idx 更新 | 文档 status 变更时 | 更新对应 .index/{type}.idx.md 中的 status 列 |
| pending-backlinks 清理 | 文档被 deprecated 时 | 清理 .pending-backlinks.yaml 中涉及该 slug 的条目 |
| _meta.yaml 更新 | 任何蒸馏执行后 | 写入 `last_distill: YYYY-MM-DDTHH:MM` |
| 操作日志 | 始终 | 追加 health/distill 记录到 personal log |

### 蒸馏完成输出

```
🧪 认知蒸馏完成

合并：2 对（4 篇 → 2 篇）
废弃：1 篇低质量 + 2 篇重复源
新增关联：1 篇孤立文档追加 related
当前总量：45 篇（active: 32  draft: 8  deprecated: 5）

下次蒸馏建议：知识库文档数增长 20% 或距上次蒸馏 >30 天时
```

### 与 lint 的关系

| 检测项 | lint | distill | 说明 |
|--------|------|---------|------|
| 语义矛盾 | L1 ✅ | ❌ | lint 专属 |
| 悬空引用 | L2 ✅ | ❌ | lint 专属 |
| 内容重复 | ❌ | ✅ | distill 专属 |
| 低质量 | ❌ | ✅ | distill 专属 |
| 孤立知识 | L4（孤儿 idx） ✅ | ✅（无 related） | 视角不同：lint 查索引孤儿，distill 查关联孤岛 |
| related 膨胀 | L6 ✅ | ❌ | lint 专属 |

### 在综合报告中的角色

`health`（无子命令）执行时：在 Step 6（lint 快速摘要）后、Step 7（反向引用）前，新增 **Step 6.5 进化建议**：

- 快速扫描：仅取每个 type 目录前 20 篇文档做 Jaccard 抽样 + 低质量计数 + 孤立计数
- 填入报告的「进化建议」行
- 不做完整蒸馏（耗时较长），仅在报告中提示 `health distill`

---

## evolve（进化建议）[NEW]

> 嵌入综合报告的主动进化指标，帮助用户识别知识库可优化的方向。不作为独立子命令，而是综合报告的一个段落。

### 综合报告新增输出段落

在 `[一致性]` 和 `[反向引用]` 之间插入：

```
[进化建议]
  🔄 疑似重复：{N} 对文档高度相似（运行 health distill 查看）
  📉 低活跃：{M} 篇 draft 超 30 天未审核
  🔗 孤立知识：{K} 篇无任何关联
  📊 覆盖不均：{type_max}/ {count_max} 篇 vs {type_min}/ {count_min} 篇
```

### 各指标计算

| 指标 | 计算方式 | 显示条件 |
|------|---------|---------|
| 疑似重复 | 每个 type 目录取前 20 篇做 Jaccard 抽样，计 > 0.80 的对数 | 对数 > 0 |
| 低活跃 | 统计 status=draft 且 created 距今 >30 天的文档数 | 数量 > 0 |
| 孤立知识 | 统计 related=[] 且无被引用 且 created 距今 >14 天 的文档数 | 数量 > 0 |
| 覆盖不均 | 比较各 type 文档数，展示最多 vs 最少的 type | 最多/最少比值 > 5 |

全部指标为 0 时，该段落整体不输出（静默放行原则）。

---

## 操作日志记录 [NEW]

每次 `health` 及其子命令执行完成后，**必须**追加一条记录到 `.logs/personal/{mis-id}.md`。

详见 `references/log-rules.md`「日志条目格式」的 **health 类型**。