from __future__ import annotations

from .segment import RawBlock


def build_scenes(blocks: list[dict], raw_blocks: list[RawBlock]) -> list[dict]:
    scenes: list[dict] = []
    scene_indices: dict[int, dict] = {}

    for raw in raw_blocks:
        if raw.type == "scene_heading" and raw.scene_index:
            si = raw.scene_index
            if si not in scene_indices:
                scene_indices[si] = {
                    "scene_id": f"s_{si}",
                    "scene_index": si,
                    "title": raw.text,
                    "block_start": raw.block_index,
                    "block_end": raw.block_index,
                    "character_ids": set(),
                }
            else:
                scene_indices[si]["title"] = raw.text
                scene_indices[si]["block_end"] = raw.block_index

    for block in blocks:
        sid = block.get("scene_id")
        if not sid:
            continue
        try:
            si = int(sid.split("_")[1])
        except (IndexError, ValueError):
            continue
        if si not in scene_indices:
            scene_indices[si] = {
                "scene_id": f"s_{si}",
                "scene_index": si,
                "title": f"第{si}场",
                "block_start": block["block_index"],
                "block_end": block["block_index"],
                "character_ids": set(),
            }
        scene_indices[si]["block_start"] = min(
            scene_indices[si]["block_start"], block["block_index"]
        )
        scene_indices[si]["block_end"] = max(
            scene_indices[si]["block_end"], block["block_index"]
        )
        sp = block.get("speaker_id")
        if sp:
            scene_indices[si]["character_ids"].add(sp)

    for si in sorted(scene_indices):
        s = scene_indices[si]
        scenes.append(
            {
                "scene_id": s["scene_id"],
                "scene_index": s["scene_index"],
                "title": s["title"],
                "block_range": [s["block_start"], s["block_end"]],
                "character_ids": sorted(s["character_ids"]),
            }
        )

    if not scenes and blocks:
        scenes.append(
            {
                "scene_id": "s_1",
                "scene_index": 1,
                "title": "全剧",
                "block_range": [0, blocks[-1]["block_index"]],
                "character_ids": sorted(
                    {b["speaker_id"] for b in blocks if b.get("speaker_id")}
                ),
            }
        )

    return scenes
