import json

with open("results/raw/exp1_memory_sweep.json") as f:
    data = json.load(f)

for r in data:
    if r["budget_kb"] in [8, 16, 32, 64, 128]:
        m = r["model"]
        mae = r["mae"]
        mae_std = r["mae_std"]
        fpr = f"{r['fpr']*100:.2f}%" if r["fpr"] is not None else "N/A"
        rse = f"{r['rse']:.4f}" if r["rse"] is not None else "N/A"
        p = f"{r['top_k_precision']:.3f}"
        rec = f"{r['top_k_recall']:.3f}"
        und = r["underestimates"]
        print(f"{r['budget_kb']:3d} KB | {m:16s} | MAE: {mae:6.3f} +/- {mae_std:5.3f} | FPR: {fpr:7s} | RSE: {rse:6s} | P: {p} R: {rec} | Under: {und}")
