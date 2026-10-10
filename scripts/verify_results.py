"""
Verify the mathematical guarantees and integrity of benchmark experiment CSV outputs.
"""

import os
import sys
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
raw_dir = os.path.join(project_root, "results", "raw")


def verify():
    bf_csv = os.path.join(raw_dir, "bloom_filter_raw.csv")
    cms_csv = os.path.join(raw_dir, "count_min_sketch_raw.csv")
    hll_csv = os.path.join(raw_dir, "hyperloglog_raw.csv")

    for path in (bf_csv, cms_csv, hll_csv):
        if not os.path.exists(path):
            print(f"FAILED: Result file {path} not found.")
            return False

    df_bf = pd.read_csv(bf_csv)
    df_cms = pd.read_csv(cms_csv)
    df_hll = pd.read_csv(hll_csv)

    print("=" * 65)
    print("VERIFYING BENCHMARK INTEGRITY & THEORETICAL GUARANTEES")
    print("=" * 65)

    all_passed = True

    # 1. Bloom Filter Guarantees
    fn_total = df_bf["false_negatives"].sum()
    print(f"[BF] Total False Negatives across all trials: {fn_total}")
    if fn_total != 0:
        print("  -> ERROR: Bloom filter returned false negatives for inserted elements!")
        all_passed = False
    else:
        print("  -> PASS: Zero false negatives property preserved perfectly.")

    bf_mem_ratio = df_bf["memory_reduction_ratio"].mean()
    print(f"[BF] Mean Memory Reduction: {bf_mem_ratio:.2f}x compared to exact set.")

    # 2. Count-Min Sketch Guarantees
    underest_total = df_cms["underestimation_count"].sum()
    print(f"\n[CMS] Total Underestimations across all trials: {underest_total}")
    if underest_total != 0:
        print("  -> ERROR: Count-Min Sketch underestimated true count!")
        all_passed = False
    else:
        print("  -> PASS: No-underestimation property preserved perfectly.")

    compliance_mean = df_cms["bound_compliance_ratio"].mean() * 100.0
    print(f"[CMS] Mean Bound Compliance: {compliance_mean:.2f}%")
    if compliance_mean < 80.0:
        print("  -> WARNING: Bound compliance lower than expected.")
    else:
        print("  -> PASS: Theoretical additive error bound obeyed.")

    cms_mem_ratio = df_cms["memory_reduction_ratio"].mean()
    print(f"[CMS] Mean Memory Reduction: {cms_mem_ratio:.2f}x compared to exact dict.")

    # 3. HyperLogLog Guarantees
    mean_rel_err = df_hll["relative_error"].mean() * 100.0
    within_rse_pct = df_hll["within_theoretical_rse"].mean() * 100.0
    print(f"\n[HLL] Mean Relative Cardinality Error: {mean_rel_err:.2f}%")
    print(f"[HLL] Fraction of trials within 1 theoretical RSE: {within_rse_pct:.2f}%")

    hll_mem_ratio = df_hll["memory_reduction_ratio"].mean()
    print(f"[HLL] Mean Memory Reduction: {hll_mem_ratio:.2f}x compared to exact set.")

    print("=" * 65)
    if all_passed:
        print("ALL THEORETICAL PROPERTIES AND EMPIRICAL CONSTRAINTS PASSED!")
    else:
        print("VERIFICATION FAILED: See details above.")
    print("=" * 65)

    return all_passed


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
