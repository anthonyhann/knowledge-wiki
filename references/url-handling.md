# URL 处理详细规则

> 由 `/knowledge-wiki in <url>` 与 `/knowledge-wiki health scan` 共享。SKILL.md 仅保留铁律表与索引，本文件是唯一权威源。

---

## 工具选型铁律（按 URL 域名硬路由）

| URL 域名 | 必走工具 | 备注 |
|---------|---------|------|
| xxx.feishu.cn / feishu.cn | agent-browser | 飞书文档需 DOM 抽取 |
| larkoffice.com | agent-browser | 飞书国际版，同上 |
| apipost.net | agent-browser（遍历目录树） | 接口文档需逐节点抓取 |
| 其他公网 URL | agent-browser | 通用 DOM 抽取 |

---

## 飞书文档处理

URL 形如 `https://xxx.feishu.cn/docx/{docToken}` 或 `https://xxx.feishu.cn/wiki/{wikiToken}`，与通用 URL 处理流程相同，使用浏览器自动化工具抓取正文。

---

## 通用 URL 处理（浏览器自动化生态）

适用于 feishu.cn / larkoffice.com / apipost.net / 其他公网 URL。

### 工具选择（按场景，任选其一即可）

| 工具 | 适用场景 | 一句话 |
|------|---------|------|
| `agent-browser` | 通用首选 | AI 工具调用的极速瑞士军刀（轻量·ref·50+ 命令） |
| `browser-harness` | 选择器易变 / 动态渲染 | AI 编程助手的自愈浏览器手 |
| `playwright` | 流程固定的批量录入 | 工程化测试的坚实基石（E2E·稳定·详细报告） |
| `browser-use` | 多步骤 LLM 自主决策 | LLM 自主操作的完整大脑（Python·规划·Deep Research） |
| `page-agent` | 中文 / 阿里系站点 | 中文网页理解的领域专家（中文优化·多模态） |

> 下文以 `agent-browser` 为示例描述子流程，其他工具按各自 CLI 等价替换即可（goto / get title / 选择器抽取 三步行为通用）。详细对比与安装见 `../SKILL.md` Group B 表与 `scripts/check-deps.sh`。

```
1. agent-browser goto <url>
2. HTTP 状态检查：
   - 4xx → 中止，输出："URL 不可达（HTTP {code}）：{url}"
   - 5xx → 中止，输出："目标站点错误（HTTP {code}），稍后重试"
   - 超时 (>30s) → 中止，输出："agent-browser 加载超时，URL：{url}"
3. 登录检测：`agent-browser get title` 含"登录"/"Login"/"Sign in"
   → 中止，输出："检测到登录页面，请先在浏览器中登录后重试。"
   登录后可重新执行 `/knowledge-wiki in <url>` 继续
4. 提取正文（按下方选择器 + 去噪规则）
5. 提取结果为空（去噪后 <100 字符）→ 中止，输出："正文提取为空，请确认 URL 内容或改用文本输入"
6. 进入 AI 结构化流程
```

### 选择器表

| 域名 | 选择器 | 备注 |
|------|--------|------|
| larkoffice.com / feishu.cn | `.doc-content` | 兜底 `.docs-reader-content` |
| apipost.net | 遍历左侧目录树 `.tree-node` | 逐节点抓取右侧详情 |
| 其他公网 URL | `main, article, [role=main]` 优先；否则 `body` | 必须去噪 |

### 通用去噪规则

1. 移除节点：`nav, header, footer, aside, script, style, iframe, .ad, .advertisement, .sidebar, .comments, .toc-fixed, .related-articles`
2. 折叠连续空白：多空格/多换行 → 单空格/双换行
3. 移除「分享/订阅/上一篇/下一篇/版权所有」等导航文案行（按正则匹配整行后丢弃）
4. 保留代码块、表格、图片 alt 文本

---

## scan 中的路由（与录入完全一致）

```
1. 读取 .sources.yaml，遍历 status=active 的源
2. 按域名路由：
   - 所有域名 → agent-browser goto <url> + 登录检测 + 选择器+去噪
3. 提取失败处理：
   - 登录页 / 4xx / 5xx / 超时 → 标记 status=error，跳过，提示用户
4. 计算 content_hash，对比 last_hash：
   相同 → 更新 last_synced，无输出
   不同 → 输出变更（diff 行数估计），等待用户选择：
          [1] /knowledge-wiki in --update <slug>（拉取更新）
          [2] 标记 stale 暂不处理
          [3] 废弃此来源
5. 处理完成后更新 .sources.yaml
```

**content_hash 算法**：取去噪后正文 → trim → 折叠连续空白为单空格 → UTF-8 编码 → `sha1` 取前 12 位十六进制（如 `a1b2c3d4e5f6`）。仅 hash 正文文本，忽略图片二进制和 DOM 属性，确保排版微调不触发 false positive。

**异常处理**：agent-browser 超时（>30s）或崩溃 → 标记该源 `status: error`，输出错误信息，继续处理下一个源，不中止整个 scan。

scan 不自动更新，所有变更由用户决策。

