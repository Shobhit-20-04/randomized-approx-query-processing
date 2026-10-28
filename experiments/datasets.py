"""Stream dataset generators for reproducible algorithmic benchmarking.

Provides:
- Synthetic Zipfian streams across skews alpha in [1.05, 1.50]
- Drifting streams with dynamic skew shifts (concept drift, bursts, scanners)
- Ground-truth frequency dictionaries and distinct key sets
"""

import math
import random
from typing import Dict, Generator, List, Tuple
from collections import Counter


def generate_zipf_stream(
    n_stream: int = 1_000_000,
    n_unique: int = 100_000,
    alpha: float = 1.25,
    seed: int = 42,
) -> Tuple[List[str], Dict[str, int]]:
    """Generate a synthetic stream following Zipf(alpha) distribution.
    
    Returns:
        (stream_keys, ground_truth_counts)
    """
    rng = random.Random(seed)
    # Precompute Zipf CDF for fast alias/binary search sampling
    weights = [1.0 / ((i + 1) ** alpha) for i in range(n_unique)]
    total_w = sum(weights)
    cdf = []
    accum = 0.0
    for w in weights:
        accum += w / total_w
        cdf.append(accum)

    stream = []
    # Batch sampling for speed
    chunk_size = 50_000
    for _ in range(0, n_stream, chunk_size):
        cur_batch = min(chunk_size, n_stream - len(stream))
        for _ in range(cur_batch):
            r = rng.random()
            lo, hi = 0, n_unique - 1
            while lo < hi:
                mid = (lo + hi) // 2
                if cdf[mid] < r:
                    lo = mid + 1
                else:
                    hi = mid
            stream.append(f"key_{lo}")

    ground_truth = Counter(stream)
    return stream, dict(ground_truth)


def generate_uniform_stream(
    n_stream: int = 100_000,
    n_unique: int = 10_000,
    seed: int = 42,
) -> Tuple[List[str], Dict[str, int]]:
    """Generate a synthetic stream following a uniform distribution over n_unique keys.
    
    Returns:
        (stream_keys, ground_truth_counts)
    """
    rng = random.Random(seed)
    stream = [f"key_{rng.randint(0, n_unique - 1)}" for _ in range(n_stream)]
    ground_truth = Counter(stream)
    return stream, dict(ground_truth)


def generate_drifting_stream(
    phase_lengths: List[int] = [100_000, 100_000, 100_000],
    alphas: List[float] = [1.10, 1.50, 1.20],
    n_unique: int = 100_000,
    burst_keys: int = 10,
    burst_intensity: int = 5_000,
    seed: int = 42,
) -> Tuple[List[str], Dict[str, int], List[int]]:
    """Generate a multi-phase drifting stream with sudden skew shifts and bursts.
    
    Returns:
        (stream_keys, ground_truth_counts, phase_boundaries)
    """
    rng = random.Random(seed)
    stream = []
    boundaries = []
    current_pos = 0

    for phase_idx, (length, alpha) in enumerate(zip(phase_lengths, alphas)):
        weights = [1.0 / ((i + 1) ** alpha) for i in range(n_unique)]
        total_w = sum(weights)
        cdf = []
        accum = 0.0
        for w in weights:
            accum += w / total_w
            cdf.append(accum)

        for _ in range(length):
            r = rng.random()
            lo, hi = 0, n_unique - 1
            while lo < hi:
                mid = (lo + hi) // 2
                if cdf[mid] < r:
                    lo = mid + 1
                else:
                    hi = mid
            stream.append(f"key_{lo}")

        current_pos += length
        boundaries.append(current_pos)

        # Inject burst at transition
        if phase_idx == 1:
            for b in range(burst_keys):
                burst_key = f"burst_key_{b}"
                for _ in range(burst_intensity // burst_keys):
                    stream.append(burst_key)
            current_pos += burst_intensity
            boundaries.append(current_pos)

    ground_truth = Counter(stream)
    return stream, dict(ground_truth), boundaries
