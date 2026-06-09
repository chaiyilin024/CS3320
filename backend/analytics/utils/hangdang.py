"""Xiqu catalog hangdang aliases → analytics schema standard hangdang (definitions.hangdang)."""
from __future__ import annotations

SCHEMA_HANGDANG = frozenset(
    {
        "老生",
        "小生",
        "武生",
        "红生",
        "青衣",
        "花旦",
        "刀马旦",
        "老旦",
        "净",
        "丑",
        "文武丑",
        "未知",
        "其他",
    }
)

SCHEMA_COARSE = frozenset({"生", "旦", "净", "丑", "未知", "其他"})

# Xiqu catalog / traditional labels → schema enum
_ALIAS_TO_CANONICAL: dict[str, str] = {
    # sheng
    "生": "老生",
    "外": "小生",
    "娃娃生": "小生",
    "冠生": "小生",
    "巾生": "小生",
    "穷生": "小生",
    "翎子生": "小生",
    "袍带生": "老生",
    "箭衣生": "武生",
    "长靠武生": "武生",
    "短打武生": "武生",
    "把子生": "武生",
    # mo → mapped to laosheng
    "末": "老生",
    "正末": "老生",
    "副末": "老生",
    "冲末": "老生",
    "外末": "老生",
    # dan
    "旦": "青衣",
    "正旦": "青衣",
    "青衣": "青衣",
    "闺门旦": "青衣",
    "花衫": "青衣",
    "刺杀旦": "青衣",
    "花旦": "花旦",
    "彩旦": "花旦",
    "贴旦": "花旦",
    "泼辣旦": "花旦",
    "奴旦": "花旦",
    "疯旦": "花旦",
    "刀马旦": "刀马旦",
    "武旦": "刀马旦",
    "老旦": "老旦",
    # jing
    "净": "净",
    "正净": "净",
    "副净": "净",
    "武净": "净",
    "铜锤花脸": "净",
    "架子花脸": "净",
    "摔打花脸": "净",
    "黑净": "净",
    "白净": "净",
    "红净": "净",
    # chou
    "丑": "丑",
    "文丑": "丑",
    "武丑": "丑",
    "老丑": "丑",
    "文武丑": "文武丑",
    "茶衣丑": "丑",
    "袍带丑": "丑",
    "鞋皮丑": "丑",
    "方巾丑": "丑",
    "婆子丑": "丑",
    "小丑": "丑",
}

_CANONICAL_TO_COARSE: dict[str, str] = {
    "老生": "生",
    "小生": "生",
    "武生": "生",
    "红生": "生",
    "青衣": "旦",
    "花旦": "旦",
    "刀马旦": "旦",
    "老旦": "旦",
    "净": "净",
    "丑": "丑",
    "文武丑": "丑",
    "未知": "未知",
    "其他": "其他",
}

_COARSE_ALIAS: dict[str, str] = {
    "末": "生",
    "生": "生",
    "旦": "旦",
    "净": "净",
    "丑": "丑",
}


def normalize_hangdang(value: str | None) -> str | None:
    """Map PDF/xiqu catalog labels to schema.hangdang enum values."""
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    if s in SCHEMA_HANGDANG:
        return s
    if s in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[s]
    return "其他"


def normalize_coarse(value: str | None, hangdang: str | None = None) -> str:
    """Map to schema.hangdangCoarse."""
    if hangdang:
        canon = normalize_hangdang(hangdang) or "未知"
        return _CANONICAL_TO_COARSE.get(canon, "未知")
    if not value:
        return "未知"
    s = value.strip()
    if s in SCHEMA_COARSE:
        return s
    if s in _COARSE_ALIAS:
        return _COARSE_ALIAS[s]
    if s in _ALIAS_TO_CANONICAL:
        return _CANONICAL_TO_COARSE.get(_ALIAS_TO_CANONICAL[s], "未知")
    return "未知"


def maybe_raw_feature(raw: str | None, canonical: str | None) -> str | None:
    if raw and canonical and raw.strip() != canonical:
        return f"hangdang_raw={raw.strip()}"
    return None
