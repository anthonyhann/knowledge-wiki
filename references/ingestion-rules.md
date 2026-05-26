# 录入结构化规则（in 子命令使用）

> 由 `/knowledge-wiki in` 文本/URL/文件三类输入共享。SKILL.md 仅保留入口与索引，本文件是唯一权威源。

---

## AI 结构化流程（14 步，含模板加载、质量门禁、索引更新、日志记录、反向引用入队）

```
1. 提取 title
2. 推断 type（见下方 type 推断规则）
2.5 加载 type 专属模板（references/templates/_registry.yaml → templates/{type}.md）
2.6 [仅当 type=glossary] 去重前置检查（详见下方「Step 2.6 glossary 去重前置」）
2.65 [所有 type 均执行] 全类型相似检测前置（详见下方「Step 2.65 全类型相似检测前置」）
2.7 [所有 type 均执行] 跨类型术语抽取（详见下方「Step 2.7 跨类型术语抽取」）
3. 提取 tags（3-5 个，从正文提取核心实体词）
4. 生成 TL;DR（50-100 词，必填，回答"这是什么+核心结论"；输入正文 < 50 词时直接复用全文，> 1000 词时先摘要再压到 100 词内，超出 100 词截断到最近句号）
5. 按模板骨架整理详情正文（必填段不可缺，可选段视内容补充）
6. 扫描 .knowledge/ 推荐 related（rg 命令见下，结果取交集 ≥1 即推荐）
7. 生成 slug（规则见下）
8. 若目标文件已存在 → 询问：覆盖 / 追加 / 中止
8.5 质量门禁：校验 _registry.yaml 中 required_sections 与 quality_gate；缺失即返回用户补充
9. 写入 .knowledge/{对应目录}/{slug}.md
9.5 [NEW] 更新分段索引：追加条目到 .index/{type}.idx.md（详见 `references/index-rules.md`「写入时机与规则」）
9.6 [NEW] 反向引用入队：若 related ≥1 条且被引用文档非 deprecated 且 related 未满 15 条，将回写请求追加到 .pending-backlinks.yaml（详见 `references/backlink-rules.md`「队列写入时机」）
10 [NEW] 追加操作日志：按格式写入 .logs/personal/{mis-id}.md（详见 `references/log-rules.md`「日志条目格式」的 ingest 类型）
```

> **2.5 步：模板加载**——AI 必须读取 `references/templates/_registry.yaml`，按 `templates[type]` 定位到对应 `.md` 模板文件，按其骨架整理正文。**禁止**用统一的「TL;DR + 详情」二段式覆盖所有 type。
>
> **2.6 步：glossary 去重前置**——仅当 type=glossary 时执行，详见下方「Step 2.6 glossary 去重前置」。
>
> **2.7 步：跨类型术语抽取**——所有 type 均执行。从输入正文中提取领域业务术语候选，检查 `glossary/` 是否已存在对应条目，未命中则创建 draft glossary stub 并将 `[[slug]]` 加入主文档 `related` 字段。详见下方「Step 2.7 跨类型术语抽取」。
>
> **8.5 步：质量门禁**——写入前对照 `_registry.yaml` 的 `required_sections` 列表逐项检查，并运行 `quality_gate` 文本校验（如 "glossary 必须含技术字段名映射"）。任一项不满足时**禁止**写入，向用户返回缺失清单。
>
> **9.5 步：索引更新**——写入成功后立即更新 `.index/` 对应的 idx 文件。若 idx 文件不存在则创建（含表头）。此步骤**不阻断**——即使 idx 更新失败也不影响 wiki 文档已写入的事实，仅输出 WARNING。详见 `references/index-rules.md`。
>
> **9.6 步：反向引用入队**——不即时修改已有文档（避免并发冲突），而是将回写请求缓冲到 `.pending-backlinks.yaml` 队列中，由后续 `health backlink-consume` 批量安全消费。详见 `references/backlink-rules.md`。
>
> **10 步：操作日志**——所有 in 操作均留痕。ask 类操作做 hash 脱敏，ingest 类操作记明文 title。详见 `references/log-rules.md`。

### Step 2.6 — glossary 去重前置（仅 type=glossary 时执行）

> 防止 glossary 唯一性被复制污染。在生成 tags / TL;DR / 正文前，先用 title 与同义关键词检索 glossary/，命中疑似同义条目时**强制**询问 --update 路径。

```bash
# 用提取的 title 与正文同义词候选做 rg 匹配
rg -i "^title:.*\b<title|候选别名 1|候选别名 2>\b" .knowledge/glossary/ --type md
```

候选别名提取：
1. 从输入正文中识别"也叫 / 又称 / 又名 / 即 / aka / ==" 后接的短语
2. 从 title 抽取英文专有名词（如"配送单(delivery_order)" → 候选 `delivery_order`、`delivery order`）
3. 从 tags 候选中取 ≥3 字的中文实体词

判定规则：

| 命中情况 | 动作 |
|---------|------|
| title 完全相同 | **强制中止**，输出已有文件路径，建议 `/knowledge-wiki in --update <slug>` |
| 命中文件 frontmatter `title` 与候选别名重叠率 ≥ 80% | **强制询问**：`[1] 改走 --update <已有 slug>  [2] 当作新术语强制创建（必须在 ## 边界 段落明确与 [[已有 slug]] 的差异）  [3] 中止` |
| 命中文件 ≥ 1 篇但重叠率 < 80% | **提示但不阻断**：列出疑似条目供用户参考，AI 在 Step 5 正文的 `## 边界（不是什么）` 段落自动用 `[[疑似 slug]]` 引用并说明差异 |
| 0 命中 | 正常进入 Step 3 |

> 重叠率算法：候选别名集合与已有 frontmatter `title` + 同义词与别名表中的"业务方/前端/后端/数据库/三方"列做集合交集 / 并集，比值 ≥0.8 视为高重叠。

### Step 2.65 — 全类型相似检测前置 [NEW]（所有 type 均执行）

> 借鉴 knowledge-evolution 的自动去重思路，在录入前对同 type 目录已有文档做快速相似度检测，降低知识重复率。与 Step 2.6 互补——2.6 是 glossary 专属的严格去重（title 完全相同则强制中止），2.65 是全类型的宽松提示（只提示不阻断，用户可选择继续）。

#### 执行条件

- 所有 type 均执行（含 glossary——作为 2.6 之后的第二道网，覆盖 2.6 未命中但正文高度重复的场景）
- 目标 type 目录无文件时跳过

#### 检测算法

用新录入的 `title + TL;DR 候选（Step 4 之前用输入正文前 100 字模拟）` 组合为查询文本，对同 type 目录已有文档逐一计算 Jaccard 相似度：

```python
def quick_similarity_check(query_text: str, target_dir: str) -> list:
    """对目标目录内的文档做快速相似度检测。"""
    query_words = extract_words(query_text)
    candidates = []
    for md_file in sorted(Path(target_dir).glob("*.md"))[:50]:  # 性能保护：最多 50 篇
        content = md_file.read_text()
        # 提取 title + TL;DR 段落（frontmatter title + ## TL;DR 到下一个 ## 之间）
        target_text = extract_title_and_tldr(content)
        target_words = extract_words(target_text)
        sim = len(query_words & target_words) / len(query_words | target_words) if (query_words | target_words) else 0
        if sim > 0.70:
            candidates.append((md_file, sim))
    return sorted(candidates, key=lambda x: -x[1])
```

> `extract_words` 函数定义见 `references/health-rules.md`「相似度算法」节（约第 401 行）：中文 bigram（相邻 2 字滑窗）+ 英文词汇（≥2 字符正则 `[a-zA-Z_]{2,}`），返回 `set`。

#### 阈值与判定

| Jaccard 相似度 | 判定 | 动作 |
|---------------|------|------|
| > 0.85 | 极高相似 | **提示 + 建议 --update**：展示相似文档，推荐走 `--update` 或确认差异后继续 |
| 0.70 ~ 0.85 | 中等相似 | **仅提示**：列出相似文档供参考，不阻断 |
| < 0.70 | 无关 | 静默通过 |

#### 输出模板（相似度 > 0.70 时）

```
⚡ 录入前相似检测

检测到同目录下 {N} 篇相似文档：
  ① {slug-a}.md — 相似度 0.88 — title: "{已有 title}"
  ② {slug-b}.md — 相似度 0.72 — title: "{已有 title}"

选择：
[1] 改走 --update <slug-a>（更新已有文档）
[2] 继续创建新文档（已知内容有差异）
[3] 中止
```

#### 设计约束

- **不阻断**：用户选 [2] 后正常继续 Step 2.7 → Step 3 → ...，不做二次拦截
- **性能保护**：同目录最多扫描前 50 篇文档（按 created 降序），超出时跳过旧文档
- **不重复检查**：若 Step 2.6 已命中并处理（如 glossary 严格去重已中止或跳转），则 Step 2.65 跳过
- **--update 场景跳过**：使用 `--update <slug>` 时天然是更新已有文档，跳过此步

---

### Step 2.7 — 跨类型术语抽取（所有 type 均执行）

> 确保黄金原则「术语唯一锚点在 glossary/，其他文档用 [[slug]] 引用，不重复定义」被结构化执行。非 glossary 类型录入时，自动检测正文中的领域业务术语，未在 glossary/ 注册的则创建 draft stub。

#### 候选术语提取

从以下三个来源提取候选术语（去重后合并）：

1. **title 中的领域实体词**——提取 title 中 ≥3 字的中文名词短语或英文专有名词（排除通用动词/形容词）
2. **tags 候选**——Step 3 将要生成的 tags 中 ≥3 字的实体词（此步与 Step 3 并行提取，不依赖 Step 3 输出）
3. **正文核心实体**——从输入正文中识别高频（≥2 次）或加粗/引号强调的领域名词短语

过滤规则：
- 排除通用技术术语（如 HTTP、API、JSON、gRPC、Redis、MySQL 等不构成业务领域知识的通用词）
- 排除 ≤2 字的短词（如"订单"例外：当其为核心业务对象时保留）
- 每次录入最多提取 **5 个**候选术语，超出时按正文出现频率降序取 Top 5

#### glossary 存在性检查

对每个候选术语执行：

```bash
rg -i "^title:.*\b<候选术语>\b" .knowledge/glossary/ --type md
```

同时检查候选术语的英文形式（如有）：

```bash
rg -i "^title:.*\b<english_form>\b" .knowledge/glossary/ --type md
```

#### 判定与执行

| 命中情况 | 动作 |
|---------|------|
| glossary/ 已存在匹配条目 | 仅将 `[[已有 slug]]` 加入主文档 `related` 字段，不重复创建 |
| glossary/ 无匹配 | 标记为「待创建 stub」，汇总后批量询问用户确认 |

#### 用户确认流程

当存在 ≥1 个待创建 stub 时，向用户展示：

```
检测到以下领域术语尚未在 glossary/ 注册：
  1. 渠道商 → 将创建 .knowledge/glossary/channel.md (draft stub)
  2. 配送商 → 将创建 .knowledge/glossary/delivery-provider.md (draft stub)

[1] 全部创建（推荐）
[2] 逐个确认
[3] 跳过，仅在 related 中标记 [[slug]]（不创建 glossary）
```

#### Stub 生成规格

每个 glossary stub 按 `references/templates/glossary.md` 模板生成，最小化填充：

```yaml
---
title: <术语原文>
type: glossary
tags: [<从主文档上下文推断 1-2 个 tag>]
owner: "<主文档 owner>"
created: <今日>
expires: never
status: draft
sources:
  - "由 <主文档 slug> 录入时自动抽取，{YYYY-MM-DD}"
related:
  - "[[<主文档 slug>]]"
---
```

正文部分：
- `## TL;DR`：一句话占位——"待补充完整定义，当前为自动抽取的 stub。"
- `## 定义`：从主文档上下文中提取该术语的 1-2 句描述（若正文有足够信息）；否则写"待补充"
- 其他 required_sections 标记为"待补充"（满足 8.5 门禁的最低要求由 stub 豁免——stub 不经过 8.5 门禁）

#### 约束

- 每次录入最多创建 **5 个** glossary stub（防止噪声膨胀）
- stub 不经过 8.5 质量门禁（因其本质为占位，由后续 `health audit` 升级时补全）
- stub 创建后自动将所有新 `[[slug]]` 追加到主文档的 `related` 字段
- 若用户选择 [3] 跳过，仍将 `[[slug]]` 写入主文档 `related`（标记引用意图，便于后续 `ask refs` 追溯）

### Step 6 — related 推荐 rg 模板

对每个 tag 并行搜索，按以下算法生成最多 5 条 related：

```bash
rg -l "^tags:.*\b<tag>\b" .knowledge/ --type md
```

算法：
1. 取所有 tag 命中文件的并集
2. 排除当前正在录入的目标文件自身（避免自引用）
3. 保留至少命中 2 个 tag 的文件作为候选
4. 候选数 > 5 时按命中 tag 数降序取 Top 5；数量 ≤ 5 时全部入选
5. 提取每条候选的 slug（通常即 basename 去 `.md`），生成 `[[slug]]` 引用
6. 候选为空时 frontmatter 的 `related` 字段写为空数组，不强制要求至少 1 条

### Step 7 — slug 生成规则

1. 中文 → 拼音（不带声调），用 `-` 连接。**优先用英文**：若 title 中括号内已含英文术语，直接取英文；如 `打印服务超时机制(print timeout)` → `print-timeout`
2. 英文 → 全小写，空格/下划线/标点 → `-`
3. 仅保留 `[a-z0-9-]`，连续 `-` 折叠为一个，去首尾 `-`
4. 长度 ≤ 50 字符；超长按词截断到最近的 `-`
5. 与 `.knowledge/` 已存在文件冲突时，依次追加 `-2`、`-3`，并在录入确认中提示用户考虑改用 `--update`

#### 拼音转换工具优先级（仅当 title 纯中文且无英文括号时）

按以下顺序探测，命中即用：

| 优先级 | 工具 | 一行命令（示例 title=`打印服务超时`） | 安装命令 |
|------|------|--------|---------|
| 1 | `python3 + pypinyin` | `python3 -c "from pypinyin import lazy_pinyin, Style; print('-'.join(lazy_pinyin('打印服务超时', style=Style.NORMAL)))"` → `da-yin-fu-wu-chao-shi` | `pipx install pypinyin` 或 `pip3 install pypinyin` |
| 2 | `node + pinyin` | `node -e "console.log(require('pinyin').default('打印服务超时',{style:0}).flat().join('-'))"` → `da-yin-fu-wu-chao-shi` | `npm i -g pinyin` |
| 3 | `bash + iconv`（仅 ASCII fallback） | `echo '打印服务超时' \| iconv -f utf-8 -t ascii//translit//ignore` 多数 locale 下输出空 → 走 P4 | macOS/Linux 自带 |
| 4 | **无库 fallback** | 剥离所有非 ASCII 字符后剩余 < 3 个英文词时，slug = `kb-` + ISO 日期（`YYYYMMDD`）+ `-` + 输入正文前 80 字 sha1 取前 6 位；如 `kb-20260521-a1b2c3` | 内置（无外部依赖） |

#### 执行算法

```python
def to_slug(title: str, body: str) -> str:
    # P0：优先 title 内已有英文（括号或全英）
    if has_english_in_title(title):
        return english_to_slug(extract_english(title))
    # P1-P2：探测 pypinyin / pinyin
    try: return pypinyin_slug(title)
    except: pass
    try: return node_pinyin_slug(title)
    except: pass
    # P3：iconv 兜底（多数中文输入会输出空，自动落到 P4）
    s = iconv_translit(title)
    if len(extract_words(s)) >= 3:
        return english_to_slug(s)
    # P4：哈希兜底（保证唯一不丢失内容）
    return f"kb-{today_yyyymmdd()}-{sha1(body[:80])[:6]}"
```

> **AI 必须**：在录入确认输出中明确告知用户最终走的是 P1-P4 哪一档；走 P4 时**强烈建议**用户改用 `--update <slug>` 或在 title 中补英文术语后重录。

---

## type 推断规则

按以下优先级从高到低匹配，命中即停：

| 优先级 | 判定条件 | type |
|--------|---------|------|
| 1 | 内容是单个术语/概念的定义或解释 | `glossary` |
| 2 | 含“架构”/“系统设计”/“整体方案”且描述当前状态 | `architecture` |
| 3 | 含“方案”/“实现”/“技术选型”且针对某需求 | `solution` |
| 4 | 含“决策”/“为什么选”/“ADR”/“取舍” | `adr` |
| 5 | 含“需求”/“PRD”/“验收”/“用户故事” | `requirement` |
| 6 | 含“流程”/“时序”/“步骤”/“规则”/“策略”/“计算”/“扣费”且描述业务流转或业务规则 | `flow` |
| 7 | 含“接口”/“API”/“字段”/“请求响应” | `api` |
| 8 | 含“表”/“模型”/“存储”/“索引”/“DDL”且描述数据结构 | `db` |
| 9 | 含“运维”/“告警”/“大促”/“保障”/“超时”/“阈值”/“配置” | `ops` |
| 10 | 含"故障"/"复盘"/"事故"/"根因"/"反例"/"踩坑"/"问题汇总"/"教训" | `case` |
| 11 | 含"综合分析"/"对比"/"关联发现"/"回流"（仅 --from-answer 模式） | `synthesis` |
| 兜底 | 无法匹配时 | `ops` |

> 业务规则（如小费计算、违约金扣除等带计算/判断逻辑的内容）统一作为 `flow` 处理，写入 `flows/` 目录，在所属流程文档的「计算 / 判断逻辑」章节内联维护。
>
> 会议纪要不再单独建模，需要沉淀的结论按其性质分流到 `design/`（决策类）、`requirements/`（需求类）或 `case/`（问题汇总类）。

## type 映射表（type → 写入目录 + 专属模板）

> **唯一权威源**：`references/templates/_registry.yaml`。下表为速查，字段语义、`layer`、`expires_days` 一律以注册表为准；本表与 `DESIGN.md` 的 L1/L2/L3 映射表均为它的派生视图，三处任一处变更必须同步改另外两处。

| type | 写入目录 | 模板文件 | 层级（layer） | 默认 expires |
|------|---------|---------|--------------|--------------|
| glossary | glossary/ | `templates/glossary.md` | L1 | never |
| architecture | design/ | `templates/architecture.md` | L1 | 180 天 |
| solution | design/ | `templates/solution.md` | L2 | 90 天 |
| adr | design/ | `templates/adr.md` | L1 | never |
| requirement | requirements/ | `templates/requirement.md` | L1 | 90 天 |
| flow | flows/ | `templates/flow.md` | L2 | 90 天 |
| api | apis/ | `templates/api.md` | L3 | 90 天 |
| db | db/ | `templates/db.md` | L3 | 90 天 |
| ops | ops/ | `templates/ops.md` | L3 | 90 天 |
| case | case/ | `templates/case.md` | L2 | 365 天 |
| synthesis | synthesis/ | `templates/synthesis.md` | L2 | 60 天 |

**新增/调整 type 的标准流程**：① 改 `_registry.yaml` 加条目（含 file/target_dir/layer/expires_days/required_sections/quality_gate）→ ② 创建 `references/templates/{type}.md` 模板 → ③ 同步本文件 type 推断规则与本表 → ④ 同步 `DESIGN.md` 第二章对应层的「在 knowledge-wiki 中的映射」表。任一步骤遗漏会导致 8.5 门禁加载失败或路由错乱。

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

### 字段填写算法（AI 必须严格执行）

```python
# created：录入当日（UTC+8）
created = today()                                # 例：2026-05-21

# expires：基于 created + _registry.yaml.expires_days
expires_days = registry.templates[type].expires_days
if expires_days == "never":
    expires = "never"                            # 字符串 never，不写日期
else:
    expires = created + timedelta(days=expires_days)
# 例：type=ops, expires_days=90, created=2026-05-21 → expires=2026-08-19

# tags：3-5 个，从正文核心实体词提取
#   - 必含：业务域（如 print/delivery/order）
#   - 必含：技术对象（如 timeout/fallback/queue）
#   - 排除：通用副词（如 全部/所有/重要）
# 例：tags: [print, timeout, fallback]

# owner：录入用户的 mis-id，前缀 @
owner = "@" + current_mis_id()                   # 例：@hanqiang

# sources：至少 1 条，按输入类型选格式
#   - 文本输入："手工录入 @{mis-id} {YYYY-MM-DD}"
#   - URL 输入："{原始URL}（同步于 {YYYY-MM-DD}）"
#   - 文件输入："{相对路径}（提取于 {YYYY-MM-DD}）"

# status：新录入恒为 draft（health audit 才升级）
status = "draft"
```

> AI 严禁填占位符 `{YYYY-MM-DD}`、`{mis-id}` 进入正式文档。占位符仅供模板展示，写入前必须按上方算法替换为真实值。

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

## --from-answer "{描述}"：Ask 回流综合录入

> 将 AI 对话中的综合分析回答沉淀为 `synthesis` 类型知识文档。详见 `ask-rules.md`「Ask 回流提示」节触发条件。

### 触发来源

由 `ask` 回答末尾的回流提示触发：
```
💡 此回答综合了 ≥2 篇文档的知识，是否录入为新的知识条目？
  /knowledge-wiki in --from-answer "{用户问题的简短描述}"
```

### 14 步流程变体（与标准 in 的差异）

```
1. 提取 title ← 从 --from-answer 后的描述参数提取（若为空则用 derived_question 首 30 字）
2. type = synthesis（跳过 type 推断，直接确定）
2.5 加载模板：references/templates/synthesis.md
2.6 [跳过] glossary 去重不适用于 synthesis
2.7 [跳过] 跨类型术语抽取不适用于 synthesis（synthesis 是派生文档，不创建新 stub）
3. 提取 tags ← 合并所有 derived_from 文档的 tags，去重后取频率最高的 3-5 个
4. 生成 TL;DR ← 从 ask 回答中提取核心结论（一句话综合）
5. 按 synthesis.md 模板骨架生成正文：
   - ## TL;DR ← Step 4 的内容
   - ## 综合问题 ← derived_question 原文
   - ## 来源文档 ← 列出所有 derived_from slug 及其 title/status
   - ## 综合结论 ← ask 回答的核心分析内容
   - ## 对比分析（可选）← 若回答中有跨文档对比
   - ## 关联发现（可选）← 若回答中有意外关联
   - ## 局限与假设（可选）← 综合分析的边界条件
6. related ← derived_from 中的所有 slug 自动作为 related
7. 生成 slug ← 从 title 按标准规则生成
8. 若目标文件已存在 → 同标准流程询问
8.5 质量门禁增强（synthesis 专属）：
   ① 标准门禁：required_sections 齐全
   ② 来源数量：derived_from ≥ 2 篇
   ③ 来源状态：所有 derived_from slug 对应文档 status ≠ deprecated
   ④ 禁止套娃：derived_from 中不能包含 synthesis 类型文档
   任一项不满足 → 拒绝创建，输出具体原因
9. 写入 .knowledge/synthesis/{slug}.md
9.5 更新分段索引：追加到 .index/synthesis.idx.md
9.6 反向引用入队：对 derived_from 中每个 slug 生成 pending backlink
10 追加操作日志（action: ingest, detail 含 from_answer: true）
```

### frontmatter 额外字段

synthesis 类型在标准 frontmatter 基础上**必须**额外包含：

```yaml
derived_from:                     # 必填：所有被综合的原始文档 slug 列表
  - "ops/print-timeout"
  - "flows/fallback-strategy"
derived_question: "打印服务超时后如何 fallback？与配送超时的异同？"  # 必填：触发此综合分析的原始问题
```

### sources 字段格式

```yaml
sources:
  - "由 /knowledge-wiki ask '打印超时 fallback 机制' 综合生成，2026-05-26"
```

### 录入确认输出

```
✓ 已写入 .knowledge/synthesis/print-timeout-fallback-comparison.md

标题：打印超时 Fallback 对比分析 | 类型：synthesis | 过期：2026-07-26
来源文档：ops/print-timeout + flows/fallback-strategy（2 篇）
原始问题：打印服务超时后如何 fallback？与配送超时的异同？
关联：[[print-timeout]] [[fallback-strategy]]

⚠️ synthesis 文档 60 天后过期，届时 health rot 会提示审查
当前为 draft，确认准确后运行：
  /knowledge-wiki health audit print-timeout-fallback-comparison
```

### 禁止二次回流

若用户在 `ask` 中命中了 synthesis 类型文档，**不显示**回流提示。原因：synthesis 是派生知识，再次回流会产生"知识套娃"（A→综合B→综合C→...），降低知识库信噪比。

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