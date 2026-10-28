"""Online Adaptive Controller (Novel Contribution N2).

Monitors streaming telemetry epoch-by-epoch and dynamically tunes the promotion
threshold tau and stash policies to adapt to concept drift, skew shifts,
and heavy-hitter bursts without violating one-sided error guarantees.
"""

from typing import List, Optional
from controller.telemetry_signals import TelemetrySnapshot, collect_telemetry


class AdaptiveController:
    """Epoch-based closed-loop controller for AdaLog-Sketch."""

    def __init__(
        self,
        epoch_size: int = 50_000,
        tau_min: int = 8,
        tau_max: int = 45,
        default_tau: int = 20,
    ):
        self.epoch_size = epoch_size
        self.tau_min = tau_min
        self.tau_max = tau_max
        self.current_tau = default_tau

        # Epoch telemetry counters
        self.epoch_updates = 0
        self.epoch_hits = 0
        self.epoch_evictions = 0
        self.total_updates = 0

        # Telemetry history for auditing
        self.history: List[TelemetrySnapshot] = []
        self.tau_history: List[int] = [default_tau]

    def record_update(self, hit: bool, evicted: bool = False):
        """Record an ingestion event."""
        self.epoch_updates += 1
        self.total_updates += 1
        if hit:
            self.epoch_hits += 1
        if evicted:
            self.epoch_evictions += 1

    def should_step(self) -> bool:
        """Check if an epoch boundary has been reached."""
        return self.epoch_updates >= self.epoch_size

    def step(self, sketch) -> int:
        """Execute one controller epoch step.
        
        Reads telemetry, computes new tau, applies it to sketch,
        resets epoch counters, and returns new tau.
        """
        snapshot = collect_telemetry(
            sketch=sketch,
            epoch_updates=self.epoch_updates,
            epoch_hits=self.epoch_hits,
            epoch_evictions=self.epoch_evictions,
        )
        self.history.append(snapshot)

        new_tau = self._compute_new_tau(snapshot)
        new_tau = max(self.tau_min, min(self.tau_max, new_tau))

        # Apply to sketch
        self.current_tau = new_tau
        sketch.stash.tau = new_tau
        self.tau_history.append(new_tau)

        # Reset epoch tracking
        self.epoch_updates = 0
        self.epoch_hits = 0
        self.epoch_evictions = 0

        return new_tau

    def _compute_new_tau(self, snap: TelemetrySnapshot) -> int:
        """Fast-acting closed-loop decision rule for tau adaptation."""
        # Rule 1: High Skew or Burst Detection
        # If stream is skewed (alpha > 1.25) or stash hit rate is high, drop tau to 8
        # so heavy items promote immediately, capturing top flow mass into stash.
        if snap.estimated_skew > 1.25 or snap.stash_hit_rate > 0.15 or snap.saturation_rate > 0.02:
            return 8

        # Rule 2: Low Skew or Dispersed Scanner Stream
        # If stream is nearly uniform (alpha < 1.15) with low stash hit rate, raise tau to 25
        # so transient tail items do not thrash the stash and cause excessive evictions.
        if snap.estimated_skew < 1.15 and snap.stash_hit_rate < 0.05:
            return 25

        # Rule 3: Thrashing Suppression
        eviction_ratio = snap.epoch_evictions / float(snap.epoch_updates) if snap.epoch_updates > 0 else 0.0
        if eviction_ratio > 0.03:
            return min(self.tau_max, self.current_tau + 5)

        return 15
