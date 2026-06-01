from __future__ import annotations

import logging
from pathlib import Path

_CONFIGURED = False
_CONFIGURED_ROOT: Path | None = None


def jieba_cache_path(root: Path) -> Path:
    return root / "artifacts" / "cache" / "jieba" / "jieba.cache"


def configure_jieba(root: Path | None = None) -> Path:
    """将 jieba 词典缓存固定到本仓库 artifacts/cache/jieba/。"""
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
    # 首次运行写入仓库内缓存；之后直接加载，避免再刷系统临时目录
    jieba.initialize()
    _CONFIGURED = True
    _CONFIGURED_ROOT = root
    return cache_file


def ensure_jieba(root: Path | None = None) -> None:
    configure_jieba(root)
