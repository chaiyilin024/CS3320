from __future__ import annotations

from collections import defaultdict

from ..utils.io import utc_now_iso

STAGES = ["铺垫", "发展", "冲突", "高潮", "结局"]


def aggregate_narrative_templates(
    plays_meta: list[dict],
    narrative_by_script: dict[str, dict],
) -> dict:
    by_genre: dict[str, list[dict]] = defaultdict(list)
    template_buckets: dict[str, list[str]] = defaultdict(list)

    for meta in plays_meta:
        sid = meta["script_id"]
        nar = narrative_by_script.get(sid)
        if not nar:
            continue
        genre = (meta.get("tags") or {}).get("genre_inferred") or "未知"
        by_genre[genre].append(nar)
        tpl = _classify_template(nar)
        template_buckets[tpl].append(sid)

    templates = []
    for tpl_id, sids in template_buckets.items():
        props = _avg_stage_proportions(
            [narrative_by_script[s] for s in sids if narrative_by_script.get(s)]
        )
        templates.append(
            {
                "template_id": tpl_id,
                "label": _template_label(tpl_id),
                "play_count": len(sids),
                "example_script_ids": sids[:10],
                "stage_proportions": props,
            }
        )

    genre_out = []
    for genre, narratives in by_genre.items():
        props = _avg_stage_proportions(narratives)
        curves = [_resample_rhythm(n) for n in narratives]
        avg_curve = _average_curves(curves) if curves else []
        genre_out.append(
            {
                "genre": genre,
                "play_count": len(narratives),
                "avg_stage_lengths": props,
                "avg_rhythm_curve": avg_curve[:50],
            }
        )

    return {
        "version": "1.0",
        "generated_at": utc_now_iso(),
        "templates": templates,
        "by_genre": genre_out,
    }


def _classify_template(nar: dict) -> str:
    stages = nar.get("plot_stages") or []
    lengths = []
    for st in stages:
        lo, hi = st["block_range"]
        lengths.append(max(0, hi - lo + 1))
    if not lengths:
        return "default"
    total = sum(lengths) or 1
    props = [l / total for l in lengths]
    if len(props) >= 4 and props[3] > 0.28:
        return "climax_centric"
    if props[0] > 0.35:
        return "slow_opening"
    return "classic_five_act"


def _template_label(tpl_id: str) -> str:
    return {
        "climax_centric": "高潮前置型",
        "slow_opening": "慢热铺垫型",
        "classic_five_act": "起承转合型",
        "default": "常规型",
    }.get(tpl_id, tpl_id)


def _avg_stage_proportions(narratives: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for nar in narratives:
        stages = nar.get("plot_stages") or []
        total_blocks = 0
        for st in stages:
            lo, hi = st["block_range"]
            span = max(0, hi - lo + 1)
            totals[st["stage"]] += span
            total_blocks += span
        if total_blocks <= 0:
            continue
        for k in list(totals.keys()):
            pass
    if not narratives:
        return {s: 0.2 for s in STAGES}
    acc: dict[str, list[float]] = defaultdict(list)
    for nar in narratives:
        stages = nar.get("plot_stages") or []
        total_blocks = sum(
            max(0, st["block_range"][1] - st["block_range"][0] + 1) for st in stages
        ) or 1
        for st in stages:
            lo, hi = st["block_range"]
            span = max(0, hi - lo + 1)
            acc[st["stage"]].append(span / total_blocks)
    return {
        stage: round(sum(vals) / len(vals), 4) if vals else 0.0
        for stage, vals in acc.items()
    }


def _resample_rhythm(nar: dict, points: int = 50) -> list[dict]:
    series = nar.get("rhythm_series") or []
    if not series:
        return []
    if len(series) <= points:
        return series
    step = len(series) / points
    out = []
    for i in range(points):
        idx = min(len(series) - 1, int(i * step))
        p = dict(series[idx])
        p["block_index"] = i
        out.append(p)
    return out


def _average_curves(curves: list[list[dict]]) -> list[dict]:
    if not curves:
        return []
    n = min(len(c) for c in curves)
    out = []
    keys = ("dialogue_density", "aria_ratio", "action_intensity", "emotion_score", "tension_score")
    for i in range(n):
        point = {"block_index": i, "window": curves[0][i].get("window", 20)}
        for k in keys:
            vals = [c[i].get(k, 0) for c in curves if i < len(c)]
            point[k] = round(sum(vals) / len(vals), 4) if vals else 0
        out.append(point)
    return out
