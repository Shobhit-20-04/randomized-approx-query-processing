"""
Disjoint Baseline Stack: SOTA Combined Reference.
Deploys optimal Bloom Filter + CMS-CU + HLL in disjoint memory partitions.
"""

from __future__ import annotations
from baselines.bloom_filter import BloomFilter
from baselines.count_min_sketch import CountMinSketch
from baselines.hyperloglog import HyperLogLog


class DisjointStack:
    def __init__(
        self,
        expected_cardinality: int = 10000,
        target_fpr: float = 0.01,
        cms_width: int = 1024,
        cms_depth: int = 4,
        cms_counter_bits: int = 32,
        hll_p: int = 10,
        total_memory_bytes: Optional[int] = None,
        seed: int = 42,
    ):
        if total_memory_bytes is not None:
            # Automatic partition under fixed budget B:
            # 20% to Bloom filter, 768 bytes to HLL (p=10), remainder to CMS (d=4, 16-bit or 8-bit)
            hll_bytes = (1024 * 6 + 7) // 8
            bf_bytes = max(128, int(total_memory_bytes * 0.20))
            cms_bytes = max(256, total_memory_bytes - bf_bytes - hll_bytes)

            self.bf = BloomFilter(
                m_bits=bf_bytes * 8,
                expected_capacity=expected_cardinality,
                seed=seed,
            )

            cms_depth = 4
            cms_width = max(64, cms_bytes // (cms_depth * 2)) # 16-bit counters (2 bytes)
            self.cms = CountMinSketch(
                width=cms_width,
                depth=cms_depth,
                counter_bits=16,
                conservative_update=True,
                seed=seed ^ 0x55555555,
            )
            self.hll = HyperLogLog(
                p=10,
                use_6bit_packing=True,
                seed=seed ^ 0xAAAAAAAA,
            )
        else:
            self.bf = BloomFilter(
                expected_capacity=expected_cardinality,
                target_fpr=target_fpr,
                seed=seed,
            )
            self.cms = CountMinSketch(
                width=cms_width,
                depth=cms_depth,
                counter_bits=cms_counter_bits,
                conservative_update=True,
                seed=seed ^ 0x55555555,
            )
            self.hll = HyperLogLog(
                p=hll_p,
                use_6bit_packing=True,
                seed=seed ^ 0xAAAAAAAA,
            )

    def top_k(self, k: int = 100):
        return []

    def update(self, key: str | bytes, count: int = 1) -> None:
        self.bf.add(key)
        self.cms.update(key, count)
        self.hll.add(key)

    def update_many(self, keys, count: int = 1) -> None:
        for k in keys:
            self.update(k, count)

    def contains(self, key: str | bytes) -> bool:
        return self.bf.contains(key)

    def estimate(self, key: str | bytes) -> int:
        return self.cms.query(key)

    def cardinality(self) -> float:
        return self.hll.cardinality()

    def memory_usage_bytes(self) -> int:
        return (
            self.bf.memory_usage_bytes()
            + self.cms.memory_usage_bytes()
            + self.hll.memory_usage_bytes()
        )


DisjointBaselineStack = DisjointStack


class DisjointStashStack:
    """
    Disjoint Stack + Elephant Stash.
    Isolates whether the performance gain of AdaLog-Sketch is from
    the heavy-hitter stash alone or from the unified memory and hashing architecture.
    """
    def __init__(
        self,
        total_memory_bytes: int = 32768,
        expected_cardinality: int = 10000,
        stash_capacity: int = 128,
        stash_tau: int = 15,
        cms_counter_bits: int = 8,
        seed: int = 42,
    ):
        from adalog.stash import ElephantStash
        self.seed = seed
        self.stash_capacity = stash_capacity
        self.stash_tau = stash_tau
        self.counter_bits = cms_counter_bits

        stash_bytes = stash_capacity * 16
        hll_bytes = 768  # 1024 registers packed at 6 bits
        rem_bytes = max(512, total_memory_bytes - stash_bytes - hll_bytes)

        # 20% to Bloom Filter
        bf_bytes = max(128, int(rem_bytes * 0.20))
        cms_bytes = max(256, rem_bytes - bf_bytes)

        self.bf = BloomFilter(
            m_bits=bf_bytes * 8,
            expected_capacity=expected_cardinality,
            seed=seed,
        )

        bytes_per_counter = 1 if cms_counter_bits == 8 else (2 if cms_counter_bits == 16 else 4)
        cms_depth = 4
        cms_width = max(64, cms_bytes // (cms_depth * bytes_per_counter))

        self.cms = CountMinSketch(
            width=cms_width,
            depth=cms_depth,
            counter_bits=cms_counter_bits,
            conservative_update=True,
            seed=seed ^ 0x55555555,
        )

        self.hll = HyperLogLog(
            p=10,
            use_6bit_packing=True,
            seed=seed ^ 0xAAAAAAAA,
        )

        self.stash = ElephantStash(
            capacity=stash_capacity,
            threshold=stash_tau,
            max_counter_val=255 if cms_counter_bits == 8 else 65535,
        )

    def update(self, key: str | bytes, count: int = 1) -> None:
        str_key = key if isinstance(key, str) else key.decode("utf-8", "replace")
        self.bf.add(str_key)
        self.hll.add(str_key)

        if self.stash.update_if_present(str_key, count):
            return

        self.cms.update(str_key, count)
        est = self.cms.query(str_key)

        if est >= self.stash_tau:
            eviction = self.stash.promote(str_key, est)
            if eviction is not None:
                evict_key, evict_count = eviction
                # Write-back into CMS
                indices = self.cms._get_indices(evict_key)
                bounded_val = min(self.cms.max_val, evict_count)
                for j in range(self.cms.depth):
                    if bounded_val > self.cms.table[j, indices[j]]:
                        self.cms.table[j, indices[j]] = bounded_val

    def update_many(self, keys, count: int = 1) -> None:
        for k in keys:
            self.update(k, count)

    def contains(self, key: str | bytes) -> bool:
        return self.bf.contains(key)

    def estimate(self, key: str | bytes) -> int:
        str_key = key if isinstance(key, str) else key.decode("utf-8", "replace")
        stash_val = self.stash.get_count(str_key)
        if stash_val is not None:
            return stash_val
        return self.cms.query(str_key)

    def cardinality(self) -> float:
        return self.hll.cardinality()

    def top_k(self, k: int = 100):
        return self.stash.top_k(k)

    def memory_usage_bytes(self) -> int:
        return (
            self.bf.memory_usage_bytes()
            + self.cms.memory_usage_bytes()
            + self.hll.memory_usage_bytes()
            + self.stash.memory_usage_bytes()
        )

