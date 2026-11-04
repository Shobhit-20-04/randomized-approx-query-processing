# Experimental Results Directory

This directory stores raw experimental telemetry, processed audit outputs, publication figures, and validation plots.

---

## 1. Directory Layout

```text
results/
├── raw/                     # Untampered experimental JSON and CSV logs
│   ├── exp1_memory_sweep.json           # 35 records across 5 synopses, 8KB–512KB (10 seeds)
│   ├── exp2_skew_sweep.json             # Skew sweep records across alpha 1.05–1.50 (10 seeds)
│   ├── exp3_latency_benchmark.json      # C++ throughput (21.97 Mops/s) and update/query latency
│   ├── exp4_ablations.json              # Component ablation metrics (7 variants, 10 seeds)
│   ├── exp5_planner_eval.json           # Analytical planner configuration evaluation
│   ├── exp6_adaptive_eval.py            # Adaptive threshold controller negative result
│   ├── exp7_certificates_eval.json      # Interval coverage metrics
│   ├── exp8_compression.json            # LightRanger bit-plane compression ratios
│   ├── exp9_real_and_failure_modes.json # CAIDA and Gutenberg real trace evaluation
│   ├── cardinality_100trials.json       # 100-seed HLL cardinality validation (RSE = 0.0239)
│   └── equal_accuracy_search.json       # Budget binary search for MAE <= 0.40
│
├── processed/               # Processed tabular summaries
│   └── AdaLog_Sketch_Audit_Test_Results.csv # 14 independent verification test results
│
├── figures/                 # High-resolution PNG figures generated from raw data
│   ├── fig1_memory_pareto.png
│   ├── fig2_skew_sensitivity.png
│   ├── fig3_latency_throughput.png
│   ├── fig4_ablations.png
│   ├── fig5_planner_accuracy.png
│   ├── fig7_certificates_coverage.png
│   └── fig8_compression_ratio.png
│
└── plots/                   # Publication-ready vector PDF plots
```

---

## 2. Experimental Traceability Matrix

| Metric | Measured Value | Provenance / Source File | Testbed Hardware |
| :--- | :--- | :--- | :--- |
| **Ingestion Throughput** | $21.97 \pm 0.38$ Mops/s | `results/raw/exp3_latency_benchmark.json` | Intel Core i5-13450HX, GCC 11.2 `-O3 -mavx2` |
| **Update Latency** | $45.52 \pm 0.79$ ns/op | `results/raw/exp3_latency_benchmark.json` | Intel Core i5-13450HX, GCC 11.2 `-O3 -mavx2` |
| **Point Query Latency** | $13.43 \pm 0.22$ ns/op | `results/raw/exp3_latency_benchmark.json` | Intel Core i5-13450HX, GCC 11.2 `-O3 -mavx2` |
| **Membership Latency** | $12.26 \pm 0.19$ ns/op | `results/raw/exp3_latency_benchmark.json` | Intel Core i5-13450HX, GCC 11.2 `-O3 -mavx2` |
| **Cardinality RSE** | $0.0239$ ($2.39\%$) | `results/raw/cardinality_100trials.json` | Python 3.11, 100 independent seeds |
| **32 KB Frequency MAE** | $0.61 \pm 0.00$ | `results/raw/exp1_memory_sweep.json` | Zipfian $\alpha = 1.25, N = 300,000$ |
| **Disjoint+Stash MAE** | $0.92 \pm 0.01$ | `results/raw/exp1_memory_sweep.json` | Historical baseline ($33,790$ bytes) |
| **Strict Baseline MAE** | $\approx 0.95$ | `baselines/disjoint_stack.py` | Strict 32 KB allocation ($w = 5,785$) |
