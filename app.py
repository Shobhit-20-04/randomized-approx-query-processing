"""
Streamlit Performance Analysis & Comparison Dashboard
Randomized Data Structures for Approximate Query Processing
Author: Shobhit Agrawal
"""

import collections
import os
import sys
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# Path configuration
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from approx_query.bloom_filter import BloomFilter
from approx_query.count_min_sketch import CountMinSketch
from approx_query.hyperloglog import HyperLogLog

# Page Setup
st.set_page_config(
    page_title="Randomized Data Structures Benchmark",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

RAW_DIR = os.path.join(PROJECT_ROOT, "results", "raw")
PLOTS_DIR = os.path.join(PROJECT_ROOT, "results", "plots")


@st.cache_data
def load_data():
    bf_path = os.path.join(RAW_DIR, "bloom_filter_raw.csv")
    cms_path = os.path.join(RAW_DIR, "count_min_sketch_raw.csv")
    hll_path = os.path.join(RAW_DIR, "hyperloglog_raw.csv")

    if not (os.path.exists(bf_path) and os.path.exists(cms_path) and os.path.exists(hll_path)):
        return None, None, None

    return pd.read_csv(bf_path), pd.read_csv(cms_path), pd.read_csv(hll_path)


df_bf, df_cms, df_hll = load_data()

# App Header - Direct & Clean
st.title("⚡ Approximate Query Processing: Comparative Performance Analysis")
st.caption("Empirical Analysis of **Bloom Filter**, **Count-Min Sketch**, and **HyperLogLog** vs. Exact Baselines | **Author:** Shobhit Agrawal")

if df_bf is None:
    st.error("No benchmark CSV results found. Run `python scripts/run_quick_benchmark.py` first.")
    st.stop()

# Sidebar Controls
st.sidebar.header("Controls & Filters")
dists = sorted(list(set(df_bf["distribution"].unique()) | set(df_cms["distribution"].unique())))
selected_dists = st.sidebar.multiselect("Data Distributions:", dists, default=dists)

sizes = sorted(df_bf["stream_size"].unique())
selected_sizes = st.sidebar.multiselect("Stream Sizes (N):", sizes, default=sizes)

# Filter Data
df_bf_f = df_bf[(df_bf["distribution"].isin(selected_dists)) & (df_bf["stream_size"].isin(selected_sizes))]
df_cms_f = df_cms[(df_cms["distribution"].isin(selected_dists)) & (df_cms["stream_size"].isin(selected_sizes))]
df_hll_f = df_hll[(df_hll["distribution"].isin(selected_dists)) & (df_hll["stream_size"].isin(selected_sizes))]

# Navigation Tabs - Focused Strictly on Comparison and Analysis
tab_overview, tab_bf, tab_cms, tab_hll, tab_graphs, tab_live = st.tabs([
    "📊 Overall Comparison",
    "🔵 Bloom Filter vs Set",
    "🔴 Count-Min Sketch vs Dict",
    "🟢 HyperLogLog vs Set",
    "📈 Analysis Charts",
    "🧪 Live Testbench",
])


# =============================================================================
# TAB 1: OVERALL COMPARISON
# =============================================================================
with tab_overview:
    st.subheader("Performance Comparison Across Data Structures")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Bloom Filter Memory Reduction",
            value=f"{df_bf_f['memory_reduction_ratio'].mean():.1f}x",
            delta=f"False Negatives: {int(df_bf_f['false_negatives'].sum())}",
        )
        st.caption("Query: Membership | Baseline: Python `set`")

    with col2:
        st.metric(
            label="Count-Min Sketch Memory Reduction",
            value=f"{df_cms_f['memory_reduction_ratio'].mean():.1f}x",
            delta=f"Bound Compliance: {df_cms_f['bound_compliance_ratio'].mean() * 100:.1f}%",
        )
        st.caption("Query: Frequency | Baseline: Python `dict`")

    with col3:
        st.metric(
            label="HyperLogLog Memory Reduction",
            value=f"{df_hll_f['memory_reduction_ratio'].mean():.1f}x",
            delta=f"Mean Error: {df_hll_f['relative_error'].mean() * 100:.2f}%",
        )
        st.caption("Query: Distinct Count | Baseline: Python `set`")

    st.markdown("---")

    # Side-by-side Comparative Table
    st.markdown("#### Head-to-Head Comparison Summary")
    summary_data = [
        {
            "Algorithm": "Bloom Filter",
            "Target Operation": "Set Membership (contains)",
            "Exact Baseline": "Python `set`",
            "Avg Memory Reduction": f"{df_bf_f['memory_reduction_ratio'].mean():.1f}x",
            "Observed Accuracy / Error": f"Empirical FPR: {df_bf_f['empirical_fpr'].mean():.4f}",
            "Key Invariant Verified": f"{int(df_bf_f['false_negatives'].sum())} False Negatives (Strict Zero)",
            "Query Latency (Avg)": f"{df_bf_f['approx_query_latency_ns'].mean() / 1000:.2f} µs",
        },
        {
            "Algorithm": "Count-Min Sketch",
            "Target Operation": "Point Frequency (frequency count)",
            "Exact Baseline": "Python `dict` / `Counter`",
            "Avg Memory Reduction": f"{df_cms_f['memory_reduction_ratio'].mean():.1f}x",
            "Observed Accuracy / Error": f"MAE: {df_cms_f['mae'].mean():.2f}",
            "Key Invariant Verified": f"{int(df_cms_f['underestimation_count'].sum())} Underestimations (Strict Zero)",
            "Query Latency (Avg)": f"{df_cms_f['approx_query_latency_ns'].mean() / 1000:.2f} µs",
        },
        {
            "Algorithm": "HyperLogLog",
            "Target Operation": "Distinct Cardinality (unique count)",
            "Exact Baseline": "Python `set` length",
            "Avg Memory Reduction": f"{df_hll_f['memory_reduction_ratio'].mean():.1f}x",
            "Observed Accuracy / Error": f"Relative Error: {df_hll_f['relative_error'].mean() * 100:.2f}%",
            "Key Invariant Verified": f"Within 1-SE: {df_hll_f['within_theoretical_rse'].mean() * 100:.1f}%",
            "Query Latency (Avg)": f"{df_hll_f['approx_query_latency_ns'].mean() / 1000:.2f} µs",
        },
    ]
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

    # Ingestion throughput and memory visual comparison
    st.markdown("#### High-Level Memory & Ingestion Throughput Comparison")
    c1, c2 = st.columns(2)

    with c1:
        # Memory Comparison Bar Chart
        fig_mem, ax_mem = plt.subplots(figsize=(6, 3.8))
        algos = ["Bloom Filter", "Count-Min Sketch", "HyperLogLog"]
        exact_mems = [
            df_bf_f["exact_memory_bytes"].mean() / 1024,
            df_cms_f["exact_memory_bytes"].mean() / 1024,
            df_hll_f["exact_memory_bytes"].mean() / 1024,
        ]
        approx_mems = [
            df_bf_f["approx_memory_bytes"].mean() / 1024,
            df_cms_f["approx_memory_bytes"].mean() / 1024,
            df_hll_f["approx_memory_bytes"].mean() / 1024,
        ]
        x = np.arange(len(algos))
        w = 0.35
        ax_mem.bar(x - w/2, exact_mems, w, label="Exact Baseline (KB)", color="#4a5568")
        ax_mem.bar(x + w/2, approx_mems, w, label="Approximate (KB)", color="#3182ce")
        ax_mem.set_yscale("log")
        ax_mem.set_xticks(x)
        ax_mem.set_xticklabels(algos)
        ax_mem.set_ylabel("Memory in KB (Log Scale)")
        ax_mem.set_title("Average Memory Footprint")
        ax_mem.legend()
        ax_mem.grid(True, linestyle="--", alpha=0.3)
        st.pyplot(fig_mem)

    with c2:
        # Ingestion Latency Comparison
        fig_lat, ax_lat = plt.subplots(figsize=(6, 3.8))
        insert_times = [
            df_bf_f["approx_insert_time_ms"].mean(),
            df_cms_f["approx_insert_time_ms"].mean(),
            df_hll_f["approx_insert_time_ms"].mean(),
        ]
        ax_lat.bar(algos, insert_times, color=["#2b6cb0", "#c53030", "#2f855a"], width=0.5)
        ax_lat.set_ylabel("Mean Insertion Time (ms)")
        ax_lat.set_title("Stream Ingestion Processing Time")
        ax_lat.grid(True, linestyle="--", alpha=0.3)
        st.pyplot(fig_lat)


# =============================================================================
# TAB 2: BLOOM FILTER VS SET
# =============================================================================
with tab_bf:
    st.subheader("Bloom Filter vs. Exact Hash Set")

    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    col_b1.metric("Memory Savings Factor", f"{df_bf_f['memory_reduction_ratio'].mean():.1f}x")
    col_b2.metric("False Negatives", f"{int(df_bf_f['false_negatives'].sum())}", help="Must be 0 for insertion-only BF")
    col_b3.metric("Mean Empirical FPR", f"{df_bf_f['empirical_fpr'].mean():.4f}")
    col_b4.metric("Mean Query Latency", f"{df_bf_f['approx_query_latency_ns'].mean() / 1000:.2f} µs")

    st.markdown("#### Detailed Trial Results")
    st.dataframe(
        df_bf_f[[
            "distribution", "stream_size", "target_fpr", "m_bits", "k_hashes",
            "exact_memory_bytes", "approx_memory_bytes", "memory_reduction_ratio",
            "exact_insert_time_ms", "approx_insert_time_ms",
            "empirical_fpr", "theoretical_fpr", "false_negatives"
        ]].style.format({
            "exact_memory_bytes": "{:,}",
            "approx_memory_bytes": "{:,}",
            "memory_reduction_ratio": "{:.2f}x",
            "exact_insert_time_ms": "{:.2f} ms",
            "approx_insert_time_ms": "{:.2f} ms",
            "empirical_fpr": "{:.4f}",
            "theoretical_fpr": "{:.4f}",
        }),
        use_container_width=True,
    )

    st.download_button(
        "Download Bloom Filter CSV Data",
        data=df_bf_f.to_csv(index=False),
        file_name="bloom_filter_stats.csv",
        mime="text/csv",
    )


# =============================================================================
# TAB 3: COUNT-MIN SKETCH VS DICT
# =============================================================================
with tab_cms:
    st.subheader("Count-Min Sketch vs. Exact Frequency Dict")

    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    col_c1.metric("Memory Savings Factor", f"{df_cms_f['memory_reduction_ratio'].mean():.1f}x")
    col_c2.metric("Underestimations", f"{int(df_cms_f['underestimation_count'].sum())}", help="Must be 0 for standard CMS")
    col_c3.metric("Mean Absolute Error (MAE)", f"{df_cms_f['mae'].mean():.2f}")
    col_c4.metric("Theoretical Bound Compliance", f"{df_cms_f['bound_compliance_ratio'].mean() * 100:.1f}%")

    st.markdown("#### Detailed Trial Results")
    st.dataframe(
        df_cms_f[[
            "distribution", "stream_size", "epsilon", "delta", "table_width", "table_depth",
            "exact_memory_bytes", "approx_memory_bytes", "memory_reduction_ratio",
            "mae", "rmse", "max_overestimation", "bound_compliance_ratio", "underestimation_count"
        ]].style.format({
            "exact_memory_bytes": "{:,}",
            "approx_memory_bytes": "{:,}",
            "memory_reduction_ratio": "{:.2f}x",
            "mae": "{:.2f}",
            "rmse": "{:.2f}",
            "max_overestimation": "{:.1f}",
            "bound_compliance_ratio": "{:.1%}",
        }),
        use_container_width=True,
    )

    st.download_button(
        "Download Count-Min Sketch CSV Data",
        data=df_cms_f.to_csv(index=False),
        file_name="count_min_sketch_stats.csv",
        mime="text/csv",
    )


# =============================================================================
# TAB 4: HYPERLOGLOG VS SET
# =============================================================================
with tab_hll:
    st.subheader("HyperLogLog vs. Exact Set Cardinality")

    col_h1, col_h2, col_h3, col_h4 = st.columns(4)
    col_h1.metric("Memory Savings Factor", f"{df_hll_f['memory_reduction_ratio'].mean():.1f}x")
    col_h2.metric("Mean Relative Error", f"{df_hll_f['relative_error'].mean() * 100:.2f}%")
    col_h3.metric("Theoretical RSE", f"{df_hll_f['theoretical_rse'].mean() * 100:.2f}%")
    col_h4.metric("Within 1-SE Ratio", f"{df_hll_f['within_theoretical_rse'].mean() * 100:.1f}%")

    st.markdown("#### Detailed Trial Results")
    st.dataframe(
        df_hll_f[[
            "distribution", "stream_size", "precision_p", "registers_m",
            "exact_memory_bytes", "approx_memory_bytes", "memory_reduction_ratio",
            "true_cardinality", "estimated_cardinality", "relative_error", "theoretical_rse", "within_theoretical_rse"
        ]].style.format({
            "exact_memory_bytes": "{:,}",
            "approx_memory_bytes": "{:,}",
            "memory_reduction_ratio": "{:.2f}x",
            "true_cardinality": "{:,}",
            "estimated_cardinality": "{:,.1f}",
            "relative_error": "{:.2%}",
            "theoretical_rse": "{:.2%}",
        }),
        use_container_width=True,
    )

    st.download_button(
        "Download HyperLogLog CSV Data",
        data=df_hll_f.to_csv(index=False),
        file_name="hyperloglog_stats.csv",
        mime="text/csv",
    )


# =============================================================================
# TAB 5: ANALYSIS CHARTS
# =============================================================================
with tab_graphs:
    st.subheader("Publication Analysis Charts")
    st.caption("Select a chart category to inspect empirical scaling curves and error trade-offs:")

    chart_category = st.radio(
        "Chart Category:",
        [
            "1. Memory Scaling vs Stream Size",
            "2. Ingestion & Lookup Latency",
            "3. Bloom Filter FPR Accuracy",
            "4. Count-Min Sketch Error & Distribution Skew",
            "5. HyperLogLog Error vs Precision",
            "6. Exact vs Approximate Memory Bar Comparison",
        ],
        horizontal=True,
    )

    if chart_category == "1. Memory Scaling vs Stream Size":
        st.image(os.path.join(PLOTS_DIR, "01_memory_vs_dataset_size.png"), use_container_width=True)
    elif chart_category == "2. Ingestion & Lookup Latency":
        c_i1, c_i2 = st.columns(2)
        with c_i1:
            st.image(os.path.join(PLOTS_DIR, "02_insertion_time_vs_dataset_size.png"), use_container_width=True)
        with c_i2:
            st.image(os.path.join(PLOTS_DIR, "04_query_latency_vs_dataset_size.png"), use_container_width=True)
    elif chart_category == "3. Bloom Filter FPR Accuracy":
        st.image(os.path.join(PLOTS_DIR, "05_bloom_filter_empirical_vs_target_fpr.png"), use_container_width=True)
    elif chart_category == "4. Count-Min Sketch Error & Distribution Skew":
        c_c1, c_c2 = st.columns(2)
        with c_c1:
            st.image(os.path.join(PLOTS_DIR, "06_count_min_sketch_mae_vs_epsilon.png"), use_container_width=True)
        with c_c2:
            st.image(os.path.join(PLOTS_DIR, "07_count_min_sketch_error_by_distribution.png"), use_container_width=True)
    elif chart_category == "5. HyperLogLog Error vs Precision":
        st.image(os.path.join(PLOTS_DIR, "08_hyperloglog_error_vs_precision.png"), use_container_width=True)
    elif chart_category == "6. Exact vs Approximate Memory Bar Comparison":
        st.image(os.path.join(PLOTS_DIR, "11_exact_vs_approx_memory_comparison.png"), use_container_width=True)


# =============================================================================
# TAB 6: LIVE TESTBENCH
# =============================================================================
with tab_live:
    st.subheader("Live Interactive Testbench")
    st.caption("Interact directly with the implemented algorithms and inspect real-time outputs.")

    selected_tool = st.selectbox("Select Structure to Test:", ["Bloom Filter", "Count-Min Sketch", "HyperLogLog"])

    if selected_tool == "Bloom Filter":
        col1, col2 = st.columns(2)
        with col1:
            cap = st.number_input("Target Capacity (n):", 100, 50000, 1000, step=100)
        with col2:
            p_val = st.select_slider("Target FPR (p):", [0.1, 0.05, 0.01, 0.001], value=0.01)

        bf_live = BloomFilter(expected_capacity=cap, target_fpr=p_val)
        st.write(f"**Bit Array Size:** {bf_live.m:,} bits ({bf_live.memory_usage_bytes():,} bytes) | **Hash Functions (k):** {bf_live.k}")

        stream_input = st.text_input("Insert Keys (comma-separated):", "alpha, beta, gamma, delta, epsilon")
        keys = [k.strip() for k in stream_input.split(",") if k.strip()]
        bf_live.add_many(keys)
        st.write(f"**Bits Set:** {bf_live.count_bits_set()} / {bf_live.m} ({bf_live.fill_ratio()*100:.2f}% filled)")

        query_key = st.text_input("Query Key:", "alpha")
        if query_key:
            res = query_key in bf_live
            if res:
                st.success(f"Result: **PROBABLY PRESENT** (Contains = True). Checked bit indices: {bf_live._get_indices(query_key)}")
            else:
                st.error(f"Result: **DEFINITELY ABSENT** (Contains = False). Checked bit indices: {bf_live._get_indices(query_key)}")

    elif selected_tool == "Count-Min Sketch":
        col1, col2 = st.columns(2)
        with col1:
            eps = st.select_slider("Epsilon (error tolerance):", [0.1, 0.05, 0.01], value=0.05)
        with col2:
            del_val = st.select_slider("Delta (failure probability):", [0.1, 0.05, 0.01, 0.001], value=0.01)

        cms_live = CountMinSketch(epsilon=eps, delta=del_val)
        st.write(f"**Table Dimensions:** {cms_live.depth} rows × {cms_live.width:,} columns ({cms_live.memory_usage_bytes():,} bytes)")

        raw_stream = st.text_area("Item Stream Updates (item: count, ...):", "server_1: 45, server_2: 12, server_3: 3, server_1: 15")
        ground_truth = collections.Counter()
        for item in raw_stream.split(","):
            if ":" in item:
                k, v = item.split(":")
                try:
                    c = int(v.strip())
                    cms_live.update(k.strip(), c)
                    ground_truth[k.strip()] += c
                except ValueError:
                    pass

        query_item = st.text_input("Query Frequency Key:", "server_1")
        if query_item:
            est = cms_live.query(query_item)
            true_c = ground_truth.get(query_item, 0)
            bound = cms_live.theoretical_bound(true_c)
            st.info(f"**Estimated Count:** {est} | **Exact Count:** {true_c} | **Theoretical Upper Bound:** {bound:.1f}")
            if est >= true_c:
                st.success("✓ Invariant satisfied (No underestimation)")

    elif selected_tool == "HyperLogLog":
        p_prec = st.slider("Precision (p):", 4, 16, 12)
        hll_live = HyperLogLog(p=p_prec)
        st.write(f"**Registers:** {hll_live.m:,} bytes | **Theoretical RSE:** {hll_live.theoretical_relative_error*100:.2f}%")

        unique_cnt = st.slider("Synthetic Unique Stream Size:", 100, 10000, 2500, step=100)
        test_items = [f"id_{i}" for i in range(unique_cnt)]
        hll_live.add_many(test_items)
        est_card = hll_live.estimate()
        rel_err = abs(est_card - unique_cnt) / unique_cnt * 100

        st.metric("Exact Unique Count", f"{unique_cnt:,}")
        st.metric("HLL Estimated Cardinality", f"{est_card:,.1f}", delta=f"Relative Error: {rel_err:.2f}%")
