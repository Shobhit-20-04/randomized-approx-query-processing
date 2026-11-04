import json

with open("results/raw/exp4_ablations.json") as f:
    data = json.load(f)

print("Variant Name                   | Width | MAE +/- Std       | Peak | FPR (%)  | RSE")
print("-" * 85)
for r in data:
    name = r["name"]
    w = r["width"]
    mae = f"{r['mae']:.3f} +/- {r['mae_std']:.3f}"
    peak = r["peak_error"]
    fpr = f"{r['fpr']*100:.2f}%"
    rse = f"{r['rse']:.4f}"
    print(f"{name:30s} | {w:5d} | {mae:17s} | {peak:4d} | {fpr:8s} | {rse:6s}")
