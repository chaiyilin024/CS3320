from __future__ import annotations

import statistics

from ..utils.io import utc_now_iso


def aggregate_network_compare(
    plays_meta: list[dict],
    network_by_script: dict[str, dict],
) -> dict:
    summaries: list[dict] = []
    by_genre: dict[str, list[dict]] = {}
    by_collection: dict[str, list[dict]] = {}

    for meta in plays_meta:
        sid = meta["script_id"]
        net = network_by_script.get(sid)
        if not net:
            continue
        metrics = net["metrics"]
        genre = net.get("genre") or "未知"
        cid = meta.get("collection_id") or "unknown"
        summaries.append(
            {
                "script_id": sid,
                "title": meta.get("title") or net.get("title", ""),
                "genre": genre,
                "collection_id": cid,
                "metrics": metrics,
            }
        )
        by_genre.setdefault(genre, []).append(metrics)
        by_collection.setdefault(cid, []).append(metrics)

    return {
        "version": "1.0",
        "generated_at": utc_now_iso(),
        "by_genre": [_group_stats(f"genre={k}", k, v) for k, v in by_genre.items()],
        "by_collection": [
            _group_stats(f"collection_id={k}", k, v) for k, v in by_collection.items()
        ],
        "plays": summaries,
    }


def _group_stats(group_key: str, label: str, metrics_list: list[dict]) -> dict:
    def dist(key: str) -> dict:
        vals = [m.get(key, 0) for m in metrics_list if m]
        if not vals:
            return {"mean": 0, "median": 0, "min": 0, "max": 0, "values": []}
        return {
            "mean": round(statistics.mean(vals), 4),
            "median": round(statistics.median(vals), 4),
            "min": round(min(vals), 4),
            "max": round(max(vals), 4),
            "values": [round(v, 4) for v in vals],
        }

    return {
        "group_key": group_key,
        "group_label": label,
        "play_count": len(metrics_list),
        "metrics": {
            "density": dist("density"),
            "avg_degree": dist("avg_degree"),
            "avg_clustering": dist("avg_clustering"),
        },
    }
