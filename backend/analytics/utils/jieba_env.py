from __future__ import annotations

import logging
from pathlib import Path

_CONFIGURED = False
_CONFIGURED_ROOT: Path | None = None

# 默认用户词典：随项目分发的京剧专有词典
DEFAULT_USER_DICTS: tuple[Path, ...] = (
    Path(__file__).resolve().parent.parent / "theme" / "dict.txt",
)


def jieba_cache_path(root: Path) -> Path:
    return root / "artifacts" / "cache" / "jieba" / "jieba.cache"


def configure_jieba(
    root: Path | None = None,
    user_dicts: tuple[Path, ...] | None = None,
) -> Path:
    """将 jieba 词典缓存固定到本仓库 artifacts/cache/jieba/，并加载京剧专有词典。

    user_dicts: 传入额外用户词典文件路径；默认加载 ``DEFAULT_USER_DICTS``。
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
                    "加载 jieba 用户词典失败 %s: %s", path, exc
                )

    _CONFIGURED = True
    _CONFIGURED_ROOT = root
    return cache_file


def ensure_jieba(root: Path | None = None) -> None:
    configure_jieba(root)


def _load_userdict_skipping_comments(jieba_mod, path: Path) -> None:
    """跳过以 ;/# 开头的注释行与空行，再交给 jieba.load_userdict 解析。"""
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
