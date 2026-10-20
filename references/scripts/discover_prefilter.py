#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["networkx==3.6.1"]
# ///
"""discover_prefilter.py — Phase 7 候选发现引擎（确定性初筛）

跨 type Jaccard 初筛 + 三角闭合检测 + 三层排除①② + 组合分排序 + Top-N 截断，
输出候选 JSON（供 health discover 的 AI 语义裁决消费）。
与 graph_build.py（构图派生）/ graph_query.py（只读查询）/ graph_analyze.py
（涌现分析）职责分离——本脚本是第四个独立脚本。

READ-ONLY 单向派生铁律：
- 只读 graph.json + 读 .knowledge/ 文档构造比较文本；
- 绝不写 graph.json / 绝不写 .pending-edges.yaml / 绝不碰 L0 文档 / 绝不产 EXTRACTED。
- 入队（append pending[]）与 AI 语义裁决是 health discover 命令体内 AI 的领地，
  本脚本只圈候选池、绝不下结论（D-01 两段式管线脚本侧）。

仅 health discover 显式触发，绝不进 in/ask 热路径（D-13 非实时）。

用法:
    uv run discover_prefilter.py --kb-root .knowledge --json
    uv run discover_prefilter.py --kb-root .knowledge --min-jaccard 0.30 \\
        --high-jaccard 0.45 --min-shared-neighbors 2 --top-n 20 \\
        --content-weight 0.6 --struct-metric jaccard --json

仅依赖 networkx==3.6.1（禁止 default extra，避免拉 numpy/scipy/matplotlib）。
禁止引入第三方 YAML 库、embedding/向量库或外部图算法/社区检测库（D-02）。
退出码：0 成功（含空候选）/ 1 kb-root 或 graph.json 不存在或损坏 / 2 .discover.lock 并发。
"""

import argparse
import hashlib
import itertools
import json
import os
import re
import sys
import tempfile
from pathlib import Path

# ── 常量 ──────────────────────────────────────────────────────────────
GRAPH_DIR = ".graph"
DISCOVER_LOCK = ".discover.lock"
SCHEMA_VERSION = "1.0"
ALGO_VERSION = "discover-prefilter-nx3.6.1@1.0"
DEFAULT_MIN_JACCARD = 0.30
DEFAULT_HIGH_JACCARD = 0.45
DEFAULT_MIN_SHARED = 2
DEFAULT_TOP_N = 20
DEFAULT_CONTENT_WEIGHT = 0.6
COMPARE_BODY_LIMIT = 500

# 10 个业务目录（复用 graph_build.py / graph_analyze.py 文档集范围）
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

# 系统目录黑名单
SYSTEM_DIRS = {".index", ".logs", ".graph"}


# ── 复用范式：atomic_write（仿 graph_analyze.py L63-83）────────────────
def atomic_write(file_path: Path, payload: dict) -> None:
    """原子写 JSON：同盘临时文件 → flush+fsync → os.replace 覆盖。

    确定性序列化：sort_keys=True + ensure_ascii=False + indent=2。
    仅用于可选候选 JSON 落盘（默认 --json 走 stdout，本期不强制落盘）。
    绝不用于写 graph.json（READ-ONLY 铁律）。
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        dir=file_path.parent,
        prefix=".discover.",
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
    os.replace(tmp.name, file_path)


# ── 复用范式：compute_source_hash（仿 graph_analyze.py L87-116）────────
def compute_source_hash(kb_root: Path) -> str:
    """对全部业务 .md 的 (相对路径, mtime, size) 三元组排序后求 sha256。

    只算 .knowledge/ 文档集不算 graph.json——标记候选基于的文档集版本。
    返回 "sha256:<hex>"。
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


# ── load_graph 只读加载（照搬 graph_analyze.py L184-201）──────────────
def load_graph(kb_root: Path):
    """加载 graph.json → (G | None, degraded | None)。

    不存在 → (None, "graph_missing")；损坏 → (None, "graph_broken")。
    只读，绝不写 graph.json（READ-ONLY 铁律）。
    """
    import networkx as nx  # noqa: PLC0415 — PEP 723 隔离环境内导入

    graph_path = kb_root / GRAPH_DIR / "graph.json"
    if not graph_path.is_file():
        return None, "graph_missing"
    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        # 显式 directed=True 强制有向；是否多重由 node-link 数据自带字段推断
        # （graph.json 为单重有向图，省略该参数即按数据还原）。
        G = nx.node_link_graph(data, edges="links", directed=True)
        return G, None
    except Exception:  # noqa: BLE001 — 损坏图降级
        return None, "graph_broken"


# ── Jaccard 内容侧：extract_words（逐字内联搬运 distill health-rules.md:481-488）
def extract_words(text: str) -> set:
    """提取中文 bigram + 英文词汇（≥2 字符），用于 Jaccard 计算。

    与 distill 算法逐字等价，保口径统一（§Reusable Assets）。仅 stdlib re。
    """
    # 中文 bigram：相邻 2 字滑窗（提升区分度，无需 jieba）
    chinese_bigrams = [text[i:i + 2] for i in range(len(text) - 1)
                       if all('\u4e00' <= c <= '\u9fff' for c in text[i:i + 2])]
    # 英文：连续字母数字（≥2 字符），统一小写
    english = re.findall(r"[a-zA-Z0-9]{2,}", text.lower())
    return set(chinese_bigrams + english)


# ── jaccard_similarity（逐字内联搬运 distill health-rules.md:490-494）──
def jaccard_similarity(text_a: str, text_b: str) -> float:
    """交集除并集；任一空集返 0.0。与 distill 算法逐字等价。"""
    words_a, words_b = extract_words(text_a), extract_words(text_b)
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


# ── build_compare_text（手写 frontmatter 解析，禁 yaml；仿 distill 比较文本）
def build_compare_text(md_path: Path) -> tuple[str, str]:
    """构造比较文本：title + TL;DR + tags（空格连接）+ 正文前 500 字（不含 frontmatter）。

    手写行扫描解析 frontmatter（仿 graph_build.py parse_frontmatter，禁 import yaml）。
    返回 (title, compare_text)，title 供候选摘要用。
    解析失败时降级用文件名 + 全文前 500 字，不抛出。
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 — 读失败降级
        return md_path.stem, md_path.stem

    lines = text.splitlines()
    title = ""
    tags: list[str] = []

    # 定位 --- 包裹的 frontmatter 区间
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    fm_start = None
    fm_end = None
    if idx < len(lines) and lines[idx].strip() == "---":
        fm_start = idx + 1
        for i in range(fm_start, len(lines)):
            if lines[i].strip() == "---":
                fm_end = i
                break

    if fm_start is not None and fm_end is not None:
        in_tags = False
        for raw in lines[fm_start:fm_end]:
            line = raw.rstrip()
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            key_is_toplevel = raw[:1] not in (" ", "\t", "-") and ":" in raw
            if key_is_toplevel:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                in_tags = False
                if key == "title":
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                        value = value[1:-1]
                    title = value
                elif key == "tags":
                    # 行内列表 tags: [a, b, c] 或块状列表
                    if value.startswith("[") and value.endswith("]"):
                        inner = value[1:-1]
                        tags.extend(_split_tag_items(inner))
                    elif value:
                        tags.extend(_split_tag_items(value))
                    else:
                        in_tags = True
            elif in_tags:
                # 块状列表项行：  - 打印
                item = line.strip().lstrip("-").strip()
                if len(item) >= 2 and item[0] == item[-1] and item[0] in ("'", '"'):
                    item = item[1:-1]
                if item:
                    tags.append(item)

    if not title:
        title = md_path.stem

    # 正文（去 frontmatter）
    body_start = (fm_end + 1) if fm_end is not None else 0
    body_lines = lines[body_start:]
    body = "\n".join(body_lines)

    # TL;DR 段：从 ## TL;DR 标题后取到下一个 ## 标题或正文段
    tldr = _extract_tldr(body_lines)

    body_head = body.strip()[:COMPARE_BODY_LIMIT]
    compare_text = " ".join([
        title,
        tldr,
        " ".join(tags),
        body_head,
    ]).strip()
    return title, compare_text


def _split_tag_items(inner: str) -> list[str]:
    """切分行内 tags 列表项，去引号与空白。"""
    items = []
    for part in inner.split(","):
        item = part.strip()
        if len(item) >= 2 and item[0] == item[-1] and item[0] in ("'", '"'):
            item = item[1:-1]
        if item:
            items.append(item)
    return items


def _extract_tldr(body_lines: list[str]) -> str:
    """从正文行抽取 ## TL;DR 段内容（到下一个 ## 标题止）。"""
    tldr_parts: list[str] = []
    capturing = False
    for line in body_lines:
        stripped = line.strip()
        if stripped.startswith("##"):
            heading = stripped.lstrip("#").strip().lower()
            if "tl;dr" in heading or "tldr" in heading:
                capturing = True
                continue
            if capturing:
                break  # 遇到下一个 ## 标题，TL;DR 段结束
        elif capturing:
            tldr_parts.append(stripped)
    return " ".join(p for p in tldr_parts if p)


# ── load_doc_index：扫 10 业务目录按 slug 收集 type + title + compare_text ─
def load_doc_index(kb_root: Path) -> dict:
    """遍历 10 业务目录 *.md，按 node id(slug=basename 去 .md) 收集。

    slug = md_file.stem（与 graph.json node id 对齐，见 graph_build.py collect_nodes）。
    type = 顶层业务目录名。
    返回 {slug: {"type": ..., "title": ..., "compare_text": ...}}。
    """
    doc_index: dict = {}
    for dirname in BUSINESS_DIRS:
        dpath = kb_root / dirname
        if not dpath.is_dir():
            continue
        for md_file in sorted(dpath.rglob("*.md")):
            if not md_file.is_file():
                continue
            if any(
                part in SYSTEM_DIRS
                for part in md_file.relative_to(kb_root).parts[:-1]
            ):
                continue
            slug = md_file.stem
            title, compare_text = build_compare_text(md_file)
            doc_index[slug] = {
                "type": dirname,
                "title": title,
                "compare_text": compare_text,
            }
    return doc_index


# ── content_candidates：跨 type 两两比较（§1，D-04/D-05）──────────────
def content_candidates(doc_index: dict, min_j: float, high_j: float) -> dict:
    """跨 type 两两 Jaccard 比较，≥min_j 进池标 tier（high/mid）。

    仅比较「跨 type」对（同 type 是 distill 的领地，跳过，守 D-05）。
    键 = (a, b)（字典序无向键），值含 content_jaccard / tier。
    性能控制：沿用 distill 思路（同 type 内才比较以收敛对数），但 discover 仅跨 type，
    天然比同 type 全比较稀疏；超大语料可按需在外层加采样上限（本期不强制）。
    """
    out: dict = {}
    slugs = sorted(doc_index)
    for a, b in itertools.combinations(slugs, 2):
        if doc_index[a]["type"] == doc_index[b]["type"]:
            continue  # 同 type 归 distill，跳过（D-05）
        cj = jaccard_similarity(
            doc_index[a]["compare_text"], doc_index[b]["compare_text"]
        )
        if cj >= high_j:
            tier = "high"
        elif cj >= min_j:
            tier = "mid"
        else:
            continue  # < min_j 噪声丢弃，不进池
        out[(a, b)] = {"content_jaccard": round(cj, 4), "tier": tier}
    return out


# ── triangle_candidates：三角闭合结构侧（§2，D-04）────────────────────
def triangle_candidates(G, min_shared: int, struct_metric: str) -> dict:
    """补捞 Jaccard 漏报的结构性关联（D-04）。

    G.to_undirected() 后对未连接对求 nx.common_neighbors；shared≥min_shared
    才算结构候选（shared==1 爆量级噪声，glossary 高 degree 枢纽，§2）。
    neighbor-set Jaccard（值域 [0,1]）作 struct 信号便于与内容 Jaccard 同尺度合并；
    adamic_adar 作备选（给高 degree 邻居降权，§Open Questions 1）。
    键 = (a, b)（字典序），值含 struct_jaccard / shared_neighbors。
    """
    import networkx as nx  # noqa: PLC0415 — PEP 723 隔离环境内导入

    out: dict = {}
    UG = G.to_undirected()
    nodes = sorted(UG.nodes)
    for a, b in itertools.combinations(nodes, 2):
        if UG.has_edge(a, b):
            continue  # 已连接 = 三角已闭合非缺失，跳过
        common = list(nx.common_neighbors(UG, a, b))
        shared = len(common)
        if shared < min_shared:
            continue
        Na, Nb = set(UG.neighbors(a)), set(UG.neighbors(b))
        if struct_metric == "adamic_adar":
            # Adamic-Adar 备选：高 degree 邻居降权，再归一化到 [0,1]
            try:
                aa = list(nx.adamic_adar_index(UG, [(a, b)]))
                raw = aa[0][2] if aa else 0.0
            except Exception:  # noqa: BLE001 — 极端图兜底
                raw = 0.0
            # 归一化：AA / (AA + 1) 单调压到 [0,1)，便于与内容 Jaccard 合并
            struct = raw / (raw + 1.0) if raw > 0 else 0.0
        else:  # 默认 jaccard：neighbor-set Jaccard
            union = Na | Nb
            struct = len(Na & Nb) / len(union) if union else 0.0
        out[(a, b)] = {
            "struct_jaccard": round(struct, 4),
            "shared_neighbors": shared,
        }
    return out


# ── exclude_existing：三层排除①②（§4，D-06）─────────────────────────
def exclude_existing(pair_keys, G) -> set:
    """三层排除①②（D-06，脚本侧）。

    ① 已在 graph.json links（G.has_edge 双向，links 恒权威边）→ 排除；
    ② related 已互引等价于 links 已含该向边（信任 graph.json，不重读文档）→ ①已覆盖；
    ③ reject-history 留给 AI 入队前做（队列归 AI 管，§4 边界，脚本不读 .pending-edges.yaml）。
    返回需排除的候选键集合。
    """
    excluded = set()
    for (a, b) in pair_keys:
        if G.has_edge(a, b) or G.has_edge(b, a):
            excluded.add((a, b))
    return excluded


# ── rank_and_truncate：组合分排序 + Top-N（§2，排除之后做）──────────────
def rank_and_truncate(survivors: dict, content_weight: float, top_n: int) -> list:
    """组合分 signal = cw*content_jaccard + (1-cw)*struct_jaccard，降序 + (a,b) tiebreak，Top-N。

    survivors: {(a,b): {content_jaccard, struct_jaccard, shared_neighbors, tier,
                        has_edge_st, has_edge_ts}}。
    Top-N 截断在三层排除之后做（否则名额被无效对占用，§2）。
    确定性：按 (-signal, a, b) 排序，同分 (a,b) 字典序 tiebreak。
    """
    ranked = []
    for (a, b), info in survivors.items():
        cj = info.get("content_jaccard", 0.0)
        sj = info.get("struct_jaccard", 0.0)
        signal = round(content_weight * cj + (1.0 - content_weight) * sj, 4)
        ranked.append((signal, a, b, info))
    ranked.sort(key=lambda r: (-r[0], r[1], r[2]))
    out = []
    for signal, a, b, info in ranked[:top_n]:
        out.append({
            "source": a,
            "target": b,
            "content_jaccard": info.get("content_jaccard", 0.0),
            "struct_jaccard": info.get("struct_jaccard", 0.0),
            "shared_neighbors": info.get("shared_neighbors", 0),
            "signal": signal,
            "tier": info.get("tier", "mid"),
            "has_edge_st": info.get("has_edge_st", False),
            "has_edge_ts": info.get("has_edge_ts", False),
            "source_location": f"similarity:{a}↔{b}:{signal}",
        })
    return out


# ── 主流程 ────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(
        description="knowledge-wiki Phase 7 候选发现引擎（跨 type Jaccard 初筛 + 三角闭合 + 排除①② + Top-N）"
    )
    ap.add_argument("--kb-root", default=".knowledge", help="知识库根目录（默认 .knowledge）")
    ap.add_argument("--min-jaccard", type=float, default=DEFAULT_MIN_JACCARD,
                    help=f"内容初筛进池下限（默认 {DEFAULT_MIN_JACCARD}）")
    ap.add_argument("--high-jaccard", type=float, default=DEFAULT_HIGH_JACCARD,
                    help=f"高信号档阈值（默认 {DEFAULT_HIGH_JACCARD}）")
    ap.add_argument("--min-shared-neighbors", type=int, default=DEFAULT_MIN_SHARED,
                    help=f"三角闭合最小共享邻居数（默认 {DEFAULT_MIN_SHARED}）")
    ap.add_argument("--top-n", type=int, default=DEFAULT_TOP_N,
                    help=f"候选 Top-N 截断（默认 {DEFAULT_TOP_N}）")
    ap.add_argument("--content-weight", type=float, default=DEFAULT_CONTENT_WEIGHT,
                    help=f"组合分内容权重（默认 {DEFAULT_CONTENT_WEIGHT}）")
    ap.add_argument("--struct-metric", choices=["jaccard", "adamic_adar"],
                    default="jaccard", help="结构信号度量（默认 jaccard，备选 adamic_adar）")
    ap.add_argument("--json", action="store_true",
                    help="以 JSON 输出候选（供 health discover 的 AI 裁决消费）")
    args = ap.parse_args()

    kb = Path(args.kb_root)
    if not kb.is_dir():
        print(f"❌ 知识库根目录不存在：{kb}", file=sys.stderr)
        sys.exit(1)

    gdir = kb / GRAPH_DIR
    # graph.json 不存在时 gdir 可能也不存在；不主动建（READ-ONLY 倾向），
    # 但锁需落在 .graph/ 下，故仅在 gdir 已存在时取锁；否则降级判定接管。
    lock = gdir / DISCOVER_LOCK
    if gdir.is_dir() and lock.exists():
        print(
            "⚠️ 候选发现正在进行中（.discover.lock 存在），请稍候或删除残留锁后重试",
            file=sys.stderr,
        )
        sys.exit(2)

    lock_taken = False
    if gdir.is_dir():
        try:
            lock.write_text(f"{os.getpid()}", encoding="utf-8")
            lock_taken = True
        except OSError:
            lock_taken = False

    try:
        # ── 降级前置 ──
        G, degraded = load_graph(kb)
        if degraded == "graph_missing":
            print("❌ 未编译图谱，请先运行 health graph-build", file=sys.stderr)
            sys.exit(1)
        if degraded == "graph_broken":
            print("❌ 图谱损坏，建议重建 health graph-build", file=sys.stderr)
            sys.exit(1)

        # ── 主流程：初筛 → 合并两路 → 排除①② → 排序 → Top-N → 组装候选 JSON ──
        doc_index = load_doc_index(kb)
        source_hash = compute_source_hash(kb)
        node_count = G.number_of_nodes()

        content_map = content_candidates(doc_index, args.min_jaccard, args.high_jaccard)
        struct_map = triangle_candidates(G, args.min_shared_neighbors, args.struct_metric)

        # ── 合并两路（content ∪ struct，§2），缺失一路实算补回 ──
        all_keys = set(content_map) | set(struct_map)
        merged: dict = {}
        for (a, b) in all_keys:
            cinfo = content_map.get((a, b))
            sinfo = struct_map.get((a, b))
            # content_jaccard：命中内容路直接取；否则用 compare_text 实算补回
            if cinfo is not None:
                content_jaccard = cinfo["content_jaccard"]
                tier = cinfo["tier"]
            else:
                ta = doc_index.get(a, {}).get("compare_text", "")
                tb = doc_index.get(b, {}).get("compare_text", "")
                content_jaccard = round(jaccard_similarity(ta, tb), 4)
                tier = "mid"
            # struct_jaccard / shared：命中结构路直接取；否则默认 0
            if sinfo is not None:
                struct_jaccard = sinfo["struct_jaccard"]
                shared = sinfo["shared_neighbors"]
            else:
                struct_jaccard = 0.0
                shared = 0
            merged[(a, b)] = {
                "content_jaccard": content_jaccard,
                "struct_jaccard": struct_jaccard,
                "shared_neighbors": shared,
                "tier": tier,
                "has_edge_st": G.has_edge(a, b),
                "has_edge_ts": G.has_edge(b, a),
            }

        # ── 排除①②（先排除，再 Top-N，§2）──
        excluded = exclude_existing(set(merged), G)
        survivors = {k: v for k, v in merged.items() if k not in excluded}

        # ── 组合分排序 + Top-N（排除之后做）──
        candidates = rank_and_truncate(survivors, args.content_weight, args.top_n)

        # ── 组装候选 JSON ──
        payload = {
            "schema_version": SCHEMA_VERSION,
            "algo_version": ALGO_VERSION,
            # 不写时间戳：候选 JSON 须两跑 byte 级一致（确定性），版本由 source_hash 标记
            "params": {
                "min_jaccard": args.min_jaccard,
                "high_jaccard": args.high_jaccard,
                "min_shared_neighbors": args.min_shared_neighbors,
                "top_n": args.top_n,
                "content_weight": args.content_weight,
                "struct_metric": args.struct_metric,
            },
            "source_hash": source_hash,
            "node_count": node_count,
            "candidate_count": len(candidates),
            "candidates": candidates,
        }

        # ── 输出（READ-ONLY：绝不写 graph.json / 绝不写 .pending-edges.yaml / 不碰文档）──
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            high_count = sum(1 for c in candidates if c["tier"] == "high")
            if not candidates:
                print("✅ 无新涌现关联候选")
            else:
                print(f"🔍 候选发现完成：{len(candidates)} 个候选（高信号 {high_count} 个）")
            print(f"   节点：{node_count} | 跨 type 内容候选：{len(content_map)} | 结构候选：{len(struct_map)}")
            print(f"   Top-N：{args.top_n} | source_hash：{source_hash}")
        # 空候选是正常结果，正常 exit 0（隐式）。

    finally:
        if lock_taken:
            lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()