"""
Augmented Sketch (Roy, Cormode, Muthukrishnan, SIGMOD 2016).
Combines an associative pre-filter table of K entries with a Count-Min Sketch.
"""

from __future__ import annotations
import numpy as np
from baselines.count_min_sketch import CountMinSketch


class AugmentedSketch:
    def __init__(
        self,
        filter_capacity: int = 64,
        sketch_width: int = 1024,
        sketch_depth: int = 4,
        counter_bits: int = 16,
        conservative_update: bool = True,
        total_memory_bytes: int | None = None,
        seed: int = 42,
    ):
        if total_memory_bytes is not None:
            # 20% to filter table (16B per entry)
            filter_bytes = max(256, int(total_memory_bytes * 0.20))
            filter_capacity = max(16, filter_bytes // 16)
            rem_bytes = max(256, total_memory_bytes - filter_capacity * 16)
            sketch_depth = 4
            counter_bits = 16
            sketch_width = max(64, rem_bytes // (sketch_depth * 2))

        self.k_capacity = filter_capacity
        self.seed = seed
        self.filter_table: dict[str, int] = {}
        self.sketch = CountMinSketch(
            width=sketch_width,
            depth=sketch_depth,
            counter_bits=counter_bits,
            conservative_update=conservative_update,
            seed=seed,
        )

    def top_k(self, k: int = 100) -> list[tuple[str, int]]:
        return sorted(self.filter_table.items(), key=lambda kv: kv[1], reverse=True)[:k]

    def update(self, key: str, count: int = 1) -> None:
        if key in self.filter_table:
            self.filter_table[key] += count
            return

        if len(self.filter_table) < self.k_capacity:
            # Query sketch first
            sketch_val = self.sketch.query(key)
            self.filter_table[key] = sketch_val + count
            return

        # Table full: check if sketch estimate + count exceeds table minimum
        sketch_val = self.sketch.query(key)
        new_val = sketch_val + count

        min_key, min_val = min(self.filter_table.items(), key=lambda kv: kv[1])
        if new_val > min_val:
            # Evict min_key back into sketch
            self.sketch.update(min_key, min_val - self.sketch.query(min_key))
            del self.filter_table[min_key]
            self.filter_table[key] = new_val
        else:
            self.sketch.update(key, count)

    def update_many(self, keys, count: int = 1) -> None:
        for k in keys:
            self.update(k, count)

    def query(self, key: str) -> int:
        if key in self.filter_table:
            return self.filter_table[key]
        return self.sketch.query(key)

    def estimate(self, key: str) -> int:
        return self.query(key)

    def top_k(self, k: int = 10) -> list[tuple[str, int]]:
        return sorted(self.filter_table.items(), key=lambda kv: kv[1], reverse=True)[:k]

    def memory_usage_bytes(self) -> int:
        # Sketch memory + filter table entries (16 bytes key hash + 4 bytes counter per entry)
        filter_bytes = self.k_capacity * 24
        return self.sketch.memory_usage_bytes() + filter_bytes
