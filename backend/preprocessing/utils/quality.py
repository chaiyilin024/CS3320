from __future__ import annotations


def compute_parse_quality(
    blocks: list[dict],
    char_count: int,
    page_count: int,
    warnings: list[str],
) -> float:
    if not blocks:
        return 0.0

    total = len(blocks)
    typed = sum(1 for b in blocks if b.get("type") != "unknown")
    dialogue = sum(1 for b in blocks if b.get("type") == "dialogue")
    with_speaker = sum(
        1 for b in blocks if b.get("type") == "dialogue" and b.get("speaker_id")
    )

    text_score = min(1.0, char_count / max(page_count * 80, 400))
    type_score = typed / total
    dialogue_score = (with_speaker / dialogue) if dialogue else 0.3

    score = 0.35 * text_score + 0.35 * type_score + 0.30 * dialogue_score
    if warnings:
        score *= max(0.5, 1.0 - 0.05 * len(warnings))
    return round(min(1.0, max(0.0, score)), 3)
