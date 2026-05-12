# AGENTS.md / CLAUDE.md 规范

## CLAUDE.md（AI 协作契约，每次必读）

**禁止行为：**
- 禁止修改 canonical 文件 / archives/ / .kb-meta/ / generated/ / graph.json / graph.html / dashboard.md
- 禁止引用 deprecated 文档（改用 links.supersedes）
- 禁止未 lint 通过即将 draft 升为 active

**写入规则：** 新内容 → inbox/ → 人工确认后升级

**读取优先级：** canonical > active > draft > deprecated（降权）

## AGENTS.md（AI 专用地图，≤100 行）

含快速索引 + Agent 权限沙盒表（各 Agent 的可读/可写/禁写范围）+ 工作流入口。
超限时详情移至 `AGENT-ROUTING.md`。
