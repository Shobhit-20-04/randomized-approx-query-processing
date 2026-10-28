"""
Elastic Sketch (Yang et al., ACM SIGCOMM 2018).
Separates high-frequency flows into a Heavy Part (with Ostracism eviction voting)
and residual low-frequency flows into a Light Part (CMS-CU).
"""

from __future__ import annotations
import numpy as np
from baselines.count_min_sketch import CountMinSketch
from baselines.hash_utils import hash128


class ElasticBucket:
    __slots__ = ("key", "positive_vote", "negative_vote", "flag")

    def __init__(self):
        self.key: str | None = None
        self.positive_vote: int = 0
        self.negative_vote: int = 0
        self.flag: bool = False  # True if evicted from or swapped into heavy part


class ElasticSketch:
    def __init__(
        self,
        heavy_buckets: int = 128,
        light_width: int = 1024,
        light_depth: int = 4,
        counter_bits: int = 16,
        vote_ratio: int = 8,  # Lambda threshold for Ostracism
        total_memory_bytes: int | None = None,
        seed: int = 42,
    ):
        if total_memory_bytes is not None:
            # Sizing under fixed byte budget B
            heavy_bytes = max(256, int(total_memory_bytes * 0.20))
            heavy_buckets = max(16, heavy_bytes // 20)
            rem_bytes = max(256, total_memory_bytes - heavy_buckets * 20)
            light_depth = 4
            counter_bits = 16
            light_width = max(64, rem_bytes // (light_depth * 2))

        self.num_heavy = heavy_buckets
        self.vote_ratio = vote_ratio
        self.seed = seed

        # Heavy part
        self.heavy_part: list[ElasticBucket] = [ElasticBucket() for _ in range(heavy_buckets)]

        # Light part: CMS with Conservative Update
        self.light_part = CountMinSketch(
            width=light_width,
            depth=light_depth,
            counter_bits=counter_bits,
            conservative_update=True,
            seed=seed,
        )

    def top_k(self, k: int = 100) -> list[tuple[str, int]]:
        candidates = [(b.key, b.positive_vote) for b in self.heavy_part if b.key is not None]
        return sorted(candidates, key=lambda kv: kv[1], reverse=True)[:k]

    def _hash_heavy(self, key: str) -> int:
        h_low, _ = hash128(key, seed=self.seed)
        return h_low % self.num_heavy

    def update(self, key: str, count: int = 1) -> None:
        b_idx = self._hash_heavy(key)
        bucket = self.heavy_part[b_idx]

        if bucket.key is None:
            bucket.key = key
            bucket.positive_vote = count
            bucket.negative_vote = 0
            bucket.flag = False
            return

        if bucket.key == key:
            bucket.positive_vote += count
            return

        # Collision with another key: vote against current resident
        bucket.negative_vote += count
        if bucket.negative_vote / max(1, bucket.positive_vote) >= self.vote_ratio:
            # Ostracism swap: evict resident to light part
            old_key = bucket.key
            old_votes = bucket.positive_vote
            self.light_part.update(old_key, old_votes)

            # Insert new key into heavy part
            bucket.key = key
            bucket.positive_vote = count
            bucket.negative_vote = 1
            bucket.flag = True
        else:
            # Resident kept: send incoming item to light part
            self.light_part.update(key, count)

    def update_many(self, keys, count: int = 1) -> None:
        for k in keys:
            self.update(k, count)

    def query(self, key: str) -> int:
        b_idx = self._hash_heavy(key)
        bucket = self.heavy_part[b_idx]

        if bucket.key == key:
            # If swapped before, count is in both heavy and light parts
            extra = self.light_part.query(key) if bucket.flag else 0
            return bucket.positive_vote + extra

        return self.light_part.query(key)

    def estimate(self, key: str) -> int:
        return self.query(key)

    def top_k(self, k: int = 10) -> list[tuple[str, int]]:
        candidates = []
        for bucket in self.heavy_part:
            if bucket.key is not None:
                candidates.append((bucket.key, self.query(bucket.key)))
        return sorted(candidates, key=lambda kv: kv[1], reverse=True)[:k]

    def memory_usage_bytes(self) -> int:
        # Heavy part: key hash (16 B) + pos (4 B) + neg (4 B) + flag (1 B) = 25 B per bucket
        heavy_bytes = self.num_heavy * 25
        return heavy_bytes + self.light_part.memory_usage_bytes()
