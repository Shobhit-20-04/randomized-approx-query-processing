"""Telemetry signal extractors for online adaptive control of AdaLog-Sketch.

Gathers lightweight internal state metrics:
- Counter saturation rate S (fraction of cells >= 250 in 8-bit mode)
- Matrix non-zero occupancy D (fraction of cells > 0)
- Stash hit rate H (stash hits / total epoch updates)
- Fitted Zipfian skew alpha_hat (estimated from rank-frequency regression of stash entries)
- Eviction count in current epoch
"""

from dataclasses import dataclass
import math
from typing import List, Tuple


@dataclass
class TelemetrySnapshot:
    saturation_rate: float
    nonzero_density: float
    stash_hit_rate: float
    stash_occupancy: float
    estimated_skew: float
    epoch_updates: int
    epoch_evictions: int


def estimate_skew_from_stash(counts: List[int]) -> float:
    """Estimate Zipfian skew alpha by fitting log(count_i) vs log(rank_i).
    
    Uses ordinary least squares (OLS) on sorted stash counts.
    If fewer than 4 distinct counts exist, returns default 1.25.
    """
    if len(counts) < 4:
        return 1.25
    
    sorted_counts = sorted(counts, reverse=True)
    xs = []
    ys = []
    for rank, c in enumerate(sorted_counts, start=1):
        if c <= 0:
            break
        xs.append(math.log(rank))
        ys.append(math.log(c))
    
    if len(xs) < 4:
        return 1.25
    
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    
    var_x = sum((x - mean_x) ** 2 for x in xs)
    if var_x < 1e-9:
        return 1.25
    
    cov_xy = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    slope = cov_xy / var_x
    alpha = -slope  # log(y) = -alpha * log(x) + const
    return max(0.5, min(2.5, alpha))


def collect_telemetry(
    sketch,
    epoch_updates: int,
    epoch_hits: int,
    epoch_evictions: int,
) -> TelemetrySnapshot:
    """Extract telemetry snapshot from an AdaLogSketch instance."""
    # Counter matrix statistics
    total_cells = sketch.d * sketch.w
    saturated_cells = 0
    nonzero_cells = 0
    
    sat_thresh = 250 if sketch.counter_bits == 8 else (sketch.max_val - 10)
    for row in sketch.matrix:
        for val in row:
            if val > 0:
                nonzero_cells += 1
            if val >= sat_thresh:
                saturated_cells += 1
                
    sat_rate = saturated_cells / float(total_cells) if total_cells > 0 else 0.0
    density = nonzero_cells / float(total_cells) if total_cells > 0 else 0.0
    
    # Stash statistics
    hit_rate = epoch_hits / float(epoch_updates) if epoch_updates > 0 else 0.0
    stash_occupancy = len(sketch.stash) / float(sketch.stash.capacity) if sketch.stash.capacity > 0 else 0.0
    
    # Skew estimation
    stash_counts = [entry.total_count for entry in sketch.stash.entries.values()]
    skew_est = estimate_skew_from_stash(stash_counts)
    
    return TelemetrySnapshot(
        saturation_rate=sat_rate,
        nonzero_density=density,
        stash_hit_rate=hit_rate,
        stash_occupancy=stash_occupancy,
        estimated_skew=skew_est,
        epoch_updates=epoch_updates,
        epoch_evictions=epoch_evictions,
    )
