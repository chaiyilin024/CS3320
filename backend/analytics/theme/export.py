from __future__ import annotations

from itertools import combinations

from .model import ThemeModel


def build_play_themes(play: dict, model: ThemeModel) -> dict:
    script_id = play["script_id"]
    title = play.get("title", "")
    composition = model.play_composition(play)
    topics = []
    for tid in range(model.num_topics):
        words = model.topic_words.get(tid, [])
        keywords = [w for w, _ in words[:15]] or [f"词{tid}"]
        item = {
            "topic_id": tid,
            "label": model.topic_label(tid),
            "weight": round(composition[tid], 4),
            "keywords": keywords,
        }
        kw_weights = [round(float(s), 4) for _, s in words[:15]]
        if kw_weights:
            item["keyword_weights"] = kw_weights
        topics.append(item)
    comp = list(composition)
    s = sum(comp) or 1.0
    comp = [round(w / s, 4) for w in comp]
    for t, w in zip(topics, comp):
        t["weight"] = w

    reps = _representative_blocks(play, model)
    return {
        "script_id": script_id,
        "title": title,
        "model": {
            "method": model.method,
            "num_topics_global": model.num_topics,
            "trained_at": model.trained_at,
        },
        "topics": topics,
        "topic_composition": comp,
        "representative_blocks": reps,
    }


def _representative_blocks(play: dict, model: ThemeModel, per_topic: int = 2) -> list[dict]:
    rows = model.transform_blocks(play)
    if not rows:
        return []
    by_topic: dict[int, list[tuple[float, str, int, str]]] = {}
    for block_id, block_index, text, vec in rows:
        tid = max(range(len(vec)), key=lambda i: vec[i])
        score = vec[tid]
        by_topic.setdefault(tid, []).append((score, block_id, block_index, text))
    reps = []
    for tid, items in by_topic.items():
        for score, block_id, block_index, text in sorted(items, reverse=True)[:per_topic]:
            reps.append(
                {
                    "topic_id": tid,
                    "block_id": block_id,
                    "block_index": block_index,
                    "text_snippet": text[:200],
                    "score": round(float(score), 4),
                }
            )
    return reps


def aggregate_theme_patterns(
    plays_meta: list[dict],
    themes_by_script: dict[str, dict],
    model: ThemeModel | None = None,
) -> dict:
    from ..utils.io import utc_now_iso

    topic_labels, k = _topic_labels_for_aggregate(themes_by_script, model)
    matrix = []
    threshold = 0.12
    cooccur: dict[tuple[int, int], int] = {}

    for meta in plays_meta:
        sid = meta["script_id"]
        th = themes_by_script.get(sid)
        if not th:
            continue
        weights = [0.0] * k
        for t in th.get("topics") or []:
            tid = t["topic_id"]
            if tid < k:
                weights[tid] = t.get("weight", 0)
        if not any(weights):
            comp = th.get("topic_composition") or []
            for i, w in enumerate(comp):
                if i < k:
                    weights[i] = w
        matrix.append(
            {
                "script_id": sid,
                "title": meta.get("title") or th.get("title", ""),
                "collection_id": meta.get("collection_id"),
                "genre": (meta.get("tags") or {}).get("genre_inferred"),
                "weights": [round(w, 4) for w in weights],
            }
        )
        active = [i for i, w in enumerate(weights) if w >= threshold]
        for a, b in combinations(active, 2):
            pair = (min(a, b), max(a, b))
            cooccur[pair] = cooccur.get(pair, 0) + 1

    pairs = [
        {"topic_a": a, "topic_b": b, "count": c}
        for (a, b), c in sorted(cooccur.items(), key=lambda x: -x[1])
    ]
    patterns = _common_patterns(matrix, topic_labels)
    return {
        "version": "1.0",
        "generated_at": utc_now_iso(),
        "topic_labels": topic_labels,
        "play_topic_matrix": matrix,
        "topic_cooccurrence": pairs,
        "common_patterns": patterns,
    }


def _common_patterns(matrix: list[dict], labels: list[dict]) -> list[dict]:
    id_to_label = {lb["topic_id"]: lb["label"] for lb in labels}
    threshold = 0.15
    pattern_counts: dict[tuple[str, ...], list[str]] = {}
    for row in matrix:
        active = [
            id_to_label[i]
            for i, w in enumerate(row["weights"])
            if w >= threshold and i in id_to_label
        ]
        if len(active) < 2:
            continue
        key = tuple(sorted(active))
        pattern_counts.setdefault(key, []).append(row["script_id"])
    n = len(matrix) or 1
    out = []
    for labels_tuple, sids in sorted(
        pattern_counts.items(), key=lambda x: -len(x[1])
    )[:10]:
        out.append(
            {
                "labels": list(labels_tuple),
                "support": round(len(sids) / n, 4),
                "play_count": len(sids),
                "example_script_ids": sids[:10],
            }
        )
    return out


def _topic_labels_for_aggregate(
    themes_by_script: dict[str, dict],
    model: ThemeModel | None,
) -> tuple[list[dict], int]:
    if model is not None:
        labels = [
            {
                "topic_id": tid,
                "label": model.topic_label(tid),
                "keywords": [w for w, _ in model.topic_words.get(tid, [])[:10]],
            }
            for tid in range(model.num_topics)
        ]
        return labels, model.num_topics
    first = next(iter(themes_by_script.values()), {})
    topics = first.get("topics") or []
    k = len(topics)
    labels = [
        {
            "topic_id": int(t["topic_id"]),
            "label": t.get("label", f"主题{t['topic_id']}"),
            "keywords": (t.get("keywords") or [])[:10],
        }
        for t in sorted(topics, key=lambda x: int(x["topic_id"]))
    ]
    return labels, k
