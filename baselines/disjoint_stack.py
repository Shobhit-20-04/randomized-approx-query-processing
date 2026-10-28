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
