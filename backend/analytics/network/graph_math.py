from __future__ import annotations

from collections import defaultdict


def build_adjacency(
    nodes: list[str], edges: list[tuple[str, str, float]]
) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    adj: dict[str, dict[str, float]] = defaultdict(dict)
    degree: dict[str, float] = defaultdict(float)
    for u, v, w in edges:
        adj[u][v] = adj[u].get(v, 0) + w
        adj[v][u] = adj[v].get(u, 0) + w
        degree[u] += w
        degree[v] += w
    for n in nodes:
        adj.setdefault(n, {})
    return dict(adj), dict(degree)


def density(n: int, m: int) -> float:
    if n <= 1:
        return 0.0
    return (2 * m) / (n * (n - 1))


def connected_components(nodes: list[str], adj: dict[str, dict[str, float]]) -> list[set[str]]:
    seen: set[str] = set()
    comps = []
    for start in nodes:
        if start in seen:
            continue
        stack = [start]
        comp = set()
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            comp.add(u)
            for v in adj.get(u, {}):
                if v not in seen:
                    stack.append(v)
        comps.append(comp)
    return comps


def betweenness_simple(nodes: list[str], adj: dict[str, dict[str, float]]) -> dict[str, float]:
    """无权近似介数（节点少时够用）。"""
    bc = {n: 0.0 for n in nodes}
    n = len(nodes)
    if n <= 2:
        return bc
    for s in nodes:
        stack: list[str] = []
        pred: dict[str, list[str]] = {w: [] for w in nodes}
        sigma: dict[str, float] = {w: 0.0 for w in nodes}
        dist: dict[str, int] = {w: -1 for w in nodes}
        sigma[s] = 1.0
        dist[s] = 0
        queue = [s]
        for v in queue:
            stack.append(v)
            for w, _ in adj.get(v, {}).items():
                if dist[w] < 0:
                    queue.append(w)
                    dist[w] = dist[v] + 1
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        delta = {w: 0.0 for w in nodes}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
            if w != s:
                bc[w] += delta[w]
    scale = 2.0 / ((n - 1) * (n - 2)) if n > 2 else 1.0
    return {k: v * scale for k, v in bc.items()}


def clustering_coefficient(nodes: list[str], adj: dict[str, dict[str, float]]) -> float:
    coeffs = []
    for u in nodes:
        nbrs = list(adj.get(u, {}).keys())
        k = len(nbrs)
        if k < 2:
            continue
        links = 0
        for i, a in enumerate(nbrs):
            for b in nbrs[i + 1 :]:
                if b in adj.get(a, {}):
                    links += 1
        coeffs.append(links / (k * (k - 1) / 2))
    return sum(coeffs) / len(coeffs) if coeffs else 0.0


def subgraph_density(char_set: set[str], edges: list[tuple[str, str, float]]) -> tuple[int, int, float]:
    sub_edges = [
        (u, v, w) for u, v, w in edges if u in char_set and v in char_set
    ]
    n = len(char_set)
    m = len(sub_edges)
    return n, m, density(n, m)
