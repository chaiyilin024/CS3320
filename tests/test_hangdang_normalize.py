"""行当归一化单元测试。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.analytics.utils.hangdang import normalize_coarse, normalize_hangdang


def test_normalize_traditional_labels():
    assert normalize_hangdang("正旦") == "青衣"
    assert normalize_hangdang("末") == "老生"
    assert normalize_hangdang("老生") == "老生"
    assert normalize_hangdang("文武丑") == "文武丑"
    assert normalize_coarse("末") == "生"
    assert normalize_coarse(None, "正旦") == "旦"
    assert normalize_coarse(None, "末") == "生"


def test_normalize_genre():
    from backend.analytics.utils.genre import normalize_genre

    assert normalize_genre("侠义剧") == "侠义剧"
    assert normalize_genre("历史剧") == "历史剧"
    assert normalize_genre("武侠剧") == "其他"
    assert normalize_genre(None) == "未知"
