"""
Cuckoo Filter (Fan, Andersen, Kaminsky, Mitzenmacher, CoNEXT 2014).
Supports constant-time membership testing and deletions via partial-key cuckoo hashing.
"""

from __future__ import annotations
import math
import random
from typing import List
from baselines.hash_utils import hash128


class CuckooFilter:
    def __init__(
        self,
        capacity: int = 10000,
        bucket_size: int = 4,
        fingerprint_size_bytes: int = 1,  # 8-bit fingerprint by default
        max_kicks: int = 500,
        seed: int = 42,
    ):
        self.capacity = capacity
        self.bucket_size = bucket_size
        self.f_bytes = fingerprint_size_bytes
        self.max_kicks = max_kicks
        self.seed = seed
        self.rng = random.Random(seed)

        # Number of buckets (power of 2 or close)
        target_buckets = max(16, int(capacity / (0.95 * bucket_size)))
        # Find next power of 2 for clean XOR indexing
        self.num_buckets = 1 << (target_buckets - 1).bit_length()

        # Buckets: 2D list of integer fingerprints
        self.buckets: List[List[int]] = [[] for _ in range(self.num_buckets)]
        self.n_inserted = 0

    def _fingerprint(self, key: str | bytes) -> int:
        _, h_high = hash128(key, seed=self.seed)
        mask = (1 << (8 * self.f_bytes)) - 1
        fp = h_high & mask
        if fp == 0:
            fp = 1  # 0 reserved for empty
        return fp

    def _hash_fingerprint(self, fp: int) -> int:
        h_low, _ = hash128(fp.to_bytes(self.f_bytes, "little"), seed=self.seed ^ 0x9E3779B9)
        return h_low % self.num_buckets

    def _get_indices(self, key: str | bytes) -> tuple[int, int, int]:
        h_low, _ = hash128(key, seed=self.seed)
        fp = self._fingerprint(key)
        i1 = h_low % self.num_buckets
        i2 = (i1 ^ self._hash_fingerprint(fp)) % self.num_buckets
        return i1, i2, fp

    def add(self, key: str | bytes) -> bool:
        i1, i2, fp = self._get_indices(key)

        # Check for free space in i1 or i2
        if len(self.buckets[i1]) < self.bucket_size:
            self.buckets[i1].append(fp)
            self.n_inserted += 1
            return True
        if len(self.buckets[i2]) < self.bucket_size:
            self.buckets[i2].append(fp)
            self.n_inserted += 1
            return True

        # Need eviction kicking
        cur_idx = i1 if self.rng.random() < 0.5 else i2
        cur_fp = fp

        for _ in range(self.max_kicks):
            # Kick a random entry from cur_idx
            slot = self.rng.randint(0, self.bucket_size - 1)
            displaced_fp = self.buckets[cur_idx][slot]
            self.buckets[cur_idx][slot] = cur_fp

            # Move displaced entry to its alternate bucket
            cur_idx = (cur_idx ^ self._hash_fingerprint(displaced_fp)) % self.num_buckets
            cur_fp = displaced_fp

            if len(self.buckets[cur_idx]) < self.bucket_size:
                self.buckets[cur_idx].append(cur_fp)
                self.n_inserted += 1
                return True

        # Filter full (cannot accommodate item)
        return False

    def contains(self, key: str | bytes) -> bool:
        i1, i2, fp = self._get_indices(key)
        return (fp in self.buckets[i1]) or (fp in self.buckets[i2])

    def __contains__(self, key: str | bytes) -> bool:
        return self.contains(key)

    def remove(self, key: str | bytes) -> bool:
        i1, i2, fp = self._get_indices(key)
        if fp in self.buckets[i1]:
            self.buckets[i1].remove(fp)
            self.n_inserted -= 1
            return True
        if fp in self.buckets[i2]:
            self.buckets[i2].remove(fp)
            self.n_inserted -= 1
            return True
        return False

    def memory_usage_bytes(self) -> int:
        return self.num_buckets * self.bucket_size * self.f_bytes
