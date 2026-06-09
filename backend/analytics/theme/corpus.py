from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

TEXT_BLOCK_TYPES = frozenset({"dialogue", "aria", "recitation"})

_THIS_DIR = Path(__file__).resolve().parent
STOPWORDS_FILE = _THIS_DIR / "stopwords.txt"

# POS whitelist: keep content words; filter pronouns, function words, particles, etc.
POS_WHITELIST = frozenset({
    "n", "nr", "ns", "nt", "nz",
    "v", "vn",
    "a", "an", "ad",
    "i", "l",
})

# Header/series/volume bibliographic noise (aligned with preprocessing noise.py)
_METADATA_BLOCK_RE = re.compile(
    r"中国京剧|戏考\s*[《《]|《[^》》]{1,16}》\s*\d{0,3}\s*$|"
    r"^\d{1,3}\s*$|scripts\.xikao",
    re.IGNORECASE,
)
_INLINE_HEADER_RE = re.compile(
    r"中国京剧\s*戏考|戏考\s*[《《][^》》]+[》》]\s*\d+"
)


@lru_cache(maxsize=1)
def _load_stopwords() -> frozenset[str]:
    """Load stopwords.txt; ignore ; / # comment lines and blank lines."""
    out: set[str] = set()
    if STOPWORDS_FILE.is_file():
        for line in STOPWORDS_FILE.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s[0] in (";", "#"):
                continue
            out.add(s)
    return frozenset(out)


@lru_cache(maxsize=1)
def _metadata_stopwords() -> frozenset[str]:
    """Bibliographic/header stopwords (also in stopwords.txt section 13; fallback here)."""
    base = _load_stopwords()
    extra = {
        "中国京剧", "戏考", "中国", "京剧", "全本", "头本", "前本", "后本",
        "二本", "三本", "四本", "五本", "六本", "七本", "八本", "九本",
        "碧缘", "天宝", "九阳", "花田错",
    }
    return frozenset(w for w in extra if w not in base) | base


def is_metadata_block(text: str) -> bool:
    """Whether the whole segment is header/series boilerplate and should be dropped from theme corpus."""
    s = (text or "").strip()
    if len(s) < 2:
        return True
    if _METADATA_BLOCK_RE.search(s):
        return True
    if len(s) <= 40 and _INLINE_HEADER_RE.search(s):
        return True
    return False


def strip_inline_metadata(text: str) -> str:
    """Remove inline remnants like 「中国京剧戏考 《剧名》 N」."""
    s = (text or "").strip()
    s = _INLINE_HEADER_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def build_dynamic_stopwords(play: dict | None) -> frozenset[str]:
    """Build dynamic stopwords from play metadata: character names + aliases + title + series."""
    if not play:
        return frozenset()
    extra: set[str] = set()
    for ch in play.get("characters") or []:
        name = (ch.get("name") or "").strip()
        if name:
            extra.add(name)
            for c in name:
                if "\u4e00" <= c <= "\u9fff":
                    extra.add(c)
        for alias in ch.get("aliases") or []:
            alias = (alias or "").strip()
            if alias:
                extra.add(alias)
    title = (play.get("title") or "").strip()
    if title:
        extra.add(title)
        for c in title:
            if "\u4e00" <= c <= "\u9fff":
                extra.add(c)
    coll = (play.get("collection_name") or "").strip()
    if coll:
        extra.add(coll)
    return frozenset(w for w in extra if w)


def build_corpus_stopwords(plays: list[dict]) -> frozenset[str]:
    """When training on full corpus, merge per-play character/title names so NMF is not dominated by cross-play names."""
    if len(plays) <= 1:
        return frozenset()
    merged: set[str] = set()
    for play in plays:
        merged.update(build_dynamic_stopwords(play))
    return frozenset(merged)


def build_corpus_stopwords_from_paths(
    paths: list[Path],
    load_play_fn,
    on_progress=None,
) -> frozenset[str]:
    """Stream-read plays and extract character/title stopwords only (no text-block traversal)."""
    merged: set[str] = set()
    n = len(paths)
    for i, path in enumerate(paths):
        if on_progress and (i % 200 == 0 or i == n - 1):
            on_progress(i + 1, n)
        try:
            merged.update(build_dynamic_stopwords(load_play_fn(path)))
        except (OSError, KeyError, ValueError, TypeError):
            continue
    return frozenset(merged)


def iter_text_blocks(play: dict) -> list[dict]:
    out = []
    for b in play.get("blocks") or []:
        if b.get("type") not in TEXT_BLOCK_TYPES:
            continue
        text = strip_inline_metadata((b.get("text") or "").strip())
        if len(text) < 2 or is_metadata_block(text):
            continue
        out.append({**b, "text": text})
    return out


def play_document(play: dict) -> str:
    return " ".join(b["text"] for b in iter_text_blocks(play))


def tokenize(text: str, extra_stopwords: frozenset[str] | None = None) -> list[str]:
    """Tokenize with POS filtering.

    dict.txt is only for jieba word boundaries; it does not bypass stopwords.
    """
    extra = extra_stopwords or frozenset()
    base_stop = _metadata_stopwords()
    text = strip_inline_metadata(text)
    if not text:
        return []
    try:
        from ..utils.jieba_env import ensure_jieba

        ensure_jieba()
        import jieba.posseg as pseg
    except ImportError:
        return _fallback_tokenize(text, base_stop, extra)

    words: list[str] = []
    for tok in pseg.cut(text):
        w = (tok.word or "").strip()
        flag = (tok.flag or "").lower()
        if len(w) < 2:
            continue
        if w in base_stop or w in extra:
            continue
        if re.match(r"^[\W\d_]+$", w):
            continue
        if flag in POS_WHITELIST:
            words.append(w)
            continue
        if flag and flag[0] in {"n", "v", "a", "i", "l"}:
            words.append(w)
    return words


def _fallback_tokenize(
    text: str, base_stop: frozenset[str], extra: frozenset[str]
) -> list[str]:
    words = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
    if words:
        return [w for w in words if w not in base_stop and w not in extra]
    return [
        c for c in text
        if "\u4e00" <= c <= "\u9fff" and c not in base_stop and c not in extra
    ]
