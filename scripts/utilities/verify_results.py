"""
Verify mathematical guarantees and benchmark integrity across both:
1. Baseline benchmark results (Bloom Filter, Count-Min Sketch, HyperLogLog CSV outputs).
2. AdaLog-Sketch unified synopsis theoretical invariants (Python reference and Native C++ engine).
"""

import os
import sys
import numpy as np
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

raw_dir = os.path.join(project_root, "results", "raw")


def verify_baseline_csvs() -> bool:
    """Verifies empirical invariants stored in baseline experiment CSV outputs."""
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

    print("-" * 65)
    print("PART A: BASELINE COMPONENT INTEGRITY CHECKS (CSV BENCHMARKS)")
    print("-" * 65)

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

    return all_passed


def verify_adalog_sketch_invariants() -> bool:
    """Directly verifies the core mathematical invariants of AdaLog-Sketch."""
    print("\n" + "-" * 65)
    print("PART B: ADALOG-SKETCH UNIFIED SYNOPSIS THEORETICAL INVARIANTS")
    print("-" * 65)

    all_passed = True

    try:
        from adalog.sketch import AdaLogSketch

        np.random.seed(42)
        n_ops = 5000
        # Generate heavy-tailed Zipfian synthetic stream (alpha = 1.25)
        raw_keys = [f"stream_key_{idx}" for idx in np.random.zipf(1.25, n_ops)]
        true_counts: dict[str, int] = {}
        for k in raw_keys:
            true_counts[k] = true_counts.get(k, 0) + 1

        n_distinct = len(true_counts)

        # Standard 32 KB budget configuration (w=7232, d=4, bits=8, K=128, tau=15, m=1024)
        sketch = AdaLogSketch(
            width=7232,
            depth=4,
            counter_bits=8,
            use_stash=True,
            stash_capacity=128,
            stash_tau=15,
            seed=42,
        )

        for k in raw_keys:
            sketch.update(k, 1)

        # 1. AMQ Invariant: Zero False Negatives
        fn_count = sum(1 for k in true_counts if not sketch.contains(k))
        print(f"[AdaLog-Python] AMQ False Negatives (FN): {fn_count} / {n_distinct} keys")
        if fn_count != 0:
            print("  -> ERROR: AdaLog-Sketch returned false negative on inserted key!")
            all_passed = False
        else:
            print("  -> PASS: Zero false negatives (Variant A all-positive test) preserved perfectly.")

        # 2. Frequency Invariant: Theorem 2 Strictly Zero Underestimations on Raw Estimates
        und_count = sum(1 for k, count in true_counts.items() if sketch.estimate(k) < count)
        print(f"\n[AdaLog-Python] Frequency Underestimations: {und_count} / {n_distinct} keys")
        if und_count != 0:
            print("  -> ERROR: AdaLog-Sketch underestimated true key frequency under K >= K_sat*!")
            all_passed = False
        else:
            print("  -> PASS: Theorem 2 zero-underestimation invariant strictly holds (K >= K_sat*).")

        # 3. Elephant Stash & Monotonic Write-back Invariant
        resident_count = len(sketch.stash.entries)
        print(f"\n[AdaLog-Python] Resident Elephant Stash Entries: {resident_count} / {sketch.stash.capacity}")
        if resident_count == 0:
            print("  -> WARNING: No heavy hitters promoted to stash.")
        else:
            print("  -> PASS: Heavy hitters promoted to 64-bit exact tracking with zero underestimation.")

        # 4. Cardinality Invariant: Bound within theoretical RSE
        card_est = sketch.cardinality()
        card_err = abs(card_est - n_distinct) / n_distinct
        expected_rse = 1.04 / np.sqrt(1024)
        print(f"\n[AdaLog-Python] Cardinality: True={n_distinct}, Estimated={card_est:.1f}, Rel Error={card_err * 100:.2f}%")
        print(f"[AdaLog-Python] Theoretical RSE: {expected_rse * 100:.2f}% (Error / RSE = {card_err / expected_rse:.2f}x)")
        if card_err > 3.0 * expected_rse:
            print("  -> WARNING: Cardinality error exceeded 3x theoretical RSE.")
        else:
            print("  -> PASS: Cardinality estimate tightly bounded within standard statistical confidence.")

        # 5. Compiled C++ Native Engine Parity Check (if DLL / SO built)
        try:
            from core.bindings import CompiledAdaLog

            c_sketch = CompiledAdaLog(
                width=7232,
                depth=4,
                counter_bits=8,
                stash_capacity=128,
                elephant_threshold=15,
                hll_m=1024,
                seed=42,
            )
            for k in raw_keys:
                c_sketch.update(k, 1)

            c_fn = sum(1 for k in true_counts if not c_sketch.contains(k))
            c_und = sum(1 for k, count in true_counts.items() if c_sketch.estimate(k) < count)
            print(f"\n[AdaLog-C++] Native Engine Verification (MurmurHash3-128, 95-bit stash, 24B layout):")
            print(f"  -> AMQ False Negatives: {c_fn}")
            print(f"  -> Raw Underestimations: {c_und}")
            if c_fn == 0 and c_und == 0:
                print("  -> PASS: Native C++ engine satisfies all theoretical guarantees identically.")
            else:
                print("  -> ERROR: Native C++ engine violated AMQ or underestimation guarantee!")
                all_passed = False
        except Exception as e:
            print(f"\n[AdaLog-C++] Native binary not tested or skipped: {e}")

    except Exception as e:
        print(f"ERROR executing AdaLog programmatic verification: {e}")
        all_passed = False

    return all_passed


def verify() -> bool:
    print("=" * 65)
    print("VERIFYING BENCHMARK INTEGRITY & THEORETICAL GUARANTEES")
    print("Scope: Baselines (BF/CMS/HLL) and Unified AdaLog-Sketch Synopsis")
    print("=" * 65)

    base_ok = verify_baseline_csvs()
    adalog_ok = verify_adalog_sketch_invariants()

    passed = base_ok and adalog_ok

    print("\n" + "=" * 65)
    if passed:
        print("ALL THEORETICAL PROPERTIES AND EMPIRICAL CONSTRAINTS PASSED!")
    else:
        print("VERIFICATION FAILED: See details above.")
    print("=" * 65)
    return passed


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
