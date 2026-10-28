"""Automated Publication-Quality Figure Generator.

Reads raw experiment JSON results from results/raw/ and generates high-resolution
publication figures into results/figures/ (both PNG and PDF).
Applies IEEE double-column styling, clean typography, and distinct line markers.
"""

import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def setup_matplotlib_style():
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.titlesize": 12,
        "lines.linewidth": 1.8,
        "lines.markersize": 6,
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

    # Group by model
    models = {}
    for row in data:
        m = row["model"]
        if m not in models:
            models[m] = {"kb": [], "mae": [], "f1": []}
        models[m]["kb"].append(row["budget_kb"])
        models[m]["mae"].append(row["mae"])
        models[m]["f1"].append(row["top_k_f1"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.2), dpi=300)

    # 1. Memory vs MAE
    for m, vals in models.items():
        marker = "o" if "AdaLog" in m else ("s" if "Disjoint" in m else "^")
        lw = 2.2 if "AdaLog" in m else 1.5
        ax1.plot(vals["kb"], vals["mae"], label=m, marker=marker, linewidth=lw)

    ax1.set_xscale("log", base=2)
    ax1.set_yscale("log")
    ax1.set_xlabel("Memory Budget (KB)")
    ax1.set_ylabel("Frequency MAE (log)")
    ax1.set_title("(a) Memory vs. Frequency Error")
    ax1.grid(True)
    ax1.legend(frameon=True, facecolor="white", framealpha=0.9)

    # 2. Memory vs Top-k F1
    for m, vals in models.items():
        marker = "o" if "AdaLog" in m else ("s" if "Disjoint" in m else "^")
        lw = 2.2 if "AdaLog" in m else 1.5
        ax2.plot(vals["kb"], vals["f1"], label=m, marker=marker, linewidth=lw)

    ax2.set_xscale("log", base=2)
    ax2.set_xlabel("Memory Budget (KB)")
    ax2.set_ylabel("Top-100 Heavy Hitters F1 Score")
    ax2.set_title("(b) Memory vs. Heavy Hitter F1")
    ax2.grid(True)
    ax2.set_ylim(-0.05, 1.05)

    plt.tight_layout()
    os.makedirs("results/figures", exist_ok=True)
    plt.savefig("results/figures/fig1_memory_pareto.png")
    plt.savefig("results/figures/fig1_memory_pareto.pdf")
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
    disjoint_mae = [r["disjoint_mae"] for r in data]
    elastic_mae = [r["elastic_mae"] for r in data]
    aug_mae = [r["augmented_mae"] for r in data]

    fig, ax = plt.subplots(figsize=(4.5, 3.2), dpi=300)
    ax.plot(alphas, adalog_mae, label="AdaLog-Sketch", marker="o", linewidth=2.2, color="#1f77b4")
    ax.plot(alphas, disjoint_mae, label="Disjoint Stack", marker="s", linewidth=1.5, color="#d62728")
    ax.plot(alphas, elastic_mae, label="Elastic Sketch", marker="^", linewidth=1.5, color="#2ca02c")
    ax.plot(alphas, aug_mae, label="Augmented Sketch", marker="d", linewidth=1.5, color="#ff7f0e")

    ax.set_xlabel(r"Zipfian Skew Parameter $\alpha$")
    ax.set_ylabel("Frequency Estimation MAE")
    ax.set_title("Skew Sensitivity (32 KB Budget)")
    ax.grid(True)
    ax.legend(frameon=True, facecolor="white", framealpha=0.9)

    plt.tight_layout()
    plt.savefig("results/figures/fig2_skew_sensitivity.png")
    plt.savefig("results/figures/fig2_skew_sensitivity.pdf")
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
    labels = ["AdaLog\n(Unified)", "Disjoint\n(BF+CMS+HLL)", "CMS\n(Standalone)", "Bloom\n(Standalone)", "HLL\n(Standalone)"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.2), dpi=300)

    # Throughput bar
    colors = ["#1f77b4", "#d62728", "#7f7f7f", "#bcbd22", "#17becf"]
    ax1.bar(labels, mops, color=colors, width=0.55, edgecolor="black", linewidth=0.8)
    ax1.set_ylabel("Throughput (Mops/s)")
    ax1.set_title("(a) Native C++ Ingestion Throughput")
    ax1.grid(axis="y")
    for i, v in enumerate(mops):
        ax1.text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=8, fontweight="bold")

    # Latency bar
    ax2.bar(labels, ns_op, color=colors, width=0.55, edgecolor="black", linewidth=0.8)
    ax2.set_ylabel("Latency (ns/op)")
    ax2.set_title("(b) Average Operation Latency")
    ax2.grid(axis="y")
    for i, v in enumerate(ns_op):
        ax2.text(i, v + 10, f"{v:.0f}ns", ha="center", fontsize=8, fontweight="bold")

    plt.tight_layout()
    plt.savefig("results/figures/fig3_latency_throughput.png")
    plt.savefig("results/figures/fig3_latency_throughput.pdf")
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
    ax1.set_xlabel("Mean Absolute Error (MAE)")
    ax1.set_title("(a) Architectural Ablation: MAE")
    ax1.grid(axis="x")

    ax2.barh(names, peaks, color=colors, height=0.55, edgecolor="black", linewidth=0.8)
    ax2.set_xlabel("Peak Error Overestimate")
    ax2.set_title("(b) Architectural Ablation: Peak Overestimate")
    ax2.grid(axis="x")

    plt.tight_layout()
    plt.savefig("results/figures/fig4_ablations.png")
    plt.savefig("results/figures/fig4_ablations.pdf")
    plt.close()
    print("Generated fig4_ablations.(png/pdf)")


def plot_experiment_5():
    path = "results/raw/exp5_planner_eval.json"
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)

    sweep = data["memory_sweep"]
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
    plt.savefig("results/figures/fig5_planner_accuracy.png")
    plt.savefig("results/figures/fig5_planner_accuracy.pdf")
    plt.close()
    print("Generated fig5_planner_accuracy.(png/pdf)")


def plot_experiment_7():
    path = "results/raw/exp7_certificates_eval.json"
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)

    datasets = data["datasets"]
    alphas = [r["alpha"] for r in datasets]
    raw_mae = [r["raw_mae"] for r in datasets]
    deb_mae = [r["debiased_mae"] for r in datasets]
    coverage = [r["coverage_pct"] for r in datasets]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.2), dpi=300)

    # Coverage
    ax1.bar([f"α={a:.2f}" for a in alphas], coverage, color="#2ca02c", width=0.55, edgecolor="black", linewidth=0.8)
    ax1.axhline(95.0, color="red", linestyle="--", linewidth=1.5, label="95% Nominal Target")
    ax1.set_ylabel("Empirical Coverage (%)")
    ax1.set_title("(a) Interval Coverage [lo, hi]")
    ax1.set_ylim(90, 101)
    ax1.grid(axis="y")
    ax1.legend(loc="lower right")

    # Debiased MAE
    x = np.arange(len(alphas))
    width = 0.35
    ax2.bar(x - width/2, raw_mae, width, label="Raw CMS-CU", color="#d62728", edgecolor="black", linewidth=0.8)
    ax2.bar(x + width/2, deb_mae, width, label="Debiased", color="#1f77b4", edgecolor="black", linewidth=0.8)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"α={a:.2f}" for a in alphas])
    ax2.set_ylabel("Frequency MAE")
    ax2.set_title("(b) Cross-Task Debiasing Benefit")
    ax2.grid(axis="y")
    ax2.legend()

    plt.tight_layout()
    plt.savefig("results/figures/fig7_certificates_coverage.png")
    plt.savefig("results/figures/fig7_certificates_coverage.pdf")
    plt.close()
    print("Generated fig7_certificates_coverage.(png/pdf)")


def plot_experiment_8():
    path = "results/raw/exp8_compression.json"
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)

    kb = [r["budget_kb"] for r in data]
    ratios = [r["compression_ratio_pct"] for r in data]

    fig, ax = plt.subplots(figsize=(4.5, 3.2), dpi=300)
    ax.plot(kb, ratios, marker="o", color="#9467bd", linewidth=2.0)
    ax.set_xlabel("In-Memory Matrix Size (KB)")
    ax.set_ylabel("Wire Size Reduction (%)")
    ax.set_title("LightRanger Wire Compression Ratio")
    ax.grid(True)
    ax.axhline(0, color="gray", linestyle=":")

    plt.tight_layout()
    plt.savefig("results/figures/fig8_compression_ratio.png")
    plt.savefig("results/figures/fig8_compression_ratio.pdf")
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
