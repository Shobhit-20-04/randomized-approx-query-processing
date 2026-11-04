"""Measure Cardinality RSE across >= 100 trials with independent seeds.
Compares:
1. AdaLog-Sketch Decoupled HLL (m = 1024 registers, 768 bytes)
2. Standalone Memory-Matched HLL (m = 1024 registers, 768 bytes)
3. Standalone Unconstrained HLL (m = 16384 registers, 12,288 bytes / 12 KB)
"""

import json
import math
import os
import sys
import numpy as np
from scipy import stats

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from baselines.hyperloglog import HyperLogLog
from experiments.datasets import generate_zipf_stream

N_TRIALS = 100
N_STREAM = 300_000
N_UNIQUE = 100_000
ALPHA = 1.25

print(f"Running Cardinality Benchmark over {N_TRIALS} trials (N={N_STREAM}, |U|={N_UNIQUE}, alpha={ALPHA})...")

rse_m1024 = []
rse_m16384 = []

# Deterministic set of 100 seeds
seeds = [1000 + i * 37 for i in range(N_TRIALS)]

for trial_idx, seed in enumerate(seeds):
    stream, gt = generate_zipf_stream(n_stream=N_STREAM, n_unique=N_UNIQUE, alpha=ALPHA, seed=seed)
    actual_n = len(gt)

    # 1. HLL m=1024 (p=10, 6-bit packed: 768 bytes)
    hll_1024 = HyperLogLog(p=10, use_6bit_packing=True, seed=seed)
    for x in stream:
        hll_1024.add(x)
    est_1024 = hll_1024.cardinality()
    rse_1024 = abs(est_1024 - actual_n) / float(actual_n)
    rse_m1024.append(rse_1024)

    # 2. HLL m=16384 (p=14, 6-bit packed: 12,288 bytes)
    hll_16384 = HyperLogLog(p=14, use_6bit_packing=True, seed=seed)
    for x in stream:
        hll_16384.add(x)
    est_16384 = hll_16384.cardinality()
    rse_16384 = abs(est_16384 - actual_n) / float(actual_n)
    rse_m16384.append(rse_16384)

    if (trial_idx + 1) % 25 == 0:
        print(f"  Completed {trial_idx + 1}/{N_TRIALS} trials...")

def calc_ci(data):
    arr = np.array(data)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    margin = stats.t.ppf(0.975, df=len(arr)-1) * (std / math.sqrt(len(arr)))
    return {
        "mean": mean,
        "std": std,
        "ci95_lo": mean - margin,
        "ci95_hi": mean + margin,
    }

stat_1024 = calc_ci(rse_m1024)
stat_16384 = calc_ci(rse_m16384)

results = {
    "n_trials": N_TRIALS,
    "actual_cardinality": N_UNIQUE,
    "hll_m1024_768bytes": {
        "m": 1024,
        "p": 10,
        "memory_bytes": 768,
        "theoretical_rse": 1.04 / math.sqrt(1024),
        "mean_rse": stat_1024["mean"],
        "std_rse": stat_1024["std"],
        "ci95": [stat_1024["ci95_lo"], stat_1024["ci95_hi"]]
    },
    "hll_m16384_12288bytes": {
        "m": 16384,
        "p": 14,
        "memory_bytes": 12288,
        "theoretical_rse": 1.04 / math.sqrt(16384),
        "mean_rse": stat_16384["mean"],
        "std_rse": stat_16384["std"],
        "ci95": [stat_16384["ci95_lo"], stat_16384["ci95_hi"]]
    }
}

out_file = os.path.join(PROJECT_ROOT, "results", "raw", "cardinality_100trials.json")
with open(out_file, "w") as f:
    json.dump(results, f, indent=2)

print("\n=== Cardinality 100-Trial Benchmark Results ===")
print(f"HLL m=1024 (768 B)  : Mean RSE = {stat_1024['mean']:.4f} +/- {stat_1024['std']:.4f} (95% CI: [{stat_1024['ci95_lo']:.4f}, {stat_1024['ci95_hi']:.4f}]) [Theoretical: {1.04/math.sqrt(1024):.4f}]")
print(f"HLL m=16384 (12 KB) : Mean RSE = {stat_16384['mean']:.4f} +/- {stat_16384['std']:.4f} (95% CI: [{stat_16384['ci95_lo']:.4f}, {stat_16384['ci95_hi']:.4f}]) [Theoretical: {1.04/math.sqrt(16384):.4f}]")
