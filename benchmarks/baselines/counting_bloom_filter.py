"""
Counting Bloom Filter (Fan et al. 2000).
Maintains 4-bit or 8-bit counters to support deletions and frequency bounds.
"""

from __future__ import annotations
import math
import numpy as np
from baselines.hash_utils import hash128


class CountingBloomFilter:
    def __init__(
        self,
        expected_capacity: int = 10000,
        target_fpr: float = 0.01,
        counter_bits: int = 4,  # 4-bit or 8-bit
        seed: int = 42,
    ):
        self.seed = seed
        self.counter_bits = counter_bits
        self.max_count = (1 << counter_bits) - 1

        # Size array
        self.m_counters = int(math.ceil(-expected_capacity * math.log(target_fpr) / (math.log(2) ** 2)))
        self.k = max(1, int(round((self.m_counters / expected_capacity) * math.log(2))))

        if counter_bits == 8:
            self.counters = np.zeros(self.m_counters, dtype=np.uint8)
        elif counter_bits == 4:
            # Pack two 4-bit counters per byte
            self.counters = np.zeros((self.m_counters + 1) // 2, dtype=np.uint8)
        else:
            raise ValueError("counter_bits must be 4 or 8")

    def _get_counter(self, idx: int) -> int:
        if self.counter_bits == 8:
            return int(self.counters[idx])
        byte_val = self.counters[idx >> 1]
        if idx & 1:
            return byte_val >> 4
        return byte_val & 0x0F

    def _set_counter(self, idx: int, val: int) -> None:
        val = min(self.max_count, max(0, val))
        if self.counter_bits == 8:
            self.counters[idx] = val
        else:
            byte_idx = idx >> 1
            cur = self.counters[byte_idx]
            if idx & 1:
                self.counters[byte_idx] = (cur & 0x0F) | (val << 4)
            else:
                self.counters[byte_idx] = (cur & 0xF0) | val

    def add(self, key: str | bytes) -> None:
        h_low, _ = hash128(key, seed=self.seed)
        h1 = h_low & 0xFFFFFFFF
        h2 = ((h_low >> 32) & 0xFFFFFFFF) | 1
        m = self.m_counters

        for i in range(self.k):
            idx = (h1 + i * h2) % m
            val = self._get_counter(idx)
            if val < self.max_count:
                self._set_counter(idx, val + 1)

    def contains(self, key: str | bytes) -> bool:
        h_low, _ = hash128(key, seed=self.seed)
        h1 = h_low & 0xFFFFFFFF
        h2 = ((h_low >> 32) & 0xFFFFFFFF) | 1
        m = self.m_counters

        for i in range(self.k):
            idx = (h1 + i * h2) % m
            if self._get_counter(idx) == 0:
                return False
        return True

    def remove(self, key: str | bytes) -> bool:
        if not self.contains(key):
            return False
        h_low, _ = hash128(key, seed=self.seed)
        h1 = h_low & 0xFFFFFFFF
        h2 = ((h_low >> 32) & 0xFFFFFFFF) | 1
        m = self.m_counters

        for i in range(self.k):
            idx = (h1 + i * h2) % m
            val = self._get_counter(idx)
            if val > 0:
                self._set_counter(idx, val - 1)
        return True

    def memory_usage_bytes(self) -> int:
        return self.counters.nbytes
