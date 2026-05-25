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

    # 归一化边权，方便前端线粗细映射；按 weight 降序排序
    max_w = max((l["weight"] for l in links_out), default=0.0)
    for l in links_out:
        l["normalized_weight"] = round(l["weight"] / max_w, 4) if max_w > 0 else 0.0
    links_out.sort(key=lambda l: -l["weight"])

    nodes = list(node_meta.keys())
    adj, weighted_deg = build_adjacency(nodes, edge_list)
    n = len(nodes)
    m = len(edge_list)
    dens = density(n, m)

    # 优先用 networkx；失败时退化为自写实现
    nx_metrics = _try_networkx_metrics(nodes, edge_list, node_meta)

    if nx_metrics is not None:
        clustering = nx_metrics["avg_clustering"]
        weighted_clustering = nx_metrics["avg_weighted_clustering"]
        betweenness = nx_metrics["betweenness"]
        weighted_bc = nx_metrics["weighted_betweenness"]
        closeness = nx_metrics["closeness"]
        eigenvector = nx_metrics["eigenvector"]
        communities = nx_metrics["communities"]
        modularity = nx_metrics["modularity"]
        assortativity = nx_metrics["assortativity"]
    else:
        clustering = clustering_coefficient(nodes, adj) if n > 2 and m else 0.0
        weighted_clustering = None
        betweenness = betweenness_simple(nodes, adj) if n > 2 else {nid: 0.0 for nid in nodes}
        weighted_bc = dict(betweenness)
        closeness = {nid: 0.0 for nid in nodes}
        eigenvector = {nid: 0.0 for nid in nodes}
        communities = _community_ids(nodes, adj)
        modularity = None
        assortativity = None

    # 度：拓扑（邻居数）与加权（边权和）
    topo_degree = {nid: len(adj.get(nid, {})) for nid in nodes}
    avg_degree = sum(topo_degree.values()) / n if n else 0.0
    avg_weighted_degree = sum(weighted_deg.values()) / n if n else 0.0
    components = len(connected_components(nodes, adj)) if n else 0

    nodes_out = []
    for nid, meta in node_meta.items():
        nodes_out.append(
            {
                "id": nid,
                "name": meta["name"],
                "hangdang": meta["hangdang"],
                "hangdang_coarse": meta["hangdang_coarse"],
                "is_main": meta["is_main"],
                "degree": topo_degree.get(nid, 0),
                "weighted_degree": round(weighted_deg.get(nid, 0.0), 2),
                "betweenness": round(betweenness.get(nid, 0.0), 4),
                "weighted_betweenness": round(weighted_bc.get(nid, 0.0), 4),
                "closeness": round(closeness.get(nid, 0.0), 4),
                "eigenvector": round(eigenvector.get(nid, 0.0), 4),
                "community_id": int(communities.get(nid, 0)),
            }
        )
    nodes_out.sort(key=lambda x: -x["weighted_degree"])

    metrics: dict = {
        "node_count": n,
        "edge_count": m,
        "density": round(dens, 4),
        "avg_clustering": round(clustering, 4),
        "avg_degree": round(avg_degree, 2),
        "avg_weighted_degree": round(avg_weighted_degree, 2),
        "component_count": max(components, 1),
    }
    if weighted_clustering is not None:
        metrics["avg_weighted_clustering"] = round(float(weighted_clustering), 4)
    if modularity is not None:
        metrics["modularity"] = round(float(modularity), 4)
    if assortativity is not None:
        metrics["assortativity_hangdang"] = round(float(assortativity), 4)

    # 主角子图指标
    main_ids = {nid for nid, meta in node_meta.items() if meta["is_main"]}
    if len(main_ids) >= 2:
        main_metrics = _subgraph_metrics(main_ids, edge_list, node_meta)
        if main_metrics:
            metrics["main_subgraph"] = main_metrics

    return {
        "script_id": script_id,
        "title": title,
        "genre": genre,
        "nodes": nodes_out,
        "links": links_out,
        "metrics": metrics,
    }


def _try_networkx_metrics(
    nodes: list[str],
    edges: list[tuple[str, str, float]],
    node_meta: dict[str, dict],
) -> dict | None:
    """优先使用 networkx 计算中心性、社区、模块度、同配性。失败返回 None。"""
    try:
        import networkx as nx
        from networkx.algorithms import community as nx_comm
    except ImportError:
        return None
    if not nodes:
        return None
    G = nx.Graph()
    for nid in nodes:
        G.add_node(nid, **node_meta.get(nid, {}))
    for u, v, w in edges:
        # 重复边累加权重
        if G.has_edge(u, v):
            G[u][v]["weight"] += w
        else:
            G.add_edge(u, v, weight=w)

    # 给每条边算 distance 仅供加权介数使用
    for _u, _v, d in G.edges(data=True):
        d["distance"] = 1.0 / max(float(d.get("weight", 1.0)), 1e-6)

    try:
        betw = nx.betweenness_centrality(G, normalized=True)
    except Exception:
        betw = {n: 0.0 for n in G.nodes}
    try:
        wbetw = nx.betweenness_centrality(G, weight="distance", normalized=True)
    except Exception:
        wbetw = dict(betw)
    try:
        # 标准 (无权) closeness：自然落在 0~1
        clos = nx.closeness_centrality(G)
    except Exception:
        clos = {n: 0.0 for n in G.nodes}
    try:
        eig = nx.eigenvector_centrality_numpy(G, weight="weight")
    except Exception:
        try:
            eig = nx.eigenvector_centrality(G, weight="weight", max_iter=500)
        except Exception:
            eig = {n: 0.0 for n in G.nodes}
    try:
        avg_clu = nx.average_clustering(G)  # 无权聚类，0~1 直观
    except Exception:
        avg_clu = 0.0
    try:
        avg_wclu = nx.average_clustering(G, weight="weight")  # 带权聚类
    except Exception:
        avg_wclu = 0.0

    # 社区检测：过滤掉 weight<=1 的纯同场弱边再算，避免被对峙性 cooccurrence 误并
    try:
        G_for_comm = nx.Graph()
        G_for_comm.add_nodes_from(G.nodes(data=True))
        kept_edges = 0
        for u, v, d in G.edges(data=True):
            w = float(d.get("weight", 0))
            if w > 1.0:
                G_for_comm.add_edge(u, v, weight=w)
                kept_edges += 1
        if kept_edges == 0:
            G_for_comm = G  # 退化：所有边都很弱
        comms = list(nx_comm.greedy_modularity_communities(G_for_comm, weight="weight"))
        comm_map: dict[str, int] = {}
        for idx, comm in enumerate(comms):
            for node in comm:
                comm_map[node] = idx
        for nid in nodes:
            comm_map.setdefault(nid, 0)
        # 模块度按完整图计算（公平指标）
        mod = nx_comm.modularity(G, comms, weight="weight") if comms else None
    except Exception:
        comm_map = {nid: 0 for nid in nodes}
        mod = None

    try:
        assort = nx.attribute_assortativity_coefficient(G, "hangdang_coarse")
    except Exception:
        assort = None

    return {
        "betweenness": betw,
        "weighted_betweenness": wbetw,
        "closeness": clos,
        "eigenvector": {k: max(float(v), 0.0) for k, v in eig.items()},
        "avg_clustering": float(avg_clu),
        "avg_weighted_clustering": float(avg_wclu),
        "communities": comm_map,
        "modularity": mod,
        "assortativity": assort,
    }


def _subgraph_metrics(
    keep_ids: set[str],
    edges: list[tuple[str, str, float]],
    node_meta: dict[str, dict],
) -> dict | None:
    sub_edges = [(u, v, w) for u, v, w in edges if u in keep_ids and v in keep_ids]
    n = len(keep_ids)
    m = len(sub_edges)
    if n == 0:
        return None
    out: dict = {
        "node_count": n,
        "edge_count": m,
        "density": round(density(n, m), 4),
    }
    try:
        import networkx as nx
        from networkx.algorithms import community as nx_comm

        sub = nx.Graph()
        for nid in keep_ids:
            sub.add_node(nid, **node_meta.get(nid, {}))
        for u, v, w in sub_edges:
            if sub.has_edge(u, v):
                sub[u][v]["weight"] += w
            else:
                sub.add_edge(u, v, weight=w)
        if sub.number_of_edges():
            out["avg_clustering"] = round(float(nx.average_clustering(sub, weight="weight")), 4)
            try:
                comms = list(nx_comm.greedy_modularity_communities(sub, weight="weight"))
                if comms:
                    out["modularity"] = round(
                        float(nx_comm.modularity(sub, comms, weight="weight")), 4
                    )
            except Exception:
                pass
        else:
            out["avg_clustering"] = 0.0
    except ImportError:
        # 用自写聚类
        adj, _ = build_adjacency(list(keep_ids), sub_edges)
        out["avg_clustering"] = round(
            clustering_coefficient(list(keep_ids), adj) if n > 2 and m else 0.0, 4
        )
    return out


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
