"""
HyperLogLog (Flajolet et al. 2007) and HLL++ (Heule et al. 2013).
Supports standard byte registers and 6-bit packed registers with Linear Counting small-range correction.
"""

from __future__ import annotations
import math
import numpy as np
from baselines.hash_utils import hash128, extract_hll_bits


class HyperLogLog:
    def __init__(self, p: int = 10, use_6bit_packing: bool = True, seed: int = 42):
        if not (4 <= p <= 16):
            raise ValueError("Precision p must be between 4 and 16")
        self.p = p
        self.m = 1 << p
        self.seed = seed
        self.use_6bit_packing = use_6bit_packing

        # Alpha constant
        if self.m == 16:
            self.alpha = 0.673
        elif self.m == 32:
            self.alpha = 0.697
        elif self.m == 64:
            self.alpha = 0.709
        else:
            self.alpha = 0.7213 / (1.0 + 1.079 / self.m)

        # Registers: 6-bit packed or uint8
        if use_6bit_packing:
            # 6 bits per register -> 4 registers per 3 bytes
            self.packed_bytes = (self.m * 6 + 7) // 8
            self.registers = bytearray(self.packed_bytes)
        else:
            self.registers = np.zeros(self.m, dtype=np.uint8)

    def _get_reg(self, idx: int) -> int:
        if not self.use_6bit_packing:
            return int(self.registers[idx])
        bit_pos = idx * 6
        byte_pos = bit_pos >> 3
        offset = bit_pos & 7
        val = int(self.registers[byte_pos])
        if offset + 6 <= 8:
            return (val >> offset) & 0x3F
        val |= (int(self.registers[byte_pos + 1]) << 8)
        return (val >> offset) & 0x3F

    def _set_reg(self, idx: int, val: int) -> None:
        val = min(63, max(0, val))
        if not self.use_6bit_packing:
            self.registers[idx] = val
            return
        bit_pos = idx * 6
        byte_pos = bit_pos >> 3
        offset = bit_pos & 7
        if offset + 6 <= 8:
            mask = (0x3F << offset)
            self.registers[byte_pos] = (self.registers[byte_pos] & (~mask & 0xFF)) | ((val << offset) & 0xFF)
        else:
            cur16 = int(self.registers[byte_pos]) | (int(self.registers[byte_pos + 1]) << 8)
            mask16 = 0x3F << offset
            cur16 = (cur16 & ~mask16) | (val << offset)
            self.registers[byte_pos] = cur16 & 0xFF
            self.registers[byte_pos + 1] = (cur16 >> 8) & 0xFF

    def add(self, key: str | bytes) -> None:
        _, h_high = hash128(key, seed=self.seed)
        idx_hll, rank = extract_hll_bits(h_high, self.p)
        cur = self._get_reg(idx_hll)
        if rank > cur:
            self._set_reg(idx_hll, rank)

    def add_many(self, keys) -> None:
        for k in keys:
            self.add(k)

    def cardinality(self) -> float:
        z_sum = 0.0
        v_zeros = 0

        for i in range(self.m):
            val = self._get_reg(i)
            z_sum += 2.0 ** (-val)
            if val == 0:
                v_zeros += 1

        raw_estimate = self.alpha * (self.m ** 2) / z_sum

        # Small range correction (Linear Counting)
        if raw_estimate <= 2.5 * self.m:
            if v_zeros > 0:
                return float(self.m * math.log(float(self.m) / float(v_zeros)))
            return float(raw_estimate)

        # Large range correction (for 32-bit threshold, though we use 64-bit hash)
        two_to_32 = 4294967296.0
        if raw_estimate > (1.0 / 30.0) * two_to_32:
            return float(-two_to_32 * math.log(1.0 - raw_estimate / two_to_32))

        return float(raw_estimate)

    def estimate(self) -> float:
        return self.cardinality()

    def memory_usage_bytes(self) -> int:
        if self.use_6bit_packing:
            return len(self.registers)
        return self.registers.nbytes

    @property
    def theoretical_rse(self) -> float:
        return 1.04 / math.sqrt(self.m)
