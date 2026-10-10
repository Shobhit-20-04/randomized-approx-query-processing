"""
Metrics and measurement utilities for approximate query processing benchmarks.
Includes high-resolution timers, tracemalloc and deep memory measurements,
and accuracy evaluation across Bloom Filter, Count-Min Sketch, and HyperLogLog.
"""

from __future__ import annotations

import math
import sys
import time
import tracemalloc
from typing import Any, Callable, Dict, List, Sequence, Tuple
import numpy as np
import psutil


def measure_execution_time_ns(func: Callable[[], Any]) -> Tuple[Any, int]:
    """
    Execute a callable and measure elapsed wall-clock time in nanoseconds
    using time.perf_counter_ns().
    """
    start_ns = time.perf_counter_ns()
    result = func()
    elapsed_ns = time.perf_counter_ns() - start_ns
    return result, elapsed_ns


def measure_batch_latencies_ns(
    query_fn: Callable[[Any], Any], items: Sequence[Any]
) -> Dict[str, float]:
    """
    Measure individual per-query latencies over a batch of items.
    Returns mean, median (p50), 95th percentile (p95), and total duration in nanoseconds.
    """
    if not items:
        return {"mean_ns": 0.0, "p50_ns": 0.0, "p95_ns": 0.0, "total_ms": 0.0}

    latencies_ns: List[int] = []
    # Warmup 5 items
    for item in items[:5]:
        query_fn(item)

    start_total_ns = time.perf_counter_ns()
    for item in items:
        t0 = time.perf_counter_ns()
        query_fn(item)
        t1 = time.perf_counter_ns()
        latencies_ns.append(t1 - t0)
    total_time_ns = time.perf_counter_ns() - start_total_ns

    lat_arr = np.array(latencies_ns, dtype=np.float64)
    return {
        "mean_ns": float(np.mean(lat_arr)),
        "p50_ns": float(np.percentile(lat_arr, 50)),
        "p95_ns": float(np.percentile(lat_arr, 95)),
        "total_ms": total_time_ns / 1_000_000.0,
    }


def estimate_object_memory_bytes(obj: Any) -> int:
    """
    Estimate memory consumed by Python data structures.
    For custom structures, uses their memory_usage_bytes() method.
    For sets and dicts, accounts for container overhead plus key storage.
    """
    if hasattr(obj, "memory_usage_bytes"):
        return obj.memory_usage_bytes()

    if isinstance(obj, set):
        # Set container size plus average pointer/entry overhead
        base_size = sys.getsizeof(obj)
        # Approximate 8 bytes per pointer reference for contained elements
        return base_size + len(obj) * 8

    if isinstance(obj, dict):
        base_size = sys.getsizeof(obj)
        # Approximate 16 bytes for key/value references
        return base_size + len(obj) * 16

    return sys.getsizeof(obj)


def get_process_rss_bytes() -> int:
    """Get current resident set size (RSS) of the process in bytes."""
    process = psutil.Process()
    return process.memory_info().rss


def compute_confidence_interval_95(values: Sequence[float]) -> Tuple[float, float, float]:
    """
    Compute mean and 95% confidence interval half-width:
    mean, ci_lower, ci_upper.
    Uses Student's t-distribution if scipy is available, otherwise normal approximation.
    """
    if len(values) == 0:
        return 0.0, 0.0, 0.0
    if len(values) == 1:
        v = float(values[0])
        return v, v, v

    arr = np.array(values, dtype=np.float64)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    n = len(arr)
    stderr = std / math.sqrt(n)

    try:
        from scipy import stats
        t_crit = float(stats.t.ppf(0.975, df=n - 1))
    except Exception:
        t_crit = 1.96

    half_width = t_crit * stderr
    return mean, mean - half_width, mean + half_width
