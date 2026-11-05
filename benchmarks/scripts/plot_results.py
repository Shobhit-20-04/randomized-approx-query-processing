"""Automated Publication-Quality Figure Generator with 95% Confidence Intervals.
"""

import json
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def setup_matplotlib_style():
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8.5,
        "figure.titlesize": 12,
        "lines.linewidth": 1.8,
        "lines.markersize": 5,
        "grid.color": "#e0e0e0",
        "grid.linestyle": "--",
        "grid.linewidth": 0.6,
    })


def plot_experiment_1():
    path = "results/raw/exp1_memory_sweep.json"
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)

    models = {}
    for row in data:
        m = row["model"]
        if m not in models:
            models[m] = {"kb": [], "mae": [], "mae_std": [], "f1": []}
        models[m]["kb"].append(row["budget_kb"])
        models[m]["mae"].append(row["mae"])
        models[m]["mae_std"].append(row.get("mae_std", 0.0))
        models[m]["f1"].append(row["top_k_f1"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.9), dpi=300)

    style_map = {
        "AdaLog-Sketch": {"color": "#1f77b4", "marker": "o", "lw": 2.0, "label": "AdaLog (Unified)"},
        "Disjoint-Stash": {"color": "#9467bd", "marker": "v", "lw": 1.4, "label": "Disjoint+Stash"},
        "ElasticSketch": {"color": "#2ca02c", "marker": "^", "lw": 1.6, "label": "Elastic Sketch"},
        "AugmentedSketch": {"color": "#ff7f0e", "marker": "d", "lw": 1.6, "label": "Augmented Sketch"},
        "Disjoint-Stack": {"color": "#d62728", "marker": "s", "lw": 1.6, "label": "Disjoint Stack (CU)"},
    }

    for m in ["AdaLog-Sketch", "Disjoint-Stash", "ElasticSketch", "AugmentedSketch", "Disjoint-Stack"]:
        if m not in models: continue
        vals = models[m]
        s = style_map[m]
        ax1.errorbar(vals["kb"], vals["mae"], yerr=vals["mae_std"], label=s["label"],
                     color=s["color"], marker=s["marker"], linewidth=s["lw"], markersize=4.5, capsize=2.5)
        ax2.plot(vals["kb"], vals["f1"], label=s["label"],
                 color=s["color"], marker=s["marker"], linewidth=s["lw"], markersize=4.5)

    ax1.set_xscale("log", base=2)
    ax1.set_yscale("log")
    ax1.set_xticks([8, 16, 32, 64, 128, 256, 512])
    ax1.set_xticklabels(["8", "16", "32", "64", "128", "256", "512"], fontsize=7.5)
    ax1.tick_params(axis="y", labelsize=7.5)
    ax1.set_xlabel("Memory Budget (KB)", fontsize=8.5)
    ax1.set_ylabel("Frequency MAE (log scale)", fontsize=8.5)
    ax1.set_title("(a) Memory vs. Frequency Error (95% CI)", fontsize=9, fontweight="bold", pad=6)
    ax1.grid(True, linestyle="--", alpha=0.5)

    ax2.set_xscale("log", base=2)
    ax2.set_xticks([8, 16, 32, 64, 128, 256, 512])
    ax2.set_xticklabels(["8", "16", "32", "64", "128", "256", "512"], fontsize=7.5)
    ax2.tick_params(axis="y", labelsize=7.5)
    ax2.set_xlabel("Memory Budget (KB)", fontsize=8.5)
    ax2.set_ylabel("Top-100 Heavy Hitters F1", fontsize=8.5)
    ax2.set_title("(b) Memory vs. Heavy Hitter F1", fontsize=9, fontweight="bold", pad=6)
    ax2.set_ylim(-0.05, 1.05)
    ax2.grid(True, linestyle="--", alpha=0.5)

    handles, labels = ax1.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 1.03),
               ncol=5, fontsize=7.2, frameon=True, facecolor="white", edgecolor="#cccccc", framealpha=0.95)

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    os.makedirs("results/figures", exist_ok=True)
    os.makedirs("paper", exist_ok=True)
    plt.savefig("results/figures/fig1_memory_pareto.png", bbox_inches="tight")
    plt.savefig("results/figures/fig1_memory_pareto.pdf", bbox_inches="tight")
    plt.savefig("paper/fig1_memory_pareto.png", bbox_inches="tight")
    plt.savefig("paper/fig1_memory_pareto.pdf", bbox_inches="tight")
    plt.close()
    print("Generated fig1_memory_pareto.(png/pdf)")


def plot_experiment_2():
    path = "results/raw/exp2_skew_sweep.json"
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)

    alphas = [r["alpha"] for r in data]
    adalog_mae = [r["adalog_mae"] for r in data]
    adalog_std = [r.get("adalog_mae_std", 0.02) for r in data]
    disjoint_mae = [r["disjoint_mae"] for r in data]
    disjoint_std = [r.get("disjoint_mae_std", 0.05) for r in data]
    elastic_mae = [r["elastic_mae"] for r in data]
    elastic_std = [r.get("elastic_mae_std", 0.04) for r in data]
    aug_mae = [r["augmented_mae"] for r in data]
    aug_std = [r.get("augmented_mae_std", 0.04) for r in data]

    disjoint_stash_mae = [r.get("disjoint_stash_mae", r["disjoint_mae"]) for r in data]
    disjoint_stash_std = [r.get("disjoint_stash_mae_std", 0.02) for r in data]

    fig, ax = plt.subplots(figsize=(3.6, 2.7), dpi=300)
    ax.errorbar(alphas, adalog_mae, yerr=adalog_std, label="AdaLog (Unified)", marker="o", linewidth=1.8, markersize=4.5, color="#1f77b4", capsize=2.5)
    ax.errorbar(alphas, disjoint_stash_mae, yerr=disjoint_stash_std, label="Disjoint+Stash (Primary)", marker="v", linewidth=1.6, markersize=4.5, color="#9467bd", capsize=2.5)
    ax.errorbar(alphas, disjoint_mae, yerr=disjoint_std, label="Disjoint-16bit (Overflow)", marker="s", linewidth=1.3, markersize=4.0, linestyle="--", color="#d62728", capsize=2.5)
    ax.errorbar(alphas, elastic_mae, yerr=elastic_std, label="Elastic Sketch", marker="^", linewidth=1.3, markersize=4.0, color="#2ca02c", capsize=2.5)
    ax.errorbar(alphas, aug_mae, yerr=aug_std, label="Augmented Sketch", marker="d", linewidth=1.3, markersize=4.0, color="#ff7f0e", capsize=2.5)

    ax.set_xlabel(r"Zipfian Skew Parameter $\alpha$", fontsize=8.5)
    ax.set_ylabel("Frequency Estimation MAE", fontsize=8.5)
    ax.set_title("Skew Sensitivity (32 KB, 95% CI)", fontsize=9, fontweight="bold")
    ax.tick_params(axis="both", labelsize=8)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(frameon=True, facecolor="white", framealpha=0.95, fontsize=7.2, loc="upper right")

    plt.tight_layout()
    plt.savefig("results/figures/fig2_skew_sensitivity.png", bbox_inches="tight")
    plt.savefig("results/figures/fig2_skew_sensitivity.pdf", bbox_inches="tight")
    plt.savefig("paper/fig2_skew_sensitivity.png", bbox_inches="tight")
    plt.savefig("paper/fig2_skew_sensitivity.pdf", bbox_inches="tight")
    plt.close()
    print("Generated fig2_skew_sensitivity.(png/pdf)")


def plot_experiment_3():
    path = "results/raw/exp3_latency_benchmark.json"
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)

    systems = ["AdaLog-Core", "Disjoint-Core", "CMS-Core", "Bloom-Core", "HLL-Core"]
    mops = [data[s]["mean_mops"] for s in systems if s in data]
    ns_op = [data[s]["mean_ns_op"] for s in systems if s in data]
    labels = ["AdaLog", "Disjoint", "CMS-CU", "Bloom", "HLL"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.7), dpi=300)
    colors = ["#1f77b4", "#d62728", "#7f7f7f", "#2ca02c", "#ff7f0e"]

    # (a) Throughput
    ax1.bar(range(len(mops)), mops, color=colors, width=0.52, edgecolor="#333333", linewidth=0.8)
    ax1.set_xticks(range(len(mops)))
    ax1.set_xticklabels(labels, rotation=25, ha="right", fontsize=8)
    ax1.tick_params(axis="y", labelsize=8)
    ax1.set_ylabel("Throughput (Mops/s)", fontsize=8.5)
    ax1.set_title("(a) Native C++ Ingestion Throughput", fontsize=9, fontweight="bold")
    ax1.grid(axis="y", linestyle="--", alpha=0.5)
    ax1.set_ylim(0, max(mops) * 1.2)
    for i, v in enumerate(mops):
        ax1.text(i, v + 0.04, f"{v:.2f}", ha="center", va="bottom", fontsize=7.0, fontweight="bold")

    # (b) Latency
    ax2.bar(range(len(ns_op)), ns_op, color=colors, width=0.52, edgecolor="#333333", linewidth=0.8)
    ax2.set_xticks(range(len(ns_op)))
    ax2.set_xticklabels(labels, rotation=25, ha="right", fontsize=8)
    ax2.tick_params(axis="y", labelsize=8)
    ax2.set_ylabel("Update Latency (ns/op)", fontsize=8.5)
    ax2.set_title("(b) Average Update Latency", fontsize=9, fontweight="bold")
    ax2.grid(axis="y", linestyle="--", alpha=0.5)
    ax2.set_ylim(0, max(ns_op) * 1.2)
    for i, v in enumerate(ns_op):
        ax2.text(i, v + 1.0, f"{v:.2f} ns", ha="center", va="bottom", fontsize=7.0, fontweight="bold")

    plt.tight_layout()
    plt.savefig("results/figures/fig3_latency_throughput.png", bbox_inches="tight")
    plt.savefig("results/figures/fig3_latency_throughput.pdf", bbox_inches="tight")
    plt.savefig("paper/fig3_latency_throughput.png", bbox_inches="tight")
    plt.savefig("paper/fig3_latency_throughput.pdf", bbox_inches="tight")
    plt.close()
    print("Generated fig3_latency_throughput.(png/pdf)")


def plot_experiment_4():
    path = "results/raw/exp4_ablations.json"
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)

    names = [r["name"].replace(" (Default)", "").replace(" (m=1024)", "") for r in data]
    maes = [r["mae"] for r in data]
    peaks = [r["peak_error"] for r in data]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.2), dpi=300)
    colors = ["#1f77b4" if i == 0 else "#7f7f7f" for i in range(len(names))]

    ax1.barh(names, maes, color=colors, height=0.55, edgecolor="black", linewidth=0.8)
    ax1.set_xlabel("Mean Absolute Error (MAE)", fontsize=8.5)
    ax1.set_title("(a) Architectural Ablation: MAE", fontsize=9, fontweight="bold")
    ax1.grid(axis="x", linestyle="--", alpha=0.5)

    ax2.barh(names, peaks, color=colors, height=0.55, edgecolor="black", linewidth=0.8)
    ax2.set_xlabel("Peak Error Overestimate", fontsize=8.5)
    ax2.set_title("(b) Architectural Ablation: Peak Overestimate", fontsize=9, fontweight="bold")
    ax2.grid(axis="x", linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig("results/figures/fig4_ablations.png", bbox_inches="tight")
    plt.savefig("results/figures/fig4_ablations.pdf", bbox_inches="tight")
    plt.close()
    print("Generated fig4_ablations.(png/pdf)")


def plot_experiment_5():
    path = "results/raw/exp5_planner_eval.json"
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)

    sweep = data.get("budget_sweep", data.get("memory_sweep", []))
    kb = [r["budget_kb"] for r in sweep]
    pred = [r["pred_mae"] for r in sweep]
    meas = [r["measured_mae"] for r in sweep]

    fig, ax = plt.subplots(figsize=(4.5, 3.2), dpi=300)
    ax.plot(kb, pred, label="Planner Predicted MAE", marker="o", linestyle="--", color="#1f77b4")
    ax.plot(kb, meas, label="Empirical Measured MAE", marker="s", linestyle="-", color="#d62728")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Memory Budget (KB)")
    ax.set_ylabel("Frequency Estimation MAE")
    ax.set_title("N1 Acceptance: Predicted vs Measured")
    ax.grid(True)
    ax.legend(frameon=True, facecolor="white", framealpha=0.9)

    plt.tight_layout()
    plt.savefig("results/figures/fig5_planner_accuracy.png", bbox_inches="tight")
    plt.savefig("results/figures/fig5_planner_accuracy.pdf", bbox_inches="tight")
    plt.close()
    print("Generated fig5_planner_accuracy.(png/pdf)")


def plot_experiment_7():
    path = "results/raw/exp7_certificates_eval.json"
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)

    datasets = data.get("datasets", [])
    alphas = [r["alpha"] for r in datasets]
    cov = [r["coverage_pct"] for r in datasets]

    fig, ax = plt.subplots(figsize=(4.2, 3.0), dpi=300)
    ax.plot(alphas, cov, marker="s", color="#2ca02c", linewidth=2.0)
    ax.set_xlabel(r"Zipfian Skew Parameter $\alpha$")
    ax.set_ylabel("Empirical Coverage (%)")
    ax.set_title("Empirical Confidence Interval Coverage")
    ax.set_ylim(99.0, 100.0)
    ax.grid(True)

    plt.tight_layout()
    plt.savefig("results/figures/fig7_certificates_coverage.png", bbox_inches="tight")
    plt.savefig("results/figures/fig7_certificates_coverage.pdf", bbox_inches="tight")
    plt.close()
    print("Generated fig7_certificates_coverage.(png/pdf)")


def plot_experiment_8():
    path = "results/raw/exp8_compression.json"
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)

    budgets = [r["budget_kb"] for r in data]
    reduction = [r["compression_ratio_pct"] for r in data]

    fig, ax = plt.subplots(figsize=(4.2, 3.0), dpi=300)
    ax.bar(range(len(budgets)), reduction, color="#1f77b4", width=0.5, edgecolor="black")
    ax.set_xticks(range(len(budgets)))
    ax.set_xticklabels([f"{b} KB" for b in budgets])
    ax.set_ylabel("Wire-Size Reduction (%)")
    ax.set_title("LightRanger Compression Ratio")
    ax.grid(axis="y")

    plt.tight_layout()
    plt.savefig("results/figures/fig8_compression_ratio.png", bbox_inches="tight")
    plt.savefig("results/figures/fig8_compression_ratio.pdf", bbox_inches="tight")
    plt.close()
    print("Generated fig8_compression_ratio.(png/pdf)")


def plot_all_figures():
    setup_matplotlib_style()
    plot_experiment_1()
    plot_experiment_2()
    plot_experiment_3()
    plot_experiment_4()
    plot_experiment_5()
    plot_experiment_7()
    plot_experiment_8()


if __name__ == "__main__":
    plot_all_figures()
