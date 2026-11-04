import json

with open(r'D:\VIT\DSA Case Study\randomized-approx-query-processing\results\raw\exp1_memory_sweep.json') as f:
    d = json.load(f)

print("EXP 1 RAW DATA ALL ROWS:")
for row in d:
    m = row['model']
    b = row['budget_kb']
    by = row['bytes']
    mae = f"{row['mae']:7.4f}" if row['mae'] is not None else "   None"
    fpr = f"{row['fpr']:6.4f}" if row['fpr'] is not None else "  None"
    rse = f"{row['rse']:6.4f}" if row['rse'] is not None else "  None"
    und = row['underestimates']
    rec = f"{row['top_k_recall']:6.4f}" if row.get('top_k_recall') is not None else "  None"
    print(f"Budget: {b:3d} KB ({by:6d} B) | {m:<20} | MAE: {mae} | FPR: {fpr} | RSE: {rse} | Under: {und} | TopK-Rec: {rec}")
