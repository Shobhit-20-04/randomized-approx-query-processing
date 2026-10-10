"""
Bloom Filter implementation for approximate membership query processing.
Implements double-hashing (Kirsch-Mitzenmacher optimization), optimal parameter sizing,
and empirical/theoretical false-positive rate estimation.
"""

from __future__ import annotations

import math
import struct
import sys
import hashlib
from typing import Any, Iterable, List, Sequence, Tuple


class BloomFilter:
    """
    Standard space-efficient randomized data structure for set membership queries.
    Guarantees no false negatives (if an item was inserted, contains(item) is always True).
    Allows a small, controllable false-positive probability p.
    """

    def __init__(
        self,
        expected_capacity: int,
        target_fpr: float,
        m: int | None = None,
        k: int | None = None,
    ) -> None:
        """
        Initialize Bloom Filter.

        Args:
            expected_capacity: Expected number of distinct elements (n > 0).
            target_fpr: Desired false-positive probability (0 < p < 1).
            m: Optional explicit bit-array size. If None, calculated from n and p.
            k: Optional explicit number of hash functions. If None, calculated from m and n.
        """
        if expected_capacity <= 0:
            raise ValueError(f"expected_capacity must be positive, got {expected_capacity}")
        if not (0.0 < target_fpr < 1.0):
            raise ValueError(f"target_fpr must be in (0, 1), got {target_fpr}")

        self.expected_capacity: int = expected_capacity
        self.target_fpr: float = target_fpr

        # Calculate optimal m and k if not explicitly given
        if m is None:
            # m = -n * ln(p) / (ln(2)^2)
            calculated_m = math.ceil(
                -expected_capacity * math.log(target_fpr) / (math.log(2) ** 2)
            )
            self.m: int = max(1, calculated_m)
        else:
            if m <= 0:
                raise ValueError(f"Bit array size m must be positive, got {m}")
            self.m = m

        if k is None:
            # k = (m / n) * ln(2)
            calculated_k = round((self.m / self.expected_capacity) * math.log(2))
            self.k: int = max(1, calculated_k)
        else:
            if k <= 0:
                raise ValueError(f"Number of hash functions k must be positive, got {k}")
            self.k = k

        # Bit array stored as compact bytearray
        self._byte_count: int = (self.m + 7) // 8
        self._bit_array: bytearray = bytearray(self._byte_count)
        self.count: int = 0  # Number of add operations performed

    @property
    def bit_count(self) -> int:
        """Total bit count m."""
        return self.m

    @property
    def hash_count(self) -> int:
        """Number of hash functions k."""
        return self.k

    def _hash_pair(self, item: Any) -> Tuple[int, int]:
        """
        Generate two 64-bit independent hashes (h1, h2) for double hashing
        using BLAKE2b (16-byte digest).
        """
        if isinstance(item, bytes):
            data = item
        elif isinstance(item, str):
            data = item.encode("utf-8")
        else:
            data = str(item).encode("utf-8")

        digest = hashlib.blake2b(data, digest_size=16).digest()
        h1, h2 = struct.unpack("<QQ", digest)
        # Ensure h2 is odd / non-zero to guarantee full cycle over m if coprime
        if h2 == 0:
            h2 = 1
        return h1, h2

    def _get_indices(self, item: Any) -> List[int]:
        """
        Generate k bit indices using Kirsch-Mitzenmacher optimization:
        g_i(x) = (h1(x) + i * h2(x)) mod m for i in 0..k-1
        """
        h1, h2 = self._hash_pair(item)
        m = self.m
        return [(h1 + i * h2) % m for i in range(self.k)]

    def add(self, item: Any) -> None:
        """
        Insert an item into the Bloom Filter.
        Sets k bits corresponding to g_i(item) to 1.
        """
        ba = self._bit_array
        for bit_index in self._get_indices(item):
            byte_idx = bit_index >> 3
            bit_mask = 1 << (bit_index & 7)
            ba[byte_idx] |= bit_mask
        self.count += 1

    def add_many(self, items: Iterable[Any]) -> None:
        """Insert multiple items in batch."""
        for item in items:
            self.add(item)

    def contains(self, item: Any) -> bool:
        """
        Check if an item is likely in the set.

        Returns:
            False: Item is definitely NOT in the set (zero false negatives).
            True: Item is probably in the set (potential false positive).
        """
        ba = self._bit_array
        for bit_index in self._get_indices(item):
            byte_idx = bit_index >> 3
            bit_mask = 1 << (bit_index & 7)
            if not (ba[byte_idx] & bit_mask):
                return False
        return True

    def __contains__(self, item: Any) -> bool:
        return self.contains(item)

    def theoretical_fpr(self, n_items: int | None = None) -> float:
        """
        Compute theoretical false positive rate for a given number of inserted items.
        Formula: (1 - exp(-k * n / m))^k or (1 - (1 - 1/m)^(k * n))^k.
        """
        n = self.count if n_items is None else n_items
        if n <= 0:
            return 0.0
        # Standard approximation: (1 - e^(-k * n / m))^k
        exponent = -self.k * n / self.m
        p_bit_zero = math.exp(exponent)
        return float((1.0 - p_bit_zero) ** self.k)

    def empirical_fpr(self, absent_items: Sequence[Any]) -> Tuple[float, int, int]:
        """
        Compute empirical false positive rate on a known set of absent items.

        Returns:
            Tuple of (fpr, false_positive_count, total_tested_absent).
        """
        if not absent_items:
            return 0.0, 0, 0
        fp_count = sum(1 for item in absent_items if self.contains(item))
        fpr = fp_count / len(absent_items)
        return fpr, fp_count, len(absent_items)

    def count_bits_set(self) -> int:
        """Return the number of bits currently set to 1."""
        return sum(bin(byte).count("1") for byte in self._bit_array)

    def fill_ratio(self) -> float:
        """Return the fraction of bits currently set to 1."""
        return self.count_bits_set() / self.m

    def memory_usage_bytes(self) -> int:
        """
        Return the exact memory footprint of the internal bit array
        plus object overhead in bytes.
        """
        return sys.getsizeof(self._bit_array) + sys.getsizeof(self)
