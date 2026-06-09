"""Parallel utilities unit tests."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.utils.parallel import resolve_workers, run_parallel


def test_resolve_workers():
    assert resolve_workers(1) == 1
    assert resolve_workers(4) == 4
    auto = resolve_workers(0)
    assert auto >= 1


def test_run_parallel_serial():
    out = run_parallel(lambda x: x * 2, [1, 2, 3], 1)
    assert out == [2, 4, 6]


def test_run_parallel_order():
    out = run_parallel(lambda x: x, [3, 1, 2], 1)
    assert out == [3, 1, 2]
