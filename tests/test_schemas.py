"""Verify JSON Schema files can be loaded by jsonschema."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"

pytest.importorskip("jsonschema")
from jsonschema import Draft7Validator  # noqa: E402
from jsonschema.exceptions import SchemaError  # noqa: E402
from jsonschema.validators import validator_for  # noqa: E402


def _iter_schema_files():
    for path in sorted(SCHEMAS.rglob("*.schema.json")):
        yield path


@pytest.mark.parametrize("schema_path", list(_iter_schema_files()), ids=lambda p: p.name)
def test_schema_is_valid_draft7(schema_path: Path):
    with schema_path.open(encoding="utf-8") as f:
        schema = json.load(f)
    cls = validator_for(schema)
    assert cls is Draft7Validator, f"{schema_path} 应使用 draft-07"
    cls.check_schema(schema)


def test_play_schema_references_resolve():
    """play.schema.json should resolve sub-schema references."""
    from backend.preprocessing.utils.schema_validate import load_validator

    play_path = SCHEMAS / "cleaned" / "play.schema.json"
    validator = load_validator(play_path, ROOT)
    Draft7Validator.check_schema(validator.schema, resolver=validator.resolver)
