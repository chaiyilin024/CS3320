from __future__ import annotations

from .model import ThemeModel

# 权重低于此值的 topic 视为噪音
NOISE_WEIGHT_THRESHOLD = 0.03


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

    # 过滤噪音 topic，但保留至少 K=2 以满足 schema minItems
    survivors = [t for t in raw_topics if composition[t["topic_id"]] >= NOISE_WEIGHT_THRESHOLD]
    if len(survivors) < 2:
        survivors = sorted(raw_topics, key=lambda t: -composition[t["topic_id"]])[:2]
    kept_ids = {t["topic_id"] for t in survivors}

    # 重归一化保留下来的 topic 权重，保证 topic_composition 和 ≈ 1
    kept_comp = [composition[t["topic_id"]] for t in survivors]
    s = sum(kept_comp) or 1.0
    comp = [round(w / s, 4) for w in kept_comp]
    for t, w in zip(survivors, comp):
        t["weight"] = w

    reps = _representative_blocks(play, model, kept_ids)
    return {
        "script_id": script_id,
        "title": title,
        "model": {
            "method": model.method,
            "num_topics_global": model.num_topics,
            "trained_at": model.trained_at,
        },
        "topics": survivors,
        "topic_composition": comp,
        "representative_blocks": reps,
    }


def _representative_blocks(
    play: dict, model: ThemeModel, kept_ids: set[int] | None = None, per_topic: int = 2
) -> list[dict]:
    rows = model.transform_blocks(play)
    if not rows:
        return []
    blocks = play.get("blocks") or []
    block_by_id = {b["block_id"]: b for b in blocks}
    char_name = {c["character_id"]: c.get("name", "") for c in play.get("characters") or []}

    by_topic: dict[int, list[tuple[float, str, int, str]]] = {}
    for block_id, block_index, text, vec in rows:
        tid = max(range(len(vec)), key=lambda i: vec[i])
        if kept_ids is not None and tid not in kept_ids:
            continue
        score = vec[tid]
        by_topic.setdefault(tid, []).append((score, block_id, block_index, text))

    reps = []
    for tid, items in by_topic.items():
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
