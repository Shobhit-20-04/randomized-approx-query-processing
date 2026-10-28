"""Experiment 4: Systematic Ablation Grid.

Deconstructs AdaLog-Sketch into its individual architectural choices at 32 KB budget:
1. Full AdaLog-Sketch (Stash ON, CU ON, 8-bit counters, Variant A, Coupled HLL)
2. Ablation 1: Elephant Stash OFF (Pure CMS-CU matrix + HLL)
3. Ablation 2: Conservative Update OFF (Standard Count-Min increment)
4. Ablation 3: Counter Width (8-bit vs 16-bit vs 32-bit counters at equal bytes)
5. Ablation 4: Membership Variant (Variant A shared vs Variant B 1-bit plane vs Dedicated Bloom)
6. Ablation 5: HLL Register Coupling (Coupled m=w vs Decoupled m=2^p)

Outputs results to results/raw/exp4_ablations.json
"""

import json
import os
from typing import Dict, List
import numpy as np

from adalog.sketch import AdaLogSketch
from baselines.bloom_filter import BloomFilter
from experiments.datasets import generate_zipf_stream


def run_ablation_grid(
    budget_kb: int = 32,
    n_stream: int = 300_000,
    n_unique: int = 30_000,
    alpha: float = 1.25,
    seed: int = 42,
    output_path: str = "results/raw/exp4_ablations.json",
):
    print("================================================================================")
    print(f"EXPERIMENT 4: SYSTEMATIC ABLATION MATRIX ({budget_kb} KB BUDGET)")
    print("================================================================================")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    total_bytes = budget_kb * 1024

    stream, ground_truth = generate_zipf_stream(n_stream=n_stream, n_unique=n_unique, alpha=alpha, seed=seed)
    actual_cardinality = len(ground_truth)
    uninserted_keys = [f"absent_ablation_{i}_{seed}" for i in range(10_000)]

    configurations = [
        ("Full AdaLog (Default)", {"use_stash": True, "use_cu": True, "bits": 8, "var": "A", "hll": "coupled"}),
        ("No Stash (-Stash)",     {"use_stash": False, "use_cu": True, "bits": 8, "var": "A", "hll": "coupled"}),
        ("No CU (-Conservative)", {"use_stash": True, "use_cu": False, "bits": 8, "var": "A", "hll": "coupled"}),
        ("16-bit Counters",       {"use_stash": True, "use_cu": True, "bits": 16, "var": "A", "hll": "coupled"}),
        ("32-bit Counters",       {"use_stash": True, "use_cu": True, "bits": 32, "var": "A", "hll": "coupled"}),
        ("Membership Variant B",  {"use_stash": True, "use_cu": True, "bits": 8, "var": "B", "hll": "coupled"}),
        ("HLL Decoupled (m=1024)",{"use_stash": True, "use_cu": True, "bits": 8, "var": "A", "hll": "decoupled"}),
    ]

    results = []

    for name, cfg in configurations:
        print(f"\nEvaluating Configuration: {name}...")
        bits = cfg["bits"]
        d = 4

        # Compute width w fitting within total_bytes
        stash_k = 64 if cfg["use_stash"] else 0
        stash_bytes = stash_k * 16
        if cfg["hll"] == "coupled":
            # coupled: m = w. Each column has d * (bits/8) bytes + (6/8) bytes HLL
            # w * (d * bits + 6) / 8 <= total_bytes - stash_bytes
            rem_bytes = max(256, total_bytes - stash_bytes)
            bits_per_col = d * bits + 6
            w = max(64, int((rem_bytes * 8) // bits_per_col))
            m_hll = None
        else:
            m_hll = 1024
            hll_bytes = (m_hll * 6 + 7) // 8
            rem_bytes = max(256, total_bytes - stash_bytes - hll_bytes)
            w = max(64, int((rem_bytes * 8) // (d * bits)))

        sketch = AdaLogSketch(
            d=d,
            w=w,
            counter_bits=bits,
            use_stash=cfg["use_stash"],
            stash_capacity=stash_k,
            stash_tau=15,
            use_conservative_update=cfg["use_cu"],
            membership_variant=cfg["var"],
            hll_layout=cfg["hll"],
            m=m_hll,
            seed=seed,
        )

        for x in stream:
            sketch.update(x)

        # MAE and peak error
        diffs = [sketch.estimate(k) - true_f for k, true_f in ground_truth.items()]
        mae = float(np.mean(np.abs(diffs)))
        peak_err = int(np.max(diffs))

        # AMQ FPR
        fps = sum(1 for uk in uninserted_keys if sketch.contains(uk))
        fpr = fps / float(len(uninserted_keys))

        # HLL RSE
        card = sketch.cardinality()
        rse = abs(card - actual_cardinality) / float(actual_cardinality)

        row = {
            "name": name,
            "config": cfg,
            "width": w,
            "mae": mae,
            "peak_error": peak_err,
            "fpr": fpr,
            "rse": rse,
            "stashed_items": len(sketch.stash) if sketch.use_stash else 0,
        }
        results.append(row)
        print(f"  {name:25s} -> MAE: {mae:6.2f} | Peak: {peak_err:4d} | FPR: {fpr:7.4f} | RSE: {rse:6.4f} | Stash: {row['stashed_items']}")

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nExperiment 4 complete. Results saved to {output_path}")
    return results


if __name__ == "__main__":
    run_ablation_grid()
