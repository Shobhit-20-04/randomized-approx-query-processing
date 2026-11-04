"""Experiment 8: Wire-Format Compression Benchmark.

Evaluates LightRanger compression (Equal Element Grouping + Base-Bit Reduction):
- Compresses AdaLog-Sketch matrix into serialized wire format.
- Strictly separates in-memory RAM size from wire transmission size.
- Verifies bit-exact lossless roundtrip reconstruction.
- Records compression ratio (%), serialization time, and deserialization time.

Outputs results to results/raw/exp8_compression.json
"""

import json
import os
import time
from typing import List
import numpy as np

from adalog.sketch import AdaLogSketch
from adalog.compression import compress_matrix, decompress_matrix
from experiments.datasets import generate_zipf_stream


def run_compression_benchmark(
    budgets_kb: List[int] = [16, 32, 64, 128, 256],
    alpha: float = 1.25,
    n_stream: int = 300_000,
    n_unique: int = 30_000,
    seed: int = 42,
    output_path: str = "results/raw/exp8_compression.json",
):
    print("================================================================================")
    print("EXPERIMENT 8: LIGHTRANGER WIRE-FORMAT COMPRESSION BENCHMARK")
    print("================================================================================")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    stream, _ = generate_zipf_stream(n_stream=n_stream, n_unique=n_unique, alpha=alpha, seed=seed)
    results = []

    for b_kb in budgets_kb:
        total_bytes = b_kb * 1024
        d = 4
        w = max(64, (total_bytes - 2048) // d)

        sketch = AdaLogSketch(d=d, w=w, counter_bits=8, m=1024, stash_capacity=64, seed=seed)
        for x in stream:
            sketch.update(x)

        raw_bytes = sketch.table.nbytes
        t0 = time.perf_counter()
        compressed_bytes = compress_matrix(sketch.table, group_size=8)
        t1 = time.perf_counter()
        comp_time_ms = (t1 - t0) * 1000.0

        t0 = time.perf_counter()
        decomp_table = decompress_matrix(compressed_bytes)
        t1 = time.perf_counter()
        decomp_time_ms = (t1 - t0) * 1000.0

        # Verify bit-exact lossless roundtrip
        is_exact = np.array_equal(sketch.table, decomp_table)
        assert is_exact, "Lossless compression check failed!"

        compressed_len = len(compressed_bytes)
        ratio_pct = (1.0 - (compressed_len / float(raw_bytes))) * 100.0

        row = {
            "budget_kb": b_kb,
            "raw_bytes": raw_bytes,
            "compressed_bytes": compressed_len,
            "compression_ratio_pct": ratio_pct,
            "compression_time_ms": comp_time_ms,
            "decompression_time_ms": decomp_time_ms,
            "lossless_verified": is_exact,
        }
        results.append(row)
        print(f"  {b_kb:3d} KB Matrix: {raw_bytes:,} B -> {compressed_len:,} B | Reduction: {ratio_pct:5.1f}% | Pack: {comp_time_ms:5.2f}ms | Unpack: {decomp_time_ms:5.2f}ms")

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nExperiment 8 complete. Results saved to {output_path}")
    return results


if __name__ == "__main__":
    run_compression_benchmark()
