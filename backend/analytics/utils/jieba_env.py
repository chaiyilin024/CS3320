from __future__ import annotations

import logging
from pathlib import Path

_CONFIGURED = False
_CONFIGURED_ROOT: Path | None = None

# Default user dictionary: Peking-opera-specific lexicon shipped with the project
DEFAULT_USER_DICTS: tuple[Path, ...] = (
    Path(__file__).resolve().parent.parent / "theme" / "dict.txt",
)


def jieba_cache_path(root: Path) -> Path:
    return root / "artifacts" / "cache" / "jieba" / "jieba.cache"


def configure_jieba(
    root: Path | None = None,
    user_dicts: tuple[Path, ...] | None = None,
) -> Path:
    """Pin jieba dict cache to artifacts/cache/jieba/ in this repo and load the opera lexicon.

    user_dicts: optional extra user-dict paths; defaults to ``DEFAULT_USER_DICTS``.

    Returns the cache file path.
    """
    global _CONFIGURED, _CONFIGURED_ROOT
    root = (root or Path(__file__).resolve().parents[3]).resolve()
    if _CONFIGURED and _CONFIGURED_ROOT == root:
        return jieba_cache_path(root)
    cache_dir = root / "artifacts" / "cache" / "jieba"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "jieba.cache"

    import jieba

    jieba.dt.cache_file = str(cache_file)
    jieba.setLogLevel(logging.ERROR)
    jieba.initialize()

    for path in (user_dicts or DEFAULT_USER_DICTS):
        if path and path.is_file():
            try:
                _load_userdict_skipping_comments(jieba, path)
            except (OSError, UnicodeDecodeError) as exc:
                logging.getLogger(__name__).warning(
                    "Failed to load jieba user dict %s: %s", path, exc
                )

    _CONFIGURED = True
    _CONFIGURED_ROOT = root
    return cache_file


def ensure_jieba(root: Path | None = None) -> None:
    configure_jieba(root)


def _load_userdict_skipping_comments(jieba_mod, path: Path) -> None:
    """Skip comment lines starting with ; or # and blank lines, then parse via jieba.load_userdict."""
    import io

    buf = io.StringIO()
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped or stripped[0] in (";", "#"):
                continue
            buf.write(line)
    buf.seek(0)
    jieba_mod.load_userdict(buf)
