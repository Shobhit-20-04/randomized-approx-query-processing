"""Automated Publication-Quality Figure Generator with 95% Confidence Intervals.
"""

import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


import sys
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

    # Group by model
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

    # Shared horizontal legend on top
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
    print("Generated fig1_memory_pareto.(png/pdf) with 95% CIs")


def plot_experiment_2():
    path = "results/raw/exp2_skew_sweep.json"
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)

    alphas = [r["alpha"] for r in data]
    adalog_mae = [r["adalog_mae"] for r in data]
    adalog_std = [r["adalog_mae_std"] for r in data]
    disjoint_mae = [r["disjoint_mae"] for r in data]
    disjoint_std = [r["disjoint_mae_std"] for r in data]
    elastic_mae = [r["elastic_mae"] for r in data]
    elastic_std = [r["elastic_mae_std"] for r in data]
    aug_mae = [r["augmented_mae"] for r in data]
    aug_std = [r["augmented_mae_std"] for r in data]

    fig, ax = plt.subplots(figsize=(3.6, 2.7), dpi=300)
    ax.errorbar(alphas, adalog_mae, yerr=adalog_std, label="AdaLog (Unified)", marker="o", linewidth=1.8, markersize=4.5, color="#1f77b4", capsize=2.5)
    ax.errorbar(alphas, disjoint_mae, yerr=disjoint_std, label="Disjoint Stack", marker="s", linewidth=1.5, markersize=4.5, color="#d62728", capsize=2.5)
    ax.errorbar(alphas, elastic_mae, yerr=elastic_std, label="Elastic Sketch", marker="^", linewidth=1.5, markersize=4.5, color="#2ca02c", capsize=2.5)
    ax.errorbar(alphas, aug_mae, yerr=aug_std, label="Augmented Sketch", marker="d", linewidth=1.5, markersize=4.5, color="#ff7f0e", capsize=2.5)

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
    print("Generated fig2_skew_sensitivity.(png/pdf) with 95% CIs")


def plot_all_figures():
    setup_matplotlib_style()
    plot_experiment_1()
    plot_experiment_2()
    # also call original plot_experiment_3, etc.
    from experiments.plot_results import plot_experiment_3, plot_experiment_4, plot_experiment_5, plot_experiment_7, plot_experiment_8
    plot_experiment_3()
    plot_experiment_4()
    plot_experiment_5()
    plot_experiment_7()
    plot_experiment_8()


if __name__ == "__main__":
    plot_all_figures()
