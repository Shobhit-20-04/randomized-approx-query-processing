"""
Benchmarking engine for randomized approximate data structures vs exact baselines.
Executes reproducible experimental trials, parameter sweeps, and generates
raw and aggregated CSV records.
"""

from __future__ import annotations

import collections
import dataclasses
import os
import sys
import time
import tracemalloc
from typing import Any, Dict, List, Sequence, Tuple
import numpy as np
import pandas as pd
import yaml

from .bloom_filter import BloomFilter
from .count_min_sketch import CountMinSketch
from .datasets import StreamDataset, create_benchmark_dataset
from .hyperloglog import HyperLogLog
from .metrics import (
    compute_confidence_interval_95,
    estimate_object_memory_bytes,
    measure_batch_latencies_ns,
    measure_execution_time_ns,
)


class BenchmarkRunner:
    """
    Orchestrates systematic experiments comparing Bloom Filter, Count-Min Sketch,
    and HyperLogLog against exact baselines.
    """

    def __init__(self, config_path: str, output_dir: str = "results") -> None:
        self.config_path = config_path
        self.output_dir = output_dir

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.raw_dir = os.path.join(output_dir, "raw")
        self.agg_dir = os.path.join(output_dir, "aggregated")
        self.plots_dir = os.path.join(output_dir, "plots")
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.agg_dir, exist_ok=True)
        os.makedirs(self.plots_dir, exist_ok=True)

    # -------------------------------------------------------------------------
    # Bloom Filter Benchmark
    # -------------------------------------------------------------------------
    def benchmark_bloom_filter(
        self,
        dataset: StreamDataset,
        target_fpr: float,
    ) -> Dict[str, Any]:
        """Run single trial of Bloom Filter vs exact set."""
        stream = dataset.stream
        n = dataset.stream_size

        # Exact Baseline: set()
        tracemalloc.start()
        exact_set = set()
        _, exact_insert_ns = measure_execution_time_ns(lambda: exact_set.update(stream))
        exact_mem_bytes = estimate_object_memory_bytes(exact_set)
        _, peak_exact_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        exact_query_stats = measure_batch_latencies_ns(
            lambda item: item in exact_set, [q for q, _ in dataset.mixed_queries]
        )

        # Approximate: BloomFilter
        tracemalloc.start()
        bf = BloomFilter(expected_capacity=max(10, n), target_fpr=target_fpr)
        _, bf_insert_ns = measure_execution_time_ns(lambda: bf.add_many(stream))
        bf_mem_bytes = bf.memory_usage_bytes()
        _, peak_bf_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        bf_query_stats = measure_batch_latencies_ns(
            lambda item: item in bf, [q for q, _ in dataset.mixed_queries]
        )

        # Accuracy checks
        # True Positives & False Negatives on known present
        tp = sum(1 for q in dataset.present_queries if q in bf)
        fn = len(dataset.present_queries) - tp  # Must be 0

        # False Positives & True Negatives on known absent
        fp = sum(1 for q in dataset.absent_queries if q in bf)
        tn = len(dataset.absent_queries) - fp
        empirical_fpr = fp / len(dataset.absent_queries) if dataset.absent_queries else 0.0
        theoretical_fpr = bf.theoretical_fpr()

        return {
            "algorithm": "BloomFilter",
            "distribution": dataset.distribution,
            "stream_size": n,
            "seed": dataset.seed,
            "target_fpr": target_fpr,
            "m_bits": bf.m,
            "k_hashes": bf.k,
            "exact_memory_bytes": exact_mem_bytes,
            "approx_memory_bytes": bf_mem_bytes,
            "memory_reduction_ratio": exact_mem_bytes / max(1, bf_mem_bytes),
            "exact_insert_time_ms": exact_insert_ns / 1_000_000.0,
            "approx_insert_time_ms": bf_insert_ns / 1_000_000.0,
            "exact_query_latency_ns": exact_query_stats["mean_ns"],
            "approx_query_latency_ns": bf_query_stats["mean_ns"],
            "approx_query_p50_ns": bf_query_stats["p50_ns"],
            "approx_query_p95_ns": bf_query_stats["p95_ns"],
            "true_positives": tp,
            "false_negatives": fn,
            "true_negatives": tn,
            "false_positives": fp,
            "empirical_fpr": empirical_fpr,
            "theoretical_fpr": theoretical_fpr,
            "fpr_ratio": empirical_fpr / max(1e-9, target_fpr),
        }

    # -------------------------------------------------------------------------
    # Count-Min Sketch Benchmark
    # -------------------------------------------------------------------------
    def benchmark_count_min_sketch(
        self,
        dataset: StreamDataset,
        epsilon: float,
        delta: float,
    ) -> Dict[str, Any]:
        """Run single trial of Count-Min Sketch vs exact frequency dictionary."""
        stream = dataset.stream
        n = dataset.stream_size

        # Exact Baseline: Counter / dict
        tracemalloc.start()
        exact_counts: Dict[str, int] = collections.Counter()
        _, exact_insert_ns = measure_execution_time_ns(lambda: exact_counts.update(stream))
        exact_mem_bytes = estimate_object_memory_bytes(exact_counts)
        tracemalloc.stop()

        query_keys = list(dataset.true_frequencies.keys())[: min(2000, len(dataset.true_frequencies))]
        # Add absent keys to query workload
        query_keys.extend(dataset.absent_queries[: min(500, len(dataset.absent_queries))])

        exact_query_stats = measure_batch_latencies_ns(
            lambda k: exact_counts.get(k, 0), query_keys
        )

        # Approximate: Count-Min Sketch
        tracemalloc.start()
        cms = CountMinSketch(epsilon=epsilon, delta=delta, seed=dataset.seed)
        _, cms_insert_ns = measure_execution_time_ns(lambda: cms.update_many(stream))
        cms_mem_bytes = cms.memory_usage_bytes()
        tracemalloc.stop()

        cms_query_stats = measure_batch_latencies_ns(
            lambda k: cms.query(k), query_keys
        )

        # Accuracy metrics across ground truth
        error_metrics = cms.compute_errors(dataset.true_frequencies)

        # Also test absent queries error (true frequency = 0)
        absent_estimates = [cms.query(k) for k in dataset.absent_queries]
        absent_overestimation_mean = float(np.mean(absent_estimates)) if absent_estimates else 0.0

        return {
            "algorithm": "CountMinSketch",
            "distribution": dataset.distribution,
            "stream_size": n,
            "seed": dataset.seed,
            "epsilon": epsilon,
            "delta": delta,
            "table_width": cms.width,
            "table_depth": cms.depth,
            "exact_memory_bytes": exact_mem_bytes,
            "approx_memory_bytes": cms_mem_bytes,
            "memory_reduction_ratio": exact_mem_bytes / max(1, cms_mem_bytes),
            "exact_insert_time_ms": exact_insert_ns / 1_000_000.0,
            "approx_insert_time_ms": cms_insert_ns / 1_000_000.0,
            "exact_query_latency_ns": exact_query_stats["mean_ns"],
            "approx_query_latency_ns": cms_query_stats["mean_ns"],
            "approx_query_p50_ns": cms_query_stats["p50_ns"],
            "approx_query_p95_ns": cms_query_stats["p95_ns"],
            "mae": error_metrics["mae"],
            "rmse": error_metrics["rmse"],
            "max_overestimation": error_metrics["max_overestimation"],
            "bound_compliance_ratio": error_metrics["bound_compliance_ratio"],
            "underestimation_count": error_metrics["underestimation_count"],
            "absent_overestimation_mean": absent_overestimation_mean,
        }

    # -------------------------------------------------------------------------
    # HyperLogLog Benchmark
    # -------------------------------------------------------------------------
    def benchmark_hyperloglog(
        self,
        dataset: StreamDataset,
        p: int,
    ) -> Dict[str, Any]:
        """Run single trial of HyperLogLog vs exact distinct set."""
        stream = dataset.stream
        n = dataset.stream_size
        true_cardinality = dataset.true_cardinality

        # Exact Baseline: set()
        tracemalloc.start()
        exact_set = set()
        _, exact_insert_ns = measure_execution_time_ns(lambda: exact_set.update(stream))
        exact_mem_bytes = estimate_object_memory_bytes(exact_set)
        tracemalloc.stop()

        _, exact_query_ns = measure_execution_time_ns(lambda: len(exact_set))

        # Approximate: HyperLogLog
        tracemalloc.start()
        hll = HyperLogLog(p=p)
        _, hll_insert_ns = measure_execution_time_ns(lambda: hll.add_many(stream))
        hll_mem_bytes = hll.memory_usage_bytes()
        tracemalloc.stop()

        est_cardinality, hll_query_ns = measure_execution_time_ns(lambda: hll.estimate())

        abs_err = abs(est_cardinality - true_cardinality)
        rel_err = abs_err / true_cardinality if true_cardinality > 0 else 0.0
        theoretical_rse = hll.theoretical_relative_error
        within_rse = rel_err <= theoretical_rse

        return {
            "algorithm": "HyperLogLog",
            "distribution": dataset.distribution,
            "stream_size": n,
            "seed": dataset.seed,
            "precision_p": p,
            "registers_m": hll.m,
            "exact_memory_bytes": exact_mem_bytes,
            "approx_memory_bytes": hll_mem_bytes,
            "memory_reduction_ratio": exact_mem_bytes / max(1, hll_mem_bytes),
            "exact_insert_time_ms": exact_insert_ns / 1_000_000.0,
            "approx_insert_time_ms": hll_insert_ns / 1_000_000.0,
            "exact_query_latency_ns": exact_query_ns,
            "approx_query_latency_ns": hll_query_ns,
            "true_cardinality": true_cardinality,
            "estimated_cardinality": est_cardinality,
            "absolute_error": abs_err,
            "relative_error": rel_err,
            "theoretical_rse": theoretical_rse,
            "within_theoretical_rse": within_rse,
        }

    # -------------------------------------------------------------------------
    # Orchestrator
    # -------------------------------------------------------------------------
    def run_all(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Execute full benchmark suite defined by loaded configuration."""
        stream_sizes = self.config.get("stream_sizes", [10000])
        distributions = self.config.get("distributions", ["uniform", "zipfian"])
        seeds = self.config.get("seeds", [42, 43])

        bf_target_fprs = self.config.get("bloom_filter", {}).get("target_fprs", [0.01])
        cms_epsilons = self.config.get("count_min_sketch", {}).get("epsilons", [0.05])
        cms_deltas = self.config.get("count_min_sketch", {}).get("deltas", [0.01])
        hll_precisions = self.config.get("hyperloglog", {}).get("precisions", [12])

        bf_results: List[Dict[str, Any]] = []
        cms_results: List[Dict[str, Any]] = []
        hll_results: List[Dict[str, Any]] = []

        total_runs = (
            len(stream_sizes) * len(distributions) * len(seeds) *
            (len(bf_target_fprs) + (len(cms_epsilons) * len(cms_deltas)) + len(hll_precisions))
        )
        print(f"Starting benchmark run: ~{total_runs} experimental configurations.")

        run_idx = 0
        for size in stream_sizes:
            for dist in distributions:
                for seed in seeds:
                    print(f"Generating dataset: size={size}, dist={dist}, seed={seed}...")
                    dataset = create_benchmark_dataset(
                        distribution=dist,
                        stream_size=size,
                        seed=seed,
                        query_sample_size=self.config.get("query_sample_size", 2000),
                    )

                    # 1. Bloom Filter Trials
                    for p_fpr in bf_target_fprs:
                        run_idx += 1
                        res = self.benchmark_bloom_filter(dataset, target_fpr=p_fpr)
                        bf_results.append(res)

                    # 2. Count-Min Sketch Trials
                    for eps in cms_epsilons:
                        for delta in cms_deltas:
                            run_idx += 1
                            res = self.benchmark_count_min_sketch(dataset, epsilon=eps, delta=delta)
                            cms_results.append(res)

                    # 3. HyperLogLog Trials
                    for p in hll_precisions:
                        run_idx += 1
                        res = self.benchmark_hyperloglog(dataset, p=p)
                        hll_results.append(res)

        # Convert to DataFrames
        df_bf = pd.DataFrame(bf_results)
        df_cms = pd.DataFrame(cms_results)
        df_hll = pd.DataFrame(hll_results)

        # Save Raw CSVs
        df_bf.to_csv(os.path.join(self.raw_dir, "bloom_filter_raw.csv"), index=False)
        df_cms.to_csv(os.path.join(self.raw_dir, "count_min_sketch_raw.csv"), index=False)
        df_hll.to_csv(os.path.join(self.raw_dir, "hyperloglog_raw.csv"), index=False)

        # Generate Aggregated DataFrames
        self._aggregate_and_save(df_bf, df_cms, df_hll)

        print("Benchmark execution complete. Raw and aggregated CSVs saved.")
        return df_bf, df_cms, df_hll

    def _aggregate_and_save(
        self, df_bf: pd.DataFrame, df_cms: pd.DataFrame, df_hll: pd.DataFrame
    ) -> None:
        """Compute aggregated statistics (mean, std, 95% CI) grouped by configuration."""
        # Aggregate BF
        bf_group_cols = ["algorithm", "distribution", "stream_size", "target_fpr"]
        bf_agg = df_bf.groupby(bf_group_cols).agg(
            approx_memory_bytes_mean=("approx_memory_bytes", "mean"),
            approx_memory_bytes_std=("approx_memory_bytes", "std"),
            exact_memory_bytes_mean=("exact_memory_bytes", "mean"),
            memory_reduction_ratio_mean=("memory_reduction_ratio", "mean"),
            approx_insert_time_ms_mean=("approx_insert_time_ms", "mean"),
            exact_insert_time_ms_mean=("exact_insert_time_ms", "mean"),
            approx_query_latency_ns_mean=("approx_query_latency_ns", "mean"),
            exact_query_latency_ns_mean=("exact_query_latency_ns", "mean"),
            empirical_fpr_mean=("empirical_fpr", "mean"),
            theoretical_fpr_mean=("theoretical_fpr", "mean"),
            false_negatives_sum=("false_negatives", "sum"),
        ).reset_index()
        bf_agg.to_csv(os.path.join(self.agg_dir, "bloom_filter_aggregated.csv"), index=False)

        # Aggregate CMS
        cms_group_cols = ["algorithm", "distribution", "stream_size", "epsilon", "delta"]
        cms_agg = df_cms.groupby(cms_group_cols).agg(
            approx_memory_bytes_mean=("approx_memory_bytes", "mean"),
            exact_memory_bytes_mean=("exact_memory_bytes", "mean"),
            memory_reduction_ratio_mean=("memory_reduction_ratio", "mean"),
            approx_insert_time_ms_mean=("approx_insert_time_ms", "mean"),
            exact_insert_time_ms_mean=("exact_insert_time_ms", "mean"),
            approx_query_latency_ns_mean=("approx_query_latency_ns", "mean"),
            exact_query_latency_ns_mean=("exact_query_latency_ns", "mean"),
            mae_mean=("mae", "mean"),
            rmse_mean=("rmse", "mean"),
            max_overestimation_mean=("max_overestimation", "mean"),
            bound_compliance_ratio_mean=("bound_compliance_ratio", "mean"),
            underestimation_count_sum=("underestimation_count", "sum"),
        ).reset_index()
        cms_agg.to_csv(os.path.join(self.agg_dir, "count_min_sketch_aggregated.csv"), index=False)

        # Aggregate HLL
        hll_group_cols = ["algorithm", "distribution", "stream_size", "precision_p"]
        hll_agg = df_hll.groupby(hll_group_cols).agg(
            approx_memory_bytes_mean=("approx_memory_bytes", "mean"),
            exact_memory_bytes_mean=("exact_memory_bytes", "mean"),
            memory_reduction_ratio_mean=("memory_reduction_ratio", "mean"),
            approx_insert_time_ms_mean=("approx_insert_time_ms", "mean"),
            exact_insert_time_ms_mean=("exact_insert_time_ms", "mean"),
            approx_query_latency_ns_mean=("approx_query_latency_ns", "mean"),
            exact_query_latency_ns_mean=("exact_query_latency_ns", "mean"),
            relative_error_mean=("relative_error", "mean"),
            theoretical_rse_mean=("theoretical_rse", "mean"),
            within_theoretical_rse_ratio=("within_theoretical_rse", "mean"),
        ).reset_index()
        hll_agg.to_csv(os.path.join(self.agg_dir, "hyperloglog_aggregated.csv"), index=False)
