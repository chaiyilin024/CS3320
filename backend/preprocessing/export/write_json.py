from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..utils.paths import get_project_root
from ..utils.schema_validate import validate_catalog, validate_play


def build_catalog_entry(play: dict) -> dict:
    meta = play["metadata"]
    entry: dict[str, Any] = {
        "script_id": play["script_id"],
        "title": play["title"],
        "collection_id": play["collection_id"],
        "collection_name": play["collection_name"],
        "source_pdf": meta["source_pdf"],
        "page_count": meta.get("page_count", 0),
        "char_count": meta.get("char_count", 0),
        "character_count": len(play.get("characters") or []),
        "block_count": len(play.get("blocks") or []),
        "scene_count": len(play.get("scenes") or []),
        "parse_quality": meta.get("parse_quality", 0),
        "output_path": f"plays/{play['script_id']}.json",
    }
    if play.get("tags"):
        entry["tags"] = play["tags"]
    return entry


class PlayWriter:
    def __init__(self, output_dir: Path, *, validate: bool = True):
        self.output_dir = output_dir
        self.plays_dir = output_dir / "plays"
        self.plays_dir.mkdir(parents=True, exist_ok=True)
        self.validate = validate
        self.root = get_project_root()
        self.entries: list[dict] = []
        self.failed: list[dict] = []

    def write_play(self, play: dict) -> Path:
        # Merge blocks: append type=unknown with speaker_id=null onto the previous block
        blocks = play.get("blocks", [])
        if blocks:
            # Build a new blocks list, skipping blocks slated for merge
            new_blocks = []
            for block in blocks:
                # Check whether this block should merge into the previous one
                if block.get("type") == "unknown" and block.get("speaker_id") is None:
                    if new_blocks:
                        # Append this block's text to the previous block
                        new_blocks[-1]["text"] = (new_blocks[-1].get("text", "") + block.get("text", "")).strip()
                    # else discard (no previous block to merge into)
                else:
                    new_blocks.append(block)
            play["blocks"] = new_blocks

        if self.validate:
            errors = validate_play(play, self.root)
            if errors:
                self.failed.append(
                    {
                        "script_id": play.get("script_id"),
                        "reason": "schema_validation",
                        "errors": errors[:5],
                    }
                )

        path = self.plays_dir / f"{play['script_id']}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(play, f, ensure_ascii=False, indent=2)
        self.entries.append(build_catalog_entry(play))
        return path

    def write_catalog(
        self,
        *,
        schema_version: str = "1.0",
        parse_version: str = "1.0",
        pipeline_meta: dict | None = None,
    ) -> Path:
        catalog = {
            "version": schema_version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline": {
                "parse_version": parse_version,
                **(pipeline_meta or {}),
                "play_count_included": len(self.entries),
            },
            "plays": sorted(self.entries, key=lambda x: x["script_id"]),
        }
        if self.validate:
            errors = validate_catalog(catalog, self.root)
            if errors:
                raise ValueError(f"catalog validation failed: {errors[:3]}")

        path = self.output_dir / "catalog.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)

        if self.failed:
            failed_path = self.output_dir / "failed.json"
            with failed_path.open("w", encoding="utf-8") as f:
                json.dump(self.failed, f, ensure_ascii=False, indent=2)

        return path