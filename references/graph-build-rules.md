# 图谱派生引擎规则（graph-build-rules.md）

> **本文件是 knowledge-wiki 图谱派生引擎（`graph_build.py`）的职责权威源**。定义「引擎必须做什么、不能做什么」——编译流程、锁、原子写、单向派生、source_hash、确定性序列化、脚本放置、uv 隔离、C6 日志、零破坏回退红线。
>
> 与 `graph-model.md` 互补：`graph-model.md` 定义**数据形状**（model），本文件定义**引擎行为**（build）。仿 `index-rules.md` 风格，用 directive prose 描述规则，**不粘贴完整 Python 脚本**（脚本本体属 01-02 的 `graph_build.py`）。
>
> 字段权威来源：Phase 1 Research `01-RESEARCH.md` §2 决策 2（脚本骨架与放置）、§3 决策 3（health 挂载）、§5 决策 5（零破坏回退）、§6（原子写 + 锁 + source_hash）、§7（uv 依赖隔离）、§9.4（复用清单）；PITFALLS Pitfall 1/5/8。

---

## 1. 引擎定位声明（单向派生铁律）

图谱引擎是文档 SSOT 的**纯函数派生器**：

```
graph = compile(documents)
```

- **唯一写入路径 = `graph_build.py` 的 `atomic_write`**。除此之外，**graph.json 没有任何 mutate 写接口**——不存在「编辑某条边」「patch 某个节点」「增量追加一行」之类的原地修改入口（守 PITFALLS Pitfall 1 双源真理）。
- 引擎**只读 `.knowledge/` 文档，绝不反写 L0 文档**。文档永远是 SSOT，图永远是派生物。
- 任何「图与文档不一致」的修复方式只有一种：**重新 `compile(documents)` 全量覆盖**。这从根本上消除双源不一致。
- 因此「人工手改 graph.json」是被禁止的——`generator` 字段标记派生来源，人工编辑视为非法产物，下次 build 会无条件覆盖。

> 这条铁律是 ROADMAP Success Criteria #4 的核心：graph.json 无 mutate 写接口，唯一写入路径 = 从文档编译。

---

## 2. 全量编译流程（10 步，套用 index-rebuild 范式）

graph-build 与既有 `index-rebuild` 同构（`index-rules.md`「重建流程」/`health-rules.md`），差异仅在「编译产物是 graph.json 而非 idx」。复用其幂等可重跑特性。Phase 1 只做全量编译（`build_mode = "full"`）。

```
1. 扫描 10 个业务目录的 *.md
     glossary/ design/ requirements/ flows/ case/ tests/ apis/ db/ ops/ synthesis/
2. 排除系统目录与根文件（黑名单抄 post-merge.sh）：
     系统目录：.index/  .logs/  .graph/
     根文件：  README.md  CLAUDE.md  AGENTS.md  .sources.yaml
     pending： .pending-backlinks.yaml  .pending-docs.yaml
3. 解析每篇文档 frontmatter（title/type/status/expires；缺失按 graph-model.md §4 容错降级 + warning，不中断）
4. 建节点：每篇 .md → 一个节点；glossary/ 目录文档标 node_kind="glossary_term"，其余标 "document"（方案 A）
5. 建边集：Phase 1 档位 1，collect_edges 返回 []（真正建边推迟 Phase 2）
6. 计算 source_hash：对全部业务 .md 的 (相对路径, mtime, size) 三元组排序后求 sha256（见 §5）
7. networkx 自检：nx.node_link_graph(payload, edges="links") 加载回内存，校验无悬空端点（Phase 1 links 为空天然通过）
8. 原子写：临时文件（建在 .graph/ 内）→ flush + os.fsync → os.replace 覆盖 graph.json（见 §4）
9. 输出 GRAPH-03 摘要：源文档数 / 节点数 / 边数 / 可信度分布 / 节点状态分布 / source_hash / 产物大小
10. 追加 C6 操作日志到 .logs/personal/{user-id}.md（见 §9）
```

> 复用既有索引重建的前置安全检查（工作区干净 + 可选 git pull）与幂等特性——同一文档集多次 build 产出一致（见 §6）。

---

## 3. 锁机制规则（.build.lock）

防止并发 build 互相覆盖。引擎入口与出口的锁约定：

| 环节 | 规则 |
|------|------|
| **入口检测** | build 入口检测 `.knowledge/.graph/.build.lock`。**存在则报「图谱正在构建中」并 `exit 2`**（非 0 退出码，供 CI / 并发探测识别） |
| **写锁** | 锁不存在则创建，写入内容 = `pid + 时间戳`（便于诊断陈旧锁归属） |
| **释放锁** | `finally` 块**无条件** `unlink(missing_ok=True)` 释放——无论 build 成功或抛异常都释放，绝不留残锁 |
| **陈旧锁** | 锁内含 pid + ts。Phase 1 **只提示不自动清**（可提示「锁龄 > N 分钟疑似残留，请手动删除后重试」），避免误删正在运行的并发锁 |

> 来源 `01-RESEARCH.md` §6 + ROADMAP SC#4。锁路径固定在 `.graph/.build.lock`，随 `.graph/` 一并隔离与回退。

---

## 4. 原子写规则（同盘 + fsync + os.replace）

graph.json 的写入必须原子，绝不允许出现「半截 JSON」。规则（来源 `01-RESEARCH.md` §6 表 + ARCHITECTURE Anti-Pattern 4）：

1. **临时文件必须建在 `.graph/` 内**（同分区）。`tempfile.NamedTemporaryFile(dir=<.graph 目录>)`——否则 `os.replace` 跨文件系统会退化为非原子的 copy+unlink，破坏原子性。
2. **写入后 `flush` + `os.fsync(fileno)`**——确保数据落盘，防止崩溃时丢内容。
3. **`os.replace(tmp, graph.json)` 原子覆盖**——`os.replace` 在同一文件系统内是原子 rename，覆盖时不会留半截文件。读者要么看到旧的完整版，要么看到新的完整版，绝无中间态。

> 中断（kill）测试：build 过程中 kill，graph.json 要么是旧完整版要么不变，绝无半截 JSON（ROADMAP SC#4 验收）。

---

## 5. source_hash 规则（三元组排序 sha256）

顶层 `source_hash` 是 `.knowledge/` 文档集的确定性指纹：

- **算法**：对全部业务 `.md` 的 `(相对路径, mtime, size)` 三元组**排序后**拼接，求 `sha256`，存为 `"sha256:<hex>"`。
- **排序保证确定性**：同一文档集（内容、mtime、size 不变）→ 同一 hash。
- **用途**：存顶层供 **Phase 2 增量重建 / staleness 判断**（文档集指纹变了 → 图过期需重建）。Phase 1 仅计算并存储，**不消费**（增量是 Phase 2 GRAPH-04 的活）。

> 来源 STACK §5 + PITFALLS Pitfall 1「hash 校验」。git hook（post-merge/post-commit）后续可检测 source_hash 漂移并提示「图过期，建议 health graph-build」，但**只提示不自动跑重算法**（守性能与可回退）。

---

## 6. 确定性序列化规则（byte 级可复现）

同一文档集两次 build 必须产出 **byte 级一致**的 graph.json（git diff 友好，且为 Phase 2「增量 == 全量等价性」回归打基础）：

- `json.dump(payload, f, sort_keys=True, ensure_ascii=False, indent=2)`
  - `sort_keys=True`：键有序
  - `ensure_ascii=False`：中文不转义，可读可 diff
  - `indent=2`：稳定缩进
- **节点 / 边按 `id` 排序写入**（节点按 `id`，边按 `(source, target, relation)`）——消除遍历顺序带来的非确定性。

> 来源 `01-RESEARCH.md` §6 + PITFALLS Pitfall 4。确定性是 Phase 2 增量正确性回归测试的前提。

---

## 7. 脚本放置决策（锁定①：随 init 复制到 .graph/scripts/）

**Phase 1 锁定方案①：`graph_build.py` 随 `init` 复制到 `.knowledge/.graph/scripts/graph_build.py`。**（来源 `01-RESEARCH.md` §决策 2）

| 方案 | 说明 | 取舍 |
|------|------|------|
| **① 随 init 复制到 `.knowledge/.graph/scripts/`（锁定）** | 脚本作为派生层的一部分，与既有 hook cp 到 `.git/hooks/` 同范式（复用 init 复制 hook 的 cp 范式） | **贴合「删 `.graph/` 即回退」**——脚本也随回退一并删除，自包含、零残留。需 init 增加一步复制（属 01-03） |
| ② 常驻 `references/scripts/` 由 health 直接 `uv run` 引用 | 不复制，health 直接引用 references 下的脚本 | **备选，不采用**——脚本留在 references/ 不随 `.graph/` 回退，破坏「删 .graph/ 即完整回退」的自包含性 |

> health graph-build 通过 `run_terminal_cmd` 执行 `uv run .knowledge/.graph/scripts/graph_build.py`（脚本本体属 01-02，init 复制属 01-03）。

---

## 8. uv 依赖隔离规则（PEP 723，零全局污染）

引擎用 `uv run` + PEP 723 内联脚本元数据管理依赖，零全局污染（来源 `01-RESEARCH.md` §7 + STACK Version Compatibility）：

| 要点 | 规则 |
|------|------|
| **唯一依赖** | PEP 723 脚本头声明 `dependencies = ["networkx==3.6.1"]`。Phase 1 **只需 networkx 一个包**——不抽 AST、不可视化，**不引 tree-sitter / pyvis** |
| **禁 default extra** | **禁止写 `networkx[default]`**——它会拉 numpy/scipy/matplotlib 重依赖。核心 node-link load + 后续图算法在裸 networkx 即可 |
| **首次运行** | `uv run graph_build.py` 首次自动拉起隔离环境装 networkx，**不污染系统 site-packages、不留全局状态**；后续命中缓存秒级启动 |
| **uv 缺失兜底** | uv 缺失时图层**优雅缺席**——graph-build 不可用，但纯文档功能（init/in/ask/docs/health 基础）不受任何影响、不阻断。check-deps 可给安装指引但不阻断 init（图层是可选叠加） |

> uv 的环境是脚本级临时隔离，非项目级 venv。删 `.graph/`（含脚本副本）+ 不留全局依赖 = 彻底回退。

---

## 9. C6 日志要求

graph-build 执行后**须追加一条 health 类操作日志**到 `.logs/personal/{user-id}.md`，**复用既有 `log-rules.md` 日志通道，不另起新通道**（守 C6）。

- 日志类型归为 `health` 类操作（graph-build 是 health 的第 11 个子命令）。
- 按 `log-rules.md`「日志条目格式」追加，记录执行时间、owner、动作（graph-build）与摘要要点（节点数/边数）。
- 这是 C6 对新命令的硬要求：所有改变知识库系统状态的操作均留痕。

---

## 10. 零破坏回退红线（地基铁律）

零破坏回退靠**架构纪律**成立，而非代码兜底（来源 `01-RESEARCH.md` §5 决策 5 + PITFALLS Pitfall 5）：

1. **物理隔离**：图层全部落 `.knowledge/.graph/`（含 graph.json、scripts/、.build.lock），与 `.index/ .logs/ .pending-*.yaml` 同级隔离（`directory-structure.md` 已是此格局）。`rm -rf .knowledge/.graph/` 不触碰任何 L0 文档与既有系统目录。
2. **零硬依赖**：既有 init/in/ask/docs/health 的**任何路径都不读 graph.json**。Phase 1 它们本就不知道图存在——只要本阶段不改既有 5 子命令的规则文件即可天然成立。
3. **删 `.graph/` 即回退**：删除整个 `.graph/` 目录后，init/in/ask/docs/health 基础功能全链路正常，行为与「图层从未存在」时完全一致（GRAPH-05 冒烟验收）。
4. **后续阶段红线**：**Phase 4 引入 `ask graph` 时才需要「图不存在 → 优雅降级」包装**（PITFALLS Pitfall 5）。Phase 1 无此风险（既有命令不消费图），但此红线写明作为后续阶段的约束——任何消费 graph.json 的新能力都必须在图缺失时优雅降级，不得让图成为既有功能的硬依赖。

> 删 `.knowledge/.graph/` 即回退到纯文档库——这是 Project Constraints 的「可回退」零破坏保证，也是 01-04 零破坏冒烟的验收依据。

---

## 12. collect_edges 职责（Phase 2 解锁真边）

Phase 1 `collect_edges(nodes)` 恒 `return []`。**Phase 2 改为真派生**——从每篇文档的 frontmatter `related` 中 `[[slug]]` 派生有向边。

### 职责边界

1. **边唯一来源 = 每篇文档 frontmatter `related` 的 `[[slug]]`**。**不读正文内联 `[[slug]]`、不读 `.pending-backlinks.yaml`**——pending 是待回写请求非 SSOT，读它会让图领先于文档（Pitfall 1 双源）。
2. **有向边**：`A.related` 含 `[[B]]` ⟹ 边 `source=A, target=B`。
3. **relation 由 `infer_relation(source, target)` 纯函数决定**（映射表见 `graph-model.md` §3.3，命中即停、优先级 1→6、同输入恒同输出）。
4. **去重键 `(source, target, relation)`**——三元组唯一，重复声明取首次出现行号（确定性）。
5. **悬空 target**（不在 nodes）→ **丢弃 + warning**（不报错不中断，文档侧由 L2 lint 负责）。**自引用**（`A.related` 含 `[[A]]`）→ 丢弃 + warning。
6. **source_location 强制非空**（行级优先降级字段级，见「§13 source_location 行号解析规则」）。缺失则**拒绝入图 + 计入摘要「拒绝入图边数」**——这是 L-graph-orphan-edge 第一道防线，守不变量 12。
7. **confidence 恒 `"EXTRACTED"`、reviewed 恒 `true`**——结构边=人写 frontmatter 声明，非机器推断（Phase 3 才引入分级与人审）。
8. **networkx 自检**：边非空后 `nx.node_link_graph(payload, edges="links")` 真正生效——校验无悬空端点（是不变量 11 的最后断言防线）。悬空边已在 collect_edges 丢弃故理论不触发；自检失败时输出明确「哪条边悬空」诊断信息而非裸抛。

> **collect_edges 是纯结构确定性派生**：同输入同输出、无 AI、无随机性。引擎不读正文、不读 pending、不消费其他辅助文件——只认落盘 frontmatter `related`。

---

## 13. source_location 行号解析规则

描述 `parse_related_with_lines(md_text) -> [(target_slug, line_no), ...]` 的健壮做法（引擎实现的输入契约）。

### 解析流程

1. **只扫描 `---` 包裹的 frontmatter 区间**（**复用 Phase 1 `parse_frontmatter` 边界定位逻辑**），绝不碰正文——避免正文 `[[x]]` 误入。
2. **支持两种 YAML 写法**：
   - 块状列表（`ingestion-rules.md` 标准格式）：
     ```yaml
     related:
       - "[[slug-a]]"
       - "[[slug-b]]"
     ```
   - 行内列表（兜底）：
     ```yaml
     related: ["[[slug-a]]", "[[slug-b]]"]
     ```
3. **行号 = `splitlines()` 索引 + 1**（1-based，与 grep -n / 编辑器行号一致）。
4. **`[[slug]]` 抓取**与 `lint-rules.md` L2 的 `\[\[\K[^\]]+` 同源语义（slug 含义完全一致）。
5. **任何异常返回已成功解析的 partial**，未定位项由调用方降级到 L2 字段级（`path:frontmatter:related`）。
6. **同一文件同一 target 多行出现** → 去重保留 **min(行号)**（确定性）。

### 降级规则

| 场景 | 处理 |
|------|------|
| `[[slug]]` 成功定位到某行 | L1 行级：`source_location = "{path}:{行号}"` |
| related 块存在但某 `[[slug]]` 未被定位 | 该边 L2 降级：`"{path}:frontmatter:related"` + warning |
| 同一文件同一 target 出现在多行 | 去重取 min(行号) |
| frontmatter 整体解析失败 | 该文档所有 related 边降级 L2 |
| 连 L2 都无法确定来源 | **拒绝该边入图 + 报错**（极罕见） |

> **健壮性铁律**：**单篇文档行号解析失败不中断整图编译**——降级 L2 + warning。只有「连 L2 都无法确定来源」才拒绝该边（极罕见，等价于边来源完全不可知）。编译鲁棒性 > 单边严格。

---

## 14. 确定性边排序（Phase 2 边非空后生效）

Phase 1 §6 已定「边按 `(source, target, relation)` 排序」——Phase 2 边非空后**真正执行**。

### 排序规则

`collect_edges` 末尾执行：`edges.sort(key=lambda e: (e["source"], e["target"], e["relation"]))`。

**同一文档集两次 build 必产出 byte 级一致的 graph.json**——这是 02-04 增量 == 全量等价性回归的底层保证，也是 git diff 友好的前提。

### 摘要增强（边非空后）

边非空后 GRAPH-03 摘要有真实数据：

- **边计数**：`边：N 条`
- **可信度分布**：`EXTRACTED N | INFERRED 0 | AMBIGUOUS 0`（Phase 2 全部 EXTRACTED）
- **relation 分布（新增）**：`term_of X | references Y | depends_on Z | derived_from W`（各 relation 类型计数）

### doc_count 契约收紧（Phase 1 遗留对齐）

摘要「源文档：N 篇 → 节点：M」的 `doc_count` 只数 `node_kind==document`，与 `graph-model.md` §1 收紧后的 `node_count`（= 源 .md 文件数）措辞对齐。实际代码改在 02-02，本节声明契约。

---

## 15. 增量重建规则（路线 B 伪增量，GRAPH-04）

### 锁定路线 B

Phase 2 采**路线 B（伪增量）**——`--incremental` 内部仍跑全量 `collect_nodes/collect_edges`（复用 Phase 1 已验证的 `atomic_write` + 确定性序列化），对外暴露增量语义。

真 dirty-set 子图重建**明确推后**——当真实团队库规模触发可感知的录入延迟时作为独立优化阶段引入，届时 Phase 2 已建的等价性回归测试正是它的回归护栏。

### staleness 判断（复用 Phase 1 `compute_source_hash`）

1. 读现存 `graph.json` 顶层 `source_hash`（文件不存在 → 直接全量重建）。
2. 计算当前 `.knowledge/` 的 `compute_source_hash`（三元组排序 sha256，见 §5）。
3. **hash 一致** ⟹ 文档集未变 ⟹ **跳过重建**（输出「图谱已最新，无需重建」+ exit 0）。
4. **hash 不一致** ⟹ 文档集已变 ⟹ 执行重建（路线 B 下即全量 collect + atomic_write），`build_mode` 写 `"incremental"`。

### CLI 形态

| 标志 | 行为 |
|------|------|
| `--full` | 无条件全量重建（兜底核弹按钮，Phase 1 已有） |
| `--incremental` | 伪增量：仅文档集真变才重建 |
| 无标志（默认） | 等价 `--incremental`（智能判断） |

### 等价性保证

**增量产物天然 == 对同一最终文档状态的全量产物**（因为它就是全量）。SC#4 等价性构造即成立。真 dirty-set 子图重建推后，届时复用 Phase 2 已建的等价性回归作护栏（守 Pitfall 4：本阶段不引入高风险 dirty-set 合并逻辑）。

### GRAPH-04 `in` 挂载（档位 P：提示驱动）

`in`/`in --update` 流程末尾追加 staleness 提示 Step：

- 检测 `.knowledge/.graph/graph.json` 存在且 `source_hash` 漂移时 → **提示**「图谱已过期，建议 `health graph-build --incremental`」。
- **不自动跑、图层不存在则静默跳过**（守零破坏 + 录入不触发重算）。
- 该 Step **不阻断、不修改图、不写额外 C6 日志**（具体挂载落点在 02-03 改 `ingestion-rules.md`）。

> **档位 P 铁律**：`in` 只提示不自动跑 graph_build——守 PITFALLS Performance Traps「录入不触发重算」+ Integration Gotchas「hook 只提示不阻塞」。

---

## 11. 边界声明（本文件不定义什么）

本文件用 directive prose 描述「引擎必须做什么、不能做什么」，**不粘贴完整 Python 脚本**（规则文档与代码实现分离是 ARCHITECTURE 既定纪律）：

- ❌ 完整 `graph_build.py` 脚本本体 → 属 01-02
- ❌ frontmatter 解析的具体实现代码 → 属 01-02（本文件只声明「按 graph-model.md §4 容错」）
- ❌ health graph-build 子命令挂载 + init 复制脚本 → 属 01-03
- ❌ 真正建边 / relation 分类 / source_location 强制校验 → Phase 2
- ❌ 增量重建 dirty-set 子图重算 → Phase 2
- ❌ 中心度 / 社区检测计算 → Phase 6

> 本文件只定义引擎的职责契约与红线，是 01-02 `graph_build.py` 实现的直接行为输入。
