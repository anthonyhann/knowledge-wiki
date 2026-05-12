# 知识库目录结构（.knowledge/）

```
.knowledge/
├── README.md              # 双受众入口：顶部给 AI，底部给人类
├── CLAUDE.md              # AI 协作整体契约 + 禁止行为清单（Agent 每次必读）
├── AGENTS.md              # AI 专用地图：路由 + 权限（硬限 100 行）
├── AGENT-ROUTING.md       # Agent 文件权限路由表
├── CONTRIBUTING.md        # 人类参与指南（AI 无需读取）
├── SCHEMA.md              # 统一规范源（结构定义、命名约定、标签体系、检索配置）
├── index.md               # Wiki 总入口
├── graph.json             # 【CI 生成】知识图谱数据
├── graph.html             # 【CI 生成】本地可视化
├── dashboard.md           # 【CI 生成】知识库全局进度看板
├── .kb-meta/              # 【全部 CI 生成】chunks.jsonl / backlinks.json / stats.json / eval-results.json / sources.json
├── strategy/              # 总纲、黄金原则、Roadmap（低频，负责人审核后修改）
├── docs/                  # 内容层，按项目生命周期分区
│   ├── requirements/      # PRD、需求文档、UI 设计图
│   ├── design/            # 技术方案、架构设计、流程图
│   ├── implementation/    # ADR、接口约定
│   ├── quality/           # 测试方案、验收文档
│   ├── release/           # 上线文档、回滚方案
│   ├── exec-plans/        # 执行计划（active/ + completed/）
│   ├── domain/            # 业务领域知识（按子领域目录）
│   └── generated/         # 【CI 生成】db-schema / api-changelog / dependency-graph
├── assets/eval/           # 评测数据集
├── playbooks/             # 锁定版任务契约（canonical，AI 只读）
├── meetings/              # 周会记录
├── people/{user-id}/      # 个人上下文（context.md / decisions.md / prefs.md）
├── processes/scripts/     # 可执行脚本（kb-sync.sh / generate-dashboard.py 等）
├── references/            # 第三方库 llms.txt 格式
├── pages/                 # Wiki 主页面（concepts/ entities/ processes/ sources/）
├── inbox/                 # 待处理草稿
└── archives/              # 只读，审计记录
```
