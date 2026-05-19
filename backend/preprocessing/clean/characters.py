from __future__ import annotations

from ..utils.ids import character_id, normalize_name
from .noise import is_valid_character_name
from .segment import COARSE_MAP, RawBlock, SegmentResult


def build_characters(
    segment: SegmentResult,
    blocks_json: list[dict],
) -> list[dict]:
    hints = segment.character_hints
    stats: dict[str, dict] = {}

    for block in segment.blocks:
        if block.speaker_name:
            name = normalize_name(block.speaker_name)
            if not is_valid_character_name(name):
                continue
            cid = character_id(name)
            st = stats.setdefault(
                cid,
                {
                    "character_id": cid,
                    "name": name,
                    "line_count": 0,
                    "first_appearance_block": block.block_index,
                },
            )
            st["line_count"] += 1
            st["first_appearance_block"] = min(
                st["first_appearance_block"], block.block_index
            )

    for name, hint in hints.items():
        nname = normalize_name(name)
        if not nname or not is_valid_character_name(nname):
            continue
        cid = character_id(nname)
        stats.setdefault(
            cid,
            {
                "character_id": cid,
                "name": nname,
                "line_count": 0,
                "first_appearance_block": 0,
            },
        )

    characters: list[dict] = []
    speaking = [s for s in stats.values() if s["line_count"] > 0]
    line_counts = sorted((s["line_count"] for s in speaking), reverse=True)
    threshold = line_counts[min(4, len(line_counts) - 1)] if line_counts else 1

    for cid, st in sorted(stats.items(), key=lambda x: -x[1]["line_count"]):
        name = st["name"]
        hint = hints.get(name, {})
        hangdang = hint.get("hangdang_labeled")
        has_lines = st["line_count"] > 0
        if not has_lines and not hangdang:
            continue
        if not has_lines and hangdang:
            pass
        elif has_lines and not is_valid_character_name(name):
            continue
        traits = dict(hint.get("traits") or {})
        cues = hint.get("performance_cues") or []
        if cues:
            traits["performance_cues"] = cues

        coarse = COARSE_MAP.get(hangdang) if hangdang else None

        characters.append(
            {
                "character_id": cid,
                "name": name,
                "aliases": [],
                "hangdang_labeled": hangdang,
                "hangdang_inferred": None,
                "hangdang_coarse": coarse,
                "traits": traits if traits else None,
                "line_count": st["line_count"],
                "first_appearance_block": st["first_appearance_block"],
                "is_main": st["line_count"] >= max(threshold, 1),
            }
        )

    if not characters and blocks_json:
        characters.append(
            {
                "character_id": "c_未知",
                "name": "未知",
                "aliases": [],
                "hangdang_labeled": None,
                "hangdang_inferred": None,
                "hangdang_coarse": None,
                "line_count": 0,
                "first_appearance_block": 0,
                "is_main": True,
            }
        )

    return characters


def attach_speakers_to_blocks(
    segment: SegmentResult,
    characters: list[dict],
) -> list[dict]:
    valid_ids = {c["character_id"] for c in characters}
    name_to_id = {c["name"]: c["character_id"] for c in characters}

    out: list[dict] = []
    for raw in segment.blocks:
        speaker_id = None
        speaker_name_raw = None
        if raw.speaker_name:
            nname = normalize_name(raw.speaker_name)
            if not is_valid_character_name(nname):
                nname = ""
            speaker_name_raw = raw.speaker_name
            speaker_id = name_to_id.get(nname) if nname else None
            if not speaker_id:
                speaker_id = character_id(nname)
                if speaker_id not in valid_ids:
                    speaker_id = None

        perf = raw.performance_tags or []
        if raw.type == "aria" and "唱" not in perf:
            perf = ["唱"] + perf

        item = {
            "block_id": f"b_{raw.block_index}",
            "block_index": raw.block_index,
            "scene_id": f"s_{raw.scene_index}" if raw.scene_index else None,
            "type": raw.type,
            "speaker_id": speaker_id,
            "text": raw.text,
            "performance_tags": perf,
            "char_len": len(raw.text),
        }
        if speaker_name_raw:
            item["speaker_name_raw"] = speaker_name_raw
        if raw.performance_cues_raw:
            item["performance_cues_raw"] = list(raw.performance_cues_raw)
        if raw.page_no:
            item["page_no"] = raw.page_no
        out.append(item)
    return out
