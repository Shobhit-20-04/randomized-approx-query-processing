"""Experiment 1: Memory Sweep Pareto Evaluation.

Evaluates multi-task performance across memory budgets B in {8, 16, 32, 64, 128, 256, 512} KB.
Compares:
1. AdaLog-Sketch (Unified single 128-bit hash)
2. Disjoint Stack (Optimal Bloom + CMS-CU + HLL)
3. Count-Min Sketch with CU (8-bit and 16-bit)
4. Elastic Sketch (Yang et al. 2018)
5. Augmented Sketch (Roy et al. 2016)

Outputs results to results/raw/exp1_memory_sweep.json
"""

import json
import math
import os
import sys
from typing import Dict, List
import numpy as np

from adalog.sketch import AdaLogSketch
from baselines.disjoint_stack import DisjointBaselineStack
from baselines.count_min_sketch import CountMinSketch
from baselines.elastic_sketch import ElasticSketch
from baselines.augmented_sketch import AugmentedSketch
from experiments.datasets import generate_zipf_stream


def evaluate_top_k_f1(true_counts: Dict[str, int], estimated_top_k: List[tuple], k: int = 100) -> float:
    """Compute F1 score for heavy hitter top-k detection."""
    actual_top_k = set([item[0] for item in sorted(true_counts.items(), key=lambda kv: kv[1], reverse=True)[:k]])
    est_set = set([item[0] for item in estimated_top_k[:k]])
    
    if not est_set:
        return 0.0
    true_positives = len(actual_top_k.intersection(est_set))
    precision = true_positives / float(len(est_set))
    recall = true_positives / float(len(actual_top_k))
    if precision + recall == 0:
        return 0.0
    return 2.0 * (precision * recall) / (precision + recall)


def run_memory_sweep(
    budgets_kb: List[int] = [8, 16, 32, 64, 128, 256, 512],
    n_stream: int = 300_000,
    n_unique: int = 30_000,
    alpha: float = 1.25,
    seed: int = 42,
    output_path: str = "results/raw/exp1_memory_sweep.json",
):
    print(f"=== Running Experiment 1: Memory Sweep across {budgets_kb} KB ===")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print("Generating synthetic Zipfian stream...")
    stream, ground_truth = generate_zipf_stream(n_stream=n_stream, n_unique=n_unique, alpha=alpha, seed=seed)
    unique_keys = list(ground_truth.keys())
    actual_cardinality = len(unique_keys)
    
    # 10,000 uninserted keys for FPR
    uninserted_keys = [f"absent_item_{i}_{seed}" for i in range(10_000)]

    results = []

    for b_kb in budgets_kb:
        total_bytes = b_kb * 1024
        print(f"\nEvaluating Memory Budget: {b_kb} KB ({total_bytes:,} bytes)")

        # -------------------------------------------------------------
        # 1. AdaLog-Sketch (Unified)
        # -------------------------------------------------------------
        # Allocation: 6-bit packed HLL (m=1024 -> 768 B), Stash (K=64 -> 1024 B), remainder matrix
        hll_m = 1024 if total_bytes >= 16384 else 512
        stash_k = 64 if total_bytes >= 16384 else 32
        fixed_bytes = (hll_m * 6 + 7) // 8 + stash_k * 16
        rem_bytes = max(256, total_bytes - fixed_bytes)
        d = 4
        # 8-bit counters: 1 byte per cell
        w = max(64, rem_bytes // d)
        
        adalog = AdaLogSketch(
            d=d,
            w=w,
            counter_bits=8,
            m=hll_m,
            stash_capacity=stash_k,
            stash_tau=15,
            use_stash=True,
            use_conservative_update=True,
            seed=seed,
        )
        for x in stream:
            adalog.update(x)

        # Metrics for AdaLog
        adalog_errors = []
        adalog_underestimates = 0
        for k, true_f in ground_truth.items():
            est_f = adalog.estimate(k)
            err = est_f - true_f
            if err < 0:
                adalog_underestimates += 1
            adalog_errors.append(abs(err))
        
        adalog_mae = float(np.mean(adalog_errors))
        adalog_fps = sum(1 for uk in uninserted_keys if adalog.contains(uk))
        adalog_fpr = adalog_fps / float(len(uninserted_keys))
        adalog_card = adalog.cardinality()
        adalog_rse = abs(adalog_card - actual_cardinality) / float(actual_cardinality)
        adalog_f1 = evaluate_top_k_f1(ground_truth, adalog.top_k(100), k=100)

        results.append({
            "model": "AdaLog-Sketch",
            "budget_kb": b_kb,
            "bytes": total_bytes,
            "mae": adalog_mae,
            "fpr": adalog_fpr,
            "rse": adalog_rse,
            "top_k_f1": adalog_f1,
            "underestimates": adalog_underestimates,
        })
        print(f"  AdaLog-Sketch  -> MAE: {adalog_mae:6.2f} | FPR: {adalog_fpr:7.4f} | RSE: {adalog_rse:6.4f} | F1: {adalog_f1:.3f} | Underestimates: {adalog_underestimates}")

        # -------------------------------------------------------------
        # 2. Disjoint Baseline Stack (Bloom + CMS-CU + HLL)
        # -------------------------------------------------------------
        disjoint = DisjointBaselineStack(
            total_memory_bytes=total_bytes,
            expected_cardinality=actual_cardinality,
            seed=seed,
        )
        for x in stream:
            disjoint.update(x)

        dis_errors = [abs(disjoint.estimate(k) - true_f) for k, true_f in ground_truth.items()]
        dis_mae = float(np.mean(dis_errors))
        dis_fps = sum(1 for uk in uninserted_keys if disjoint.contains(uk))
        dis_fpr = dis_fps / float(len(uninserted_keys))
        dis_card = disjoint.cardinality()
        dis_rse = abs(dis_card - actual_cardinality) / float(actual_cardinality)
        dis_f1 = evaluate_top_k_f1(ground_truth, disjoint.top_k(100), k=100)

        results.append({
            "model": "Disjoint-Stack",
            "budget_kb": b_kb,
            "bytes": total_bytes,
            "mae": dis_mae,
            "fpr": dis_fpr,
            "rse": dis_rse,
            "top_k_f1": dis_f1,
            "underestimates": 0,
        })
        print(f"  Disjoint-Stack -> MAE: {dis_mae:6.2f} | FPR: {dis_fpr:7.4f} | RSE: {dis_rse:6.4f} | F1: {dis_f1:.3f}")

        # -------------------------------------------------------------
        # 3. Elastic Sketch (Yang et al. 2018)
        # -------------------------------------------------------------
        elastic = ElasticSketch(total_memory_bytes=total_bytes, seed=seed)
        for x in stream:
            elastic.update(x)

        el_errors = [abs(elastic.estimate(k) - true_f) for k, true_f in ground_truth.items()]
        el_mae = float(np.mean(el_errors))
        el_f1 = evaluate_top_k_f1(ground_truth, elastic.top_k(100), k=100)

        results.append({
            "model": "ElasticSketch",
            "budget_kb": b_kb,
            "bytes": total_bytes,
            "mae": el_mae,
            "fpr": None,
            "rse": None,
            "top_k_f1": el_f1,
            "underestimates": 0,
        })
        print(f"  ElasticSketch  -> MAE: {el_mae:6.2f} | F1: {el_f1:.3f}")

        # -------------------------------------------------------------
        # 4. Augmented Sketch (Roy et al. 2016)
        # -------------------------------------------------------------
        augmented = AugmentedSketch(total_memory_bytes=total_bytes, seed=seed)
        for x in stream:
            augmented.update(x)

        aug_errors = [abs(augmented.estimate(k) - true_f) for k, true_f in ground_truth.items()]
        aug_mae = float(np.mean(aug_errors))
        aug_f1 = evaluate_top_k_f1(ground_truth, augmented.top_k(100), k=100)

        results.append({
            "model": "AugmentedSketch",
            "budget_kb": b_kb,
            "bytes": total_bytes,
            "mae": aug_mae,
            "fpr": None,
            "rse": None,
            "top_k_f1": aug_f1,
            "underestimates": 0,
        })
        print(f"  AugmentedSketch-> MAE: {aug_mae:6.2f} | F1: {aug_f1:.3f}")

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nExperiment 1 complete. Results saved to {output_path}")
    return results


if __name__ == "__main__":
    run_memory_sweep()
