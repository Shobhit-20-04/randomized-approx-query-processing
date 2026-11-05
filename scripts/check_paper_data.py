import json
import re
import os

def check_all_numbers():
    with open('paper_local/latex/main.tex', 'r', encoding='utf-8') as f:
        latex = f.read()

    print("=" * 80)
    print("VERIFYING EXP 1 (MEMORY SWEEP): TABLE 4 & TEXT")
    print("=" * 80)
    with open('results/raw/exp1_memory_sweep.json', 'r', encoding='utf-8') as f:
        raw1 = json.load(f)

    # Let's inspect raw1 keys and structures
    print(f"exp1 raw type: {type(raw1)}")
    if isinstance(raw1, list):
        print(f"Total items in exp1 list: {len(raw1)}")
        sample = raw1[0]
        print(f"Sample keys: {list(sample.keys())}")
    elif isinstance(raw1, dict):
        print(f"exp1 keys: {list(raw1.keys())}")

    print("\n" + "=" * 80)
    print("VERIFYING EXP 2 (SKEW SWEEP): TABLE 6")
    print("=" * 80)
    with open('results/raw/exp2_skew_sweep.json', 'r', encoding='utf-8') as f:
        raw2 = json.load(f)
    print(f"exp2 raw type: {type(raw2)}")
    if isinstance(raw2, list):
        for item in raw2:
            print(f"alpha={item.get('alpha')}: adalog_mae={item.get('adalog_mae')}, disjoint={item.get('disjoint_mae')}, elastic={item.get('elastic_mae')}")
    elif isinstance(raw2, dict):
        print(f"exp2 keys: {list(raw2.keys())}")

    print("\n" + "=" * 80)
    print("VERIFYING EXP 3 (LATENCY & THROUGHPUT): TABLE 7")
    print("=" * 80)
    with open('results/raw/exp3_latency_benchmark.json', 'r', encoding='utf-8') as f:
        raw3 = json.load(f)
    print(json.dumps(raw3, indent=2))

    print("\n" + "=" * 80)
    print("VERIFYING EXP 4 (ABLATIONS): TABLE 8")
    print("=" * 80)
    with open('results/raw/exp4_ablations.json', 'r', encoding='utf-8') as f:
        raw4 = json.load(f)
    print(json.dumps(raw4, indent=2))

    print("\n" + "=" * 80)
    print("VERIFYING EXP 8 (COMPRESSION)")
    print("=" * 80)
    with open('results/raw/exp8_compression.json', 'r', encoding='utf-8') as f:
        raw8 = json.load(f)
    print(json.dumps(raw8, indent=2))

if __name__ == '__main__':
    check_all_numbers()
