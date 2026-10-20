#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["networkx==3.6.1"]
# ///
"""graph_build.py — knowledge-wiki 派生引擎（Phase 1：全量编译）

单向派生铁律：graph = compile(documents)。
- 唯一写入路径 = 本脚本的 atomic_write，写 .knowledge/.graph/graph.json。
- 绝不反写 L0 文档（.knowledge/{业务目录}/*.md 严格只读）。
- 任何「图与文档不一致」的修复方式只有一种：重新全量 compile 覆盖。

用法:
    uv run graph_build.py --kb-root .knowledge --full

实现契约见 references/graph-model.md（节点 schema）+ references/graph-build-rules.md（引擎行为）。
Phase 1 最小依赖只 networkx==3.6.1（禁止 default extra，避免拉 numpy/scipy/matplotlib）。
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# ── 常量 ──────────────────────────────────────────────────────────────
GRAPH_DIR = ".graph"
LOCK = ".build.lock"
SCHEMA_VERSION = "1.0"
GENERATOR = "knowledge-wiki/graph-build@1.0"

# 10 个业务目录（graph-build-rules.md §2 步骤 1）
BUSINESS_DIRS = [
    "glossary",
    "design",
    "requirements",
    "flows",
    "case",
    "tests",
    "apis",
    "db",
    "ops",
    "synthesis",
]

# 目录名 → type 推断（frontmatter type 缺失时兜底；仍不得为空）
DIR_TYPE_MAP = {
    "glossary": "glossary",
    "design": "architecture",
    "requirements": "requirement",
    "flows": "flow",
    "case": "solution",
    "tests": "test",
    "apis": "api",
    "db": "db",
    "ops": "ops",
    "synthesis": "synthesis",
}

# 系统目录黑名单（抄 post-merge.sh 排除范式）
SYSTEM_DIRS = {".index", ".logs", ".graph"}
# 根文件黑名单
ROOT_FILE_BLACKLIST = {
    "README.md",
    "CLAUDE.md",
    "AGENTS.md",
    ".sources.yaml",
    ".pending-backlinks.yaml",
    ".pending-docs.yaml",
    ".pending-edges.yaml",
}

# status 合法取值（缺失默认 draft，守 C3 草稿优先，不擅自升级）
VALID_STATUS = {"canonical", "active", "draft", "deprecated"}

# 单个 [[slug]] 提取（与 lint-rules.md L2 的 grep -oP '\[\[\K[^\]]+' 同源语义）
SLUG_RE = re.compile(r"\[\[([^\]]+)\]\]")

# 解析过程中收集的告警（单篇异常降级填默认 + warning，不中断整图编译）
warnings: list[str] = []


# ── relation 结构推定 ─────────────────────────────────────────────────
def infer_relation(source: dict, target: dict) -> str:
    """纯结构 relation 推定（无 AI、确定性）。

    优先级见 graph-model.md §3.3 / 02-RESEARCH §2.3。
    命中即停，同输入恒同输出，不读文件、不调 AI、无随机性。
    Phase 2 产出集 = {references, depends_on, derived_from, term_of}。
    绝不返回冲突类或 AST 类 relation。
    """
    if target["node_kind"] == "glossary_term":        # 优先级 1
        return "term_of"
    if source["type"] == "glossary":                   # 优先级 2
        return "references"
    if source["type"] in ("architecture", "solution", "adr"):  # 优先级 3
        return "derived_from"
    if source["type"] == "requirement":               # 优先级 4
        return "depends_on"
    if source["type"] == "synthesis":                 # 优先级 5
        return "derived_from"
    return "references"                                # 优先级 6 兜底


# ── related 行号解析 ──────────────────────────────────────────────────
def parse_related_with_lines(md_text: str) -> list[tuple[str, int]]:
    """解析 frontmatter related 块，返回 [(target_slug, line_number_1based), ...]。

    健壮性原则（与 Phase 1 parse_frontmatter 同级容错）：
    - 只扫描 --- 包裹的 frontmatter 区间，绝不碰正文（避免正文 [[x]] 误入）。
    - related 块支持两种 YAML 写法：
        related:
          - "[[slug-a]]"        # 块状列表（ingestion-rules.md 标准格式）
          - "[[slug-b]]"
      以及  related: ["[[slug-a]]", "[[slug-b]]"]   # 行内列表（兜底）
    - 行号 = splitlines() 索引 + 1（1-based，与编辑器/grep -n 一致）。
    - 任何异常 → 返回已成功解析的部分（partial），由调用方对未定位项降级到 L2 字段级。
    """
    results: list[tuple[str, int]] = []
    try:
        lines = md_text.splitlines()
        # 1. 定位 frontmatter 区间 [start, end)（复用 Phase 1 定位逻辑）
        i = 0
        while i < len(lines) and lines[i].strip() == "":
            i += 1
        if i >= len(lines) or lines[i].strip() != "---":
            return results
        start = i + 1
        end = None
        for j in range(start, len(lines)):
            if lines[j].strip() == "---":
                end = j
                break
        if end is None:
            return results
        # 2. 在区间内定位 related: key，进入其块状列表
        in_related = False
        for ln in range(start, end):
            raw = lines[ln]
            key_is_toplevel = raw[:1] not in (" ", "\t", "-") and ":" in raw
            if key_is_toplevel:
                key = raw.split(":", 1)[0].strip()
                if key == "related":
                    in_related = True
                    # 行内列表：related: ["[[a]]","[[b]]"] —— 同行直接抓
                    inline = raw.split(":", 1)[1]
                    for m in SLUG_RE.finditer(inline):
                        results.append((m.group(1).strip(), ln + 1))  # 1-based
                    continue
                else:
                    in_related = False  # 遇到下一个顶层 key，related 块结束
            if in_related:
                # 块状列表项行：- "[[slug]]"
                for m in SLUG_RE.finditer(raw):
                    results.append((m.group(1).strip(), ln + 1))  # 1-based
    except Exception:  # noqa: BLE001 — 鲁棒性 > 单篇严格，任何异常返回 partial
        pass
    return results


# ── frontmatter 解析 ─────────────────────────────────────────────────
def parse_frontmatter(md_text: str) -> dict:
    """手写最小 YAML frontmatter 解析。

    只提取 Phase 1 需要的 4 个标量字段：title / type / status / expires。
    不引第三方 pyyaml（守最小依赖，frontmatter 是简单 key: value，
    容错级别与 pre-commit.sh 的 grep/awk 抽取同级）。
    不解析 related 列表（建边推迟 Phase 2）。

    解析失败时返回空 dict，由调用方降级填默认 + 收集 warning，不抛出。
    """
    wanted = ("title", "type", "status", "expires")
    result: dict = {}
    try:
        lines = md_text.splitlines()
        # 定位 --- 包裹的 frontmatter 块：首个非空行必须是 ---
        idx = 0
        while idx < len(lines) and lines[idx].strip() == "":
            idx += 1
        if idx >= len(lines) or lines[idx].strip() != "---":
            return result  # 无 frontmatter
        start = idx + 1
        end = None
        for i in range(start, len(lines)):
            if lines[i].strip() == "---":
                end = i
                break
        if end is None:
            return result  # frontmatter 未闭合，视为无
        for raw in lines[start:end]:
            line = raw.rstrip()
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if ":" not in line:
                continue
            # 只在顶层 key（无前导缩进）取标量，避免误吃列表项/嵌套
            if line[0] in (" ", "\t", "-"):
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            if key not in wanted:
                continue
            value = value.strip()
            # 去除成对引号
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            # 去除行内注释（仅对未加引号的标量做保守处理）
            value = value.strip()
            if value:
                result[key] = value
    except Exception:  # noqa: BLE001 — 鲁棒性 > 单篇严格，任何异常都降级
        return {}
    return result


# ── 节点抽取 ──────────────────────────────────────────────────────────
def collect_nodes(kb_root: Path) -> list[dict]:
    """遍历 10 个业务目录的 *.md → 文档节点。

    字段映射严格按 graph-model.md §4：
    - id          = basename 去 .md（= slug，与 idx slug 列同源），不会缺
    - type        = frontmatter type，缺则按目录推断，仍不得为空
    - status      = frontmatter status，缺则默认 draft
    - expires     = frontmatter expires，缺则默认 never
    - title       = frontmatter title，缺则用 slug 占位
    - path        = 相对仓库根的 .md 路径
    - node_kind   = 方案 A：glossary/ 目录 → glossary_term，否则 document
    - source_mtime= 文件系统 mtime（int）
    - centrality  = None（Phase 6 回填）
    - community   = None（Phase 6 回填）

    单篇 frontmatter 残缺/异常时降级填默认值 + 收集 warning，不中断整体编译。
    """
    nodes: list[dict] = []
    for dirname in BUSINESS_DIRS:
        dpath = kb_root / dirname
        if not dpath.is_dir():
            continue
        node_kind = "glossary_term" if dirname == "glossary" else "document"
        inferred_type = DIR_TYPE_MAP.get(dirname, dirname)
        for md_file in sorted(dpath.rglob("*.md")):
            if not md_file.is_file():
                continue
            # 排除藏在业务目录下的系统子目录（保守，业务目录内一般不应有）
            if any(part in SYSTEM_DIRS for part in md_file.relative_to(kb_root).parts[:-1]):
                continue
            slug = md_file.stem
            try:
                text = md_file.read_text(encoding="utf-8")
                fm = parse_frontmatter(text)
            except Exception as exc:  # noqa: BLE001 — 读文件失败也降级
                text = ""
                fm = {}
                warnings.append(f"{md_file}: 读取/解析失败降级填默认（{exc}）")

            node_type = fm.get("type") or inferred_type
            if not node_type:
                node_type = inferred_type
                warnings.append(f"{md_file}: type 缺失，按目录推断为 {inferred_type}")

            status = fm.get("status")
            if status not in VALID_STATUS:
                if status:
                    warnings.append(
                        f"{md_file}: status='{status}' 非法，降级为 draft"
                    )
                else:
                    warnings.append(f"{md_file}: status 缺失，默认 draft")
                status = "draft"

            expires = fm.get("expires") or "never"
            if not fm.get("expires"):
                warnings.append(f"{md_file}: expires 缺失，默认 never")

            title = fm.get("title") or slug

            try:
                mtime = int(md_file.stat().st_mtime)
            except OSError:
                mtime = 0

            # 解析 related 行号（供 collect_edges 消费，仅内存字段不落盘）
            try:
                related_edges = parse_related_with_lines(text)
            except Exception:  # noqa: BLE001 — 降级为空
                related_edges = []
                warnings.append(f"{md_file}: _related_edges 解析失败降级为空")

            nodes.append(
                {
                    "id": slug,
                    "type": node_type,
                    "status": status,
                    "expires": expires,
                    "title": title,
                    "path": str(md_file),
                    "node_kind": node_kind,
                    "source_mtime": mtime,
                    "centrality": None,
                    "community": None,
                    "_related_edges": related_edges,
                }
            )
    # 确定性序列化：节点按 id 排序写入，消除遍历顺序非确定性
    nodes.sort(key=lambda n: n["id"])
    return nodes


def collect_edges(nodes: list[dict]) -> list[dict]:
    """从节点的 related（含行号）派生有向边。纯结构、确定性、无 AI。

    前置：collect_nodes 已为每个节点附加 _related_edges = [(target_slug, line_no), ...]
         （仅 build 期内存字段，不落盘）。

    职责：去重(source,target,relation)/悬空丢弃/自引用丢弃/source_location 行级优先
    降级字段级/confidence=EXTRACTED/reviewed=true/(source,target,relation) 排序。
    """
    node_by_id = {n["id"]: n for n in nodes}
    seen: set[tuple[str, str, str]] = set()  # (source, target, relation) 去重键
    edges: list[dict] = []
    rejected_count = 0

    for src in nodes:
        a = src["id"]
        for target_slug, line_no in src.get("_related_edges", []):
            # 自引用丢弃
            if target_slug == a:
                warnings.append(f"{src['path']}: related 含自引用 [[{a}]]，已丢弃")
                continue
            tgt = node_by_id.get(target_slug)
            # 悬空 [[slug]]：target 不在 nodes → 丢弃 + warning
            if tgt is None:
                warnings.append(f"{src['path']}: related 含悬空引用 [[{target_slug}]]，边已丢弃")
                continue
            relation = infer_relation(src, tgt)
            key = (a, target_slug, relation)
            if key in seen:  # 去重（同对同 relation 只一条，取首次行号）
                continue
            seen.add(key)
            # source_location：行号优先，降级字段级
            if line_no and line_no > 0:
                src_loc = f"{src['path']}:{line_no}"
            else:
                src_loc = f"{src['path']}:frontmatter:related"
            # L-graph-orphan-edge 第一道防线：source_location 必非空
            if not src_loc:
                warnings.append(f"边 {a}->{target_slug} 缺 source_location，拒绝入图")
                rejected_count += 1
                continue
            edges.append({
                "source": a,
                "target": target_slug,
                "relation": relation,
                "confidence": "EXTRACTED",
                "source_location": src_loc,
                "reviewed": True,
            })
    # 确定性序列化：边按 (source, target, relation) 排序
    edges.sort(key=lambda e: (e["source"], e["target"], e["relation"]))
    # 将 rejected_count 存到模块级变量供摘要消费
    collect_edges._rejected_count = rejected_count  # type: ignore[attr-defined]
    return edges


# ── source_hash ──────────────────────────────────────────────────────
def compute_source_hash(kb_root: Path) -> str:
    """对全部业务 .md 的 (相对路径, mtime, size) 三元组排序后求 sha256。

    排序保证确定性：同一文档集（内容/mtime/size 不变）→ 同一 hash。
    返回 "sha256:<hex>"。Phase 1 仅计算并存储，不消费（增量是 Phase 2 的活）。
    """
    triples: list[tuple[str, int, int]] = []
    for dirname in BUSINESS_DIRS:
        dpath = kb_root / dirname
        if not dpath.is_dir():
            continue
        for md_file in dpath.rglob("*.md"):
            if not md_file.is_file():
                continue
            if any(
                part in SYSTEM_DIRS
                for part in md_file.relative_to(kb_root).parts[:-1]
            ):
                continue
            try:
                st = md_file.stat()
                rel = str(md_file.relative_to(kb_root))
                triples.append((rel, int(st.st_mtime), int(st.st_size)))
            except OSError:
                continue
    triples.sort(key=lambda t: t[0])
    h = hashlib.sha256()
    for rel, mtime, size in triples:
        h.update(f"{rel}|{mtime}|{size}\n".encode("utf-8"))
    return f"sha256:{h.hexdigest()}"


# ── 原子写 ────────────────────────────────────────────────────────────
def atomic_write(graph_path: Path, payload: dict) -> None:
    """原子写 graph.json：同盘临时文件 → flush+fsync → os.replace 覆盖。

    临时文件必须建在 graph_path.parent（.graph/ 内，同分区），
    否则 os.replace 跨文件系统会退化为非原子 copy+unlink。
    确定性序列化：sort_keys=True + ensure_ascii=False + indent=2。
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        dir=graph_path.parent,
        prefix=".graph.",
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    )
    try:
        json.dump(payload, tmp, ensure_ascii=False, indent=2, sort_keys=True)
        tmp.flush()
        os.fsync(tmp.fileno())
    finally:
        tmp.close()
    os.replace(tmp.name, graph_path)  # 同盘原子 rename，绝无半截 JSON


# ── 摘要渲染（GRAPH-03）─────────────────────────────────────────────
def print_summary(payload: dict, graph_path: Path, as_json: bool = False) -> None:
    """输出 GRAPH-03 摘要：节点数/边数/可信度分布/节点状态分布。

    可信度分布即使 Phase 1 全为 0 也打印（GRAPH-03 明确验收字段）。
    预留 --json 模式供 CI 消费。
    """
    nodes = payload["nodes"]
    edges = payload["links"]
    doc_count = sum(1 for n in nodes if n.get("node_kind") == "document")
    term_count = sum(1 for n in nodes if n.get("node_kind") == "glossary_term")

    # 节点状态分布
    status_dist = {"canonical": 0, "active": 0, "draft": 0, "deprecated": 0}
    for n in nodes:
        s = n.get("status")
        if s in status_dist:
            status_dist[s] += 1

    # 可信度分布（Phase 1 边为空恒全 0；GRAPH-03 验收字段）
    conf_dist = {"EXTRACTED": 0, "INFERRED": 0, "AMBIGUOUS": 0}
    for e in edges:
        c = e.get("confidence")
        if c in conf_dist:
            conf_dist[c] += 1

    try:
        size_bytes = graph_path.stat().st_size
        size_kb = f"{size_bytes / 1024:.1f} KB"
    except OSError:
        size_kb = "未知"

    # relation 分布
    relation_dist: dict[str, int] = {}
    for e in edges:
        r = e.get("relation", "")
        relation_dist[r] = relation_dist.get(r, 0) + 1

    # 拒绝入图边数
    rejected = getattr(collect_edges, "_rejected_count", 0)

    if as_json:
        print(
            json.dumps(
                {
                    "build_mode": payload["build_mode"],
                    "doc_count": doc_count,
                    "term_count": term_count,
                    "node_count": payload["node_count"],
                    "edge_count": payload["edge_count"],
                    "confidence_distribution": conf_dist,
                    "relation_distribution": relation_dist,
                    "status_distribution": status_dist,
                    "rejected_edges": rejected,
                    "source_hash": payload["source_hash"],
                    "artifact": str(graph_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    print(f"🕸️ 图谱编译完成（{payload['build_mode']}）")
    print("")
    print(
        f"源文档：{doc_count} 篇 → 节点：{payload['node_count']}"
        f"（文档 {doc_count} + 术语 {term_count}）"
    )
    print(f"边：{payload['edge_count']} 条")
    print(
        "可信度分布："
        f"EXTRACTED {conf_dist['EXTRACTED']} | "
        f"INFERRED {conf_dist['INFERRED']} | "
        f"AMBIGUOUS {conf_dist['AMBIGUOUS']}"
    )
    print(
        "relation 分布："
        f"term_of {relation_dist.get('term_of', 0)} | "
        f"references {relation_dist.get('references', 0)} | "
        f"depends_on {relation_dist.get('depends_on', 0)} | "
        f"derived_from {relation_dist.get('derived_from', 0)}"
    )
    if rejected > 0:
        print(f"⚠️ 拒绝入图边数：{rejected}")
    print(
        "节点状态分布："
        f"canonical {status_dist['canonical']} | "
        f"active {status_dist['active']} | "
        f"draft {status_dist['draft']} | "
        f"deprecated {status_dist['deprecated']}"
    )
    print(f"source_hash：{payload['source_hash']}")
    # ── 待审推断边只读统计（Phase 3：读 .pending-edges.yaml，队列存在才输出）──
    try:
        pending_yaml_path = graph_path.parent.parent / ".pending-edges.yaml"
        if pending_yaml_path.is_file():
            _pe_text = pending_yaml_path.read_text(encoding="utf-8")
            # 极简行扫描统计（禁引第三方 YAML 库）：扫 pending: 块下 confidence: 值与 reviewed: 值
            _in_pending = False
            _inferred_count = 0
            _ambiguous_count = 0
            _reviewed_false_count = 0
            for _line in _pe_text.splitlines():
                _stripped = _line.strip()
                # 检测 pending: 块开始（顶层 key）
                if _line[:1] not in (" ", "\t", "-", "#") and _stripped.startswith("pending:"):
                    _in_pending = True
                    continue
                # 检测下一个顶层 key 结束 pending 块
                if _in_pending and _line[:1] not in (" ", "\t", "-", "#") and ":" in _stripped:
                    _in_pending = False
                    continue
                if _in_pending:
                    if "confidence:" in _stripped and "INFERRED" in _stripped:
                        _inferred_count += 1
                    elif "confidence:" in _stripped and "AMBIGUOUS" in _stripped:
                        _ambiguous_count += 1
                    if "reviewed:" in _stripped and "false" in _stripped.lower():
                        _reviewed_false_count += 1
            _pending_total = _inferred_count + _ambiguous_count
            if _pending_total > 0:
                print(
                    f"待审推断边：{_pending_total} 条"
                    f"（INFERRED {_inferred_count} | AMBIGUOUS {_ambiguous_count}），"
                    f"运行 health edge-review"
                )
    except Exception:  # noqa: BLE001 — 统计解析失败静默跳过，不中断摘要
        pass
    # ── 待审推断边统计结束 ──
    print(f"产物：{graph_path}（{size_kb}）")
    if warnings:
        print(f"⚠️ 降级告警：{len(warnings)} 条（单篇 frontmatter 异常已填默认，不中断编译）")


# ── C6 日志 ───────────────────────────────────────────────────────────
def resolve_user_id() -> str | None:
    """user-id 获取（log-rules.md 优先级）：KB_OWNER → git → whoami → None。"""
    owner = os.environ.get("KB_OWNER")
    if owner:
        return owner.strip()
    for cmd in (["git", "config", "user.email"], ["git", "config", "user.name"]):
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, timeout=3
            ).stdout.strip()
            if out:
                return out.split("@")[0].strip()
        except Exception:  # noqa: BLE001
            pass
    try:
        import getpass

        return getpass.getuser()
    except Exception:  # noqa: BLE001
        return None


def write_c6_log(kb_root: Path, payload: dict) -> None:
    """编译成功后追加一条 health 类操作日志到 .logs/personal/{user-id}.md。

    复用既有 log-rules.md 通道，不另起新通道（守 C6）。
    user-id 缺失时降级跳过，不阻断编译。
    """
    user_id = resolve_user_id()
    if not user_id:
        warnings.append("无法确定 user-id（请设置 git config user.name 或 KB_OWNER），C6 日志已跳过")
        return
    try:
        logs_dir = kb_root / ".logs" / "personal"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / f"{user_id}.md"
        now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        detail = {
            "node_count": payload["node_count"],
            "edge_count": payload["edge_count"],
            "doc_count": payload["doc_count"],
            "build_mode": payload["build_mode"],
            "source_hash": payload["source_hash"],
        }
        if not log_file.exists():
            today = datetime.now().strftime("%Y-%m-%d")
            log_file.write_text(
                f"# @{user_id} 操作日志\n\n"
                f"> 自动生成于 {today} | 归档阈值：150 条或 90 天\n"
                f"> 最后归档：从未\n\n---\n",
                encoding="utf-8",
            )
        entry = (
            f"\n## [{now}] @{user_id} | health | graph-build\n"
            f"  detail: {json.dumps(detail, ensure_ascii=False)}\n"
        )
        with log_file.open("a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as exc:  # noqa: BLE001 — C6 日志失败不阻断编译
        warnings.append(f"C6 日志写入失败（不阻断编译）：{exc}")


# ── 主流程 ────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(
        description="knowledge-wiki 图谱派生引擎"
    )
    ap.add_argument("--kb-root", default=".knowledge", help="知识库根目录（默认 .knowledge）")
    ap.add_argument("--full", action="store_true", help="无条件全量编译（兜底核弹按钮）")
    ap.add_argument("--incremental", action="store_true", help="伪增量：仅文档集真变才重建")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出摘要（供 CI 消费）")
    args = ap.parse_args()

    kb = Path(args.kb_root)
    if not kb.is_dir():
        print(f"❌ 知识库根目录不存在：{kb}", file=sys.stderr)
        sys.exit(1)

    gdir = kb / GRAPH_DIR
    gdir.mkdir(exist_ok=True)
    lock = gdir / LOCK

    # 入口锁检测：存在则 exit 2
    if lock.exists():
        print(
            "⚠️ 图谱正在构建中（.build.lock 存在），请稍候或删除残留锁后重试",
            file=sys.stderr,
        )
        sys.exit(2)
    lock.write_text(f"{os.getpid()} {time.time()}", encoding="utf-8")

    try:
        # ── staleness 判断（--incremental 或默认时生效）──
        # 退出点位在取锁成功后、collect_nodes 前
        graph_path = gdir / "graph.json"
        current_hash = compute_source_hash(kb)
        is_incremental = args.incremental or (not args.full)

        if is_incremental and not args.full and graph_path.exists():
            try:
                existing = json.loads(graph_path.read_text(encoding="utf-8"))
                existing_hash = existing.get("source_hash", "")
            except Exception:  # noqa: BLE001
                existing_hash = ""
            if existing_hash == current_hash:
                print("✅ 图谱已最新，无需重建（source_hash 一致）")
                sys.exit(0)

        # ── 执行重建 ──
        nodes = collect_nodes(kb)
        edges = collect_edges(nodes)
        # generated_at 从文档集最大 mtime 派生（而非 wall-clock），
        # 保证「文档集不变 → 两次 build byte 级一致」（确定性序列化，PITFALLS Pitfall 4）；
        # 文档集变更 → 最大 mtime 变 → 时间戳更新，仍反映文档集状态。
        max_mtime = max((n["source_mtime"] for n in nodes), default=0)
        generated_at = datetime.fromtimestamp(max_mtime, tz=timezone.utc).astimezone().isoformat(
            timespec="seconds"
        )
        doc_count = sum(1 for n in nodes if n["node_kind"] == "document")

        # build_mode 判定
        if args.full:
            build_mode = "full"
        else:
            build_mode = "incremental"

        # 落盘前剥离 _related_edges（节点恒 10 字段，不含下划线前缀临时内存字段）
        clean_nodes = [
            {k: v for k, v in n.items() if not k.startswith("_")}
            for n in nodes
        ]

        payload = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at,
            "generator": GENERATOR,
            "source_hash": current_hash,
            "doc_count": doc_count,
            "node_count": len(clean_nodes),
            "edge_count": len(edges),
            "build_mode": build_mode,
            "nodes": clean_nodes,
            "links": edges,
        }

        # networkx 自检：load 回内存确认无悬空端点（写入前）
        import networkx as nx  # noqa: PLC0415 — PEP 723 隔离环境内导入

        try:
            nx.node_link_graph(payload, edges="links")
        except Exception as nx_exc:
            print(f"❌ networkx 自检失败（悬空端点）：{nx_exc}", file=sys.stderr)
            sys.exit(1)

        atomic_write(graph_path, payload)
        write_c6_log(kb, payload)
        print_summary(payload, graph_path, as_json=args.json)
    finally:
        # 无条件释放锁（无论成败）
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
