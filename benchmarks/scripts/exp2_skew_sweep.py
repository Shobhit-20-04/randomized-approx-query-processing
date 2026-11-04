"""Experiment 2: Skew Sensitivity Sweep.

Sweeps Zipfian skew alpha in {1.05, 1.15, 1.25, 1.35, 1.50} at 32 KB and 64 KB budgets.
Evaluates frequency accuracy, peak error, and stash dynamics across:
- AdaLog-Sketch
- Disjoint Stack
- Elastic Sketch
- Augmented Sketch

Outputs results to results/raw/exp2_skew_sweep.json
"""

import json
import os
from typing import List
import numpy as np

from adalog.sketch import AdaLogSketch
from baselines.disjoint_stack import DisjointBaselineStack
from baselines.elastic_sketch import ElasticSketch
from baselines.augmented_sketch import AugmentedSketch
from experiments.datasets import generate_zipf_stream


def run_skew_sweep(
    alphas: List[float] = [1.05, 1.15, 1.25, 1.35, 1.50],
    budget_kb: int = 32,
    n_stream: int = 300_000,
    n_unique: int = 30_000,
    seed: int = 42,
    output_path: str = "results/raw/exp2_skew_sweep.json",
):
    print(f"=== Running Experiment 2: Skew Sweep across alphas={alphas} at {budget_kb} KB ===")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    total_bytes = budget_kb * 1024

    results = []

    for alpha in alphas:
        print(f"\nEvaluating Skew alpha = {alpha:.2f}...")
        stream, ground_truth = generate_zipf_stream(n_stream=n_stream, n_unique=n_unique, alpha=alpha, seed=seed)

        # 1. AdaLog-Sketch
        hll_m = 1024
        stash_k = 64
        fixed_bytes = (hll_m * 6 + 7) // 8 + stash_k * 16
        rem_bytes = max(256, total_bytes - fixed_bytes)
        d = 4
        w = max(64, rem_bytes // d)

        adalog = AdaLogSketch(
            d=d, w=w, counter_bits=8, m=hll_m, stash_capacity=stash_k, stash_tau=15,
            use_stash=True, use_conservative_update=True, seed=seed
        )
        for x in stream:
            adalog.update(x)

        adalog_diffs = [adalog.estimate(k) - true_f for k, true_f in ground_truth.items()]
        adalog_mae = float(np.mean(np.abs(adalog_diffs)))
        adalog_peak = int(np.max(adalog_diffs))

        # 2. Disjoint Stack
        disjoint = DisjointBaselineStack(total_memory_bytes=total_bytes, expected_cardinality=len(ground_truth), seed=seed)
        for x in stream:
            disjoint.update(x)
        dis_diffs = [disjoint.estimate(k) - true_f for k, true_f in ground_truth.items()]
        dis_mae = float(np.mean(np.abs(dis_diffs)))
        dis_peak = int(np.max(dis_diffs))

        # 3. Elastic Sketch
        elastic = ElasticSketch(total_memory_bytes=total_bytes, seed=seed)
        for x in stream:
            elastic.update(x)
        el_diffs = [elastic.estimate(k) - true_f for k, true_f in ground_truth.items()]
        el_mae = float(np.mean(np.abs(el_diffs)))
        el_peak = int(np.max(el_diffs))

        # 4. Augmented Sketch
        augmented = AugmentedSketch(total_memory_bytes=total_bytes, seed=seed)
        for x in stream:
            augmented.update(x)
        aug_diffs = [augmented.estimate(k) - true_f for k, true_f in ground_truth.items()]
        aug_mae = float(np.mean(np.abs(aug_diffs)))
        aug_peak = int(np.max(aug_diffs))

        row = {
            "alpha": alpha,
            "budget_kb": budget_kb,
            "adalog_mae": adalog_mae,
            "adalog_peak": adalog_peak,
            "adalog_evictions": adalog.stash.evictions,
            "disjoint_mae": dis_mae,
            "disjoint_peak": dis_peak,
            "elastic_mae": el_mae,
            "elastic_peak": el_peak,
            "augmented_mae": aug_mae,
            "augmented_peak": aug_peak,
        }
        results.append(row)
        print(f"  alpha={alpha:.2f} | AdaLog MAE: {adalog_mae:5.2f} (peak {adalog_peak:4d}) | Disjoint MAE: {dis_mae:5.2f} | Elastic MAE: {el_mae:5.2f} | Aug MAE: {aug_mae:5.2f}")

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nExperiment 2 complete. Results saved to {output_path}")
    return results


if __name__ == "__main__":
    run_skew_sweep()
