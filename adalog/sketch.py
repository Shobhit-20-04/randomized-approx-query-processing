"""
AdaLog-Sketch Unified Data Structure.
Integrates Membership (AMQ), Frequency (CMS-CU), Cardinality (HLL), and Heavy Hitters
into a single shared memory block and single 128-bit hash pipeline per item.
All modules are fully switchable for systematic ablation testing.
"""

from __future__ import annotations
import math
from typing import Optional, List, Tuple, Dict
import numpy as np

from adalog.hash_utils import hash128, get_matrix_indices, get_hll_index_and_rank
from adalog.stash import ElephantStash
from adalog.hll_packed import PackedHLLRegisters
from adalog.compression import compress_matrix, decompress_matrix


class AdaLogSketch:
    def __init__(
        self,
        width: Optional[int] = None,
        depth: Optional[int] = None,
        w: Optional[int] = None,
        d: Optional[int] = None,
        counter_bits: int = 8,                 # 8, 16, or 32
        use_stash: bool = True,                # Switchable ablation
        stash_capacity: int = 64,
        elephant_threshold: Optional[int] = None, # tau < counter saturation
        stash_tau: Optional[int] = None,
        use_conservative_update: bool = True,  # Switchable ablation
        membership_variant: str = "A",         # "A" (shared counters > 0) or "B" (1-bit presence plane)
        hll_layout: str = "coupled",           # "coupled" (m = w) or "decoupled" (m = 2^p)
        hll_p: int = 10,                       # used if decoupled
        m: Optional[int] = None,
        seed: int = 42,
    ):
        self.width = int(w if w is not None else (width if width is not None else 1024))
        self.depth = int(d if d is not None else (depth if depth is not None else 4))
        self.w = self.width
        self.d = self.depth
        self.counter_bits = counter_bits
        self.use_stash = use_stash
        self.use_conservative_update = use_conservative_update
        self.membership_variant = membership_variant.upper()
        self.hll_layout = hll_layout.lower()
        if m is not None:
            self.hll_layout = "decoupled"
            self.hll_p = max(4, int(math.ceil(math.log2(m))))
        else:
            self.hll_p = hll_p
        self.seed = seed
        self.total_volume = 0

        thresh = stash_tau if stash_tau is not None else (elephant_threshold if elephant_threshold is not None else 20)

        # Saturation value based on counter width
        if counter_bits == 8:
            self.dtype = np.uint8
            self.max_val = 255
        elif counter_bits == 16:
            self.dtype = np.uint16
            self.max_val = 65535
        elif counter_bits == 32:
            self.dtype = np.uint32
            self.max_val = 4294967295
        else:
            raise ValueError("counter_bits must be 8, 16, or 32")

        # 1. Base Counter Matrix
        self.table = np.zeros((self.depth, self.width), dtype=self.dtype)
        self.matrix = self.table

        # 2. Membership Plane (if Variant B)
        if self.membership_variant == "B":
            # 1-bit per column in a dedicated bit-plane of width w
            self.presence_bytes = (self.width + 7) // 8
            self.presence_plane = bytearray(self.presence_bytes)
        else:
            self.presence_plane = None

        # 3. HLL Registers (6-bit packed)
        if self.hll_layout == "coupled":
            self.hll_m = self.width
            self.hll_p_eff = int(math.ceil(math.log2(self.width)))
        else:
            self.hll_m = 1 << self.hll_p
            self.hll_p_eff = self.hll_p

        self.hll_registers = PackedHLLRegisters(self.hll_m)

        # 4. Elephant Stash
        if self.use_stash:
            # tau must stay strictly below saturation threshold
            safe_tau = min(thresh, self.max_val - 1)
            self.stash = ElephantStash(capacity=stash_capacity, threshold=safe_tau, max_counter_val=self.max_val)
        else:
            self.stash = None

    def update(self, key: str | bytes, count: int = 1) -> None:
        if count <= 0:
            return
        self.total_volume += count
        str_key = key if isinstance(key, str) else key.decode("utf-8", "replace")

        # FAST PATH: Stash hit
        if self.use_stash and self.stash.update_if_present(str_key, count):
            return

        # Single 128-bit hash computation
        h_low, h_high = hash128(key, seed=self.seed)

        # 1. Derive d matrix row indices via Kirsch-Mitzenmacher
        indices = get_matrix_indices(h_low, self.depth, self.width)

        # 2. Update HLL registers from high hash bits
        if self.hll_layout == "coupled":
            # Primary column idx_0 selects HLL register
            reg_idx = indices[0] % self.hll_m
            # Leading zeros from remaining hash bits
            _, rank = get_hll_index_and_rank(h_high, 0)
            self.hll_registers.update_register(reg_idx, rank)
        else:
            reg_idx, rank = get_hll_index_and_rank(h_high, self.hll_p_eff)
            self.hll_registers.update_register(reg_idx, rank)

        # 3. Update Membership plane (Variant B only)
        if self.membership_variant == "B":
            for idx in indices:
                self.presence_plane[idx >> 3] |= (1 << (idx & 7))

        # 4. Update Counter Matrix (Conservative Update or Standard)
        if self.use_conservative_update:
            v_min = min(int(self.table[j, indices[j]]) for j in range(self.depth))
            v_new = min(self.max_val, v_min + count)
            for j in range(self.depth):
                if int(self.table[j, indices[j]]) == v_min:
                    self.table[j, indices[j]] = v_new
            est_after = v_new
        else:
            for j in range(self.depth):
                cur = int(self.table[j, indices[j]])
                self.table[j, indices[j]] = min(self.max_val, cur + count)
            est_after = min(int(self.table[j, indices[j]]) for j in range(self.depth))

        # 5. Check Stash Promotion
        if self.use_stash and est_after >= self.stash.threshold:
            eviction = self.stash.promote(str_key, est_after)
            if eviction is not None:
                evict_key, evict_count = eviction
                # Write-back into base table with max()
                h_evict_low, _ = hash128(evict_key, seed=self.seed)
                evict_indices = get_matrix_indices(h_evict_low, self.depth, self.width)
                bounded_evict = min(self.max_val, evict_count)
                for j in range(self.depth):
                    cur_val = int(self.table[j, evict_indices[j]])
                    if bounded_evict > cur_val:
                        self.table[j, evict_indices[j]] = bounded_evict

    def update_many(self, keys, count: int = 1) -> None:
        for k in keys:
            self.update(k, count)

    def contains(self, key: str | bytes) -> bool:
        """
        Approximate Membership Query (AMQ).
        Variant A: True iff all d counters > 0 (shared counters, 0 marginal bytes).
        Variant B: True iff all d bits are set in presence plane.
        """
        str_key = key if isinstance(key, str) else key.decode("utf-8", "replace")
        if self.use_stash and self.stash.contains(str_key):
            return True

        h_low, _ = hash128(key, seed=self.seed)
        indices = get_matrix_indices(h_low, self.depth, self.width)

        if self.membership_variant == "B":
            for idx in indices:
                if not (self.presence_plane[idx >> 3] & (1 << (idx & 7))):
                    return False
            return True
        else:
            # Variant A: counting-Bloom style check on base matrix
            for j in range(self.depth):
                if self.table[j, indices[j]] == 0:
                    return False
            return True

    def __contains__(self, key: str | bytes) -> bool:
        return self.contains(key)

    def estimate(self, key: str | bytes) -> int:
        """
        Point Frequency Query.
        Never underestimates true count (Theorem 2).
        """
        str_key = key if isinstance(key, str) else key.decode("utf-8", "replace")
        if self.use_stash:
            stash_val = self.stash.get_count(str_key)
            if stash_val is not None:
                return stash_val

        h_low, _ = hash128(key, seed=self.seed)
        indices = get_matrix_indices(h_low, self.depth, self.width)
        return min(int(self.table[j, indices[j]]) for j in range(self.depth))

    def query(self, key: str | bytes) -> int:
        return self.estimate(key)

    def cardinality(self) -> float:
        """
        Distinct Cardinality Query via 6-bit packed HLL registers.
        """
        return self.hll_registers.estimate_cardinality()

    def top_k(self, k: int = 10) -> list[tuple[str, int]]:
        """
        Heavy-Hitter Query in O(K) time without scanning universe.
        """
        if self.use_stash:
            return self.stash.top_k(k)
        return []

    def memory_usage_bytes(self) -> int:
        """
        Returns exact in-memory RAM usage (matrix + stash + HLL registers + presence plane).
        """
        total = self.table.nbytes
        total += self.hll_registers.memory_usage_bytes()
        if self.use_stash:
            total += self.stash.memory_usage_bytes()
        if self.membership_variant == "B":
            total += len(self.presence_plane)
        return total

    def compress_wire(self, group_size: int = 8) -> bytes:
        """
        LightRanger wire-format compression for network/disk serialization.
        """
        return compress_matrix(self.table, group_size=group_size)

    def compute_metrics(
        self,
        ground_truth_freqs: dict[str, int],
        true_cardinality: int,
    ) -> dict[str, float]:
        """
        Computes comprehensive evaluation metrics against exact ground truth.
        """
        errors = []
        rel_errors = []
        overestimates = []
        underestimates = 0

        for key, true_f in ground_truth_freqs.items():
            est_f = self.estimate(key)
            diff = est_f - true_f
            if diff < 0:
                underestimates += 1
            errors.append(abs(diff))
            overestimates.append(max(0, diff))
            rel_errors.append(abs(diff) / max(1, true_f))

        est_card = self.cardinality()
        card_rse = abs(est_card - true_cardinality) / max(1, true_cardinality)

        return {
            "mae": float(np.mean(errors)) if errors else 0.0,
            "are": float(np.mean(rel_errors)) if rel_errors else 0.0,
            "max_overestimation": float(np.max(overestimates)) if overestimates else 0.0,
            "underestimates_count": underestimates,
            "estimated_cardinality": est_card,
            "cardinality_relative_error": card_rse,
            "memory_bytes": self.memory_usage_bytes(),
        }
