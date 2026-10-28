"""
AdaLog-Sketch Associative Elephant Stash with Baseline Tracking and Write-Back Eviction.
Guarantees one-sided error invariant via max() write-back.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
from adalog.hash_utils import hash128, get_matrix_indices


@dataclass
class StashEntry:
    key: str
    base_count: int   # CMS estimate at the moment of promotion
    exact_count: int  # Increments accumulated while resident in stash

    @property
    def total_count(self) -> int:
        return self.base_count + self.exact_count


class ElephantStash:
    def __init__(self, capacity: int = 64, threshold: int = 20, max_counter_val: int = 255):
        self.capacity = capacity
        self.threshold = threshold
        self.max_counter_val = max_counter_val
        self.entries: dict[str, StashEntry] = {}
        self.evictions = 0

    @property
    def tau(self) -> int:
        return self.threshold

    @tau.setter
    def tau(self, value: int):
        self.threshold = value

    def __len__(self) -> int:
        return len(self.entries)

    def contains(self, key: str) -> bool:
        return key in self.entries

    def get_count(self, key: str) -> Optional[int]:
        entry = self.entries.get(key)
        if entry is not None:
            return entry.total_count
        return None

    def update_if_present(self, key: str, count: int = 1) -> bool:
        """
        Fast path: if key is in stash, updates in O(1) time without hash computation.
        """
        entry = self.entries.get(key)
        if entry is not None:
            entry.exact_count += count
            return True
        return False

    def promote(self, key: str, baseline_count: int) -> Optional[Tuple[str, int]]:
        """
        Attempts to promote key to the stash.
        Returns evicted (key, evict_count) if an eviction occurred, else None.
        """
        if key in self.entries:
            return None

        if len(self.entries) < self.capacity:
            self.entries[key] = StashEntry(key=key, base_count=baseline_count, exact_count=0)
            return None

        # Stash full: find entry with minimum total count.
        # Invariant Protection (Theorem 1): An entry with total_count >= max_counter_val
        # must NOT be evicted into narrow matrix counters, which would truncate and underestimate.
        # We only consider candidates whose total_count < max_counter_val.
        evictable_candidates = [
            (k, e) for k, e in self.entries.items()
            if e.total_count < self.max_counter_val
        ]
        if not evictable_candidates:
            # All stash slots hold saturated elephants; retain them to prevent underestimation
            return None

        min_key, min_entry = min(evictable_candidates, key=lambda kv: kv[1].total_count)
        min_total = min_entry.total_count

        if baseline_count > min_total:
            # Evict min_key
            self.evictions += 1
            evicted_item = (min_key, min_total)
            del self.entries[min_key]
            self.entries[key] = StashEntry(key=key, base_count=baseline_count, exact_count=0)
            return evicted_item

        # Promotion rejected; stash retains heavier items
        return None

    def top_k(self, k: int = 10) -> list[tuple[str, int]]:
        return sorted(
            [(e.key, e.total_count) for e in self.entries.values()],
            key=lambda kv: kv[1],
            reverse=True,
        )[:k]

    def memory_usage_bytes(self) -> int:
        # 16-byte key hash + 4-byte baseline + 4-byte exact count = 24 bytes per entry
        return self.capacity * 24
