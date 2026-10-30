"""
Master End-to-End Reproduction Pipeline for AdaLog-Sketch Paper.
Executes all benchmarks across >= 10 seeds, computes statistical confidence intervals,
records raw JSON results, updates publication figures, and outputs exact table data.
Strictly adheres to DSA (Data Structures and Algorithms) principles.
"""

from __future__ import annotations
import json
import math
import os
import subprocess
import sys
import time
from typing import Dict, List, Tuple
import numpy as np
from scipy import stats

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from adalog.sketch import AdaLogSketch
from baselines.disjoint_stack import DisjointBaselineStack, DisjointStashStack
from baselines.count_min_sketch import CountMinSketch
from baselines.elastic_sketch import ElasticSketch
from baselines.augmented_sketch import AugmentedSketch
from experiments.datasets import generate_zipf_stream

SEEDS = [42, 100, 2024, 31415, 27182, 16180, 57721, 14142, 17320, 22360]  # 10 seeds


def calc_stats(values: List[float]) -> Dict[str, float]:
    """Calculate mean, std, and 95% Student-t confidence interval."""
    arr = np.array(values, dtype=float)
    n = len(arr)
    mean = float(np.mean(arr))
    if n <= 1:
        return {"mean": mean, "std": 0.0, "ci95_lo": mean, "ci95_hi": mean}
    std = float(np.std(arr, ddof=1))
    t_crit = float(stats.t.ppf(0.975, df=n - 1))
    margin = t_crit * (std / math.sqrt(n))
    return {
        "mean": mean,
        "std": std,
        "ci95_lo": mean - margin,
        "ci95_hi": mean + margin,
    }


def evaluate_top_k(true_counts: Dict[str, int], estimated_top_k: List[tuple], k: int = 100) -> Tuple[float, float, float]:
    """Compute Precision, Recall, and F1 for top-k heavy hitter detection."""
    actual_top_k = set([item[0] for item in sorted(true_counts.items(), key=lambda kv: kv[1], reverse=True)[:k]])
    est_set = set([item[0] for item in estimated_top_k[:k]])
    if not est_set:
        return 0.0, 0.0, 0.0
    true_positives = len(actual_top_k.intersection(est_set))
    precision = true_positives / float(len(est_set))
    recall = true_positives / float(len(actual_top_k))
    f1 = 2.0 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


# ==============================================================================
# 1. C++ NATIVE BENCHMARK (Exp 3)
# ==============================================================================
def run_cpp_benchmark():
    print("\n" + "=" * 80)
    print("STEP 1: Compiling and Running Native C++ Ingestion Benchmark (Exp 3)")
    print("=" * 80)
    bench_exe = os.path.join(PROJECT_ROOT, "core", "bench_core.exe")
    bench_cpp = os.path.join(PROJECT_ROOT, "core", "bench_core.cpp")

    # Compile with g++ -O3
    cmd_compile = ["g++", "-O3", "-std=c++17", "-static", "-static-libgcc", "-static-libstdc++", "-o", bench_exe, bench_cpp]
    print(f"Compiling: {' '.join(cmd_compile)}")
    subprocess.run(cmd_compile, check=True, cwd=PROJECT_ROOT)

    # Run benchmark
    out_json = os.path.join(PROJECT_ROOT, "results", "raw", "exp3_latency_benchmark.json")
    cmd_run = [bench_exe, out_json]
    print(f"Running: {' '.join(cmd_run)}")
    subprocess.run(cmd_run, check=True, cwd=PROJECT_ROOT)
    print("C++ Latency benchmark complete.")


# ==============================================================================
# 2. EXPERIMENT 1: MEMORY SWEEP PARETO (8 KB to 512 KB, 10 Seeds)
# ==============================================================================
def run_exp1_memory_sweep():
    print("\n" + "=" * 80)
    print("STEP 2: Running Experiment 1 (Memory Sweep, 10 Seeds, K=128 Sized Stash)")
    print("=" * 80)
    budgets_kb = [8, 16, 32, 64, 128, 256, 512]
    n_stream = 300_000
    n_unique = 100_000
    alpha = 1.25

    out_file = os.path.join(PROJECT_ROOT, "results", "raw", "exp1_memory_sweep.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    summary_results = []

    for b_kb in budgets_kb:
        total_bytes = b_kb * 1024
        print(f"\n--- Budget {b_kb} KB ({total_bytes:,} bytes) across {len(SEEDS)} seeds ---")

        # Accumulators per model
        models_data = {
            "AdaLog-Sketch": {"mae": [], "are": [], "fpr": [], "cards": [], "f1": [], "prec": [], "rec": [], "under": []},
            "Disjoint-Stack": {"mae": [], "are": [], "fpr": [], "cards": [], "f1": [], "prec": [], "rec": [], "under": []},
            "Disjoint-Stash": {"mae": [], "are": [], "fpr": [], "cards": [], "f1": [], "prec": [], "rec": [], "under": []},
            "ElasticSketch": {"mae": [], "are": [], "fpr": [], "cards": [], "f1": [], "prec": [], "rec": [], "under": []},
            "AugmentedSketch": {"mae": [], "are": [], "fpr": [], "cards": [], "f1": [], "prec": [], "rec": [], "under": []},
        }

        true_cards = []

        for seed in SEEDS:
            stream, ground_truth = generate_zipf_stream(n_stream=n_stream, n_unique=n_unique, alpha=alpha, seed=seed)
            true_card = len(ground_truth)
            true_cards.append(true_card)
            uninserted = [f"uninserted_{i}_{seed}" for i in range(10_000)]

            # 1. AdaLog-Sketch (Unified, K=128, tau=15, decoupled m=1024)
            hll_m = 1024
            stash_k = 128
            fixed_bytes = (hll_m * 6 + 7) // 8 + stash_k * 24
            rem_bytes = max(256, total_bytes - fixed_bytes)
            d = 4
            w = max(64, rem_bytes // d)
            adalog = AdaLogSketch(d=d, w=w, counter_bits=8, stash_capacity=stash_k, elephant_threshold=15, m=hll_m, seed=seed)
            for x in stream: adalog.update(x)

            errs = [adalog.estimate(k) - tf for k, tf in ground_truth.items()]
            models_data["AdaLog-Sketch"]["mae"].append(float(np.mean(np.abs(errs))))
            models_data["AdaLog-Sketch"]["are"].append(float(np.mean([abs(e)/tf for e, tf in zip(errs, ground_truth.values())])))
            models_data["AdaLog-Sketch"]["fpr"].append(sum(1 for uk in uninserted if adalog.contains(uk)) / float(len(uninserted)))
            models_data["AdaLog-Sketch"]["cards"].append(adalog.cardinality())
            p, r, f = evaluate_top_k(ground_truth, adalog.top_k(100), 100)
            models_data["AdaLog-Sketch"]["prec"].append(p)
            models_data["AdaLog-Sketch"]["rec"].append(r)
            models_data["AdaLog-Sketch"]["f1"].append(f)
            models_data["AdaLog-Sketch"]["under"].append(sum(1 for e in errs if e < 0))

            # 2. Disjoint Stack (Memory matched: 20% BF, 768B HLL, remainder CMS-CU 16-bit)
            disjoint = DisjointBaselineStack(expected_cardinality=true_card, total_memory_bytes=total_bytes, seed=seed)
            for x in stream: disjoint.update(x)

            dis_errs = [disjoint.estimate(k) - tf for k, tf in ground_truth.items()]
            models_data["Disjoint-Stack"]["mae"].append(float(np.mean(np.abs(dis_errs))))
            models_data["Disjoint-Stack"]["are"].append(float(np.mean([abs(e)/tf for e, tf in zip(dis_errs, ground_truth.values())])))
            models_data["Disjoint-Stack"]["fpr"].append(sum(1 for uk in uninserted if disjoint.contains(uk)) / float(len(uninserted)))
            models_data["Disjoint-Stack"]["cards"].append(disjoint.cardinality())
            models_data["Disjoint-Stack"]["prec"].append(0.0)
            models_data["Disjoint-Stack"]["rec"].append(0.0)
            models_data["Disjoint-Stack"]["f1"].append(0.0)
            models_data["Disjoint-Stack"]["under"].append(sum(1 for e in dis_errs if e < 0))

            # 3. Disjoint + Stash (Ablation isolating unification vs stash)
            dis_stash = DisjointStashStack(total_memory_bytes=total_bytes, stash_capacity=128, stash_tau=15, cms_counter_bits=8, seed=seed)
            for x in stream: dis_stash.update(x)

            ds_errs = [dis_stash.estimate(k) - tf for k, tf in ground_truth.items()]
            models_data["Disjoint-Stash"]["mae"].append(float(np.mean(np.abs(ds_errs))))
            models_data["Disjoint-Stash"]["are"].append(float(np.mean([abs(e)/tf for e, tf in zip(ds_errs, ground_truth.values())])))
            models_data["Disjoint-Stash"]["fpr"].append(sum(1 for uk in uninserted if dis_stash.contains(uk)) / float(len(uninserted)))
            models_data["Disjoint-Stash"]["cards"].append(dis_stash.cardinality())
            p, r, f = evaluate_top_k(ground_truth, dis_stash.top_k(100), 100)
            models_data["Disjoint-Stash"]["prec"].append(p)
            models_data["Disjoint-Stash"]["rec"].append(r)
            models_data["Disjoint-Stash"]["f1"].append(f)
            models_data["Disjoint-Stash"]["under"].append(sum(1 for e in ds_errs if e < 0))

            # 4. Elastic Sketch (Yang et al. SIGCOMM 2018)
            elastic = ElasticSketch(total_memory_bytes=total_bytes, seed=seed)
            for x in stream: elastic.update(x)

            el_errs = [elastic.estimate(k) - tf for k, tf in ground_truth.items()]
            models_data["ElasticSketch"]["mae"].append(float(np.mean(np.abs(el_errs))))
            models_data["ElasticSketch"]["are"].append(float(np.mean([abs(e)/tf for e, tf in zip(el_errs, ground_truth.values())])))
            models_data["ElasticSketch"]["fpr"].append(None)
            models_data["ElasticSketch"]["cards"].append(None)
            p, r, f = evaluate_top_k(ground_truth, elastic.top_k(100), 100)
            models_data["ElasticSketch"]["prec"].append(p)
            models_data["ElasticSketch"]["rec"].append(r)
            models_data["ElasticSketch"]["f1"].append(f)
            models_data["ElasticSketch"]["under"].append(sum(1 for e in el_errs if e < 0))

            # 5. Augmented Sketch (Roy et al. SIGMOD 2016)
            augmented = AugmentedSketch(total_memory_bytes=total_bytes, seed=seed)
            for x in stream: augmented.update(x)

            aug_errs = [augmented.estimate(k) - tf for k, tf in ground_truth.items()]
            models_data["AugmentedSketch"]["mae"].append(float(np.mean(np.abs(aug_errs))))
            models_data["AugmentedSketch"]["are"].append(float(np.mean([abs(e)/tf for e, tf in zip(aug_errs, ground_truth.values())])))
            models_data["AugmentedSketch"]["fpr"].append(None)
            models_data["AugmentedSketch"]["cards"].append(None)
            p, r, f = evaluate_top_k(ground_truth, augmented.top_k(100), 100)
            models_data["AugmentedSketch"]["prec"].append(p)
            models_data["AugmentedSketch"]["rec"].append(r)
            models_data["AugmentedSketch"]["f1"].append(f)
            models_data["AugmentedSketch"]["under"].append(sum(1 for e in aug_errs if e < 0))

        # Aggregate across seeds
        avg_true_card = float(np.mean(true_cards))

        for m_name, d_dict in models_data.items():
            mae_stat = calc_stats(d_dict["mae"])
            are_stat = calc_stats(d_dict["are"])
            under_stat = calc_stats(d_dict["under"])
            f1_stat = calc_stats(d_dict["f1"])
            prec_stat = calc_stats(d_dict["prec"])
            rec_stat = calc_stats(d_dict["rec"])

            if d_dict["fpr"][0] is not None:
                fpr_stat = calc_stats(d_dict["fpr"])
                fpr_mean = fpr_stat["mean"]
                fpr_std = fpr_stat["std"]
            else:
                fpr_mean, fpr_std = None, None

            if d_dict["cards"][0] is not None:
                # True Multi-Seed Cardinality RSE: RMSE / n
                card_rmse = math.sqrt(float(np.mean([(c - tc) ** 2 for c, tc in zip(d_dict["cards"], true_cards)])))
                rse_val = card_rmse / avg_true_card
            else:
                rse_val = None

            row_summary = {
                "model": m_name,
                "budget_kb": b_kb,
                "bytes": total_bytes,
                "mae": mae_stat["mean"],
                "mae_std": mae_stat["std"],
                "mae_ci95": [mae_stat["ci95_lo"], mae_stat["ci95_hi"]],
                "are": are_stat["mean"],
                "fpr": fpr_mean,
                "fpr_std": fpr_std,
                "rse": rse_val,
                "top_k_f1": f1_stat["mean"],
                "top_k_precision": prec_stat["mean"],
                "top_k_recall": rec_stat["mean"],
                "underestimates": int(round(under_stat["mean"])),
                "underestimates_runs": d_dict["under"],
            }
            summary_results.append(row_summary)
            fpr_str = f"{fpr_mean*100:6.2f}%" if fpr_mean is not None else "   N/A  "
            rse_str = f"{rse_val:6.4f}" if rse_val is not None else " N/A  "
            print(f"  {m_name:16s} -> MAE: {mae_stat['mean']:6.3f} +/- {mae_stat['std']:5.3f} | FPR: {fpr_str} | RSE: {rse_str} | F1: {f1_stat['mean']:.3f} (P={prec_stat['mean']:.3f}, R={rec_stat['mean']:.3f}) | Under: {row_summary['underestimates']}")

    with open(out_file, "w") as f:
        json.dump(summary_results, f, indent=2)
    print(f"\nExperiment 1 successfully written to {out_file}")


# ==============================================================================
# 3. EXPERIMENT 2: SKEW SWEEP (alphas in [1.05, 1.50], 10 Seeds)
# ==============================================================================
def run_exp2_skew_sweep():
    print("\n" + "=" * 80)
    print("STEP 3: Running Experiment 2 (Skew Sweep, 10 Seeds, Head/Tail Breakdown)")
    print("=" * 80)
    alphas = [1.05, 1.15, 1.25, 1.35, 1.50]
    b_kb = 32
    total_bytes = b_kb * 1024
    n_stream = 300_000
    n_unique = 100_000

    out_file = os.path.join(PROJECT_ROOT, "results", "raw", "exp2_skew_sweep.json")
    results = []

    for alpha in alphas:
        print(f"\n--- Skew alpha = {alpha:.2f} at {b_kb} KB across {len(SEEDS)} seeds ---")

        adalog_maes, dis_maes, el_maes, aug_maes = [], [], [], []
        head_errs_dis, tail_errs_dis = [], []

        for seed in SEEDS:
            stream, ground_truth = generate_zipf_stream(n_stream=n_stream, n_unique=n_unique, alpha=alpha, seed=seed)
            true_card = len(ground_truth)

            # 1. AdaLog
            adalog = AdaLogSketch(d=4, w=6682, counter_bits=8, stash_capacity=128, elephant_threshold=15, m=1024, seed=seed)
            for x in stream: adalog.update(x)
            adalog_err = [abs(adalog.estimate(k) - tf) for k, tf in ground_truth.items()]
            adalog_maes.append(float(np.mean(adalog_err)))

            # 2. Disjoint
            disjoint = DisjointBaselineStack(expected_cardinality=true_card, total_memory_bytes=total_bytes, seed=seed)
            for x in stream: disjoint.update(x)
            dis_err = {k: abs(disjoint.estimate(k) - tf) for k, tf in ground_truth.items()}
            dis_maes.append(float(np.mean(list(dis_err.values()))))

            # Head vs Tail diagnosis for Disjoint
            sorted_keys = [kv[0] for kv in sorted(ground_truth.items(), key=lambda kv: kv[1], reverse=True)]
            head_keys = sorted_keys[:100]
            tail_keys = sorted_keys[100:]
            head_errs_dis.append(float(np.mean([dis_err[k] for k in head_keys])))
            tail_errs_dis.append(float(np.mean([dis_err[k] for k in tail_keys])))

            # 3. Elastic
            elastic = ElasticSketch(total_memory_bytes=total_bytes, seed=seed)
            for x in stream: elastic.update(x)
            el_err = [abs(elastic.estimate(k) - tf) for k, tf in ground_truth.items()]
            el_maes.append(float(np.mean(el_err)))

            # 4. Augmented
            augmented = AugmentedSketch(total_memory_bytes=total_bytes, seed=seed)
            for x in stream: augmented.update(x)
            aug_err = [abs(augmented.estimate(k) - tf) for k, tf in ground_truth.items()]
            aug_maes.append(float(np.mean(aug_err)))

        ad_stat = calc_stats(adalog_maes)
        dis_stat = calc_stats(dis_maes)
        el_stat = calc_stats(el_maes)
        aug_stat = calc_stats(aug_maes)
        head_stat = calc_stats(head_errs_dis)
        tail_stat = calc_stats(tail_errs_dis)

        res_row = {
            "alpha": alpha,
            "budget_kb": b_kb,
            "adalog_mae": ad_stat["mean"],
            "adalog_mae_std": ad_stat["std"],
            "disjoint_mae": dis_stat["mean"],
            "disjoint_mae_std": dis_stat["std"],
            "disjoint_head_mae": head_stat["mean"],
            "disjoint_tail_mae": tail_stat["mean"],
            "elastic_mae": el_stat["mean"],
            "elastic_mae_std": el_stat["std"],
            "augmented_mae": aug_stat["mean"],
            "augmented_mae_std": aug_stat["std"],
        }
        results.append(res_row)
        print(f"  alpha={alpha:.2f} -> AdaLog MAE: {ad_stat['mean']:6.3f} | Disjoint MAE: {dis_stat['mean']:6.3f} (Head: {head_stat['mean']:6.2f}, Tail: {tail_stat['mean']:6.2f}) | Elastic: {el_stat['mean']:6.3f} | Augmented: {aug_stat['mean']:6.3f}")

    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nExperiment 2 successfully written to {out_file}")


# ==============================================================================
# 4. EXPERIMENT 4: COMPONENT ABLATIONS (32 KB, 10 Seeds)
# ==============================================================================
def run_exp4_ablations():
    print("\n" + "=" * 80)
    print("STEP 4: Running Experiment 4 (Ablation Matrix at 32 KB across 10 Seeds)")
    print("=" * 80)
    b_kb = 32
    total_bytes = b_kb * 1024
    n_stream = 300_000
    n_unique = 100_000
    alpha = 1.25

    out_file = os.path.join(PROJECT_ROOT, "results", "raw", "exp4_ablations.json")

    ablation_configs = [
        ("AdaLog-Default (Decoupled)", {"use_stash": True, "use_cu": True, "bits": 8, "var": "A", "hll": "decoupled"}),
        ("Coupled HLL (m=w)",         {"use_stash": True, "use_cu": True, "bits": 8, "var": "A", "hll": "coupled"}),
        ("No Stash (-Stash)",          {"use_stash": False, "use_cu": True, "bits": 8, "var": "A", "hll": "decoupled"}),
        ("No CU (-Conservative)",      {"use_stash": True, "use_cu": False, "bits": 8, "var": "A", "hll": "decoupled"}),
        ("16-bit Counters",            {"use_stash": True, "use_cu": True, "bits": 16, "var": "A", "hll": "decoupled"}),
        ("32-bit Counters",            {"use_stash": True, "use_cu": True, "bits": 32, "var": "A", "hll": "decoupled"}),
        ("Membership Variant B (1-bit)",{"use_stash": True, "use_cu": True, "bits": 8, "var": "B", "hll": "decoupled"}),
    ]

    results = []

    for name, cfg in ablation_configs:
        print(f"\nEvaluating Ablation: {name}...")
        bits = cfg["bits"]
        d = 4

        stash_k = 128 if cfg["use_stash"] else 0
        stash_bytes = stash_k * 24

        if cfg["hll"] == "coupled":
            # coupled: m = w. Each column has d * (bits/8) bytes + (6/8) bytes HLL
            rem_bytes = max(256, total_bytes - stash_bytes)
            bits_per_col = d * bits + 6
            w = max(64, int((rem_bytes * 8) // bits_per_col))
            m_hll = None
        else:
            m_hll = 1024
            hll_bytes = (m_hll * 6 + 7) // 8
            # If Variant B: deduct 1-bit presence plane (w/8 bytes)
            if cfg["var"] == "B":
                # w * (d * bits + 1) / 8 <= rem_bytes
                rem_bytes = max(256, total_bytes - stash_bytes - hll_bytes)
                w = max(64, int((rem_bytes * 8) // (d * bits + 1)))
            else:
                rem_bytes = max(256, total_bytes - stash_bytes - hll_bytes)
                w = max(64, int((rem_bytes * 8) // (d * bits)))

        maes, peaks, fprs, cards = [], [], [], []
        true_cards = []

        for seed in SEEDS:
            stream, ground_truth = generate_zipf_stream(n_stream=n_stream, n_unique=n_unique, alpha=alpha, seed=seed)
            true_cards.append(len(ground_truth))
            uninserted = [f"uninserted_abl_{i}_{seed}" for i in range(10_000)]

            sketch = AdaLogSketch(
                d=d, w=w, counter_bits=bits,
                use_stash=cfg["use_stash"], stash_capacity=stash_k, stash_tau=15,
                use_conservative_update=cfg["use_cu"], membership_variant=cfg["var"],
                hll_layout=cfg["hll"], m=m_hll, seed=seed
            )
            for x in stream: sketch.update(x)

            diffs = [sketch.estimate(k) - tf for k, tf in ground_truth.items()]
            maes.append(float(np.mean(np.abs(diffs))))
            peaks.append(int(np.max(diffs)))
            fprs.append(sum(1 for uk in uninserted if sketch.contains(uk)) / float(len(uninserted)))
            cards.append(sketch.cardinality())

        mae_stat = calc_stats(maes)
        peak_val = int(np.median(peaks))
        fpr_stat = calc_stats(fprs)
        avg_true_card = float(np.mean(true_cards))
        rse_val = math.sqrt(float(np.mean([(c - tc) ** 2 for c, tc in zip(cards, true_cards)]))) / avg_true_card

        row = {
            "name": name,
            "width": w,
            "mae": mae_stat["mean"],
            "mae_std": mae_stat["std"],
            "peak_error": peak_val,
            "fpr": fpr_stat["mean"],
            "fpr_std": fpr_stat["std"],
            "rse": rse_val,
        }
        results.append(row)
        print(f"  {name:30s} -> Width: {w:5d} | MAE: {mae_stat['mean']:6.3f} +/- {mae_stat['std']:5.3f} | Peak: {peak_val:3d} | FPR: {fpr_stat['mean']*100:6.2f}% | RSE: {rse_val:6.4f}")

    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nExperiment 4 successfully written to {out_file}")


# ==============================================================================
# 5. EXPERIMENT 8: WIRE COMPRESSION (16 KB to 256 KB)
# ==============================================================================
def run_exp8_compression():
    print("\n" + "=" * 80)
    print("STEP 5: Running Experiment 8 (LightRanger Lossless State Compression)")
    print("=" * 80)
    from experiments.exp8_compression import run_compression_benchmark
    run_compression_benchmark()


# ==============================================================================
# 6. REGENERATE ALL PLOTS
# ==============================================================================
def regenerate_all_plots():
    print("\n" + "=" * 80)
    print("STEP 6: Regenerating Publication Figures (PDF & PNG)")
    print("=" * 80)
    from experiments.plot_results import plot_all_figures
    plot_all_figures()


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
def main():
    start_time = time.time()
    print("################################################################################")
    print("           ADALOG-SKETCH COMPLETE RIGOROUS REPRODUCTION SUITE                  ")
    print("################################################################################")

    run_cpp_benchmark()
    run_exp1_memory_sweep()
    run_exp2_skew_sweep()
    run_exp4_ablations()
    run_exp8_compression()
    regenerate_all_plots()

    elapsed = time.time() - start_time
    print("\n" + "#" * 80)
    print(f"ALL EXPERIMENTS AND PLOTS REGENERATED SUCCESSFULLY IN {elapsed:.1f} SECONDS!")
    print("#" * 80)


if __name__ == "__main__":
    main()
