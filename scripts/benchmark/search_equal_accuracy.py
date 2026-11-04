"""Search for exact memory budget (in KB) required by each architecture
to achieve MAE <= 0.40 on a Zipfian stream (N=300,000, alpha=1.25).
Evaluates across seeds to ensure statistical validity.
"""

from __future__ import annotations
import json
import os
import sys
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from adalog.sketch import AdaLogSketch
from baselines.disjoint_stack import DisjointBaselineStack, DisjointStashStack
from baselines.count_min_sketch import CountMinSketch
from baselines.elastic_sketch import ElasticSketch
from baselines.augmented_sketch import AugmentedSketch
from experiments.datasets import generate_zipf_stream

SEEDS = [42, 100, 2024]
N_STREAM = 300_000
N_UNIQUE = 100_000
ALPHA = 1.25
TARGET_MAE = 0.40


def eval_adalog(b_kb: float) -> float:
    maes = []
    total_bytes = int(b_kb * 1024)
    for seed in SEEDS:
        stream, gt = generate_zipf_stream(n_stream=N_STREAM, n_unique=N_UNIQUE, alpha=ALPHA, seed=seed)
        hll_m = 1024
        stash_k = 128
        fixed_bytes = (hll_m * 6 + 7) // 8 + stash_k * 24
        rem_bytes = max(256, total_bytes - fixed_bytes)
        d = 4
        w = max(64, rem_bytes // d)
        adalog = AdaLogSketch(d=d, w=w, counter_bits=8, stash_capacity=stash_k, elephant_threshold=15, m=hll_m, seed=seed)
        for x in stream: adalog.update(x)
        errs = [abs(adalog.estimate(k) - tf) for k, tf in gt.items()]
        maes.append(float(np.mean(errs)))
    return float(np.mean(maes))


def eval_disjoint_stash(b_kb: float) -> float:
    maes = []
    total_bytes = int(b_kb * 1024)
    for seed in SEEDS:
        stream, gt = generate_zipf_stream(n_stream=N_STREAM, n_unique=N_UNIQUE, alpha=ALPHA, seed=seed)
        ds = DisjointStashStack(total_memory_bytes=total_bytes, stash_capacity=128, stash_tau=15, cms_counter_bits=8, seed=seed)
        for x in stream: ds.update(x)
        errs = [abs(ds.estimate(k) - tf) for k, tf in gt.items()]
        maes.append(float(np.mean(errs)))
    return float(np.mean(maes))


def eval_disjoint_16(b_kb: float) -> float:
    maes = []
    total_bytes = int(b_kb * 1024)
    for seed in SEEDS:
        stream, gt = generate_zipf_stream(n_stream=N_STREAM, n_unique=N_UNIQUE, alpha=ALPHA, seed=seed)
        dis = DisjointBaselineStack(expected_cardinality=len(gt), total_memory_bytes=total_bytes, seed=seed)
        for x in stream: dis.update(x)
        errs = [abs(dis.estimate(k) - tf) for k, tf in gt.items()]
        maes.append(float(np.mean(errs)))
    return float(np.mean(maes))


def eval_disjoint_32(b_kb: float) -> float:
    maes = []
    total_bytes = int(b_kb * 1024)
    for seed in SEEDS:
        stream, gt = generate_zipf_stream(n_stream=N_STREAM, n_unique=N_UNIQUE, alpha=ALPHA, seed=seed)
        # Disjoint 32-bit: BF + HLL + CMS 32-bit (4 rows)
        hll_bytes = 768
        bf_bytes = max(512, int(total_bytes * 0.20))
        cms_bytes = max(512, total_bytes - bf_bytes - hll_bytes)
        w = max(64, cms_bytes // (4 * 4)) # 4 bytes per counter
        cms = CountMinSketch(depth=4, width=w, counter_bits=32, conservative_update=False, seed=seed)
        for x in stream: cms.update(x)
        errs = [abs(cms.query(k) - tf) for k, tf in gt.items()]
        maes.append(float(np.mean(errs)))
    return float(np.mean(maes))


def eval_elastic(b_kb: float) -> float:
    maes = []
    total_bytes = int(b_kb * 1024)
    for seed in SEEDS:
        stream, gt = generate_zipf_stream(n_stream=N_STREAM, n_unique=N_UNIQUE, alpha=ALPHA, seed=seed)
        el = ElasticSketch(total_memory_bytes=total_bytes, seed=seed)
        for x in stream: el.update(x)
        errs = [abs(el.estimate(k) - tf) for k, tf in gt.items()]
        maes.append(float(np.mean(errs)))
    return float(np.mean(maes))


def eval_augmented(b_kb: float) -> float:
    maes = []
    total_bytes = int(b_kb * 1024)
    for seed in SEEDS:
        stream, gt = generate_zipf_stream(n_stream=N_STREAM, n_unique=N_UNIQUE, alpha=ALPHA, seed=seed)
        aug = AugmentedSketch(total_memory_bytes=total_bytes, seed=seed)
        for x in stream: aug.update(x)
        errs = [abs(aug.estimate(k) - tf) for k, tf in gt.items()]
        maes.append(float(np.mean(errs)))
    return float(np.mean(maes))


def find_budget_for_target(eval_fn, low_kb: float = 8.0, high_kb: float = 256.0, tol: float = 1.0) -> float:
    """Binary search for minimal budget in KB to achieve MAE <= TARGET_MAE."""
    best_kb = high_kb
    l, r = low_kb, high_kb
    for _ in range(10):
        mid = (l + r) / 2.0
        mae = eval_fn(mid)
        print(f"  Testing budget {mid:6.1f} KB -> MAE = {mae:6.3f} (target <= {TARGET_MAE:.2f})")
        if mae <= TARGET_MAE:
            best_kb = mid
            r = mid
        else:
            l = mid
        if (r - l) < tol:
            break
    return round(best_kb, 1)


if __name__ == "__main__":
    print("Searching exact memory budgets for MAE <= 0.40...")
    res = {}
    print("\n1. AdaLog-Sketch:")
    res["AdaLog-Sketch"] = find_budget_for_target(eval_adalog, 16.0, 64.0)

    print("\n2. Disjoint + Stash (Primary Baseline):")
    res["Disjoint-Stash"] = find_budget_for_target(eval_disjoint_stash, 40.0, 56.0)

    print("\n3. Disjoint Stack (16-bit CU, Overflow Illustration):")
    res["Disjoint-16bit"] = find_budget_for_target(eval_disjoint_16, 64.0, 160.0)

    print("\n4. Disjoint Stack (32-bit Standard):")
    res["Disjoint-32bit"] = find_budget_for_target(eval_disjoint_32, 96.0, 256.0)

    print("\n5. Elastic Sketch:")
    res["ElasticSketch"] = find_budget_for_target(eval_elastic, 48.0, 128.0)

    print("\n6. Augmented Sketch:")
    res["AugmentedSketch"] = find_budget_for_target(eval_augmented, 48.0, 128.0)

    out_json = os.path.join(PROJECT_ROOT, "results", "raw", "equal_accuracy_search.json")
    with open(out_json, "w") as f:
        json.dump(res, f, indent=2)
    print(f"\nFinal Search Results: {res}")
