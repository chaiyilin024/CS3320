from __future__ import annotations

from collections import defaultdict


def build_cooccurrence_edges(
    blocks: list[dict],
    scenes: list[dict],
) -> list[dict]:
    dialogue_counts: dict[tuple[str, str], int] = defaultdict(int)
    same_scene_counts: dict[tuple[str, str], int] = defaultdict(int)

    prev_speaker: str | None = None
    for block in blocks:
        sp = block.get("speaker_id")
        if block.get("type") == "dialogue" and sp:
            if prev_speaker and prev_speaker != sp:
                pair = _pair(prev_speaker, sp)
                dialogue_counts[pair] += 1
            prev_speaker = sp
        elif block.get("type") not in ("dialogue", "recitation", "aria"):
            prev_speaker = None

    for scene in scenes:
        chars = scene.get("character_ids") or []
        for i, a in enumerate(chars):
            for b in chars[i + 1 :]:
                pair = _pair(a, b)
                same_scene_counts[pair] += 1

    all_pairs = set(dialogue_counts) | set(same_scene_counts)
    edges: list[dict] = []
    for pair in sorted(all_pairs):
        d = dialogue_counts.get(pair, 0)
        s = same_scene_counts.get(pair, 0)
        weight = d * 2 + s
        if weight <= 0:
            continue
        types: list[str] = []
        if d:
            types.append("对话")
        if s:
            types.append("同场")
        edges.append(
            {
                "source_id": pair[0],
                "target_id": pair[1],
                "weight": float(weight),
                "relation_types": types,
                "dialogue_count": d,
                "same_scene_count": s,
            }
        )
    return edges


def _pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)
