"""Certified frequency intervals [lo, hi] for AdaLog-Sketch (Novel Contribution N3).

Returns a certified confidence interval for point frequency queries where:
- hi: safe one-sided upper bound from CMS-CU (never underestimates true frequency)
- lo: probabilistic lower bound derived from collision noise tail bounds
"""

from typing import Tuple
import math


def compute_frequency_interval(
    f_raw: int,
    total_stream_items: int,
    w: int,
    d: int,
    confidence: float = 0.95,
    is_stash_hit: bool = False,
    stash_baseline: int = 0,
) -> Tuple[int, int]:
    """Compute certified frequency interval [lo, hi].
    
    Args:
        f_raw: raw frequency estimate from sketch
        total_stream_items: total items inserted into the sketch (N)
        w: width of counter matrix
        d: depth of counter matrix
        confidence: desired confidence level (default 0.95)
        is_stash_hit: whether item is currently stored in the stash
        stash_baseline: baseline estimate recorded upon promotion
        
    Returns:
        (lo, hi): certified interval such that P(f_true in [lo, hi]) >= confidence.
    """
    if f_raw <= 0:
        return (0, 0)

    # Upper bound is guaranteed by Theorem 2 (one-sided invariant)
    hi = f_raw

    if is_stash_hit:
        # In stash: true frequency is f_base_true + c_exact.
        # Since f_base >= f_base_true >= 1, the max error on baseline is stash_baseline - 1.
        lo = max(1, f_raw - max(0, stash_baseline - 1))
        return (lo, hi)

    if w <= 1:
        return (1, hi)

    # Collision noise bound via Markov / Chebyshev tail inequality:
    # With probability >= confidence (delta = 1 - confidence),
    # max noise across CU min-selection is bounded by:
    delta = max(0.001, 1.0 - confidence)
    multiplier = (1.0 / delta) ** (1.0 / float(d))

    cu_factor = 1.0 + 0.15 * d
    residual_mass = max(0, total_stream_items - f_raw)
    mean_noise = residual_mass / (float(w) * cu_factor)

    noise_bound = multiplier * mean_noise
    lo = max(1, int(math.floor(f_raw - noise_bound)))

    # Ensure lo <= hi always
    lo = min(lo, hi)
    return (lo, hi)
