"""Theme analysis quality evaluation — per-play and corpus-wide."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .model import _load_label_rules, _score_label, is_metadata_topic

# Labels treated as "unrecognized" (frontend often shows as unknown/other)
FALLBACK_LABELS = frozenset({"其他情节", "未知", "其他", "通用主题"})

# Common function words / boilerplate in keywords that reduce interpretability
WEAK_KEYWORDS = frozenset({
    "正是", "只见", "怎么", "为何", "为何事", "为何来", "为何去",
    "如此", "这般", "那个", "这个", "什么", "不是", "就是", "也是",
    "已经", "还是", "便是", "便是了", "罢了", "而已", "怎的",
    "众人", "大家", "你们", "我们", "他们", "自己", "今日", "明日",
    "左右", "罢了", "且说", "话说", "原来", "不想", "却原来",
    "无有", "不得", "不可", "不能", "不知", "不知怎的",
})

LOW_QUALITY_THRESHOLD = 0.55


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_fallback_label(label: str) -> bool:
    s = (label or "").strip()
    if not s or s in FALLBACK_LABELS:
        return True
    if s.startswith("主题") and s[2:].isdigit():
        return True
    if len(s) <= 1:
        return True
    return False


def _keyword_signal(keywords: list[str]) -> tuple[float, list[str]]:
    """Return (0–1 signal strength, list of issues)."""
    kws = [k.strip() for k in (keywords or []) if k and k.strip()]
    if not kws:
        return 0.0, ["无有效关键词"]

    issues: list[str] = []
    top = kws[:8]
    weak = sum(1 for w in top if w in WEAK_KEYWORDS or len(w) < 2)
    meta = sum(1 for w in top if is_metadata_topic([w]))
    distinct = len(set(top))
    dup_ratio = 1.0 - distinct / len(top) if top else 0.0

    if weak >= 3:
        issues.append(f"Top 关键词含 {weak} 个低信息词")
    if meta >= 2:
        issues.append("关键词含文献/页眉噪声")
    if dup_ratio > 0.3:
        issues.append("关键词重复较多")

    clean = len(top) - weak - meta
    signal = max(0.0, min(1.0, clean / max(len(top), 1) - dup_ratio * 0.2))
    return round(signal, 3), issues


def _label_match_tier(keywords: list[str], assigned_label: str) -> tuple[str, float, list[str]]:
    """Score label hit strength against theme.json rules."""
    rules, threshold, min_hits, fb_threshold = _load_label_rules()
    word_set = frozenset(k for k in (keywords or []) if k)
    if not rules or not word_set:
        return "fallback", 0.0, ["无规则或无关键词"]

    scored: list[tuple[str, float, list[str]]] = []
    for rule in rules:
        score = _score_label(rule, word_set)
        hits = [k for k in rule.keywords if k in word_set]
        scored.append((rule.label, score, hits))
    scored.sort(key=lambda x: -x[1])
    best_label, best_score, best_hits = scored[0]

    issues: list[str] = []
    if _is_fallback_label(assigned_label):
        if best_score >= threshold and (
            len(best_hits) >= min_hits or best_score >= 8.0
        ):
            issues.append(f"标签为未识别，但关键词更接近「{best_label}」")
        return "fallback", round(best_score, 3), issues

    strong = best_score >= threshold and (
        len(best_hits) >= min_hits or best_score >= 8.0
    )
    weak = best_score >= fb_threshold
    if assigned_label == best_label:
        if strong:
            return "strong", round(best_score, 3), issues
        if weak:
            return "weak", round(best_score, 3), issues
        issues.append("标签命中规则较弱")
        return "weak", round(best_score, 3), issues

    if strong and assigned_label != best_label:
        issues.append(f"标签「{assigned_label}」与规则最佳「{best_label}」不一致")
    elif not weak:
        issues.append("关键词与 theme.json 规则匹配度低")
    return ("weak" if weak else "fallback"), round(best_score, 3), issues


def assess_topic(topic: dict) -> dict:
    """Evaluate a single topic entry (topic object in themes.json)."""
    label = str(topic.get("label") or "")
    keywords = list(topic.get("keywords") or [])
    weight = float(topic.get("weight") or 0.0)
    kw_signal, kw_issues = _keyword_signal(keywords)
    tier, label_score, label_issues = _label_match_tier(keywords, label)

    issues = list(dict.fromkeys(kw_issues + label_issues))
    if weight < 0.05:
        issues.append("主题权重过低，可能是噪音")
    if is_metadata_topic(keywords):
        tier = "noise"
        issues.append("疑似文献/页眉噪声主题")

    return {
        "topic_id": int(topic.get("topic_id", 0)),
        "label": label,
        "tier": tier,
        "label_score": label_score,
        "keyword_signal": kw_signal,
        "weight": round(weight, 4),
        "issues": issues,
    }


def assess_play_themes(themes_doc: dict) -> dict:
    """Evaluate a single-play themes.json; return the quality block."""
    topics = themes_doc.get("topics") or []
    assessments = [assess_topic(t) for t in topics]
    if not assessments:
        return {
            "score": 0.0,
            "labeled_weight": 0.0,
            "fallback_weight": 0.0,
            "tier_counts": {},
            "topic_assessments": [],
            "issues": ["无主题输出"],
        }

    total_w = sum(a["weight"] for a in assessments) or 1.0
    fallback_w = sum(
        a["weight"] for a in assessments if a["tier"] in ("fallback", "noise")
    )
    labeled_w = 1.0 - fallback_w / total_w
    kw_avg = sum(a["keyword_signal"] for a in assessments) / len(assessments)
    score = round(0.65 * labeled_w + 0.35 * kw_avg, 3)

    tier_counts = Counter(a["tier"] for a in assessments)
    play_issues: list[str] = []
    if fallback_w / total_w >= 0.4:
        play_issues.append(
            f"{fallback_w / total_w * 100:.0f}% 主题为未识别（其他情节/未知）"
        )
    if kw_avg < 0.45:
        play_issues.append("关键词整体可解释性偏低")
    if score < LOW_QUALITY_THRESHOLD:
        play_issues.append("综合质量偏低，建议检查文本分块或扩展 theme.json 规则")

    method = (themes_doc.get("model") or {}).get("method", "")
    return {
        "score": score,
        "labeled_weight": round(labeled_w, 4),
        "fallback_weight": round(fallback_w / total_w, 4),
        "keyword_signal_avg": round(kw_avg, 3),
        "tier_counts": dict(tier_counts),
        "method": method,
        "topic_assessments": assessments,
        "issues": play_issues,
    }


def attach_quality(themes_doc: dict) -> dict:
    """Attach quality field to themes document (mutates in place and returns it)."""
    themes_doc["quality"] = assess_play_themes(themes_doc)
    return themes_doc


def aggregate_theme_quality(
    plays_dir: Path,
    catalog_idx: dict[str, dict],
) -> dict:
    """Aggregate corpus-wide theme quality → global/theme_quality.json."""
    tier_totals: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    label_weight: Counter[str] = Counter()
    fallback_kw: Counter[str] = Counter()
    play_rows: list[dict] = []
    scores: list[float] = []

    for play_dir in sorted(plays_dir.iterdir()):
        if not play_dir.is_dir():
            continue
        path = play_dir / "themes.json"
        if not path.is_file():
            continue
        try:
            import json

            themes = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        sid = themes.get("script_id") or play_dir.name
        meta = catalog_idx.get(sid, {})
        quality = themes.get("quality") or assess_play_themes(themes)
        score = float(quality.get("score") or 0.0)
        scores.append(score)

        for a in quality.get("topic_assessments") or []:
            tier_totals[a.get("tier", "fallback")] += 1
            lbl = a.get("label") or "?"
            label_counts[lbl] += 1
            label_weight[lbl] += float(a.get("weight") or 0.0)
            if a.get("tier") in ("fallback", "noise"):
                for kw in (themes.get("topics") or []):
                    if int(kw.get("topic_id", -1)) == int(a.get("topic_id", -2)):
                        for w in (kw.get("keywords") or [])[:6]:
                            fallback_kw[w] += 1
                        break

        play_rows.append({
            "script_id": sid,
            "title": themes.get("title") or meta.get("title") or "",
            "genre": (meta.get("tags") or {}).get("genre_inferred") or "未知",
            "score": score,
            "labeled_weight": quality.get("labeled_weight", 0.0),
            "fallback_weight": quality.get("fallback_weight", 0.0),
            "tier_counts": quality.get("tier_counts") or {},
            "issues": quality.get("issues") or [],
        })

    n = len(play_rows)
    low = [r for r in play_rows if r["score"] < LOW_QUALITY_THRESHOLD]
    low.sort(key=lambda x: (x["score"], -x["fallback_weight"]))

    label_distribution = [
        {
            "label": lbl,
            "topic_count": label_counts[lbl],
            "weight_sum": round(label_weight[lbl], 3),
        }
        for lbl, _ in label_counts.most_common(30)
    ]

    return {
        "version": "1.0",
        "generated_at": _utc_now(),
        "summary": {
            "play_count": n,
            "avg_score": round(sum(scores) / n, 3) if n else 0.0,
            "low_quality_count": len(low),
            "low_quality_threshold": LOW_QUALITY_THRESHOLD,
            "fallback_label_share": round(
                label_counts.get("其他情节", 0) / max(sum(label_counts.values()), 1),
                4,
            ),
            "tier_totals": dict(tier_totals),
        },
        "label_distribution": label_distribution,
        "fallback_keywords": [
            {"keyword": w, "count": c}
            for w, c in fallback_kw.most_common(25)
        ],
        "low_quality_plays": low[:50],
        "plays": play_rows,
    }


def backfill_play_quality(path: Path) -> bool:
    """Write quality field into an existing themes.json."""
    import json

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    attach_quality(doc)
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return True
