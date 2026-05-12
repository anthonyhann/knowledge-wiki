# Ingest Agent 处理流程

## Step 1：内容分析

- 输入：原始文本/URL 抓取结果
- 操作：
  - 按 heading 分段，提取所有 h1-h3 标题作为候选概念
  - 识别文档类型：
    - 含 CREATE TABLE / 字段说明 → `type: entity`
    - 含 "背景""方案""结论" → `type: adr`
    - 含 Q&A 对 ≥3 组 → `type: faq`
    - 含步骤/流程/SOP → `type: process`
    - 其他 → `type: concept`
  - 提取关键实体名词（出现 ≥2 次的专有名词）作为 WikiLink 候选
- 输出：文档类型 + 候选概念列表 + WikiLink 候选

## Step 2：草稿生成（写入 inbox/）

- 输入：Step 1 的分析结果
- 操作：
  - 为每个顶层概念生成 `inbox/{slug}.md`
  - frontmatter 字段：title / type / status:draft / created / tags / sources
  - TL;DR：用 50-100 词概括核心信息（禁止"本文介绍"等套话）
  - 正文按标准模板（定义→属性→示例→相关页面→引用来源）
- 输出：inbox/ 下 N 个草稿文件

## Step 3：链接发现

- 输入：所有 inbox/ 草稿 + 已有 pages/
- 操作：
  - 对 Step 1c 的候选名词，在 pages/ 中 grep 匹配已有页面
  - 匹配成功 → 插入 `[[WikiLink]]`；未匹配 → 标注 `<!-- suggested: 新建页面? -->`
  - 更新 `.kb-meta/backlinks.json`（source→target 追加）
- 输出：草稿中的 WikiLink 已填充

## Step 4：索引更新

- 输入：新生成的草稿列表
- 操作：
  - `graph.json` 追加 nodes（id/label/type/tags/status/tldr）
  - `graph.json` 追加 links（基于 WikiLink 关系）
  - `index.md` 在对应分类下追加新入口
- 输出：graph.json 和 index.md 已更新

## 异常处理

| 场景 | 触发条件 | 处理方式 |
|------|----------|----------|
| 超大文件 | 单文件 > 500KB 或 > 2000 行 | 按 heading 拆分为多页，每页 ≤ 800 行；无 heading 则按 500 行分段 |
| 网络中断 | agent-browser 超时 > 30s | 重试 1 次；仍失败→保存已提取部分到 inbox/ 并标注 `<!-- partial: 中断于第N节 -->` |
| 格式无法解析 | OCR 失败 / 加密 PDF / 二进制文件 | 跳过并输出：`⚠ 无法处理 {文件名}，原因：{错误}`，继续处理其他文件 |
| 重复导入 | inbox/ 或 pages/ 中已存在同 source URL | 询问用户：`该源已导入过，选择：[1]跳过 [2]覆盖更新 [3]并存` |
| graph.json 损坏 | JSON 解析失败 | 备份 `graph.json.bak.{timestamp}` → 从 pages/ 重建 nodes/links → 提示用户确认 |
| .kb-meta/ 缺失 | chunks.jsonl 等文件不存在 | 自动重建空文件并提示：`⚠ .kb-meta/ 已重建，建议重新执行 /knowledge-wiki eval` |

## 代码提取规则

- 每个模块/包 → 一个 `entity` 类型页面
- 公开接口/函数 → 页面内章节（复杂度高时单独建页）
- 关键注释（`// NOTE:` `// WHY:` `// FIXME:`）→ `synthesis` 草稿
