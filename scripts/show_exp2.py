import json

with open("results/raw/exp2_skew_sweep.json") as f:
    data = json.load(f)

print("Skew alpha | AdaLog (Unified)  | Disjoint+Stash (Primary) | Disjoint-16bit (Overflow)   | Elastic MAE       | Augmented MAE")
print("-" * 125)
for r in data:
    alpha = r["alpha"]
    ad_mae = f"{r['adalog_mae']:.3f} +/- {r['adalog_mae_std']:.3f}"
    ds_mae = f"{r.get('disjoint_stash_mae', 0.0):.3f} +/- {r.get('disjoint_stash_mae_std', 0.0):.3f}"
    dis_mae = f"{r['disjoint_mae']:.3f} +/- {r['disjoint_mae_std']:.3f}"
    dis_ht = f"H: {r['disjoint_head_mae']:.1f}, T: {r['disjoint_tail_mae']:.2f}"
    el_mae = f"{r['elastic_mae']:.3f} +/- {r['elastic_mae_std']:.3f}"
    aug_mae = f"{r['augmented_mae']:.3f} +/- {r['augmented_mae_std']:.3f}"
    print(f"  {alpha:5.2f}    | {ad_mae:17s} | {ds_mae:24s} | {dis_mae:13s} ({dis_ht:14s}) | {el_mae:17s} | {aug_mae:17s}")
