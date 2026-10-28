"""
AdaLog-Sketch: Unified Approximate Query Processing & Streaming Data Structures
Research Demonstration & Performance Evaluation Dashboard
Authors: Shobhit Agrawal & Mayuri Rajendra Pawar (School of Computer Science and Engineering, VIT)
"""

import collections
import math
import os
import sys
import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# Configure project paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from adalog.sketch import AdaLogSketch
from baselines.disjoint_stack import DisjointStack
from baselines.count_min_sketch import CountMinSketch
from baselines.bloom_filter import BloomFilter
from baselines.hyperloglog import HyperLogLog
from baselines.elastic_sketch import ElasticSketch
from baselines.augmented_sketch import AugmentedSketch
from planner.planner import AdaLogPlanner
from certificates.debiaser import compute_debiased_frequency
from certificates.intervals import compute_frequency_interval
from certificates.live_certificates import compute_live_fpr, compute_cardinality_certificate
from adalog.compression import compress_matrix, decompress_matrix
from experiments.datasets import generate_zipf_stream, generate_uniform_stream
from core.bindings import is_dll_available, CompiledAdaLog, CompiledDisjoint

# Page configuration
st.set_page_config(
    page_title="AdaLog-Sketch | Unified Streaming Query Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Application Header - Academic & Professional
st.title("⚡ AdaLog-Sketch: Unified Randomized Approximate Query Processing Engine")
st.markdown(
    "**Authors:** Shobhit Agrawal & Mayuri Rajendra Pawar &nbsp;|&nbsp; "
    "*School of Computer Science and Engineering, Vellore Institute of Technology (VIT)*"
)
st.caption(
    "A reproducible comparative case study of **Bloom Filter**, **Count-Min Sketch (CMS)**, and **HyperLogLog (HLL)** "
    "vs. our unified multi-task streaming architecture (**AdaLog-Sketch**)."
)

# Clean 5-Tab Interface
tab_overview, tab_planner, tab_benchmark, tab_certificates, tab_engine = st.tabs([
    "📊 1. Research Overview & Empirical Benchmarks",
    "🧠 2. Interactive AdaLog-Planner (N1)",
    "⚡ 3. Multi-Task Streaming Benchmark",
    "🔍 4. Query Inspector & Error Certificates (N3)",
    "🚀 5. Compiled C++ Engine & Wire Compression",
])


# =============================================================================
# TAB 1: RESEARCH OVERVIEW & EMPIRICAL BENCHMARKS
# =============================================================================
with tab_overview:
    st.subheader("Core Findings & Scientific Trade-offs")
    st.info(
        """
        **Research Finding:** *At equal memory, AdaLog-Sketch reduces frequency error about 3× versus the best same-width 
        Conservative Update sketch and 3–5× versus Elastic and Augmented Sketch up to 64 KB, with zero underestimates. 
        It trades this for weaker membership and cardinality accuracy than dedicated structures, and shows no significant 
        latency change in our C++ harness (1.92 Mops/s vs 1.88 Mops/s, within 1.9% measurement noise).*
        """
    )

    # 4 High-Impact Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label="Equal-Accuracy Memory",
            value="32 KB vs ~44 KB",
            delta="-27.3% RAM vs 16-bit CU",
            delta_color="normal",
        )
        st.caption("-57.9% RAM vs 32-bit CMS stack")
    with c2:
        st.metric(
            label="Compiled C++ Latency",
            value="522.0 ns/op",
            delta="1.92 Mops/s (Comparable)",
            delta_color="off",
        )
        st.caption("Within 1.9% of disjoint stack (532 ns)")
    with c3:
        st.metric(
            label="Frequency Error (32 KB)",
            value="0.40 MAE",
            delta="-84.1% Error vs Disjoint (2.51)",
            delta_color="normal",
        )
        st.caption("3-5x lower error up to 64 KB")
    with c4:
        st.metric(
            label="Lossless Wire Compression",
            value="36.9% – 67.0%",
            delta="5.4 KB compressed payload",
            delta_color="normal",
        )
        st.caption("Inline LightRanger EEG+BBR engine")

    st.divider()

    # Equal-Accuracy Comparison Table
    st.write("### ⚖️ Equal-Accuracy Memory Comparison (Target MAE $\le 0.40$)")
    st.caption("Bytes each design needs to reach the same frequency error floor on the benchmark stream (alpha=1.25, N=300,000).")
    eq_acc_df = pd.DataFrame({
        "Architecture": [
            "AdaLog-Sketch (Ours)",
            "Disjoint Stack (16-bit CU)",
            "Elastic Sketch",
            "Augmented Sketch",
            "Disjoint Stack (32-bit Classical)",
        ],
        "Configuration": [
            "8-bit CU + Elephant Stash (K=64)",
            "16-bit CU CMS + Bloom Filter + HLL",
            "16-bit CU CMS + Heavy Part",
            "16-bit CU CMS + Associative Pre-Filter",
            "32-bit Standard CMS + Bloom Filter + HLL",
        ],
        "Memory Required": ["32 KB", "≈ 44 KB", "≈ 64 KB", "≈ 64 KB", "≈ 76 KB"],
        "AdaLog Memory Savings": ["Baseline", "-27.3% less RAM", "-50.0% less RAM", "-50.0% less RAM", "-57.9% less RAM"],
    })
    st.dataframe(eq_acc_df, use_container_width=True, hide_index=True)

    st.divider()

    # Pre-Registered Acceptance Test Status Table
    st.write("### 🔬 Evaluated Modules & Pre-Registered Acceptance Verdicts")
    st.caption("Every module was evaluated against a strict pre-registered acceptance gate on held-out seeds.")
    
    verdicts_data = {
        "Module": ["N1: AdaLog-Planner", "N2: Adaptive Controller", "N3: Error Certificates", "N4: Theoretical Proofs"],
        "Core Mechanism": [
            "Analytical closed-form error models optimizing (d, w, bits, m, K, tau) under byte budget B",
            "Closed-loop epoch feedback adjusting promotion threshold tau from live telemetry signals",
            "Cross-task collision debiasing via HLL cardinality n_hat + certified [lo, hi] confidence intervals",
            "Formal inductive proof of write-back invariant under saturating counters (K >= K_sat)",
        ],
        "Pre-Registered Acceptance Gate": [
            "Predicted MAE within <= 25% of measured MAE across sweep; beats fixed config on >= 3/5 skews",
            "Beats best single fixed tau on drifting streams (95% CI excludes zero); non-inferior on stationary streams",
            "Empirical interval coverage >= 95% on all datasets; debiased MAE lower than raw estimate",
            "Zero underestimations (f_hat >= f) and zero false negatives verified across 10^6 updates",
        ],
        "Empirical Outcome": [
            "Mean prediction error = 2.74% on held-out seeds; won 5 of 5 skew settings",
            "Non-inferior on stationary stream (ratio 1.000); adaptation lag on sudden drift (Delta MAE = -0.049)",
            "Interval coverage = 99.83%–100.00% (interval widths 5.6–23.3 counts); debiasing cut MAE by 25.6%–76.7%",
            "0 underestimations, 0 false negatives on 10^6 updates; sizing fix K >= K_sat proven",
        ],
        "Falsification Verdict": [
            "✅ ACCEPTED (PASS)",
            "❌ REJECTED (Documented Negative Result)",
            "✅ ACCEPTED (PASS)",
            "✅ ACCEPTED (PASS)",
        ],
    }
    st.dataframe(pd.DataFrame(verdicts_data), use_container_width=True, hide_index=True)

    st.divider()

    # Benchmark Data Accordion
    st.write("### 📋 Published Benchmark Empirical Matrices (Paper Tables II – V)")
    
    with st.expander("Table II: Multi-Task Performance Across Memory Budgets (Zipf alpha = 1.25, N = 300,000, Raw MAE)", expanded=True):
        st.caption("All models evaluated using raw estimates. Baselines equipped with Conservative Update and 16-bit counters.")
        mem_data = {
            "Memory Budget": ["8 KB", "8 KB", "8 KB", "8 KB", "16 KB", "16 KB", "16 KB", "16 KB", "32 KB", "32 KB", "32 KB", "32 KB", "64 KB", "64 KB", "64 KB", "64 KB", "128 KB", "128 KB", "128 KB", "128 KB"],
            "Architecture": [
                "AdaLog-Sketch (Decoupled)", "Disjoint Stack (16-bit CU)", "Elastic Sketch", "Augmented Sketch",
                "AdaLog-Sketch (Decoupled)", "Disjoint Stack (16-bit CU)", "Elastic Sketch", "Augmented Sketch",
                "AdaLog-Sketch (Decoupled)", "Disjoint Stack (16-bit CU)", "Elastic Sketch", "Augmented Sketch",
                "AdaLog-Sketch (Decoupled)", "Disjoint Stack (16-bit CU)", "Elastic Sketch", "Augmented Sketch",
                "AdaLog-Sketch (Decoupled)", "Disjoint Stack (16-bit CU)", "Elastic Sketch (Wins)", "Augmented Sketch",
            ],
            "Frequency MAE": [6.73, 25.85, 19.71, 19.50, 1.75, 8.18, 6.67, 6.53, 0.40, 2.51, 1.90, 1.87, 0.13, 0.78, 0.40, 0.41, 0.10, 0.39, 0.05, 0.08],
            "Frequency ARE": [0.082, 0.312, 0.241, 0.239, 0.021, 0.098, 0.081, 0.079, 0.005, 0.030, 0.023, 0.022, 0.002, 0.009, 0.005, 0.005, 0.001, 0.005, 0.001, 0.001],
            "AMQ FPR": ["99.88%", "64.02%", "N/A", "N/A", "91.30%", "39.98%", "N/A", "N/A", "47.16%", "14.81%", "N/A", "N/A", "11.28%", "2.39%", "N/A", "N/A", "1.37%", "0.06%", "N/A", "N/A"],
            "Cardinality RSE": [0.0360, 0.0098, "N/A", "N/A", 0.0396, 0.0098, "N/A", "N/A", 0.0396, 0.0098, "N/A", "N/A", 0.0396, 0.0098, "N/A", "N/A", 0.0396, 0.0098, "N/A", "N/A"],
            "Top-100 F1 Score": [0.485, 0.000, 0.608, 1.000, 0.780, 0.000, 0.750, 1.000, 0.780, 0.000, 0.810, 1.000, 0.780, 0.000, 0.900, 1.000, 0.780, 0.000, 0.940, 1.000],
            "Underestimate Violations": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        }
        st.dataframe(pd.DataFrame(mem_data), use_container_width=True, hide_index=True)
        st.info("💡 **Trade-off Insights:** (1) **128 KB Crossover**: Elastic Sketch achieves lower MAE (0.05 vs 0.10) because once the matrix is wide (w > 30,000), base collision noise is negligible, diminishing the stash's relative gain. (2) **Membership**: Shared counters (Variant A) lose in FPR to dedicated Bloom filters at all budgets. (3) **Cardinality**: AdaLog-Sketch fixes m=1024 (768 bytes), keeping RSE flat at 0.0396 (4x worse than dedicated HLL's 0.0098).")

    with st.expander("Table III: Skew Sensitivity Evaluation (32 KB Budget, N = 300,000, Raw MAE)"):
        st.caption("All models evaluated using raw estimates under 32 KB total memory.")
        skew_data = {
            "Zipfian Skew (alpha)": ["alpha = 1.05", "alpha = 1.15", "alpha = 1.25", "alpha = 1.35", "alpha = 1.50"],
            "AdaLog MAE": [1.53, 0.85, 0.40, 0.14, 0.02],
            "AdaLog Peak Error": [76, 26, 14, 13, 7],
            "Disjoint Stack MAE": [7.25, 4.23, 2.51, 3.47, 10.14],
            "Disjoint Peak Error": [215, 148, 94, 102, 280],
            "Elastic Sketch MAE": [6.61, 3.75, 1.90, 0.81, 0.16],
            "Augmented Sketch MAE": [6.42, 3.67, 1.87, 0.81, 0.19],
            "Error Reduction vs Disjoint": ["-78.9% (4.7x)", "-79.9% (5.0x)", "-84.1% (6.3x)", "-96.0% (24.8x)", "-99.8% (vs Disjoint)"],
        }
        st.dataframe(pd.DataFrame(skew_data), use_container_width=True, hide_index=True)
        st.info("💡 **Why Disjoint Error Rises While Elastic and AdaLog Fall:** In disjoint CMS without a stash, higher skew concentrates volume into dominant keys. Tail items colliding with dominant keys suffer severe overestimation spikes (Disjoint MAE jumps from 2.51 to 10.14). With a stash (Elastic and AdaLog), top keys are intercepted, reducing the residual volume entering the matrix and lowering collision noise.")

    with st.expander("Table IV: Native Compiled C++ Latency and Throughput (N = 1,000,000 operations)"):
        st.caption("Compiled with MinGW GCC 16.1.0 (-O3 -static) on x86-64 testbed.")
        cpp_data = {
            "Streaming Structure": ["AdaLog-Core (Unified)", "Disjoint-Core (BF+CMS+HLL)", "CMS-Core (Standalone CMS-CU)", "Bloom-Core (Standalone BF)", "HLL-Core (Standalone HLL)"],
            "Implementation": ["C++ (x86-64, -O3)", "C++ (x86-64, -O3)", "C++ (x86-64, -O3)", "C++ (x86-64, -O3)", "C++ (x86-64, -O3)"],
            "Ingestion Throughput": ["1.92 Mops/s", "1.88 Mops/s", "1.95 Mops/s", "2.45 Mops/s", "2.47 Mops/s"],
            "Update Latency (Mean)": ["522.0 ns/op", "532.3 ns/op", "513.8 ns/op", "407.8 ns/op", "404.3 ns/op"],
            "Point Query Latency": ["397.3 ns/op", "504.4 ns/op (CMS)", "380.1 ns/op", "N/A", "N/A"],
            "AMQ Query Latency": ["389.8 ns/op", "407.8 ns/op (BF)", "N/A", "385.0 ns/op", "N/A"],
            "Latency Comparison": ["Comparable (1.9% diff)", "Baseline", "N/A", "N/A", "N/A"],
        }
        st.dataframe(pd.DataFrame(cpp_data), use_container_width=True, hide_index=True)

    with st.expander("Table V: Systematic Ablation Matrix (32 KB Budget, Zipf alpha = 1.25, Raw MAE)"):
        st.caption("Consistent with Table II: Decoupled HLL row (m=1024) achieves MAE 0.40 and FPR 47.11%.")
        abl_data = {
            "Ablation Variant": [
                "Coupled HLL Layout (m=w)",
                "Decoupled HLL Layout (m=1024) [Table II Default]",
                "No Stash (-Stash)",
                "No CU (-Conservative Update)",
                "16-bit Narrow Counters",
                "32-bit Classical Counters",
                "Membership Variant B (1-bit Plane)",
            ],
            "Matrix Width w": [9984, 9984, 10240, 9984, 3968, 1984, 7200],
            "Frequency MAE": [0.54, 0.40, 15.71, 1.28, 1.71, 5.48, 0.54],
            "Peak Overestimate": [19, 14, 79, 33, 365, 88, 19],
            "Membership FPR": ["55.89%", "47.11%", "54.96%", "55.89%", "91.08%", "99.89%", "99.91%"],
            "Cardinality RSE": [0.0399, 0.0396, 0.0157, 0.0399, 0.0043, 0.0061, 0.0399],
            "Key Engineering Takeaway": [
                "Coupled HLL layout leaves less matrix padding (MAE 0.54)",
                "Decoupled HLL fixes m=1024, achieving best MAE (0.40) and lowest peak error (14)",
                "MAE inflates by 29.1x without associative stash under skew",
                "MAE increases by 2.37x with naive counter increments",
                "Halving columns quadruples collision noise (3.16x MAE)",
                "Quartering columns degrades MAE by 10.1x",
                "1-bit plane consumes budget without improving FPR at 32KB",
            ],
        }
        st.dataframe(pd.DataFrame(abl_data), use_container_width=True, hide_index=True)


# =============================================================================
# TAB 2: INTERACTIVE ADALOG-PLANNER (N1)
# =============================================================================
with tab_planner:
    st.subheader("🧠 AdaLog-Planner: Analytical Joint Memory Optimization")
    st.markdown(
        """
        Given a global byte budget $B$ and expected streaming workload characteristics, **AdaLog-Planner** 
        analytically derives the optimal multi-task configuration:
        $$(d, w, \\text{counter\\_bits}, m, K, \\tau)$$
        balancing frequency error (CMS-CU), membership false positive rate (AMQ), and cardinality precision (HLL).
        """
    )

    pl_col1, pl_col2, pl_col3 = st.columns(3)
    with pl_col1:
        target_budget = st.slider("Total Memory Budget (KB):", min_value=8, max_value=256, value=32, step=8) * 1024
    with pl_col2:
        expected_stream = st.slider("Stream Volume (N elements):", min_value=50000, max_value=1000000, value=300000, step=50000)
    with pl_col3:
        workload_skew = st.slider("Workload Skew (Zipf alpha):", min_value=0.8, max_value=2.0, value=1.25, step=0.05)

    planner = AdaLogPlanner()
    opt_config = planner.optimize(
        budget_bytes=target_budget,
        n_stream=expected_stream,
        n_unique=max(1000, expected_stream // 10),
        skew=workload_skew,
    )

    st.success(f"Optimal Configuration Derived for {target_budget:,} Bytes ({target_budget // 1024} KB)")

    pc1, pc2, pc3, pc4, pc5, pc6 = st.columns(6)
    with pc1:
        st.metric("Matrix Depth (d)", f"{opt_config.d}")
    with pc2:
        st.metric("Matrix Width (w)", f"{opt_config.w:,}")
    with pc3:
        st.metric("Counter Width", f"{opt_config.counter_bits}-bit")
    with pc4:
        st.metric("HLL Registers (m)", f"{opt_config.m:,}")
    with pc5:
        st.metric("Stash Capacity (K)", f"{opt_config.K}")
    with pc6:
        st.metric("Threshold (tau)", f"{opt_config.tau}")

    st.divider()

    # Single-column aligned analytical error predictions and memory breakdown
    st.write("#### 📈 Planner-Predicted Analytical Error Targets")
    pred_df = pd.DataFrame({
        "Query Metric": ["Predicted Frequency MAE", "Predicted Membership FPR", "Predicted Cardinality RSE"],
        "Theoretical Prediction": [
            f"{opt_config.predicted_mae:.2f} counts",
            f"{opt_config.predicted_fpr * 100:.2f}%",
            f"{opt_config.predicted_rse * 100:.2f}%",
        ],
        "Underlying Analytical Model": [
            "CMS-CU damped noise floor: (N - V_stash) / (w * (1 + 0.5*d^2))",
            "Product of independent row occupancies: (1 - e^(-n/w))^d",
            "Flajolet asymptotic standard error: 1.04 / sqrt(m)",
        ],
    })
    st.dataframe(pred_df, use_container_width=True, hide_index=True)
    st.info("💡 **Acceptance Gate Passed:** AdaLog-Planner's predicted MAE matches empirical measured error within **2.74%** across memory sweeps.")

    st.write("#### 🧩 Internal Memory Partition Breakdown")
    matrix_bytes = int((opt_config.d * opt_config.w * opt_config.counter_bits) / 8)
    hll_bytes = int((opt_config.m * 6 + 7) / 8)
    stash_bytes = opt_config.K * 16
    actual_total = matrix_bytes + hll_bytes + stash_bytes

    mem_breakdown = pd.DataFrame({
        "Component": ["Base Counter Matrix (d x w)", "Packed 6-bit HLL Registers", "Associative Elephant Stash"],
        "Bytes Allocated": [f"{matrix_bytes:,} Bytes", f"{hll_bytes:,} Bytes", f"{stash_bytes:,} Bytes"],
        "Percentage of Total": [
            f"{matrix_bytes / actual_total * 100:.1f}%",
            f"{hll_bytes / actual_total * 100:.1f}%",
            f"{stash_bytes / actual_total * 100:.1f}%",
        ],
    })
    st.dataframe(mem_breakdown, use_container_width=True, hide_index=True)
    st.caption(f"Total Allocated: **{actual_total:,} Bytes** (Remaining padding: {target_budget - actual_total} Bytes)")


# =============================================================================
# TAB 3: MULTI-TASK STREAMING BENCHMARK
# =============================================================================
with tab_benchmark:
    st.subheader("⚡ Live Head-to-Head Streaming Workload Benchmark")
    st.caption("Generate synthetic skewed query streams and evaluate real-time multi-task error reductions.")

    b_col1, b_col2, b_col3 = st.columns(3)
    with b_col1:
        workload_type = st.selectbox(
            "Select Stream Distribution:",
            ["Heavy-Tailed Zipfian Stream (alpha = 1.25)", "High-Skew Zipfian Stream (alpha = 1.50)", "Moderate Zipfian Stream (alpha = 1.05)", "Uniform Key Stream"],
        )
    with b_col2:
        stream_len = st.slider("Stream Ingestion Size (N keys):", 5000, 50000, 20000, step=5000)
    with b_col3:
        tau_val = st.slider("Elephant Stash Threshold (tau):", 5, 50, 15)

    if st.button("🚀 Run Live Comparative Benchmark", type="primary", use_container_width=True):
        with st.spinner("Generating stream keys and updating streaming synopses..."):
            if "1.50" in workload_type:
                alpha = 1.50
            elif "1.05" in workload_type:
                alpha = 1.05
            elif "Uniform" in workload_type:
                alpha = 0.0
            else:
                alpha = 1.25

            if alpha > 0.0:
                stream_keys, ground_truth = generate_zipf_stream(
                    n_stream=stream_len,
                    n_unique=max(500, stream_len // 5),
                    alpha=alpha,
                    seed=42,
                )
            else:
                stream_keys, ground_truth = generate_uniform_stream(
                    n_stream=stream_len,
                    n_unique=max(500, stream_len // 5),
                    seed=42,
                )

            true_cardinality = len(ground_truth)

            # 1. Benchmark AdaLog-Sketch
            t0 = time.perf_counter()
            adalog = AdaLogSketch(
                width=1024,
                depth=4,
                counter_bits=8,
                stash_capacity=64,
                stash_tau=tau_val,
                seed=42,
            )
            adalog.update_many(stream_keys)
            adalog_time = (time.perf_counter() - t0) * 1000.0
            adalog_metrics = adalog.compute_metrics(ground_truth, true_cardinality)

            # 2. Benchmark Disjoint Baseline Stack
            t0 = time.perf_counter()
            disjoint = DisjointStack(
                expected_cardinality=true_cardinality,
                cms_width=1024,
                cms_depth=4,
                cms_counter_bits=16,
                seed=42,
            )
            disjoint.update_many(stream_keys)
            disjoint_time = (time.perf_counter() - t0) * 1000.0

            disjoint_errs = [abs(disjoint.estimate(k) - true_c) for k, true_c in ground_truth.items()]
            disjoint_mae = float(np.mean(disjoint_errs))
            disjoint_peak = float(np.max(disjoint_errs))
            disjoint_card_rse = abs(disjoint.cardinality() - true_cardinality) / max(1, true_cardinality)

            # 3. Benchmark Elastic Sketch
            elastic = ElasticSketch(heavy_buckets=64, light_width=1024, light_depth=4, seed=42)
            for k in stream_keys:
                elastic.update(k)
            elastic_errs = [abs(elastic.estimate(k) - true_c) for k, true_c in ground_truth.items()]
            elastic_mae = float(np.mean(elastic_errs))

            # 4. Benchmark Augmented Sketch
            augmented = AugmentedSketch(filter_capacity=64, sketch_width=1024, sketch_depth=4, seed=42)
            for k in stream_keys:
                augmented.update(k)
            augmented_errs = [abs(augmented.estimate(k) - true_c) for k, true_c in ground_truth.items()]
            augmented_mae = float(np.mean(augmented_errs))

            # Display Live Metrics Cards
            st.success(f"Ingested {stream_len:,} stream elements ({true_cardinality:,} unique keys) successfully!")
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                mae_cut = (disjoint_mae - adalog_metrics["mae"]) / max(0.001, disjoint_mae) * 100.0
                st.metric(
                    "Frequency MAE",
                    f"{adalog_metrics['mae']:.2f}",
                    delta=f"-{mae_cut:.1f}% vs Disjoint ({disjoint_mae:.2f})",
                    delta_color="normal",
                )
            with m2:
                peak_cut = disjoint_peak - adalog_metrics["max_overestimation"]
                st.metric(
                    "Peak Overestimation",
                    f"{adalog_metrics['max_overestimation']:.0f}",
                    delta=f"-{peak_cut:.0f} noise cut vs Disjoint",
                    delta_color="normal",
                )
            with m3:
                card_pct = adalog_metrics["cardinality_relative_error"] * 100.0
                st.metric(
                    "Estimated Cardinality",
                    f"{int(adalog.cardinality()):,}",
                    delta=f"RSE: {card_pct:.2f}% (True: {true_cardinality:,})",
                )
            with m4:
                speedup = disjoint_time / max(0.001, adalog_time)
                st.metric(
                    "Ingestion Speedup",
                    f"{speedup:.2f}x Faster",
                    delta=f"{adalog_time:.1f} ms vs {disjoint_time:.1f} ms",
                    delta_color="normal",
                )

            st.divider()

            # Single-column aligned Heavy Hitters Table and Error Plot
            st.write("#### 🐘 O(1) Extracted Heavy Hitters (Elephant Stash)")
            st.caption("Stash counts include CMS baseline noise recorded upon promotion (bounded <= tau). Post-promotion increments are tracked exactly.")
            heavy_items = adalog.top_k(10)
            if heavy_items:
                df_hh = pd.DataFrame([
                    {
                        "Item Key": k,
                        "Estimated Frequency": v,
                        "Ground Truth": ground_truth.get(k, 0),
                        "Estimation Error": v - ground_truth.get(k, 0),
                        "Stash Accounting": "Exact Match" if v == ground_truth.get(k, 0) else f"+{v - ground_truth.get(k, 0)} base noise",
                    }
                    for k, v in heavy_items
                ])
                st.dataframe(df_hh, use_container_width=True, hide_index=True)
            else:
                st.info("No items exceeded the promotion threshold.")

            st.write("#### 📊 Frequency Collision Error on Top Frequent Items")
            top_items = [k for k, _ in sorted(ground_truth.items(), key=lambda kv: kv[1], reverse=True)[:15]]
            disjoint_item_err = [disjoint.estimate(k) - ground_truth[k] for k in top_items]
            adalog_item_err = [adalog.estimate(k) - ground_truth[k] for k in top_items]

            fig, ax = plt.subplots(figsize=(10, 3.8))
            x_pos = np.arange(len(top_items))
            bar_w = 0.35
            ax.bar(x_pos - bar_w/2, disjoint_item_err, width=bar_w, label="Disjoint Stack", color="#d9534f", alpha=0.85)
            ax.bar(x_pos + bar_w/2, adalog_item_err, width=bar_w, label="AdaLog-Sketch (Ours)", color="#5cb85c", alpha=0.85)
            ax.set_ylabel("Overestimation Error (Counts)", fontsize=10)
            ax.set_xlabel("Top Items (Ranked by Ground Truth Frequency)", fontsize=10)
            ax.set_xticks(x_pos)
            ax.set_xticklabels(top_items, rotation=25, ha="right", fontsize=9)
            ax.set_title("Frequency Collision Error Comparison (Lower is Better)", fontsize=11, fontweight="bold")
            ax.legend(fontsize=9)
            ax.grid(True, linestyle="--", alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig)


# =============================================================================
# TAB 4: QUERY INSPECTOR & ERROR CERTIFICATES (N3)
# =============================================================================
with tab_certificates:
    st.subheader("🔍 Query Inspector & Cross-Task Error Certificates (Contribution N3)")
    st.markdown(
        """
        Classical probabilistic data structures return single point estimates with zero reliability guarantees.
        **AdaLog-Sketch (N3)** exploits cross-task synergies (combining total volume $N$, HLL cardinality $\\hat{n}$, 
        and matrix fill factor) to return **certified confidence intervals and live error probabilities**:
        - **Certified Frequency Interval $[\\text{lo}, \\text{hi}]$:** $\\text{hi}$ is the safe CMS-CU upper bound (never underestimates); $\\text{lo}$ is bounded via Chebyshev collision tail bounds.
        - **Debiased Frequency $\\tilde{f}(x)$:** Subtracts expected matrix collision noise using HLL cardinality $\\hat{n}$.
        - **Live AMQ False-Positive Probability $P_{\\text{FP}}(t)$:** Dynamically computed from exact matrix row occupancies.
        - **Cardinality Confidence Interval:** Flajolet asymptotic variance $[n_{\\text{lo}}, n_{\\text{hi}}]$ at $95\\%$ confidence.
        """
    )

    # Initialize a demo sketch with skewed data
    @st.cache_resource
    def get_certified_demo_sketch():
        keys, truth = generate_zipf_stream(n_stream=30000, n_unique=3000, alpha=1.25, seed=42)
        sk = AdaLogSketch(width=1024, depth=4, counter_bits=8, stash_capacity=64, stash_tau=15, seed=42)
        sk.update_many(keys)
        return sk, truth

    demo_sketch, demo_truth = get_certified_demo_sketch()

    # Query Input UI
    q_col1, q_col2 = st.columns([2, 1])
    with q_col1:
        sample_keys = [k for k, _ in sorted(demo_truth.items(), key=lambda kv: kv[1], reverse=True)[:5]]
        query_key = st.text_input("Enter Key to Query:", value=sample_keys[0])
    with q_col2:
        st.write("Or pick a sample key:")
        c_p1, c_p2, c_p3 = st.columns(3)
        if c_p1.button("Heavy Key (Rank 1)"):
            query_key = sample_keys[0]
        if c_p2.button("Moderate Key"):
            query_key = sample_keys[3]
        if c_p3.button("Absent Key"):
            query_key = "key_unseen_9999"

    # Compute certificates
    f_raw = demo_sketch.estimate(query_key)
    true_f = demo_truth.get(query_key, 0)
    is_stash = demo_sketch.use_stash and (query_key in demo_sketch.stash.entries)
    stash_base = demo_sketch.stash.entries[query_key].base_count if is_stash else 0
    stash_vol = sum(e.total_count for e in demo_sketch.stash.entries.values()) if demo_sketch.use_stash else 0

    card_est = int(demo_sketch.cardinality())
    f_debiased = compute_debiased_frequency(
        f_raw=f_raw,
        total_stream_items=demo_sketch.total_volume,
        cardinality_estimate=card_est,
        w=demo_sketch.width,
        d=demo_sketch.depth,
        is_stash_hit=is_stash,
        stash_baseline=stash_base,
        stash_volume=stash_vol,
    )

    f_lo, f_hi = compute_frequency_interval(
        f_raw=f_raw,
        total_stream_items=demo_sketch.total_volume,
        w=demo_sketch.width,
        d=demo_sketch.depth,
        confidence=0.95,
        is_stash_hit=is_stash,
        stash_baseline=stash_base,
    )

    live_fpr = compute_live_fpr(demo_sketch)
    card_cert = compute_cardinality_certificate(card_est, demo_sketch.hll_m, confidence=0.95)

    st.divider()

    # Display Query Certificates
    st.write(f"### 📋 Certified Audit Report for Key: `{query_key}`")
    
    cert_c1, cert_c2, cert_c3, cert_c4 = st.columns(4)
    with cert_c1:
        st.metric("Raw Estimate (Safe Upper Bound)", f"{f_raw}", delta=f"Ground Truth: {true_f}")
        st.caption("Guaranteed never to underestimate")
    with cert_c2:
        mae_reduct = abs(f_raw - true_f) - abs(f_debiased - true_f)
        st.metric(
            "Debiased Estimate (N3)",
            f"{f_debiased}",
            delta=f"{'+' if mae_reduct >= 0 else ''}{mae_reduct} error reduction",
            delta_color="normal",
        )
        st.caption("Noise subtracted via HLL cardinality")
    with cert_c3:
        contains_truth = (f_lo <= true_f <= f_hi)
        st.metric(
            "95% Certified Interval",
            f"[{f_lo}, {f_hi}]",
            delta="✓ Contains True Count" if contains_truth else "Interval Miss",
            delta_color="normal" if contains_truth else "inverse",
        )
        st.caption(f"Interval width: {f_hi - f_lo} counts")
    with cert_c4:
        st.metric("Storage Tier", "🐘 Elephant Stash (Exact O(1))" if is_stash else "Base Table Matrix")
        st.caption("Fast-path cache bypass" if is_stash else "Base saturating counter")

    st.write("#### 🛡️ Live Membership & Cardinality Certificates")
    lm_c1, lm_c2 = st.columns(2)
    with lm_c1:
        is_present = demo_sketch.contains(query_key)
        st.info(
            f"**AMQ Membership Status:** `{'PRESENT' if is_present else 'ABSENT'}`  \n"
            f"**Live Dynamic False Positive Rate:** `{live_fpr * 100:.2f}%`  \n"
            f"*(Calculated dynamically from current matrix occupancy across all {demo_sketch.depth} rows)*"
        )
    with lm_c2:
        c_lo, c_hi = card_cert.confidence_interval
        st.info(
            f"**Distinct Cardinality Estimate:** `{card_est:,}` unique keys  \n"
            f"**95% Confidence Bounds:** `[{c_lo:,}, {c_hi:,}]` unique keys  \n"
            f"**Relative Standard Error (RSE):** `±{card_cert.relative_standard_error * 100:.2f}%` (Flajolet limit: 1.04 / √m)"
        )


# =============================================================================
# TAB 5: NATIVE C++ ENGINE & WIRE COMPRESSION
# =============================================================================
with tab_engine:
    st.subheader("🚀 High-Performance C++ Kernel & LightRanger Wire Compression")
    st.markdown(
        """
        To achieve sub-microsecond ingestion in production environments, AdaLog-Sketch is implemented as a 
        compiled C++ dynamic library (`adalog_core.dll`) compiled with `-O3 -static` optimizations.
        For distributed network transmission and disk snapshots, an inline **LightRanger** engine 
        compresses counter matrices losslessly.
        """
    )

    cpp_c1, cpp_c2 = st.columns([1, 1])
    with cpp_c1:
        st.write("#### ⚙️ Native C++ Engine Status & Live Benchmark")
        dll_status = is_dll_available()
        if dll_status:
            st.success("✅ **Native C++ Library Loaded:** `core/adalog_core.dll` is active and linked via ctypes.")
        else:
            st.warning("⚠️ C++ dynamic library not found. Falling back to high-performance Python reference.")

        if st.button("⚡ Run Live C++ Speed Test (100,000 Keys)", use_container_width=True):
            if dll_status:
                test_keys, _ = generate_zipf_stream(n_stream=100000, n_unique=10000, alpha=1.25, seed=42)
                
                # C++ Benchmark
                cpp_sketch = CompiledAdaLog(width=1024, depth=4, counter_bits=8, stash_capacity=64, elephant_threshold=20)
                t0 = time.perf_counter()
                cpp_sketch.update_batch(test_keys)
                cpp_elapsed = time.perf_counter() - t0
                cpp_throughput = (100000 / cpp_elapsed) / 1e6
                cpp_latency_ns = (cpp_elapsed / 100000) * 1e9

                st.metric("C++ Ingestion Throughput", f"{cpp_throughput:.2f} Mops/s", delta=f"{cpp_latency_ns:.1f} ns/op")
                st.info(f"Ingested 100,000 keys in **{cpp_elapsed * 1000.0:.2f} ms** via compiled C++ kernel.")
            else:
                st.error("C++ DLL is not available on this system.")

    with cpp_c2:
        st.write("#### 📦 Inline LightRanger Lossless State Compression (Exp 8)")
        st.markdown(
            """
            Compresses counter matrices by combining:
            1. **Equal Element Grouping (EEG):** Partitions rows into blocks of $L_g = 8$ cells.
            2. **Base-Bit Reduction (BBR):** Subtracts group minimum $v_{\\min}$.
            3. **Dynamic Bit-Packing:** Stores residuals $\\Delta$ using only $\\lceil \\log_2(\\max \\Delta + 1) \\rceil$ bits.
            """
        )

        test_sketch = AdaLogSketch(width=4096, depth=4, counter_bits=8, stash_capacity=64, stash_tau=15, seed=42)
        stream_sample, _ = generate_zipf_stream(n_stream=50000, n_unique=5000, alpha=1.25, seed=42)
        test_sketch.update_many(stream_sample)

        raw_bytes = test_sketch.table.nbytes
        t_c0 = time.perf_counter()
        compressed_bytes = test_sketch.compress_wire(group_size=8)
        comp_time = (time.perf_counter() - t_c0) * 1000.0
        comp_size = len(compressed_bytes)
        savings = (1.0 - (comp_size / raw_bytes)) * 100.0

        # Decompression check
        t_d0 = time.perf_counter()
        decompressed_matrix = decompress_matrix(compressed_bytes)
        decomp_time = (time.perf_counter() - t_d0) * 1000.0
        is_identical = np.array_equal(test_sketch.table, decompressed_matrix)

        st.metric(
            "State Serialization Size",
            f"{comp_size:,} Bytes",
            delta=f"-{savings:.1f}% reduction (from {raw_bytes:,} Bytes)",
            delta_color="normal",
        )
        st.caption(f"Compression time: **{comp_time:.2f} ms** | Decompression time: **{decomp_time:.2f} ms**")

        if is_identical:
            st.success("✅ **Bit-Exact Lossless Roundtrip Verified:** Decompressed matrix is 100% identical to original state.")
        else:
            st.error("Lossy reconstruction error detected.")
