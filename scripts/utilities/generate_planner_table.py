"""Generate comprehensive predicted-vs-measured table for AdaLog-Planner across memory budgets and skews.
Computes:
- Predicted MAE, FPR, RSE
- Measured MAE, FPR, RSE across seeds
- Percentage relative prediction errors
"""

import json
import math
import os
import sys
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from planner.planner import AdaLogPlanner
from adalog.sketch import AdaLogSketch
from experiments.datasets import generate_zipf_stream

SEEDS = [42, 100, 2024]
N_STREAM = 300_000
N_UNIQUE = 100_000
ALPHA = 1.25
BUDGETS_KB = [8, 16, 32, 64, 128, 256]

planner = AdaLogPlanner()
table_data = []

print("Evaluating Planner: Predicted vs Measured Across Budgets...")
for b_kb in BUDGETS_KB:
    total_bytes = b_kb * 1024
    opt_cfg = planner.optimize(budget_bytes=total_bytes, n_stream=N_STREAM, n_unique=N_UNIQUE, skew=ALPHA)
    
    # Measured across seeds
    maes, fprs, rses = [], [], []
    for s in SEEDS:
        stream, gt = generate_zipf_stream(n_stream=N_STREAM, n_unique=N_UNIQUE, alpha=ALPHA, seed=s)
        actual_n = len(gt)
        uninserted = [f"absent_item_{i}_{s}" for i in range(10_000)]
        
        sketch = AdaLogSketch(
            d=opt_cfg.d, w=opt_cfg.w, counter_bits=opt_cfg.counter_bits,
            m=opt_cfg.m, stash_capacity=opt_cfg.K, stash_tau=opt_cfg.tau,
            use_stash=True, use_conservative_update=True, seed=s
        )
        for x in stream: sketch.update(x)
        
        errs = [abs(sketch.estimate(k) - tf) for k, tf in gt.items()]
        maes.append(float(np.mean(errs)))
        fprs.append(sum(1 for uk in uninserted if sketch.contains(uk)) / float(len(uninserted)))
        rses.append(abs(sketch.cardinality() - actual_n) / float(actual_n))
        
    meas_mae = float(np.mean(maes))
    meas_fpr = float(np.mean(fprs))
    meas_rse = float(np.mean(rses))
    
    # Predicted metrics
    pred_mae = opt_cfg.predicted_mae
    pred_fpr = (1.0 - math.exp(-opt_cfg.d * N_UNIQUE / float(opt_cfg.w))) ** opt_cfg.d
    pred_rse = 1.04 / math.sqrt(opt_cfg.m)
    
    mae_err_pct = abs(pred_mae - meas_mae) / meas_mae * 100.0 if meas_mae > 0 else 0.0
    fpr_err_pct = abs(pred_fpr - meas_fpr) / meas_fpr * 100.0 if meas_fpr > 0 else 0.0
    rse_err_pct = abs(pred_rse - meas_rse) / meas_rse * 100.0 if meas_rse > 0 else 0.0
    
    entry = {
        "budget_kb": b_kb,
        "d": opt_cfg.d,
        "w": opt_cfg.w,
        "m": opt_cfg.m,
        "K": opt_cfg.K,
        "tau": opt_cfg.tau,
        "pred_mae": round(pred_mae, 4),
        "measured_mae": round(meas_mae, 4),
        "mae_rel_err_pct": round(mae_err_pct, 2),
        "pred_fpr": round(pred_fpr, 4),
        "measured_fpr": round(meas_fpr, 4),
        "fpr_rel_err_pct": round(fpr_err_pct, 2),
        "pred_rse": round(pred_rse, 4),
        "measured_rse": round(meas_rse, 4),
        "rse_rel_err_pct": round(rse_err_pct, 2),
    }
    table_data.append(entry)
    print(f"  Budget {b_kb:3d} KB -> MAE: Pred={pred_mae:6.3f}, Meas={meas_mae:6.3f} (Err: {mae_err_pct:5.2f}%) | FPR: Pred={pred_fpr*100:5.2f}%, Meas={meas_fpr*100:5.2f}% | RSE: Pred={pred_rse:6.4f}, Meas={meas_rse:6.4f}")

out_file = os.path.join(PROJECT_ROOT, "results", "raw", "exp5_planner_eval.json")
mean_mae_err = float(np.mean([e["mae_rel_err_pct"] for e in table_data]))
result = {
    "mean_mae_prediction_error_pct": round(mean_mae_err, 2),
    "budget_sweep": table_data
}
with open(out_file, "w") as f:
    json.dump(result, f, indent=2)

print(f"\nPlanner evaluation complete! Mean MAE prediction error: {mean_mae_err:.2f}%")
