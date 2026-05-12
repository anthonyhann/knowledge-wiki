# Lint 规则与自动修复建议

| 检查类型 | 级别 | 条件 | 自动修复建议 |
|----------|------|------|----------|
| 断裂链接 | ERROR | `[[target]]` 不存在 | 列出候选：`rg -l "{target}" pages/` → 提示修正链接或创建新页 |
| 缺失 frontmatter | ERROR | 任意遗漏 | 输出缺失字段名 + 默认值建议，用户确认后自动补全 |
| deprecated 仍被引用 | ERROR | 任意 | 查找 `links.supersedes` 替代页，提示替换为 `[[new-slug]]` |
| 文件行数超限 | ERROR | > 800 行 | 按 heading 拆分建议：列出拆分点 + 新页slug预览 |
| 孤立页面 | WARNING | 无入站链接 | 建议在 index.md 添加入口，或在相关页面插入 WikiLink |
| 缺失 TL;DR | WARNING | stable 页面 | 基于正文前 200 字自动生成候选 TL;DR，用户确认后插入 |
| last-reviewed 过期 | WARNING | > 90 天 | 输出 `请审阅: {slug}，上次审阅: {date}` + 更新 last-reviewed 命令 |
