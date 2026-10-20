#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["networkx==3.6.1", "scipy"]  # scipy 供 nx.pagerank 使用（networkx 3.x 必需）
# ///
"""graph_analyze.py — Phase 6 涌现分析引擎：非实时全量跑 Louvain 社区检测 + 中心度 + 内聚度

落 communities.json + 回填 graph.json 预留字段。
与 graph_build.py（构图派生）/ graph_query.py（只读查询）职责分离。
仅 health graph 显式触发，绝不进 in/ask 热路径（ANALYZE-05）。

用法:
    uv run graph_analyze.py --kb-root .knowledge
    uv run graph_analyze.py --kb-root .knowledge --seed 42 --min-nodes 10 --json

仅依赖 networkx==3.6.1（禁止 default extra，避免拉 numpy/scipy/matplotlib）。
禁止引入第三方 YAML 库、外部社区检测库、外部图计算库。
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

# ── 常量 ──────────────────────────────────────────────────────────────
GRAPH_DIR = ".graph"
ANALYZE_LOCK = ".analyze.lock"
SCHEMA_VERSION = "1.0"
ALGO_VERSION = "louvain-nx3.6.1@1.0"
COMMUNITIES_FILE = "communities.json"
DEFAULT_SEED = 42
DEFAULT_MIN_NODES = 10
GOD_NODE_TOP_N = 10

# 10 个业务目录（复用 graph_build.py 文档集范围）
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

# 告警收集
warnings: list[str] = []


# ── 复用范式：atomic_write（仿 graph_build.py L403-424）────────────────
def atomic_write(file_path: Path, payload: dict) -> None:
    """原子写 JSON：同盘临时文件 → flush+fsync → os.replace 覆盖。

    临时文件建在 file_path.parent（同分区），确保 os.replace 原子。
    确定性序列化：sort_keys=True + ensure_ascii=False + indent=2。
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        dir=file_path.parent,
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
    os.replace(tmp.name, file_path)


# ── 复用范式：compute_source_hash（仿 graph_build.py L370-399）────────
def compute_source_hash(kb_root: Path) -> str:
    """对全部业务 .md 的 (相对路径, mtime, size) 三元组排序后求 sha256。

    只算 .knowledge/ 文档集不算 graph.json——破「图自我过期」循环的根本（§6.3）。
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


# ── 复用范式：resolve_user_id + write_c6_log（仿 graph_build.py L563-622）
def resolve_user_id() -> str | None:
    """user-id 获取：KB_OWNER → git → whoami → None。"""
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
    """分析成功后追加一条操作日志到 .logs/personal/{user-id}.md。

    复用既有 log-rules.md 通道，layer 标 graph-analyze（区别于 graph-build）。
    user-id 缺失时降级跳过，不阻断分析。
    ⚠️ W1 修正：取键改为 graph-analyze 语义，用 payload.get() 防 KeyError。
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
            "node_count": payload.get("node_count"),
            "community_count": payload.get("community_count"),
            "modularity": payload.get("modularity"),
            "skipped": payload.get("skipped"),
            "source_hash": payload.get("source_hash"),
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
            f"\n## [{now}] @{user_id} | health | graph-analyze\n"
            f"  detail: {json.dumps(detail, ensure_ascii=False)}\n"
        )
        with log_file.open("a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as exc:  # noqa: BLE001 — C6 日志失败不阻断分析
        warnings.append(f"C6 日志写入失败（不阻断分析）：{exc}")


# ── load_graph 只读加载（仿 graph_query.py L38-54）───────────────────
def load_graph(kb_root: Path):
    """加载 graph.json → (G | None, degraded | None)。

    不存在 → (None, "graph_missing")；损坏 → (None, "graph_broken")。
    只读，绝不写 graph.json。
    """
    import networkx as nx  # noqa: PLC0415 — PEP 723 隔离环境内导入

    graph_path = kb_root / GRAPH_DIR / "graph.json"
    if not graph_path.is_file():
        return None, "graph_missing"
    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        G = nx.node_link_graph(data, edges="links", directed=True,
                               multigraph=False)
        return G, None
    except Exception:  # noqa: BLE001 — 损坏图降级
        return None, "graph_broken"


# ── 有向转无向加权图（RESEARCH §2.3）────────────────────────────────
def build_undirected_for_louvain(G):
    """有向 graph.json → 确定性无向加权图（合并双向边累加权重）。

    确定性三要素：① 节点按 slug 字典序 add ② 边按 (min,max) 字典序 add
    ③ 双向边累加 weight（A→B + B→A = weight 2）。
    绝不修改原 G（新建图，只读 G）。
    双向边累加权重保留「双向关联更强」信号（§2.2）。
    自环（s==t）跳过（不影响社区结构）。
    """
    import networkx as nx  # noqa: PLC0415 — PEP723 隔离环境内导入

    UG = nx.Graph()
    # ① 节点按 slug 字典序加入（消除遍历顺序非确定性）
    for n in sorted(G.nodes):
        UG.add_node(n, **G.nodes[n])
    # ② 边按无向键 (min,max) 字典序聚合权重
    weight_acc: dict[tuple[str, str], int] = {}
    for s, t in G.edges:
        if s == t:  # 自环跳过
            continue
        key = (s, t) if s <= t else (t, s)
        weight_acc[key] = weight_acc.get(key, 0) + 1
    for (s, t) in sorted(weight_acc):
        UG.add_edge(s, t, weight=weight_acc[(s, t)])
    return UG


# ── Louvain 社区检测 + 确定性社区 id 重映射（RESEARCH §2.3）─────────
def detect_communities(UG, seed: int):
    """Louvain 社区检测 + 确定性社区 id 重映射。

    返回 (node_to_comm, sorted_comms)。
    社区 id 按成员最小 slug 字典序重映射，消除 Louvain 内部任意编号的
    非确定性——byte 级可复现的关键第四要素（§2.1）。
    """
    import networkx as nx  # noqa: PLC0415

    raw_communities = nx.community.louvain_communities(UG, weight="weight", seed=seed)
    # ★ 确定性重映射：每社区取成员最小 slug 作排序键
    sorted_comms = sorted(raw_communities, key=lambda c: min(c))
    node_to_comm: dict[str, int] = {}
    for new_id, members in enumerate(sorted_comms):
        for node in members:
            node_to_comm[node] = new_id
    return node_to_comm, sorted_comms


# ── per-community 内聚度（RESEARCH §4.2）────────────────────────────
def compute_cohesion(UG, node_to_comm):
    """每社区内聚度 = 内部边占比 internal / (internal + boundary)。

    ANALYZE-03：各子领域健康度按社区给分（0~1，越高越自洽）。
    在无向 UG 上算（社区是无向概念）；用 weight 加权（双向边算 2）。
    低 cohesion = 横切性强（正常）非质量差（§4.1，守 C1）。
    孤立社区（无任何边）→ 0.0。
    """
    internal = defaultdict(int)
    boundary = defaultdict(int)
    for s, t, data in UG.edges(data=True):
        w = data.get("weight", 1)
        cs, ct = node_to_comm[s], node_to_comm[t]
        if cs == ct:
            internal[cs] += w
        else:
            boundary[cs] += w
            boundary[ct] += w
    cohesion = {}
    for comm_id in set(node_to_comm.values()):
        i, b = internal[comm_id], boundary[comm_id]
        cohesion[comm_id] = round(i / (i + b), 4) if (i + b) > 0 else 0.0
    return cohesion, dict(internal), dict(boundary)


# ── 中心度三度全算 + god nodes（RESEARCH §3）─────────────────────────
def compute_centrality(G, top_n: int = GOD_NODE_TOP_N):
    """三中心度全算 + god_nodes 榜 + is_hub_candidate 业务语义校验。

    三度全算供人工综合判断；hub_candidate 双高+status 校验（§3.3 D-Q4）；
    god_nodes 按 degree 降序 top N；回填用 degree_centrality（§3.4）。
    在有向 G 上算（graph.json 是有向图）。
    """
    import networkx as nx  # noqa: PLC0415

    degree_c = nx.degree_centrality(G)
    betweenness_c = nx.betweenness_centrality(G)
    try:
        pagerank_c = nx.pagerank(G)
    except ImportError:
        raise  # 依赖缺失（scipy/numpy）必须显式失败，绝不静默兜底为 0.0
    except Exception:  # noqa: BLE001 — 空/极端小图 pagerank 兜底
        pagerank_c = {n: 0.0 for n in G.nodes}

    # 阈值取相对分位（§3.3：mean + 1σ；空/单节点退化时兜底）
    deg_values = list(degree_c.values())
    btw_values = list(betweenness_c.values())

    if len(deg_values) >= 2:
        deg_thr = mean(deg_values) + pstdev(deg_values)
        btw_thr = mean(btw_values) + pstdev(btw_values)
    elif len(deg_values) == 1:
        deg_thr = deg_values[0]
        btw_thr = btw_values[0]
    else:
        deg_thr = 0.0
        btw_thr = 0.0

    # god_nodes 榜：所有节点按 degree 降序取 top N，同分用 id 字典序 tiebreak
    all_nodes_sorted = sorted(
        G.nodes,
        key=lambda n: (-degree_c.get(n, 0.0), n)
    )
    god_nodes = []
    for nid in all_nodes_sorted[:top_n]:
        attrs = G.nodes[nid]
        status = attrs.get("status", "draft")
        dc = degree_c.get(nid, 0.0)
        bc = betweenness_c.get(nid, 0.0)
        pr = pagerank_c.get(nid, 0.0)

        # is_hub_candidate: 高 degree + 高 betweenness 且 canonical/active
        high_centrality = (dc >= deg_thr) and (bc >= btw_thr)
        high_status = status in ("canonical", "active")
        is_hub = high_centrality and high_status

        if is_hub:
            hint = f"涌现提示：高连接+高桥接且为 {status} 知识，可能是核心知识枢纽，供人工判断"
        elif high_centrality and not high_status:
            hint = f"高连接度节点（status={status}），不作为枢纽候选"
        else:
            hint = "连接度较高的知识节点"

        god_nodes.append({
            "id": nid,
            "title": attrs.get("title", nid),
            "type": attrs.get("type", ""),
            "status": status,
            "degree_centrality": round(dc, 4),
            "betweenness_centrality": round(bc, 4),
            "pagerank": round(pr, 4),
            "is_hub_candidate": is_hub,
            "hint": hint,
        })

    centrality_map = degree_c
    return centrality_map, god_nodes


# ── 孤岛检测（RESEARCH §3.4）────────────────────────────────────────
def detect_islands(G, centrality_map):
    """isolates + 低 degree 双信号 → islands[]。

    isolates: in_degree + out_degree == 0（纯孤儿）。
    低 degree: G.degree(n) == 1（准孤岛，仅 1 条边）。
    措辞中性「待连接」非「坏文档」（§7.3 守 C1）。
    按 id 字典序排（确定性）。
    在有向 G 上算。
    """
    import networkx as nx  # noqa: PLC0415

    isolates = set(nx.isolates(G))
    islands = []

    for nid in sorted(G.nodes):
        attrs = G.nodes[nid]
        deg = G.degree(nid)
        if nid in isolates:
            islands.append({
                "id": nid,
                "title": attrs.get("title", nid),
                "type": attrs.get("type", ""),
                "status": attrs.get("status", "draft"),
                "degree": deg,
                "hint": "孤岛：无任何关联边，待连接",
            })
        elif deg == 1:
            islands.append({
                "id": nid,
                "title": attrs.get("title", nid),
                "type": attrs.get("type", ""),
                "status": attrs.get("status", "draft"),
                "degree": deg,
                "hint": "准孤岛：仅 1 条边，待加强连接",
            })

    return islands


# ── 回填 graph.json 预留字段（RESEARCH §6.1）──────────────────────────
def backfill_graph_json(graph_path: Path, node_to_comm: dict, centrality_map: dict) -> int:
    """读 graph.json → 改节点 centrality/community → 原子写回。

    只改 centrality/community 两预留字段，不动 schema/边/顶层。
    回填不碰文档故不影响 source_hash（§6.3 破图自我过期循环）。
    skipped 时 community 全 None、centrality 仍回填。
    返回回填的节点数。
    """
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes_updated = 0
    for node in data["nodes"]:
        nid = node["id"]
        node["centrality"] = round(centrality_map[nid], 4) if nid in centrality_map else None
        node["community"] = node_to_comm.get(nid)
        nodes_updated += 1
    atomic_write(graph_path, data)
    return nodes_updated


# ── 主流程 ────────────────────────────────────────────────────────────
def main() -> None:
    import networkx as nx  # noqa: PLC0415 — PEP 723 隔离环境内导入

    ap = argparse.ArgumentParser(
        description="knowledge-wiki Phase 6 涌现分析引擎（社区检测 + 中心度 + 内聚度）"
    )
    ap.add_argument("--kb-root", default=".knowledge", help="知识库根目录（默认 .knowledge）")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"Louvain 随机种子（默认 {DEFAULT_SEED}）")
    ap.add_argument("--min-nodes", type=int, default=DEFAULT_MIN_NODES, help=f"社区检测最小节点门槛（默认 {DEFAULT_MIN_NODES}）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出摘要（供 CI / health 报告消费）")
    args = ap.parse_args()

    kb = Path(args.kb_root)
    if not kb.is_dir():
        print(f"❌ 知识库根目录不存在：{kb}", file=sys.stderr)
        sys.exit(1)

    gdir = kb / GRAPH_DIR
    gdir.mkdir(exist_ok=True)
    lock = gdir / ANALYZE_LOCK

    # 入口锁检测
    if lock.exists():
        print(
            "⚠️ 图分析正在进行中（.analyze.lock 存在），请稍候或删除残留锁后重试",
            file=sys.stderr,
        )
        sys.exit(2)
    lock.write_text(f"{os.getpid()}", encoding="utf-8")

    try:
        # ── 降级前置 ──
        G, degraded = load_graph(kb)
        if degraded == "graph_missing":
            print("❌ 未编译图谱，请先运行 health graph-build", file=sys.stderr)
            sys.exit(1)
        if degraded == "graph_broken":
            print("❌ 图谱损坏，建议重建 health graph-build", file=sys.stderr)
            sys.exit(1)

        graph_path = gdir / "graph.json"
        communities_path = gdir / COMMUNITIES_FILE
        seed = args.seed
        min_nodes = args.min_nodes

        # 读 graph.json 顶层元信息（透传 generated_at/source_hash 保确定性）
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        generated_at = data.get("generated_at")
        source_hash = data.get("source_hash")

        node_count = G.number_of_nodes()
        edge_count = G.number_of_edges()

        # ── 中心度 + 孤岛（始终跑，不受门槛影响）──
        centrality_map, god_nodes = compute_centrality(G)
        islands = detect_islands(G, centrality_map)

        # ── 社区检测（小语料跳过）──
        skipped = node_count < min_nodes
        if skipped:
            skipped_reason = f"语料过小（节点数 {node_count} < {min_nodes}），跳过社区检测，需更多节点形成有意义的社区"
            node_to_comm: dict[str, int | None] = {n: None for n in G.nodes}
            communities_list: list[dict] = []
            modularity = None
            community_count = 0
        else:
            skipped_reason = None
            UG = build_undirected_for_louvain(G)
            node_to_comm_int, sorted_comms = detect_communities(UG, seed)
            node_to_comm = node_to_comm_int  # type: ignore[assignment]
            cohesion, internal, boundary_dict = compute_cohesion(UG, node_to_comm_int)
            modularity = round(nx.community.modularity(UG, sorted_comms, weight="weight"), 4)
            community_count = len(sorted_comms)

            # 组装 communities[]
            communities_list = []
            for comm_id, members_set in enumerate(sorted_comms):
                members_sorted = sorted(members_set)
                # dominant_type: 成员里最多的 type
                type_counts: dict[str, int] = {}
                for m in members_sorted:
                    t = G.nodes[m].get("type", "")
                    type_counts[t] = type_counts.get(t, 0) + 1
                dominant_type = max(type_counts, key=lambda k: (type_counts[k], k)) if type_counts else ""

                communities_list.append({
                    "id": comm_id,
                    "size": len(members_sorted),
                    "members": members_sorted,
                    "dominant_type": dominant_type,
                    "cohesion": cohesion.get(comm_id, 0.0),
                    "internal_edges": internal.get(comm_id, 0),
                    "boundary_edges": boundary_dict.get(comm_id, 0),
                })

        # ── 回填 graph.json ──
        # centrality_map 是 degree_centrality（float），node_to_comm 是社区 id 或 None
        nodes_updated = backfill_graph_json(graph_path, node_to_comm, centrality_map)

        # ── 组装 communities.json（§1.3 全字段）──
        communities_payload = {
            "schema_version": SCHEMA_VERSION,
            "algo_version": ALGO_VERSION,
            "seed": seed,
            "generated_at": generated_at,
            "source_hash": source_hash,
            "min_nodes": min_nodes,
            "node_count": node_count,
            "edge_count": edge_count,
            "skipped": skipped,
            "skipped_reason": skipped_reason,
            "modularity": modularity,
            "community_count": community_count,
            "communities": communities_list,
            "god_nodes": god_nodes,
            "islands": islands,
            "backfilled": {
                "graph_json": str(graph_path),
                "nodes_updated": nodes_updated,
                "centrality_metric": "degree_centrality",
            },
        }

        # ── 落盘 communities.json ──
        atomic_write(communities_path, communities_payload)

        # ── C6 日志 ──
        write_c6_log(kb, {
            "node_count": node_count,
            "community_count": community_count,
            "modularity": modularity,
            "skipped": skipped,
            "source_hash": source_hash,
        })

        # ── 摘要输出 ──
        if args.json:
            summary = {
                "node_count": node_count,
                "edge_count": edge_count,
                "community_count": community_count,
                "modularity": modularity,
                "skipped": skipped,
                "god_nodes_count": len(god_nodes),
                "islands_count": len(islands),
                "nodes_backfilled": nodes_updated,
                "source_hash": source_hash,
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            if skipped:
                print(f"⚠️ {skipped_reason}")
            else:
                print(f"🕸️ 社区检测完成：{community_count} 个社区，modularity={modularity}")
            print(f"   节点：{node_count} | 边：{edge_count}")
            print(f"   god nodes：{len(god_nodes)} | 孤岛：{len(islands)}")
            print(f"   回填：{nodes_updated} 个节点（centrality=degree, community）")
            print(f"   产物：{communities_path}")

    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
