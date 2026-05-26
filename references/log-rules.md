# 操作日志规则（log）

> 由 `in` / `ask` / `health` 所有子命令写入，`health` 负责归档与聚合。
> 核心设计：按人分文件解决 git 并发冲突，hash 脱敏保护隐私。
> SKILL.md 仅保留入口，本文件为唯一权威源。

---

## 设计原则

1. **按人分文件**：每人一个 log 文件，append-only，零 git 冲突
2. **结构化格式**：每条记录固定前缀，支持 grep 快速过滤
3. **隐私保护**：ask 内容做 hash 脱敏，不记录原始问题
4. **自动归档**：双阈值（条数 OR 时间）触发归档
5. **派生聚合**：digest 由 health 自动生成，不手动维护

---

## 目录结构

```
.knowledge/
├── .logs/
│   ├── _config.yaml              # 日志配置（归档阈值、脱敏规则等）
│   ├── personal/                 # 每人私有日志
│   │   ├── hanqiang.md           # @hanqiang 的操作记录
│   │   ├── zhangsan.md           # @zhangsan 的操作记录
│   │   └── ...
│   ├── archive/                  # 归档日志（只读）
│   │   ├── hanqiang-2026-Q1.md
│   │   └── ...
│   └── digest.md                 # 团队聚合摘要（health 自动生成，可 .gitignore）
```

---

## _config.yaml 格式

```yaml
# .knowledge/.logs/_config.yaml
# init 时创建，后续按需调整

version: 1

# 归档规则
archive:
  max_entries_per_file: 150       # 单文件超过此条数时触发归档
  max_days: 90                    # 或超过此天数也触发（先到为准）
  format: "{owner}-{YYYY-Q}.md"   # 归档文件名格式（按季度）

# 脱敏规则
sensitive_actions:
  ask:
    mode: hash                    # ask 内容只记 sha1(内容) 前 8 位
    # 例：ask: "a1b2c3d4" 而非 ask: "配送超时怎么配置"
  ingest:
    mode: plain                   # 录入操作记录 title 明文（需要，用于追溯）

# digest 聚合规则
digest:
  auto_generate_on: health        # 每次 health 执行时自动重新生成
  keep_recent: 50                 # digest 只保留最近 50 条
  include_personal_files: true    # 聚合所有 personal/*.md
  sort_by: time_desc              # 按时间倒序

# 覆盖率缺口分析（依赖 log 数据）
gap_analysis:
  min_window_days: 7              # 至少积累 7 天数据才分析
  min_hit_count: 3                # 同类去重后 ≥3 次未命中才算缺口
  anonymize: true                 # 聚合时去掉 @who 信息
```

---

## 日志条目格式

### 通用格式

```markdown
## [{ISO datetime}] @{owner} | {action} | {title}
  detail: {detail JSON or text}
  slug: {slug}                    # 有 slug 的操作（in/audit/deprecate）
  duration: {optional}            # 可选：操作耗时（human readable）
```

### 各 action 的 detail 字段规范

#### ingest（录入）

```markdown
## [2026-05-26T14:30:08+08:00] @hanqiang | ingest | 打印服务超时机制
  detail: {"type": "ops", "dir": "ops/", "status": "draft", "input_type": "url", "source": "feishu.cn/..."}
  slug: print-timeout
  related_updated: [timeout-mechanism, fallback-strategy]  # Step 9.5 回写的 related
```

#### update（更新）

```markdown
## [2026-05-26T14:35:22+08:00] @hanqiang | update | 打印服务超时机制
  detail: {"mode": "覆盖", "old_sources": 3, "new_sources": 4, "lines_changed": "+12 -5"}
  slug: print-timeout
```

#### ask（查询）— **脱敏处理**

```markdown
## [2026-05-26T14:40:15+08:00] @hanqiang | ask | a1b2c3d4
  detail: {"hit": "ops/print-timeout.md", "status": "FRESH", "docs_read": 1, "layer": "L0-R1"}
  # 注意：title 是 query_hash，不是原始问题原文
```

**hash 算法**：`sha1(原始问题)[:8]`，仅用于去重统计和"是否问过类似问题"的判定。

如果用户后续想查"我之前问了什么"，可以通过 hash 反向查找——但需要在 AI 对话上下文中保留映射（不在 log 文件中存储明文）。

#### health（维护各子命令）

```markdown
## [2026-05-26T15:00:00+08:00] @hanqiang | health | 综合报告
  detail: {"total": 47, "active": 32, "draft": 10, "deprecated": 5, "expired": 3, "warning": 5}
```

```markdown
## [2026-05-26T15:01:30+08:00] @hanqiang | health | audit print-timeout
  detail: {"result": "确认有效", "new_status": "active", "new_expires": "2026-08-24"}
  slug: print-timeout
```

```markdown
## [2026-05-26T15:02:10+08:00] @hanqiang | health | deprecate old-config
  detail: {"refs_found": 2, "refs_processed": 2}
  slug: old-config
```

```markdown
## [2026-05-26T15:03:45+08:00] @hanqiang | health | lint
  detail: {"contradictions": 2, "orphan_refs": 0, "stale_related": 5}
```

```markdown
## [2026-05-26T15:04:20+08:00] @hanqiang | health | index-rebuild
  detail: {"total_entries": 80, "added": 3, "removed": 1, "updated": 5}
```

#### backlink-consume（反向引用消费）

```markdown
## [2026-05-26T15:05:00+08:00] @hanqiang | backlink-consume | 批量回写
  detail: {"consumed": 5, "targets_updated": ["flows/fallback.md", "glossary/timeout.md"]}
```

---

## 写入规则

### 写入时机

| 操作 | 写入位置 | 时机 |
|------|---------|------|
| `/knowledge-wiki in` | `.logs/personal/{mis-id}.md` | Step 9（写入 wiki 文档成功后）立即追加 |
| `/knowledge-wiki in --update` | `.logs/personal/{mis-id}.md` | 更新完成后追加 |
| `/knowledge-wiki ask` | `.logs/personal/{mis-id}.md` | 回答生成后追加（无论是否命中） |
| `/knowledge-wiki health *` | `.logs/personal/{mis-id}.md` | 每个子命令执行后追加 |
| backlink consume | `.logs/personal/{mis-id}.md` | health 消费 pending 队列后追加 |

### 文件名规则

```
文件名 = mis-id（@ 符号后的部分）+ ".md"
例：@hanqiang → hanqiang.md
    @zhang_san → zhang_san.md
```

### mis-id 获取策略（优先级从高到低）

| 优先级 | 来源 | 适用场景 | 获取方式 |
|--------|------|---------|---------|
| 1 | 环境变量 `KB_OWNER` | CI/CD 或脚本自动化 | `echo $KB_OWNER` |
| 2 | git 配置 | 本地开发常规场景 | `git config user.name` 或 `git config user.email` 取 `@` 前缀（如 `hanqiang@meituan.com` → `hanqiang`） |
| 3 | 系统用户名 | git 未配置时兜底 | `whoami`（macOS/Linux） |
| 4 | 无法获取 | 异常场景 | 使用 `unknown` + 输出 WARNING |

**AI 执行规则**：
- 在每次 session 首次 in/ask/health 操作时确定 mis-id 并**缓存**（同一 session 内不重复获取）
- 确定后的 mis-id 同时用于：log 文件名 + frontmatter `owner` 字段 + commit author
- 若走到优先级 4（unknown），必须**明确提示用户**设置 `git config user.name` 或 `KB_OWNER` 环境变量

### 首次写入

当某用户的 personal 文件不存在时：
1. 创建 `.logs/personal/{mis-id}.md`
2. 写入文件头：

```markdown
# @{mis-id} 操作日志

> 自动生成于 {YYYY-MM-DD} | 归档阈值：{max_entries} 条或 {max_days} 天
> 最后归档：从未

---
```

3. 然后在 `---` 后追加第一条记录

---

## 归档流程

### 触发条件（满足任一即触发）

| 条件 | 判定逻辑 |
|------|---------|
| 条数超标 | `grep -c "^## \[" personal/{id}.md` > `_config.archive.max_entries` |
| 时间超标 | 文件首条记录时间距今 > `_config.archive.max_days` 天 |

### 归档步骤

```
1. 读取 personal/{id}.md 全文
2. 按 时间区间 分割：
   - 最近 150 条 → 保留在原文件（清空重写）
   - 其余 → 追加到 archive/{id}-{季度}.md
3. 更新原文件头的"最后归档"日期
4. 输出："日志已归档：{N} 条移至 archive/{id}-2026-Q2.md"
```

### 归档文件格式

```markdown
# @{mis-id} 归档日志 — 2026-Q2

> 归档于 2026-06-01 | 原始条目数：200

---

## [2026-04-01T09:00:00+08:00] @hanqiang | ingest | XXX
  ...

## [2026-04-03T14:20:00+08:00] @hanqiang | ask | abc12345
  ...

（其余历史记录...）
```

归档文件 **只读**（不再追加），仅作为审计用途。LLM 在跨 session 续写时**不读 archive**，只读当前 personal 文件的最近 N 条。

---

## digest.md 团队聚合

### 生成时机

每次 `/knowledge-wiki health`（无子命令，即综合报告模式）执行时自动重新生成。

### 生成逻辑

```
1. 读取 .logs/personal/ 下所有 .md 文件
2. 提取所有 "^## [" 开头的行（grep -h "^## \[" .logs/personal/*.md）
3. 按时间戳降序排序（sort -t '[' -k2 -r）
4. 取最近 _config.digest.keep_recent 条（默认 50）
5. 统计分析（见下方「统计维度」）
6. 覆写 .logs/digest.md（含统计段 + 最近记录段）
```

### digest 统计维度

在 digest.md 顶部生成统计段落，结构如下：

```markdown
## 统计（近 30 天）

| 操作类型 | 次数 | 占比 |
|---------|------|------|
| ingest  | 15   | 30%  |
| ask     | 28   | 56%  |
| health  | 5    | 10%  |
| backlink-consume | 2 | 4% |

### ask 未命中高频主题（去重后 ≥3 次）

| hash 前缀 | 次数 | 首次出现 | 建议 |
|-----------|------|---------|------|
| a1b2c3d4  | 5    | 2026-05-20 | 建议 /knowledge-wiki in 录入相关知识 |
| e5f6g7h8  | 3    | 2026-05-22 | 建议 /knowledge-wiki in 录入相关知识 |
```

统计提取命令参考：

```bash
# 按 action 分组统计
grep -h "^## \[" .logs/personal/*.md | grep -oP '\| \K[a-z-]+(?= \|)' | sort | uniq -c | sort -rn

# 提取 ask 未命中（detail 含 "hit":"none"）
grep -A1 "| ask |" .logs/personal/*.md | grep '"hit":"none"' | ...
```

### digest.md 格式

```markdown
# 团队操作摘要

> 自动生成于 2026-05-26T15:00:00 | 最近 50 条 | 来源：所有成员个人日志

---

## [2026-05-26T14:40:15] @zhangsan | ask | a1b2c3d4 → hit: ops/print-timeout (FRESH)
## [2026-05-26T14:35:22] @hanqiang | update | 打印服务超时机制
## [2026-05-26T14:30:08] @hanqiang | ingest | 打印服务超时机制 (ops/draft)
## [2026-05-25T16:20:00] @lisi | health | audit delivery-flow → active
## [2026-05-25T11:05:00] @zhangsan | ingest | 配送单状态机 (flow/draft)
...
```

### digest 的 git 处理

推荐将 `digest.md` 加入 `.gitignore`：

```
# .gitignore（知识库根目录或项目根 .gitignore）
.knowledge/.logs/digest.md
```

原因：
- digest 是纯派生文件，每次 health 都会重建
- 多人环境容易冲突且无价值（每个人本地 health 都能生成）
- 不影响 personal log 的版本管理（personal 文件仍正常 git track）

---

## 跨 session 续写

### LLM 如何使用 log 恢复上下文

新 session 开始时，CLAUDE.md / AGENTS.md 中应指示 LLM：

```
续写指引：
1. 读取 .logs/personal/{当前用户 mis-id}.md 的最近 20 条记录
2. 重点关注最近的 ingest 和 ask 记录
3. 如果上次操作是未完成的 --update 或 audit，主动提示继续
4. 如果最近多次 ask 未命中同一主题，建议录入该主题
```

### 推荐读取量

| 场景 | 读取条数 | 原因 |
|------|---------|------|
| 新 session 开始 | 最近 20 条 | 足够恢复上下文，不过多消耗 token |
| `health` 执行前 | 最近 50 条 | 了解近期活动全貌 |
| `in` 录入前 | 最近 10 条 | 检查是否有重复录入 |

---

## 与 coverage 缺口分析的集成

### 数据来源

从 personal log 中提取 `ask` 未命中记录：

```bash
# 提取最近 7 天的 ask 未命中记录
grep "| ask |" .logs/personal/*.md | grep '"hit":"none"' | ...
```

### 过滤规则

详见 `_config.gap_analysis`：

1. **时间窗口**：只分析近 7 天的数据（太旧的不反映当前需求）
2. **最低频次**：语义去重后 ≥3 次未命中才算缺口
3. **排除模式**：编码问题、排查请求、个人事务等排除
4. **匿名化**：聚合报告中不显示 @who

### 输出位置

在 `health coverage` 报告中增加 `[问答缺口]` 段落（详见 `health-rules.md` 更新部分）。