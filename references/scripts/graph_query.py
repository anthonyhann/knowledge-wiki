#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["networkx==3.6.1"]
# ///
"""graph_query.py — knowledge-wiki 只读图查询引擎（Phase 4）

只读 graph.json 与 .pending-edges.yaml，绝不写 graph.json、绝不改文档、绝不改 graph_build.py。
三子命令 neighbors/node/count 分别喂 ask graph / ask explain / 裸 ask 轻提示。

用法:
    uv run graph_query.py neighbors <slug> --kb-root .knowledge
    uv run graph_query.py node <slug> --kb-root .knowledge
    uv run graph_query.py count <slug> --kb-root .knowledge
"""

import argparse
import json
import re
import sys
from collections import deque
from datetime import date
from pathlib import Path

# ── 常量 ──────────────────────────────────────────────────────────────
GRAPH_DIR = ".graph"
GRAPH_JSON = "graph.json"
PENDING_EDGES = ".pending-edges.yaml"
DEFAULT_HOPS = 1
MAX_HOPS = 3
DEFAULT_BUDGET = 60

# status 优先级（消歧排序用，沿 ask-rules.md status 优先级）
STATUS_PRIORITY = {"canonical": 0, "active": 1, "draft": 2, "deprecated": 3}


# ── 加载函数 ──────────────────────────────────────────────────────────
def load_graph(kb_root: Path):
    """加载 graph.json → (G | None, degraded | None)。

    不存在/损坏 → (None, "graph_missing") 退 0（降级非错误，守零破坏）。
    """
    import networkx as nx  # noqa: PLC0415 — PEP 723 隔离环境内导入

    graph_path = kb_root / GRAPH_DIR / GRAPH_JSON
    if not graph_path.is_file():
        return None, "graph_missing"
    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        # 强制加载为有向图（边有 source/target 方向语义）
        G = nx.node_link_graph(data, edges="links", directed=True, multigraph=False)
        return G, None
    except Exception:  # noqa: BLE001 — 损坏图当作图层不可用降级，不抛栈
        return None, "graph_missing"


# ── 节点定位（四级，MVP 前三级）─────────────────────────────────────
def locate_node(G, query: str):
    """四级节点定位 → (node_id | None, candidates[], degraded | None)。

    Level 1: slug 精确匹配
    Level 2: title 完全匹配
    Level 3: title 子串匹配（不分大小写）
    Level 4: tags —— MVP 不做（graph.json 节点无 tags 字段，由 ask 层先用
              四层检索定位 slug 再喂精确 slug）
    """
    # Level 1: slug 精确
    if query in G.nodes:
        return query, [], None

    # Level 2: title 完全匹配
    hits = [n for n in G.nodes if G.nodes[n].get("title") == query]
    if len(hits) == 1:
        return hits[0], [], None
    if len(hits) > 1:
        candidates = _build_candidates(G, hits)
        return None, candidates, "ambiguous"

    # Level 3: title 子串匹配（不分大小写）
    q_lower = query.lower()
    hits = [n for n in G.nodes if q_lower in (G.nodes[n].get("title") or "").lower()]
    if len(hits) == 1:
        return hits[0], [], None
    if len(hits) > 1:
        candidates = _build_candidates(G, hits)
        return None, candidates, "ambiguous"

    # Level 4: tags — MVP 不做
    # 0 命中
    return None, [], "node_not_found"


def _build_candidates(G, hit_ids: list) -> list:
    """构建候选列表，按 (STATUS_PRIORITY[status], slug) 排序。"""
    candidates = []
    for nid in hit_ids:
        attrs = G.nodes[nid]
        candidates.append({
            "id": nid,
            "title": attrs.get("title", nid),
            "type": attrs.get("type", ""),
            "status": attrs.get("status", "draft"),
        })
    candidates.sort(key=lambda c: (STATUS_PRIORITY.get(c["status"], 9), c["id"]))
    return candidates


# ── 节点视图 ──────────────────────────────────────────────────────────
def node_view(G, node_id: str) -> dict:
    """从 G.nodes[node_id] 取节点视图字段。"""
    attrs = G.nodes[node_id]
    return {
        "id": node_id,
        "title": attrs.get("title", node_id),
        "type": attrs.get("type", ""),
        "status": attrs.get("status", "draft"),
        "expires": attrs.get("expires", "never"),
        "node_kind": attrs.get("node_kind", "document"),
        "path": attrs.get("path", ""),
    }


# ── 边对象构造器 ──────────────────────────────────────────────────────
def edge_obj(G, s: str, t: str, origin: str = "links") -> dict:
    """从 G.edges[s,t] 构造 §1.3 edge schema 对象。"""
    attrs = G.edges[s, t] if G.has_edge(s, t) else {}
    confidence = attrs.get("confidence", "EXTRACTED")
    reviewed = attrs.get("reviewed", True)
    authoritative = (confidence == "EXTRACTED" and reviewed is True)
    return {
        "source": s,
        "target": t,
        "relation": attrs.get("relation", "references"),
        "confidence": confidence,
        "reviewed": reviewed,
        "source_location": attrs.get("source_location", ""),
        "authoritative": authoritative,
        "origin": origin,
    }


# ── 统一输出 ──────────────────────────────────────────────────────────
def base_payload(subcommand: str, **kw) -> dict:
    """§1.3 schema 全字段基础 payload，缺省安全默认。"""
    payload = {
        "ok": True,
        "subcommand": subcommand,
        "degraded": None,
        "center": None,
        "candidates": [],
        "neighbors": [],
        "edges": [],
        "truncated": False,
        "budget": DEFAULT_BUDGET,
        "budget_used": 0,
        "hops": DEFAULT_HOPS,
        "include_inferred": False,
        "authoritative_edge_count": 0,
        "stats": {"node_count": 0, "edge_count": 0, "by_confidence": {"EXTRACTED": 0, "INFERRED": 0, "AMBIGUOUS": 0}},
    }
    payload.update(kw)
    return payload


def emit(payload: dict) -> None:
    """确定性 JSON 输出（固定缩进，可读+可复现）。"""
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False))


# ── slug 归一化（RESEARCH §7.2 头号风险防御）────────────────────────
def normalize_slug(value: str) -> str:
    """剥离可能存在的 dir/ 前缀，兼容 ops/print-timeout 与 print-timeout。

    RESEARCH §7.2：pending dir/slug ≠ node id 纯 slug，归一化对齐。
    """
    return value.split("/")[-1]


# ── pending 边文本扫描（禁 pyyaml，标准库行扫描）────────────────────
def load_pending_edges(kb_root: Path) -> list:
    """标准库文本扫描 .pending-edges.yaml → list[dict]。

    不存在 → []（静默）。任何解析异常 → []（当作无 pending 叠加，
    绝不让 --include-inferred 崩掉主查询）。
    """
    pending_path = kb_root / PENDING_EDGES
    if not pending_path.is_file():
        return []
    try:
        text = pending_path.read_text(encoding="utf-8")
        return _parse_pending_block(text)
    except Exception:  # noqa: BLE001 — 降级为「无 pending 叠加」
        return []


def _parse_pending_block(text: str) -> list:
    """行扫描 pending: 块，提取待审条目。

    仿 graph_build.py parse_frontmatter 块扫描去引号范式。
    """
    lines = text.splitlines()
    entries = []
    in_pending = False
    current_entry = None

    for line in lines:
        stripped = line.strip()
        # 检测 pending: 块开始（顶层 key）
        if line[:1] not in (" ", "\t", "-", "#") and stripped.startswith("pending:"):
            in_pending = True
            continue
        # 检测下一个顶层 key 结束 pending 块
        if in_pending and line[:1] not in (" ", "\t", "-", "#") and ":" in stripped:
            in_pending = False
            if current_entry:
                entries.append(current_entry)
                current_entry = None
            continue
        if not in_pending:
            continue
        # 块内：检测条目起始 = 任意 "- <key>:" 列表项（不硬编码首字段名，
        # 真实 schema 条目以 "- source:" 起始，无 id 字段）
        is_item_start = stripped.startswith("- ") and ":" in stripped
        if is_item_start:
            if current_entry:
                entries.append(current_entry)
            current_entry = {}
            # 不 continue —— 首字段需在下方统一解析逻辑里被记录
        # 块内字段 "key: value"（含列表项首字段）
        if current_entry is not None and ":" in stripped:
            # 去除列表项前缀 "- " 如果存在
            field_line = stripped
            if field_line.startswith("- "):
                field_line = field_line[2:]
            key, _, value = field_line.partition(":")
            key = key.strip()
            value = _extract_value(value)
            if key in ("source", "target", "relation", "confidence", "source_location", "reviewed", "decision"):
                if key == "reviewed":
                    current_entry[key] = value.lower() == "true"
                else:
                    current_entry[key] = value
    # 末尾条目
    if current_entry:
        entries.append(current_entry)

    # 只取 reviewed==false 的待审条目
    return [e for e in entries if e.get("reviewed") is False]


def _extract_value(raw: str) -> str:
    """去引号、strip。仿 graph_build.py L209。"""
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value.strip()


# ── pending 边叠加逻辑 ────────────────────────────────────────────────
def overlay_pending(G, scope_nodes: set, authoritative_keys: set, pending_edges: list,
                    budget_state: dict | None = None) -> list:
    """叠加 pending 边到子图。

    RESEARCH §7.3: (source,target,relation) 去重权威优先。
    scope_nodes: 当前子图已纳入的节点集。
    authoritative_keys: 权威边三元组 set {(s,t,relation)}。
    budget_state: {"budget_used": N, "budget": M, "truncated": bool} 或 None（不限预算）。
    返回叠加的 edge_obj 列表。
    """
    overlaid = []
    seen_pending: set = set()  # pending 内部去重

    for pe in pending_edges:
        s = normalize_slug(pe.get("source", ""))
        t = normalize_slug(pe.get("target", ""))
        relation = pe.get("relation", "references")

        # 悬空丢弃：归一化后 s 或 t 不在 G.nodes
        if s not in G.nodes or t not in G.nodes:
            continue

        # scope 过滤：仅叠加与当前子图相关的边
        if s not in scope_nodes and t not in scope_nodes:
            continue

        # 三元组去重（权威优先）
        key = (s, t, relation)
        if key in authoritative_keys:
            continue
        if key in seen_pending:
            continue
        seen_pending.add(key)

        # budget 检查
        if budget_state is not None:
            if budget_state["budget_used"] >= budget_state["budget"]:
                budget_state["truncated"] = True
                break
            budget_state["budget_used"] += 1

        # 构造 edge_obj（origin=pending）
        confidence = pe.get("confidence", "INFERRED")
        source_location = pe.get("source_location", "")
        overlaid.append({
            "source": s,
            "target": t,
            "relation": relation,
            "confidence": confidence,
            "reviewed": False,
            "source_location": source_location,
            "authoritative": False,
            "origin": "pending",
        })

    return overlaid


# ── path 专属：时效谓词 + 治理过滤构图 ─────────────────────────────
def is_expired(expires: str, today: date) -> bool:
    """复用 ask-rules.md L238-244 时效逻辑：今日 > expires 即 EXPIRED。

    - expires == "never"（或空）→ 永不过期 → False
    - 非法日期 → 当作未过期 False（健壮性 > 严格，不让脏数据误杀节点）
    - 严格小于（== 当天不算过期，与 ask WARNING 边界一致）
    """
    if not expires or expires == "never":
        return False
    try:
        return date.fromisoformat(expires) < today
    except ValueError:
        return False


def build_path_graph(G, today, include_deprecated, include_expired,
                     include_inferred, pending_edges):
    """构建 path 最短路专用的治理过滤有向图。

    返回 (PG, filtered_out)。PG 上跑 nx.shortest_path 即「带治理的最短路」。
    复用既有 normalize_slug / is_expired 谓词；绝不修改 G（新建图，只读 G）。
    AMBIGUOUS 永不入 path 图（§4 白名单：仅 confidence=="INFERRED" 可叠）。
    """
    import networkx as nx  # noqa: PLC0415 — PEP723 隔离环境内导入

    # ── 1. 节点过滤谓词（status + EXPIRED）──
    keep, has_deprecated, has_expired = set(), False, False
    for n in G.nodes:
        attrs = G.nodes[n]
        is_dep = attrs.get("status", "draft") == "deprecated"
        is_exp = is_expired(attrs.get("expires", "never"), today)
        if is_dep:
            has_deprecated = True
            if not include_deprecated:
                continue
        if is_exp:
            has_expired = True
            if not include_expired:
                continue
        keep.add(n)

    # ── 2. 建新有向图，只放 keep 内节点 + 两端都在 keep 内的权威 links 边 ──
    PG = nx.DiGraph()
    PG.add_nodes_from((n, G.nodes[n]) for n in keep)
    for s, t in G.edges:
        if s in keep and t in keep:
            PG.add_edge(s, t, **G.edges[s, t], origin="links")

    # ── 3. --include-inferred：只叠 INFERRED 软边，坚决排除 AMBIGUOUS（§4）──
    if include_inferred:
        for pe in pending_edges:
            conf = pe.get("confidence", "INFERRED")
            if conf == "AMBIGUOUS":       # ★ 硬护栏：AMBIGUOUS 永不入 path 图
                continue
            if not (conf == "INFERRED"):  # 白名单——仅 conf == "INFERRED" 可叠
                continue
            s = normalize_slug(pe.get("source", ""))
            t = normalize_slug(pe.get("target", ""))
            if s not in keep or t not in keep:
                continue
            if PG.has_edge(s, t):          # 权威边优先，已有则不覆盖
                continue
            PG.add_edge(s, t, relation=pe.get("relation", "references"),
                        confidence="INFERRED", reviewed=False,
                        source_location=pe.get("source_location", ""),
                        origin="pending")

    filtered_out = {
        "deprecated_excluded": has_deprecated and not include_deprecated,
        "expired_excluded": has_expired and not include_expired,
    }
    return PG, filtered_out


# ── path 专属：确定性最短路 + cmd_path 主逻辑 ──────────────────────
def deterministic_shortest_path(PG, a: str, b: str, max_hops=None):
    """确定性单条最短路：收集全部等长最短路，按节点 id 序列字典序取第一条。

    返回 node_id 列表（含 a/b），无路径返回 None。
    确定性依据（§3.2）：node id 是纯 slug 全序无平局，min(key=tuple) 跨运行稳定。
    """
    import networkx as nx  # noqa: PLC0415

    if a == b:
        return [a]                                   # A==B：长度 0 单节点路径（§5.3）
    if a not in PG or b not in PG:
        return None                                  # 端点被治理过滤掉 → 无路径
    try:
        all_sp = list(nx.all_shortest_paths(PG, a, b))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None                                  # 不连通 → no_path
    if not all_sp:
        return None
    chosen = min(all_sp, key=lambda p: tuple(p))     # ★ 节点 id 序列字典序取第一条
    if max_hops is not None and (len(chosen) - 1) > max_hops:
        return None                                  # 超 max-hops 兜底 → no_path
    return chosen


def _path_edge_obj(PG, s: str, t: str) -> dict:
    """从 PG 取边属性构造 path_edges 每跳对象（含软边，不能从 G 取）。"""
    attrs = PG.edges[s, t] if PG.has_edge(s, t) else {}
    confidence = attrs.get("confidence", "EXTRACTED")
    reviewed = attrs.get("reviewed", True)
    authoritative = (confidence == "EXTRACTED" and reviewed is True)
    return {
        "source": s,
        "target": t,
        "relation": attrs.get("relation", "references"),
        "confidence": confidence,
        "reviewed": reviewed,
        "source_location": attrs.get("source_location", ""),
        "authoritative": authoritative,
        "origin": attrs.get("origin", "links"),
    }


def _path_node_view(PG, nid: str) -> dict:
    """从 PG.nodes 取路径节点视图（PG 节点属性是 G 透传）。"""
    attrs = PG.nodes.get(nid, {})
    return {
        "id": nid,
        "title": attrs.get("title", nid),
        "type": attrs.get("type", ""),
        "status": attrs.get("status", "draft"),
        "node_kind": attrs.get("node_kind", "document"),
    }


def cmd_path(G, node_id_a: str, node_id_b: str, include_inferred: bool,
             include_deprecated: bool, include_expired: bool,
             max_hops, today, kb_root: Path) -> dict:
    """path 子命令主逻辑：双定位后构图 → 确定性最短路 → 填 §1.3 schema。"""
    payload = base_payload("path", include_inferred=include_inferred)
    payload["endpoints"] = {
        "from": node_view(G, node_id_a),
        "to": node_view(G, node_id_b),
    }

    # 构图
    pending = load_pending_edges(kb_root) if include_inferred else []
    PG, filtered_out = build_path_graph(G, today, include_deprecated, include_expired,
                                        include_inferred, pending)

    # 确定性最短路
    chosen = deterministic_shortest_path(PG, node_id_a, node_id_b, max_hops)

    if chosen is None:
        # 无路径分支：不脑补中间节点（守 C1）
        payload["no_path"] = True
        payload["path_nodes"] = []
        payload["path_edges"] = []
        payload["path_length"] = 0
        payload["has_inferred_edge"] = False
    else:
        # 有路径分支
        payload["no_path"] = False
        payload["path_nodes"] = [_path_node_view(PG, n) for n in chosen]
        path_edges = [_path_edge_obj(PG, s, t) for s, t in zip(chosen, chosen[1:])]
        payload["path_edges"] = path_edges
        payload["path_length"] = len(chosen) - 1
        payload["has_inferred_edge"] = any(e["origin"] == "pending" for e in path_edges)

    # 回显治理过滤状态
    payload["include_deprecated"] = include_deprecated
    payload["include_expired"] = include_expired
    payload["max_hops"] = max_hops
    payload["filtered_out"] = filtered_out

    # stats
    by_confidence = {"EXTRACTED": 0, "INFERRED": 0, "AMBIGUOUS": 0}
    for e in payload["path_edges"]:
        c = e.get("confidence", "")
        if c in by_confidence:
            by_confidence[c] += 1
    payload["stats"] = {
        "node_count": len(payload["path_nodes"]),
        "edge_count": len(payload["path_edges"]),
        "by_confidence": by_confidence,
    }

    return payload


# ── 子命令：neighbors（BFS 分层 + 确定性排序 + budget 截断）────────
def cmd_neighbors(G, center: str, hops: int, budget: int, include_inferred: bool, kb_root: Path) -> dict:
    """以 center 为中心的 k-hop 子图（BFS + budget 截断）。"""
    payload = base_payload("neighbors", budget=budget, hops=hops, include_inferred=include_inferred)
    payload["center"] = node_view(G, center)

    # 自写分层 BFS（deque），不用 nx.bfs_tree（排序键需完全可控）
    # 无向视图做邻居探索（关系有向但「找关系网」按无向扩展）
    visited = {center}
    edges_collected = []
    neighbors_info = {}  # node_id -> hop
    budget_used = 0
    truncated = False

    # 权威边三元组集合（用于去重）
    authoritative_keys: set = set()

    # BFS 层序
    current_layer = [center]
    for hop in range(1, hops + 1):
        if truncated:
            break
        next_layer_set: set = set()
        # 收集本层所有候选边
        candidate_edges = []
        for node in current_layer:
            # 出边
            for _, neighbor in G.out_edges(node):
                if neighbor not in visited:
                    candidate_edges.append((node, neighbor, hop))
                    next_layer_set.add(neighbor)
            # 入边
            for neighbor, _ in G.in_edges(node):
                if neighbor not in visited:
                    candidate_edges.append((neighbor, node, hop))
                    next_layer_set.add(neighbor)

        # 确定性排序：(hop 升序, 源节点 degree 降序, source slug 字典序, target slug 字典序)
        candidate_edges.sort(key=lambda e: (e[2], -G.degree(e[0]), e[0], e[1]))

        # 去重并按排序纳入
        seen_edge_keys: set = set()
        layer_nodes: list = []
        for s, t, h in candidate_edges:
            if truncated:
                break
            edge_key = (s, t)
            if edge_key in seen_edge_keys:
                continue
            if not G.has_edge(s, t):
                continue
            seen_edge_keys.add(edge_key)
            # budget 检查
            if budget_used >= budget:
                truncated = True
                break
            eo = edge_obj(G, s, t, origin="links")
            edges_collected.append(eo)
            authoritative_keys.add((s, t, eo["relation"]))
            budget_used += 1
            # 记录触达的新邻居
            for endpoint in (s, t):
                if endpoint != center and endpoint not in visited:
                    neighbors_info[endpoint] = h
                    layer_nodes.append(endpoint)

        # 标记本层已访问
        for n in layer_nodes:
            visited.add(n)
        # 下一层队列 = 本层新触达的邻居
        current_layer = sorted(set(layer_nodes))

    # --include-inferred 叠加
    if include_inferred:
        pending_edges = load_pending_edges(kb_root)
        if pending_edges:
            scope_nodes = visited.copy()
            budget_state = {"budget_used": budget_used, "budget": budget, "truncated": truncated}
            overlaid = overlay_pending(G, scope_nodes, authoritative_keys, pending_edges, budget_state)
            edges_collected.extend(overlaid)
            budget_used = budget_state["budget_used"]
            truncated = budget_state["truncated"]
            # 新触达的邻居（pending 边端点）
            for eo in overlaid:
                for endpoint in (eo["source"], eo["target"]):
                    if endpoint != center and endpoint not in neighbors_info:
                        neighbors_info[endpoint] = 1  # pending 边标 hop=1

    # 构建 neighbors 列表，按 (hop 升序, degree 降序, slug 字典序) 排序
    neighbors_list = []
    for nid, hop in neighbors_info.items():
        attrs = G.nodes.get(nid, {})
        neighbors_list.append({
            "id": nid,
            "title": attrs.get("title", nid),
            "type": attrs.get("type", ""),
            "status": attrs.get("status", "draft"),
            "hop": hop,
            "node_kind": attrs.get("node_kind", "document"),
        })
    neighbors_list.sort(key=lambda n: (n["hop"], -G.degree(n["id"]) if n["id"] in G.nodes else 0, n["id"]))

    # stats
    by_confidence = {"EXTRACTED": 0, "INFERRED": 0, "AMBIGUOUS": 0}
    for e in edges_collected:
        c = e.get("confidence", "")
        if c in by_confidence:
            by_confidence[c] += 1

    payload["neighbors"] = neighbors_list
    payload["edges"] = edges_collected
    payload["truncated"] = truncated
    payload["budget_used"] = budget_used
    payload["stats"] = {
        "node_count": len(neighbors_list) + 1,  # +1 for center
        "edge_count": len(edges_collected),
        "by_confidence": by_confidence,
    }
    return payload


# ── 子命令：node（入边/出边全连接）────────────────────────────────────
def cmd_node(G, center: str, include_inferred: bool, kb_root: Path) -> dict:
    """单节点入边/出边全连接（explain 语义）。"""
    payload = base_payload("node", include_inferred=include_inferred)
    payload["center"] = node_view(G, center)
    payload["hops"] = None  # node 子命令无 hops 语义

    edges_collected = []
    authoritative_keys: set = set()
    neighbor_ids: set = set()

    # 出边（source==center）
    for _, t in G.out_edges(center):
        eo = edge_obj(G, center, t, origin="links")
        edges_collected.append(eo)
        authoritative_keys.add((center, t, eo["relation"]))
        neighbor_ids.add(t)

    # 入边（target==center）
    for s, _ in G.in_edges(center):
        eo = edge_obj(G, s, center, origin="links")
        edges_collected.append(eo)
        authoritative_keys.add((s, center, eo["relation"]))
        neighbor_ids.add(s)

    # --include-inferred 叠加（scope: 端点含 center）
    if include_inferred:
        pending_edges = load_pending_edges(kb_root)
        if pending_edges:
            scope_nodes = {center}
            overlaid = overlay_pending(G, scope_nodes, authoritative_keys, pending_edges)
            edges_collected.extend(overlaid)
            for eo in overlaid:
                for endpoint in (eo["source"], eo["target"]):
                    if endpoint != center:
                        neighbor_ids.add(endpoint)

    # 确定性排序：(source, target, relation)
    edges_collected.sort(key=lambda e: (e["source"], e["target"], e["relation"]))

    # neighbors
    neighbors_list = []
    for nid in sorted(neighbor_ids):
        attrs = G.nodes.get(nid, {})
        neighbors_list.append({
            "id": nid,
            "title": attrs.get("title", nid),
            "type": attrs.get("type", ""),
            "status": attrs.get("status", "draft"),
            "hop": 1,
            "node_kind": attrs.get("node_kind", "document"),
        })

    # stats
    by_confidence = {"EXTRACTED": 0, "INFERRED": 0, "AMBIGUOUS": 0}
    for e in edges_collected:
        c = e.get("confidence", "")
        if c in by_confidence:
            by_confidence[c] += 1

    payload["neighbors"] = neighbors_list
    payload["edges"] = edges_collected
    payload["truncated"] = False
    payload["budget_used"] = len(edges_collected)
    payload["stats"] = {
        "node_count": len(neighbors_list) + 1,
        "edge_count": len(edges_collected),
        "by_confidence": by_confidence,
    }
    return payload


# ── 子命令：count（权威边计数，最低成本无遍历）────────────────────────
def cmd_count(G, center: str) -> dict:
    """只数权威边（in_degree + out_degree），无遍历。"""
    payload = base_payload("count")
    payload["center"] = node_view(G, center)
    # graph.json links 恒权威边（不变量 14），degree 即权威边数
    count = G.in_degree(center) + G.out_degree(center)
    payload["authoritative_edge_count"] = count
    payload["hops"] = None
    return payload


# ── 主流程 ────────────────────────────────────────────────────────────
def main() -> None:
    # 通用参数放入 parent parser，子命令自动继承
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--kb-root", default=".knowledge", help="知识库根目录（默认 .knowledge）")
    parent.add_argument("--format", default="json", choices=["json"], help="输出格式（默认 json）")
    parent.add_argument("--include-inferred", action="store_true", default=False,
                        help="额外读 .pending-edges.yaml 叠加 INFERRED/AMBIGUOUS 边（默认关闭）")

    ap = argparse.ArgumentParser(
        description="knowledge-wiki 只读图查询引擎（Phase 4）",
        parents=[parent],
    )

    sub = ap.add_subparsers(dest="subcommand")

    # neighbors 子命令
    p_neighbors = sub.add_parser("neighbors", parents=[parent], help="以节点为中心的 k-hop 子图")
    p_neighbors.add_argument("node", help="被查询节点（slug 或 title）")
    p_neighbors.add_argument("--hops", type=int, default=DEFAULT_HOPS, help=f"BFS 跳数（默认 {DEFAULT_HOPS}，上限 {MAX_HOPS}）")
    p_neighbors.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help=f"边数预算（默认 {DEFAULT_BUDGET}）")

    # node 子命令
    p_node = sub.add_parser("node", parents=[parent], help="单节点入边/出边全连接")
    p_node.add_argument("node", help="被查询节点（slug 或 title）")

    # count 子命令
    p_count = sub.add_parser("count", parents=[parent], help="该 slug 的权威边数")
    p_count.add_argument("node", help="被查询节点（slug 或 title）")

    # path 子命令（Phase 5：A 与 B 之间的多跳桥接知识链）
    p_path = sub.add_parser("path", parents=[parent], help="A 与 B 之间的多跳桥接知识链（最短路）")
    p_path.add_argument("source", help="起点节点（slug 或 title）")
    p_path.add_argument("target", help="终点节点（slug 或 title）")
    p_path.add_argument("--include-deprecated", action="store_true", default=False,
                        help="纳入 deprecated 节点参与遍历（默认排除）")
    p_path.add_argument("--include-expired", action="store_true", default=False,
                        help="纳入 EXPIRED 节点参与遍历（默认排除）")
    p_path.add_argument("--max-hops", type=int, default=None,
                        help="路径最大跳数上限（超过视为 no_path；默认不限）")
    p_path.add_argument("--today", default=None,
                        help="EXPIRED 判定基准日期 YYYY-MM-DD（仅测试注入，默认系统当天）")

    args = ap.parse_args()

    if not args.subcommand:
        ap.print_help()
        sys.exit(1)

    kb = Path(args.kb_root)
    if not kb.is_dir():
        print(f"❌ 知识库根目录不存在：{kb}", file=sys.stderr)
        sys.exit(1)

    # 加载 graph.json
    G, degraded = load_graph(kb)
    if degraded:
        # 图层不存在/损坏 → degraded payload 退 0
        payload = base_payload(args.subcommand, degraded=degraded)
        emit(payload)
        sys.exit(0)

    # path 子命令：双定位分支隔离（path 用 source/target，非 node）
    if args.subcommand == "path":
        # A 定位（先报 A，§5.2）
        a_id, a_cands, a_deg = locate_node(G, args.source)
        if a_deg:
            for c in a_cands:
                c["endpoint"] = "from"
            emit(base_payload("path", degraded=a_deg, candidates=a_cands,
                              endpoints={"from": None, "to": None}))
            sys.exit(0)
        # B 定位（A 命中后才定位 B）
        b_id, b_cands, b_deg = locate_node(G, args.target)
        if b_deg:
            for c in b_cands:
                c["endpoint"] = "to"
            emit(base_payload("path", degraded=b_deg, candidates=b_cands,
                              endpoints={"from": None, "to": None}))
            sys.exit(0)
        # 两端命中 → 解析 today → cmd_path
        if args.today:
            try:
                today_val = date.fromisoformat(args.today)
            except ValueError:
                print(f"❌ --today 格式非法（需 YYYY-MM-DD）：{args.today}", file=sys.stderr)
                sys.exit(1)
        else:
            today_val = date.today()
        result = cmd_path(G, a_id, b_id, args.include_inferred,
                          args.include_deprecated, args.include_expired,
                          args.max_hops, today_val, kb)
        emit(result)
        sys.exit(0)

    # 节点定位（neighbors/node/count 走此路径）
    node_id, candidates, degraded = locate_node(G, args.node)
    if degraded:
        payload = base_payload(args.subcommand, degraded=degraded, candidates=candidates)
        emit(payload)
        sys.exit(0)

    # 分发子命令
    include_inferred = args.include_inferred
    if args.subcommand == "neighbors":
        hops = max(1, min(args.hops, MAX_HOPS))  # clamp [1, MAX_HOPS]
        result = cmd_neighbors(G, node_id, hops, args.budget, include_inferred, kb)
    elif args.subcommand == "node":
        result = cmd_node(G, node_id, include_inferred, kb)
    elif args.subcommand == "count":
        result = cmd_count(G, node_id)
    else:
        ap.print_help()
        sys.exit(1)

    emit(result)


if __name__ == "__main__":
    main()
