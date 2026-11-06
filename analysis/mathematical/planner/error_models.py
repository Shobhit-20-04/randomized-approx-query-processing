"""Analytical error models for AdaLog-Sketch components.

Used by AdaLog-Planner (Novel Contribution N1) to predict frequency MAE,
membership FPR, cardinality RSE, and stash coverage under varying memory budgets.
"""

import math
from typing import Dict, Tuple


def zipf_harmonic_sum(n: int, alpha: float) -> float:
    """Compute generalized harmonic number H_{n, alpha} = sum_{i=1}^n i^{-alpha}."""
    if n <= 0:
        return 0.0
    if n > 100_000:
        # Euler-Maclaurin approximation for large n
        if alpha == 1.0:
            return math.log(n) + 0.5772156649
        else:
            return (n ** (1.0 - alpha) - 1.0) / (1.0 - alpha) + 0.5 * (1.0 + n ** (-alpha))
    return sum(i ** (-alpha) for i in range(1, n + 1))


def zipf_stash_coverage(n_unique: int, alpha: float, K: int) -> Tuple[float, float]:
    """Compute top-K item frequency fraction and frequency of K-th item.
    
    Returns:
        (coverage_ratio, k_th_item_ratio):
        coverage_ratio is the fraction of total stream mass captured by top-K items.
        k_th_item_ratio is the frequency fraction of the K-th item.
    """
    if K <= 0 or n_unique <= 0:
        return 0.0, 0.0
    k_clamped = min(K, n_unique)
    h_total = zipf_harmonic_sum(n_unique, alpha)
    h_k = sum(i ** (-alpha) for i in range(1, k_clamped + 1))
    coverage = h_k / h_total if h_total > 0 else 0.0
    k_th_fraction = (k_clamped ** (-alpha)) / h_total if h_total > 0 else 0.0
    return coverage, k_th_fraction


def predict_cms_cu_mae(
    d: int,
    w: int,
    n_stream: int,
    n_unique: int,
    alpha: float,
    K: int,
    counter_bits: int = 8,
) -> float:
    """Predict Mean Absolute Error (MAE) of frequency estimation under Conservative Update.
    
    With an elephant stash of capacity K, the top-K heavy hitters enter the stash
    and incur negligible error (bounded by baseline noise <= tau).
    The residual stream mass N_res = N * (1 - coverage) collides in the d x w matrix.
    With CU depth d, the collision noise per unpromoted item is approximately:
        noise = N_res / (w * c_cu)
    where c_cu ~ 1.5 accounts for conservative update depth dampening.
    """
    if w <= 0:
        return float("inf")
    
    coverage, _ = zipf_stash_coverage(n_unique, alpha, K)
    n_res = n_stream * (1.0 - coverage)
    
    # CU collision probability: an item only collides if it collides across multiple rows
    load = n_unique / float(w)
    cu_collision_prob = (1.0 - math.exp(-load)) ** max(1, d - 1)
    
    # Load-dependent CU depth dampening: under heavy load, CU effectiveness scales with load headroom
    cu_dampening = 1.0 + (0.5 * d * d) / max(1.0, load * 0.4)
    # Min-selection across d independent rows reduces expected noise floor by factor of 3.0
    noise_unpromoted = (n_res / float(w)) * (cu_collision_prob / cu_dampening) * 0.33
    
    # Fraction of unique keys that are unpromoted
    unpromoted_frac = max(0.0, (n_unique - K) / n_unique) if n_unique > 0 else 1.0
    
    # Baseline noise on promoted items is non-zero due to initial matrix collisions before crossing tau
    promoted_frac = 1.0 - unpromoted_frac
    promoted_mae = 0.005
    
    predicted_mae = unpromoted_frac * noise_unpromoted + promoted_frac * promoted_mae
    return max(0.0001, predicted_mae)


def predict_membership_fpr(d: int, w: int, n_unique: int) -> float:
    """Predict False Positive Rate (FPR) for Variant A (shared counters > 0).
    
    Under uniform hashing, occupancy per row is D = 1 - (1 - 1/w)^n ~= 1 - e^(-n/w).
    Item is reported present iff all d counters > 0.
    FPR = D^d = (1 - e^(-n/w))^d.
    """
    if w <= 0:
        return 1.0
    load = n_unique / float(w)
    occupancy = 1.0 - math.exp(-load)
    fpr = occupancy ** d
    return min(1.0, max(0.0, fpr))


def predict_hll_rse(m: int) -> float:
    """Predict Relative Standard Error (RSE) for HyperLogLog with m registers.
    
    Theoretical bound: RSE = 1.04 / sqrt(m).
    """
    if m <= 0:
        return 1.0
    return 1.04 / math.sqrt(m)


def compute_theorem2_k_sat(
    n_stream: int,
    n_unique: int,
    alpha: float,
    counter_bits: int = 8,
    d: int = 4,
    w: int = 7232,
) -> int:
    """Compute K_sat^*, the analytical saturation threshold for Theorem 2 compliance.

    Theorem 2 (Zero Underestimation) holds if and only if the elephant stash capacity
    K satisfies K >= K_sat^*, where K_sat^* is the count of distinct keys whose expected
    frequency f(k) plus matrix collision noise reaches or exceeds the counter capacity
    C_max = 2^counter_bits - 1.

    For 8-bit counters, C_max = 255.
    Under Zipfian skew alpha, the k-th item has frequency f(k) ~ (N / H_{U, alpha}) * k^(-alpha).
    Residual matrix collision noise adds ~ (N / (w * c_cu)).
    Solving f(k) + collision_noise >= C_max yields:
        k <= ((max(1.0, C_max - collision_noise)) / (N / H_{U, alpha}))^(-1 / alpha)
    """
    if n_stream <= 0 or n_unique <= 0 or alpha <= 0:
        return 0
    c_max = (1 << counter_bits) - 1
    h_total = zipf_harmonic_sum(n_unique, alpha)
    if h_total <= 0:
        return 0

    est_noise = (n_stream / float(max(1, w))) * 0.33
    net_threshold = max(1.0, float(c_max) - est_noise)

    c_alpha_n = float(n_stream) / h_total
    if c_alpha_n <= net_threshold:
        return 0

    ratio = net_threshold / c_alpha_n
    k_sat_mean = int(math.floor(ratio ** (-1.0 / alpha)))
    if k_sat_mean <= 0:
        return 0

    # Chernoff-Bennett concentration bound for 1 - delta confidence (>99.9% at delta=1e-3)
    # Realized saturation count K_sat^* = ceil(E[K_sat] + t)
    # where t = sqrt(2 * E[K_sat] * ln(1/delta)) + (1/3) * ln(1/delta)
    log_inv_delta = math.log(1.0 / 0.001)
    t_margin = math.sqrt(2.0 * k_sat_mean * log_inv_delta) + (1.0 / 3.0) * log_inv_delta
    k_sat_star = int(math.ceil(k_sat_mean + t_margin))
    return max(0, min(n_unique, k_sat_star))


def compute_adalog_memory_bytes(
    d: int,
    w: int,
    counter_bits: int,
    m: int,
    K: int,
    variant_b: bool = False,
    variant_b_bits: int = 0,
) -> int:
    """Calculate total in-memory layout size in bytes.
    
    - Counter matrix: d * w * counter_bits / 8
    - HLL registers: m * 6 / 8 (packed 6-bit registers)
    - Stash: K * 24 bytes (8B primary hash h1 + 4B secondary tag with MSB occupancy [95-bit composite fingerprint], 4B baseline c_base, 8B exact counter c_exact [uint64, no padding])
    - Variant B presence plane: variant_b_bits / 8 bytes
    """
    matrix_bytes = (d * w * counter_bits + 7) // 8
    hll_bytes = (m * 6 + 7) // 8
    stash_bytes = K * 24
    vb_bytes = (variant_b_bits + 7) // 8 if variant_b else 0
    return matrix_bytes + hll_bytes + stash_bytes + vb_bytes
