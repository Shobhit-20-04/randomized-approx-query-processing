"""
AdaLog-Sketch: Adaptive Logarithmic Heavy-Hitter and Cardinality Sketch.
Synthesizes principles from:
  1. Cormode-Muthukrishnan (2005) - Count-Min Sketch matrix foundations.
  2. Goyal et al. / Estan-Varghese - Conservative Update (CU) optimization.
  3. Metwally et al. - Heavy-Hitter Elephant Stash (Space-Saving isolation).
  4. Flajolet et al. (2007) - Integrated Harmonic Mean Cardinality Estimation.
  5. Yu et al. (IWQoS 2026) - LightRanger Equal Element Grouping (EEG) & Base-Bit Reduction (BBR).
"""

from __future__ import annotations

import collections
import dataclasses
import hashlib
import io
import math
import struct
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
import numpy as np


class AdaLogSketch:
    """
    AdaLog-Sketch: A unified, skew-adaptive probabilistic data structure
    providing concurrent Approximate Membership Queries (AMQ), Frequency Estimation,
    Heavy-Hitter Tracking, and Distinct Cardinality Estimation.
    """

    # 61-bit Mersenne prime for 2-universal hashing
    MERSENNE_PRIME_61: int = (1 << 61) - 1

    def __init__(
        self,
        width: int = 1024,
        depth: int = 4,
        stash_capacity: int = 128,
        elephant_threshold: int = 16,
        seed: int = 42,
    ) -> None:
        """
        Initialize AdaLog-Sketch.

        Args:
            width: Number of counter buckets per row (w > 0).
            depth: Number of hash rows (d > 0).
            stash_capacity: Max items tracked in high-precision elephant stash.
            elephant_threshold: Frequency threshold to promote item to elephant stash.
            seed: Random seed for hash functions.
        """
        if width <= 0:
            raise ValueError(f"width must be positive, got {width}")
        if depth <= 0:
            raise ValueError(f"depth must be positive, got {depth}")
        if stash_capacity <= 0:
            raise ValueError(f"stash_capacity must be positive, got {stash_capacity}")
        if elephant_threshold <= 0:
            raise ValueError(f"elephant_threshold must be positive, got {elephant_threshold}")

        self.width: int = width
        self.depth: int = depth
        self.stash_capacity: int = stash_capacity
        self.elephant_threshold: int = elephant_threshold
        self.seed: int = seed

        # Tier 1: Base Count-Min matrix (32-bit unsigned integers for fast vector ops)
        self.table: np.ndarray = np.zeros((self.depth, self.width), dtype=np.uint32)

        # Integrated Cardinality: 1D array of HLL registers across columns (width registers)
        # Each register stores max leading zeros rho(w) of items hashing to that column
        self.hll_registers: bytearray = bytearray(self.width)

        # Tier 2: Heavy-Hitter Elephant Stash (Exact frequency tracking for heavy flows)
        # Isolates elephants from contaminating the base table, solving the Zipfian skew problem
        self.elephant_stash: Dict[Any, int] = {}

        # Stream statistics
        self.total_volume: int = 0
        self.total_updates: int = 0

        # Precompute 2-universal hash coefficients
        import random
        rng = random.Random(seed)
        self._hash_a: List[int] = [
            rng.randint(1, self.MERSENNE_PRIME_61 - 1) for _ in range(self.depth)
        ]
        self._hash_b: List[int] = [
            rng.randint(0, self.MERSENNE_PRIME_61 - 1) for _ in range(self.depth)
        ]

    def _hash_item_64(self, item: Any) -> int:
        """Hash item to 64-bit integer using BLAKE2b."""
        if isinstance(item, bytes):
            data = item
        elif isinstance(item, str):
            data = item.encode("utf-8")
        else:
            data = str(item).encode("utf-8")
        digest = hashlib.blake2b(data, digest_size=8).digest()
        (val,) = struct.unpack("<Q", digest)
        return val

    def _get_indices(self, h64: int) -> List[int]:
        """Compute row bucket indices for an item hash."""
        indices = []
        for j in range(self.depth):
            idx = ((self._hash_a[j] * h64 + self._hash_b[j]) % self.MERSENNE_PRIME_61) % self.width
            indices.append(idx)
        return indices

    @staticmethod
    def _rho(w: int, max_bits: int = 64) -> int:
        """Count leading zeros + 1."""
        if w == 0:
            return max_bits
        return max_bits - w.bit_length() + 1

    def update(self, item: Any, count: int = 1) -> None:
        """
        Insert/update an item with frequency increment.
        Applies:
          1. Elephant Stash bypass for known heavy-hitters.
          2. Conservative Update (CU) on Base Table.
          3. Dynamic Elephant Promotion.
          4. Integrated HLL register update for cardinality.
        """
        if count <= 0:
            raise ValueError(f"Increment count must be positive, got {count}")

        self.total_volume += count
        self.total_updates += 1

        # Check if already in Elephant Stash
        if item in self.elephant_stash:
            self.elephant_stash[item] += count
            return

        h64 = self._hash_item_64(item)
        indices = self._get_indices(h64)

        # 1. Update HLL register for cardinality (using primary column index)
        col0 = indices[0]
        # Use secondary hash bits for leading-zero estimation
        sub_hash = (h64 ^ 0x5555555555555555) & 0xFFFFFFFFFFFFFFFF
        lead_zeros = self._rho(sub_hash, 64)
        if lead_zeros > self.hll_registers[col0]:
            self.hll_registers[col0] = lead_zeros

        # 2. Conservative Update (CU) on Base Table:
        # Only increment counters that match the current minimum across rows.
        # This significantly dampens collision noise compared to standard CMS.
        current_vals = [self.table[j, indices[j]] for j in range(self.depth)]
        min_val = min(current_vals)
        new_val = min_val + count

        for j in range(self.depth):
            if self.table[j, indices[j]] == min_val:
                self.table[j, indices[j]] = new_val

        # 3. Dynamic Promotion to Elephant Stash
        if new_val >= self.elephant_threshold:
            if len(self.elephant_stash) < self.stash_capacity:
                self.elephant_stash[item] = new_val
            else:
                # Stash is full: find minimum entry (Space-Saving style replacement)
                min_stash_item, min_stash_count = min(
                    self.elephant_stash.items(), key=lambda kv: kv[1]
                )
                if new_val > min_stash_count:
                    # Write-back evicted count to base table to maintain no-underestimation invariant
                    h64_evicted = self._hash_item_64(min_stash_item)
                    evicted_indices = self._get_indices(h64_evicted)
                    for j in range(self.depth):
                        if min_stash_count > self.table[j, evicted_indices[j]]:
                            self.table[j, evicted_indices[j]] = min_stash_count

                    del self.elephant_stash[min_stash_item]
                    self.elephant_stash[item] = new_val

    def update_many(self, items: Iterable[Any]) -> None:
        """Batch update items with increment 1."""
        for item in items:
            self.update(item, 1)

    def query(self, item: Any) -> int:
        """
        Estimate point frequency of an item.
        Guarantees:
          - No underestimation: query(item) >= true_count
          - Tight error bound via Conservative Update and Elephant Stash isolation.
        """
        # If present in elephant stash, return the high-precision tracked count
        if item in self.elephant_stash:
            return self.elephant_stash[item]

        h64 = self._hash_item_64(item)
        indices = self._get_indices(h64)

        # Base table point query: minimum across rows
        min_val = min(int(self.table[j, indices[j]]) for j in range(self.depth))
        return min_val

    def __contains__(self, item: Any) -> bool:
        """Approximate Set Membership (AMQ): Returns True if query(item) > 0."""
        return self.query(item) > 0

    def cardinality(self) -> int:
        """
        Estimate distinct elements in the stream using integrated HLL registers
        across width columns via Flajolet harmonic mean.
        """
        m = self.width
        # Flajolet alpha_m bias correction
        if m >= 128:
            alpha = 0.7213 / (1.0 + 1.079 / m)
        elif m >= 64:
            alpha = 0.709
        elif m >= 32:
            alpha = 0.697
        else:
            alpha = 0.673

        # Harmonic mean of 2^(-R[j])
        sum_harmonic = sum(2.0 ** (-reg) for reg in self.hll_registers)
        if sum_harmonic == 0.0:
            return 0

        raw_estimate = alpha * (m ** 2) / sum_harmonic

        # Linear counting correction for small cardinalities
        zeros = self.hll_registers.count(0)
        if zeros > 0 and raw_estimate <= 2.5 * m:
            linear_count = m * math.log(m / zeros)
            return round(linear_count)

        return round(raw_estimate)

    def heavy_hitters(self, min_freq: Optional[int] = None) -> List[Tuple[Any, int]]:
        """
        Enumerate all heavy hitters without scanning the universe.
        Returns sorted list of (item, frequency) descending.
        """
        threshold = min_freq if min_freq is not None else self.elephant_threshold
        results = [
            (item, count)
            for item, count in self.elephant_stash.items()
            if count >= threshold
        ]
        results.sort(key=lambda kv: kv[1], reverse=True)
        return results

    def decay(self, factor: float = 0.5) -> None:
        """
        Time-decay / sliding-window operation.
        Multiplies base counters and stash counts by decay factor (0 < factor < 1).
        Mitigates counter saturation in continuous long-running streams.
        """
        if not (0.0 < factor < 1.0):
            raise ValueError(f"Decay factor must be in (0, 1), got {factor}")

        # Decay base table
        self.table = (self.table * factor).astype(np.uint32)

        # Decay elephant stash
        decayed_stash: Dict[Any, int] = {}
        for item, count in self.elephant_stash.items():
            new_count = int(count * factor)
            if new_count >= (self.elephant_threshold // 2):
                decayed_stash[item] = new_count
        self.elephant_stash = decayed_stash
        self.total_volume = int(self.total_volume * factor)

    def compress_lightranger(self, group_size: int = 8) -> bytes:
        """
        LightRanger Compression (Yu et al., IWQoS 2026).
        Applies Equal Element Grouping (EEG) and Base-Bit Reduction (BBR):
          1. Partitions each row of counters into groups of size group_size.
          2. Extracts group baseline v_min = min(group).
          3. Computes deltas Delta_i = c_i - v_min.
          4. Encodes baseline and variable-width deltas into compact bytes.
        """
        buf = io.BytesIO()

        # Header: depth, width, group_size
        buf.write(struct.pack("<III", self.depth, self.width, group_size))

        for j in range(self.depth):
            row = self.table[j]
            num_groups = (self.width + group_size - 1) // group_size

            for g in range(num_groups):
                start = g * group_size
                end = min(start + group_size, self.width)
                group = row[start:end]

                v_min = int(np.min(group))
                deltas = [int(v - v_min) for v in group]
                max_delta = max(deltas) if deltas else 0

                # Determine minimal bits needed for max_delta
                bit_width = max(1, max_delta.bit_length()) if max_delta > 0 else 0

                # Pack: v_min (4 bytes), bit_width (1 byte), actual group size (1 byte)
                buf.write(struct.pack("<IBB", v_min, bit_width, len(group)))

                # Pack deltas if bit_width > 0
                if bit_width > 0:
                    bit_buffer = 0
                    bits_in_buffer = 0
                    for delta in deltas:
                        bit_buffer = (bit_buffer << bit_width) | delta
                        bits_in_buffer += bit_width
                        while bits_in_buffer >= 8:
                            bits_in_buffer -= 8
                            byte_val = (bit_buffer >> bits_in_buffer) & 0xFF
                            buf.write(struct.pack("B", byte_val))
                    if bits_in_buffer > 0:
                        byte_val = (bit_buffer << (8 - bits_in_buffer)) & 0xFF
                        buf.write(struct.pack("B", byte_val))

        return buf.getvalue()

    @classmethod
    def decompress_lightranger(cls, data: bytes) -> Tuple[int, int, np.ndarray]:
        """
        Decompress a LightRanger compressed byte string back to counter table.
        Returns (depth, width, table).
        """
        buf = io.BytesIO(data)
        depth, width, group_size = struct.unpack("<III", buf.read(12))

        table = np.zeros((depth, width), dtype=np.uint32)

        for j in range(depth):
            col_idx = 0
            while col_idx < width:
                header = buf.read(6)
                if not header:
                    break
                v_min, bit_width, actual_len = struct.unpack("<IBB", header)

                if bit_width == 0:
                    table[j, col_idx : col_idx + actual_len] = v_min
                    col_idx += actual_len
                else:
                    # Read packed bits
                    total_bits = bit_width * actual_len
                    num_bytes = (total_bits + 7) // 8
                    raw_bytes = buf.read(num_bytes)

                    bit_buffer = 0
                    bits_in_buffer = 0
                    byte_offset = 0

                    for _ in range(actual_len):
                        while bits_in_buffer < bit_width and byte_offset < len(raw_bytes):
                            bit_buffer = (bit_buffer << 8) | raw_bytes[byte_offset]
                            byte_offset += 1
                            bits_in_buffer += 8

                        bits_in_buffer -= bit_width
                        delta = (bit_buffer >> bits_in_buffer) & ((1 << bit_width) - 1)
                        table[j, col_idx] = v_min + delta
                        col_idx += 1

        return depth, width, table

    def memory_usage_bytes(self) -> int:
        """
        Calculate total memory consumption in bytes:
          Base Table (uint32) + HLL Registers + Elephant Stash + Object overhead.
        """
        table_bytes = self.table.nbytes
        hll_bytes = len(self.hll_registers)
        # Dictionary overhead: approximate 32 bytes per key/value entry + container
        stash_bytes = sys.getsizeof(self.elephant_stash) + len(self.elephant_stash) * 32
        hash_params_bytes = len(self._hash_a) * 8 + len(self._hash_b) * 8
        return table_bytes + hll_bytes + stash_bytes + hash_params_bytes + 128

    def compute_metrics(
        self, true_frequencies: Dict[Any, int], true_cardinality: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Evaluate accuracy metrics across ground truth:
          MAE, RMSE, Max Overestimation, ARE (Average Relative Error),
          and Cardinality Error.
        """
        errors = []
        rel_errors = []
        underestimations = 0

        for item, true_f in true_frequencies.items():
            est_f = int(self.query(item))
            err = int(est_f) - int(true_f)
            if err < 0:
                underestimations += 1
            errors.append(err)
            rel_errors.append(err / max(1, true_f))

        err_arr = np.array(errors, dtype=np.float64)
        rel_arr = np.array(rel_errors, dtype=np.float64)

        card_err_rel = 0.0
        if true_cardinality is not None and true_cardinality > 0:
            est_c = self.cardinality()
            card_err_rel = abs(est_c - true_cardinality) / true_cardinality

        return {
            "mae": float(np.mean(err_arr)),
            "rmse": float(math.sqrt(np.mean(err_arr ** 2))),
            "are": float(np.mean(rel_arr)),
            "max_overestimation": float(np.max(err_arr)),
            "underestimations": float(underestimations),
            "cardinality_relative_error": float(card_err_rel),
        }
