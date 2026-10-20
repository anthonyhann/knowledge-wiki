#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["networkx==3.6.1"]
# ///
"""graph_export.py — Phase 9 知识网络可视化导出引擎：只读 graph.json + communities.json →
渲染 HTML(Cytoscape.js CDN)/Canvas/GraphML 到 .graph/exports/。

与五兄弟脚本（graph_build / graph_query / graph_analyze / explore_questions / discover_prefilter）
职责分离。

单向派生：只读，唯一写 .graph/exports/，绝不回填 graph.json/不碰 source_hash/不碰文档（D-10）。
纯静态 HTML 浏览器直接打开无服务进程（VIZ-01）。

用法:
    uv run graph_export.py --kb-root .knowledge --html
    uv run graph_export.py --kb-root .knowledge --html --canvas --graphml
    uv run graph_export.py --kb-root .knowledge --html --include-inferred --json

仅依赖 networkx==3.6.1（禁止 default extra，避免拉 numpy/scipy/matplotlib）。
禁止引入 jinja2/pyvis/matplotlib/lxml 等第三方渲染库。
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

# ── 常量 ──────────────────────────────────────────────────────────────
GRAPH_DIR = ".graph"
EXPORT_LOCK = ".export.lock"          # 独立锁，不复用 .build/.analyze/.explore/.discover.lock
EXPORTS_DIR = "exports"
HTML_FILE = "graph.html"
CANVAS_FILE = "graph.canvas"         # 09-02 用，先声明
GRAPHML_FILE = "graph.graphml"       # 09-02 用，先声明
COMMUNITIES_FILE = "communities.json"
PENDING_FILE = ".pending-edges.yaml"
SCHEMA_VERSION = "1.0"
GENERATOR = "knowledge-wiki/graph-export@1.0"

# 大图阈值（D-13 / §3.2）
EXPORT_NODE_THRESHOLD = 2000

# CDN URL 锁版本（§1.2，仅需 cytoscape core——内置 cose 布局零外部依赖，符合 VIZ-01 浏览器直接打开）
# 不用 fcose 扩展：其 2.2.0 UMD bundle 依赖 cose-base，浏览器单文件加载时 window.cytoscapeFcose
# 不注册，cytoscape.use(undefined) 抛错中断整个 IIFE → cytoscape() 从未执行 → 白屏。
# cose 是 fcose 前身，core 内置（零外部依赖），对知识图谱规模够用。
CDN_CYTOSCAPE = "https://cdn.jsdelivr.net/npm/cytoscape@3.34.0/dist/cytoscape.min.js"

# 三套调色板（§2.3，Python 端确定性预算）
PALETTE_COMMUNITY = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2",
    "#59a14f", "#edc948", "#b07aa1", "#ff9da7",
    "#9c755f", "#bab0ac",
]

PALETTE_STATUS = {
    "canonical": "#1a6b3a",   # 深绿——最高权威
    "active":    "#4e79a7",   # 主蓝——活跃
    "draft":     "#f28e2b",   # 橙——草稿
    "deprecated": "#9aa0a6",  # 灰——废弃
}

PALETTE_TYPE = {
    "glossary":     "#b07aa1",
    "architecture": "#4e79a7",
    "solution":     "#59a14f",
    "adr":          "#76b7b2",
    "requirement":  "#edc948",
    "flow":         "#f28e2b",
    "test":         "#86bcb6",   # v2.1.0 新增（测试知识；青绿系，与 adr 区分）
    "api":          "#e15759",
    "db":           "#9c755f",
    "ops":          "#ff9da7",
    "synthesis":    "#bab0ac",
}

COLOR_NEUTRAL = "#cccccc"   # community=null 兜底色

# 10 个业务目录（复用 graph_analyze.py 文档集范围）
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

# 告警收集（模块级，便于 write_c6_log 获取）
warnings: list[str] = []


# ── 复用范式：atomic_write_text（仿 graph_analyze.py L63-83，写文本而非 JSON）
def atomic_write_text(file_path: Path, text: str) -> None:
    """原子写文本文件：同盘临时文件 → flush+fsync → os.replace 覆盖。

    临时文件建在 file_path.parent（同分区），确保 os.replace 原子。
    仅写 exports/ 下文件（HTML/Canvas/GraphML 等纯文本产物）。
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        dir=file_path.parent,
        prefix=".export.",
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    )
    try:
        tmp.write(text)
        tmp.flush()
        os.fsync(tmp.fileno())
    finally:
        tmp.close()
    os.replace(tmp.name, file_path)


# ── 复用范式：resolve_user_id + write_c6_log（照搬 graph_analyze.py L120-180）
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
    """导出成功后追加一条操作日志到 .logs/personal/{user-id}.md。

    复用既有 log-rules.md 通道，layer 标 graph-export（区别于 graph-build/graph-analyze）。
    detail 记 formats/node_count/edge_count/include_inferred/source_hash/oversized。
    user-id 缺失时降级跳过，不阻断导出。
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
            "formats":          payload.get("formats"),
            "node_count":       payload.get("node_count"),
            "edge_count":       payload.get("edge_count"),
            "include_inferred": payload.get("include_inferred"),
            "source_hash":      payload.get("source_hash"),
            "oversized":        payload.get("oversized"),
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
            f"\n## [{now}] @{user_id} | health | graph-export\n"
            f"  detail: {json.dumps(detail, ensure_ascii=False)}\n"
        )
        with log_file.open("a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as exc:  # noqa: BLE001 — C6 日志失败不阻断导出
        warnings.append(f"C6 日志写入失败（不阻断导出）：{exc}")


# ── load_graph_data 只读加载（仿 graph_analyze.py L184-201，保留原始 dict）
def load_graph_data(kb_root: Path):
    """加载 graph.json → (data:dict | None, degraded | None)。

    不存在 → (None, "graph_missing")；损坏 → (None, "graph_broken")。
    返回原始 dict（保留 generated_at/source_hash/nodes/links 等顶层字段）。
    用 nx.node_link_graph 做自检（确认无悬空端点、格式合法）。
    只读，绝不写 graph.json。
    """
    import networkx as nx  # noqa: PLC0415 — PEP 723 隔离环境内导入

    graph_path = kb_root / GRAPH_DIR / "graph.json"
    if not graph_path.is_file():
        return None, "graph_missing"
    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        # nx 自检：确认 node-link schema 合法、无悬空端点
        nx.node_link_graph(data, edges="links", directed=True, multigraph=False)
        # 返回原始 dict 供 generated_at/source_hash/nodes/links 使用
        return data, None
    except Exception:  # noqa: BLE001 — 损坏图降级
        return None, "graph_broken"


# ── load_communities 只读加载（照搬 explore_questions.py L206-220）
def load_communities(kb_root: Path):
    """加载 communities.json → (dict | None, degraded | None)。

    不存在 → (None, "communities_missing")；损坏 → (None, "communities_broken")。
    只读，绝不写。
    """
    path = kb_root / GRAPH_DIR / COMMUNITIES_FILE
    if not path.is_file():
        return None, "communities_missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data, None
    except Exception:  # noqa: BLE001 — 损坏降级
        return None, "communities_broken"


# ── is_expired 时效谓词（照搬 explore_questions.py L245-256）
def is_expired(expires_str) -> bool:
    """expires 是日期且 < 今日 → True；"never"/None/非法 → False。"""
    if not expires_str or expires_str == "never":
        return False
    s = str(expires_str).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            d = datetime.strptime(s, fmt).date()
            return d < datetime.now().date()
        except ValueError:
            continue
    return False


# ── normalize_slug：slug 归一化去目录前缀（照搬 explore_questions.py L259-268）
def normalize_slug(s: str) -> str:
    """把路径式 slug 与 graph node id 归一到同形（basename 去 .md）。

    graph node id 是 basename（如 print-timeout），而 .pending-edges.yaml 的
    source/target 可能是路径式 slug（如 ops/print-timeout）。
    本函数去目录前缀 + 去尾部 .md，使两端可比对。
    """
    if s is None:
        return ""
    base = str(s).rsplit("/", 1)[-1]
    if base.endswith(".md"):
        base = base[:-3]
    return base


# ── 共享中间表示层：pick_colors（§2.3 三套调色板，Python 端确定性预算）────
def pick_colors(node: dict, communities) -> dict:
    """三套调色板预算 → {"color_community": ..., "color_status": ..., "color_type": ...}。

    全 Python 端确定性预算（同输入同输出），供 build_elements 写入 data。
    HTML 前端 <select> 切换 colorBy 时直接读 data.color_* 零重算（§1.4）。
    community id % len(palette) 循环，community=null → COLOR_NEUTRAL。
    """
    c = node.get("community")
    if c is not None:
        color_community = PALETTE_COMMUNITY[c % len(PALETTE_COMMUNITY)]
    else:
        color_community = COLOR_NEUTRAL

    color_status = PALETTE_STATUS.get(node.get("status", ""), COLOR_NEUTRAL)
    color_type = PALETTE_TYPE.get(node.get("type", ""), COLOR_NEUTRAL)

    return {
        "color_community": color_community,
        "color_status":    color_status,
        "color_type":      color_type,
    }


# ── 09-02: load_pending_inferred（手写行扫描读 .pending-edges.yaml pending[] source/target/relation/confidence）
def load_pending_inferred(kb_root: Path) -> list:
    """只读 .knowledge/.pending-edges.yaml 的 pending[].source/target/relation/confidence。

    手写行扫描（禁 import yaml，仿 explore_questions.py L352-400）。
    额外收集 relation/confidence（对比 load_pending_pairs 只取 source/target）。
    端点先过 normalize_slug（R7）使路径式 slug 与 graph node id 同形可比对。
    .pending-edges.yaml 放 .knowledge/ 根（不在 .graph/ 下，删 .graph/ 后仍在）。
    只读，绝不写 .pending-edges.yaml（D-10）。
    禁 import yaml（守 §2.4 手写行扫描铁律，守技术栈锁定原则）。
    """
    path = kb_root / PENDING_FILE
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    result: list[dict] = []
    in_pending = False
    # 当前列表项累积字段
    cur: dict = {}

    def _flush(item: dict) -> None:
        """flush 一个 pending 列表项，端点过 normalize_slug 并收集。"""
        s = item.get("source")
        t = item.get("target")
        if s and t:
            ns = normalize_slug(s)
            nt = normalize_slug(t)
            if ns and nt:
                result.append({
                    "source":     ns,
                    "target":     nt,
                    "relation":   item.get("relation") or "references",
                    "confidence": item.get("confidence") or "INFERRED",
                    "reviewed":   False,
                })

    for raw in lines:
        stripped = raw.strip()
        # 进入 pending: 块
        if stripped == "pending:" or stripped.startswith("pending:"):
            in_pending = True
            continue
        if not in_pending:
            continue
        # 顶层其它键（无缩进且非空且末尾 :）→ 退出 pending 块
        if raw and not raw[0].isspace() and stripped.endswith(":") and stripped != "pending:":
            _flush(cur)
            cur = {}
            break
        # 新列表项起点：flush 上一项
        if stripped.startswith("- "):
            _flush(cur)
            cur = {}
            stripped = stripped[2:].strip()
        # 提取 source/target/relation/confidence（去引号）
        for field in ("source", "target", "relation", "confidence"):
            prefix = f"{field}:"
            if stripped.startswith(prefix):
                cur[field] = stripped[len(prefix):].strip().strip("'\"")
                break

    # flush 末项
    _flush(cur)
    return result


# ── 共享中间表示层：build_elements（§2.2，09-02 to_canvas/to_graphml 复用）───
def build_elements(graph_data: dict, communities, include_inferred: bool,
                   *, pending_edges=None) -> dict:
    """graph.json nodes/links → Cytoscape elements 中间表示层。

    确定性三要素（过 09-03 两跑 byte 级一致 §3.1）：
      ① 节点按 id 字典序排序
      ② 边按 (source, target, relation) 三元组排序
      ③ compound 父按 community id 升序，且只为 graph.json 节点实际出现的 community 产父

    灰显（D-15）：status=="deprecated" 或 is_expired(expires) → classes:"dimmed"
    孤岛显示（D-07）：孤岛不过滤，全节点入图；孤岛 community=null 不设 parent 落顶层
    community=null → 不设 data.parent（§1.3 路线 B）
    centrality=null → 不写 data.centrality（让 style 走固定基线 width §1.4）
    pending_edges: 可选 list（来自 load_pending_inferred），向后兼容旧调用（默认 None）
    --include-inferred + pending_edges：只读 .pending-edges.yaml 注入推断边；
      端点须在 graph 内（避免悬空），标 classes:"unreviewed"，
      与已有 EXTRACTED 边去重，注入后仍按 (source,target,relation) 排序确定性（D-06）
    默认不注入：视图干净全 EXTRACTED 权威边（D-05/D-06）
    """
    nodes_raw = graph_data.get("nodes", [])
    links_raw = graph_data.get("links", [])

    # ── 收集实际出现的 community id（只为真实出现的 community 产 compound 父，避免悬空）
    actual_community_ids: set[int] = set()
    for n in nodes_raw:
        c = n.get("community")
        if c is not None:
            actual_community_ids.add(c)

    # ── compound 父节点（每非空 community 一个，按 id 升序，§1.3 路线 B）
    community_parents: list[dict] = []
    if communities is not None and not communities.get("skipped", True):
        comm_list = communities.get("communities", [])
        # 按 community id 升序，且只产真实出现的 community
        for c_entry in sorted(comm_list, key=lambda x: x["id"]):
            cid = c_entry["id"]
            if cid not in actual_community_ids:
                continue  # 不为无真实成员的社区产父
            dominant_type = c_entry.get("dominant_type", "")
            community_parents.append({
                "data": {
                    "id":        f"comm-{cid}",
                    "kind":      "community",
                    "label":     f"社区{cid}·{dominant_type}",
                    "community": cid,
                }
            })

    # ── 真实文档节点（按 id 字典序排序，确定性①）
    doc_nodes: list[dict] = []
    for node in sorted(nodes_raw, key=lambda n: n.get("id", "")):
        nid = node.get("id", "")
        c = node.get("community")
        centrality = node.get("centrality")

        # 灰显判定（D-15）：deprecated 或 EXPIRED
        expired = is_expired(node.get("expires"))
        cls = "dimmed" if (node.get("status") == "deprecated" or expired) else ""

        # data 字段
        node_data: dict = {
            "id":       nid,
            "title":    node.get("title") or nid,
            "type":     node.get("type", ""),
            "status":   node.get("status", ""),
            "community": c,
            "node_kind": node.get("node_kind", ""),
            "path":     node.get("path", ""),
            "expires":  node.get("expires", "never"),
            "kind":     "doc",                          # 区分真实节点 vs compound 父
        }
        # centrality=null → 不写键，让 style 走固定基线 width（§1.4）
        if centrality is not None:
            node_data["centrality"] = centrality

        # community 非 None → 设 parent（§1.3 路线 B）
        if c is not None:
            node_data["parent"] = f"comm-{c}"

        # 三套颜色（Python 端确定性预算，§2.3）
        colors = pick_colors(node, communities)
        node_data.update(colors)

        doc_nodes.append({
            "data":    node_data,
            "classes": cls,
        })

    # ── 边（按 (source, target, relation) 三元组排序，确定性②）
    edges: list[dict] = []
    for e in sorted(links_raw, key=lambda x: (x.get("source", ""), x.get("target", ""), x.get("relation", ""))):
        src = e.get("source", "")
        tgt = e.get("target", "")
        rel = e.get("relation", "")
        edges.append({
            "data": {
                "id":              f"{src}__{rel}__{tgt}",  # 稳定确定性 id
                "source":          src,
                "target":          tgt,
                "relation":        rel,
                "confidence":      e.get("confidence", "EXTRACTED"),
                "source_location": e.get("source_location", ""),
                "reviewed":        e.get("reviewed", True),
            }
        })

    # ── --include-inferred：只读 pending 注入推断边（D-06，禁 import yaml，端点 normalize_slug 对齐 R7）
    # 只注入端点都在 graph 内的边（避免悬空）+ classes:"unreviewed"
    # 与已有 EXTRACTED 边去重 + 注入后仍按 (source,target,relation) 排序保确定性
    # 默认不注入：视图干净全 EXTRACTED 权威边（D-05）
    if include_inferred and pending_edges:
        # 收集真实文档节点 id 集合（端点须在 graph 内）
        node_ids: set[str] = {n["data"]["id"] for n in doc_nodes}
        # 已有边三元组（去重用）
        existing_edge_keys: set[tuple] = {
            (e["data"]["source"], e["data"]["target"], e["data"]["relation"])
            for e in edges
        }
        for pe in pending_edges:
            s = pe.get("source", "")
            t = pe.get("target", "")
            r = pe.get("relation", "references")
            conf = pe.get("confidence", "INFERRED")
            # 端点须都在 graph 内（避免悬空），且不与已有边重复
            if s in node_ids and t in node_ids and (s, t, r) not in existing_edge_keys:
                edges.append({
                    "data": {
                        "id":              f"{s}__{r}__{t}",
                        "source":          s,
                        "target":          t,
                        "relation":        r,
                        "confidence":      conf,
                        "source_location": "pending:.pending-edges.yaml",
                        "reviewed":        False,
                    },
                    "classes": "unreviewed",
                })
                existing_edge_keys.add((s, t, r))  # 防同一 pending 列表内重复
        # 注入后仍按 (source,target,relation) 排序保确定性（§3.1）
        edges.sort(key=lambda x: (
            x["data"].get("source", ""),
            x["data"].get("target", ""),
            x["data"].get("relation", ""),
        ))

    # 父在前不影响 Cytoscape；确定性 = 父按 id 升序 + 节点按 id 排序 + 边按三元组排序
    return {
        "nodes": community_parents + doc_nodes,
        "edges": edges,
    }


# ── 09-02: grid_layout（确定性纯整数网格坐标，Canvas 专用，禁随机/浮点/wall-clock §3.3）────
# Canvas x/y 必须 Python 端确定性算（无浏览器布局引擎）；禁 spring_layout/random（§3.3）
# community 块按 id 升序铺成 BLOCKS_PER_ROW 列网格；块内成员按 slug 字典序子网格；
# group 框坐标=包住块内全部成员的外接矩形；孤岛（community=null）放末尾未分组区
_CELL_W       = 240    # 每个节点单元宽
_CELL_H       = 120    # 每个节点单元高
_GAP          = 40     # 块间间距（纯整数）
_COLS_PER_BLK = 4      # 块内子网格列数
_BLOCKS_PER_ROW = 3    # community 块每行列数
_GROUP_PAD    = 30     # group 框内边距


def grid_layout(elements: dict) -> dict:
    """确定性纯整数网格坐标（Canvas 专用，§3.3）。

    返回 {node_id: (x, y, w, h)} + {"comm-{id}": (x, y, w, h)} 的合并字典。
    禁随机/浮点/wall-clock——纯整数算术保两跑 byte 级一致（§3.1/§3.3）。
    禁 networkx spring_layout / random（§3.3）。
    """
    nodes = elements.get("nodes", [])

    # 分离 doc 节点（kind=="doc"）和 community 父节点（kind=="community"）
    doc_list = [n["data"] for n in nodes if n["data"].get("kind") == "doc"]
    comm_list = [n["data"] for n in nodes if n["data"].get("kind") == "community"]

    # community 父按 id 升序（comm-0, comm-1, ...）
    comm_ids_sorted = sorted(
        (n["community"] for n in comm_list if "community" in n),
    )

    # community id → 成员 doc id 列表（按 slug 字典序）
    comm_to_members: dict[int, list[str]] = {}
    orphans: list[str] = []
    for dn in sorted(doc_list, key=lambda x: x.get("id", "")):
        c = dn.get("community")
        did = dn.get("id", "")
        if c is not None:
            comm_to_members.setdefault(c, []).append(did)
        else:
            orphans.append(did)

    coords: dict = {}  # node_id → (x, y, w, h)

    # ── community 块网格 ──
    for blk_idx, cid in enumerate(comm_ids_sorted):
        members = comm_to_members.get(cid, [])
        # 块在全局网格的行/列
        blk_col = blk_idx % _BLOCKS_PER_ROW
        blk_row = blk_idx // _BLOCKS_PER_ROW

        # 块内成员行列数
        n_members = len(members)
        mem_cols = _COLS_PER_BLK if n_members >= _COLS_PER_BLK else (n_members or 1)
        mem_rows = (n_members + _COLS_PER_BLK - 1) // _COLS_PER_BLK

        # 块左上角偏移（纯整数）
        blk_block_w = mem_cols * _CELL_W + 2 * _GROUP_PAD
        blk_block_h = mem_rows * _CELL_H + 2 * _GROUP_PAD
        blk_x = blk_col * (blk_block_w + _GAP)
        blk_y = blk_row * (blk_block_h + _GAP)

        # 块内成员子网格（按 slug 字典序）
        for mem_idx, nid in enumerate(members):
            mem_col = mem_idx % _COLS_PER_BLK
            mem_row = mem_idx // _COLS_PER_BLK
            x = blk_x + _GROUP_PAD + mem_col * _CELL_W
            y = blk_y + _GROUP_PAD + mem_row * _CELL_H
            coords[nid] = (x, y, _CELL_W - 10, _CELL_H - 10)

        # group 框坐标（包住块内全部成员的外接矩形）
        coords[f"comm-{cid}"] = (blk_x, blk_y, blk_block_w, blk_block_h)

    # ── 孤岛区（末尾，按 slug 字典序）──
    if orphans:
        # 孤岛区偏移：所有 community 块末行之后
        n_blks = len(comm_ids_sorted)
        max_blk_row = 0 if n_blks == 0 else ((n_blks - 1) // _BLOCKS_PER_ROW)
        orphan_area_y = (max_blk_row + 1) * (_CELL_H * ((max_blk_row + 1) or 1) + _GROUP_PAD * 2 + _GAP)
        # 简化：所有 community 块总高度最大值 + GAP（保守算法，确定性足够）
        # 直接用 blk_row_count * 估算高度
        n_blk_rows = (n_blks + _BLOCKS_PER_ROW - 1) // _BLOCKS_PER_ROW if n_blks > 0 else 0
        orphan_y_base = n_blk_rows * (_CELL_H * 4 + 2 * _GROUP_PAD + _GAP) + _GAP
        for orp_idx, nid in enumerate(sorted(orphans)):
            orp_col = orp_idx % (_COLS_PER_BLK * _BLOCKS_PER_ROW)
            orp_row = orp_idx // (_COLS_PER_BLK * _BLOCKS_PER_ROW)
            x = orp_col * _CELL_W
            y = orphan_y_base + orp_row * _CELL_H
            coords[nid] = (x, y, _CELL_W - 10, _CELL_H - 10)

    return coords


# ── 09-02: to_canvas（JSON Canvas 1.0，确定性 + 治理基因跨格式 D-17）────────────
# Canvas x/y 必须 Python 端 grid_layout 确定性算（§3.3）
# file 节点优先 path 缺降 text（R4）；status→color；confidence→edge color+label（D-17）
# 节点按 id 排序 + 边按三元组排序 + json.dumps(sort_keys=True) 保两跑一致（§3.1）
# Canvas 无 2000 阈值（§3.2），Canvas/GraphML 交外部工具消化大图

def to_canvas(elements: dict, meta: dict) -> str:
    """Cytoscape elements → JSON Canvas 1.0 字符串（§2.5，D-17）。

    确定性：grid_layout 纯整数坐标 + 节点按 id 排序 + 边按三元组排序 + sort_keys=True（§3.1）。
    file 节点：有 path → type:"file"（点击在 Obsidian 内打开源 .md，SSOT 导航 R4）；
               无 path/空 path → type:"text"（降级，R4）。
    status 着色：canonical/active→"4"(绿)、draft→"3"(黄)、deprecated→"#9aa0a6"(灰，D-15）。
    confidence：EXTRACTED 无色；INFERRED→"3"(黄)；AMBIGUOUS→"2"(橙)；
                Canvas 无线型字段 → 用 edge label 追加 confidence 文字保治理基因（D-17）。
    group 节点：每 community 父产 type:"group"（§2.5 Canvas group）。
    Canvas 无 2000 阈值（§3.2）。
    """
    coords = grid_layout(elements)

    def _status_color(status: str) -> str | None:
        """status → Canvas canvasColor（"4"/绿 "3"/黄 hex/灰 或 None）。"""
        if status in ("canonical", "active"):
            return "4"
        if status == "draft":
            return "3"
        if status == "deprecated":
            return "#9aa0a6"
        return None  # 其它 status 不设 color

    canvas_nodes: list[dict] = []
    canvas_edges: list[dict] = []

    # ── doc 节点 ──
    for n in elements.get("nodes", []):
        data = n["data"]
        if data.get("kind") != "doc":
            continue  # 跳过 community 父（下面单独处理 group）
        nid = data["id"]
        path = data.get("path", "")
        title = data.get("title") or nid
        status = data.get("status", "")
        x, y, w, h = coords.get(nid, (0, 0, _CELL_W - 10, _CELL_H - 10))
        color = _status_color(status)

        if path:
            node_obj: dict = {
                "id":     nid,
                "type":   "file",
                "file":   path,
                "x":      x,
                "y":      y,
                "width":  w,
                "height": h,
            }
        else:
            node_obj = {
                "id":     nid,
                "type":   "text",
                "text":   title,
                "x":      x,
                "y":      y,
                "width":  w,
                "height": h,
            }
        if color is not None:
            node_obj["color"] = color
        canvas_nodes.append(node_obj)

    # ── group 社区节点 ──
    for n in elements.get("nodes", []):
        data = n["data"]
        if data.get("kind") != "community":
            continue
        cid = data.get("community")
        label = data.get("label", f"社区{cid}")
        grp_id = data["id"]  # "comm-{cid}"
        x, y, w, h = coords.get(grp_id, (0, 0, _CELL_W * _COLS_PER_BLK + 2 * _GROUP_PAD, _CELL_H * 4 + 2 * _GROUP_PAD))
        group_obj: dict = {
            "id":     grp_id,
            "type":   "group",
            "label":  label,
            "x":      x,
            "y":      y,
            "width":  w,
            "height": h,
        }
        canvas_nodes.append(group_obj)

    # ── 边 ──
    for e in elements.get("edges", []):
        data = e["data"]
        eid = data.get("id", "")
        src = data.get("source", "")
        tgt = data.get("target", "")
        rel = data.get("relation", "")
        conf = data.get("confidence", "EXTRACTED")

        edge_label = rel
        edge_color: str | None = None
        if conf == "INFERRED":
            edge_color = "3"
            edge_label = f"{rel} ?INFERRED"
        elif conf == "AMBIGUOUS":
            edge_color = "2"
            edge_label = f"{rel} ?AMBIGUOUS"
        # EXTRACTED 无色、无额外 label 追加（默认即权威，不需要警示）

        edge_obj: dict = {
            "fromNode": src,
            "id":       eid,
            "label":    edge_label,
            "toEnd":    "arrow",
            "toNode":   tgt,
        }
        if edge_color is not None:
            edge_obj["color"] = edge_color
        canvas_edges.append(edge_obj)

    # 节点按 id 排序、边按 (fromNode,label,toNode) 排序（确定性 §3.1）
    canvas_nodes.sort(key=lambda x: x["id"])
    canvas_edges.sort(key=lambda x: (x.get("fromNode", ""), x.get("label", ""), x.get("toNode", "")))

    canvas_dict = {
        "edges": canvas_edges,
        "nodes": canvas_nodes,
    }
    return json.dumps(canvas_dict, ensure_ascii=False, indent=2, sort_keys=True)


# ── 09-02: to_graphml（手写 XML 模板，非 nx.write_graphml，§2.6）────────────────
# 手写 XML 确定性更强（key 顺序写死、空值省略、escape/quoteattr）
# keys 声明顺序写死：node d0~d6 / edge d7~d10（固定）
# 节点按 id 排序、边按三元组排序保两跑 byte 级一致（§3.1）
# centrality=null 省略该 <data>（不写空值，§2.6）
# compound 父节点不进 GraphML（无 compound 概念，community 作 node <data> 属性承载）
# xml.sax.saxutils.escape 文本 + quoteattr 属性（R8，防 title/path 含 <>&" 破 XML）
# GraphML 无 2000 阈值（§3.2）

# GraphML key id 映射（顺序写死，d0~d10，确定性）
_GML_NODE_KEYS = [
    ("d0", "status",        "string"),
    ("d1", "type",          "string"),
    ("d2", "community",     "long"),
    ("d3", "centrality",    "double"),
    ("d4", "node_kind",     "string"),
    ("d5", "title",         "string"),
    ("d6", "path",          "string"),
]
_GML_EDGE_KEYS = [
    ("d7",  "relation",        "string"),
    ("d8",  "confidence",      "string"),
    ("d9",  "source_location", "string"),
    ("d10", "reviewed",        "boolean"),
]


def to_graphml(elements: dict, meta: dict) -> str:
    """Cytoscape elements → GraphML XML 字符串（§2.6，手写模板非 nx.write_graphml）。

    确定性：节点按 id 排序 + 边按 (source,target,relation) 三元组排序 + keys 声明顺序写死
    + centrality=null 省略 data + community=null 可省略 data + escape/quoteattr 转义（§3.1）。
    仅 doc 节点（kind=="doc"）进入 GraphML（compound 父不进，GraphML 无 compound 概念）。
    edge source/target 必须指向已声明 node id（doc 节点集合，悬空则跳过）。
    xml.sax.saxutils.escape 文本 + quoteattr 属性（标准库零依赖，R8）。
    禁 nx.write_graphml / import lxml（§2.6 确定性 + 依赖铁律）。
    GraphML 无 2000 阈值（§3.2）。
    """
    lines: list[str] = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')

    # ── key 声明（顺序写死，确定性）──
    for kid, attr_name, attr_type in _GML_NODE_KEYS:
        lines.append(
            f'  <key id={quoteattr(kid)} for="node" '
            f'attr.name={quoteattr(attr_name)} attr.type={quoteattr(attr_type)}/>'
        )
    for kid, attr_name, attr_type in _GML_EDGE_KEYS:
        lines.append(
            f'  <key id={quoteattr(kid)} for="edge" '
            f'attr.name={quoteattr(attr_name)} attr.type={quoteattr(attr_type)}/>'
        )

    lines.append('  <graph edgedefault="directed">')

    # 提取 doc 节点（kind=="doc"），按 id 排序
    doc_nodes_data = [
        n["data"] for n in elements.get("nodes", [])
        if n["data"].get("kind") == "doc"
    ]
    doc_nodes_data.sort(key=lambda x: x.get("id", ""))
    doc_node_ids: set[str] = {n["id"] for n in doc_nodes_data}

    # 构建 key attr_name → kid 映射
    node_key_map = {attr_name: kid for kid, attr_name, _ in _GML_NODE_KEYS}
    node_key_type_map = {attr_name: t for _, attr_name, t in _GML_NODE_KEYS}
    edge_key_map = {attr_name: kid for kid, attr_name, _ in _GML_EDGE_KEYS}
    edge_key_type_map = {attr_name: t for _, attr_name, t in _GML_EDGE_KEYS}

    def _node_data_el(attr_name: str, val) -> str | None:
        """节点属性 → <data key="dX">val</data>，null/None 省略（§2.6）。"""
        if val is None:
            return None
        kid = node_key_map[attr_name]
        return f'      <data key={quoteattr(kid)}>{escape(str(val))}</data>'

    def _edge_data_el(attr_name: str, val) -> str | None:
        """边属性 → <data key="dX">val</data>。"""
        if val is None:
            return None
        kid = edge_key_map[attr_name]
        # reviewed 转 "true"/"false"
        if node_key_type_map.get(attr_name) == "boolean" or edge_key_type_map.get(attr_name) == "boolean":
            val_str = "true" if val else "false"
        else:
            val_str = str(val)
        return f'      <data key={quoteattr(kid)}>{escape(val_str)}</data>'

    # ── 节点（仅 doc 节点，按 id 排序）──
    for nd in doc_nodes_data:
        nid = nd.get("id", "")
        lines.append(f'    <node id={quoteattr(nid)}>')
        for attr_name, _ in [(a, t) for _, a, t in _GML_NODE_KEYS]:
            val = nd.get(attr_name)
            # centrality=null/None 省略（§2.6）
            # community=null 省略
            if val is None:
                continue
            el = _node_data_el(attr_name, val)
            if el is not None:
                lines.append(el)
        lines.append('    </node>')

    # ── 边（按 (source,target,relation) 三元组排序；端点须指向已声明 node id）──
    edges_raw = [
        e["data"] for e in elements.get("edges", [])
        if e["data"].get("source") in doc_node_ids and e["data"].get("target") in doc_node_ids
    ]
    edges_raw.sort(key=lambda x: (
        x.get("source", ""),
        x.get("target", ""),
        x.get("relation", ""),
    ))
    for ed in edges_raw:
        src = ed.get("source", "")
        tgt = ed.get("target", "")
        eid = ed.get("id", f"{src}__{ed.get('relation','')}_{tgt}")
        lines.append(f'    <edge id={quoteattr(eid)} source={quoteattr(src)} target={quoteattr(tgt)}>')
        for attr_name in ("relation", "confidence", "source_location", "reviewed"):
            val = ed.get(attr_name)
            if val is None:
                continue
            el = _edge_data_el(attr_name, val)
            if el is not None:
                lines.append(el)
        lines.append('    </edge>')

    lines.append('  </graph>')
    lines.append('</graphml>')
    return "\n".join(lines) + "\n"


# ── HTML 模板常量（仅需 cytoscape core CDN，内置 cose 布局，§1.2）──────────────
# 占位符：
#   {CDN_CYTOSCAPE}      → CDN_CYTOSCAPE 常量值（Python 端 str.replace 注入）
#   /*__ELEMENTS_JSON__*/→ elements JSON（json.dumps + </→<\/ 转义）
#   /*__META_JSON__*/    → meta JSON
#   __FOOTER_TS__        → graph.json generated_at（非 wall-clock，§3.1）
HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>知识网络图谱</title>
<script src="{CDN_CYTOSCAPE}"></script>
<style>
  body { margin:0; font-family: 'Helvetica Neue', Arial, sans-serif; background:#f5f5f5; }
  #cy { width:100%; height:calc(100vh - 90px); min-height:600px; background:#fff; }
  #toolbar {
    position:fixed; top:8px; left:8px; z-index:100;
    background:rgba(255,255,255,0.95); padding:6px 10px; border-radius:6px;
    box-shadow:0 1px 4px rgba(0,0,0,0.2); display:flex; align-items:center; gap:10px;
    font-size:13px;
  }
  #legend {
    position:fixed; top:8px; right:8px; z-index:100;
    background:rgba(255,255,255,0.95); padding:8px 12px; border-radius:6px;
    box-shadow:0 1px 4px rgba(0,0,0,0.2); font-size:12px; min-width:160px;
  }
  #legend h4 { margin:0 0 6px; font-size:12px; }
  .leg-row { display:flex; align-items:center; margin:3px 0; gap:6px; }
  .leg-swatch { width:14px; height:14px; border-radius:2px; flex-shrink:0; }
  .leg-line-solid { width:28px; height:2px; background:#555; }
  .leg-line-dashed { width:28px; height:2px; background:#555;
    background: repeating-linear-gradient(90deg,#555 0,#555 4px,transparent 4px,transparent 8px); }
  .leg-line-dotted { width:28px; height:2px;
    background: repeating-linear-gradient(90deg,#e8710a 0,#e8710a 2px,transparent 2px,transparent 5px); }
  footer {
    position:fixed; bottom:0; left:0; right:0;
    background:rgba(240,240,240,0.95); text-align:center;
    font-size:11px; color:#666; padding:4px 0; z-index:100;
  }
  #tip {
    display:none; position:fixed; background:rgba(255,255,255,0.97);
    border:1px solid #ccc; border-radius:5px; padding:8px 12px;
    font-size:12px; max-width:320px; z-index:200; box-shadow:0 2px 8px rgba(0,0,0,0.15);
    pointer-events:none;
  }
</style>
</head>
<body>
<div id="toolbar">
  <label for="colorBy" style="font-weight:600">着色：</label>
  <select id="colorBy">
    <option value="community" selected>社区（默认）</option>
    <option value="status">治理状态</option>
    <option value="type">文档类型</option>
  </select>
  <span id="stats" style="color:#888"></span>
</div>

<div id="legend">
  <h4>图例</h4>
  <div style="font-size:11px;color:#888;margin-bottom:4px">边线型（可信度）</div>
  <div class="leg-row"><div class="leg-line-solid"></div><span>EXTRACTED 权威边</span></div>
  <div class="leg-row"><div class="leg-line-dashed"></div><span>INFERRED 推断边</span></div>
  <div class="leg-row"><div class="leg-line-dotted"></div><span>AMBIGUOUS 存疑边</span></div>
  <div style="font-size:11px;color:#888;margin:6px 0 4px">节点大小</div>
  <div class="leg-row"><span style="font-size:11px">● 大 = 高中心度；● 小 = 低中心度</span></div>
  <div style="font-size:11px;color:#888;margin:6px 0 4px">节点透明度</div>
  <div class="leg-row"><span style="font-size:11px;color:#9aa0a6">■ 灰显 = deprecated/过期</span></div>
</div>

<div id="cy"></div>
<div id="tip"></div>

<footer>源自 graph.json 派生·非文档原文·非真理源·生成时间 __FOOTER_TS__</footer>

<script>
(function() {
  'use strict';
  // 布局用 cytoscape core 内置 cose（零外部依赖）；不用 fcose（依赖 cose-base，浏览器不可靠，见 CDN 注释）

  const GRAPH_DATA = /*__ELEMENTS_JSON__*/;
  const META = /*__META_JSON__*/;

  document.getElementById('stats').textContent =
    META.node_count + ' 节点 / ' + META.edge_count + ' 边';

  const STYLE = [
    { selector: 'node[kind = "doc"]', style: {
        'width': 'mapData(centrality, 0, 1, 20, 80)',
        'height': 'mapData(centrality, 0, 1, 20, 80)',
        'label': 'data(title)',
        'font-size': 8,
        'text-valign': 'center',
        'text-halign': 'center',
        'text-wrap': 'ellipsis',
        'text-max-width': 70,
        'background-color': 'data(color_community)',
        'border-width': 1,
        'border-color': '#aaa',
        'color': '#333'
    }},
    { selector: 'node[kind = "community"]', style: {
        'background-opacity': 0.08,
        'border-width': 1.5,
        'border-color': '#888',
        'border-style': 'dashed',
        'label': 'data(label)',
        'text-valign': 'top',
        'text-halign': 'center',
        'font-size': 10,
        'font-weight': 'bold',
        'color': '#555',
        'shape': 'round-rectangle',
        'padding': '20px'
    }},
    { selector: 'node.dimmed', style: {
        'opacity': 0.35,
        'background-color': '#9aa0a6'
    }},
    { selector: 'edge', style: {
        'curve-style': 'bezier',
        'target-arrow-shape': 'triangle',
        'width': 1.2,
        'line-color': '#aaa',
        'target-arrow-color': '#aaa',
        'font-size': 7,
        'color': '#777'
    }},
    { selector: 'edge[confidence = "EXTRACTED"]', style: {
        'line-style': 'solid',
        'line-color': '#7c9fc4',
        'target-arrow-color': '#7c9fc4'
    }},
    { selector: 'edge[confidence = "INFERRED"]', style: {
        'line-style': 'dashed',
        'line-color': '#f0c040',
        'target-arrow-color': '#f0c040'
    }},
    { selector: 'edge[confidence = "AMBIGUOUS"]', style: {
        'line-style': 'dotted',
        'line-color': '#e8710a',
        'target-arrow-color': '#e8710a',
        'label': '?未审',
        'font-size': 7
    }}
  ];

  var cy = cytoscape({
    container: document.getElementById('cy'),
    elements: GRAPH_DATA,
    style: STYLE,
    // randomize:true 生成初始随机位置，避免节点堆原点；cose 内置于 core，无需 fcose 扩展
    layout: { name: 'cose', randomize: true, animate: false, padding: 30, nodeRepulsion: 8000, idealEdgeLength: 100, componentSpacing: 40 }
  });

  // 着色切换（前端零重算，§1.4）
  var colorSel = document.getElementById('colorBy');
  colorSel.addEventListener('change', function() {
    var mode = colorSel.value;
    cy.style().selector('node[kind = "doc"]')
      .style('background-color', function(ele) { return ele.data('color_' + mode); })
      .update();
  });

  // 节点 hover/点击 弹详情（D-12）
  var tip = document.getElementById('tip');
  cy.on('tap', 'node[kind = "doc"]', function(e) {
    var d = e.target.data();
    var pos = e.renderedPosition;
    tip.innerHTML =
      '<strong>' + (d.title || d.id) + '</strong><br/>' +
      'slug: ' + d.id + '<br/>' +
      'type: ' + (d.type || '-') + '<br/>' +
      'status: ' + (d.status || '-') + '<br/>' +
      'community: ' + (d.community !== undefined ? d.community : '-') + '<br/>' +
      (d.centrality !== undefined ? 'centrality: ' + d.centrality + '<br/>' : '') +
      'path: <small>' + (d.path || '-') + '</small>';
    tip.style.left = (pos.x + 12) + 'px';
    tip.style.top  = (pos.y + 12) + 'px';
    tip.style.display = 'block';
  });

  // 边 hover 显示 source_location（C1 溯源）
  cy.on('mouseover', 'edge', function(e) {
    var d = e.target.data();
    var pos = e.renderedPosition;
    if (d.source_location) {
      tip.innerHTML = 'relation: ' + (d.relation || '-') +
        '<br/>confidence: ' + (d.confidence || '-') +
        '<br/>source: <small>' + d.source_location + '</small>';
      tip.style.left = (pos.x + 8) + 'px';
      tip.style.top  = (pos.y + 8) + 'px';
      tip.style.display = 'block';
    }
  });

  // 点击空白 / 离开边 → 隐藏 tip
  cy.on('tap', function(e) {
    if (e.target === cy) { tip.style.display = 'none'; }
  });
  cy.on('mouseout', 'edge', function() { tip.style.display = 'none'; });

})();
</script>
</body>
</html>
"""

# 注释：页脚 ts 透传 graph.json generated_at（非 wall-clock）→ 同 graph.json 两跑 HTML byte 级一致（§3.1）
# `</`→`<\/` 转义防 HTML 内联 JSON 中 </script> 提前闭合（§1.5 唯一安全坑）
# CDN 仅 cytoscape core（cytoscape@3.34.0 dist/），内置 cose 布局零外部依赖（§1.2）


def to_html(elements: dict, meta: dict) -> str:
    """graph elements + meta → Cytoscape.js 静态 HTML 字符串（§1.5）。

    elements: build_elements() 的返回值 {"nodes":[...], "edges":[...]}
    meta: {"node_count":..., "edge_count":..., "source_hash":..., "generated_at":...}

    确定性：json.dumps(sort_keys=True) + '</' 转义为 '<\\/' + 透传 generated_at（§3.1）。
    """
    # json.dumps 后必须做 </→<\/ 转义，防 JSON 串内 </script> 提前闭合 HTML（§1.5）
    elements_json = json.dumps(elements, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    meta_json = json.dumps(meta, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")

    # 页脚 ts = meta["generated_at"] 透传 graph.json（非 export 时现取 wall-clock，§3.1）
    footer_ts = meta.get("generated_at", "")

    html = (
        HTML_TEMPLATE
        .replace("{CDN_CYTOSCAPE}", CDN_CYTOSCAPE)
        .replace("/*__ELEMENTS_JSON__*/", elements_json)
        .replace("/*__META_JSON__*/", meta_json)
        .replace("__FOOTER_TS__", footer_ts)
    )
    return html


# ── 主流程 ────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(
        description="knowledge-wiki Phase 9 可视化导出引擎（graph export）"
    )
    ap.add_argument("--kb-root", default=".knowledge", help="知识库根目录（默认 .knowledge）")
    ap.add_argument("--html",     action="store_true", help="导出 Cytoscape.js 交互式 HTML（默认）")
    ap.add_argument("--canvas",   action="store_true", help="导出 Obsidian Canvas（09-02 实现）")
    ap.add_argument("--graphml",  action="store_true", help="导出 GraphML（09-02 实现）")
    ap.add_argument("--include-inferred", action="store_true",
                    help="叠加 .pending-edges.yaml 推断边（09-02 实现）")
    ap.add_argument("--json",     action="store_true", help="以 JSON 输出摘要")
    args = ap.parse_args()

    kb = Path(args.kb_root)
    if not kb.is_dir():
        print(f"❌ 知识库根目录不存在：{kb}", file=sys.stderr)
        sys.exit(1)

    gdir = kb / GRAPH_DIR
    gdir.mkdir(exist_ok=True)
    lock = gdir / EXPORT_LOCK

    # 入口锁检测（独立 .export.lock）
    if lock.exists():
        print(
            "⚠️ 可视化导出正在进行中（.export.lock 存在），请稍候或删除残留锁后重试",
            file=sys.stderr,
        )
        sys.exit(2)
    lock.write_text(f"{os.getpid()}", encoding="utf-8")

    try:
        # ── 降级前置：graph.json ──
        data, gdeg = load_graph_data(kb)
        if gdeg == "graph_missing":
            print("❌ 未编译图谱，请先运行 `graph export` 前先 `health graph-build`", file=sys.stderr)
            sys.exit(1)
        if gdeg == "graph_broken":
            print("❌ 图谱损坏，建议重建 `health graph-build`", file=sys.stderr)
            sys.exit(1)

        # ── 透传 generated_at/source_hash（§3.1 不引入新 wall-clock）──
        source_hash = data.get("source_hash")
        generated_at = data.get("generated_at")
        node_count = data.get("node_count", len(data.get("nodes", [])))
        edge_count = data.get("edge_count", len(data.get("links", [])))

        # ── communities 可选（缺失→着色降级退 0，§5.1）──
        comm, cdeg = load_communities(kb)
        if cdeg in ("communities_missing", "communities_broken"):
            warnings.append(
                f"communities.json {'缺失' if cdeg == 'communities_missing' else '损坏'}，"
                "社区着色降级为 COLOR_NEUTRAL，不报错继续（§5.1）"
            )

        # ── exports_dir 按需创建 ──
        exports_dir = kb / GRAPH_DIR / EXPORTS_DIR
        exports_dir.mkdir(parents=True, exist_ok=True)

        # ── 格式路由（不传标志默认 --html，D-09）──
        want_html = args.html or not (args.html or args.canvas or args.graphml)
        formats: list[str] = []
        oversized = node_count >= EXPORT_NODE_THRESHOLD

        # ── include_inferred 透传：统一 build_elements 共用同一份 elements（D-09/§4.1）──
        # HTML/Canvas/GraphML 共用同一份 elements，保一致 + 性能（§4.1 三格式共享加载/排序逻辑）
        # include_inferred 时先 load_pending_inferred，传 pending_edges 给 build_elements
        # 绝不回填 graph.json/不碰 source_hash/不碰文档（D-10）
        if args.include_inferred:
            pend = load_pending_inferred(kb)
        else:
            pend = None
        meta = {
            "node_count":   node_count,
            "edge_count":   edge_count,
            "source_hash":  source_hash,
            "generated_at": generated_at,  # 透传，非 wall-clock（§3.1）
        }
        elements = build_elements(data, comm, args.include_inferred, pending_edges=pend)

        # ── --html 分支（含 2000 阈值，Canvas/GraphML 无此限制 §3.2）──
        if want_html:
            if oversized:
                # 超阈值：WARNING + 跳过 HTML + 建议改用 Canvas/GraphML（D-13/§3.2）
                warnings.append(
                    f"⚠️ 节点数 {node_count} ≥ {EXPORT_NODE_THRESHOLD}，"
                    "HTML 渲染可能卡顿，已跳过 HTML，"
                    "建议改用 --canvas / --graphml 交 Gephi/Obsidian 处理大图"
                )
            else:
                html = to_html(elements, meta)
                # 唯一写 .graph/exports/graph.html（atomic_write_text，D-10）
                atomic_write_text(exports_dir / HTML_FILE, html)
                formats.append("html")

        # ── --canvas 分支（无 2000 阈值，§3.2；交 Obsidian 处理大图）──
        if args.canvas:
            canvas_txt = to_canvas(elements, meta)
            # 唯一写 .graph/exports/graph.canvas（atomic_write_text，D-10）
            atomic_write_text(exports_dir / CANVAS_FILE, canvas_txt)
            formats.append("canvas")

        # ── --graphml 分支（无 2000 阈值，§3.2；交 Gephi/yEd 处理大图）──
        if args.graphml:
            graphml_txt = to_graphml(elements, meta)
            # 唯一写 .graph/exports/graph.graphml（atomic_write_text，D-10）
            atomic_write_text(exports_dir / GRAPHML_FILE, graphml_txt)
            formats.append("graphml")

        # ── C6 日志（layer=graph-export，记实际导出的 formats）──
        write_c6_log(kb, {
            "formats":          formats,
            "node_count":       node_count,
            "edge_count":       edge_count,
            "include_inferred": args.include_inferred,
            "source_hash":      source_hash,
            "oversized":        oversized,
        })

        # ── 打印警告 ──
        for w in warnings:
            print(f"⚠️  {w}", file=sys.stderr)

        # ── 输出摘要 ──
        if args.json:
            print(json.dumps({
                "formats":     formats,
                "node_count":  node_count,
                "edge_count":  edge_count,
                "oversized":   oversized,
                "exports_dir": str(exports_dir),
                "warnings":    warnings,
            }, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            ts = generated_at or ""
            if formats:
                print("🎨 知识网络可视化导出")
                print(f"   源图 {node_count} 节点 / {edge_count} 边（source_hash {source_hash}）")
                for fmt in formats:
                    if fmt == "html":
                        print(f"   产物：{exports_dir / HTML_FILE}")
                    elif fmt == "canvas":
                        print(f"   产物：{exports_dir / CANVAS_FILE}")
                    elif fmt == "graphml":
                        print(f"   产物：{exports_dir / GRAPHML_FILE}")
                print("   着色默认 community | 边线型：实线=EXTRACTED")
                print(f"   来源：源自 graph.json 派生·非文档原文·非真理源·生成时间 {ts}")
            else:
                print(f"ℹ️  无产物生成（节点超阈值 {node_count}/{EXPORT_NODE_THRESHOLD} 或未指定格式）")

    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
