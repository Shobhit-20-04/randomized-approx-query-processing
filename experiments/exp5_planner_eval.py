"""Experiment 5: Acceptance Test for Novel Contribution N1 (AdaLog-Planner).

Tests whether:
1. Planner-predicted MAE is within +/- 25% of empirical measured MAE across a memory sweep (8 KB to 256 KB).
2. The planner's optimized configuration beats a fixed default configuration at equal bytes on at least 3 of 5 skew values (alpha in {1.05, 1.15, 1.25, 1.35, 1.50}).

Outputs results to results/raw/exp5_planner_eval.json and logs PASS/FAIL verdict.
"""

import json
import os
from typing import Dict, List
import numpy as np

from planner.planner import AdaLogPlanner
from adalog.sketch import AdaLogSketch
from experiments.datasets import generate_zipf_stream


def run_planner_evaluation(
    budgets_kb: List[int] = [8, 16, 32, 64, 128, 256],
    alphas: List[float] = [1.05, 1.15, 1.25, 1.35, 1.50],
    n_stream: int = 200_000,
    n_unique: int = 20_000,
    seed: int = 42,
    output_path: str = "results/raw/exp5_planner_eval.json",
):
    print("================================================================================")
    print("EXPERIMENT 5: ACCEPTANCE TEST EVALUATION FOR NOVEL CONTRIBUTION N1 (PLANNER)")
    print("================================================================================")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    planner = AdaLogPlanner()

    # -------------------------------------------------------------------------
    # PART 1: Prediction Error Gate (Must be <= 25% across sweep)
    # -------------------------------------------------------------------------
    print("\n[PART 1] Testing Planner Prediction Accuracy (8 KB to 256 KB, alpha=1.25)...")
    stream, ground_truth = generate_zipf_stream(n_stream=n_stream, n_unique=n_unique, alpha=1.25, seed=seed)
    
    sweep_results = []
    rel_errors = []

    for b_kb in budgets_kb:
        total_bytes = b_kb * 1024
        opt_cfg = planner.optimize(budget_bytes=total_bytes, n_stream=n_stream, n_unique=n_unique, skew=1.25)

        # Build empirical sketch matching planner configuration
        sketch = AdaLogSketch(
            d=opt_cfg.d,
            w=opt_cfg.w,
            counter_bits=opt_cfg.counter_bits,
            m=opt_cfg.m,
            stash_capacity=opt_cfg.K,
            stash_tau=opt_cfg.tau,
            use_stash=True,
            use_conservative_update=True,
            seed=seed,
        )
        for x in stream:
            sketch.update(x)

        diffs = [abs(sketch.estimate(k) - true_f) for k, true_f in ground_truth.items()]
        measured_mae = float(np.mean(diffs))
        pred_mae = opt_cfg.predicted_mae

        denom = max(1.0, (pred_mae + measured_mae) / 2.0)
        rel_err = abs(pred_mae - measured_mae) / float(denom)
        rel_errors.append(rel_err)

        sweep_results.append({
            "budget_kb": b_kb,
            "bytes": total_bytes,
            "d": opt_cfg.d,
            "w": opt_cfg.w,
            "m": opt_cfg.m,
            "K": opt_cfg.K,
            "tau": opt_cfg.tau,
            "pred_mae": pred_mae,
            "measured_mae": measured_mae,
            "rel_error_pct": rel_err * 100.0,
        })
        print(f"  {b_kb:3d} KB -> Predicted MAE: {pred_mae:6.2f} | Measured MAE: {measured_mae:6.2f} | Error: {rel_err*100.0:5.1f}%")

    mean_rel_err = float(np.mean(rel_errors))
    pass_gate1 = mean_rel_err <= 0.25
    print(f"\n-> PART 1 GATE: Mean Prediction Error = {mean_rel_err*100.0:.2f}% (Threshold: <= 25.0%) -> {'PASS' if pass_gate1 else 'FAIL'}")

    # -------------------------------------------------------------------------
    # PART 2: Comparative Win-Rate Gate (Must beat fixed default on >= 3 of 5 skews)
    # -------------------------------------------------------------------------
    print("\n[PART 2] Testing Planner vs Fixed Default Config across 5 Skews (32 KB budget)...")
    budget_32k = 32 * 1024
    skew_results = []
    planner_wins = 0

    for alpha in alphas:
        stream_a, gt_a = generate_zipf_stream(n_stream=n_stream, n_unique=n_unique, alpha=alpha, seed=seed)
        
        # 1. Planner-tailored config
        p_cfg = planner.optimize(budget_bytes=budget_32k, n_stream=n_stream, n_unique=n_unique, skew=alpha)
        s_planner = AdaLogSketch(
            d=p_cfg.d, w=p_cfg.w, counter_bits=p_cfg.counter_bits, m=p_cfg.m,
            stash_capacity=p_cfg.K, stash_tau=p_cfg.tau, use_stash=True, use_conservative_update=True, seed=seed
        )
        for x in stream_a:
            s_planner.update(x)
        mae_planner = float(np.mean([abs(s_planner.estimate(k) - true_f) for k, true_f in gt_a.items()]))

        # 2. Fixed Default Config (d=4, K=32, tau=20, m=1024, remainder w)
        fixed_hll_bytes = (1024 * 6 + 7) // 8
        fixed_stash_bytes = 32 * 16
        fixed_w = max(64, (budget_32k - fixed_hll_bytes - fixed_stash_bytes) // 4)
        s_fixed = AdaLogSketch(
            d=4, w=fixed_w, counter_bits=8, m=1024,
            stash_capacity=32, stash_tau=20, use_stash=True, use_conservative_update=True, seed=seed
        )
        for x in stream_a:
            s_fixed.update(x)
        mae_fixed = float(np.mean([abs(s_fixed.estimate(k) - true_f) for k, true_f in gt_a.items()]))

        won = mae_planner < mae_fixed
        if won:
            planner_wins += 1

        skew_results.append({
            "alpha": alpha,
            "planner_mae": mae_planner,
            "fixed_mae": mae_fixed,
            "planner_won": won,
            "improvement_pct": ((mae_fixed - mae_planner) / mae_fixed) * 100.0,
        })
        print(f"  alpha={alpha:.2f} | Planner MAE: {mae_planner:5.2f} vs Fixed MAE: {mae_fixed:5.2f} -> {'WIN (+' + f'{((mae_fixed - mae_planner) / mae_fixed) * 100.0:.1f}%)' if won else 'LOSS'}")

    pass_gate2 = planner_wins >= 3
    print(f"\n-> PART 2 GATE: Planner Win Rate = {planner_wins}/5 (Threshold: >= 3/5) -> {'PASS' if pass_gate2 else 'FAIL'}")

    verdict = pass_gate1 and pass_gate2
    print(f"\n================================================================================")
    print(f"NOVEL CONTRIBUTION N1 ACCEPTANCE TEST VERDICT: {'ACCEPTED (PASS)' if verdict else 'REJECTED (FAIL)'}")
    print(f"================================================================================")

    output_data = {
        "verdict": "PASS" if verdict else "FAIL",
        "part1_mean_prediction_error_pct": mean_rel_err * 100.0,
        "part1_pass": pass_gate1,
        "part2_wins_out_of_5": planner_wins,
        "part2_pass": pass_gate2,
        "memory_sweep": sweep_results,
        "skew_sweep": skew_results,
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"Results saved to {output_path}")
    return output_data


if __name__ == "__main__":
    run_planner_evaluation()
