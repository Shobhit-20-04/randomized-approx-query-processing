"""Live per-query error certificates for AdaLog-Sketch (Novel Contribution N3).

Generates real-time membership false-positive probabilities and
cardinality confidence intervals grounded in current internal sketch occupancy.
"""

from dataclasses import dataclass
from typing import List, Tuple
import math


@dataclass
class CertifiedFrequencyResult:
    f_raw: int
    f_debiased: int
    lo: int
    hi: int
    is_stash: bool


@dataclass
class CertifiedMembershipResult:
    is_present: bool
    live_fpr: float


@dataclass
class CertifiedCardinalityResult:
    cardinality_estimate: int
    confidence_interval: Tuple[int, int]
    relative_standard_error: float


def compute_live_fpr(sketch) -> float:
    """Compute exact live false-positive probability from current row occupancies.
    
    For Variant A, query returns present iff all d counters > 0.
    Under independent hash functions, live FPR is product of row occupancies.
    """
    total_fpr = 1.0
    for row in sketch.matrix:
        nonzero = sum(1 for v in row if v > 0)
        row_occupancy = nonzero / float(sketch.w) if sketch.w > 0 else 1.0
        total_fpr *= row_occupancy
    return min(1.0, max(0.0, total_fpr))


def compute_cardinality_certificate(
    cardinality_estimate: int,
    m: int,
    confidence: float = 0.95,
) -> CertifiedCardinalityResult:
    """Compute confidence interval for HLL cardinality estimate."""
    rse = 1.04 / math.sqrt(m) if m > 0 else 1.0
    std_err = cardinality_estimate * rse

    # Two-tailed normal z-score: 1.96 for 95%
    z = 1.96 if abs(confidence - 0.95) < 0.02 else 2.576
    margin = z * std_err

    lo = max(1, int(round(cardinality_estimate - margin)))
    hi = int(round(cardinality_estimate + margin))

    return CertifiedCardinalityResult(
        cardinality_estimate=cardinality_estimate,
        confidence_interval=(lo, hi),
        relative_standard_error=rse,
    )
