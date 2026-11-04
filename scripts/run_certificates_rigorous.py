"""Rerun Debiasing and Empirical Confidence Intervals on N=300,000, |U|=100,000, K=128, w=7232 at 32 KB.
Evaluates:
- Raw MAE vs Debiased MAE across skews
- Empirical coverage of [lo, hi] confidence interval
- Average interval width
- Distinct cardinality coverage
"""

import json
import os
import sys
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from adalog.sketch import AdaLogSketch
from certificates.debiaser import compute_debiased_frequency
from certificates.intervals import compute_frequency_interval
from certificates.live_certificates import compute_cardinality_certificate, compute_live_fpr
from experiments.datasets import generate_zipf_stream

SEEDS = [42, 100, 2024]
ALPHAS = [1.05, 1.15, 1.25, 1.35, 1.50]
N_STREAM = 300_000
N_UNIQUE = 100_000

print("Evaluating Debiasing and Empirical Confidence Intervals across Skews (32 KB, w=7232, K=128)...")
results = []

for alpha in ALPHAS:
    cov_runs, width_runs, raw_mae_runs, debias_mae_runs, red_runs = [], [], [], [], []
    card_cov_runs = []

    for s in SEEDS:
        stream, gt = generate_zipf_stream(n_stream=N_STREAM, n_unique=N_UNIQUE, alpha=alpha, seed=s)
        actual_n = len(gt)

        sketch = AdaLogSketch(d=4, w=7232, counter_bits=8, m=1024, stash_capacity=128, stash_tau=15,
                              use_stash=True, use_conservative_update=True, seed=s)
        for x in stream: sketch.update(x)

        stash_vol = sum(e.total_count for e in sketch.stash.entries.values()) if sketch.use_stash else 0
        hll_card = sketch.cardinality()

        covered_count = 0
        widths = []
        raw_errs = []
        debias_errs = []

        for k, tf in gt.items():
            f_raw = sketch.estimate(k)
            raw_errs.append(abs(f_raw - tf))

            # Residual debiasing
            f_deb = compute_debiased_frequency(f_raw, sketch.d, sketch.width, N_STREAM, stash_vol, hll_card)
            debias_errs.append(abs(f_deb - tf))

            # Empirical confidence interval [lo, hi]
            lo, hi = compute_frequency_interval(f_raw, N_STREAM, sketch.width, sketch.d, confidence=0.95)
            if lo <= tf <= hi:
                covered_count += 1
            widths.append(hi - lo)

        cov_pct = (covered_count / float(len(gt))) * 100.0
        avg_w = float(np.mean(widths))
        r_mae = float(np.mean(raw_errs))
        d_mae = float(np.mean(debias_errs))
        red_pct = (r_mae - d_mae) / r_mae * 100.0

        cov_runs.append(cov_pct)
        width_runs.append(avg_w)
        raw_mae_runs.append(r_mae)
        debias_mae_runs.append(d_mae)
        red_runs.append(red_pct)

        card_cert = compute_cardinality_certificate(hll_card, sketch.hll_m)
        card_cov = card_cert.confidence_interval[0] <= actual_n <= card_cert.confidence_interval[1]
        card_cov_runs.append(card_cov)

    row = {
        "alpha": alpha,
        "raw_mae": round(float(np.mean(raw_mae_runs)), 3),
        "debiased_mae": round(float(np.mean(debias_mae_runs)), 3),
        "mae_reduction_pct": round(float(np.mean(red_runs)), 1),
        "coverage_pct": round(float(np.mean(cov_runs)), 2),
        "avg_width": round(float(np.mean(width_runs)), 1),
        "cardinality_covered": bool(all(card_cov_runs))
    }
    results.append(row)
    print(f"  alpha={alpha:.2f} -> Raw MAE={row['raw_mae']:6.3f}, Debiased MAE={row['debiased_mae']:6.3f} (Red: {row['mae_reduction_pct']:4.1f}%) | Cov={row['coverage_pct']:5.2f}%, Width={row['avg_width']:4.1f}")

out_file = os.path.join(PROJECT_ROOT, "results", "raw", "exp7_certificates_eval.json")
with open(out_file, "w") as f:
    json.dump({"datasets": results}, f, indent=2)
print(f"\nResults successfully written to {out_file}")
