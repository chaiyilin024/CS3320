from __future__ import annotations

from collections import Counter, defaultdict

from ..utils.hangdang import (
    maybe_raw_feature,
    normalize_coarse,
    normalize_hangdang,
)
from .traits_extract import extract_traits

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

# identity → 可能行当（仅来自台词上下文抽出的 identity，不依赖人物姓名）
_IDENTITY_HANGDANG: list[tuple[str, str, float]] = [
    ("君主", "老生", 0.75),
    ("谋士", "老生", 0.70),
    ("将领", "武生", 0.60),
    ("妃后", "青衣", 0.75),
    ("公子", "小生", 0.70),
    ("弟兄", "小生", 0.55),
    ("书生", "小生", 0.70),
    ("兵卒", "净", 0.50),
]

# 表演线索 → 行当倾向
_PERF_HANGDANG: dict[str, tuple[str, float]] = {
    "sing_dominant": ("老生", 0.65),
    "action_dominant": ("武生", 0.65),
}


def _line_bucket(n: int) -> str:
    if n >= 50:
        return "high"
    if n >= 15:
        return "mid"
    return "low"


def analyze_play_role(play: dict) -> dict:
    script_id = play["script_id"]
    blocks = play.get("blocks") or []
    perf_by_char = _performance_profile(blocks)
    traits_derived_all = extract_traits(play)

    characters_out: list[dict] = []
    dist: Counter[str] = Counter()
    coarse_dist: Counter[str] = Counter()
    trait_links: list[dict] = []
    inferred_count = 0
    labeled_count = 0

    for ch in play.get("characters") or []:
        cid = ch["character_id"]
        labeled_raw = ch.get("hangdang_labeled")
        labeled = normalize_hangdang(labeled_raw) if labeled_raw else None
        derived = traits_derived_all.get(cid) or {}
        inferred, confidence, top_features = _infer_hangdang(
            ch, perf_by_char.get(cid, {}), derived
        )
        inferred_norm = normalize_hangdang(inferred) if inferred else None
        raw_feat = maybe_raw_feature(labeled_raw, labeled)
        if raw_feat and raw_feat not in top_features:
            top_features = [raw_feat, *top_features[:7]]
        if labeled and labeled != "未知":
            final = labeled
            labeled_count += 1
        else:
            final = inferred_norm or "未知"
            if final and final != "未知":
                inferred_count += 1
        record: dict = {
            "character_id": cid,
            "name": ch["name"],
            "hangdang_labeled": labeled,
            "hangdang_inferred": inferred_norm if not labeled_raw else None,
            "hangdang_final": final,
            "confidence": round(confidence, 3),
            "top_features": top_features,
        }
        if derived:
            record["traits_derived"] = derived
        characters_out.append(record)
        dist[final] += 1
        coarse_dist[normalize_coarse(ch.get("hangdang_coarse"), final)] += 1
        for feat in top_features:
            trait_links.append({"trait": feat, "hangdang": final, "count": 1})

    merged_traits = _merge_trait_links(trait_links)
    return {
        "script_id": script_id,
        "hangdang_distribution": {k: dist[k] for k in HANGDANG_LIST if dist[k]},
        "hangdang_coarse_distribution": {k: coarse_dist[k] for k in coarse_dist},
        "characters": characters_out,
        "trait_summary": merged_traits[:30],
        "labeled_count": labeled_count,
        "inferred_count": inferred_count,
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
    ch: dict, perf: dict[str, int], derived: dict
) -> tuple[str | None, float, list[str]]:
    """综合 traits_derived + 表演侧重 + 行数分箱，得出行当推断。

    返回 (hangdang, confidence, top_features)。
    top_features 是离散化后的 key=value 串，便于做 PMI 聚合。
    """
    features: list[str] = []
    traits = ch.get("traits") or {}
    line_count = ch.get("line_count") or 0
    bucket = _line_bucket(line_count)
    features.append(f"line_count_bucket={bucket}")

    # traits_derived 特征
    if derived.get("gender"):
        features.append(f"gender={derived['gender']}")
    if derived.get("age"):
        features.append(f"age={derived['age']}")
    if derived.get("identity"):
        features.append(f"identity={derived['identity']}")
    for pers in derived.get("personality") or []:
        features.append(f"personality={pers}")

    # 表演线索：把 performance_cues 拆成 multi-hot
    cues = (traits.get("performance_cues") or []) + (derived.get("performance_cues") or [])
    for c in dict.fromkeys(cues):
        features.append(f"cue={c}")

    # 表演侧重比例
    sing = perf.get("唱", 0)
    nian = perf.get("念", 0)
    zuo = perf.get("做", 0)
    da = perf.get("打", 0)
    total = sing + nian + zuo + da + perf.get("unknown", 0)
    sing_ratio = sing / total if total else 0.0
    action_ratio = (zuo + da) / total if total else 0.0

    # 1) 已标注：features 已完整，直接返回（不再产生推断分支）
    labeled = ch.get("hangdang_labeled")
    if labeled and labeled != "未知":
        return None, 0.95, _truncate(features, 8)

    # 4) 决策树
    gender = derived.get("gender") or "未知"
    age = derived.get("age") or ""
    identity = derived.get("identity") or ""
    personality = derived.get("personality") or []

    # 4a) 女性
    if gender == "女":
        if age == "老年":
            return "老旦", 0.78, _truncate(features, 6)
        if "勇猛" in personality or action_ratio > 0.2:
            return "刀马旦", 0.7, _truncate(features, 6)
        if sing_ratio > 0.3:
            return "青衣", 0.72, _truncate(features, 6)
        return "花旦", 0.65, _truncate(features, 6)

    # 4b) 老年男性
    if age == "老年" and gender != "女":
        return "老生", 0.72, _truncate(features, 6)

    # 4c) 身份倾向
    for ident_key, hd, conf in _IDENTITY_HANGDANG:
        if ident_key == identity:
            features.append(f"matched_identity={ident_key}")
            target_hd = hd
            adj = 0.0
            if hd == "老生" and "智谋" in personality:
                adj += 0.05
            if hd == "小生" and age == "少年":
                adj += 0.08
            # 将领的细分：唱多→老生，打多→武生，否则武生兜底
            if ident_key == "将领":
                if "勇猛" in personality or action_ratio > 0.2:
                    target_hd = "武生"
                    adj += 0.05
                elif sing_ratio > 0.4 and bucket == "high":
                    target_hd = "老生"
                elif sing_ratio == 0 and bucket == "low":
                    target_hd = "武生"
            return target_hd, min(0.95, conf + adj), _truncate(features, 6)

    # 4d) 表演侧重
    if total > 0:
        if sing_ratio > 0.45 and bucket != "low":
            features.append("sing_dominant")
            return "老生", 0.6, _truncate(features, 6)
        if action_ratio > 0.25:
            features.append("action_dominant")
            return "武生", 0.6, _truncate(features, 6)
        if sing_ratio < 0.15 and bucket != "low" and "诙谐" in personality:
            return "丑", 0.6, _truncate(features, 6)

    # 4e) 粗行当兜底（来自 cleaned）
    coarse = ch.get("hangdang_coarse")
    if coarse == "净":
        return "净", 0.55, _truncate(features, 6)
    if coarse == "旦":
        if age == "老年":
            return "老旦", 0.55, _truncate(features, 6)
        return "花旦", 0.5, _truncate(features, 6)
    if coarse == "生":
        if age == "少年":
            return "小生", 0.55, _truncate(features, 6)
        if bucket == "high":
            return "老生", 0.5, _truncate(features, 6)
        return "小生", 0.45, _truncate(features, 6)

    # 4f) 仅靠台词体量
    if bucket == "high":
        return "老生", 0.4, _truncate(features, 6)
    if bucket == "mid":
        return "小生", 0.35, _truncate(features, 6)
    return "未知", 0.3, _truncate(features, 6)


def _truncate(features: list[str], n: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for f in features:
        if f in seen:
            continue
        seen.add(f)
        out.append(f)
        if len(out) >= n:
            break
    return out


def _merge_trait_links(links: list[dict]) -> list[dict]:
    counts: Counter[tuple[str, str]] = Counter()
    for ln in links:
        counts[(ln["trait"], ln["hangdang"])] += 1
    merged = [
        {"trait": t, "hangdang": h, "count": c}
        for (t, h), c in counts.most_common()
    ]
    return merged
