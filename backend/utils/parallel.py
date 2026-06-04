"""批处理并行工具 — CPU 密集型任务使用进程池（非线程）。"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Callable, TypeVar

T = TypeVar("T")
R = TypeVar("R")

DEFAULT_MAX_WORKERS = 8


def resolve_workers(workers: int | None = None, *, cap: int = DEFAULT_MAX_WORKERS) -> int:
    """0 或负数表示自动：min(CPU 核数, cap)。"""
    if workers is None or workers <= 0:
        cpu = os.cpu_count() or 4
        return max(1, min(cpu, cap))
    return max(1, workers)


def run_parallel(
    fn: Callable[[T], R],
    items: list[T],
    workers: int,
    *,
    cap: int = DEFAULT_MAX_WORKERS,
    progress: Callable[[int, int, R], None] | None = None,
) -> list[R]:
    """对 items 并行 map；workers=1 时退化为串行。"""
    if not items:
        return []
    n_workers = resolve_workers(workers, cap=cap)
    if n_workers == 1 or len(items) == 1:
        out: list[R] = []
        for i, item in enumerate(items):
            result = fn(item)
            out.append(result)
            if progress:
                progress(i + 1, len(items), result)
        return out

    indexed: list[R | None] = [None] * len(items)
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        future_map = {pool.submit(fn, item): idx for idx, item in enumerate(items)}
        done = 0
        for future in as_completed(future_map):
            idx = future_map[future]
            result = future.result()
            indexed[idx] = result
            done += 1
            if progress:
                progress(done, len(items), result)
    return indexed  # type: ignore[return-value]
