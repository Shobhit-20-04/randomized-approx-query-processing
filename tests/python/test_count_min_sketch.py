"""
Unit and property-based tests for CountMinSketch.
Verifies no underestimation, additive bound guarantees, multi-updates, and unseen key behavior.
"""

import collections
import pytest
from approx_query.count_min_sketch import CountMinSketch


def test_count_min_sketch_invalid_parameters():
    """Verify parameter validation."""
    with pytest.raises(ValueError):
        CountMinSketch(epsilon=0.0, delta=0.01)

    with pytest.raises(ValueError):
        CountMinSketch(epsilon=1.0, delta=0.01)

    with pytest.raises(ValueError):
        CountMinSketch(epsilon=0.05, delta=0.0)

    with pytest.raises(ValueError):
        CountMinSketch(epsilon=0.05, delta=1.0)


def test_count_min_sketch_sizing():
    """Verify table width and depth calculations."""
    cms = CountMinSketch(epsilon=0.01, delta=0.01)
    # width = ceil(e / 0.01) ~ 272
    # depth = ceil(ln(1 / 0.01)) ~ 5
    assert cms.width >= 271
    assert cms.depth >= 4
    assert cms.table.shape == (cms.depth, cms.width)


def test_count_min_sketch_no_underestimation():
    """
    CRITICAL PROPERTY: Count-Min Sketch must NEVER underestimate
    the true frequency of an item under nonnegative updates.
    """
    cms = CountMinSketch(epsilon=0.05, delta=0.01, seed=42)
    stream = ["alpha"] * 50 + ["beta"] * 12 + ["gamma"] * 3
    cms.update_many(stream)

    assert cms.query("alpha") >= 50
    assert cms.query("beta") >= 12
    assert cms.query("gamma") >= 3
    assert cms.query("nonexistent") >= 0


def test_count_min_sketch_repeated_updates():
    """Verify incremental updates accumulate correctly."""
    cms = CountMinSketch(epsilon=0.05, delta=0.01)
    cms.update("item_x", count=5)
    assert cms.query("item_x") >= 5

    cms.update("item_x", count=10)
    assert cms.query("item_x") >= 15

    with pytest.raises(ValueError):
        cms.update("item_x", count=-1)


def test_count_min_sketch_theoretical_error_bound():
    """
    Verify additive error bound:
    query(x) <= true_freq(x) + epsilon * total_count with probability >= 1 - delta.
    """
    eps = 0.05
    delta = 0.01
    cms = CountMinSketch(epsilon=eps, delta=delta, seed=123)

    # 1000 items stream
    stream = [f"item_{i % 50}" for i in range(1000)]
    cms.update_many(stream)

    truth = collections.Counter(stream)
    error_summary = cms.compute_errors(truth)

    assert error_summary["underestimation_count"] == 0
    # Over 95% of queries should obey the theoretical bound
    assert error_summary["bound_compliance_ratio"] >= (1.0 - delta)
    assert cms.memory_usage_bytes() > 0
