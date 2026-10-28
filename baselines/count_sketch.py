"""
Count-Sketch (Charikar, Chen, Farach-Colton 2002).
Provides unbiased frequency estimates with L2-norm error bounds using random +/-1 sign hashing.
"""

from __future__ import annotations
import math
import numpy as np
from baselines.hash_utils import hash128, kirsch_mitzenmacher


class CountSketch:
    def __init__(self, width: int = 1024, depth: int = 5, seed: int = 42):
        self.width = width
        self.depth = depth
        self.seed = seed
        self.table = np.zeros((depth, width), dtype=np.int32)

    def _get_hashes(self, key: str | bytes) -> tuple[list[int], list[int]]:
        h_low, h_high = hash128(key, seed=self.seed)
        indices = kirsch_mitzenmacher(h_low, self.depth, self.width)
        # Derive signs from high hash bits
        signs = []
        for j in range(self.depth):
            bit = (h_high >> j) & 1
            signs.append(1 if bit == 1 else -1)
        return indices, signs

    def update(self, key: str | bytes, count: int = 1) -> None:
        indices, signs = self._get_hashes(key)
        for j in range(self.depth):
            self.table[j, indices[j]] += signs[j] * count

    def update_many(self, keys, count: int = 1) -> None:
        for k in keys:
            self.update(k, count)

    def query(self, key: str | bytes) -> int:
        indices, signs = self._get_hashes(key)
        estimates = [signs[j] * int(self.table[j, indices[j]]) for j in range(self.depth)]
        return int(np.median(estimates))

    def memory_usage_bytes(self) -> int:
        return self.table.nbytes
