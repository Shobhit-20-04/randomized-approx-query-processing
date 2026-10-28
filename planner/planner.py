"""AdaLog-Planner: Joint Memory Optimization Engine (Novel Contribution N1).

Given a total byte budget B and streaming workload characteristics (or target
error constraints), AdaLog-Planner analytically solves for the optimal configuration:
  (d, w, counter_bits, m, K, tau)
minimizing multi-objective approximate query processing error.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import math

from planner.error_models import (
    compute_adalog_memory_bytes,
    predict_cms_cu_mae,
    predict_hll_rse,
    predict_membership_fpr,
    zipf_harmonic_sum,
)


@dataclass
class PlannerConfig:
    d: int
    w: int
    counter_bits: int
    m: int
    K: int
    tau: int
    variant_b: bool
    predicted_mae: float
    predicted_fpr: float
    predicted_rse: float
    total_bytes: int

    def to_dict(self) -> Dict:
        return {
            "d": self.d,
            "w": self.w,
            "counter_bits": self.counter_bits,
            "m": self.m,
            "K": self.K,
            "tau": self.tau,
            "variant_b": self.variant_b,
            "predicted_mae": self.predicted_mae,
            "predicted_fpr": self.predicted_fpr,
            "predicted_rse": self.predicted_rse,
            "total_bytes": self.total_bytes,
        }


class AdaLogPlanner:
    """Multi-objective memory planner for unified streaming sketches."""

    def __init__(
        self,
        weight_mae: float = 1.0,
        weight_fpr: float = 1.0,
        weight_rse: float = 1.0,
    ):
        self.w_mae = weight_mae
        self.w_fpr = weight_fpr
        self.w_rse = weight_rse

    def predict_metrics(
        self,
        config: PlannerConfig,
        n_stream: int = 1_000_000,
        n_unique: int = 100_000,
        skew: float = 1.25,
    ) -> Tuple[float, float, float]:
        """Compute theoretical predicted (MAE, FPR, RSE) for a given config."""
        mae = predict_cms_cu_mae(
            d=config.d,
            w=config.w,
            n_stream=n_stream,
            n_unique=n_unique,
            alpha=skew,
            K=config.K,
            counter_bits=config.counter_bits,
        )
        fpr = predict_membership_fpr(d=config.d, w=config.w, n_unique=n_unique)
        rse = predict_hll_rse(m=config.m)
        return mae, fpr, rse

    def optimize(
        self,
        budget_bytes: int,
        n_stream: int = 1_000_000,
        n_unique: int = 100_000,
        skew: float = 1.25,
        target_fpr: Optional[float] = None,
        target_rse: Optional[float] = None,
        target_mae: Optional[float] = None,
    ) -> PlannerConfig:
        """Find the optimal (d, w, counter_bits, m, K, tau) fitting within budget_bytes."""
        best_config: Optional[PlannerConfig] = None
        best_score = float("inf")

        # Candidate parameter search space
        d_candidates = [3, 4, 5]
        counter_bit_candidates = [8, 16]
        m_candidates = [256, 512, 1024, 2048, 4096]
        k_candidates = [16, 32, 64, 128]

        for bits in counter_bit_candidates:
            # Sizing invariant: 8-bit saturating counters require K >= 64 to prevent truncation on elephants
            k_candidates = [64, 128] if bits == 8 else [16, 32, 64, 128]
            for m in m_candidates:
                hll_bytes = (m * 6 + 7) // 8
                if hll_bytes >= budget_bytes:
                    continue

                for K in k_candidates:
                    stash_bytes = K * 16
                    fixed_bytes = hll_bytes + stash_bytes
                    remaining_bytes = budget_bytes - fixed_bytes
                    if remaining_bytes <= 100:
                        continue

                    for d in d_candidates:
                        # Max columns w that fit in remaining_bytes
                        # w * d * bits / 8 <= remaining_bytes
                        w = int((remaining_bytes * 8) // (d * bits))
                        if w < 64:
                            continue

                        # Determine optimal promotion threshold tau
                        # For 8-bit counters, max value is 255, so tau must be in [8, 30]
                        # to guarantee no premature saturation.
                        h_total = zipf_harmonic_sum(n_unique, skew)
                        k_item_count = n_stream * ((K ** (-skew)) / h_total) if h_total > 0 else 10
                        if bits == 8:
                            tau = max(8, min(30, int(k_item_count * 0.7)))
                        else:
                            tau = max(10, min(100, int(k_item_count * 0.7)))

                        # Theoretical predictions
                        pred_mae = predict_cms_cu_mae(
                            d=d, w=w, n_stream=n_stream, n_unique=n_unique,
                            alpha=skew, K=K, counter_bits=bits
                        )
                        pred_fpr = predict_membership_fpr(d=d, w=w, n_unique=n_unique)
                        pred_rse = predict_hll_rse(m=m)

                        actual_bytes = compute_adalog_memory_bytes(
                            d=d, w=w, counter_bits=bits, m=m, K=K
                        )
                        if actual_bytes > budget_bytes:
                            continue

                        # Objective function calculation
                        # Penalties for exceeding explicit targets if specified
                        penalty = 0.0
                        if target_fpr is not None and pred_fpr > target_fpr:
                            penalty += 50.0 * (pred_fpr - target_fpr)
                        if target_rse is not None and pred_rse > target_rse:
                            penalty += 100.0 * (pred_rse - target_rse)
                        if target_mae is not None and pred_mae > target_mae:
                            penalty += 10.0 * (pred_mae - target_mae)

                        # Normalized score (lower is better)
                        # RSE target 0.035 is achieved by m=1024; penalize if RSE exceeds 0.04
                        rse_penalty = max(0.0, pred_rse - 0.035) * 50.0
                        score = (
                            self.w_mae * pred_mae
                            + self.w_fpr * (pred_fpr * 5.0)
                            + self.w_rse * rse_penalty
                            + penalty
                        )

                        if score < best_score:
                            best_score = score
                            best_config = PlannerConfig(
                                d=d,
                                w=w,
                                counter_bits=bits,
                                m=m,
                                K=K,
                                tau=tau,
                                variant_b=False,
                                predicted_mae=pred_mae,
                                predicted_fpr=pred_fpr,
                                predicted_rse=pred_rse,
                                total_bytes=actual_bytes,
                            )

        # Fallback if no configuration met constraints
        if best_config is None:
            m = 512
            K = 32
            d = 4
            bits = 8
            fixed_bytes = (m * 6 + 7) // 8 + K * 16
            rem = max(64, budget_bytes - fixed_bytes)
            w = max(64, int((rem * 8) // (d * bits)))
            best_config = PlannerConfig(
                d=d, w=w, counter_bits=bits, m=m, K=K, tau=20,
                variant_b=False,
                predicted_mae=predict_cms_cu_mae(d, w, n_stream, n_unique, skew, K, bits),
                predicted_fpr=predict_membership_fpr(d, w, n_unique),
                predicted_rse=predict_hll_rse(m),
                total_bytes=compute_adalog_memory_bytes(d, w, bits, m, K),
            )

        return best_config
