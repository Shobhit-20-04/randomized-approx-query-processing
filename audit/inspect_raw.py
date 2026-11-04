import json

with open(r'D:\VIT\DSA Case Study\randomized-approx-query-processing\results\raw\exp2_skew_sweep.json') as f:
    data = json.load(f)

print("EXP 2 RAW DATA:")
for row in data:
    a = row['alpha']
    ad = row['adalog_mae']
    ds = row['disjoint_stash_mae']
    red = (1.0 - ad / ds) * 100.0
    print(f"alpha: {a:.2f} | AdaLog MAE: {ad:.4f} | Disjoint+Stash MAE: {ds:.4f} | Reduction: {red:.2f}%")

with open(r'D:\VIT\DSA Case Study\randomized-approx-query-processing\results\raw\exp1_memory_sweep.json') as f:
    d1 = json.load(f)

print("\nEXP 1 RAW DATA (Summary by Budget):")
for row in d1:
    b = row.get('budget_kb')
    m = row.get('method')
    mae = row.get('point_mae')
    are = row.get('point_are')
    und = row.get('point_underestimates')
    fpr = row.get('bloom_fpr')
    re = row.get('hll_relative_error')
    print(f"Budget: {b} KB | Method: {m:<15} | MAE: {mae} | ARE: {are} | Under: {und} | FPR: {fpr} | HLL RE: {re}")
