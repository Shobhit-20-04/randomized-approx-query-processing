"""
Publication-quality plotting module for approximate query processing experimental results.
Generates all 11 required comparative figures in both PNG and PDF formats.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def set_academic_style() -> None:
    """Configure matplotlib with clean academic publishing styling."""
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 14,
        "figure.dpi": 300,
        "lines.linewidth": 2,
        "lines.markersize": 6,
        "grid.alpha": 0.35,
        "grid.linestyle": "--",
    })


def save_figure(fig: plt.Figure, output_dir: str, filename_base: str) -> None:
    """Save figure in both high-res PNG and vector PDF."""
    os.makedirs(output_dir, exist_ok=True)
    png_path = os.path.join(output_dir, f"{filename_base}.png")
    pdf_path = os.path.join(output_dir, f"{filename_base}.pdf")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)


def generate_all_plots(
    df_bf: pd.DataFrame,
    df_cms: pd.DataFrame,
    df_hll: pd.DataFrame,
    output_dir: str = "results/plots",
) -> List[str]:
    """
    Generate the 11 required academic plots from benchmark data.
    """
    set_academic_style()
    generated_plots = []

    # Filter to default uniform baseline for standard scaling comparisons
    bf_u = df_bf[df_bf["distribution"] == "uniform"] if "distribution" in df_bf.columns else df_bf
    cms_u = df_cms[df_cms["distribution"] == "uniform"] if "distribution" in df_cms.columns else df_cms
    hll_u = df_hll[df_hll["distribution"] == "uniform"] if "distribution" in df_hll.columns else df_hll

    # 1. Memory Usage vs Dataset Size
    fig, ax = plt.subplots(figsize=(8, 5))
    sizes = sorted(df_bf["stream_size"].unique())
    # Exact set memory vs BF / CMS / HLL memory
    bf_mem = bf_u.groupby("stream_size")["approx_memory_bytes"].mean() / 1024.0  # KB
    exact_set_mem = bf_u.groupby("stream_size")["exact_memory_bytes"].mean() / 1024.0  # KB
    cms_mem = cms_u.groupby("stream_size")["approx_memory_bytes"].mean() / 1024.0
    hll_mem = hll_u.groupby("stream_size")["approx_memory_bytes"].mean() / 1024.0

    ax.plot(bf_mem.index, exact_set_mem.values, "k--o", label="Exact Set / Dict (Baseline)")
    ax.plot(bf_mem.index, bf_mem.values, "b-s", label="Bloom Filter (target FPR=0.01)")
    ax.plot(cms_mem.index, cms_mem.values, "r-^", label="Count-Min Sketch (eps=0.05)")
    ax.plot(hll_mem.index, hll_mem.values, "g-d", label="HyperLogLog (p=12)")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Stream Size (Items)")
    ax.set_ylabel("Memory Footprint (KB)")
    ax.set_title("Figure 1: Memory Footprint vs. Dataset Size (Log-Log Scale)")
    ax.grid(True)
    ax.legend()
    save_figure(fig, output_dir, "01_memory_vs_dataset_size")
    generated_plots.append("01_memory_vs_dataset_size")

    # 2. Construction/Insertion Time vs Dataset Size
    fig, ax = plt.subplots(figsize=(8, 5))
    bf_ins = bf_u.groupby("stream_size")["approx_insert_time_ms"].mean()
    cms_ins = cms_u.groupby("stream_size")["approx_insert_time_ms"].mean()
    hll_ins = hll_u.groupby("stream_size")["approx_insert_time_ms"].mean()
    exact_ins = bf_u.groupby("stream_size")["exact_insert_time_ms"].mean()

    ax.plot(bf_ins.index, exact_ins.values, "k--o", label="Exact Baseline Insert")
    ax.plot(bf_ins.index, bf_ins.values, "b-s", label="Bloom Filter Insert")
    ax.plot(cms_ins.index, cms_ins.values, "r-^", label="Count-Min Sketch Insert")
    ax.plot(hll_ins.index, hll_ins.values, "g-d", label="HyperLogLog Insert")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Stream Size (Items)")
    ax.set_ylabel("Insertion Time (ms)")
    ax.set_title("Figure 2: Stream Insertion Time vs. Dataset Size")
    ax.grid(True)
    ax.legend()
    save_figure(fig, output_dir, "02_insertion_time_vs_dataset_size")
    generated_plots.append("02_insertion_time_vs_dataset_size")

    # 3. Update Throughput / Rate vs Dataset Size
    fig, ax = plt.subplots(figsize=(8, 5))
    bf_rate = (bf_ins.index / (bf_ins.values / 1000.0)) / 1000.0  # k ops / sec
    cms_rate = (cms_ins.index / (cms_ins.values / 1000.0)) / 1000.0
    hll_rate = (hll_ins.index / (hll_ins.values / 1000.0)) / 1000.0
    exact_rate = (exact_ins.index / (exact_ins.values / 1000.0)) / 1000.0

    ax.plot(bf_ins.index, exact_rate.values, "k--o", label="Exact Set Throughput")
    ax.plot(bf_ins.index, bf_rate.values, "b-s", label="Bloom Filter Throughput")
    ax.plot(cms_ins.index, cms_rate.values, "r-^", label="Count-Min Sketch Throughput")
    ax.plot(hll_ins.index, hll_rate.values, "g-d", label="HyperLogLog Throughput")

    ax.set_xscale("log")
    ax.set_xlabel("Stream Size (Items)")
    ax.set_ylabel("Insertion Throughput (k ops / sec)")
    ax.set_title("Figure 3: Ingestion Throughput vs. Dataset Size")
    ax.grid(True)
    ax.legend()
    save_figure(fig, output_dir, "03_update_throughput_vs_dataset_size")
    generated_plots.append("03_update_throughput_vs_dataset_size")

    # 4. Query Latency vs Dataset Size
    fig, ax = plt.subplots(figsize=(8, 5))
    bf_lat = bf_u.groupby("stream_size")["approx_query_latency_ns"].mean() / 1000.0  # us
    cms_lat = cms_u.groupby("stream_size")["approx_query_latency_ns"].mean() / 1000.0
    exact_lat = bf_u.groupby("stream_size")["exact_query_latency_ns"].mean() / 1000.0

    ax.plot(bf_lat.index, exact_lat.values, "k--o", label="Exact Lookup Latency")
    ax.plot(bf_lat.index, bf_lat.values, "b-s", label="Bloom Filter Lookup Latency")
    ax.plot(cms_lat.index, cms_lat.values, "r-^", label="Count-Min Sketch Point Latency")

    ax.set_xscale("log")
    ax.set_xlabel("Stream Size (Items)")
    ax.set_ylabel("Mean Query Latency (microseconds)")
    ax.set_title("Figure 4: Query Latency vs. Dataset Size")
    ax.grid(True)
    ax.legend()
    save_figure(fig, output_dir, "04_query_latency_vs_dataset_size")
    generated_plots.append("04_query_latency_vs_dataset_size")

    # 5. Bloom Filter Empirical vs Target False-Positive Rate
    fig, ax = plt.subplots(figsize=(8, 5))
    bf_fpr_grp = df_bf.groupby("target_fpr")[["empirical_fpr", "theoretical_fpr"]].mean().reset_index()
    x_targets = bf_fpr_grp["target_fpr"].values
    ax.plot(x_targets, x_targets, "k--", label="Ideal Parity Line (y = x)")
    ax.scatter(x_targets, bf_fpr_grp["theoretical_fpr"], color="blue", marker="s", s=80, label="Theoretical FPR")
    ax.scatter(x_targets, bf_fpr_grp["empirical_fpr"], color="crimson", marker="o", s=80, label="Empirical Measured FPR")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Target False Positive Rate (p)")
    ax.set_ylabel("Observed False Positive Rate")
    ax.set_title("Figure 5: Bloom Filter Empirical vs. Target False Positive Rate")
    ax.grid(True)
    ax.legend()
    save_figure(fig, output_dir, "05_bloom_filter_empirical_vs_target_fpr")
    generated_plots.append("05_bloom_filter_empirical_vs_target_fpr")

    # 6. Count-Min Sketch MAE vs Epsilon
    fig, ax = plt.subplots(figsize=(8, 5))
    cms_eps_grp = df_cms.groupby("epsilon")["mae"].mean().reset_index()
    ax.plot(cms_eps_grp["epsilon"], cms_eps_grp["mae"], "r-^", markersize=8, label="Empirical MAE")
    ax.set_xlabel("Error Tolerance Parameter (epsilon)")
    ax.set_ylabel("Mean Absolute Frequency Error (MAE)")
    ax.set_title("Figure 6: Count-Min Sketch Mean Absolute Error vs. Epsilon")
    ax.grid(True)
    ax.legend()
    save_figure(fig, output_dir, "06_count_min_sketch_mae_vs_epsilon")
    generated_plots.append("06_count_min_sketch_mae_vs_epsilon")

    # 7. Count-Min Sketch Frequency Error across Skewed vs Uniform Distribution
    fig, ax = plt.subplots(figsize=(8, 5))
    cms_dist_grp = df_cms.groupby(["distribution", "stream_size"])["mae"].mean().unstack(level=0)
    cms_dist_grp.plot(kind="bar", ax=ax, colormap="viridis")
    ax.set_xlabel("Stream Size")
    ax.set_ylabel("Mean Absolute Error (MAE)")
    ax.set_title("Figure 7: Count-Min Sketch Estimation Error Across Stream Distributions")
    ax.grid(True, axis="y")
    save_figure(fig, output_dir, "07_count_min_sketch_error_by_distribution")
    generated_plots.append("07_count_min_sketch_error_by_distribution")

    # 8. HyperLogLog Relative Cardinality Error vs Precision
    fig, ax = plt.subplots(figsize=(8, 5))
    hll_p_grp = df_hll.groupby("precision_p")[["relative_error", "theoretical_rse"]].mean().reset_index()
    ax.plot(hll_p_grp["precision_p"], hll_p_grp["theoretical_rse"] * 100, "b--s", label="Theoretical RSE (1.04 / sqrt(2^p)) (%)")
    ax.plot(hll_p_grp["precision_p"], hll_p_grp["relative_error"] * 100, "g-o", label="Empirical Relative Error (%)")
    ax.set_xlabel("Precision Parameter (p)")
    ax.set_ylabel("Relative Error (%)")
    ax.set_title("Figure 8: HyperLogLog Relative Error vs. Precision Parameter (p)")
    ax.grid(True)
    ax.legend()
    save_figure(fig, output_dir, "08_hyperloglog_error_vs_precision")
    generated_plots.append("08_hyperloglog_error_vs_precision")

    # 9. Accuracy-vs-Memory Trade-Offs
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 5))
    # BF: memory vs FPR
    bf_mem_tradeoff = df_bf.groupby("target_fpr")[["approx_memory_bytes", "empirical_fpr"]].mean()
    ax1.scatter(bf_mem_tradeoff["approx_memory_bytes"] / 1024, bf_mem_tradeoff["empirical_fpr"], color="blue", s=70)
    ax1.set_xlabel("Memory (KB)")
    ax1.set_ylabel("Empirical FPR")
    ax1.set_title("Bloom Filter: Memory vs. FPR")
    ax1.set_yscale("log")
    ax1.grid(True)

    # CMS: memory vs MAE
    cms_mem_tradeoff = df_cms.groupby("epsilon")[["approx_memory_bytes", "mae"]].mean()
    ax2.scatter(cms_mem_tradeoff["approx_memory_bytes"] / 1024, cms_mem_tradeoff["mae"], color="red", s=70)
    ax2.set_xlabel("Memory (KB)")
    ax2.set_ylabel("MAE")
    ax2.set_title("Count-Min: Memory vs. MAE")
    ax2.grid(True)

    # HLL: memory vs Rel Error
    hll_mem_tradeoff = df_hll.groupby("precision_p")[["approx_memory_bytes", "relative_error"]].mean()
    ax3.scatter(hll_mem_tradeoff["approx_memory_bytes"] / 1024, hll_mem_tradeoff["relative_error"] * 100, color="green", s=70)
    ax3.set_xlabel("Memory (KB)")
    ax3.set_ylabel("Rel. Error (%)")
    ax3.set_title("HyperLogLog: Memory vs. Rel. Error")
    ax3.grid(True)

    fig.suptitle("Figure 9: Distinct Accuracy vs. Memory Allocation Across Structures", y=1.02)
    save_figure(fig, output_dir, "09_accuracy_vs_memory_tradeoffs")
    generated_plots.append("09_accuracy_vs_memory_tradeoffs")

    # 10. Uniform vs Zipfian Performance Comparison
    fig, ax = plt.subplots(figsize=(8, 5))
    comp_df = pd.DataFrame({
        "BF Uniform FPR": df_bf[df_bf["distribution"] == "uniform"]["empirical_fpr"].mean(),
        "BF Zipfian FPR": df_bf[df_bf["distribution"] == "zipfian"]["empirical_fpr"].mean() if "zipfian" in df_bf["distribution"].values else 0.0,
        "CMS Uniform MAE": df_cms[df_cms["distribution"] == "uniform"]["mae"].mean(),
        "CMS Zipfian MAE": df_cms[df_cms["distribution"] == "zipfian"]["mae"].mean() if "zipfian" in df_cms["distribution"].values else 0.0,
        "HLL Uniform Err (%)": df_hll[df_hll["distribution"] == "uniform"]["relative_error"].mean() * 100,
        "HLL Zipfian Err (%)": df_hll[df_hll["distribution"] == "zipfian"]["relative_error"].mean() * 100 if "zipfian" in df_hll["distribution"].values else 0.0,
    }, index=["Metric Value"]).T

    comp_df.plot(kind="barh", ax=ax, color=["#1f77b4", "#aec7e8", "#d62728", "#ff9896", "#2ca02c", "#98df8a"])
    ax.set_xlabel("Measured Metric Value")
    ax.set_title("Figure 10: Comparison of Metric Behaviors Across Uniform and Zipfian Streams")
    ax.grid(True, axis="x")
    save_figure(fig, output_dir, "10_uniform_vs_zipfian_comparison")
    generated_plots.append("10_uniform_vs_zipfian_comparison")

    # 11. Exact-vs-Approximate Memory Comparison
    fig, ax = plt.subplots(figsize=(9, 5))
    max_size = sizes[-1]
    bf_latest = df_bf[df_bf["stream_size"] == max_size].iloc[0]
    cms_latest = df_cms[df_cms["stream_size"] == max_size].iloc[0]
    hll_latest = df_hll[df_hll["stream_size"] == max_size].iloc[0]

    categories = ["Bloom Filter vs Set", "Count-Min vs Dict", "HyperLogLog vs Set"]
    approx_mem = [
        bf_latest["approx_memory_bytes"] / 1024,
        cms_latest["approx_memory_bytes"] / 1024,
        hll_latest["approx_memory_bytes"] / 1024,
    ]
    exact_mem = [
        bf_latest["exact_memory_bytes"] / 1024,
        cms_latest["exact_memory_bytes"] / 1024,
        hll_latest["exact_memory_bytes"] / 1024,
    ]

    x = np.arange(len(categories))
    width = 0.35
    ax.bar(x - width / 2, exact_mem, width, label="Exact Baseline (KB)", color="#4c72b0")
    ax.bar(x + width / 2, approx_mem, width, label="Approximate Structure (KB)", color="#55a868")

    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.set_ylabel("Memory Consumption (KB, Log Scale)")
    ax.set_title(f"Figure 11: Exact vs. Approximate Memory Footprint (N = {max_size:,})")
    ax.legend()
    ax.grid(True, axis="y")
    save_figure(fig, output_dir, "11_exact_vs_approx_memory_comparison")
    generated_plots.append("11_exact_vs_approx_memory_comparison")

    return generated_plots
