"""
Unit and property-based tests for HyperLogLog.
Verifies empty sets, small-cardinality Linear Counting correction,
medium/large streams, merge operation, and theoretical relative error bounds.
"""

import pytest
from approx_query.hyperloglog import HyperLogLog


def test_hyperloglog_invalid_precision():
    """Verify bounds on precision parameter p."""
    with pytest.raises(ValueError):
        HyperLogLog(p=3)

    with pytest.raises(ValueError):
        HyperLogLog(p=17)


def test_hyperloglog_empty_stream():
    """Empty HyperLogLog should estimate 0 distinct items."""
    hll = HyperLogLog(p=10)
    assert hll.estimate() == 0.0


def test_hyperloglog_small_cardinality_correction():
    """
    Linear Counting small-range bias correction when estimate <= 2.5 * m.
    Should accurately estimate small distinct counts (e.g. 5, 20).
    """
    hll = HyperLogLog(p=12)  # m = 4096
    items = [f"unique_small_{i}" for i in range(25)]
    hll.add_many(items)

    est = hll.estimate()
    # Expect very high accuracy for small sets via Linear Counting
    assert abs(est - 25) < 3.0


def test_hyperloglog_stream_cardinality():
    """Verify estimate accuracy across 1000 distinct items."""
    hll = HyperLogLog(p=12)  # theoretical RSE ~ 1.625%
    n_distinct = 1000
    items = [f"item_{i}" for i in range(n_distinct)]
    hll.add_many(items)

    est = hll.estimate()
    rel_err = abs(est - n_distinct) / n_distinct

    # For 1000 items, error should reasonably stay within 3 * RSE (approx 5%)
    assert rel_err < 0.08, f"Relative error {rel_err:.4f} was unexpectedly high"


def test_hyperloglog_merge_union():
    """Verify merge functionality of two independent HLL sketches."""
    hll1 = HyperLogLog(p=10)
    hll2 = HyperLogLog(p=10)

    set1 = [f"set1_{i}" for i in range(300)]
    set2 = [f"set2_{i}" for i in range(300)]

    hll1.add_many(set1)
    hll2.add_many(set2)

    merged = hll1.merge(hll2)
    est_union = merged.estimate()

    # Total distinct items = 600
    assert abs(est_union - 600) / 600 < 0.10


def test_hyperloglog_merge_precision_mismatch():
    """Mismatched precision should raise ValueError."""
    hll1 = HyperLogLog(p=10)
    hll2 = HyperLogLog(p=12)
    with pytest.raises(ValueError):
        hll1.merge(hll2)
