# 一致性检查规则（lint / 矛盾检测）

> 集中式知识库健康检查，涵盖矛盾检测、引用完整性、索引一致性等。
> 作为 `/knowledge-wiki health lint` 子命令的权威规则源。
> **不在 in/ask 流程中执行**（避免阻断用户主流程和误报干扰）。

---

## 设计原则

1. **集中式执行**：只在 `health lint` 时运行，不嵌入 in/ask
2. **高置信优先**：只报告高概率问题，宁可漏报不误报
3. **只读分析 + 报告**：不自动修改任何 wiki 文件（除 `--fix` 模式的安全操作）
4. **分级输出**：ERROR / WARNING / INFO 三级，用户按级别决定处理优先级

---

## 检查项目总览

| # | 检查项 | 级别 | 检测逻辑 | 修复方式 |
|---|--------|------|---------|---------|
| L1 | 数值/状态矛盾 | ERROR/WARNING | 同实体同属性值冲突 | 人工确认 |
| L2 | 悬空引用（文件不存在） | ERROR | related 中 slug 无对应 .md 文件 | 人工确认 |
| L3 | 废弃引用未标记 | WARNING | related 引用了 deprecated 文档但未标记 | `--fix` 自动标记 |
| L4 | 孤儿文档（无 idx 条目） | WARNING | .md 文件存在但 idx 中无记录 | health index-rebuild 修复 |
| L5 | 孤儿索引（无对应文件） | ERROR | idx 有条目但 .md 不存在 | 人工确认 |
| L6 | related 膨胀 | WARNING | 单文档 related > 12 条 | 建议审查 |
| L7 | pending 队列积压 | WARNING | backlink pending > 7 天未消费 | 提示 backlink-consume |
| L8 | status 不一致 | WARNING | frontmatter status ≠ idx status | 以 frontmatter 为准 |
| L9 | 过期未处理 | EXPIRED 类 | expires 已过但 status 非 deprecated | 提示 audit/deprecate |

---

## L1：数值/状态矛盾检测

### 核心策略：五维过滤，全满足才报告

为避免误报率过高，矛盾检测采用**严格的多维过滤**：

```python
def check_contradiction(new_doc, existing_doc):
    """返回 (is_contradiction, confidence, reason)"""

    checks = {
        'same_entity': False,       # 维度1: 是否同一实体
        'same_attribute': False,    # 维度2: 是否同一属性
        'value_type_match': False,  # 维度3: 值类型是否相同
        'context_overlap': False,   # 维度4: 所属上下文是否重叠
        'not_version_diff': False,  # 维度5: 排除版本演进差异
    }

    # --- 维度1：同一实体 ---
    # slug 相似度 > 0.8 或 title 完全/高度相似
    entity_similarity = compute_similarity(
        new_doc.slug + new_doc.title,
        existing_doc.slug + existing_doc.title
    )
    if entity_similarity >= 0.8:
        checks['same_entity'] = True

    # --- 维度2：同一属性 ---
    # 从 TL;DR 和正文中提取"属性-值"对，检查属性名是否相同
    new_attr_pairs = extract_attribute_values(new_doc.tldr + new_doc.body)
    existing_attr_pairs = extract_attribute_values(existing_doc.tldr + existing_doc.body)

    for attr_name, new_value in new_attr_pairs.items():
        for ex_attr_name, ex_value in existing_attr_pairs.items():
            if attr_name == ex_attr_name or similarity(attr_name, ex_attr_name) > 0.9:
                checks['same_attribute'] = True
                # 记录冲突的属性名和值
                conflicting_attr = attr_name
                conflicting_values = (new_value, ex_value)

    # --- 维度3：值类型匹配 ---
    if conflicting_values:
        new_type = classify_value_type(conflicting_values[0])  # time/count/enum/text/status
        ex_type = classify_value_type(conflicting_values[1])
        if new_type == ex_type and new_type in ('time', 'count', 'status', 'enum'):
            checks['value_type_match'] = True

    # --- 维度4：上下文重叠 ---
    # tags 重合度 > 0.5 或同属一个目录
    tag_overlap = len(set(new_doc.tags) & set(existing_doc.tags)) / max(len(new_doc.tags), len(existing_doc.tags))
    same_dir = (get_dir(new_doc.slug) == get_dir(existing_doc.slug))
    if tag_overlap > 0.5 or same_dir:
        checks['context_overlap'] = True

    # --- 维度5：排除版本演进 ---
    # 如果两篇文档的 title 含 v1/v2/version 或时间差异大 → 可能是版本迭代
    version_indicators = re.search(r'v[\d.]+|version|\d{4}年|\d{4}-\d{2}',
                                   new_doc.title + ' ' + existing_doc.title)
    created_gap = abs(days_between(new_doc.created, existing_doc.created))
    if not version_indicators or created_gap < 365:
        checks['not_version_diff'] = True

    # --- 判定（阈值与报告级别对齐 §5D 判定阈值表）---
    passed = sum(checks.values())
    if passed == 5:
        return ('contradiction', 'ERROR', f"{conflicting_attr}: {conflicting_values}")
    elif passed == 4:
        return ('possible_conflict', 'WARNING', f"{conflicting_attr}: {conflicting_values}（4D 通过）")
    elif passed == 3:
        return ('low_confidence', 'INFO', f"{conflicting_attr}: {conflicting_values}（仅 --verbose 显示）")
    else:
        return (None, None, None)  # ≤ 2D：静默跳过，不报告
```

### 属性值提取启发式

从 TL;DR 和正文首段中提取常见的"属性-值"模式：

```
模式示例：
  "超时阈值为 30s"          → {超时阈值: "30s"}
  "默认重试 3 次"            → {重试次数: "3"}
  "状态包含: 待支付/已支付/已取消"  → {状态枚举: ["待支付","已支付","已取消"]}
  "端口 8080"               → {端口: "8080"}
  "队列容量 10000"           → {队列容量: "10000"}
```

**注意**：此提取是近似算法，不需要完美。配合五维过滤后，即使提取有噪声也不会产生误报。

### 检测范围（性能控制）

L1 矛盾检测**不做全量笛卡尔积**，按以下策略缩小比较范围：

```
1. 只检查 status=active|canonical 的文档（draft/deprecated 不参与矛盾检测）
2. 按 tag 分组：同一 tag 下的文档才互相比较（tag 重合度 ≥ 1 个共同 tag）
3. 同一目录下的文档强制互比（同 type 是最可能矛盾的）
4. 单次 lint 最多检测 100 对文档组合（超出时按 tag 热度排序取 Top 100 对）
```

**复杂度**：假设 N 篇文档平均 3 个 tag，同 tag 分组后每组 5-15 篇，实际比较对数远小于 N²。

### 5D 判定阈值与报告级别

| 维度通过数 | 判定结果 | 报告级别 | 行动 |
|-----------|---------|---------|------|
| 5/5 全通过 | `contradiction`（高置信矛盾） | 🔴 ERROR | 人工确认必须处理 |
| 4/5 通过 | `possible_conflict`（疑似矛盾） | ⚠️ WARNING | 建议人工审查 |
| 3/5 通过 | `low_confidence` | ℹ️ INFO（仅 `--verbose` 时显示） | 可忽略 |
| ≤ 2/5 通过 | 不报告 | — | 静默跳过 |

> **与 TODO 中"4D+ 才报 ERROR"的对齐**：只有 5D 全满足才 ERROR；4D 为 WARNING；严格不误报。

### AI 执行 L1 检测的 prompt 模板

AI 在执行 `health lint` 的 L1 检查时，对每对候选文档按以下结构化 prompt 进行判定：

```markdown
## L1 矛盾检测任务

你是一个知识库一致性审查员。请比较以下两篇文档，判断是否存在属性值矛盾。

### 文档 A
- slug: {slug_a}
- title: {title_a}
- tags: {tags_a}
- TL;DR: {tldr_a}
- 正文首段（前 200 字）: {body_a_excerpt}

### 文档 B
- slug: {slug_b}
- title: {title_b}
- tags: {tags_b}
- TL;DR: {tldr_b}
- 正文首段（前 200 字）: {body_b_excerpt}

### 检查清单（逐项回答 yes/no + 证据）

1. **同一实体**：两篇是否在讨论同一个业务实体/模块/服务？
2. **同一属性**：是否提到了同一个可量化属性（如超时阈值、重试次数、端口号、状态枚举）？
3. **值类型匹配**：两个值是否属于同类型（时间/数量/状态/枚举）？
4. **上下文重叠**：tags 重合度是否 > 50% 或同属一个目录？
5. **排除版本迭代**：两篇 title 中是否无 v1/v2/version 等版本指示词，且创建时间差 < 365 天？

### 输出格式（严格 JSON）

```json
{
  "dimension_results": {
    "same_entity": {"pass": true/false, "evidence": "..."},
    "same_attribute": {"pass": true/false, "evidence": "...", "attr_name": "...", "value_a": "...", "value_b": "..."},
    "value_type_match": {"pass": true/false, "evidence": "..."},
    "context_overlap": {"pass": true/false, "evidence": "..."},
    "not_version_diff": {"pass": true/false, "evidence": "..."}
  },
  "passed_count": N,
  "verdict": "contradiction|possible_conflict|low_confidence|no_conflict",
  "summary": "一句话说明"
}
```
```

### 属性值提取指引（AI 执行参考）

AI 从 TL;DR 和正文首段中提取"属性-值"对时，遵循以下启发式模式匹配：

```
匹配模式（正则参考，AI 做语义级理解即可）：
  /{名词短语}\s*(为|是|=|：|:)\s*{数值|时间|枚举}/
  /{动词}\s*{数量词}\s*{单位}/

高优先级属性类型（最容易产生矛盾的）：
  - time: "30s" / "60 秒" / "5 分钟"       → 时间量
  - count: "3 次" / "重试 5 次" / "10000"   → 计数量
  - status/enum: "待支付/已支付/已取消"      → 状态枚举列表
  - port/config: "端口 8080" / "容量 10000"  → 配置值

低优先级（不检测矛盾）：
  - 描述性文字（如"该模块负责..."）
  - 不同粒度的概述（如"架构分三层" vs "详细的五层描述"）
```

### 输出格式

```
📋 一致性检查报告（2026-05-26T15:30:00）

[L1] 可能矛盾 (2):
  🔴 ERROR (5D 全通过):
    ops/timeout-v2.md(第15行) ↔ ops/timeout-v1.md(第8行)
      属性: 超时阈值 | 新值: 30s | 旧值: 60s
      上下文: 同属 print 模块 (tags 重合度: 0.75)
      建议: 人工确认——可能是版本演进？如确认矛盾请 update 其中一篇

  ⚠️ WARNING (4D 通过):
    db/order-table.md(第22行) ↔ db/order-archive.md(第40行)
      属性: order_status 枚举 | 新值: 含"已取消" | 旧值: 无"已取消"
      上下文: 同属 order 实体 (title 相似度: 0.85)
      建议: 确认哪个是最新定义，旧版可能需要 deprecate
```

---

## L2：悬空引用检测

### 检测逻辑

```bash
# 1. 收集所有 wiki 文件的 slug（去 .md 后缀）
all_slugs=$(find .knowledge/ -name "*.md" -not -path "*/.index/*" -not -path "*/.logs/*" -basename -a | sed 's/\.md$//')

# 2. 对每个 wiki 文件，检查 related 中的每个 slug
for file in $(find .knowledge/ -name "*.md" -not -path "*/.index/*" -not -path "*/.logs/*"); do
  related_slugs=$(grep -oP '\[\[\K[^\]]+' "$file")
  for slug in $related_slugs; do
    echo "$all_slugs" | grep -q "^${slug}$"
    if [ $? -ne 0 ]; then
      echo "ORPHAN: $file references [[$slug]] but file not found"
    fi
  done
done
```

### 输出格式

```
[L2] 悬空引用 (1):
  ❌ ERROR:
    flows/delivery-flow.md 第 18 行: [[old-module-doc]] → 文件不存在
    可能原因: 文件被删除但未更新引用 / slug 拼写错误
    建议: 运行 /knowledge-wiki ask refs old-module-doc 确认，然后手动修正或 deprecate
```

---

## L3：废弃引用未标记

### 检测逻辑

```bash
# related 中引用了 deprecated 文档，但引用处没有 ~~删除线~~ 标记
for file in $(find .knowledge/ -name "*.md" -not -path "*/.index/*" -not -path "*/.logs/*"); do
  related_slugs=$(grep -oP '\[\[\K[^\]]+' "$file")
  for slug in $related_slugs; do
    target_file=$(find .knowledge/ -name "${slug}.md" -not -path "*/.index/*")
    if [ -n "$target_file" ]; then
      target_status=$(grep '^status:' "$target_file" | head -1 | awk '{print $2}')
      if [ "$target_status" = "deprecated" ]; then
        # 检查是否有 ~~ 标记
        grep -q "\[\[${slug}\]\]" "$file"  # 没有 ~~ 包裹
        if [ $? -eq 0 ]; then
          echo "UNMARKED_DEPRECATED: $file references deprecated [[$slug]] without strikethrough"
        fi
      fi
    fi
  done
done
```

### --fix 行为

`--fix` 模式下自动将 `[[$slug]]` 替换为 `~~[[$slug]]~~ (deprecated)`：

```bash
# 安全操作：仅追加标记，不改正文
sed -i "s/\[\[${slug}\]\]/~~[[${slug}]]~~ (deprecated)/g" "$file"
```

---

## L4-L5：孤儿检测（与 index-rebuild 联动）

L4/L5 的完整检测逻辑在 `index-rules.md` 的「一致性校验」节。lint 执行时调用相同的检测逻辑并汇总报告。

---

## L6：related 膨胀检测

### 规则

```yaml
threshold:
  warning: 12     # ≥ 12 条时 WARNING
  critical: 15    # ≥ 15 条时 CRITICAL（已达上限，后续 backlink 会触发裁剪）
```

### 输出

```
[L6] related 膨胀 (1):
  ⚠️ WARNING:
    design/architecture-overview.md: related = 14 条（接近上限 15）
    建议: 审查这些引用是否仍然相关，移除不再需要的
```

---

## L7：pending 队列积压检测

### 规则

```yaml
threshold:
  warning_days: 7    # 有 pending 超过 7 天未消费时 WARNING
  error_days: 30     # 超过 30 天时 ERROR
```

### 输出

```
[L7] 反向引用积压 (1):
  ⚠️ WARNING:
    3 条 pending 回写已等待超过 7 天未消费
    最新积压: bl-003 (flows/fallback.md ← ops/new-doc.md), 8 天前
    建议: 运行 /knowledge-wiki health backlink-consume
```

---

## L8：status 不一致

### 检测逻辑

对比 frontmatter `status` 字段与 idx 文件中的 `status` 列。不一致时以 frontmatter 为准，报告差异。

### --fix 行为

自动用 frontmatter 的值覆盖 idx 中的值（安全操作，idx 是派生数据）。

---

## L9：过期未处理

复用 `health rot` 的检测结果。lint 中以独立段落展示所有 EXPIRED 文档列表，并在末尾追加批量操作入口提示。

---

## 综合报告模板

```markdown
📋 一致性检查报告（{datetime}）

扫描范围：.knowledge/ 下 N 篇文档
耗时：{duration}

---
摘要：
  🔴 ERROR: {N} 条（必须处理）
  ⚠️ WARNING: {N} 条（建议处理）
  ℹ️ INFO: {N} 条（仅供参考）

---

[L1] 数值/状态矛盾 ({N})
  ...

[L2] 悬空引用 ({N})
  ...

[L3] 废弃引用未标记 ({N})
  ...

[L4] 孤儿文档 ({N})
  ...

[L5] 孤儿索引 ({N})
  ...

[L6] related 膨胀 ({N})
  ...

[L7] pending 积压 ({N})
  ...

[L8] status 不一致 ({N})
  ...

[L9] 过期未处理 ({N})
  ...

---
下一步操作建议：
  {根据结果动态生成}
```

---

## --fix 模式

### 用法

```bash
/knowledge-wiki health lint           # 只报告，不修改
/knowledge-wiki health lint --fix     # 安全自动修复（仅 L3/L8 两项）
```

### --fix 安全边界

| 检查项 | --fix 动作 | 安全等级 |
|--------|----------|---------|
| L1 矛盾 | ❌ 不自动修复 | 需要人工判断 |
| L2 悬空引用 | ❌ 不自动修复 | 可能是有效引用（文件路径不同） |
| L3 废弃引用未标记 | ✅ 自动加 ~~~~ 标记 | 安全，纯标记操作 |
| L4 孤儿文档 | ❌ 不自动修复 | 需 index-rebuild |
| L5 孤儿索引 | ❌ 不自动修复 | 需人工确认 |
| L6 related 膨胀 | ❌ 不自动修复 | 需人工判断 |
| L7 pending 积压 | ❌ 不自动修复 | 应手动执行 backlink-consume |
| L8 status 不一致 | ✅ 自动同步 idx | 安全，idx 是派生数据 |
| L9 过期未处理 | ❌ 不自动修复 | 需人工 audit/deprecate |

---

## 与其他子命令的关系

```
health（综合报告）
├── rot         → L9 数据来源
├── scan        → 外部源变更（独立于 lint）
├── coverage    → 目录覆盖 + 问答缺口（独立于 lint）
├── audit       → 更新单个文档状态
├── deprecate   → 标记废弃 + 处理引用
├── lint        → 本文件：L1-L9 全量检查 ★
├── index-rebuild → 重建 idx + L4/L5 检测
└── backlink-consume → 消费 pending 队列（解决 L7）
```