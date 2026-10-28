"""
Count-Min Sketch (Cormode & Muthukrishnan 2005) with Conservative Update (Estan & Varghese 2002).
Supports 8-bit, 16-bit, and 32-bit saturating counters.
"""

from __future__ import annotations
import math
import numpy as np
from baselines.hash_utils import hash128, kirsch_mitzenmacher


class CountMinSketch:
    def __init__(
        self,
        epsilon: float | None = None,
        delta: float | None = None,
        width: int | None = None,
        depth: int | None = None,
        counter_bits: int = 32,  # 8, 16, or 32
        conservative_update: bool = False,
        seed: int = 42,
    ):
        self.seed = seed
        self.counter_bits = counter_bits
        self.conservative_update = conservative_update

        if width is not None and depth is not None:
            self.width = int(width)
            self.depth = int(depth)
        elif epsilon is not None and delta is not None:
            self.width = int(math.ceil(math.e / epsilon))
            self.depth = int(math.ceil(math.log(1.0 / delta)))
        else:
            self.width = 1024
            self.depth = 4

        # Dtype and saturation limit
        if counter_bits == 8:
            self.dtype = np.uint8
            self.max_val = 255
        elif counter_bits == 16:
            self.dtype = np.uint16
            self.max_val = 65535
        elif counter_bits == 32:
            self.dtype = np.uint32
            self.max_val = 4294967295
        else:
            raise ValueError("counter_bits must be 8, 16, or 32")

        self.table = np.zeros((self.depth, self.width), dtype=self.dtype)
        self.total_volume = 0

    def _get_indices(self, key: str | bytes) -> list[int]:
        h_low, _ = hash128(key, seed=self.seed)
        return kirsch_mitzenmacher(h_low, self.depth, self.width)

    def update(self, key: str | bytes, count: int = 1) -> None:
        if count <= 0:
            return
        indices = self._get_indices(key)
        self.total_volume += count

        if self.conservative_update:
            # CU: find minimum counter value across all rows
            v_min = min(int(self.table[j, indices[j]]) for j in range(self.depth))
            v_new = min(self.max_val, v_min + count)
            for j in range(self.depth):
                if int(self.table[j, indices[j]]) == v_min:
                    self.table[j, indices[j]] = v_new
        else:
            # Standard CMS update
            for j in range(self.depth):
                cur = int(self.table[j, indices[j]])
                self.table[j, indices[j]] = min(self.max_val, cur + count)

    def update_many(self, keys, count: int = 1) -> None:
        for k in keys:
            self.update(k, count)

    def query(self, key: str | bytes) -> int:
        indices = self._get_indices(key)
        return min(int(self.table[j, indices[j]]) for j in range(self.depth))

    def memory_usage_bytes(self) -> int:
        return self.table.nbytes

    def compute_errors(self, ground_truth: dict[str, int]) -> dict[str, float]:
        errors = []
        rel_errors = []
        underestimates = 0
        overestimates = []

        for key, true_f in ground_truth.items():
            est_f = self.query(key)
            diff = est_f - true_f
            if diff < 0:
                underestimates += 1
            errors.append(abs(diff))
            overestimates.append(max(0, diff))
            rel_errors.append(abs(diff) / max(1, true_f))

        return {
            "mae": float(np.mean(errors)) if errors else 0.0,
            "are": float(np.mean(rel_errors)) if rel_errors else 0.0,
            "max_overestimation": float(np.max(overestimates)) if overestimates else 0.0,
            "underestimates_count": underestimates,
        }
