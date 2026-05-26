# 查询（ask）详细规则

> 由 `/knowledge-wiki ask` 使用。SKILL.md 仅保留入口与索引，本文件是唯一权威源。

---

## 检索策略（三层：Index 预筛选 → rg 关键词 → 语义筛选）

### Layer -1 [NEW]：Index 分段预筛选（调用上限 1 轮，可选跳过）

在 Layer 0 之前插入的轻量级预筛选层。**核心目标：缩小 rg 搜索范围，减少噪声候选。** 详见 `references/index-rules.md`「读取规则」。

```
1. 从用户问题中提取关键词特征（同 Layer 0 的关键词提取逻辑）
2. 根据问题特征推断最可能的 1-2 个 idx 文件（见下方「idx 选择策略」表）
3. 读取对应 idx 文件的 title / tags / TL;DR 列（仅 1-2 个文件，非全部 9 个）
4. 在 idx 表格中做子串匹配（title + tags + TL;DR 三列）
5. 命中 ≥1 行 → 提取这些 slug 作为 Layer 0 的"优先范围"
6. 命中 0 行或无法推断 idx → **跳过本层**，直接进入 Layer 0（退化为原有行为）
```

**idx 选择策略**（从问题推断用哪个 idx）：

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

**Index 命中后的效果**：Layer 0 的 rg 搜索增加路径约束，限定在 idx 命中的 type 对应目录内搜索。

### Layer 0：rg 关键词匹配（调用上限 3 轮）

```bash
rg "<关键词>" .knowledge/ -l --type md
```

**关键词提取**：去掉停用词（的/是/了/多少/什么/吗/呢/怎么），提取名词和动词原形，保留专业术语原样。

**重试层级**（任一轮命中 ≥1 文件即进入 Layer 1）：

| 轮次 | 策略 | 示例（查询："配送超时怎么配置"） |
|------|------|---------|
| Round 1 | 原始关键词 2-4 个并行搜索 | rg "配送超时" / rg "配送" / rg "超时" |
| Round 2 | 拆词为词根 + 同义词扩展 | + rg "timeout" / rg "delivery" |
| Round 3 | 拼音 + 只查 frontmatter title/tags | rg -i "^title:.*(配送\|delivery)" |

3 轮后仍 0 命中 → 进入 Layer 0.5 兜底；Layer 0.5 仍 0 命中 → 输出「知识库无记录」模板，不猜测。

> **注意**：若 Layer -1 已返回候选 slug 列表，Layer 0 的 rg 搜索应限定在这些 slug 所在的目录范围内（通过路径前缀约束），大幅减少噪声。

### Layer 0.5：frontmatter 模糊兜底（最后一搏，1 轮）

仅在 Layer 0 三轮全部 0 命中时执行，目标是抓回「关键词偏但主题相近」的文档：

```bash
# 拆查询为单字符级 fuzzy 模式，只扫 frontmatter 的 title 和 tags
rg -i "^(title|tags):" .knowledge/ --type md
```

匹配规则：
1. 提取查询中所有 ≥2 字的连续中文片段 + 所有英文单词
2. 对每个片段做大小写不敏感的子串匹配（不要求词边界）
3. 命中 ≥1 个片段的文件即视为候选，进入 Layer 1
4. 候选 > 5 时按 frontmatter `status` 优先级（canonical > active > draft）取 Top 5
5. 仍 0 命中 → 走「无记录」分支

**铁律**：本层不放宽「不用模型训练知识填补」原则，只是把搜索范围扩到 frontmatter；正文未命中绝不脑补。

### Layer 1：Claude 语义筛选

读取命中文件的 frontmatter + TL;DR，选出最相关 1-3 篇，读全文生成回答。若语义筛选后仍无明确中的 → 输出「知识库无记录」模板。

**status 优先级**：`canonical > active > draft > deprecated`（deprecated 禁止引用）

---

## 标准回答格式

```
回答：打印服务超时阈值为 30s，超时后 fallback 到本地缓存，不直接报错。

来源：.knowledge/ops/print-timeout.md（第 12 行）
录入：@hanqiang，2026-05-12
状态：FRESH（距过期还有 82 天）

被引用：[[order-flow-design]]（1 处）
引用了：[[fallback-strategy]]（1 处）
```

### 时效状态

| 状态 | 条件 | 计算示例 |
|------|------|---------|
| FRESH | 距 expires > 30 天，或 never | created=2026-05-12, expires=2026-08-12, 今日=2026-05-13 → 90 天 → FRESH |
| WARNING | 距 expires ≤ 30 天且未过期 | 今日=2026-07-20, expires=2026-08-12 → 23 天 → WARNING |
| EXPIRED | 已超过 expires | 今日=2026-09-01, expires=2026-08-12 → 已过 20 天 → EXPIRED |

EXPIRED 文档引用时，末尾追加：

```
⚠️ 此条知识已过期，建议：/knowledge-wiki health audit <slug>
```

---

## 知识库无记录时

```
知识库中无相关记录。
搜索范围：.knowledge/**/*.md（共 47 篇）

建议：
  /knowledge-wiki in <描述>           手工录入
  /knowledge-wiki health scan         检查外部源是否有相关文档
```

**核心约束：不用模型训练知识填补，不说"通常情况下"。**

---

## links / refs（追溯）

```bash
# 反向追溯：谁引用了这篇
/knowledge-wiki ask links <slug>
→ rg "\[\[<slug>\]\]" .knowledge/ -l --type md

# 正向追溯：这篇引用了谁
/knowledge-wiki ask refs <slug>
→ rg "\[\[.*\]\]" .knowledge/<对应文件>.md
```

输出：文件路径 + 行号，说明"更新此文档时，以上关联文档可能需要同步检查"。


---

## 操作日志记录 [NEW]

每次 `ask` 执行完成后（无论是否命中），**必须**追加一条记录到 `.logs/personal/{mis-id}.md`。

### 记录格式

详见 `references/log-rules.md`「日志条目格式」的 **ask 类型**：

```markdown
## [2026-05-26T14:40:15+08:00] @hanqiang | ask | a1b2c3d4
  detail: {"hit": "ops/print-timeout.md", "status": "FRESH", "docs_read": 1, "layer": "L0-R1"}
```

**关键：ask 的 title 字段使用 `sha1(原始问题)[:8]` 而非问题原文，保护用户隐私。**

### 命中与未命中均记录

| 场景 | detail 内容 |
|------|------------|
| 命中（有答案） | `{"hit": "<slug>", "status": "FRESH\|WARNING\|EXPIRED", "docs_read": N, "layer": "L-1/L0/L0.5/L1"}` |
| 未命中 | `{"hit": "none", "docs_scanned": N, "reason": "L0 全失败 + L0.5 兜底无结果"}` |

---

## Ask 回流提示 [NEW]（可选，条件触发）

当满足以下**所有条件**时，在标准回答末尾追加回流提示：

```
💡 此回答综合了 ≥2 篇文档的知识，是否录入为新的知识条目？
  /knowledge-wiki in --from-answer "{用户问题的简短描述}"
```

### 触发条件（全部满足才显示）

1. Layer 1 语义筛选时读取了 **≥2 篇文档**并做了综合
2. 回答长度 **>300 词**（短回答通常不值得独立成篇）
3. 回答内容包含**跨文档的对比、分析或关联发现**（非简单引用单篇）

### 不触发的情况

- 命中了 synthesis 类型文档 → synthesis 本身就是派生知识，禁止二次回流
- 用户问题为简单事实查询（如"XX 的超时配置是多少"）
- 回答来源为单一文档

### --from-answer 处理

`in --from-answer` 将当前 AI 对话中的回答内容作为输入源，走正常 `in` 结构化流程：
- type 直接设为 `synthesis`（无需走 type 推断，因为回流内容本身就是综合分析）
- sources 标注为：`"由 /knowledge-wiki ask '{question}' 综合生成，{YYYY-MM-DD}"`
- `derived_from`：自动填充为当前 ask 回答中引用的所有文档 slug
- `derived_question`：原始问题原文
- 质量门禁：来源文档 ≥2 篇且均非 deprecated（见 `_registry.yaml` synthesis 的 quality_gate）
- 模板：按 `references/templates/synthesis.md` 骨架生成正文