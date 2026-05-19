from __future__ import annotations

from collections import Counter, defaultdict

HANGDANG_LIST = [
    "老生",
    "小生",
    "武生",
    "红生",
    "青衣",
    "花旦",
    "刀马旦",
    "老旦",
    "净",
    "丑",
    "文武丑",
    "未知",
    "其他",
]
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
    "未知": "未知",
    "其他": "其他",
}

_IDENTITY_HANGDANG = {
    "君主": "老生",
    "将": "武生",
    "将领": "武生",
    "书生": "小生",
    "谋士": "老生",
    "妃": "青衣",
    "后": "青衣",
}


def analyze_play_role(play: dict) -> dict:
    script_id = play["script_id"]
    blocks = play.get("blocks") or []
    perf_by_char = _performance_profile(blocks)
    characters_out: list[dict] = []
    dist: Counter[str] = Counter()
    coarse_dist: Counter[str] = Counter()
    trait_links: list[dict] = []

    for ch in play.get("characters") or []:
        cid = ch["character_id"]
        labeled = ch.get("hangdang_labeled")
        inferred, confidence, top_features = _infer_hangdang(ch, perf_by_char.get(cid, {}))
        final = labeled if labeled and labeled != "未知" else inferred
        if not final:
            final = "未知"
        characters_out.append(
            {
                "character_id": cid,
                "name": ch["name"],
                "hangdang_labeled": labeled,
                "hangdang_inferred": inferred if not labeled else None,
                "hangdang_final": final,
                "confidence": round(confidence, 3),
                "top_features": top_features,
            }
        )
        dist[final] += 1
        coarse_dist[COARSE_MAP.get(final, "未知")] += 1
        for feat in top_features:
            trait_links.append(
                {"trait": feat, "hangdang": final, "count": 1}
            )

    merged_traits = _merge_trait_links(trait_links)
    return {
        "script_id": script_id,
        "hangdang_distribution": {k: dist[k] for k in HANGDANG_LIST if dist[k]},
        "hangdang_coarse_distribution": {k: coarse_dist[k] for k in coarse_dist},
        "characters": characters_out,
        "trait_summary": merged_traits[:30],
    }


def _performance_profile(blocks: list[dict]) -> dict[str, dict[str, int]]:
    out: dict[str, Counter[str]] = defaultdict(Counter)
    for b in blocks:
        sp = b.get("speaker_id")
        if not sp:
            continue
        tags = b.get("performance_tags") or []
        if not tags:
            tags = ["unknown"]
        for t in tags:
            out[sp][t] += 1
    return {k: dict(v) for k, v in out.items()}


def _infer_hangdang(
    ch: dict, perf: dict[str, int]
) -> tuple[str | None, float, list[str]]:
    features: list[str] = []
    traits = ch.get("traits") or {}
    if traits.get("gender"):
        features.append(f"gender={traits['gender']}")
    if traits.get("identity"):
        features.append(f"identity={traits['identity']}")
    if traits.get("age"):
        features.append(f"age={traits['age']}")
    cues = traits.get("performance_cues") or []
    if cues:
        features.append(f"performance_cues={','.join(cues)}")
    line_count = ch.get("line_count") or 0
    features.append(f"line_count={line_count}")

    labeled = ch.get("hangdang_labeled")
    if labeled and labeled != "未知":
        return None, 0.95, features[:5]

    identity = traits.get("identity") or ""
    for key, hd in _IDENTITY_HANGDANG.items():
        if key in identity:
            return hd, 0.72, features[:5]

    sing = perf.get("唱", 0)
    nian = perf.get("念", 0)
    total = sing + nian + perf.get("做", 0) + perf.get("打", 0) + perf.get("unknown", 0)
    if total > 0:
        sing_ratio = sing / total
        if sing_ratio > 0.45 and line_count >= 30:
            features.append("high_sing_ratio")
            return "老生", 0.65, features[:5]
        if sing_ratio < 0.15 and line_count >= 15:
            return "丑", 0.55, features[:5]

    coarse = ch.get("hangdang_coarse")
    if coarse == "净":
        return "净", 0.6, features[:5]
    if coarse == "旦":
        return "花旦", 0.58, features[:5]

    if line_count >= 40:
        return "老生", 0.5, features[:5]
    if line_count >= 20:
        return "小生", 0.45, features[:5]
    return "未知", 0.3, features[:5]


def _merge_trait_links(links: list[dict]) -> list[dict]:
    counts: Counter[tuple[str, str]] = Counter()
    for ln in links:
        counts[(ln["trait"], ln["hangdang"])] += 1
    merged = [
        {"trait": t, "hangdang": h, "count": c}
        for (t, h), c in counts.most_common()
    ]
    return merged
