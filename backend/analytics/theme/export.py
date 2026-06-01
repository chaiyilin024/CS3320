from __future__ import annotations

from collections import defaultdict

from .model import ThemeModel, is_metadata_topic

# 权重低于此值的 topic 视为噪音
NOISE_WEIGHT_THRESHOLD = 0.03
MAX_KEYWORDS = 15
MAX_REP_BLOCKS_PER_TOPIC = 2


def build_play_themes(play: dict, model: ThemeModel) -> dict:
    script_id = play["script_id"]
    title = play.get("title", "")
    composition = model.play_composition(play)
    raw_topics = []
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
        raw_topics.append(item)

    # 过滤低权重与文献噪声 topic，保留至少 2 个以满足 schema
    survivors = [
        t
        for t in raw_topics
        if composition[t["topic_id"]] >= NOISE_WEIGHT_THRESHOLD
        and not is_metadata_topic(t.get("keywords") or [])
        and "京剧" not in (t.get("label") or "")
    ]
    if len(survivors) < 2:
        candidates = [
            t
            for t in raw_topics
            if not is_metadata_topic(t.get("keywords") or [])
            and "京剧" not in (t.get("label") or "")
        ]
        survivors = sorted(
            candidates or raw_topics, key=lambda t: -composition[t["topic_id"]]
        )[: max(2, len(candidates))]
    kept_ids = {t["topic_id"] for t in survivors}

    # 重归一化保留下来的 topic 权重，保证 topic_composition 和 ≈ 1
    kept_comp = [composition[t["topic_id"]] for t in survivors]
    s = sum(kept_comp) or 1.0
    comp = [round(w / s, 4) for w in kept_comp]
    for t, w in zip(survivors, comp):
        t["weight"] = w

    # 同一 label 的 NMF 子主题合并为一条（权重相加、关键词按权重去重取 Top）
    merged_topics, old_to_new = _merge_topics_by_label(survivors)
    comp = [t["weight"] for t in merged_topics]
    # 修正四舍五入误差，保证 composition 之和为 1
    drift = 1.0 - sum(comp)
    if merged_topics and abs(drift) > 1e-6:
        merged_topics[0]["weight"] = round(merged_topics[0]["weight"] + drift, 4)
        comp[0] = merged_topics[0]["weight"]

    reps = _representative_blocks(
        play, model, kept_ids, old_to_new=old_to_new
    )
    return {
        "script_id": script_id,
        "title": title,
        "model": {
            "method": model.method,
            "num_topics_global": model.num_topics,
            "trained_at": model.trained_at,
        },
        "topics": merged_topics,
        "topic_composition": comp,
        "representative_blocks": reps,
    }


def _merge_topics_by_label(
    topics: list[dict],
) -> tuple[list[dict], dict[int, int]]:
    """按 label 合并 topic；返回 (合并后列表, 原 topic_id → 新 topic_id)。"""
    if not topics:
        return [], {}

    groups: dict[str, list[dict]] = defaultdict(list)
    for t in topics:
        groups[t["label"]].append(t)

    merged: list[dict] = []
    old_to_new: dict[int, int] = {}
    for new_id, (_label, group) in enumerate(
        sorted(groups.items(), key=lambda x: -sum(t["weight"] for t in x[1]))
    ):
        total_w = sum(t["weight"] for t in group)
        kw_scores: dict[str, float] = {}
        for t in group:
            kws = t.get("keywords") or []
            weights = t.get("keyword_weights") or [1.0] * len(kws)
            for kw, w in zip(kws, weights):
                kw_scores[kw] = max(kw_scores.get(kw, 0.0), float(w))

        ranked = sorted(kw_scores.items(), key=lambda x: -x[1])[:MAX_KEYWORDS]
        keywords = [k for k, _ in ranked]
        if not keywords:
            keywords = [group[0].get("label", "主题")]

        item: dict = {
            "topic_id": new_id,
            "label": _label,
            "weight": round(total_w, 4),
            "keywords": keywords,
            "keyword_weights": [round(s, 4) for _, s in ranked],
        }
        merged.append(item)
        for t in group:
            old_to_new[t["topic_id"]] = new_id

    return merged, old_to_new


def _representative_blocks(
    play: dict,
    model: ThemeModel,
    kept_ids: set[int] | None = None,
    *,
    old_to_new: dict[int, int] | None = None,
    per_topic: int = MAX_REP_BLOCKS_PER_TOPIC,
) -> list[dict]:
    rows = model.transform_blocks(play)
    if not rows:
        return []
    blocks = play.get("blocks") or []
    block_by_id = {b["block_id"]: b for b in blocks}
    char_name = {c["character_id"]: c.get("name", "") for c in play.get("characters") or []}

    by_topic: dict[int, list[tuple[float, str, int, str]]] = {}
    for block_id, block_index, text, vec in rows:
        raw_tid = max(range(len(vec)), key=lambda i: vec[i])
        if kept_ids is not None and raw_tid not in kept_ids:
            continue
        score = vec[raw_tid]
        tid = old_to_new.get(raw_tid, raw_tid) if old_to_new else raw_tid
        by_topic.setdefault(tid, []).append((score, block_id, block_index, text))

    reps = []
    for tid, items in sorted(by_topic.items()):
        for score, block_id, block_index, text in sorted(items, reverse=True)[:per_topic]:
            block = block_by_id.get(block_id) or {}
            speaker_id = block.get("speaker_id")
            context = _context_snippet(blocks, block_index, window=1)
            entry: dict = {
                "topic_id": tid,
                "block_id": block_id,
                "block_index": block_index,
                "text_snippet": text[:200],
                "context_snippet": context[:800],
                "speaker_id": speaker_id,
                "speaker_name": char_name.get(speaker_id, "") if speaker_id else "",
                "score": round(float(score), 4),
            }
            reps.append(entry)
    return reps


def _context_snippet(blocks: list[dict], center_index: int, window: int = 1) -> str:
    """取 center_index ±window 的文本块拼接，去掉舞台说明纯标记。"""
    if not blocks:
        return ""
    pieces: list[str] = []
    for b in blocks:
        bi = b.get("block_index")
        if bi is None:
            continue
        if center_index - window <= bi <= center_index + window:
            t = (b.get("text") or "").strip()
            if not t:
                continue
            sp = b.get("speaker_id") or ""
            prefix = "" if bi != center_index else "» "
            pieces.append(f"{prefix}{t}")
    return "  /  ".join(pieces)
