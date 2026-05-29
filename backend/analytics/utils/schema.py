from __future__ import annotations

from pathlib import Path

from backend.preprocessing.utils.schema_validate import load_validator


def validate_analytics(doc: dict, schema_rel: str, root: Path) -> list[str]:
    schema_path = root / "schemas" / "analytics" / schema_rel
    if not schema_path.exists():
        return [f"schema not found: {schema_rel}"]
    validator = load_validator(schema_path, root)
    return [e.message for e in validator.iter_errors(doc)]
