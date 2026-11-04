"""
Xor Filter (Graf & Lemire, ACM JEA 2020).
Provides faster membership testing and smaller size (~1.23x fingerprint bits/key) using 3-way peeling.
"""

from __future__ import annotations
import math
import numpy as np
from typing import Sequence
from baselines.hash_utils import hash128


class XorFilter:
    def __init__(self, keys: Sequence[str | bytes] | None = None, fingerprint_bits: int = 8, seed: int = 42):
        self.f_bits = fingerprint_bits
        self.seed = seed
        self.fingerprints: np.ndarray = np.array([], dtype=np.uint8)
        self.block_len = 0
        self.size = 0

        if keys:
            self.build(keys)

    def _hash(self, key: str | bytes, s: int) -> tuple[int, int, int, int]:
        h_low, h_high = hash128(key, seed=s)
        fp = h_high & 0xFF
        if fp == 0:
            fp = 1

        b = self.block_len
        h0 = h_low % b
        h1 = ((h_low >> 21) % b) + b
        h2 = ((h_low >> 42) % b) + 2 * b
        return h0, h1, h2, fp

    def build(self, keys: Sequence[str | bytes]) -> bool:
        keys_list = list(set(keys))
        n = len(keys_list)
        if n == 0:
            return True

        self.size = n
        # 1.23 factor for 3-way hypergraph peeling
        self.block_len = max(32, int(math.ceil(1.23 * n / 3.0)))
        total_len = 3 * self.block_len

        # Peeling algorithm up to 10 trials with different seeds
        for trial in range(10):
            cur_seed = self.seed + trial * 997
            h_data = [self._hash(k, cur_seed) for k in keys_list]

            # Build adjacency lists and degrees
            degrees = [0] * total_len
            t2keys = [[] for _ in range(total_len)]
            for idx, (h0, h1, h2, _) in enumerate(h_data):
                degrees[h0] += 1
                degrees[h1] += 1
                degrees[h2] += 1
                t2keys[h0].append(idx)
                t2keys[h1].append(idx)
                t2keys[h2].append(idx)

            # Queue of degree-1 vertices
            q = [i for i in range(total_len) if degrees[i] == 1]
            stack = []

            while q:
                v = q.pop()
                if degrees[v] != 1:
                    continue
                # Find matching key
                k_idx = -1
                for candidate in t2keys[v]:
                    h0, h1, h2, _ = h_data[candidate]
                    if v in (h0, h1, h2):
                        k_idx = candidate
                        break
                if k_idx == -1:
                    continue

                stack.append((v, k_idx))
                h0, h1, h2, _ = h_data[k_idx]
                for u in (h0, h1, h2):
                    degrees[u] -= 1
                    if degrees[u] == 1:
                        q.append(u)

            if len(stack) == n:
                # Peeling succeeded! Compute fingerprints
                self.seed = cur_seed
                self.fingerprints = np.zeros(total_len, dtype=np.uint8)

                # Solve in reverse order
                while stack:
                    v, k_idx = stack.pop()
                    h0, h1, h2, target_fp = h_data[k_idx]
                    other_xor = 0
                    for u in (h0, h1, h2):
                        if u != v:
                            other_xor ^= int(self.fingerprints[u])
                    self.fingerprints[v] = target_fp ^ other_xor
                return True

        # Fallback if all trials fail
        self.fingerprints = np.zeros(total_len, dtype=np.uint8)
        return False

    def contains(self, key: str | bytes) -> bool:
        if len(self.fingerprints) == 0:
            return False
        h0, h1, h2, fp = self._hash(key, self.seed)
        val = int(self.fingerprints[h0]) ^ int(self.fingerprints[h1]) ^ int(self.fingerprints[h2])
        return val == fp

    def __contains__(self, key: str | bytes) -> bool:
        return self.contains(key)

    def memory_usage_bytes(self) -> int:
        return self.fingerprints.nbytes
