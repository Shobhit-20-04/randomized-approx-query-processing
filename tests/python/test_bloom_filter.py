"""
Unit and property-based tests for BloomFilter.
Verifies zero false negatives, theoretical sizing, empirical FPR, and parameter boundaries.
"""

import pytest
from approx_query.bloom_filter import BloomFilter


def test_bloom_filter_invalid_parameters():
    """Verify proper validation errors on invalid inputs."""
    with pytest.raises(ValueError):
        BloomFilter(expected_capacity=0, target_fpr=0.01)

    with pytest.raises(ValueError):
        BloomFilter(expected_capacity=-10, target_fpr=0.01)

    with pytest.raises(ValueError):
        BloomFilter(expected_capacity=1000, target_fpr=0.0)

    with pytest.raises(ValueError):
        BloomFilter(expected_capacity=1000, target_fpr=1.0)


def test_bloom_filter_parameter_calculation():
    """Verify optimal bit-array size m and hash function count k."""
    n = 10000
    p = 0.01
    bf = BloomFilter(expected_capacity=n, target_fpr=p)
    # Expected m = -10000 * ln(0.01) / (ln(2)^2) ~ 95850.58 -> 95851 bits
    assert bf.m > 90000 and bf.m < 100000
    # Expected k = (m / n) * ln(2) ~ 6.64 -> 7
    assert bf.k in (6, 7)


def test_bloom_filter_zero_false_negatives():
    """
    CRITICAL PROPERTY: An insertion-only Bloom Filter must NEVER return False
    for an element that was inserted.
    """
    bf = BloomFilter(expected_capacity=1000, target_fpr=0.01)
    items = [f"item_{i}" for i in range(1000)]
    bf.add_many(items)

    for item in items:
        assert bf.contains(item) is True, f"False negative observed for {item}!"
        assert (item in bf) is True


def test_bloom_filter_empirical_fpr():
    """Verify empirical false-positive rate on absent items is bounded."""
    n = 2000
    p = 0.05
    bf = BloomFilter(expected_capacity=n, target_fpr=p)
    inserted = [f"key_{i}" for i in range(n)]
    bf.add_many(inserted)

    absent = [f"absent_{i}" for i in range(2000)]
    fpr, fp_count, total = bf.empirical_fpr(absent)

    assert total == 2000
    assert fp_count >= 0
    # Empirical FPR should be in the neighborhood of target (e.g. <= 3 * p)
    assert fpr <= 0.15, f"Empirical FPR {fpr} significantly exceeded tolerance!"


def test_bloom_filter_fill_ratio_and_memory():
    """Verify fill ratio increases with insertions and memory calculation is positive."""
    bf = BloomFilter(expected_capacity=500, target_fpr=0.01)
    assert bf.count_bits_set() == 0
    assert bf.fill_ratio() == 0.0

    bf.add("test_1")
    bf.add("test_2")
    assert bf.count_bits_set() > 0
    assert bf.fill_ratio() > 0.0
    assert bf.memory_usage_bytes() > 0
