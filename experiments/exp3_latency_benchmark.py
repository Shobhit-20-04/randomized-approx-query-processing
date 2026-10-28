"""Experiment 3: Compiled C++ Latency and Throughput Benchmark.

Measures headline ingestion latency (ns/op), throughput (Mops/s), and query latency (ns/op)
using the native compiled C++ engine (core/adalog_core.dll).
Runs across multiple trials with warm-up to ensure CPU caches are primed.

Compares:
1. AdaLog-Core (Unified: Single 128-bit hash pipeline updating Matrix + HLL + Stash)
2. Disjoint-Core (Running separate BF + CMS + HLL pipelines)
3. CMS-Core (Standalone Count-Min Sketch)
4. Bloom-Core (Standalone Bloom Filter)
5. HLL-Core (Standalone HyperLogLog)

Outputs results to results/raw/exp3_latency_benchmark.json
"""

import json
import os
import time
from typing import Dict, List
import numpy as np

from core.bindings import (
    CompiledAdaLog,
    CompiledDisjoint,
    CompiledCMS,
    CompiledBloom,
    CompiledHLL,
)


def run_latency_benchmark(
    n_ops: int = 1_000_000,
    n_trials: int = 5,
    seed: int = 42,
    output_path: str = "results/raw/exp3_latency_benchmark.json",
):
    print("================================================================================")
    print(f"EXPERIMENT 3: NATIVE COMPILED C++ LATENCY & THROUGHPUT BENCHMARK ({n_ops:,} ops)")
    print("================================================================================")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Pre-generate stream keys as UTF-8 encoded bytes for clean measurement
    print("Pre-generating dataset in memory...")
    keys = [f"item_key_{i % 50000}_{seed}".encode("utf-8") for i in range(n_ops)]
    query_keys = [f"item_key_{i % 50000}_{seed}".encode("utf-8") for i in range(100_000)]

    def benchmark_system(name: str, create_fn, update_fn) -> Dict:
        print(f"\nBenchmarking {name} across {n_trials} trials...")
        # Warm-up run
        obj = create_fn()
        for k in keys[:50_000]:
            update_fn(obj, k)
        del obj

        throughputs = []
        latencies_ns = []

        for trial in range(n_trials):
            obj = create_fn()
            t0 = time.perf_counter()
            for k in keys:
                update_fn(obj, k)
            t1 = time.perf_counter()
            elapsed = t1 - t0

            mops = (n_ops / elapsed) / 1e6
            ns_op = (elapsed / n_ops) * 1e9
            throughputs.append(mops)
            latencies_ns.append(ns_op)
            print(f"  Trial {trial+1}: {mops:6.2f} Mops/s | {ns_op:6.1f} ns/op ({elapsed*1000:6.1f} ms)")
            del obj

        mean_mops = float(np.mean(throughputs))
        mean_ns = float(np.mean(latencies_ns))
        p50_ns = float(np.percentile(latencies_ns, 50))
        p99_ns = float(np.percentile(latencies_ns, 99))
        print(f"  -> {name} Average: {mean_mops:.2f} Mops/s | {mean_ns:.1f} ns/op")

        return {
            "name": name,
            "mean_mops": mean_mops,
            "mean_ns_op": mean_ns,
            "p50_ns_op": p50_ns,
            "p99_ns_op": p99_ns,
            "raw_latencies_ns": latencies_ns,
            "raw_throughputs_mops": throughputs,
        }

    results = {}

    # 1. Compiled AdaLog
    results["AdaLog-Core"] = benchmark_system(
        "AdaLog-Core (Unified: Matrix+HLL+Stash)",
        lambda: CompiledAdaLog(width=2048, depth=4, counter_bits=8, stash_capacity=64, elephant_threshold=20),
        lambda obj, k: obj.update(k),
    )

    # 2. Compiled Disjoint Stack
    results["Disjoint-Core"] = benchmark_system(
        "Disjoint-Core (Stack: BF+CMS+HLL)",
        lambda: CompiledDisjoint(bf_m=16384, bf_k=7, cms_w=2048, cms_d=4, hll_p=10),
        lambda obj, k: obj.update(k),
    )

    # 3. Standalone CMS
    results["CMS-Core"] = benchmark_system(
        "CMS-Core (Standalone CMS-CU)",
        lambda: CompiledCMS(width=2048, depth=4),
        lambda obj, k: obj.update(k),
    )

    # 4. Standalone Bloom Filter
    results["Bloom-Core"] = benchmark_system(
        "Bloom-Core (Standalone Bloom)",
        lambda: CompiledBloom(m_bits=16384, k_hashes=7),
        lambda obj, k: obj.add(k),
    )

    # 5. Standalone HyperLogLog
    results["HLL-Core"] = benchmark_system(
        "HLL-Core (Standalone HLL)",
        lambda: CompiledHLL(p=10),
        lambda obj, k: obj.add(k),
    )

    # Query Latency Benchmark on AdaLog
    print("\nBenchmarking AdaLog Query Latencies (100,000 queries)...")
    adalog_query = CompiledAdaLog(width=2048, depth=4, counter_bits=8, stash_capacity=64, elephant_threshold=20)
    for k in keys[:100_000]:
        adalog_query.update(k)

    # Point query
    t0 = time.perf_counter()
    for qk in query_keys:
        adalog_query.estimate(qk)
    t1 = time.perf_counter()
    query_est_ns = ((t1 - t0) / len(query_keys)) * 1e9

    # Membership query
    t0 = time.perf_counter()
    for qk in query_keys:
        adalog_query.contains(qk)
    t1 = time.perf_counter()
    query_mem_ns = ((t1 - t0) / len(query_keys)) * 1e9

    print(f"  Point Query estimate():    {query_est_ns:.1f} ns/op")
    print(f"  Membership contains():     {query_mem_ns:.1f} ns/op")

    results["query_latencies"] = {
        "estimate_ns_op": query_est_ns,
        "contains_ns_op": query_mem_ns,
    }

    # Speedup calculation
    adalog_mops = results["AdaLog-Core"]["mean_mops"]
    disjoint_mops = results["Disjoint-Core"]["mean_mops"]
    speedup = adalog_mops / disjoint_mops
    latency_reduction = (1.0 - (results["AdaLog-Core"]["mean_ns_op"] / results["Disjoint-Core"]["mean_ns_op"])) * 100.0

    print(f"\nHEADLINE RESULT: AdaLog-Core achieves {speedup:.2f}x throughput speedup")
    print(f"                 ({latency_reduction:.1f}% latency reduction) vs Disjoint Stack!")

    results["summary"] = {
        "speedup_vs_disjoint": speedup,
        "latency_reduction_pct": latency_reduction,
    }

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nExperiment 3 complete. Results saved to {output_path}")
    return results


if __name__ == "__main__":
    run_latency_benchmark()
