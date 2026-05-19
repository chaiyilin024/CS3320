from __future__ import annotations

from collections import Counter, defaultdict

from ..utils.io import utc_now_iso
from .infer import HANGDANG_LIST


def aggregate_role_analysis(
    plays_meta: list[dict],
    role_by_script: dict[str, dict],
) -> dict:
    matrix: Counter[tuple[str, str]] = Counter()
    by_collection: dict[str, dict] = {}
    inference_results: list[dict] = []

    for meta in plays_meta:
        sid = meta["script_id"]
        role = role_by_script.get(sid)
        if not role:
            continue
        cid = meta.get("collection_id") or "unknown"
        cname = meta.get("collection_name") or cid
        if cid not in by_collection:
            by_collection[cid] = {
                "collection_id": cid,
                "collection_name": cname,
                "hangdang_distribution": Counter(),
                "trait_hangdang_links": Counter(),
                "play_count": 0,
            }
        by_collection[cid]["play_count"] += 1
        for hd, n in (role.get("hangdang_distribution") or {}).items():
            by_collection[cid]["hangdang_distribution"][hd] += n
        for ln in role.get("trait_summary") or []:
            key = (ln["trait"], ln["hangdang"])
            by_collection[cid]["trait_hangdang_links"][key] += ln.get("count", 1)
            matrix[key] += ln.get("count", 1)

        for ch in role.get("characters") or []:
            if ch.get("hangdang_labeled"):
                continue
            inf = ch.get("hangdang_inferred")
            if inf and inf != "未知":
                inference_results.append(
                    {
                        "script_id": sid,
                        "character_id": ch["character_id"],
                        "name": ch["name"],
                        "hangdang_inferred": inf,
                        "confidence": ch.get("confidence", 0.5),
                        "top_features": ch.get("top_features") or [],
                    }
                )

    era_buckets: dict[str, Counter] = defaultdict(Counter)
    era_play_count: dict[str, int] = defaultdict(int)
    for meta in plays_meta:
        sid = meta["script_id"]
        role = role_by_script.get(sid)
        if not role:
            continue
        era = (meta.get("tags") or {}).get("era_inferred") or "未知"
        for hd, n in (role.get("hangdang_distribution") or {}).items():
            era_buckets[era][hd] += n
        era_play_count[era] += 1

    global_matrix = []
    for (feat, hd), count in matrix.most_common(200):
        global_matrix.append(
            {
                "feature": feat,
                "hangdang": hd,
                "count": count,
                "ratio": round(count / max(sum(matrix.values()), 1), 4),
            }
        )

    collections_out = []
    for cid, data in by_collection.items():
        links = [
            {"trait": t, "hangdang": h, "count": c}
            for (t, h), c in data["trait_hangdang_links"].most_common(20)
        ]
        collections_out.append(
            {
                "collection_id": cid,
                "collection_name": data["collection_name"],
                "hangdang_distribution": dict(data["hangdang_distribution"]),
                "trait_hangdang_links": links,
                "play_count": data["play_count"],
            }
        )

    by_era = [
        {
            "era": era,
            "hangdang_distribution": {
                k: v for k, v in dist.items() if k in HANGDANG_LIST
            },
            "play_count": era_play_count.get(era, 0),
        }
        for era, dist in era_buckets.items()
    ]

    return {
        "version": "1.0",
        "generated_at": utc_now_iso(),
        "global_feature_hangdang_matrix": global_matrix,
        "by_collection": collections_out,
        "by_era_bucket": by_era,
        "inference_results": inference_results[:500],
    }
