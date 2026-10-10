"""
Reproducible dataset generator for approximate query processing benchmarks.
Generates streams under Uniform, Zipfian (skewed), Duplicate-heavy, and High-cardinality distributions.
Provides disjoint known-present and known-absent query sets, hit-rate mixed workloads,
and exact ground truth for frequency and distinct cardinality.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass
from typing import Counter, Dict, List, Sequence, Set, Tuple
import numpy as np


@dataclass
class StreamDataset:
    """Encapsulates a generated stream, query workloads, and ground truth."""
    distribution: str
    stream_size: int
    seed: int
    stream: List[str]
    present_queries: List[str]
    absent_queries: List[str]
    mixed_queries: List[Tuple[str, bool]]  # (query_item, is_present)
    true_frequencies: Dict[str, int]
    true_cardinality: int


def generate_stream(
    distribution: str,
    stream_size: int,
    seed: int = 42,
    universe_size: int | None = None,
    zipf_alpha: float = 1.25,
) -> List[str]:
    """
    Generate a reproducible synthetic data stream of strings.

    Args:
        distribution: One of 'uniform', 'zipfian', 'duplicate_heavy', 'high_cardinality'.
        stream_size: Total number of items in the stream.
        seed: Random seed for reproducibility.
        universe_size: Number of distinct possible items (if None, determined by distribution).
        zipf_alpha: Skewness exponent for Zipfian distribution (alpha > 1).

    Returns:
        List of string tokens.
    """
    rng = np.random.RandomState(seed)

    if distribution == "uniform":
        if universe_size is None:
            universe_size = max(100, stream_size // 2)
        raw_ids = rng.randint(0, universe_size, size=stream_size)

    elif distribution == "zipfian":
        if universe_size is None:
            universe_size = max(100, stream_size // 2)
        # Sample from bounded Zipfian distribution
        # Sample using zipf, bounded to universe_size
        raw_samples = rng.zipf(zipf_alpha, size=stream_size)
        raw_ids = (raw_samples - 1) % universe_size

    elif distribution == "duplicate_heavy":
        # Small universe with high repetition
        small_universe = max(10, min(200, stream_size // 100))
        raw_ids = rng.randint(0, small_universe, size=stream_size)

    elif distribution == "high_cardinality":
        # Nearly all items are unique (e.g. 95% unique)
        universe_size = int(stream_size * 1.5)
        raw_ids = rng.choice(universe_size, size=stream_size, replace=True)

    else:
        raise ValueError(
            f"Unknown distribution '{distribution}'. "
            f"Supported: 'uniform', 'zipfian', 'duplicate_heavy', 'high_cardinality'"
        )

    # Convert to prefixed string identifiers
    return [f"item_{uid:09d}" for uid in raw_ids]


def create_benchmark_dataset(
    distribution: str,
    stream_size: int,
    seed: int = 42,
    query_sample_size: int = 2000,
    hit_rate: float = 0.5,
    zipf_alpha: float = 1.25,
) -> StreamDataset:
    """
    Generate a complete dataset including the stream, known-present queries,
    guaranteed known-absent queries, mixed hit-rate workload, and exact ground truth.
    """
    stream = generate_stream(
        distribution=distribution,
        stream_size=stream_size,
        seed=seed,
        zipf_alpha=zipf_alpha,
    )

    rng = np.random.RandomState(seed + 1000)

    # Compute ground truth
    freq_counter: Counter[str] = collections.Counter(stream)
    true_frequencies: Dict[str, int] = dict(freq_counter)
    distinct_items = list(true_frequencies.keys())
    true_cardinality = len(distinct_items)

    # Sample present queries from distinct items in the stream
    num_queries = min(query_sample_size, len(distinct_items))
    present_indices = rng.choice(len(distinct_items), size=num_queries, replace=False)
    present_queries = [distinct_items[idx] for idx in present_indices]

    # Generate guaranteed absent queries from a strictly disjoint key universe
    # Using prefix "absent_" guarantees disjointness from "item_*"
    absent_queries = [f"absent_{seed}_{i:09d}" for i in range(num_queries)]

    # Verify disjointness
    inserted_set: Set[str] = set(distinct_items)
    for q in absent_queries:
        assert q not in inserted_set, f"Absent query {q} inadvertently present in stream!"

    # Mixed workload with specified hit rate
    num_present_in_mixed = int(num_queries * hit_rate)
    num_absent_in_mixed = num_queries - num_present_in_mixed

    mixed_present = [(present_queries[i], True) for i in range(num_present_in_mixed)]
    mixed_absent = [(absent_queries[i], False) for i in range(num_absent_in_mixed)]
    mixed_workload = mixed_present + mixed_absent
    rng.shuffle(mixed_workload)

    return StreamDataset(
        distribution=distribution,
        stream_size=stream_size,
        seed=seed,
        stream=stream,
        present_queries=present_queries,
        absent_queries=absent_queries,
        mixed_queries=mixed_workload,
        true_frequencies=true_frequencies,
        true_cardinality=true_cardinality,
    )
