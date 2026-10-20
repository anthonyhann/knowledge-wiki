# 代码提交知识文档生成规则（docs 子命令使用）

> 由 `/knowledge-wiki docs` 子命令使用。定义代码变更分析引擎、变更分类映射、已有文档匹配规则、逐条问询交互流程。SKILL.md 仅保留入口与索引，本文件是唯一权威源。

---

## 概述

`docs` 子命令在代码提交时自动分析代码变更（diff），结合 commit message 和已有知识库文档，识别：
1. **需要更新的已有文档**——代码变更导致现有知识文档过时
2. **可新增的知识文档**——代码变更引入了新的知识点尚未文档化

分析结果以 **逐条问询** 方式与用户交互确认，用户可对每条分析结果独立决策（录入/跳过/编辑后录入）。

---

## 子命令矩阵

| 子命令 | 行为 | 输入源 |
|--------|------|--------|
| `docs` | 分析最近一次 commit 的变更 | `git show HEAD --stat` + `git show HEAD` |
| `docs --staged` | 分析当前 staged 文件（commit 前/hook 中止后使用） | `git diff --cached` |
| `docs --last <N>` | 分析最近 N 次 commit 的累积变更（默认 N=1） | `git log -N --oneline` + `git diff HEAD~N..HEAD` |
| `docs --range <ref1>..<ref2>` | 分析指定 commit 范围 | `git diff <ref1>..<ref2>` |
| `docs --pending` | 查看/处理 `.pending-docs.yaml` 中暂存的待处理项 | 读取 `.knowledge/.pending-docs.yaml` |

### 通用参数

| 参数 | 说明 |
|------|------|
| `--dry-run` | 仅输出分析结果，不进入交互确认（用于 CI 或预览） |
| `--auto-skip-minor` | 自动跳过影响度 < 0.3 的建议（减少打扰） |

---

## 分析引擎（AI 执行步骤）

### Step 1：获取变更数据

```bash
# --staged 模式
git diff --cached --stat
git diff --cached

# 默认模式（最近 commit）
git show HEAD --stat
git show HEAD

# --range 模式
git diff <ref1>..<ref2> --stat
git diff <ref1>..<ref2>
```

同时获取 commit message：

```bash
git log -1 --format="%s%n%n%b" HEAD
```

### Step 2：变更文件分类与过滤

**过滤规则**（以下文件不参与分析）：

| 排除条件 | 原因 |
|---------|------|
| `.knowledge/` 目录下的文件 | 知识库自身变更不触发 |
| `*_test.*` / `*.test.*` / `*.spec.*` / `test_*` | 纯测试用例文件（与被测代码镜像，无独立知识价值；v2.1.0 起 `tests/` 目录的**基础设施变更**不再排除，改映射 `test` type，见 Step 4） |
| `*.md` / `*.txt` / `*.json`（非 schema） | 纯文档/配置 |
| `go.sum` / `package-lock.json` / `yarn.lock` | 依赖锁文件 |
| `*.min.js` / `*.min.css` / `dist/` / `build/` | 构建产物 |
| 图片/字体/二进制文件 | 非代码资产 |

**保留的有效代码文件扩展名**：

```
go, php, ts, tsx, js, jsx, py, java, rs, rb, vue, proto, api, sql, graphql, yaml（仅 k8s/docker 相关）
```

### Step 3：变更意图提取

从以下三个来源综合提取变更意图：

1. **Commit message**：提取主要动作（feat/fix/refactor/chore 等）和涉及模块
2. **新增文件名**：从路径和命名推断功能（如 `handler/fastexpress.go` → 极速配送相关接口）
3. **Diff 内容**：提取新增的关键结构（函数签名、路由定义、SQL DDL、proto message 等）

### Step 4：变更分类 → type 映射

对每个有效变更文件/变更块，按以下规则分类：

| 代码变更特征 | 推断 type | 生成方向 |
|-------------|-----------|----------|
| 新增 route/handler/controller/endpoint 文件或函数 | `api` | 接口文档草稿 |
| 新增 migration/DDL/model/entity/schema 文件 | `db` | 数据模型文档草稿 |
| 新增或修改 service/logic/usecase 层核心流程 | `flow` | 流程变更说明 |
| 新增 .proto/.api 定义文件 | `api` | 接口规范文档 |
| 新增配置/运维/deploy/docker/k8s 文件 | `ops` | 运维配置文档草稿 |
| 新增顶层模块/服务目录/独立 package | `architecture` | 架构变更说明 |
| 大规模重构（rename/move ≥ 5 个文件） | `adr` | 决策记录 |
| 含 "fix" + 复盘注释/临时绕行标记 | `case` | 问题记录 |
| tests/ 下测试基础设施（autoload/bootstrap/phpunit 配置/mock 工具）或测试指南/规范文档变更 | `test` | 测试知识文档草稿（v2.1.0；仅限基础设施与规范，用例文件本身仍被 Step 2 排除） |
| 新增中间件/拦截器/通用工具函数 | `solution` | 技术方案说明 |

**优先级**：当同一文件匹配多条规则时，取优先级最高的（表中从上到下优先级递减）。

**聚合规则**：同 type 的多个小变更聚合为一条建议（如新增 3 个 handler → 聚合为一条 api 文档建议，而非 3 条）。

### Step 5：已有文档匹配

从 diff 中提取关键实体词用于匹配：

```bash
# 提取关键词源
# 1. 新增/修改的函数名、类名、结构体名
# 2. 路由路径（如 /api/fastexpress/createOrder）
# 3. 表名/model 名
# 4. 配置 key
# 5. commit message 中的业务实体词

# 用提取的关键词搜索知识库
rg -l "关键词1|关键词2|关键词3" .knowledge/ --type md -g "!.index/" -g "!.logs/"
```

匹配到的文档进一步判断：

| 匹配情况 | 判定 | 动作 |
|---------|------|------|
| 文档 title/tags 命中且 diff 修改了对应代码逻辑 | **需要更新** | 纳入"需要更新"列表 |
| 文档 title/tags 命中但 diff 仅为 bugfix 小改动 | **可能需要更新** | 低优先级纳入，影响度标记 < 0.3 |
| 文档正文引用的接口/表/配置被修改 | **需要更新** | 纳入"需要更新"列表 |
| 无匹配但变更符合 Step 4 的 type 映射 | **可新增** | 纳入"可新增"列表 |

### Step 6：影响度评分

对每条建议计算影响度分数（0-1），用于排序和 `--auto-skip-minor` 过滤：

```python
def calc_impact(suggestion):
    score = 0.0
    # 新增文件权重高
    if suggestion.has_new_files:
        score += 0.4
    # 代码行数贡献
    if suggestion.added_lines >= 100:
        score += 0.3
    elif suggestion.added_lines >= 50:
        score += 0.2
    elif suggestion.added_lines >= 20:
        score += 0.1
    # 涉及公共接口（exported/public）
    if suggestion.has_public_api_change:
        score += 0.2
    # commit message 明确提及相关功能
    if suggestion.keyword_in_commit_msg:
        score += 0.1
    return min(score, 1.0)
```

### Step 7：生成建议列表

按影响度降序排列，输出两类列表：

1. **需要更新**的已有文档列表（附变更原因 + 建议更新内容预览）
2. **可新增**的知识文档草稿列表（附推断的 type/title/TL;DR 草稿）

---

## 逐条问询交互流程

### 总体原则

1. **逐条展示**：每次只输出一条分析结果，等用户输入选择后再展示下一条
2. **可中断**：任何时候用户选择"全部跳过"即终止后续问询
3. **顺序**：先展示"需要更新"的文档（按影响度降序），再展示"可新增"的文档
4. **超时保护**：若分析结果超过 10 条，先输出 Top 5（按影响度排序），然后询问"是否继续查看剩余 N 条？"
5. **编辑模式**：用户选"编辑后录入"时，输出完整草稿内容，用户可直接修改后确认

### 总览摘要（首次输出）

分析完成后，先输出一次总览摘要：

```
📖 [knowledge-wiki docs] 代码变更知识分析
═══════════════════════════════════════════════════

Commit: {commit_message_first_line}
变更统计: {N} files changed, +{added} -{deleted}
分析结果: 发现 {update_count} 篇需要更新 + {new_count} 篇可新增，将逐条与你确认

═══════════════════════════════════════════════════
```

### 问询模板——更新已有文档

```
─── [{current}/{total}] 需要更新 ──────────────────

📄 {file_path}
   当前标题: {existing_title}
   变更原因: {reason_description}
     {具体变更点列表，每行一个 bullet}
   
   建议更新内容预览:
   ┌─────────────────────────────────────────┐
   │ {diff_preview_lines}                    │
   │ ...（共 +{N} 行）                        │
   └─────────────────────────────────────────┘

请选择操作:
[1] 更新此文档
[2] 跳过
[3] 编辑后更新（进入编辑模式）
[4] 全部跳过，结束本次分析
```

### 问询模板——新增文档

```
─── [{current}/{total}] 建议新增 ──────────────────

📝 新文档草稿
   推断标题: {inferred_title}
   推断类型: {inferred_type}
   推断路径: .knowledge/{target_dir}/{slug}.md
   
   TL;DR 草稿:
   {tldr_draft_50_100_words}
   
   正文预览（前 10 行）:
   ┌─────────────────────────────────────────┐
   │ {body_preview_lines}                    │
   └─────────────────────────────────────────┘

请选择操作:
[1] 录入此文档（走标准 in 流程）
[2] 跳过
[3] 编辑后录入（可修改标题/类型/内容后再录入）
[4] 全部跳过，结束本次分析
```

### 编辑模式

用户选 [3] 编辑后录入/更新时：

```
进入编辑模式。以下为完整草稿，可直接修改：

───── 可编辑区域 ─────────────────────────────────

标题: {title}（可修改）
类型: {type}（可修改，可选: glossary/architecture/solution/adr/requirement/flow/api/db/ops/case）

## TL;DR
{完整 TL;DR 草稿}

## 正文
{完整正文草稿}

───── 编辑结束 ─────────────────────────────────

确认录入请输入 [1]，放弃修改请输入 [2]
```

### 完成总结

所有问询结束后输出总结：

```
═══════════════════════════════════════════════════
✓ 知识文档处理完成

  已更新: {N} 篇
    • {path1}（+{lines} 行）
    • {path2}（+{lines} 行）
  已录入: {N} 篇
    • {path1}（draft）
    • {path2}（draft）
  已跳过: {N} 篇
    • {path1}
  已暂存: {N} 篇（写入 .pending-docs.yaml，稍后可用 docs --pending 处理）
    • {path1}

💡 新录入文档为 draft 状态，确认准确后运行:
   /knowledge-wiki health audit {slug}
═══════════════════════════════════════════════════
```

---

## 确认后的执行流程

### 更新已有文档

用户选 [1] 更新时，等效于执行：

```
/knowledge-wiki in --update <existing_slug>
```

自动填入：
- 更新内容 = AI 根据 diff 生成的变更文本
- sources 追加 = `"代码变更自动检测，commit {short_hash} {YYYY-MM-DD}"`

走标准 `--update` 三选一流程（覆盖/追加版本节/中止），但 AI 自动推荐 [1] 覆盖。

### 新增文档

用户选 [1] 录入时，等效于执行：

```
/knowledge-wiki in <AI 生成的结构化内容>
```

走标准 14 步结构化流程，但以下步骤已由 docs 分析引擎预计算：
- Step 1（title）：使用推断的 title
- Step 2（type）：使用推断的 type
- Step 4（TL;DR）：使用预生成的草稿
- Step 5（正文）：使用预生成的模板骨架正文

其余步骤（2.5 模板加载、2.65 相似检测、2.7 术语抽取、6 related、7 slug、8.5 门禁、9.5 索引、9.6 backlink、10 日志）正常执行。

### sources 字段格式（docs 来源）

```yaml
sources:
  - "代码变更自动检测，commit {short_hash}（{YYYY-MM-DD}）"
  # 若 commit message 引用了 PR/MR：
  - "PR #{pr_number}: {pr_title}（{YYYY-MM-DD}）"
```

---

## .pending-docs.yaml 暂存机制

当用户在 prepare-commit-msg hook 阶段选择"稍后处理"时，将分析结果缓存到 `.knowledge/.pending-docs.yaml`：

```yaml
# .knowledge/.pending-docs.yaml
# 由 prepare-commit-msg hook 或 docs 子命令写入
# 由 docs --pending 消费
pending:
  - commit: "abc1234"
    date: "2026-05-21"
    message: "feat(delivery): 新增极速配送渠道对接"
    suggestions:
      - type: update
        target: "apis/fast-express-api.md"
        reason: "新增 3 个接口 endpoint"
        impact: 0.85
      - type: new
        inferred_type: solution
        inferred_title: "极速配送渠道对接方案"
        inferred_slug: "fast-express-adapter"
        impact: 0.72
```

### docs --pending 消费流程

1. 读取 `.pending-docs.yaml`
2. 按 `date` 降序（最新的优先）展示
3. 逐条问询（同标准流程）
4. 处理完的条目从 yaml 中移除
5. 全部处理完后删除文件

---

## 阈值与行为控制

| 条件 | 行为 |
|------|------|
| 有效代码变更行 < 20 且无新增文件 | 不触发分析（hook 静默退出） |
| 分析结果 = 0 条建议 | 输出"未发现需要文档化的变更"，正常退出 |
| 分析结果 > 10 条 | 按影响度排序，先展示 Top 5，询问是否继续 |
| `--auto-skip-minor` 启用时影响度 < 0.3 | 自动跳过，仅在总结中标注 |
| 已有 `.pending-docs.yaml` 且条目 > 20 | 提示用户先处理积压：`/knowledge-wiki docs --pending` |

---

## 与现有机制的关系

| 现有机制 | 关系 |
|---------|------|
| `commit-msg` hook（`[kb]` 标记） | 互补：commit-msg 处理用户主动标记；prepare-commit-msg 处理自动检测 |
| `in` 子命令 | 复用：docs 确认后调用标准 `in` / `in --update` 流程 |
| `health lint` | 互补：docs 关注增量变更；lint 关注全量一致性 |
| `post-merge` hook | 互补：post-merge 关注他人的变更合入；prepare-commit-msg 关注自己的变更提交 |

---

## 执行约束

### 🔴 核心不变量

| # | 约束 | 说明 |
|---|------|------|
| D1 | **不阻断 commit** | prepare-commit-msg hook 仅输出提示，`exit 0` 不阻断；分析和确认在 commit 后由 `docs` 子命令完成 |
| D2 | **复用 in 流程** | 所有写入操作必须走标准 14 步 `in` 流程（含 8.5 门禁、索引更新等），不走捷径 |
| D3 | **用户决策权** | 每条建议必须经用户明确确认才执行写入，禁止自动写入 |
| D4 | **逐条问询** | 一次只展示一条，等用户决策后再展示下一条；禁止批量展示要求用户批量决策 |
| D5 | **可中断** | 任何环节用户选"全部跳过"即立即终止，不再展示后续条目 |

### 🟡 扩展行为

| # | 约束 | 说明 | 降级策略 |
|---|------|------|---------|
| E1 | **影响度排序** | 按影响度高→低展示 | 无法计算时按文件路径字母序 |
| E2 | **pending 缓存** | hook 中止时写入 `.pending-docs.yaml` | 写入失败不影响 commit |
| E3 | **PR 信息增强** | 尝试从 commit message 提取 PR 信息 | 无 PR 信息时仅用 commit hash |
| E4 | **相似检测复用** | 新增文档时复用 Step 2.65 相似检测 | 检测失败不阻断录入 |
