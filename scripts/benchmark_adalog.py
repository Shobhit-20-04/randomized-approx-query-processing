"""
Empirical Benchmark: AdaLog-Sketch vs. Standard CMS, Bloom Filter, and HyperLogLog.
Demonstrates superior error bounds on heavy-tailed (Zipfian) data streams,
multi-functional query unification, and LightRanger compression efficiency.
"""

import collections
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import numpy as np
import pandas as pd

from approx_query.bloom_filter import BloomFilter
from approx_query.count_min_sketch import CountMinSketch
from approx_query.hyperloglog import HyperLogLog
from approx_query.adalog_sketch import AdaLogSketch
from approx_query.datasets import create_benchmark_dataset


def run_comparison(stream_size: int = 50000, zipf_alpha: float = 1.25):
    print(f"\n=================================================================")
    print(f" EXPERIMENTAL BENCHMARK: AdaLog-Sketch vs. Classical Baselines")
    print(f" Stream Size: {stream_size:,} | Distribution: Zipfian (alpha={zipf_alpha})")
    print(f"=================================================================\n")

    # 1. Generate heavy-tailed streaming dataset
    dataset = create_benchmark_dataset(
        distribution="zipfian", stream_size=stream_size, seed=42, zipf_alpha=zipf_alpha
    )
    stream = dataset.stream
    true_counts = dataset.true_frequencies
    true_cardinality = dataset.true_cardinality
    absent_keys = dataset.absent_queries

    print(f"Dataset generated:")
    print(f"  - Total Stream Items (N): {len(stream):,}")
    print(f"  - True Distinct Cardinality: {true_cardinality:,}")
    top_10 = sorted(true_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    print(f"  - Top 5 Elephants: {top_10}\n")

    # 2. Benchmark Standard Count-Min Sketch (CMS)
    t0 = time.perf_counter_ns()
    cms = CountMinSketch(epsilon=0.01, delta=0.01, width=1024, depth=4, seed=42)
    cms.update_many(stream)
    cms_insert_ms = (time.perf_counter_ns() - t0) / 1e6
    cms_mem = cms.memory_usage_bytes()
    cms_errors = cms.compute_errors(true_counts)
    cms_are = float(np.mean([max(0, cms.query(k) - true_counts[k]) / max(1, true_counts[k]) for k in true_counts]))

    # 3. Benchmark Standard HyperLogLog (p=10, 1024 registers)
    t0 = time.perf_counter_ns()
    hll = HyperLogLog(p=10)
    for item in stream:
        hll.add(item)
    hll_insert_ms = (time.perf_counter_ns() - t0) / 1e6
    hll_mem = hll.memory_usage_bytes()
    hll_card = hll.estimate()
    hll_card_err = abs(hll_card - true_cardinality) / true_cardinality

    # 4. Benchmark Standard Bloom Filter (target_fpr=0.01)
    t0 = time.perf_counter_ns()
    bf = BloomFilter(expected_capacity=true_cardinality, target_fpr=0.01)
    bf.add_many(true_counts.keys())
    bf_insert_ms = (time.perf_counter_ns() - t0) / 1e6
    bf_mem = bf.memory_usage_bytes()
    bf_fp = sum(1 for k in absent_keys if k in bf)
    bf_fpr = bf_fp / len(absent_keys)

    # 5. Benchmark Proposed AdaLog-Sketch
    t0 = time.perf_counter_ns()
    adalog = AdaLogSketch(
        width=1024, depth=4, stash_capacity=128, elephant_threshold=20, seed=42
    )
    adalog.update_many(stream)
    adalog_insert_ms = (time.perf_counter_ns() - t0) / 1e6
    adalog_mem = adalog.memory_usage_bytes()
    adalog_metrics = adalog.compute_metrics(true_counts, true_cardinality)

    # LightRanger Compression benchmark
    t_comp_0 = time.perf_counter_ns()
    compressed_bytes = adalog.compress_lightranger(group_size=8)
    comp_latency_ms = (time.perf_counter_ns() - t_comp_0) / 1e6
    raw_matrix_bytes = adalog.table.nbytes
    comp_bytes = len(compressed_bytes)
    comp_ratio = (1.0 - (comp_bytes / raw_matrix_bytes)) * 100.0

    # Membership accuracy on absent keys
    adalog_fp = sum(1 for k in absent_keys if k in adalog)
    adalog_fpr = adalog_fp / len(absent_keys)

    print("---------------------------------------------------------------------------------------------------------")
    print(f"| Metric / Capability                | Standard CMS     | HyperLogLog (HLL) | Bloom Filter    | AdaLog-Sketch (Novel) |")
    print("---------------------------------------------------------------------------------------------------------")
    print(f"| Supported Functions                | Frequency Only   | Cardinality Only  | Membership Only | ALL 4 SIMULTANEOUSLY  |")
    print(f"| Memory Consumption                 | {cms_mem:>10,} B   | {hll_mem:>11,} B   | {bf_mem:>9,} B   | {adalog_mem:>15,} B   |")
    print(f"| Insertion Latency (Total)          | {cms_insert_ms:>10.2f} ms  | {hll_insert_ms:>11.2f} ms  | {bf_insert_ms:>9.2f} ms  | {adalog_insert_ms:>15.2f} ms  |")
    print(f"| Frequency Mean Abs. Error (MAE)    | {cms_errors['mae']:>14.2f}   |              N/A  |             N/A | {adalog_metrics['mae']:>19.2f}   |")
    print(f"| Frequency Avg. Rel. Error (ARE)    | {cms_are:>14.4f}   |              N/A  |             N/A | {adalog_metrics['are']:>19.4f}   |")
    print(f"| Max Overestimation Peak            | {cms_errors['max_overestimation']:>14,}   |              N/A  |             N/A | {adalog_metrics['max_overestimation']:>19.0f}   |")
    print(f"| Cardinality Rel. Error             |              N/A | {hll_card_err*100:>13.2f}%  |             N/A | {adalog_metrics['cardinality_relative_error']*100:>18.2f}%  |")
    print(f"| False Positive Rate (Absent Keys)  |              N/A |              N/A  | {bf_fpr*100:>11.2f}%  | {adalog_fpr*100:>17.2f}%  |")
    print("---------------------------------------------------------------------------------------------------------")
    print(f"\nLightRanger Sketch Compression on AdaLog-Sketch:")
    print(f"  - Raw Counter Matrix: {raw_matrix_bytes:,} bytes")
    print(f"  - LightRanger Compressed: {comp_bytes:,} bytes")
    print(f"  - Telemetry Bandwidth Savings: {comp_ratio:.2f}% reduction")
    print(f"  - Compression Latency: {comp_latency_ms:.3f} ms\n")

    print(f"Heavy Hitters Extracted by AdaLog-Sketch in O(1) time without universe scan:")
    for rank, (item, count) in enumerate(adalog.heavy_hitters()[:5], 1):
        true_f = true_counts.get(item, 0)
        print(f"  #{rank}: {item} -> Estimated: {count:,} | Ground Truth: {true_f:,} (Exact Match: {count == true_f})")
    print("\n=================================================================\n")


if __name__ == "__main__":
    run_comparison()
