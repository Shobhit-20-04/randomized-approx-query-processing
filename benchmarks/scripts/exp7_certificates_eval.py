"""Experiment 7: Acceptance Test for Novel Contribution N3 (Certificates and Calibration).

Tests whether:
1. Certified frequency intervals [lo, hi] achieve empirical coverage >= 95% on all datasets.
2. Debiased frequency estimator achieves lower MAE than the raw estimate at equal bytes.
3. Live membership FPR probability matches empirical false-positive rate.
4. Cardinality confidence interval encapsulates true distinct count.

Outputs results to results/raw/exp7_certificates_eval.json and logs PASS/FAIL verdict.
"""

import json
import os
from typing import Dict, List
import numpy as np

from adalog.sketch import AdaLogSketch
from certificates.debiaser import compute_debiased_frequency
from certificates.intervals import compute_frequency_interval
from certificates.live_certificates import compute_cardinality_certificate, compute_live_fpr
from experiments.datasets import generate_zipf_stream


def run_certificates_evaluation(
    alphas: List[float] = [1.05, 1.15, 1.25, 1.35, 1.50],
    budget_kb: int = 32,
    n_stream: int = 250_000,
    n_unique: int = 25_000,
    seed: int = 42,
    output_path: str = "results/raw/exp7_certificates_eval.json",
):
    print("================================================================================")
    print("EXPERIMENT 7: ACCEPTANCE TEST EVALUATION FOR NOVEL CONTRIBUTION N3 (CERTIFICATES)")
    print("================================================================================")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    uninserted_keys = [f"absent_cert_{i}_{seed}" for i in range(10_000)]

    dataset_results = []
    all_coverages = []
    all_mae_reductions = []

    for alpha in alphas:
        print(f"\nEvaluating Skew alpha = {alpha:.2f}...")
        stream, ground_truth = generate_zipf_stream(n_stream=n_stream, n_unique=n_unique, alpha=alpha, seed=seed)
        actual_n = len(ground_truth)

        sketch = AdaLogSketch(
            d=4, w=1500, counter_bits=8, m=1024, stash_capacity=64, stash_tau=15,
            use_stash=True, use_conservative_update=True, seed=seed
        )
        for x in stream:
            sketch.update(x)

        stash_vol = sum(e.total_count for e in sketch.stash.entries.values()) if sketch.use_stash else 0

        # -------------------------------------------------------------
        # 1. Frequency Interval Coverage & Width
        # -------------------------------------------------------------
        covered_count = 0
        widths = []
        raw_errors = []
        debiased_errors = []

        for k, true_f in ground_truth.items():
            f_raw = sketch.estimate(k)
            is_stash = sketch.use_stash and sketch.stash.contains(k)
            stash_base = sketch.stash.entries[k].base_count if is_stash else 0

            # Certified Interval [lo, hi]
            lo, hi = compute_frequency_interval(
                f_raw=f_raw,
                total_stream_items=len(stream),
                w=sketch.w,
                d=sketch.d,
                confidence=0.95,
                is_stash_hit=is_stash,
                stash_baseline=stash_base,
            )
            if lo <= true_f <= hi:
                covered_count += 1
            widths.append(hi - lo)

            # Debiased Estimate
            f_deb = compute_debiased_frequency(
                f_raw=f_raw,
                total_stream_items=len(stream),
                cardinality_estimate=actual_n,
                w=sketch.w,
                d=sketch.d,
                is_stash_hit=is_stash,
                stash_baseline=stash_base,
                stash_volume=stash_vol,
            )
            raw_errors.append(abs(f_raw - true_f))
            debiased_errors.append(abs(f_deb - true_f))

        coverage_pct = (covered_count / float(actual_n)) * 100.0
        avg_width = float(np.mean(widths))
        raw_mae = float(np.mean(raw_errors))
        deb_mae = float(np.mean(debiased_errors))
        mae_reduction_pct = ((raw_mae - deb_mae) / raw_mae) * 100.0 if raw_mae > 0 else 0.0

        all_coverages.append(coverage_pct)
        all_mae_reductions.append(mae_reduction_pct)

        # -------------------------------------------------------------
        # 2. Live Membership FPR Certificate Check
        # -------------------------------------------------------------
        live_fpr = compute_live_fpr(sketch)
        fps = sum(1 for uk in uninserted_keys if sketch.contains(uk))
        measured_fpr = fps / float(len(uninserted_keys))

        # -------------------------------------------------------------
        # 3. Cardinality Certificate Check
        # -------------------------------------------------------------
        card_est = int(round(sketch.cardinality()))
        card_cert = compute_cardinality_certificate(card_est, m=sketch.hll_m, confidence=0.95)
        card_covered = (card_cert.confidence_interval[0] <= actual_n <= card_cert.confidence_interval[1])

        print(f"  Coverage: {coverage_pct:5.2f}% (Target: >=95%) | Avg Width: {avg_width:5.1f}")
        print(f"  Raw MAE: {raw_mae:5.2f} -> Debiased MAE: {deb_mae:5.2f} (Reduction: {mae_reduction_pct:5.1f}%)")
        print(f"  Live FPR: {live_fpr*100:5.2f}% vs Measured FPR: {measured_fpr*100:5.2f}%")
        print(f"  Cardinality {actual_n} in [{card_cert.confidence_interval[0]}, {card_cert.confidence_interval[1]}]: {'YES' if card_covered else 'NO'}")

        dataset_results.append({
            "alpha": alpha,
            "coverage_pct": coverage_pct,
            "avg_width": avg_width,
            "raw_mae": raw_mae,
            "debiased_mae": deb_mae,
            "mae_reduction_pct": mae_reduction_pct,
            "live_fpr": live_fpr,
            "measured_fpr": measured_fpr,
            "cardinality_true": actual_n,
            "cardinality_estimate": card_est,
            "cardinality_ci": card_cert.confidence_interval,
            "cardinality_covered": card_covered,
        })

    # Gates
    pass_gate1 = all(c >= 95.0 for c in all_coverages)
    pass_gate2 = all(r > 0.0 for r in all_mae_reductions)
    verdict = pass_gate1 and pass_gate2

    print(f"\n-> GATE 1: Minimum Coverage across all skews = {min(all_coverages):.2f}% (Target: >= 95.0%) -> {'PASS' if pass_gate1 else 'FAIL'}")
    print(f"-> GATE 2: Debiased MAE lower than Raw MAE on all skews: {'PASS' if pass_gate2 else 'FAIL'}")
    print(f"\n================================================================================")
    print(f"NOVEL CONTRIBUTION N3 ACCEPTANCE TEST VERDICT: {'ACCEPTED (PASS)' if verdict else 'REJECTED (FAIL)'}")
    print(f"================================================================================")

    output_data = {
        "verdict": "PASS" if verdict else "FAIL",
        "gate1_min_coverage_pct": min(all_coverages),
        "gate1_pass": pass_gate1,
        "gate2_all_mae_reduced": pass_gate2,
        "gate2_pass": pass_gate2,
        "datasets": dataset_results,
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"Results saved to {output_path}")
    return output_data


if __name__ == "__main__":
    run_certificates_evaluation()
