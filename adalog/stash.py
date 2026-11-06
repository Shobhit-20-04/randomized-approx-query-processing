"""
AdaLog-Sketch Associative Elephant Stash with Baseline Tracking and Monotonic Write-Back Eviction.
Guarantees one-sided error invariant via max() write-back.
Supports arbitrary string and raw binary keys.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, Union, Dict, List
import sys

KeyType = Union[str, bytes]

@dataclass
class StashEntry:
    key: KeyType
    base_count: int   # CMS estimate at the moment of promotion
    exact_count: int  # Increments accumulated while resident in stash
    tag: int = 0      # Secondary tag slice (31 bits in native C++ where bit 31 is occupancy flag, completing a 95-bit composite fingerprint with 64-bit h1)

    @property
    def total_count(self) -> int:
        tot = self.base_count + self.exact_count
        return min(tot, 0xFFFFFFFFFFFFFFFF)


class ElephantStash:
    def __init__(self, capacity: int = 64, threshold: int = 20, max_counter_val: int = 255):
        self.capacity = capacity
        self.threshold = threshold
        self.max_counter_val = max_counter_val
        self.entries: Dict[KeyType, StashEntry] = {}
        self.evictions = 0
        self.rejections = 0
        self.insertions = 0

    @property
    def tau(self) -> int:
        return self.threshold

    @tau.setter
    def tau(self, value: int):
        self.threshold = value

    def __len__(self) -> int:
        return len(self.entries)

    def __contains__(self, key: KeyType) -> bool:
        return self.contains(key)

    def contains(self, key: KeyType) -> bool:
        return key in self.entries

    def get_count(self, key: KeyType) -> Optional[int]:
        entry = self.entries.get(key)
        if entry is not None:
            return entry.total_count
        return None

    def update_if_present(self, key: KeyType, count: int = 1) -> bool:
        """
        Fast path: if key is in stash, updates in O(1) time without hash computation.
        """
        entry = self.entries.get(key)
        if entry is not None:
            new_exact = entry.exact_count + count
            entry.exact_count = min(new_exact, 0xFFFFFFFFFFFFFFFF)
            return True
        return False

    def promote(self, key: KeyType, baseline_count: int, tag: int = 0) -> Optional[Tuple[KeyType, int]]:
        """
        Attempts to promote key to the stash.
        Returns evicted (key, evict_count) if an eviction occurred, else None.
        Globally fully associative: never rejects when len(entries) < capacity.
        """
        if key in self.entries:
            return None

        # Case A: Stash not full - admit unconditionally into open capacity
        if len(self.entries) < self.capacity:
            self.entries[key] = StashEntry(key=key, base_count=baseline_count, exact_count=0, tag=tag)
            self.insertions += 1
            return None

        # Case B: Stash full - globally find non-saturated entry with minimum total count.
        # Saturated elephants (total_count >= max_counter_val) must NOT be evicted into
        # narrow matrix counters, which would truncate and underestimate (Theorem 2).
        evictable_candidates = [
            (k, e) for k, e in self.entries.items()
            if e.total_count < self.max_counter_val
        ]
        if not evictable_candidates:
            # All stash slots hold saturated elephants; retain them to guarantee Theorem 2
            self.rejections += 1
            return None

        min_key, min_entry = min(evictable_candidates, key=lambda kv: kv[1].total_count)
        min_total = min_entry.total_count

        if baseline_count > min_total:
            # Evict min_key with lossless write-back
            self.evictions += 1
            evicted_item = (min_key, min_total)
            del self.entries[min_key]
            self.entries[key] = StashEntry(key=key, base_count=baseline_count, exact_count=0, tag=tag)
            return evicted_item

        # Promotion rejected: candidate does not exceed the lightest evictable elephant
        self.rejections += 1
        return None

    def top_k(self, k: int = 10) -> List[Tuple[KeyType, int]]:
        return sorted(
            [(e.key, e.total_count) for e in self.entries.values()],
            key=lambda kv: kv[1],
            reverse=True,
        )[:k]

    def logical_memory_bytes(self) -> int:
        """
        Logical hardware memory model: exactly 24 bytes per slot.
        - 8B: Primary 64-bit key hash h1 (Lane 0).
        - 4B: Secondary tag (31-bit entropy mask 0x7FFFFFFF; MSB 0x80000000 is occupancy flag).
              Together with the 64-bit primary hash, this yields an effective 95-bit composite fingerprint.
        - 4B: Baseline count (c_base, uint32).
        - 8B: Exact count accumulator (c_exact, uint64).
        Total: 8 + 4 + 4 + 8 = 24 bytes (strictly zero padding).
        For K=128: exactly 3,072 bytes (48 x 64-byte cache lines).
        """
        return self.capacity * 24

    def memory_usage_bytes(self) -> int:
        """Returns the logical hardware layout allocation (24B * capacity)."""
        return self.logical_memory_bytes()

    def actual_python_runtime_bytes(self) -> int:
        """Reports the host Python dictionary and object allocation overhead."""
        base_size = sys.getsizeof(self.entries)
        for k, e in self.entries.items():
            base_size += sys.getsizeof(k) + sys.getsizeof(e)
        return base_size
