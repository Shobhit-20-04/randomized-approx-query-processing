"""Cross-task debiasing for AdaLog-Sketch (Novel Contribution N3).

Combines total stream length N, HLL cardinality n_hat, and matrix dimensions
to compute a debiased point estimate of frequency alongside the one-sided upper bound.
"""

import math
from typing import Optional


def compute_debiased_frequency(
    f_raw: int,
    total_stream_items: int,
    cardinality_estimate: int,
    w: int,
    d: int,
    is_stash_hit: bool = False,
    stash_baseline: int = 0,
    stash_volume: int = 0,
) -> int:
    """Compute debiased frequency estimate removing positive collision bias.
    
    If the item was tracked in the stash, its exact post-promotion count is known,
    and baseline noise is bounded <= tau.
    Otherwise, collision noise in CMS-CU is estimated from residual matrix mass:
        E[noise] ~= (N_matrix - f_raw) / (w * (1 + 0.15 * d))
    
    Returns:
        Debiased frequency estimate (guaranteed >= 1 if f_raw >= 1).
    """
    if f_raw <= 0:
        return 0
    if is_stash_hit:
        # In stash: count is f_base + c_exact.
        noise_base = min(stash_baseline, 1)
        return max(1, f_raw - noise_base)

    if w <= 1:
        return f_raw

    # The actual volume entering the matrix excludes stashed heavy hitters
    matrix_mass = max(0, total_stream_items - stash_volume)
    residual_mass = max(0, matrix_mass - f_raw)
    
    # CU noise model: depth d and occupancy determine true collision probability
    load = cardinality_estimate / float(w) if w > 0 else 1.0
    cu_collision_prob = (1.0 - math.exp(-load)) ** max(1, d - 1)
    cu_dampening = 1.0 + 0.5 * d * d
    expected_noise = (residual_mass / float(w)) * (cu_collision_prob / cu_dampening)

    # If expected collision noise is negligible (< 0.25), no debiasing needed
    if expected_noise < 0.25:
        return f_raw

    # Noise cannot exceed f_raw - 1
    expected_noise = min(float(f_raw - 1), expected_noise)
    debiased = f_raw - expected_noise
    return max(1, int(round(debiased)))
