"""
HyperLogLog implementation for approximate distinct cardinality query processing.
Implements Flajolet et al. (2007) algorithm with 64-bit hashing, Linear Counting small-range
bias correction, union/merging capability, and theoretical standard error analysis.
"""

from __future__ import annotations

import math
import struct
import sys
import hashlib
import numpy as np
from typing import Any, Iterable, Sequence, Tuple


class HyperLogLog:
    """
    Randomized data structure for distinct-element cardinality estimation.
    Uses m = 2^p registers, where p is the precision parameter.
    Theoretical relative standard error is approximately 1.04 / sqrt(m).
    """

    def __init__(self, p: int = 12) -> None:
        """
        Initialize HyperLogLog with precision p.

        Args:
            p: Precision parameter (4 <= p <= 16).
               Registers m = 2^p.
               p=8  -> m=256,    RSE ~ 6.50%
               p=10 -> m=1024,   RSE ~ 3.25%
               p=12 -> m=4096,   RSE ~ 1.625%
               p=14 -> m=16384,  RSE ~ 0.8125%
        """
        if not (4 <= p <= 16):
            raise ValueError(f"Precision p must be between 4 and 16, got {p}")

        self.p: int = p
        self.m: int = 1 << p  # 2^p
        self.registers: bytearray = bytearray(self.m)
        self.count_updates: int = 0

        # Precompute alpha_m constant
        self.alpha_m: float = self._compute_alpha_m(self.m)

        # Bit masks and shifts for 64-bit hash
        self._p_shift: int = 64 - p
        self._w_mask: int = (1 << self._p_shift) - 1

    @staticmethod
    def _compute_alpha_m(m: int) -> float:
        """Flajolet et al. bias correction factor alpha_m."""
        if m == 16:
            return 0.673
        elif m == 32:
            return 0.697
        elif m == 64:
            return 0.709
        else:
            return 0.7213 / (1.0 + 1.079 / m)

    @property
    def theoretical_relative_error(self) -> float:
        """Theoretical relative standard error: 1.04 / sqrt(m)."""
        return 1.04 / math.sqrt(self.m)

    def _hash_64(self, item: Any) -> int:
        """Generate well-distributed 64-bit unsigned hash using BLAKE2b."""
        if isinstance(item, bytes):
            data = item
        elif isinstance(item, str):
            data = item.encode("utf-8")
        else:
            data = str(item).encode("utf-8")

        digest = hashlib.blake2b(data, digest_size=8).digest()
        (val,) = struct.unpack("<Q", digest)
        return val

    @staticmethod
    def _rho(w: int, max_bits: int) -> int:
        """
        Return the 1-based index of the first 1-bit from the MSB of w.
        rho(w) = (number of leading zeros in max_bits) + 1.
        If w == 0, returns max_bits + 1.
        """
        if w == 0:
            return max_bits + 1
        # In Python: bit_length gives position of highest 1 bit (1-indexed from LSB)
        # Leading zeros in max_bits = max_bits - w.bit_length()
        return max_bits - w.bit_length() + 1

    def add(self, item: Any) -> None:
        """
        Insert an item into HyperLogLog.
        Extracts j (first p bits) and w (remaining 64-p bits),
        and updates register j with max(registers[j], rho(w)).
        """
        x = self._hash_64(item)
        j = x >> self._p_shift
        w = x & self._w_mask
        rank = self._rho(w, self._p_shift)

        if rank > self.registers[j]:
            self.registers[j] = rank

        self.count_updates += 1

    def add_many(self, items: Iterable[Any]) -> None:
        """Insert a stream of items."""
        for item in items:
            self.add(item)

    def estimate(self) -> float:
        """
        Estimate distinct cardinality of the stream using Flajolet's HLL estimator
        with Linear Counting small-cardinality correction.
        """
        # Indicator sum: sum_{j=0}^{m-1} 2^(-R[j])
        indicator_sum = sum(math.ldexp(1.0, -r) for r in self.registers)
        if indicator_sum == 0.0:
            return 0.0

        raw_estimate = (self.alpha_m * (self.m ** 2)) / indicator_sum

        # Small cardinality correction (Linear Counting) when raw_estimate <= 2.5 * m
        if raw_estimate <= 2.5 * self.m:
            zero_registers = self.registers.count(0)
            if zero_registers > 0:
                # Linear Counting: m * ln(m / V)
                return float(self.m * math.log(self.m / zero_registers))

        # 64-bit hash space avoids large range correction for realistic stream sizes
        return float(raw_estimate)

    def cardinality_error(
        self, true_cardinality: int
    ) -> Tuple[float, float, float, bool]:
        """
        Compute error metrics against exact distinct cardinality.

        Returns:
            Tuple of:
              - estimated_cardinality
              - absolute_error: abs(est - true)
              - relative_error: abs(est - true) / true (0.0 if true == 0)
              - within_theoretical_std_error: bool (rel_err <= 1.04 / sqrt(m))
        """
        est = self.estimate()
        abs_err = abs(est - true_cardinality)
        rel_err = (abs_err / true_cardinality) if true_cardinality > 0 else 0.0
        within_std = rel_err <= self.theoretical_relative_error
        return est, abs_err, rel_err, within_std

    def merge(self, other: HyperLogLog) -> HyperLogLog:
        """
        Merge with another HyperLogLog instance of the same precision p (union).
        """
        if self.p != other.p:
            raise ValueError(
                f"Cannot merge HyperLogLog with different precisions: {self.p} != {other.p}"
            )
        merged = HyperLogLog(p=self.p)
        merged.registers = bytearray(
            max(r1, r2) for r1, r2 in zip(self.registers, other.registers)
        )
        merged.count_updates = self.count_updates + other.count_updates
        return merged

    def memory_usage_bytes(self) -> int:
        """
        Return the exact memory footprint of the internal register bytearray
        plus object overhead in bytes.
        """
        return sys.getsizeof(self.registers) + sys.getsizeof(self)
