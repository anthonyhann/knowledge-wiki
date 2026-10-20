#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["networkx==3.6.1"]
# ///
"""explore_questions.py — Phase 8 可探索问题预计算引擎

消费 communities.json + graph.json status/expires + .pending-edges.yaml + coverage
已解决缺口 → 信号融合加权 + 三层去噪 + Top-N + 每类配额 + 确定性模板生成问题文案
→ 输出 explorable-questions.json。

与 graph_build.py（构图派生）/ graph_query.py（只读查询）/ graph_analyze.py（涌现分析）
/ discover_prefilter.py（候选发现）职责分离——这是第五个脚本。

绝不重算图分析（不跑 Louvain/中心度，只读 communities.json 现成字段）。
绝不重做 coverage 缺口分析（不重算 sha1，只消费外部传入的结构化缺口/已解决 hash）。
只读 communities.json/graph.json + 读 .pending-edges.yaml，唯一写 explorable-questions.json，
绝不写 graph.json（不回填）/不碰 source_hash/不写 .pending-edges.yaml/不碰 L0 文档（D-06）。
仅 health graph 同批显式触发（D-05），绝不进 in/ask 热路径。

用法:
    uv run explore_questions.py --kb-root .knowledge --json
    uv run explore_questions.py --kb-root .knowledge --top-n 10 --cohesion-threshold 0.40 \
        --min-hit-count 3 --gaps-file gaps.txt --resolved-gaps resolved.txt

仅依赖 networkx==3.6.1（禁止 default extra，避免拉 numpy/scipy/matplotlib）。
禁止引入第三方 YAML 库、外部社区检测库、外部图计算库、embedding 库。
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# ── 常量 ──────────────────────────────────────────────────────────────
GRAPH_DIR = ".graph"
EXPLORE_LOCK = ".explore.lock"
COMMUNITIES_FILE = "communities.json"
EXPLORABLE_FILE = "explorable-questions.json"
PENDING_FILE = ".pending-edges.yaml"
SCHEMA_VERSION = "1.0"
ALGO_VERSION = "explore-questions@1.0"
DEFAULT_TOP_N = 10
DEFAULT_COHESION_THRESHOLD = 0.40
DEFAULT_MIN_HIT_COUNT = 3
DEFAULT_PER_TYPE_QUOTA = {
    "island": 4,
    "low-cohesion": 2,
    "god-node": 2,
    "coverage-gap": 3,
}

# 加权公式权重（RESEARCH §8.2：weight = 0.6×signal_strength + 0.4×demand_heat）
W_STRUCT = 0.6
W_DEMAND = 0.4

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


# ── 复用范式：atomic_write（照搬 graph_analyze.py L63-83）─────────────
def atomic_write(file_path: Path, payload: dict) -> None:
    """原子写 JSON：同盘临时文件 → flush+fsync → os.replace 覆盖。

    仅用于写 explorable-questions.json（唯一写出口）。
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


# ── 复用范式：compute_source_hash（照搬 graph_analyze.py L87-116）──────
def compute_source_hash(kb_root: Path) -> str:
    """对全部业务 .md 的 (相对路径, mtime, size) 三元组排序后求 sha256。

    备用：主路径优先透传 communities.json 的 source_hash（守确定性）。
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
    """可探索问题生成成功后追加一条操作日志到 .logs/personal/{user-id}.md。

    复用既有 log-rules.md 通道，layer 标 graph-explore（区别于 graph-analyze）。
    user-id 缺失时降级跳过，不阻断生成。
    """
    user_id = resolve_user_id()
    if not user_id:
        warnings.append("无法确定 user-id（请设置 git config user.name 或 KB_OWNER），C6 日志已跳过")
        return
    try:
        logs_dir = kb_root / ".logs" / "personal"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / f"{user_id}.md"
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        detail = {
            "questions": payload.get("questions"),
            "island": payload.get("island"),
            "low_cohesion": payload.get("low_cohesion"),
            "god_node": payload.get("god_node"),
            "coverage_gap": payload.get("coverage_gap"),
            "filtered_deprecated": payload.get("filtered_deprecated"),
            "filtered_pending": payload.get("filtered_pending"),
            "filtered_resolved": payload.get("filtered_resolved"),
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
            f"\n## [{now}] @{user_id} | health | graph-explore\n"
            f"  detail: {json.dumps(detail, ensure_ascii=False)}\n"
        )
        with log_file.open("a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as exc:  # noqa: BLE001 — C6 日志失败不阻断生成
        warnings.append(f"C6 日志写入失败（不阻断生成）：{exc}")


# ── load_communities 只读加载（仿 load_graph 范式）────────────────────
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


# ── load_graph 只读加载（照搬 graph_analyze.py L184-201）──────────────
def load_graph(kb_root: Path):
    """加载 graph.json → (G | None, degraded | None)。

    不存在 → (None, "graph_missing")；损坏 → (None, "graph_broken")。
    只读，绝不写 graph.json。供去噪查 status/expires。
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


# ── is_expired 时效谓词（新增）─────────────────────────────────────────
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


# ── normalize_slug：slug 归一化去目录前缀（去噪② 正确性关键）──────────
def normalize_slug(s: str) -> str:
    """把路径式 slug 与 graph node id 归一到同形（basename 去 .md）。

    graph node id 是 basename（如 print-timeout），而 .pending-edges.yaml 的
    source/target 可能是路径式 slug（如 ops/print-timeout，pending-edges-rules.md:36-37）。
    本函数去目录前缀 + 去尾部 .md，使两端可比对，避免去噪② 漏排。
    """
    if s is None:
        return ""
    base = str(s).rsplit("/", 1)[-1]
    if base.endswith(".md"):
        base = base[:-3]
    return base


# ── 信号融合：四类 build_*_signals（RESEARCH §8.2）────────────────────
def build_island_signals(communities: dict, cohesion_threshold: float) -> list:
    """孤岛信号：纯孤儿 degree==0 → 1.0，准孤岛 degree==1 → 0.6（demand_heat=0.0）。"""
    signals = []
    for isl in communities.get("islands", []):
        degree = isl.get("degree", 0)
        signal_strength = 1.0 if degree == 0 else 0.6
        signals.append({
            "signal_type": "island",
            "source": f"island:{isl['id']}",
            "refs": [isl["id"]],
            "signal_strength": signal_strength,
            "demand_heat": 0.0,
            "_payload": isl,
        })
    return signals


def build_low_cohesion_signals(communities: dict, cohesion_threshold: float) -> list:
    """低内聚社区信号：1.0-cohesion（入选 cohesion<阈值 且 size>=3，避免 2 人小社区误报）。"""
    signals = []
    for c in communities.get("communities", []):
        if c.get("cohesion", 1.0) < cohesion_threshold and c.get("size", 0) >= 3:
            signals.append({
                "signal_type": "low-cohesion",
                "source": f"low-cohesion:{c['id']}",
                "refs": list(c.get("members", [])),
                "signal_strength": round(1.0 - c["cohesion"], 4),
                "demand_heat": 0.0,
                "_payload": c,
            })
    return signals


def build_god_node_signals(communities: dict, cohesion_threshold: float) -> list:
    """god-node 信号：degree_centrality（仅 is_hub_candidate==true 入选，天然排 deprecated）。"""
    signals = []
    for g in communities.get("god_nodes", []):
        if g.get("is_hub_candidate") is True:
            signals.append({
                "signal_type": "god-node",
                "source": f"god-node:{g['id']}",
                "refs": [g["id"]],
                "signal_strength": round(g["degree_centrality"], 4),
                "demand_heat": 0.0,
                "_payload": g,
            })
    return signals


def build_coverage_gap_signals(gaps: list, min_hit_count: int) -> list:
    """coverage-gap 信号：signal_strength=0.6 基线，demand_heat=min(count/max_count,1.0)。

    gaps 是 [{"hash":..,"count":..}, ...]（由 main 从外部缺口候选构造）；
    入选 count>=min_hit_count。脚本只消费结构化缺口，不自己跑 gap_analysis/sha1。
    """
    if not gaps:
        return []
    max_count = max((g.get("count", 0) for g in gaps), default=0) or 1
    signals = []
    for g in gaps:
        count = g.get("count", 0)
        if count >= min_hit_count:
            h = g["hash"]
            signals.append({
                "signal_type": "coverage-gap",
                "source": f"coverage-gap:{h}",
                "refs": [h],
                "signal_strength": 0.6,
                "demand_heat": round(min(count / max_count, 1.0), 4),
                "hit_count": count,
                "_payload": {"hash": h, "count": count},
            })
    return signals


# ── load_pending_pairs：手写行扫描读 .pending-edges.yaml（禁 yaml）─────
def load_pending_pairs(kb_root: Path):
    """读 .pending-edges.yaml 的 pending[].source/target → (无向端点对集合, 归一端点 slug 集合)。

    手写行扫描（禁 import yaml，仿 graph_build.py）。端点先过 normalize_slug 去目录前缀，
    使路径式 slug（ops/print-timeout）与 graph node id（print-timeout）同形可比对（去噪② 正确性关键）。
    .pending-edges.yaml 放 .knowledge/ 根（不在 .graph/ 下，删 .graph/ 后仍在）。
    """
    path = kb_root / PENDING_FILE
    pending_pairs: set = set()
    pending_slugs: set = set()
    if not path.is_file():
        return pending_pairs, pending_slugs
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return pending_pairs, pending_slugs

    in_pending = False
    cur_source = None
    cur_target = None

    def _flush(s, t):
        if s and t:
            ns, nt = normalize_slug(s), normalize_slug(t)
            pending_slugs.add(ns)
            pending_slugs.add(nt)
            pending_pairs.add((min(ns, nt), max(ns, nt)))

    for raw in lines:
        stripped = raw.strip()
        # 进入 pending: 块
        if stripped == "pending:" or stripped.startswith("pending:"):
            in_pending = True
            continue
        if not in_pending:
            continue
        # 顶层其它键（无缩进且以 key: 结尾）→ 退出 pending 块
        if raw and not raw[0].isspace() and stripped.endswith(":") and stripped != "pending:":
            break
        # 新列表项起点：flush 上一项
        if stripped.startswith("- "):
            _flush(cur_source, cur_target)
            cur_source = None
            cur_target = None
            stripped = stripped[2:].strip()
        # 在列表项内提取 source/target
        if stripped.startswith("source:"):
            cur_source = stripped[len("source:"):].strip().strip("'\"")
        elif stripped.startswith("target:"):
            cur_target = stripped[len("target:"):].strip().strip("'\"")
    # flush 末项
    _flush(cur_source, cur_target)
    return pending_pairs, pending_slugs


# ── load_resolved_gaps：读 --resolved-gaps 文件（不重算 sha1）──────────
def load_resolved_gaps(path_str) -> set:
    """读已解决缺口 hash 集合。

    已解决缺口 hash 由 AI 从 health coverage『已解决』分组提供（RESEARCH §3.4），
    脚本不重算 sha1。path 为 None 或不存在 → 空 set；逐行读 hash（忽略空行/#注释）。
    """
    resolved: set = set()
    if not path_str:
        return resolved
    p = Path(path_str)
    if not p.is_file():
        return resolved
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        resolved.add(line)
    return resolved


# ── load_coverage_gaps：读 --gaps-file 结构化缺口（不重算 sha1）────────
def load_coverage_gaps(path_str) -> list:
    """读 coverage 缺口候选 → [{"hash":str,"count":int}, ...]。

    coverage 缺口候选由 AI 从 health coverage『高频未答』分组写临时文件传入（RESEARCH §3.4），
    脚本只消费结构化缺口、不自己跑 gap_analysis/sha1（守 §十三-1）。
    每行为 {"hash":..,"count":..} JSON 或 `hash<TAB>count`（忽略空行/#注释）。
    path 为 None 或不存在 → 空 list（coverage-gap 候选恒空，向后兼容）。
    """
    gaps: list = []
    if not path_str:
        return gaps
    p = Path(path_str)
    if not p.is_file():
        return gaps
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("{"):
            try:
                obj = json.loads(line)
                gaps.append({"hash": str(obj["hash"]), "count": int(obj["count"])})
            except (ValueError, KeyError):
                continue
        else:
            parts = line.split("\t") if "\t" in line else line.split()
            if len(parts) >= 2:
                try:
                    gaps.append({"hash": str(parts[0]), "count": int(parts[1])})
                except ValueError:
                    continue
    return gaps


# ── denoise：三层去噪（RESEARCH §五）──────────────────────────────────
def denoise(signals, G, pending_pairs, pending_slugs, resolved_gaps):
    """三层去噪 + filtered 计数。

    ① graph.json status==deprecated 或 expires<今日（EXPIRED）→ 排除
       （island 显式查节点；low-cohesion 全成员失效才排；god-node 经 is_hub_candidate 天然排）。
    ② pending 端点 slug（已归一）已在 pending_slugs → 排除 island 连接题（不撞 discover，§五②）。
    ③ coverage-gap hash 在 resolved_gaps → 排除（不出录入题）。
    返回 (kept, filtered)。
    """
    filtered = {"deprecated_or_expired": 0, "in_pending": 0, "coverage_resolved": 0}
    kept = []

    def _node_dead(slug: str) -> bool:
        """节点 deprecated 或 EXPIRED；graph 缺失时降级为不排除。"""
        if G is None:
            return False
        nid = slug if slug in G.nodes else None
        if nid is None:
            # 尝试归一匹配
            for cand in G.nodes:
                if normalize_slug(cand) == normalize_slug(slug):
                    nid = cand
                    break
        if nid is None:
            return False
        attrs = G.nodes[nid]
        if attrs.get("status") == "deprecated":
            return True
        return is_expired(attrs.get("expires"))

    for sig in signals:
        st = sig["signal_type"]
        if st == "island":
            slug = sig["refs"][0]
            if _node_dead(slug):
                filtered["deprecated_or_expired"] += 1
                continue
            if normalize_slug(slug) in pending_slugs:
                filtered["in_pending"] += 1
                continue
            kept.append(sig)
        elif st == "low-cohesion":
            members = sig["refs"]
            if members and all(_node_dead(m) for m in members):
                filtered["deprecated_or_expired"] += 1
                continue
            kept.append(sig)
        elif st == "god-node":
            # is_hub_candidate 已天然排 deprecated，不再显式查
            kept.append(sig)
        elif st == "coverage-gap":
            h = sig["refs"][0]
            if h in resolved_gaps:
                filtered["coverage_resolved"] += 1
                continue
            kept.append(sig)
        else:
            kept.append(sig)

    return kept, filtered


# ── render_question：四类确定性模板（RESEARCH §九，守 C1/D-04）─────────
def render_question(sig: dict):
    """按 signal_type 确定性生成 (question, why_worth_digging)。

    全用疑问/建议口吻（D-04 不替用户下结论）。low-cohesion 守 C1 标
    「横切性强（可能正常）」绝不断言「质量差」（§2.2）。插值字段从 _payload 取。
    """
    st = sig["signal_type"]
    p = sig.get("_payload", {})
    if st == "island":
        title = p.get("title", p.get("id", ""))
        question = f"「{title}」目前未与任何知识关联，它应该连到哪里？"
        why = "结构孤岛：无任何关联边，补连可让它被检索与遍历命中。"
    elif st == "low-cohesion":
        cid = p.get("id", "")
        dominant = p.get("dominant_type", "")
        cohesion = p.get("cohesion", "")
        question = (
            f"「{dominant}」社区（{cid}）横切性强（内聚度 {cohesion}），"
            f"是否需要拆分或补连？"
        )
        why = "社区横切性强（正常）——人工判断是否需要拆分或补主线。"
    elif st == "god-node":
        title = p.get("title", p.get("id", ""))
        dc = p.get("degree_centrality", "")
        question = f"「{title}」是知识枢纽（中心度 {dc}），改动它会影响哪些知识？"
        why = "高连接+高桥接枢纽，改动牵连面大，值得先盘清下游影响。"
    elif st == "coverage-gap":
        cnt = p.get("count", sig.get("hit_count", ""))
        question = f"团队近 7 天多次（{cnt} 次）问及某主题但知识库无记录，要不要录入？"
        why = "高频未命中且尚未录入，录入可直接消除检索盲区。"
    else:
        question = ""
        why = ""
    return question, why


# ── rank_quota_truncate：去重合并 + 配额 + 排序 + Top-N（RESEARCH §8.3）
def rank_quota_truncate(signals, top_n: int, per_type_quota: dict) -> list:
    """同节点去重合并取最高 weight + 每类配额 + (-weight,signal_type,source) 排序 + Top-N。

    - weight = round(0.6*signal_strength + 0.4*demand_heat, 4)（RESEARCH §8.2，排序前写入）。
    - 去重合并只在『同一 slug 的单节点信号』间做（island/god-node，去重键=normalize_slug(refs[0])），
      同一 slug 同时被判孤岛+枢纽时取 weight 最高的一条；low-cohesion 以 source(community_id)
      为独立键、coverage-gap 以 hash 为独立键，均不参与跨节点 slug 合并。
    - 确定性 tiebreak：合并组内 weight 相同时按 (signal_type, source) 字典序最小取一条。
    - 每类配额：先按 signal_type 分桶各取 per_type_quota 条；全局按 (-weight,signal_type,source)
      排序取前 top_n（守确定性 §4.1）。
    """
    # 计算 weight
    for sig in signals:
        sig["weight"] = round(
            W_STRUCT * sig["signal_strength"] + W_DEMAND * sig["demand_heat"], 4
        )

    # 同节点去重合并（仅 island/god-node 单节点信号按归一 slug 合并）
    single_node_best: dict = {}
    others: list = []
    for sig in signals:
        if sig["signal_type"] in ("island", "god-node"):
            key = normalize_slug(sig["refs"][0])
            cur = single_node_best.get(key)
            if cur is None:
                single_node_best[key] = sig
            elif sig["weight"] > cur["weight"] or (
                sig["weight"] == cur["weight"]
                and (sig["signal_type"], sig["source"])
                < (cur["signal_type"], cur["source"])
            ):
                single_node_best[key] = sig
        else:
            others.append(sig)
    merged = list(single_node_best.values()) + others

    # 每类配额：分桶各取 per_type_quota 条（桶内按 weight 降序 + tiebreak）
    buckets: dict = {}
    for sig in merged:
        buckets.setdefault(sig["signal_type"], []).append(sig)
    quota_kept: list = []
    for st, bucket in buckets.items():
        bucket_sorted = sorted(
            bucket, key=lambda s: (-s["weight"], s["signal_type"], s["source"])
        )
        limit = per_type_quota.get(st, len(bucket_sorted))
        quota_kept.extend(bucket_sorted[:limit])

    # 全局排序 + Top-N
    ranked = sorted(
        quota_kept, key=lambda s: (-s["weight"], s["signal_type"], s["source"])
    )
    return ranked[:top_n]


# ── 主流程 ────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(
        description="knowledge-wiki Phase 8 可探索问题预计算引擎"
    )
    ap.add_argument("--kb-root", default=".knowledge", help="知识库根目录（默认 .knowledge）")
    ap.add_argument("--top-n", type=int, default=DEFAULT_TOP_N,
                    help=f"可探索问题数量上限（默认 {DEFAULT_TOP_N}）")
    ap.add_argument("--cohesion-threshold", type=float, default=DEFAULT_COHESION_THRESHOLD,
                    help=f"低内聚社区入选阈值（默认 {DEFAULT_COHESION_THRESHOLD}）")
    ap.add_argument("--min-hit-count", type=int, default=DEFAULT_MIN_HIT_COUNT,
                    help=f"coverage 缺口入选最小命中次数（默认 {DEFAULT_MIN_HIT_COUNT}）")
    ap.add_argument("--gaps-file", default=None,
                    help="coverage『高频未答』缺口候选文件（AI 从 health coverage 写入，脚本只读不重算 sha1）")
    ap.add_argument("--resolved-gaps", default=None,
                    help="已解决缺口 hash 文件（AI 从 health coverage『已解决』分组写入，脚本只读不重算 sha1）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出（供 health 报告消费）")
    args = ap.parse_args()

    kb = Path(args.kb_root)
    if not kb.is_dir():
        print(f"❌ 知识库根目录不存在：{kb}", file=sys.stderr)
        sys.exit(1)

    gdir = kb / GRAPH_DIR
    gdir.mkdir(exist_ok=True)
    lock = gdir / EXPLORE_LOCK

    # 入口锁检测
    if lock.exists():
        print(
            "⚠️ 可探索问题生成正在进行中（.explore.lock 存在），请稍候或删除残留锁后重试",
            file=sys.stderr,
        )
        sys.exit(2)
    lock.write_text(f"{os.getpid()}", encoding="utf-8")

    try:
        # ── 降级前置 ──
        comm, degraded = load_communities(kb)
        if degraded == "communities_missing":
            print("❌ 未生成图分析结果，请先运行 health graph", file=sys.stderr)
            sys.exit(1)
        if degraded == "communities_broken":
            print("❌ communities.json 损坏，建议重建 health graph", file=sys.stderr)
            sys.exit(1)

        # 透传确定性字段（非现取 wall-clock，§4.1）
        source_hash = comm.get("source_hash")
        generated_at = comm.get("generated_at")
        skipped = comm.get("skipped", False)

        # graph.json 供去噪查 status/expires（缺失则去噪降级为不排除）
        G, gdeg = load_graph(kb)
        if gdeg in ("graph_missing", "graph_broken"):
            warnings.append(f"graph.json 不可用（{gdeg}），status/expires 去噪降级为不排除")

        pending_pairs, pending_slugs = load_pending_pairs(kb)
        resolved_gaps = load_resolved_gaps(args.resolved_gaps)
        gaps = load_coverage_gaps(args.gaps_file)

        # ── 四类信号融合（skipped 时跳过 low-cohesion，§8.4）──
        island_sigs = build_island_signals(comm, args.cohesion_threshold)
        low_cohesion_sigs = (
            [] if skipped else build_low_cohesion_signals(comm, args.cohesion_threshold)
        )
        god_sigs = build_god_node_signals(comm, args.cohesion_threshold)
        coverage_sigs = build_coverage_gap_signals(gaps, args.min_hit_count)
        all_signals = island_sigs + low_cohesion_sigs + god_sigs + coverage_sigs

        # ── 三层去噪 ──
        kept, filtered = denoise(all_signals, G, pending_pairs, pending_slugs, resolved_gaps)

        # ── 去重合并 + 配额 + 排序 + Top-N ──
        ranked = rank_quota_truncate(kept, args.top_n, DEFAULT_PER_TYPE_QUOTA)

        # ── 填文案 + 组装 questions[]（移除 _payload）──
        questions = []
        type_counts = {"island": 0, "low-cohesion": 0, "god-node": 0, "coverage-gap": 0}
        for sig in ranked:
            question, why = render_question(sig)
            q = {
                "signal_type": sig["signal_type"],
                "source": sig["source"],
                "weight": sig["weight"],
                "signal_strength": sig["signal_strength"],
                "demand_heat": sig["demand_heat"],
                "refs": sig["refs"],
                "question": question,
                "why_worth_digging": why,
            }
            if sig["signal_type"] == "coverage-gap":
                q["hit_count"] = sig.get("hit_count", sig["_payload"].get("count"))
            questions.append(q)
            type_counts[sig["signal_type"]] = type_counts.get(sig["signal_type"], 0) + 1

        # ── 组装 explorable-questions.json（§七 schema）──
        payload = {
            "schema_version": SCHEMA_VERSION,
            "algo_version": ALGO_VERSION,
            "source_hash": source_hash,
            "generated_at": generated_at,
            "params": {
                "top_n": args.top_n,
                "cohesion_threshold": args.cohesion_threshold,
                "min_hit_count": args.min_hit_count,
                "per_type_quota": DEFAULT_PER_TYPE_QUOTA,
            },
            "question_count": len(questions),
            "filtered": filtered,
            "skipped": skipped,
            "questions": questions,
        }

        # ── 落盘（唯一写，绝不回填 graph.json/不碰 source_hash）──
        atomic_write(gdir / EXPLORABLE_FILE, payload)

        # ── C6 日志（layer=graph-explore）──
        write_c6_log(kb, {
            "questions": len(questions),
            "island": type_counts["island"],
            "low_cohesion": type_counts["low-cohesion"],
            "god_node": type_counts["god-node"],
            "coverage_gap": type_counts["coverage-gap"],
            "filtered_deprecated": filtered["deprecated_or_expired"],
            "filtered_pending": filtered["in_pending"],
            "filtered_resolved": filtered["coverage_resolved"],
            "source_hash": source_hash,
        })

        # ── 输出 ──
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"🔍 可探索问题生成完成：{len(questions)} 条")
            print(
                f"   类型：孤岛 {type_counts['island']} | 低内聚 {type_counts['low-cohesion']} "
                f"| 枢纽 {type_counts['god-node']} | 缺口 {type_counts['coverage-gap']}"
            )
            print(
                f"   去噪：deprecated/EXPIRED {filtered['deprecated_or_expired']} "
                f"| 已入 pending {filtered['in_pending']} "
                f"| 已解决缺口 {filtered['coverage_resolved']}"
            )
            if skipped:
                print("   ⚠️ 小语料：已跳过低内聚社区信号（communities.json skipped=true）")
            print(f"   产物：{gdir / EXPLORABLE_FILE}")
            for w in warnings:
                print(f"   ⚠️ {w}")

    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
