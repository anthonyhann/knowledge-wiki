# 查询（ask）详细规则

> 由 `/knowledge-wiki ask` 使用。SKILL.md 仅保留入口与索引，本文件是唯一权威源。

---

## 检索策略（两层）

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

3 轮后仍 0 命中 → 跳过 Layer 1，直接输出「知识库无记录」模板，不猜测。

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

