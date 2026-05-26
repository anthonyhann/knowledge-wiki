# knowledge-wiki 待实现能力清单

> 本文件记录 v0.8.0「知识编译器」架构中**规则已定义但尚未完全落地实现**的能力项。
> 已完成的能力（规则文档 + SKILL.md 集成 + README/CHANGELOG 同步）不在本文件范围内。
> **上次审计日期：2026-05-26**

---

## 规则覆盖完整性自检

> 以下为用户明确要求的关键设计决策，逐项对照 references 文件的覆盖情况。

### ✅ 已完整覆盖（无需额外实现）

| # | 设计决策 | 覆盖文件 | 关键位置 |
|---|---------|---------|---------|
| 1 | 每个 .idx.md 只在对应 in 操作时更新（减少冲突面） | `index-rules.md` | §设计原则 #1 + §写入时机 |
| 2 | ask 时先推断属于哪个 idx，只读那一个（不读全部） | `index-rules.md` | §读取规则 Layer -1 + idx 选择策略表（含 synthesis 行） |
| 3 | _meta.yaml 记录上次重建时间，超 30 天 health 提示 | `index-rules.md` | §_meta.yaml 格式 `rebuild_threshold_days: 30` |
| 4 | ask 内容做 hash 脱敏（保护隐私） | `log-rules.md` | §_config.yaml `sensitive_actions.ask.mode: hash` |
| 5 | 归档双阈值（条数 150 OR 时间 90 天） | `log-rules.md` | §_config.yaml `archive.max_entries_per_file + max_days` |
| 6 | digest 只在 health 时生成（不实时） | `log-rules.md` | §_config.yaml `digest.auto_generate_on: health` + §digest 统计维度 |
| 7 | 不即时回写 related，记录到 pending 队列 | `backlink-rules.md` | §设计原则 #1-2 + §队列写入时机 |
| 8 | health 批量消费队列（单人操作冲突低） | `backlink-rules.md` | §队列消费 `health backlink-consume`（含 add/remove 分支） |
| 9 | related_max: 15（单文档最多 15 条） | `backlink-rules.md` | §设计原则 #3 + 消费流程 step 4c |
| 10 | 矛盾检测在 health lint 集中做，不自动检测 | `lint-rules.md` | §设计原则（辅助提示非自动修复） |
| 11 | lint 矛盾规则收敛到高置信场景（5D 过滤） | `lint-rules.md` | §5D 矛盾过滤框架 + §5D 判定阈值与报告级别 + §AI prompt 模板 |
| 12 | 矛盾标记不写入 wiki 文档，只输出到 lint 报告 | `lint-rules.md` | §lint 输出（只报告不修改） |
| 13 | 不自动解决矛盾，只记录和提示 | `lint-rules.md` | §--fix 只修 L3+L8，L1 矛盾不可 fix |
| 14 | health rot 增加 related 清理（deprecated 自动移除） | `health-rules.md` | §rot 附带：related 悬空链接清理 |
| 15 | synthesis.idx.md 独立存在 | `index-rules.md` | §type → idx 文件映射表 + idx 选择策略表 |
| 16 | mis-id 获取策略（4 级优先级回退） | `log-rules.md` | §mis-id 获取策略（环境变量→git→whoami→unknown） |
| 17 | L1 检测范围限制（不做全量笛卡尔积） | `lint-rules.md` | §检测范围（性能控制）（tag 分组 + 100 对上限） |
| 18 | backlink remove action 的消费处理 | `backlink-rules.md` | §消费流程 action: "remove" 分支 |
| 19 | deprecate 联动清理 pending（from + target 双向） | `backlink-rules.md` | §与 deprecate 的联动（步骤 A/B/C） |
| 20 | --from-answer 完整规则（type/sources/derived_from） | `ask-rules.md` | §--from-answer 处理（已更新为正式 synthesis 流程） |

---

## ~~P0 — 必须落地~~ ✅ 已完成

### ~~1. 系统配置文件模板初始化~~ ✅

**状态**：已完成（v0.8.1）

已创建的模板文件：
- `references/templates/_meta.yaml.tpl` — 索引元数据（9 个 indexes, `${TODAY}` 变量）
- `references/templates/_logs_config.yaml.tpl` — 日志配置（完整匹配 log-rules.md §_config.yaml）
- `references/templates/_pending_backlinks.yaml.tpl` — 空队列模板
- `references/templates/_idx_empty.md.tpl` — 通用 idx 表头模板（`${TYPE_DISPLAY}` + `${TODAY}` 变量）

`directory-structure.md` Step 4-5 已更新引用这些模板文件。

---

## ~~P1 — 应尽快落地~~ ✅ 已完成

### ~~2. `--from-answer` 完整流程实现~~ ✅

**状态**：已完成（v0.8.2）

已在 `ingestion-rules.md` 中新增完整的 `## --from-answer` 节，包含：
- 14 步流程变体（含跳过项说明 + synthesis 专属质量门禁 4 项）
- frontmatter 额外字段规范（derived_from / derived_question）
- sources 字段格式
- 录入确认输出模板
- 禁止二次回流规则

### ~~3. log digest 自动聚合~~ ✅

**状态**：已完成（v0.8.2）

- `health-rules.md` 已有 §digest 重建（上轮审计新增）
- 综合报告模板中已增加 `[操作日志]` 摘要行
- 综合报告生成流程中明确 Step 1 为 digest 重建、Step 9 为日志摘要提取

### ~~4. init 端到端验证~~ ✅

**状态**：已完成（v0.8.2）

- `SKILL.md` init Step 4 已扩展为"自我校验 + 输出安装摘要"
- 8 项校验清单内嵌于 SKILL.md（无需额外文件）
- 支持部分失败时 WARNING 输出（不中止）

---

## P2 — 锦上添花（长期优化）

### 5. idx 条目的增量更新 vs 全量覆写策略

**现状**：`index-rules.md` 定义了 append-only 写入和 update 时替换行的逻辑，当前设计在中小规模足够。

| 场景 | 当前行为 | 评估 |
|------|---------|------|
| 同一 slug 多次 in（无 --update） | 不检查重复，追加新行 | OK，由 health rebuild 去重 |
| --update 找不到旧行 | 不报错，直接追加新行 | OK，rebuild 补齐 |
| deprecate 后 idx status 更新 | 标记 deprecated + 删除线 | ✅ 已覆盖 |
| idx 文件过大（>500 行） | 无分割策略 | ⚠️ 中期监控（当前 9 个 type 分 9 个文件，每个不太会超 100 行） |

**结论**：当前设计在中小规模（<100 文档/type）足够，无需立即实现分割。

### 6. pending-backlinks.yaml 的并发安全增强

**现状**：队列文件是单一 YAML，多用户同时 append 可能冲突

**已有的缓解策略**：
- `in` 只 append（git merge 通常能自动合并尾部追加）
- `backlink-consume` 是 health 的子命令，通常单人执行
- consumed_history 保留审计轨迹，FIFO 截断 200 条

**可选增强方案**（P2 优先级）：
- 方案 A：每人一个 pending 文件（`.pending-backlinks-{mis-id}.yaml`），consume 时合并读取
- 方案 B：保持单文件，consume 前 `git pull --rebase` 确保最新
- **推荐 B**（已在 backlink-rules.md 的"安全保障"中规定了 consume 前 pull）

### 7. 操作日志的隐私增强

**现状**（已覆盖）：
- ask 内容：sha1 hash 脱敏 ✅
- ingest title：明文 ✅（需要，用于追溯）

**可选增强**（低优先级）：
- title 中检测到 URL/IP/密钥模式时自动 mask
- 增加 `_config.yaml` 的 `sensitive_patterns` 正则配置

### ~~8. health 综合报告的可视化输出~~ ✅

**状态**：已完成（v0.9.0）

- `health-rules.md` 新增 §输出模式选项：`--json`（完整 JSON schema）+ `--verbose`（ASCII 图表）
- SKILL.md 子命令速查已增加 `--json` 和 `--verbose` 两个选项
- 综合报告模板增加 type 分布树 + 操作活跃度摘要行

### ~~9. git hook 增强~~ ✅

**状态**：已完成（v0.9.0）

已创建的脚本：
- `references/scripts/pre-commit.sh` — 轻量 lint（L2 悬空引用 + L5 孤儿索引），<2s，ERROR 阻断
- `references/scripts/post-merge.sh` — 合并后提示 index-rebuild（检测变更数 + 索引年龄）

SKILL.md hook 表格已更新（4 个 hook），安装命令已同步。

---

## 本次审计修复清单（2026-05-26）

> 以下问题在本次审计中已被修复，从待实现转为已完成。

| # | 修复项 | 影响文件 | 修复内容 |
|---|--------|---------|---------|
| F1 | synthesis idx 选择策略行缺失 | `index-rules.md` / `ask-rules.md` | 在 idx 选择策略表中添加 synthesis 推断行 |
| F2 | 全局 "8 个" → "9 个" 不一致 | 7 个文件 | 统一更新为 9 个业务目录/idx 文件 |
| F3 | mis-id 获取逻辑不明确 | `log-rules.md` | 新增 §mis-id 获取策略（4 级优先级回退） |
| F4 | digest 缺具体统计维度和命令 | `log-rules.md` | 新增 §digest 统计维度 + grep 命令参考 |
| F5 | backlink remove 消费逻辑缺失 | `backlink-rules.md` | 消费流程增加 action: remove 分支 |
| F6 | deprecate 联动缺 target 侧清理 | `backlink-rules.md` | 新增步骤 B（target == slug 的 pending 也清理） |
| F7 | consumed_history 截断方式不明 | `backlink-rules.md` | 明确 FIFO 截断策略 |
| F8 | L1 检测缺 prompt 模板 | `lint-rules.md` | 新增 §AI 执行 L1 检测的 prompt 模板 |
| F9 | 5D 阈值与伪代码不一致 | `lint-rules.md` | 统一为 5=ERROR/4=WARNING/3=INFO/≤2=静默 |
| F10 | L1 检测范围未定义（性能问题） | `lint-rules.md` | 新增 §检测范围（tag 分组 + 100 对上限） |
| F11 | 属性值提取缺 AI 指引 | `lint-rules.md` | 新增 §属性值提取指引（匹配模式 + 优先级分类） |
| F12 | ask-rules.md --from-answer 描述过时 | `ask-rules.md` | 更新为正式 synthesis 流程规则 |

---

## 版本规划建议

| 版本 | 目标 | 状态 | 包含项 |
|------|------|------|--------|
| v0.8.1 | **可用性修复** | ✅ 已完成 | P0 #1（系统配置模板文件） |
| v0.8.2 | **体验提升** | ✅ 已完成 | P1 #2（--from-answer）+ P1 #3（digest 聚合）+ P1 #4（init 校验） |
| v0.9.0 | **架构优化** | ✅ 已完成 | P2 #8（--json/--verbose）+ P2 #9（pre-commit/post-merge hook） |
| v0.9.1 | **稳定性增强**（未来） | 待定 | P2 #5（idx 分割监控）+ P2 #6（pending 并发安全）+ P2 #7（隐私增强） |

---

## 关键设计决策备忘录

> 以下决策已固化到 references 文件中，列在此处方便快速回顾。

1. **idx 不做实时全量更新**——只在 in 对应 type 的 idx 时 append，减少冲突面 → 定期 health rebuild 保证一致性
2. **ask 不读全部 idx**——先推断 1-2 个最可能的 idx（含 synthesis），命中则限定 rg 范围；无法推断则跳过（不比原来慢）
3. **log 不即时 digest**——digest 只在 health 执行时重新生成，含统计段落和未命中高频分析
4. **backlink 不即时回写**——pending 队列 + health 单人消费，支持 add/remove 双向操作；related_max=15 防膨胀
5. **矛盾检测是辅助而非自动**——只在 health lint 集中做，tag 分组限制检测范围（≤100 对），5D 全满足才 ERROR，不写入文档，不自动解决
6. **rot 顺带清理 related**——deprecated 引用自动移除，悬空链接仅 WARNING 需人工确认
7. **deprecate 双向清理 pending**——废弃文档无论是 from 还是 target，其 pending 记录均标记 consumed
8. **mis-id 四级回退**——KB_OWNER → git config → whoami → unknown（WARNING），session 内缓存

---

## Ask 回流（synthesis）与问题驱动覆盖率 — 深度分析

> 以下归纳当前两大功能的已实现能力、核心风险、遗留问题及可行的实施方案。

---

### 一、Ask 回流（synthesis）功能总览

#### 1.1 已实现能力

| 能力 | 覆盖文件 | 状态 |
|------|---------|------|
| 回流触发条件（≥2 篇 + >300 词 + 跨文档综合） | `ask-rules.md` §Ask 回流提示 | ✅ 规则完备 |
| 禁止二次回流（synthesis 命中时不显示提示） | `ask-rules.md` / `ingestion-rules.md` / `synthesis.md` | ✅ 三处一致 |
| `--from-answer` 14 步流程变体 | `ingestion-rules.md` §--from-answer | ✅ 规则完备 |
| synthesis 专属质量门禁（4 项） | `ingestion-rules.md` Step 8.5 | ✅ 规则完备 |
| frontmatter 额外字段（derived_from / derived_question） | `ingestion-rules.md` + `synthesis.md` 模板 | ✅ 规则完备 |
| synthesis.idx.md 索引独立管理 | `index-rules.md` idx 选择策略表 | ✅ 规则完备 |
| 60 天短过期策略 | `_registry.yaml` expires_days=60 | ✅ 已配置 |

#### 1.2 核心风险

| # | 风险 | 影响 | 严重度 |
|---|------|------|--------|
| R1 | **synthesis 膨胀导致信噪比下降** | 若用户频繁触发回流，synthesis/ 目录迅速膨胀，ask 时 synthesis.idx.md 变得臃肿，真正有价值的综合分析被噪声淹没 | 🔴 HIGH |
| R2 | **derived_from 级联过期** | 原始文档 A 过期/废弃后，依赖 A 的 synthesis 文档可能给出过时结论，但当前 rot 扫描不检查 derived_from 源的健康状态 | 🔴 HIGH |
| R3 | **回流触发误判** | "跨文档综合"的判断由 AI 语义理解完成，缺乏硬性规则校验；可能将简单拼接误判为综合分析，或遗漏真正有价值的综合 | 🟡 MEDIUM |
| R4 | **ask 上下文丢失** | `--from-answer` 依赖当前对话上下文中的 AI 回答内容；若用户在新会话中执行该命令，原始回答已不可见，无法完成回流 | 🟡 MEDIUM |
| R5 | **derived_from slug 变更** | 原始文档被 rename（slug 重新生成）后，synthesis 的 derived_from 变成悬空引用，但当前无检测机制 | 🟡 MEDIUM |
| R6 | **synthesis 与原文的一致性漂移** | synthesis 创建后原始文档被 `--update` 修改，综合结论可能已过时，但只能等 60 天过期才被动发现 | 🟡 MEDIUM |

#### 1.3 遗留问题

| # | 问题 | 当前规则缺失 |
|---|------|-------------|
| Q1 | synthesis 文档数量上限未定义 | 无配额策略（如每月/每季度最多生成 N 篇），可能导致无限膨胀 |
| Q2 | 级联过期检测未纳入 rot 流程 | `rot` 只检查文档自身 expires，不检查 derived_from 源是否已 deprecated/expired |
| Q3 | `--from-answer` 无会话绑定机制 | 规则未定义"当原始 ask 对话不可访问时如何降级处理" |
| Q4 | synthesis 的 health audit 升级策略不明 | 当前 audit 选 [1] 续期 60 天，但 synthesis 升级为 active 的准入条件是什么？是否需要人工验证 derived_from 源均有效？ |
| Q5 | 回流触发的"跨文档综合"无量化标准 | "包含跨文档的对比、分析或关联发现"完全依赖 AI 主观判断，缺乏可操作的判定 checklist |
| Q6 | synthesis 正文更新路径未定义 | 原始文档更新后 synthesis 如何同步？`--update` 对 synthesis 的行为未特别说明 |

#### 1.4 可行实施方案

##### 方案 S1：synthesis 配额与自动清理（解决 R1/Q1）

```
规则新增位置：health-rules.md §rot 或 _registry.yaml synthesis 条目

配额策略：
- 软上限：synthesis/ 目录 ≤30 篇（超出时 health 报 WARNING，建议 deprecate 低价值条目）
- 硬上限：≤50 篇（超出时 --from-answer 拒绝创建，提示先清理）
- 自动清理候选：status=draft 且 >60 天未 audit 的 synthesis 自动标记为 expired

优先级：P2
依赖：无
```

##### 方案 S2：derived_from 级联健康检查（解决 R2/Q2）

```
规则新增位置：health-rules.md §rot 段

扩展 rot 流程：
1. 对每篇 synthesis 文档，读取 derived_from 列表
2. 逐一检查源文档状态：
   - 任一源 status=deprecated → synthesis 标记 WARNING（"源文档已废弃，综合结论可能失效"）
   - 任一源 status=expired → synthesis 标记 WARNING（"源文档已过期，建议重新审视"）
   - 所有源均 deprecated → synthesis 直接标记 expired
3. 输出段独立展示（不混入普通 rot）

优先级：P1（影响数据可靠性）
依赖：rot 流程已完备
```

##### 方案 S3：会话绑定降级策略（解决 R4/Q3）

```
规则新增位置：ingestion-rules.md §--from-answer 流程变体

降级分支：
- 若 AI 无法获取当前会话中的 ask 回答内容（新会话/上下文丢失）：
  1. 检查最近 1 条 personal log 中 action=ask 且 hit≠none 的记录
  2. 若 log 中有匹配记录且 detail.docs_read ≥2：
     → 提示用户手动粘贴之前的分析内容，按标准 in 流程处理（type 仍强制为 synthesis）
  3. 若无匹配：
     → 拒绝，提示"请在包含原始 ask 回答的同一会话中执行此命令"

优先级：P2
依赖：log 规则已完备
```

##### 方案 S4：回流触发量化 Checklist（解决 R3/Q5）

```
规则新增位置：ask-rules.md §Ask 回流提示 → 触发条件细化

量化标准（全部满足才触发）：
1. docs_read ≥ 2（保持不变）
2. 回答 token 数 > 300（保持不变）
3. 回答中包含至少 1 个"跨文档信号词"：
   - 对比类：与...不同 / 区别在于 / 相比 / 对比
   - 综合类：综合来看 / 结合...和... / 综合以上
   - 关联类：关联发现 / 值得注意的是 / ...暗示...
   - 矛盾类：然而 / 但...指出 / 与...冲突
4. 若无信号词但 docs_read ≥ 3 → 仍触发（多文档参考本身暗示综合）

优先级：P2
依赖：无
```

##### 方案 S5：synthesis 被动更新通知（解决 R6/Q6）

```
规则新增位置：ingestion-rules.md §--update 段 或 health-rules.md 新增段

策略：
- 当 in --update <slug> 修改的文档被某 synthesis 的 derived_from 引用时：
  1. 通过 rg "derived_from:.*{slug}" .knowledge/synthesis/ 找到受影响的 synthesis
  2. 在 --update 确认输出末尾追加提示：
     "⚠️ 以下 synthesis 文档基于此文档生成，可能需要审查：
       - synthesis/xxx.md（created: 2026-05-20）"
  3. 不自动修改 synthesis，仅提示

优先级：P3（提示型，不影响主流程）
依赖：rg 追溯能力
```

##### 方案 S6：derived_from 悬空链接检测（解决 R5）

```
规则新增位置：lint-rules.md 新增 L10 检查项

L10 检查逻辑：
- 遍历 synthesis/ 下所有文档的 derived_from 字段
- 检查每个 slug 对应的 .md 文件是否存在
- 不存在 → 报 ERROR（可 --fix 标记为 # orphan）
- 存在但 slug 不匹配（可能是 rename 残留）→ 报 WARNING

优先级：P2
依赖：lint 框架已完备
```

---

### 二、问题驱动覆盖率（coverage）功能总览

#### 2.1 已实现能力

| 能力 | 覆盖文件 | 状态 |
|------|---------|------|
| 项目根检测（4 级回退） | `health-rules.md` §coverage / SKILL.md | ✅ 规则完备 |
| 目录映射覆盖率（模块级） | `health-rules.md` §coverage 扫描流程 | ✅ 规则完备 |
| 问答缺口分析（log 驱动） | `health-rules.md` §coverage 增强版 | ✅ 规则完备 |
| 未命中高频去重（≥3 次算缺口） | `health-rules.md` §数据来源与过滤 | ✅ 规则完备 |
| 已解决缺口展示 | `health-rules.md` §新增段落输出 | ✅ 规则完备 |
| digest 中包含 ask 未命中统计 | `log-rules.md` §digest 统计维度 | ✅ 规则完备 |

#### 2.2 核心风险

| # | 风险 | 影响 | 严重度 |
|---|------|------|--------|
| R7 | **未命中聚合的语义模糊** | "配送超时配置" 和 "delivery timeout setting" 是同一问题但 hash 不同，无法自动聚合，导致缺口被低估 | 🔴 HIGH |
| R8 | **覆盖率仅模块级，缺乏主题级深度** | 目录映射只能发现"哪个模块没文档"，无法发现"某模块虽有文档但缺关键主题" | 🟡 MEDIUM |
| R9 | **日志数据不足时的冷启动问题** | 规则要求"至少积累 7 天数据才分析"，新团队或新项目初期 coverage 无问答缺口输出 | 🟡 MEDIUM |
| R10 | **ask 脱敏与缺口分析的矛盾** | ask 记录使用 sha1 hash 脱敏，但问答缺口需要聚合"同类问题"——hash 后无法做语义聚合 | 🔴 HIGH |
| R11 | **"已解决"判定误差** | 当前用"后来录入了"简单判断，但录入的文档不一定能回答原始问题（tag 匹配 ≠ 语义覆盖） | 🟡 MEDIUM |

#### 2.3 遗留问题

| # | 问题 | 当前规则缺失 |
|---|------|-------------|
| Q7 | hash 脱敏与语义聚合矛盾 | `log-rules.md` 要求 ask 做 sha1 脱敏，但 `coverage` 需要对未命中问题做语义聚合，两者冲突未解决 |
| Q8 | 缺口聚合算法未定义 | "同类去重后 ≥3 次才算缺口"的"同类"如何判定？当前规则无聚合算法（中英文同义/近义匹配） |
| Q9 | coverage 缺乏趋势对比 | 只有当前快照，没有"本周 vs 上周"或"本月 vs 上月"的覆盖率趋势变化 |
| Q10 | 目录映射覆盖率的排除规则不够智能 | 硬编码排除 node_modules/vendor 等，若项目有自定义目录（如 `scripts/`、`tools/`）不应算作业务模块但可能被误报 |
| Q11 | "已解决缺口"的验证不够严谨 | 只检查"后来是否有录入操作"，未验证录入内容是否确实覆盖了原始问题 |

#### 2.4 可行实施方案

##### 方案 C1：双轨记录解决脱敏与聚合矛盾（解决 R10/Q7）

```
规则修改位置：log-rules.md §ask 记录格式

双轨策略：
- personal log（git tracked）：保持 sha1 hash 脱敏（隐私保护）
- coverage 聚合专用文件 .logs/_coverage_hints.yaml（建议 .gitignore）：
  记录 ask 未命中时的关键词摘要（非完整问题，仅保留 2-3 个核心实体词）
  格式：
    - date: 2026-05-26
      keywords: ["配送超时", "配置"]
      hash: a1b2c3d4   # 关联到 personal log
      hit: none

优点：隐私敏感信息不入 git；聚合分析用本地文件完成
缺点：.gitignore 后多人场景下无法跨人聚合

优先级：P1（直接影响 coverage 功能可用性）
依赖：log-rules.md 修改
```

##### 方案 C2：关键词聚合算法（解决 Q8）

```
规则新增位置：health-rules.md §coverage 增强版 → 新增"聚合算法"段

聚合逻辑（基于 _coverage_hints.yaml）：
1. 提取所有 hit=none 记录的 keywords 数组
2. 按 Jaccard 相似度聚类：两条记录的 keywords 交集/并集 ≥ 0.5 → 视为同类
3. 同类聚合后 count ≥ 3 → 标记为缺口
4. 取每个聚类中频率最高的关键词组合作为缺口描述
5. 中英文同义处理：维护 .knowledge/glossary/ 中的别名表做 alias 映射

示例：
  - ["配送超时", "配置"] + ["delivery", "timeout"] → Jaccard 通过 glossary alias 归一后 = 1.0 → 同类

优先级：P2
依赖：方案 C1 + glossary 别名表
```

##### 方案 C3：coverage 趋势快照（解决 Q9）

```
规则新增位置：health-rules.md §coverage 新增"趋势"段

策略：
- 每次 health coverage 执行时，将结果追加到 .logs/_coverage_snapshots.yaml：
    - date: 2026-05-26
      total_modules: 15
      covered: 12
      coverage_pct: 80%
      gaps: ["goods", "queue", "redis3"]
      ask_miss_count: 5
- 输出时对比上一条快照，展示变化：
    "覆盖率：80%（↑5% vs 上次 75%）| 新增覆盖：payment | 新增缺口：redis3"

优先级：P3
依赖：无
```

##### 方案 C4：目录映射可配置排除（解决 Q10）

```
规则修改位置：health-rules.md §coverage 扫描流程

新增：支持 .knowledge/.coverage-ignore 文件
格式（每行一个 glob 模式）：
    scripts/
    tools/
    docs/
    *.bak

若文件不存在 → 使用默认排除列表（node_modules/vendor/.git/...）
若文件存在 → 默认排除列表 + 用户自定义排除列表合并

优先级：P3
依赖：无
```

##### 方案 C5：主题级覆盖率增强（解决 R8）

```
规则新增位置：health-rules.md §coverage 新增"主题深度"段

策略：
- 在目录级覆盖率基础上，增加"主题热力图"：
  1. 从 synthesis.idx.md + 各 idx 的 tags 列，提取知识库已覆盖的主题词集合 S
  2. 从项目代码注释（// TODO / FIXME / HACK）和 README 中提取潜在主题词集合 P
  3. P - S = 潜在未覆盖主题
  4. 结合 ask 未命中的 keywords 做交叉验证（若 P-S 中某主题同时出现在未命中关键词中 → 高置信缺口）

输出示例：
  "[主题级缺口]  高置信：redis-cluster-failover（代码 TODO + ask 未命中 2 次）"

优先级：P3（探索性，依赖代码分析能力）
依赖：方案 C1 + 项目代码扫描
```

##### 方案 C6："已解决"严格验证（解决 R11/Q11）

```
规则修改位置：health-rules.md §coverage 增强版 → "已解决"判定

增强判定逻辑：
1. 原始：检查缺口关键词是否在新录入文档的 title/tags 中出现 → 命中算已解决
2. 增强：
   a. 关键词出现在新文档 title/tags/TL;DR → 强命中 ✓
   b. 仅出现在正文 → 弱命中（标记 "可能已解决，建议验证"）
   c. 未出现 → 未解决
3. 验证方式：用新文档对原始问题做模拟 ask（不记 log），若 Layer 0 能命中 → 确认已解决

优先级：P3
依赖：ask 流程可内部调用
```

---

### 三、两功能交叉风险与联动方案

| # | 交叉场景 | 当前状态 | 建议 |
|---|---------|---------|------|
| X1 | ask 未命中 → 用户手动综合多文档回答 → 触发回流 → synthesis 录入 | 流程完备但未命中 log 可能已记录 hash → coverage 无法知道此缺口已被 synthesis 解决 | 回流录入后应消除对应的 coverage 缺口记录 |
| X2 | synthesis 过期后的 ask 命中 | 命中 expired synthesis 会显示过期警告，但不会提示"重新运行 ask 获取最新综合" | 增加提示："此综合文档已过期，源文档可能已更新。建议重新 ask 获取最新结论。" |
| X3 | coverage 缺口与 synthesis 触发的正反馈循环 | 高频未命中 → 用户录入 → 后续 ask 命中 → 可能触发回流 → synthesis 膨胀 | 配额策略（S1）是安全网；同时应在回流提示中显示当前 synthesis 篇数 |

### 四、实施优先级总览

| 优先级 | 方案编号 | 描述 | 预计工作量 |
|--------|---------|------|-----------|
| **P1** | S2 | derived_from 级联健康检查 | 小（rot 流程扩展） |
| **P1** | C1 | 双轨记录解决脱敏聚合矛盾 | 中（log 格式变更） |
| **P2** | S1 | synthesis 配额与自动清理 | 小（_registry + rot 扩展） |
| **P2** | S3 | 会话绑定降级策略 | 小（规则补充） |
| **P2** | S4 | 回流触发量化 Checklist | 小（规则补充） |
| **P2** | S6 | derived_from 悬空链接检测（L10） | 小（lint 扩展） |
| **P2** | C2 | 关键词聚合算法 | 中（算法设计） |
| **P3** | S5 | synthesis 被动更新通知 | 小（--update 扩展） |
| **P3** | C3 | coverage 趋势快照 | 小（日志扩展） |
| **P3** | C4 | 目录映射可配置排除 | 小（新增配置文件） |
| **P3** | C5 | 主题级覆盖率增强 | 大（探索性） |
| **P3** | C6 | "已解决"严格验证 | 中（ask 内部调用） |

---

### 五、版本规划建议（追加）

| 版本 | 目标 | 包含方案 |
|------|------|---------|
| v0.9.2 | **数据可靠性** | S2（级联过期检测）+ C1（双轨记录） |
| v0.9.3 | **回流质量** | S1（配额）+ S4（触发 checklist）+ S6（L10 检测） |
| v1.0.0 | **覆盖率闭环** | C2（聚合算法）+ S3（会话降级）+ C3（趋势） |
| v1.1.0 | **深度增强** | S5（被动通知）+ C4/C5/C6（覆盖率精细化） |