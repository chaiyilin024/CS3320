from __future__ import annotations

from .graph_math import (
    betweenness_simple,
    build_adjacency,
    clustering_coefficient,
    connected_components,
    density,
)

COARSE_MAP = {
    "老生": "生",
    "小生": "生",
    "武生": "生",
    "红生": "生",
    "青衣": "旦",
    "花旦": "旦",
    "刀马旦": "旦",
    "老旦": "旦",
    "净": "净",
    "丑": "丑",
    "文武丑": "丑",
}


def analyze_play_network(play: dict, role: dict | None = None) -> dict:
    script_id = play["script_id"]
    title = play.get("title", "")
    genre = (play.get("tags") or {}).get("genre_inferred") or "未知"
    chars = {c["character_id"]: c for c in play.get("characters") or []}
    role_map = {}
    if role:
        role_map = {c["character_id"]: c for c in role.get("characters") or []}

    node_meta: dict[str, dict] = {}
    for cid, ch in chars.items():
        hd = ch.get("hangdang_labeled") or "未知"
        rf = role_map.get(cid) or {}
        if rf.get("hangdang_final"):
            hd = rf["hangdang_final"]
        coarse = COARSE_MAP.get(hd) or ch.get("hangdang_coarse") or "未知"
        if coarse not in ("生", "旦", "净", "丑", "未知", "其他"):
            coarse = "未知"
        node_meta[cid] = {
            "name": ch["name"],
            "hangdang": hd if hd else "未知",
            "hangdang_coarse": coarse,
            "is_main": bool(ch.get("is_main")),
        }

    edge_list: list[tuple[str, str, float]] = []
    links_out: list[dict] = []
    for edge in play.get("cooccurrence_edges_raw") or []:
        src = edge.get("source_id")
        tgt = edge.get("target_id")
        w = float(edge.get("weight") or 0)
        if not src or not tgt or w <= 0:
            continue
        _ensure_node(node_meta, src)
        _ensure_node(node_meta, tgt)
        edge_list.append((src, tgt, w))
        types = edge.get("relation_types") or ["其他"]
        links_out.append(
            {
                "source": src,
                "target": tgt,
                "weight": w,
                "types": types,
                "dialogue_count": edge.get("dialogue_count", 0),
            }
        )

    nodes = list(node_meta.keys())
    adj, degrees = build_adjacency(nodes, edge_list)
    n = len(nodes)
    m = len(edge_list)
    dens = density(n, m)
    clustering = clustering_coefficient(nodes, adj) if n > 2 and m else 0.0
    avg_degree = sum(degrees.values()) / n if n else 0.0
    components = len(connected_components(nodes, adj)) if n else 0
    betweenness = betweenness_simple(nodes, adj) if n > 2 else {nid: 0.0 for nid in nodes}
    communities = _community_ids(nodes, adj)

    nodes_out = []
    for nid, meta in node_meta.items():
        nodes_out.append(
            {
                "id": nid,
                "name": meta["name"],
                "hangdang": meta["hangdang"],
                "hangdang_coarse": meta["hangdang_coarse"],
                "is_main": meta["is_main"],
                "degree": int(degrees.get(nid, 0)),
                "betweenness": round(betweenness.get(nid, 0.0), 4),
                "community_id": communities.get(nid, 0),
            }
        )
    nodes_out.sort(key=lambda x: -x["degree"])

    return {
        "script_id": script_id,
        "title": title,
        "genre": genre,
        "nodes": nodes_out,
        "links": links_out,
        "metrics": {
            "node_count": n,
            "edge_count": m,
            "density": round(dens, 4),
            "avg_clustering": round(clustering, 4),
            "avg_degree": round(avg_degree, 2),
            "component_count": max(components, 1),
        },
    }


def _ensure_node(node_meta: dict[str, dict], cid: str) -> None:
    if cid not in node_meta:
        node_meta[cid] = {
            "name": cid[2:] if cid.startswith("c_") else cid,
            "hangdang": "未知",
            "hangdang_coarse": "未知",
            "is_main": False,
        }


def _community_ids(nodes: list[str], adj: dict[str, dict[str, float]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for i, comp in enumerate(connected_components(nodes, adj)):
        for node in comp:
            out[node] = i
    return out
