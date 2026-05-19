from __future__ import annotations

import json
from pathlib import Path

try:
    from jsonschema import Draft7Validator, RefResolver
except ImportError:
    Draft7Validator = None  # type: ignore
    RefResolver = None  # type: ignore


def _build_schema_store(schemas_dir: Path) -> dict:
    """加载 schemas/ 下所有文件，供 RefResolver 解析 $ref（含 ../common/...）。"""
    store: dict = {}
    for path in sorted(schemas_dir.rglob("*.schema.json")):
        with path.open(encoding="utf-8") as f:
            content = json.load(f)
        rel = path.relative_to(schemas_dir).as_posix()
        file_uri = path.resolve().as_uri()
        store[file_uri] = content
        store[rel] = content
        schema_id = content.get("$id")
        if schema_id:
            store[schema_id] = content
    return store


def load_validator(schema_path: Path, root: Path | None = None):
    if Draft7Validator is None or RefResolver is None:
        raise ImportError("jsonschema 未安装，请 pip install jsonschema 或 --no-validate")

    root = root or schema_path.resolve().parents[2]
    schemas_dir = root / "schemas"
    store = _build_schema_store(schemas_dir)

    with schema_path.open(encoding="utf-8") as f:
        schema = json.load(f)

    base_uri = schema_path.resolve().parent.as_uri() + "/"
    resolver = RefResolver(base_uri=base_uri, referrer=schema, store=store)
    return Draft7Validator(schema, resolver=resolver)


def validate_play(play: dict, root: Path) -> list[str]:
    if Draft7Validator is None:
        return []
    schema_path = root / "schemas" / "cleaned" / "play.schema.json"
    validator = load_validator(schema_path, root)
    return [e.message for e in validator.iter_errors(play)]


def validate_catalog(catalog: dict, root: Path) -> list[str]:
    if Draft7Validator is None:
        return []
    schema_path = root / "schemas" / "cleaned" / "catalog.schema.json"
    validator = load_validator(schema_path, root)
    return [e.message for e in validator.iter_errors(catalog)]
