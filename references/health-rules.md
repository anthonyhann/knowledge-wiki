# 维护（health）详细规则

> 由 `/knowledge-wiki health` 使用。SKILL.md 仅保留入口与索引，本文件是唯一权威源。

---

## 综合报告（health）

```
📊 知识库健康报告（2026-05-12）

文档总数：47 篇（active: 32  draft: 10  deprecated: 5）

[腐烂检测]  EXPIRED 3 篇 | WARNING 5 篇
[覆盖率]    未覆盖模块：goods / queue / redis3
[外部源]    3 个源，上次扫描 22 天前

/knowledge-wiki health rot       查看过期详情
/knowledge-wiki health scan      检查外部源
/knowledge-wiki health coverage  查看覆盖率
```

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

---

## scan（外部源扫描）

> **工具路由**：scan 中每个外部源 URL 统一走 agent-browser 浏览器工具。详见 `url-handling.md`。

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
  expires → 今日 +90 天
  sources 追加："人工确认 @who YYYY-MM-DD"

选 [2]：跳转 /knowledge-wiki in --update <slug>
选 [3]：跳转 /knowledge-wiki health deprecate <slug>
```

---

## deprecate `<slug>`（标记废弃）

```
1. rg 查找所有引用该 slug 的文档
2. 列出引用处，确认后：
   - status → deprecated
   - 引用处追加：<!-- deprecated: [[<slug>]] 已废弃，请更新引用 -->
```

废弃前必须处理引用，防止悬空链接。

