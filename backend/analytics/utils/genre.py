"""Align genre tags with schema.genre."""
from __future__ import annotations

SCHEMA_GENRES = frozenset(
    {
        "历史剧",
        "家庭剧",
        "公案剧",
        "神话剧",
        "爱情剧",
        "战争剧",
        "侠义剧",
        "其他",
        "未知",
    }
)


def normalize_genre(value: str | None) -> str:
    if not value or not str(value).strip():
        return "未知"
    s = str(value).strip()
    if s in SCHEMA_GENRES:
        return s
    return "其他"
