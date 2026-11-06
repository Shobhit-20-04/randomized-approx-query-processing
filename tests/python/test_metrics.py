"""
Unit tests for metrics and timing utilities.
"""

import pytest
from approx_query.metrics import (
    compute_confidence_interval_95,
    estimate_object_memory_bytes,
    measure_batch_latencies_ns,
    measure_execution_time_ns,
)


def test_measure_execution_time_ns():
    """Verify execution time measurement is positive and returns result."""
    result, elapsed_ns = measure_execution_time_ns(lambda: sum(range(100)))
    assert result == 4950
    assert elapsed_ns > 0


def test_measure_batch_latencies_ns():
    """Verify per-query latencies calculation."""
    d = {"k1": 1, "k2": 2}
    stats = measure_batch_latencies_ns(lambda k: d.get(k, 0), ["k1", "k2", "k3"])
    assert "mean_ns" in stats
    assert "p50_ns" in stats
    assert "p95_ns" in stats
    assert stats["mean_ns"] >= 0


def test_estimate_object_memory_bytes():
    """Verify memory estimation for built-in containers."""
    s = set(range(100))
    mem_s = estimate_object_memory_bytes(s)
    assert mem_s > 0

    d = {i: i * 2 for i in range(100)}
    mem_d = estimate_object_memory_bytes(d)
    assert mem_d > 0


def test_confidence_interval_95():
    """Verify 95% confidence interval computation."""
    vals = [10.0, 10.0, 10.0, 10.0]
    mean, lower, upper = compute_confidence_interval_95(vals)
    assert mean == 10.0
    assert lower == 10.0
    assert upper == 10.0

    vals_spread = [9.0, 10.0, 11.0]
    mean, lower, upper = compute_confidence_interval_95(vals_spread)
    assert mean == 10.0
    assert lower < mean < upper
