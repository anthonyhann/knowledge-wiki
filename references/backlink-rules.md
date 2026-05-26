# 双向 related 回写规则（backlink）

> 解决"录入新文档时，旧文档不知道自己被引用了"的问题。
> 核心策略：延迟回写 + pending 队列 + health 批量消费。
> 由 `in` 写入队列，由 `health backlink-consume` 消费队列。
> SKILL.md 仅保留入口，本文件为唯一权威源。

---

## 设计原则

1. **不即时回写**：in 时不修改已有文档（避免并发冲突和用户等待）
2. **队列缓冲**：回写请求先写入 pending 文件，延迟到 health 时批量处理
3. **上限控制**：单个文档 related 总数 ≤ 15，超出时按优先级裁剪
4. **幂等安全**：重复消费同一条 pending 不产生副作用（去重检查）
5. **可追溯**：每条 backlink 记录来源 slug 和时间

---

## 数据结构

### pending-backlinks.yaml

```yaml
# .knowledge/.pending-backlinks.yaml
# 待消费的反向引用队列
# 格式：严格列表，每条记录一个"谁应该被添加到谁的 related 中"

version: 1
pending:
  - id: bl-001                    # 唯一 ID（时间戳 + 短 hash）
    target: flows/fallback-strategy.md   # 被引用的旧文档（需要追加 related 的目标）
    from: ops/timeout-mechanism.md       # 新文档（引用来源）
    from_title: 打印服务超时机制          # 来源文档标题
    created_at: "2026-05-26T14:30:08+08:00"
    consumed: false                   # 是否已被消费
    consumed_at: null                 # 消费时间

  - id: bl-002
    target: glossary/timeout.md
    from: ops/timeout-mechanism.md
    from_title: 打印服务超时机制
    created_at: "2026-05-26T14:30:08+08:00"
    consumed: false
    consumed_at: null

consumed_history: []                # 已消费记录（保留最近 200 条用于审计）
```

### ID 生成规则

```
id = "bl-" + {YYYYMMDDHHmmss} + "-" + {target_slug 前 4 字符 sha1[:4]}
例：bl-20260526143008-f6a7
```

保证同一 target + from 组合在短时间内不会重复生成（幂等）。

---

## 队列写入时机（in 流程 Step 9.5）

在 `in` 的 Step 9（写入 wiki 文档成功）之后、Step 10（log 追加）之前执行：

### 触发条件

以下条件**全部满足**时才生成 backlink：

1. 新文档的 `related` 字段 ≥ 1 条（即新文档引用了其他文档）
2. 被引用的文档不是 deprecated 状态（不给废弃文档追加引用）
3. 被引用的文档的 `related` 当前条数 < 15（未达上限则追加；已达上限则跳过并 WARNING）

### 执行流程

```
对 new_doc.related 中的每个 [[target_slug]]：
  1. 定位 target_slug 对应的实际文件路径（rg 搜索 .knowledge/）
  2. 读取该文件的 frontmatter 的 related 字段
  3. 检查是否已包含 [[new_doc_slug]]
     - 已包含 → 跳过（幂等，不重复添加）
     - 未包含 → 检查 related 条数
       - < 15 → 生成一条 pending 记录
       - ≥ 15 → 输出 WARNING："[[{target}]] related 已满(15)，跳过反向引用 [[{new_slug}]]"
  4. 将所有新生成的 pending 记录追加到 .pending-backlinks.yaml
```

### 示例

```
✓ 已写入 .knowledge/ops/print-timeout.md

正在检查反向引用...
  → flows/fallback-strategy.md 将追加 [[print-timeout]]（入队待消费）
  → glossary/timeout.md 将追加 [[print-timeout]]（入队待完成）
  → ops/timeout-v1.md related 已满(15)，跳过反向引用

运行 /knowledge-wiki health backlink-consume 完成回写
```

### --update 场景

`in --update` 时也执行 Step 9.5：
- 如果 update 后 related **新增**了对某文档的引用 → 生成 pending
- 如果 update 后 related **移除了**对某文档的引用 → 生成一条特殊 pending（action: remove）
- 如果 related 无变化 → 不生成任何 pending

remove 类型的 pending：

```yaml
  - id: bl-003
    target: flows/fallback-strategy.md
    from: ops/timeout-mechanism.md
    action: remove                     # 特殊标记：移除而非追加
    created_at: "2026-05-26T14:35:00+08:00"
    consumed: false
```

---

## 队列消费（health 子命令）

### `/knowledge-wiki health backlink-consume`

批量消费 `.pending-backlinks.yaml` 中的所有未消费记录。

### 消费流程

```
1. 读取 .pending-backlinks.yaml
2. 过滤出 consumed == false 的记录
3. 若无未消费记录 → 完全静默，输出"无待处理的反向引用"
4. 按 action 类型分组处理：

   ── action 为空或 "add"（默认，追加引用）──
   a. 读取 target 文件
   b. 检查 target 的 related 是否已包含 [[from]]（二次幂等检查）
      - 已包含 → 标记 consumed=true，跳过文件修改
      - 未包含 → 继续下一步
   c. 检查 target 的 related 条数
      - < 15 → 追加 [[from]] 到 related 数组末尾
      - ≥ 15 → 执行裁剪逻辑（见下方「上限裁剪」），然后追加
   d. 写回 target 文件（仅修改 frontmatter 的 related 字段）

   ── action: "remove"（移除引用）──
   a. 读取 target 文件
   b. 检查 target 的 related 是否包含 [[from]]
      - 不包含 → 标记 consumed=true，跳过（已自然消失或从未存在）
      - 包含 → 从 related 数组中移除 [[from]]
   c. 写回 target 文件

   ── 通用收尾（所有 action 类型）──
   e. 标记该 pending 为 consumed=true，记录 consumed_at
   f. 追加到 consumed_history（FIFO 截断：超过 200 条时丢弃最早的记录）

5. 更新 .pending-backlinks.yaml
6. 输出摘要
```

### 输出示例

```
🔗 反向引用消费完成

已处理：3 条
  ✅ flows/fallback-strategy.md ← 追加 [[print-timeout]]
  ✅ glossary/timeout.md ← 追加 [[print-timeout]]
  ⏭️ ops/timeout-v1.md ← 已存在，跳过

队列剩余：0 条
建议：下次 /knowledge-wiki health lint 检查一致性
```

### 上限裁剪算法

当 target 的 related 即将达到 16 条（即当前 15 条要再加 1 条）时触发：

```python
def trim_related(current_list, new_entry, max_size=15):
    if len(current_list) < max_size:
        return current_list + [new_entry]  # 不需裁剪

    # 需要裁剪：移除 1 条，腾出空间给新条目
    # 优先级排序（低优先级先被淘汰）：
    priority_order = [
        ('deprecated', 1),     # 引用了 deprecated 文档 → 最低优先级
        ('stale', 2),          # 目标文档 status=deprecated 或 draft 且 >180天
        ('cross_layer', 3),    # 跨 L1/L2/L3 层级的引用（同层优先保留）
        ('old', 4),            # 最久未被 ask 命中的引用（需要 log 数据支持）
        ('random', 5),         # 兜底：随机淘汰（极少走到这里）
    ]

    victim = select_victim(current_list, priority_order)
    current_list.remove(victim)
    return current_list + [new_entry]
```

**裁剪日志**：被裁剪的 related 条目不在文件中删除，而是在 log 中记录：

```markdown
## [2026-05-26T15:00:00] @hanqiang | backlink-trim | ops/timeout-v1.md
  detail: {"removed": "[[old-deprecated-doc]]", "reason": "related 上限(15)，淘汰最低优先级", "added": "[[new-doc]]"}
```

---

## 并发安全保障

### 为什么选择延迟回写

| 方案 | 冲突概率 | 说明 |
|------|---------|------|
| in 时即时回写 | **高** | 多人同时 in 可能同时写同一个 target 文件 |
| 异步后台回写 | 中 | 需要额外进程/守护机制 |
| **health 时批量消费** | **极低** | health 通常由单人操作，且操作前会 git pull 最新 |

### 消费前的安全检查

backlink-consume 开始前：

```bash
# 1. 确认工作区干净（无未提交更改）
git diff --quiet
if [ $? -ne 0 ]; then
  echo "⚠️ 工作区有未提交的更改，请先 commit 或 stash 后再执行 backlink-consume"
  exit 1
fi

# 2. git pull 确保最新
git pull --rebase
```

### 消费后的自动 commit

消费完成后，自动 commit 所有变更：

```bash
git add .knowledge/.pending-backlinks.yaml
git add .knowledge/{所有被修改的目标文件}
git commit -m "[kb] backlink-consume: 处理 N 条反向引用"
```

commit message 符合 `commit-msg.sh` hook 的 `[kb]` 前缀规范。

---

## 与 deprecate 的联动

当 `health deprecate <slug>` 执行时：

1. 正常流程：标记 slug 为 deprecated + 处理引用
2. **额外步骤 A**：扫描 `.pending-backlinks.yaml`，将所有 `from == <slug>` 的未消费 pending 标记为 consumed=true（原因：来源文档已废弃，不再需要追加其引用到其他文档）
3. **额外步骤 B**：扫描 `.pending-backlinks.yaml`，将所有 `target == <slug>` 的未消费 pending 标记为 consumed=true（原因：目标文档已废弃，无需继续向其追加任何 related）
4. **额外步骤 C**：扫描所有文档的 related，将 `[[<slug>]]` 标记为 `~~[[<slug>]]~~ (deprecated)`（不删除，只标记）

> 步骤 2-3 保证废弃文档不再参与任何方向的 backlink 消费，避免 consume 时处理已无意义的回写。

---

## 与 lint 的联动

`health lint`（详见 `lint-rules.md`）会检查：
- pending 队列中是否有积压超过 7 天未消费的记录 → 提示执行 backlink-consume
- 是否有悬空引用（related 中的 slug 对应文件不存在或已废弃但未标记）