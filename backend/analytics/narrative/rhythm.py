from __future__ import annotations

import re

from ..theme.model import ThemeModel

STAGES = ["铺垫", "发展", "冲突", "高潮", "结局"]
PERF_KEYS = ("唱", "念", "做", "打", "unknown")

# 简易情感词典
POS_WORDS = frozenset("喜 贺 笑 欢 成功 胜 安 乐 好 喜".split())
NEG_WORDS = frozenset("怒 恨 杀 死 哭 悲 怕 惊 吓 危 险 败".split())


def analyze_play_narrative(
    play: dict,
    window: int = 20,
    theme_model: ThemeModel | None = None,
) -> dict:
    script_id = play["script_id"]
    title = play.get("title", "")
    blocks = play.get("blocks") or []
    if not blocks:
        return _empty_narrative(script_id, title)

    perf_dist = {k: 0 for k in PERF_KEYS}
    for b in blocks:
        tags = b.get("performance_tags") or []
        if not tags:
            perf_dist["unknown"] += 1
            continue
        for t in tags:
            if t in perf_dist:
                perf_dist[t] += 1
            else:
                perf_dist["unknown"] += 1

    rhythm_series = _rhythm_series(blocks, window)
    plot_stages = _plot_stages(blocks, rhythm_series)
    perf_by_stage = _perf_by_stage(blocks, plot_stages)
    annotations = _block_annotations(play, plot_stages, rhythm_series, theme_model)

    return {
        "script_id": script_id,
        "title": title,
        "plot_stages": plot_stages,
        "rhythm_series": rhythm_series,
        "performance_mark_distribution": perf_dist,
        "performance_by_stage": perf_by_stage,
        "block_annotations": annotations,
    }


def _rhythm_series(blocks: list[dict], window: int) -> list[dict]:
    series = []
    n = len(blocks)
    half = max(1, window // 2)
    for i, b in enumerate(blocks):
        start = max(0, i - half)
        end = min(n, i + half + 1)
        win = blocks[start:end]
        dialogue = sum(1 for x in win if x.get("type") == "dialogue")
        aria = sum(
            1
            for x in win
            if x.get("type") == "aria"
            or "唱" in (x.get("performance_tags") or [])
        )
        action = sum(
            1
            for x in win
            if x.get("type") in ("action", "combat", "stage_direction")
            or any(t in ("做", "打") for t in (x.get("performance_tags") or []))
        )
        wlen = len(win) or 1
        text = " ".join(x.get("text", "") for x in win)
        emotion = _emotion_score(text)
        tension = _tension_score(text, action / wlen)
        series.append(
            {
                "block_index": b["block_index"],
                "window": window,
                "dialogue_density": round(dialogue / wlen, 4),
                "aria_ratio": round(aria / wlen, 4),
                "action_intensity": round(action / wlen, 4),
                "emotion_score": round(emotion, 4),
                "tension_score": round(tension, 4),
            }
        )
    return series


def _emotion_score(text: str) -> float:
    pos = sum(1 for w in POS_WORDS if w in text)
    neg = sum(1 for w in NEG_WORDS if w in text)
    if pos + neg == 0:
        return 0.5
    return min(1.0, max(0.0, 0.5 + (pos - neg) / (pos + neg + 2) * 0.4))


def _tension_score(text: str, action_ratio: float) -> float:
    excl = text.count("！") + text.count("!") + text.count("？")
    bang = min(1.0, excl / 5)
    return min(1.0, 0.35 * action_ratio + 0.35 * bang + 0.3 * _emotion_score(text))


def _plot_stages(blocks: list[dict], rhythm: list[dict]) -> list[dict]:
    n = len(blocks)
    if n == 0:
        return [{"stage": "其他", "block_range": [0, 0], "label": "全剧"}]
    scores = [p.get("tension_score", 0.5) for p in rhythm]
    boundaries = _stage_boundaries(n, len(STAGES))
    stages_out = []
    for i, stage_name in enumerate(STAGES):
        if i >= len(boundaries) - 1:
            break
        start, end = boundaries[i], boundaries[i + 1] - 1
        if start > end:
            continue
        seg_scores = scores[start : end + 1]
        avg_t = sum(seg_scores) / len(seg_scores) if seg_scores else 0.5
        summary = _stage_summary(blocks[start : end + 1])
        stages_out.append(
            {
                "stage": stage_name,
                "label": _stage_label(stage_name, avg_t),
                "block_range": [blocks[start]["block_index"], blocks[end]["block_index"]],
                "summary": summary,
            }
        )
    if not stages_out:
        stages_out.append(
            {
                "stage": "其他",
                "block_range": [blocks[0]["block_index"], blocks[-1]["block_index"]],
                "label": "全剧",
            }
        )
    return stages_out


def _stage_boundaries(n: int, k: int) -> list[int]:
    """将 n 块均分为 k 段的起始下标。"""
    return [round(i * n / k) for i in range(k + 1)]


def _stage_label(stage: str, tension: float) -> str:
    extras = {
        "铺垫": "引入",
        "发展": "推进",
        "冲突": "对峙",
        "高潮": "激战",
        "结局": "收束",
    }
    base = extras.get(stage, stage)
    if tension > 0.65:
        return f"{base}·高张力"
    if tension < 0.4:
        return f"{base}·平缓"
    return base


def _stage_summary(segment: list[dict]) -> str:
    words: list[str] = []
    for b in segment[:40]:
        t = b.get("text", "")
        words.extend(re.findall(r"[\u4e00-\u9fff]{2,4}", t))
    if not words:
        return ""
    from collections import Counter

    common = Counter(words).most_common(5)
    return "、".join(w for w, _ in common)


def _perf_by_stage(blocks: list[dict], stages: list[dict]) -> list[dict]:
    index_map = {b["block_index"]: b for b in blocks}
    out = []
    for st in stages:
        lo, hi = st["block_range"]
        dist = {k: 0 for k in PERF_KEYS}
        for b in blocks:
            if lo <= b["block_index"] <= hi:
                tags = b.get("performance_tags") or ["unknown"]
                for t in tags:
                    dist[t if t in dist else "unknown"] += 1
        out.append({"stage": st["stage"], "distribution": dist})
    return out


def _block_annotations(
    play: dict,
    stages: list[dict],
    rhythm: list[dict],
    theme_model: ThemeModel | None,
) -> list[dict]:
    blocks = play.get("blocks") or []
    stage_by_index = {}
    for st in stages:
        lo, hi = st["block_range"]
        for bi in range(lo, hi + 1):
            stage_by_index[bi] = st["stage"]
    emotion_by_index = {p["block_index"]: p.get("emotion_score", 0.5) for p in rhythm}
    topic_by_block: dict[str, int] = {}
    if theme_model:
        for block_id, _bidx, _text, vec in theme_model.transform_blocks(play):
            topic_by_block[block_id] = max(range(len(vec)), key=lambda i: vec[i])

    ann = []
    for b in blocks[:500]:
        item = {
            "block_index": b["block_index"],
            "block_id": b["block_id"],
            "stage": stage_by_index.get(b["block_index"], "其他"),
            "emotion_score": emotion_by_index.get(b["block_index"], 0.5),
        }
        if b["block_id"] in topic_by_block:
            item["dominant_topic_id"] = topic_by_block[b["block_id"]]
        ann.append(item)
    return ann


def _empty_narrative(script_id: str, title: str) -> dict:
    return {
        "script_id": script_id,
        "title": title,
        "plot_stages": [{"stage": "其他", "block_range": [0, 0], "label": "全剧"}],
        "rhythm_series": [
            {
                "block_index": 0,
                "window": 20,
                "dialogue_density": 0,
                "aria_ratio": 0,
                "action_intensity": 0,
                "emotion_score": 0.5,
            }
        ],
        "performance_mark_distribution": {k: 0 for k in PERF_KEYS},
    }
