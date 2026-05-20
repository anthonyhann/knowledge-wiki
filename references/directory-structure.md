# .knowledge/ 目录框架与根文件模板

> `init` 子命令初始化时使用的静态资产。SKILL.md 主流程仅需引用本文件，不重复展开。

---

## 目录树（11 个业务目录 + 4 个根文件）

```
.knowledge/
├── README.md               ← 双受众入口（顶部给 AI，底部给人类）
├── CLAUDE.md               ← AI 协作契约 + 禁止行为 + 黄金原则
├── AGENTS.md               ← AI 地图（≤50 行）
├── .sources.yaml           ← 外部知识源注册表
│
├── glossary/               ← 术语词典（全局唯一锚点，最先写）
├── design/                 ← 架构/技术方案/决策（type 字段区分）
├── requirements/           ← 需求文档、PRD、验收标准
├── flows/                  ← 核心业务流程
├── apis/                   ← 接口约定、字段映射
├── data/                   ← 数据模型、存储
├── ops/                    ← 运维、告警、大促保障
├── incidents/              ← 故障复盘
├── bizrules/               ← 业务规则（运营+技术共用）
├── meetings/               ← 会议记录
└── people/                 ← 个人上下文（AI 只读）
    └── {user-id}/
        ├── context.md
        ├── decisions.md
        └── prefs.md
```

### 目录职责速查

| 目录 | 写入 type | 适用场景 |
|------|----------|---------|
| glossary/ | glossary | 术语、概念定义（全局唯一） |
| design/ | architecture / solution / adr | 架构现状 / 技术方案 / 决策记录 |
| requirements/ | requirement | PRD、feature spec、验收标准 |
| flows/ | flow | 业务流程、时序 |
| apis/ | api | 接口约定、字段映射 |
| data/ | data | 数据模型、存储设计 |
| ops/ | ops | 运维、告警、大促保障、超时阈值 |
| incidents/ | incident | 故障复盘、根因分析 |
| bizrules/ | bizrule | 业务规则、计费策略 |
| meetings/ | meeting | 会议记录、对齐结论 |
| people/{user-id}/ | — | 个人上下文（AI 只读） |

---

## 根文件模板

### README.md

```markdown
# 知识库

> 双受众入口：顶部给 AI 检索，底部给人类阅读。

## AI 快速导航
- 术语查询 → glossary/
- 系统架构/方案/决策 → design/（type: architecture|solution|adr）
- 业务流程 → flows/
- 接口约定 → apis/
- 数据模型 → data/
- 运维手册 → ops/
- 故障复盘 → incidents/
- 业务规则 → bizrules/
- 需求文档 → requirements/
- 会议记录 → meetings/
- 个人上下文 → people/{user-id}/（只读）

## 人类阅读指引

新人入职先读 glossary/ 和 design/architecture-*；日常通过 `/knowledge-wiki ask` 查询。
```

### CLAUDE.md

```markdown
# AI 协作契约

## 黄金原则
1. 所有知识必须有 sources 字段，无来源不写
2. 术语唯一锚点在 glossary/，其他文档用 [[slug]] 引用，不重复定义
3. AI 禁止修改 status: canonical 的文档
4. AI 写入一律放入对应目录，不新建目录结构

## 禁止行为
- 引用 status: deprecated 的文档
- 修改 people/ 下任何文件
- 在非 glossary/ 目录重复定义已有术语
- 在 SKILL 文档外内联生成 hook 脚本（必须复制 references/scripts/）

## 检索优先级
canonical > active > draft > deprecated（deprecated 禁引用）
```

### AGENTS.md（≤50 行）

```markdown
# 知识库 AI 地图

查询：/knowledge-wiki ask "<问题>"
录入：/knowledge-wiki in <内容>
维护：/knowledge-wiki health

## 检索优先级
canonical > active > draft > deprecated（禁引用）

## 写入规则
新内容 → 对应目录，status: draft → 人工 /knowledge-wiki health audit 升级
术语 → 必须在 glossary/ 中唯一定义
```

### .sources.yaml

```yaml
sources: []
# 通过 /knowledge-wiki in source add <url> 添加，结构：
#   - id: print-api-doc
#     name: 打印接口文档
#     url: https://docs.apipost.net/docs/detail/xxx
#     tracked_by: "@hanqiang"
#     last_hash: ""
#     last_synced: ""
#     status: active           # active | stale | error
#     related_docs:
#       - apis/print-api.md
```

---

## 创建顺序（init Step 1-2 内部使用）

1. 在仓库根 `mkdir -p .knowledge/{glossary,design,requirements,flows,apis,data,ops,incidents,bizrules,meetings,people}`
2. 写入 4 个根文件：README.md / CLAUDE.md / AGENTS.md / .sources.yaml（内容如上）
3. 不预创建 people/{user-id}/ 子目录，由用户首次写入个人上下文时按需建立

