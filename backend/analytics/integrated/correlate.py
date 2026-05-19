from __future__ import annotations

from ..network.graph_math import build_adjacency, density, subgraph_density


def analyze_integrated(
    play: dict,
    role: dict,
    network: dict,
    themes: dict,
    narrative: dict,
) -> dict:
    script_id = play["script_id"]
    title = play.get("title", "")
    char_topic = _character_topic_matrix(play, themes)
    snapshots = _stage_network_snapshots(play, narrative)
    correlations = _correlations(play, role, network, themes, narrative, char_topic)
    insights = _summary_insights(play, role, network, themes, narrative, correlations)
    return {
        "script_id": script_id,
        "title": title,
        "correlations": correlations,
        "summary_insights": insights,
        "character_topic_matrix": char_topic,
        "stage_network_snapshots": snapshots,
    }


def _character_topic_matrix(play: dict, themes: dict) -> list[dict]:
    topic_map = {t["topic_id"]: t["label"] for t in themes.get("topics") or []}
    char_blocks: dict[str, list[str]] = {}
    for b in play.get("blocks") or []:
        sp = b.get("speaker_id")
        if not sp or b.get("type") not in ("dialogue", "aria", "recitation"):
            continue
        char_blocks.setdefault(sp, []).append(b.get("text", ""))

    rep_by_topic = {}
    for r in themes.get("representative_blocks") or []:
        rep_by_topic.setdefault(r["topic_id"], []).append(r)

    cells = []
    for ch in play.get("characters") or []:
        cid = ch["character_id"]
        texts = char_blocks.get(cid, [])
        if not texts:
            continue
        joined = " ".join(texts)
        best_tid, best_score = 0, 0.0
        for tid, label in topic_map.items():
            kws = next(
                (t["keywords"] for t in themes["topics"] if t["topic_id"] == tid),
                [],
            )
            score = sum(1 for k in kws if k in joined) / max(len(kws), 1)
            if score > best_score:
                best_score, best_tid = score, tid
        if best_score < 0.05:
            weights = themes.get("topic_composition") or []
            if weights:
                best_tid = max(range(len(weights)), key=lambda i: weights[i])
                best_score = weights[best_tid]
        cells.append(
            {
                "character_id": cid,
                "character_name": ch["name"],
                "topic_id": best_tid,
                "topic_label": topic_map.get(best_tid, ""),
                "strength": round(min(1.0, best_score + 0.2), 3),
            }
        )
    return sorted(cells, key=lambda x: -x["strength"])[:40]


def _stage_network_snapshots(play: dict, narrative: dict) -> list[dict]:
    edge_list = [
        (e["source_id"], e["target_id"], float(e.get("weight") or 1))
        for e in play.get("cooccurrence_edges_raw") or []
        if e.get("source_id") and e.get("target_id")
    ]

    snapshots = []
    for st in narrative.get("plot_stages") or []:
        lo, hi = st["block_range"]
        chars = set()
        for b in play.get("blocks") or []:
            if lo <= b["block_index"] <= hi and b.get("speaker_id"):
                chars.add(b["speaker_id"])
        n, m, dens = subgraph_density(chars, edge_list)
        snapshots.append(
            {
                "stage": st["stage"],
                "block_range": [lo, hi],
                "edge_density": round(dens, 4),
                "node_count": n,
                "edge_count": m,
            }
        )
    return snapshots


def _correlations(
    play: dict,
    role: dict,
    network: dict,
    themes: dict,
    narrative: dict,
    char_topic: list[dict],
) -> list[dict]:
    out = []
    for cell in char_topic[:8]:
        out.append(
            {
                "type": "character_theme",
                "strength": cell["strength"],
                "character_id": cell["character_id"],
                "character_name": cell.get("character_name"),
                "topic_id": cell["topic_id"],
                "topic_label": cell.get("topic_label"),
                "evidence": f"{cell.get('character_name')} 台词与主题「{cell.get('topic_label')}」关键词重合度较高",
            }
        )

    snapshots = _stage_network_snapshots(play, narrative)
    prev_density = None
    for snap in snapshots:
        delta = 0.0
        if prev_density is not None:
            delta = snap["edge_density"] - prev_density
        if abs(delta) > 0.05:
            out.append(
                {
                    "type": "network_stage",
                    "strength": round(min(1.0, abs(delta) * 3), 3),
                    "stage": snap["stage"],
                    "edge_density_delta": round(delta, 4),
                    "evidence": f"「{snap['stage']}」阶段人物同场网络密度变化 {delta:+.2f}",
                }
            )
        prev_density = snap["edge_density"]

    top_topic = max(
        themes.get("topics") or [{"topic_id": 0, "weight": 0}],
        key=lambda t: t.get("weight", 0),
    )
    for st in narrative.get("plot_stages") or []:
        if st["stage"] in ("冲突", "高潮"):
            out.append(
                {
                    "type": "theme_narrative",
                    "strength": round(top_topic.get("weight", 0.5), 3),
                    "topic_id": top_topic["topic_id"],
                    "topic_label": top_topic.get("label"),
                    "stage": st["stage"],
                    "evidence": f"「{st['stage']}」段与全剧主导主题「{top_topic.get('label')}」相对应",
                }
            )
            break

    for ch in role.get("characters") or []:
        if not ch.get("hangdang_final"):
            continue
        peaks = [
            a
            for a in narrative.get("block_annotations") or []
            if a.get("emotion_score", 0) > 0.65
        ]
        if peaks:
            out.append(
                {
                    "type": "hangdang_narrative",
                    "strength": 0.6,
                    "hangdang": ch["hangdang_final"],
                    "peak_block_index": peaks[0]["block_index"],
                    "evidence": f"{ch['hangdang_final']} 行当在 block {peaks[0]['block_index']} 附近情感强度较高",
                }
            )
            break

    main_nodes = sorted(
        network.get("nodes") or [], key=lambda n: -n.get("degree", 0)
    )[:2]
    if len(main_nodes) >= 2:
        out.append(
            {
                "type": "character_network",
                "strength": 0.7,
                "character_id": main_nodes[0]["id"],
                "character_name": main_nodes[0]["name"],
                "evidence": f"{main_nodes[0]['name']} 为关系网络核心（度={main_nodes[0].get('degree')}）",
            }
        )
    return out[:25]


def _summary_insights(
    play: dict,
    role: dict,
    network: dict,
    themes: dict,
    narrative: dict,
    correlations: list[dict],
) -> list[str]:
    insights = []
    metrics = network.get("metrics") or {}
    insights.append(
        f"《{play.get('title', play['script_id'])}》共 {metrics.get('node_count', 0)} 位主要人物、"
        f"{metrics.get('edge_count', 0)} 条关系边，网络密度 {metrics.get('density', 0):.2f}。"
    )
    top_topics = sorted(
        themes.get("topics") or [], key=lambda t: -t.get("weight", 0)
    )[:2]
    if top_topics:
        labels = "、".join(t["label"] for t in top_topics)
        insights.append(f"主题构成以「{labels}」为主。")
    stages = narrative.get("plot_stages") or []
    if stages:
        insights.append(
            f"叙事划分为 {len(stages)} 个阶段，高潮位于 block "
            f"{next((s['block_range'] for s in stages if s['stage']=='高潮'), stages[-1]['block_range'])}。"
        )
    ct = [c for c in correlations if c["type"] == "character_theme"]
    if ct:
        c0 = ct[0]
        insights.append(
            f"{c0.get('character_name')} 与主题「{c0.get('topic_label')}」关联最强（{c0.get('strength')}）。"
        )
    dist = role.get("hangdang_distribution") or {}
    if dist:
        top_hd = max(dist.items(), key=lambda x: x[1])
        insights.append(f"行当以{top_hd[0]}为主（{top_hd[1]} 人）。")
    return insights[:6]
