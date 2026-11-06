"""
Unit tests for dataset generation.
Verifies reproducibility, distributions, disjointness of absent queries, and ground truth accuracy.
"""

import collections
import pytest
from approx_query.datasets import create_benchmark_dataset, generate_stream


def test_dataset_reproducibility():
    """Identical seeds must yield identical streams."""
    stream_a = generate_stream("uniform", stream_size=500, seed=42)
    stream_b = generate_stream("uniform", stream_size=500, seed=42)
    assert stream_a == stream_b

    stream_c = generate_stream("uniform", stream_size=500, seed=999)
    assert stream_a != stream_c


def test_dataset_distributions():
    """Verify stream generation across all supported distributions."""
    for dist in ["uniform", "zipfian", "duplicate_heavy", "high_cardinality"]:
        stream = generate_stream(dist, stream_size=1000, seed=42)
        assert len(stream) == 1000

    with pytest.raises(ValueError):
        generate_stream("invalid_distribution", stream_size=100)


def test_benchmark_dataset_disjointness_and_truth():
    """Ensure absent queries are genuinely absent and ground truth matches."""
    ds = create_benchmark_dataset("uniform", stream_size=1000, seed=123, query_sample_size=200)

    # Stream size
    assert len(ds.stream) == 1000

    # Ground truth frequency counter
    expected_counter = collections.Counter(ds.stream)
    assert ds.true_frequencies == dict(expected_counter)
    assert ds.true_cardinality == len(expected_counter)

    # Disjointness check
    inserted_set = set(ds.stream)
    for q in ds.absent_queries:
        assert q not in inserted_set

    # Present queries must be in the stream
    for q in ds.present_queries:
        assert q in inserted_set
