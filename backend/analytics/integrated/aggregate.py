"""Aggregate single-play analytics artifacts into global/*.json."""
from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from ..utils.genre import normalize_genre
from ..utils.io import load_catalog, utc_now_iso

TOPIC_CO_THRESHOLD = 0.05
PATTERN_THRESHOLD = 0.10

TEMPLATE_RULES: list[tuple[str, str, callable]] = [
    (
        "climax_front",
        "高潮前置型",
        lambda p: p.get("高潮", 0) >= 0.32,
    ),
    (
        "slow_opening",
        "铺垫冗长型",
        lambda p: p.get("铺垫", 0) >= 0.38,
    ),
    (
        "conflict_heavy",
        "冲突密集型",
        lambda p: p.get("冲突", 0) >= 0.22,
    ),
    (
        "classic_five_act",
        "起承转合型",
        lambda _p: True,
    ),
]


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _metric_distribution(values: list[float]) -> dict:
    clean = [float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(float(v))]
    if not clean:
        return {"mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "values": []}
    s = sorted(clean)
    n = len(clean)
    return {
        "mean": round(statistics.fmean(clean), 4),
        "median": round(statistics.median(clean), 4),
        "min": round(s[0], 4),
        "max": round(s[-1], 4),
        "values": [round(v, 4) for v in clean],
    }


def _sanitize_metrics(metrics: dict) -> dict:
    """Remove NaN/Inf so output JSON is browser JSON.parse-safe."""
    out: dict = {}
    for key, val in metrics.items():
        if isinstance(val, float):
            if math.isfinite(val):
                out[key] = val
            continue
        if isinstance(val, dict):
            out[key] = _sanitize_metrics(val)
            continue
        out[key] = val
    return out


def _catalog_index(catalog: dict) -> dict[str, dict]:
    return {p["script_id"]: p for p in catalog.get("plays") or []}


def _stage_proportions(narrative: dict) -> dict[str, float]:
    stages = narrative.get("plot_stages") or []
    spans: dict[str, int] = {}
    total = 0
    for st in stages:
        br = st.get("block_range") or [0, 0]
        length = max(0, int(br[1]) - int(br[0]) + 1)
        name = st.get("stage") or st.get("label") or "未知"
        spans[name] = spans.get(name, 0) + length
        total += length
    if not total:
        return {}
    return {k: round(v / total, 4) for k, v in spans.items()}


def _assign_template(props: dict[str, float]) -> tuple[str, str]:
    for tid, label, pred in TEMPLATE_RULES:
        if pred(props):
            return tid, label
    return "classic_five_act", "起承转合型"


def aggregate_role_analysis(
    plays_dir: Path,
    catalog_idx: dict[str, dict],
) -> dict:
    matrix: Counter[tuple[str, str]] = Counter()
    by_collection: dict[str, dict] = defaultdict(
        lambda: {
            "hangdang_distribution": Counter(),
            "trait_hangdang_links": Counter(),
            "play_count": 0,
        }
    )
    by_era: dict[str, dict] = defaultdict(
        lambda: {"hangdang_distribution": Counter(), "play_count": 0}
    )
    inference_results: list[dict] = []

    for play_dir in sorted(plays_dir.iterdir()):
        if not play_dir.is_dir():
            continue
        role = _load_json(play_dir / "role.json")
        if not role:
            continue
        sid = role["script_id"]
        meta = catalog_idx.get(sid, {})
        collection_id = meta.get("collection_id", "unknown")
        collection_name = meta.get("collection_name", collection_id)
        era = (meta.get("tags") or {}).get("era_inferred") or "未知"

        by_collection[collection_id]["collection_id"] = collection_id
        by_collection[collection_id]["collection_name"] = collection_name
        by_collection[collection_id]["play_count"] += 1
        by_era[era]["play_count"] = by_era[era].get("play_count", 0) + 1

        for ch in role.get("characters") or []:
            hd = ch.get("hangdang_final") or "未知"
            by_collection[collection_id]["hangdang_distribution"][hd] += 1
            by_era[era].setdefault("hangdang_distribution", Counter())[hd] += 1
            for feat in ch.get("top_features") or []:
                matrix[(feat, hd)] += 1
                by_collection[collection_id]["trait_hangdang_links"][(feat, hd)] += 1
            if ch.get("hangdang_inferred"):
                inference_results.append({
                    "script_id": sid,
                    "character_id": ch["character_id"],
                    "name": ch.get("name", ""),
                    "hangdang_inferred": ch["hangdang_inferred"],
                    "confidence": ch.get("confidence", 0.0),
                    "top_features": (ch.get("top_features") or [])[:8],
                })

    hangdang_totals = Counter(h for (_, h), c in matrix.items() for _ in range(c))
    global_matrix = [
        {
            "feature": feat,
            "hangdang": hd,
            "count": cnt,
            "ratio": round(cnt / hangdang_totals[hd], 4) if hangdang_totals[hd] else 0.0,
        }
        for (feat, hd), cnt in matrix.most_common()
    ]

    collection_out = []
    for cid, row in sorted(by_collection.items(), key=lambda x: -x[1]["play_count"]):
        links = [
            {"trait": t, "hangdang": h, "count": c}
            for (t, h), c in row["trait_hangdang_links"].most_common(40)
        ]
        collection_out.append({
            "collection_id": cid,
            "collection_name": row.get("collection_name", cid),
            "hangdang_distribution": dict(row["hangdang_distribution"]),
            "trait_hangdang_links": links,
            "play_count": row["play_count"],
        })

    era_out = [
        {
            "era": era,
            "hangdang_distribution": dict(row["hangdang_distribution"]),
            "play_count": row["play_count"],
        }
        for era, row in sorted(by_era.items(), key=lambda x: -x[1]["play_count"])
    ]

    return {
        "version": "1.0",
        "generated_at": utc_now_iso(),
        "global_feature_hangdang_matrix": global_matrix,
        "by_collection": collection_out,
        "by_era_bucket": era_out,
        "inference_results": inference_results,
    }


def aggregate_network_compare(
    plays_dir: Path,
    catalog_idx: dict[str, dict],
) -> dict:
    by_genre: dict[str, list[dict]] = defaultdict(list)
    by_collection: dict[str, list[dict]] = defaultdict(list)
    play_summaries: list[dict] = []

    for play_dir in sorted(plays_dir.iterdir()):
        if not play_dir.is_dir():
            continue
        net = _load_json(play_dir / "network.json")
        if not net:
            continue
        sid = net["script_id"]
        meta = catalog_idx.get(sid, {})
        genre = normalize_genre(net.get("genre") or (meta.get("tags") or {}).get("genre_inferred"))
        collection_id = meta.get("collection_id", "unknown")
        metrics = net.get("metrics") or {}

        summary = {
            "script_id": sid,
            "title": net.get("title") or meta.get("title"),
            "genre": genre,
            "collection_id": collection_id,
            "metrics": _sanitize_metrics(metrics),
        }
        play_summaries.append(summary)
        by_genre[genre].append(summary)
        by_collection[collection_id].append(summary)

    def _group_stats(group_key: str, label: str, rows: list[dict]) -> dict:
        densities = [r["metrics"].get("density", 0.0) for r in rows]
        degrees = [r["metrics"].get("avg_degree", 0.0) for r in rows]
        clusterings = [r["metrics"].get("avg_clustering", 0.0) for r in rows]
        modularities = [r["metrics"].get("modularity", 0.0) for r in rows if r["metrics"].get("modularity") is not None]
        metrics_out = {
            "density": _metric_distribution(densities),
            "avg_degree": _metric_distribution(degrees),
            "avg_clustering": _metric_distribution(clusterings),
        }
        if modularities:
            metrics_out["modularity"] = _metric_distribution(modularities)
        return {
            "group_key": group_key,
            "group_label": label,
            "play_count": len(rows),
            "metrics": metrics_out,
        }

    genre_out = [
        _group_stats(f"genre={g}", g, rows)
        for g, rows in sorted(by_genre.items(), key=lambda x: -len(x[1]))
    ]
    collection_out = [
        _group_stats(f"collection_id={cid}", cid, rows)
        for cid, rows in sorted(by_collection.items(), key=lambda x: -len(x[1]))
    ]

    return {
        "version": "1.0",
        "generated_at": utc_now_iso(),
        "by_genre": genre_out,
        "by_collection": collection_out,
        "plays": play_summaries,
    }


def _play_label_weights(themes: dict) -> dict[str, float]:
    """Sum per-play topic weights by semantic label (topics already deduped by label after merge)."""
    from ..theme.model import FALLBACK_LABEL

    out: dict[str, float] = {}
    for t in themes.get("topics") or []:
        label = str(t.get("label") or FALLBACK_LABEL)
        out[label] = out.get(label, 0.0) + float(t.get("weight") or 0.0)
    return out


def _weights_for_labels(label_weights: dict[str, float], canonical: list[str]) -> list[float]:
    return [round(label_weights.get(lab, 0.0), 4) for lab in canonical]


def _infer_canonical_from_corpus(
    plays_dir: Path,
) -> tuple[list[str], list[dict]]:
    """Without a global model, infer heatmap columns from per-play theme label frequencies."""
    from ..theme.model import FALLBACK_LABEL

    label_mass: Counter[str] = Counter()
    keyword_votes: dict[str, Counter[str]] = defaultdict(Counter)
    for play_dir in sorted(plays_dir.iterdir()):
        if not play_dir.is_dir():
            continue
        themes = _load_json(play_dir / "themes.json")
        if not themes:
            continue
        for t in themes.get("topics") or []:
            lab = str(t.get("label") or FALLBACK_LABEL)
            label_mass[lab] += float(t.get("weight") or 0.0)
            for kw in (t.get("keywords") or [])[:12]:
                keyword_votes[lab][str(kw)] += 1
    ordered = [lab for lab, _ in label_mass.most_common() if lab != FALLBACK_LABEL]
    if FALLBACK_LABEL in label_mass:
        ordered.append(FALLBACK_LABEL)
    topic_labels = [
        {
            "topic_id": i,
            "label": lab,
            "keywords": [w for w, _ in keyword_votes[lab].most_common(10)],
        }
        for i, lab in enumerate(ordered)
    ]
    return ordered, topic_labels


def aggregate_theme_patterns(
    plays_dir: Path,
    catalog_idx: dict[str, dict],
    theme_model=None,
) -> dict:
    from ..theme.model import FALLBACK_LABEL, global_topic_label_entries

    if theme_model is not None:
        topic_labels = global_topic_label_entries(theme_model)
        canonical_labels = [e["label"] for e in topic_labels]
    else:
        canonical_labels, topic_labels = _infer_canonical_from_corpus(plays_dir)

    label_to_idx = {lab: i for i, lab in enumerate(canonical_labels)}
    play_rows: list[dict] = []
    co_counts: Counter[tuple[int, int]] = Counter()
    pattern_plays: dict[frozenset[str], set[str]] = defaultdict(set)
    n_plays = 0

    for play_dir in sorted(plays_dir.iterdir()):
        if not play_dir.is_dir():
            continue
        themes = _load_json(play_dir / "themes.json")
        if not themes:
            continue
        n_plays += 1
        sid = themes["script_id"]
        meta = catalog_idx.get(sid, {})

        label_weights = _play_label_weights(themes)
        for lab, w in label_weights.items():
            if lab not in label_to_idx and w >= TOPIC_CO_THRESHOLD:
                label_to_idx[lab] = len(canonical_labels)
                canonical_labels.append(lab)
                topic_labels.append({
                    "topic_id": label_to_idx[lab],
                    "label": lab,
                    "keywords": [],
                })

        play_rows.append({
            "script_id": sid,
            "title": themes.get("title") or meta.get("title"),
            "collection_id": meta.get("collection_id"),
            "genre": normalize_genre((meta.get("tags") or {}).get("genre_inferred")),
            "weights": _weights_for_labels(label_weights, canonical_labels),
        })

        active_labels = [
            str(t.get("label") or FALLBACK_LABEL)
            for t in themes.get("topics") or []
            if float(t.get("weight") or 0) >= TOPIC_CO_THRESHOLD
        ]
        active_indices = sorted({
            label_to_idx[lab] for lab in active_labels if lab in label_to_idx
        })
        for a, b in combinations(active_indices, 2):
            co_counts[(a, b)] += 1

        pattern_labels = sorted({
            str(t.get("label") or FALLBACK_LABEL)
            for t in themes.get("topics") or []
            if float(t.get("weight") or 0) >= PATTERN_THRESHOLD
        })
        for i in range(len(pattern_labels)):
            for j in range(i + 1, len(pattern_labels)):
                pattern_plays[frozenset({pattern_labels[i], pattern_labels[j]})].add(sid)

    topic_cooccurrence = [
        {"topic_a": a, "topic_b": b, "count": c}
        for (a, b), c in co_counts.most_common()
    ]

    common_patterns = []
    for labels, sids in sorted(
        pattern_plays.items(),
        key=lambda x: -len(x[1]),
    )[:20]:
        if len(labels) < 2:
            continue
        common_patterns.append({
            "labels": sorted(labels),
            "support": round(len(sids) / n_plays, 4) if n_plays else 0.0,
            "play_count": len(sids),
            "example_script_ids": sorted(sids)[:10],
        })

    return {
        "version": "1.0",
        "generated_at": utc_now_iso(),
        "topic_labels": topic_labels,
        "play_topic_matrix": play_rows,
        "topic_cooccurrence": topic_cooccurrence,
        "common_patterns": common_patterns,
    }


RHYTHM_RESAMPLE_LEN = 100


def _resample_series(values: list[float], n: int = RHYTHM_RESAMPLE_LEN) -> list[float]:
    """Linearly interpolate variable-length sequences to fixed length for cross-play averaging."""
    if not values:
        return []
    m = len(values)
    if m == 1:
        return [round(values[0], 4)] * n
    out: list[float] = []
    for i in range(n):
        pos = (i / (n - 1)) * (m - 1) if n > 1 else 0.0
        lo = int(pos)
        hi = min(lo + 1, m - 1)
        frac = pos - lo
        v = values[lo] * (1.0 - frac) + values[hi] * frac
        out.append(round(v, 4))
    return out


def _avg_resampled_curves(curves: list[list[float]], n: int = RHYTHM_RESAMPLE_LEN) -> list[dict]:
    if not curves:
        return []
    resampled = [_resample_series(c, n) for c in curves if c]
    if not resampled:
        return []
    return [
        {
            "block_index": i,
            "tension_score": round(
                statistics.fmean(row[i] for row in resampled), 4
            ),
        }
        for i in range(n)
    ]


def aggregate_narrative_templates(
    plays_dir: Path,
    catalog_idx: dict[str, dict],
) -> dict:
    template_plays: dict[str, list[str]] = defaultdict(list)
    template_props: dict[str, list[dict[str, float]]] = defaultdict(list)
    by_genre_props: dict[str, list[dict[str, float]]] = defaultdict(list)
    by_genre_tension: dict[str, list[list[float]]] = defaultdict(list)
    all_props: list[dict[str, float]] = []
    perf_total: Counter[str] = Counter()

    for play_dir in sorted(plays_dir.iterdir()):
        if not play_dir.is_dir():
            continue
        narrative = _load_json(play_dir / "narrative.json")
        if not narrative:
            continue
        sid = narrative["script_id"]
        meta = catalog_idx.get(sid, {})
        genre = normalize_genre((meta.get("tags") or {}).get("genre_inferred"))
        props = _stage_proportions(narrative)
        if not props:
            continue
        tid, label = _assign_template(props)
        template_plays[tid].append(sid)
        template_props[tid].append(props)
        by_genre_props[genre].append(props)
        all_props.append(props)

        for k, v in (narrative.get("performance_mark_distribution") or {}).items():
            perf_total[str(k)] += int(v)

        rhythm = narrative.get("rhythm_series") or []
        if rhythm:
            tensions = [float(p.get("tension_score") or 0.5) for p in rhythm]
            by_genre_tension[genre].append(tensions)

    templates = []
    label_map = {tid: label for tid, label, _ in TEMPLATE_RULES}
    for tid, sids in sorted(template_plays.items(), key=lambda x: -len(x[1])):
        props_list = template_props[tid]
        avg_props: dict[str, float] = {}
        if props_list:
            keys = set().union(*props_list)
            for key in keys:
                avg_props[key] = round(
                    statistics.fmean(p.get(key, 0.0) for p in props_list), 4
                )
        templates.append({
            "template_id": tid,
            "label": label_map.get(tid, tid),
            "play_count": len(sids),
            "example_script_ids": sorted(sids)[:10],
            "stage_proportions": avg_props,
        })

    by_genre = []
    for genre, props_list in sorted(by_genre_props.items(), key=lambda x: -len(x[1])):
        keys = set().union(*props_list) if props_list else set()
        avg_stage_lengths = {
            key: round(statistics.fmean(p.get(key, 0.0) for p in props_list), 4)
            for key in keys
        }
        entry: dict = {
            "genre": genre,
            "play_count": len(props_list),
            "avg_stage_lengths": avg_stage_lengths,
        }
        avg_curve = _avg_resampled_curves(by_genre_tension.get(genre, []))
        if avg_curve:
            entry["avg_rhythm_curve"] = avg_curve
        by_genre.append(entry)

    corpus_stage_proportions: dict[str, float] = {}
    if all_props:
        keys = set().union(*all_props)
        corpus_stage_proportions = {
            key: round(statistics.fmean(p.get(key, 0.0) for p in all_props), 4)
            for key in keys
        }

    return {
        "version": "1.0",
        "generated_at": utc_now_iso(),
        "total_play_count": len(all_props),
        "corpus_stage_proportions": corpus_stage_proportions,
        "performance_distribution": dict(perf_total),
        "templates": templates,
        "by_genre": by_genre,
    }


def aggregate_theme_quality_report(
    plays_dir: Path,
    catalog_idx: dict[str, dict],
) -> dict:
    from ..theme.quality import aggregate_theme_quality

    return aggregate_theme_quality(plays_dir, catalog_idx)


def run_global_aggregation(cfg) -> dict[str, dict]:
    """Aggregate artifacts/analytics/plays → global/*.json; return each output document."""
    from ..theme.model import global_theme_model_path, load_theme_model

    plays_dir = cfg.analytics_dir / "plays"
    global_dir = cfg.analytics_dir / "global"
    global_dir.mkdir(parents=True, exist_ok=True)

    catalog = load_catalog(cfg.catalog_path)
    catalog_idx = _catalog_index(catalog)

    theme_model = None
    model_path = global_theme_model_path(cfg.analytics_dir)
    if model_path.is_file():
        try:
            theme_model = load_theme_model(model_path)
        except Exception:
            theme_model = None

    outputs = {
        "role_analysis.json": aggregate_role_analysis(plays_dir, catalog_idx),
        "network_compare.json": aggregate_network_compare(plays_dir, catalog_idx),
        "theme_patterns.json": aggregate_theme_patterns(
            plays_dir, catalog_idx, theme_model=theme_model
        ),
        "theme_quality.json": aggregate_theme_quality_report(plays_dir, catalog_idx),
        "narrative_templates.json": aggregate_narrative_templates(plays_dir, catalog_idx),
    }
    return outputs
