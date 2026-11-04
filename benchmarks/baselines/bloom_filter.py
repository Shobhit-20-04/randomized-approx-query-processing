"""
Standard Bloom Filter (Bloom 1970, Kirsch-Mitzenmacher 2006).
Provides optimal k-hash bit probing and exact byte-level memory tracking.
"""

from __future__ import annotations
import math
import numpy as np
from baselines.hash_utils import hash128


class BloomFilter:
    def __init__(
        self,
        expected_capacity: int | None = None,
        target_fpr: float = 0.01,
        m_bits: int | None = None,
        k_hashes: int | None = None,
        seed: int = 42,
    ):
        self.seed = seed
        self.n_inserted = 0

        if m_bits is not None:
            self.m_bits = int(m_bits)
            if k_hashes is not None:
                self.k = int(k_hashes)
            else:
                self.k = max(1, int(round((self.m_bits / max(1, expected_capacity or 1000)) * math.log(2))))
        else:
            if expected_capacity is None or expected_capacity <= 0:
                expected_capacity = 10000
            self.expected_capacity = expected_capacity
            self.target_fpr = target_fpr
            # Optimal m and k
            self.m_bits = int(math.ceil(-expected_capacity * math.log(target_fpr) / (math.log(2) ** 2)))
            self.k = max(1, int(round((self.m_bits / expected_capacity) * math.log(2))))

        self.num_bytes = (self.m_bits + 7) // 8
        self.bit_array = bytearray(self.num_bytes)

    def add(self, key: str | bytes) -> None:
        h_low, _ = hash128(key, seed=self.seed)
        h1 = h_low & 0xFFFFFFFF
        h2 = ((h_low >> 32) & 0xFFFFFFFF) | 1
        m = self.m_bits

        for i in range(self.k):
            bit_idx = (h1 + i * h2) % m
            self.bit_array[bit_idx >> 3] |= (1 << (bit_idx & 7))
        self.n_inserted += 1

    def add_many(self, keys) -> None:
        for k in keys:
            self.add(k)

    def contains(self, key: str | bytes) -> bool:
        h_low, _ = hash128(key, seed=self.seed)
        h1 = h_low & 0xFFFFFFFF
        h2 = ((h_low >> 32) & 0xFFFFFFFF) | 1
        m = self.m_bits

        for i in range(self.k):
            bit_idx = (h1 + i * h2) % m
            if not (self.bit_array[bit_idx >> 3] & (1 << (bit_idx & 7))):
                return False
        return True

    def __contains__(self, key: str | bytes) -> bool:
        return self.contains(key)

    def memory_usage_bytes(self) -> int:
        return self.num_bytes

    def theoretical_fpr(self, n: int | None = None) -> float:
        n_items = n if n is not None else self.n_inserted
        if self.m_bits == 0:
            return 1.0
        return (1.0 - math.exp(-self.k * n_items / self.m_bits)) ** self.k
