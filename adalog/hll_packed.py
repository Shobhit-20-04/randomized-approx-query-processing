"""
6-Bit Packed HyperLogLog Registers with Linear Counting for AdaLog-Sketch.
Supports both coupled (m = w) and decoupled (m = 2^p) layouts.
"""

from __future__ import annotations
import math


class PackedHLLRegisters:
    def __init__(self, m: int):
        self.m = m
        # Pack 6 bits per register: 4 registers per 3 bytes
        self.num_bytes = (m * 6 + 7) // 8
        self.buffer = bytearray(self.num_bytes)

        # Alpha constant
        if self.m >= 128:
            self.alpha = 0.7213 / (1.0 + 1.079 / self.m)
        elif self.m >= 64:
            self.alpha = 0.709
        elif self.m >= 32:
            self.alpha = 0.697
        else:
            self.alpha = 0.673

    def get_register(self, idx: int) -> int:
        bit_pos = idx * 6
        byte_pos = bit_pos >> 3
        offset = bit_pos & 7
        val = int(self.buffer[byte_pos])
        if offset + 6 <= 8:
            return (val >> offset) & 0x3F
        val |= (int(self.buffer[byte_pos + 1]) << 8)
        return (val >> offset) & 0x3F

    def update_register(self, idx: int, rank: int) -> None:
        rank = min(63, max(0, rank))
        cur = self.get_register(idx)
        if rank <= cur:
            return

        bit_pos = idx * 6
        byte_pos = bit_pos >> 3
        offset = bit_pos & 7
        if offset + 6 <= 8:
            mask = 0x3F << offset
            self.buffer[byte_pos] = (self.buffer[byte_pos] & (~mask & 0xFF)) | ((rank << offset) & 0xFF)
        else:
            cur16 = int(self.buffer[byte_pos]) | (int(self.buffer[byte_pos + 1]) << 8)
            mask16 = 0x3F << offset
            cur16 = (cur16 & ~mask16) | (rank << offset)
            self.buffer[byte_pos] = cur16 & 0xFF
            self.buffer[byte_pos + 1] = (cur16 >> 8) & 0xFF

    def estimate_cardinality(self) -> float:
        z_sum = 0.0
        v_zeros = 0

        for i in range(self.m):
            val = self.get_register(i)
            z_sum += 2.0 ** (-val)
            if val == 0:
                v_zeros += 1

        raw_estimate = self.alpha * (self.m ** 2) / z_sum

        # Small range correction (Linear Counting)
        if raw_estimate <= 2.5 * self.m:
            if v_zeros > 0:
                return float(self.m * math.log(float(self.m) / float(v_zeros)))
            return float(raw_estimate)

        return float(raw_estimate)

    def memory_usage_bytes(self) -> int:
        return self.num_bytes
