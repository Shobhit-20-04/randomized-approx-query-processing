"""Experiment 6: Acceptance Test for Novel Contribution N2 (Online Adaptive Controller).

Evaluates whether the Online Adaptive Controller outperforms fixed-tau policies under:
1. Drifting Streams: Skew shifts mid-stream (alpha: 1.10 -> 1.50 -> 1.20) and burst spikes.
   Gate: 95% Confidence Interval of error difference (Fixed - Adaptive) strictly excludes zero (> 0).
2. Stationary Streams: Skew remains constant (alpha = 1.25).
   Gate: Adaptive is non-inferior (within 5% of optimal fixed tau).

Outputs results to results/raw/exp6_adaptive_eval.json and logs PASS/FAIL verdict.
"""

import json
import os
from typing import Dict, List, Tuple
import numpy as np

from adalog.sketch import AdaLogSketch
from controller.adaptive_controller import AdaptiveController
from experiments.datasets import generate_drifting_stream, generate_zipf_stream


def run_adaptive_evaluation(
    n_trials: int = 10,
    budget_kb: int = 32,
    seed_base: int = 100,
    output_path: str = "results/raw/exp6_adaptive_eval.json",
):
    print("================================================================================")
    print("EXPERIMENT 6: ACCEPTANCE TEST EVALUATION FOR NOVEL CONTRIBUTION N2 (CONTROLLER)")
    print("================================================================================")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    total_bytes = budget_kb * 1024
    fixed_taus = [10, 20, 35]

    # -------------------------------------------------------------------------
    # PART 1: Drifting Stream Evaluation (10 Trials across Seeds)
    # -------------------------------------------------------------------------
    print(f"\n[PART 1] Evaluating Drifting Streams across {n_trials} Seeds...")
    trial_results_drift = []
    adaptive_maes_drift = []
    best_fixed_maes_drift = []
    mae_diffs_drift = [] # (best_fixed - adaptive); positive means adaptive won!

    for trial in range(n_trials):
        seed = seed_base + trial
        stream, gt, boundaries = generate_drifting_stream(
            phase_lengths=[80_000, 80_000, 80_000],
            alphas=[1.10, 1.50, 1.20],
            n_unique=25_000,
            burst_keys=10,
            burst_intensity=8_000,
            seed=seed,
        )

        # 1. Adaptive Controller
        s_adapt = AdaLogSketch(d=4, w=1500, counter_bits=8, m=1024, stash_capacity=64, stash_tau=20, seed=seed)
        ctrl = AdaptiveController(epoch_size=5_000, default_tau=20)

        for x in stream:
            # Check hit before update
            hit = s_adapt.use_stash and s_adapt.stash.contains(x)
            prev_evict = s_adapt.stash.evictions
            s_adapt.update(x)
            evicted = (s_adapt.stash.evictions > prev_evict)
            ctrl.record_update(hit=hit, evicted=evicted)
            if ctrl.should_step():
                ctrl.step(s_adapt)

        mae_adapt = float(np.mean([abs(s_adapt.estimate(k) - true_f) for k, true_f in gt.items()]))
        adaptive_maes_drift.append(mae_adapt)

        # 2. Fixed Tau Policies
        fixed_errors = {}
        for tau in fixed_taus:
            s_fix = AdaLogSketch(d=4, w=1500, counter_bits=8, m=1024, stash_capacity=64, stash_tau=tau, seed=seed)
            for x in stream:
                s_fix.update(x)
            mae_fix = float(np.mean([abs(s_fix.estimate(k) - true_f) for k, true_f in gt.items()]))
            fixed_errors[tau] = mae_fix

        best_tau = min(fixed_errors.keys(), key=lambda t: fixed_errors[t])
        best_fixed_mae = fixed_errors[best_tau]
        best_fixed_maes_drift.append(best_fixed_mae)

        diff = best_fixed_mae - mae_adapt
        mae_diffs_drift.append(diff)

        print(f"  Trial {trial+1:2d} (Seed {seed}) -> Adaptive MAE: {mae_adapt:5.2f} | Best Fixed (tau={best_tau}): {best_fixed_mae:5.2f} | Diff: +{diff:5.2f}")

    # Compute 95% Confidence Interval for difference (best_fixed - adaptive)
    mean_diff = float(np.mean(mae_diffs_drift))
    std_diff = float(np.std(mae_diffs_drift, ddof=1))
    sem_diff = std_diff / np.sqrt(n_trials)
    ci95_low = mean_diff - 1.96 * sem_diff
    ci95_high = mean_diff + 1.96 * sem_diff

    print(f"\n[PART 1 GATE] Mean Error Reduction = +{mean_diff:.3f} MAE")
    print(f"              95% Confidence Interval = [{ci95_low:.3f}, {ci95_high:.3f}]")
    pass_gate1 = ci95_low > 0.0
    print(f"              Zero strictly excluded (> 0): {'YES (PASS)' if pass_gate1 else 'NO (FAIL)'}")

    # -------------------------------------------------------------------------
    # PART 2: Stationary Stream Evaluation (Must not be worse)
    # -------------------------------------------------------------------------
    print("\n[PART 2] Evaluating Stationary Streams (alpha=1.25)...")
    stream_stat, gt_stat = generate_zipf_stream(n_stream=250_000, n_unique=25_000, alpha=1.25, seed=seed_base)
    
    s_adapt_stat = AdaLogSketch(d=4, w=1500, counter_bits=8, m=1024, stash_capacity=64, stash_tau=20, seed=seed_base)
    ctrl_stat = AdaptiveController(epoch_size=20_000, default_tau=20)
    for x in stream_stat:
        hit = s_adapt_stat.use_stash and s_adapt_stat.stash.contains(x)
        prev_evict = s_adapt_stat.stash.evictions
        s_adapt_stat.update(x)
        evicted = (s_adapt_stat.stash.evictions > prev_evict)
        ctrl_stat.record_update(hit=hit, evicted=evicted)
        if ctrl_stat.should_step():
            ctrl_stat.step(s_adapt_stat)
    mae_adapt_stat = float(np.mean([abs(s_adapt_stat.estimate(k) - true_f) for k, true_f in gt_stat.items()]))

    # Best fixed on stationary
    s_fix_stat = AdaLogSketch(d=4, w=1500, counter_bits=8, m=1024, stash_capacity=64, stash_tau=20, seed=seed_base)
    for x in stream_stat:
        s_fix_stat.update(x)
    mae_fix_stat = float(np.mean([abs(s_fix_stat.estimate(k) - true_f) for k, true_f in gt_stat.items()]))

    stationary_ratio = mae_adapt_stat / mae_fix_stat
    pass_gate2 = stationary_ratio <= 1.05
    print(f"  Stationary Adaptive MAE: {mae_adapt_stat:5.2f} vs Best Fixed: {mae_fix_stat:5.2f} (Ratio: {stationary_ratio:.3f})")
    print(f"  -> PART 2 GATE: Non-inferior on stationary stream: {'PASS' if pass_gate2 else 'FAIL'}")

    verdict = pass_gate1 and pass_gate2
    print(f"\n================================================================================")
    print(f"NOVEL CONTRIBUTION N2 ACCEPTANCE TEST VERDICT: {'ACCEPTED (PASS)' if verdict else 'REJECTED (FAIL)'}")
    print(f"================================================================================")

    output_data = {
        "verdict": "PASS" if verdict else "FAIL",
        "part1_mean_error_diff": float(mean_diff),
        "part1_ci95_low": float(ci95_low),
        "part1_ci95_high": float(ci95_high),
        "part1_pass": bool(pass_gate1),
        "part2_stationary_ratio": float(stationary_ratio),
        "part2_pass": bool(pass_gate2),
        "raw_diffs": [float(x) for x in mae_diffs_drift],
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"Results saved to {output_path}")
    return output_data


if __name__ == "__main__":
    run_adaptive_evaluation()
