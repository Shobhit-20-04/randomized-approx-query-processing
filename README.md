# Beyond Bloom Filter, Count-Min Sketch, and HyperLogLog: AdaLog-Sketch

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![C++ Engine: MinGW x86-64](https://img.shields.io/badge/C++%20Core-1.92%20Mops%2Fs-success.svg)](core/)
[![Streamlit App](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg)](http://localhost:8501)

A reproducible research codebase and benchmark case study evaluating classical probabilistic data structures (**Bloom Filter**, **Count-Min Sketch**, **HyperLogLog**, **Elastic Sketch**, **Augmented Sketch**) alongside **AdaLog-Sketch**—a unified randomized algorithm that executes Approximate Membership Queries (AMQ), Point Frequency Estimation, Distinct Cardinality Counting, and Heavy Hitters from a **single shared memory block driven by a single 128-bit hash computation per stream item**.

**Authors:** Shobhit Agrawal & Mayuri Rajendra Pawar (Vellore Institute of Technology, Vellore)  
**Faculty Guide:** Dr. Parveen Sultana H (Associate Dean in-charge, School of Computer Science and Engineering - SCOPE, VIT Vellore)  
**Repository:** [https://github.com/Shobhit-20-04/randomized-approx-query-processing](https://github.com/Shobhit-20-04/randomized-approx-query-processing)

---

## ⚡ Executive Performance Matrix

All metrics are grounded in reproducible benchmarks on 64-bit Windows (x86-64, compiled C++ with MinGW GCC 16.1.0 `-O3`):

| Streaming Data Structure | Unified Query Support | Ingestion Latency (Mean) | Ingestion Throughput | Frequency MAE (32 KB Budget) | AMQ False Positive Rate | Zero Underestimate Guarantee |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **AdaLog-Sketch (Ours)** | **Membership + Frequency + Cardinality + Top-$k$** | **522.0 ns/op** | **1.92 Mops/s** | **0.40** | **47.16% (Var A) / 0.11% (256KB)** | **Strictly 0 Underestimates** |
| **Disjoint Stack (BF+CMS+HLL)** | Membership + Frequency + Cardinality | 532.3 ns/op | 1.88 Mops/s | 2.51 | 14.81% | Bounded by CMS |
| **Augmented Sketch** (SIGMOD 2016) | Frequency + Top-$k$ | ~530 ns/op | ~1.89 Mops/s | 1.87 | N/A | Bounded |
| **Elastic Sketch** (SIGCOMM 2018) | Frequency + Top-$k$ | ~530 ns/op | ~1.89 Mops/s | 1.90 | N/A | Bounded |
| **Count-Min Sketch (CMS-CU)** | Frequency only | 513.8 ns/op | 1.95 Mops/s | 2.85 | N/A | Strictly $\hat{f} \ge f$ |
| **Standard Bloom Filter** | Membership only | 407.8 ns/op | 2.45 Mops/s | N/A | Target FPR | Zero False Negatives |
| **HyperLogLog (HLL)** | Cardinality only | 404.3 ns/op | 2.47 Mops/s | N/A | N/A | $\text{RSE} \approx 1.04/\sqrt{m}$ |

---

## 🔬 Core Novel Contributions & Falsification Verdicts

In accordance with strict empirical science, all novel modules were tested against pre-registered acceptance criteria on held-out seeds:

| Module | Title | Core Mechanism | Acceptance Test Gate | Empirical Outcome | Verdict |
|---|---|---|---|---|---|
| **N1** | **AdaLog-Planner** | Analytical error models solving for $(d, w, \text{bits}, m, K, \tau)$ given budget $B$. | Predicted error $\le \pm 25\%$ across memory sweep; beats fixed config on $\ge 3/5$ skews. | Mean prediction error = **2.74%**; won **5/5** skew evaluations ($35.8\%\text{--}94.2\%$ lower MAE). | **ACCEPTED (PASS)** |
| **N2** | **Online Adaptive Controller** | Closed-loop epoch controller tuning $\tau$ via internal telemetry ($S$, $D$, $H$, $\hat{\alpha}$). | On drifting streams ($\alpha: 1.1 \to 1.5 \to 1.2$), beats best fixed $\tau$ with 95% CI excluding 0. | Non-inferior on stationary stream (ratio 1.000); incurred transition lag on drifting streams ($\Delta \text{MAE} = -0.049$). | **REJECTED (FAIL)** *(Documented Negative Result)* |
| **N3** | **Cross-Task Error Certificates** | Count-Mean-Min residual debiasing using HLL cardinality $\hat{n}$; certified $[\text{lo}, \text{hi}]$ intervals. | Empirical interval coverage $\ge \mathbf{95\%}$; debiased MAE strictly lower than raw estimate. | Interval coverage = **99.83%–100.00%**; debiasing reduced MAE by **25.6%–76.7%** across all skews. | **ACCEPTED (PASS)** |
| **N4** | **Theoretical Framework** | Theorem 1 proof of zero-underestimate write-back invariant; AMQ break-even analysis. | Mathematical induction proof; simulation across $10^6$ updates confirms zero underestimates. | **0 underestimates**, **0 false negatives** across all trials; counterexample & fix verified. | **ACCEPTED (PASS)** |

---

## 🏗️ Architectural Overview

```
                            STREAM ITEM x
                                 │
                        xxh3_128(x) -> 128 bits
            ┌───────────────────┴───────────────────┐
       Bits [0:63]                              Bits [64:127]
   (Kirsch-Mitzenmacher)                     (HyperLogLog Extraction)
    idx_j = (h1 + j*h2) mod w                  idx_hll = bits[64 : 64+p] mod m
         │                                     rank rho = clz(bits[64+p : 127]) + 1
         │                                           │
         ▼                                           ▼
 ┌─────────────────────────────────┐        ┌─────────────────────────────────┐
 │ Counter Matrix T (d x w)        │        │ Packed HLL Registers M (m x 6b) │
 │ - 8-bit saturating counters     │        │ - 6-bit packed bit-array        │
 │ - Conservative Update (CU)      │        │ - Small-range Linear Counting   │
 │ - Membership: all d > 0 (Var A) │        │ - Coupled (m=w) or Decoupled    │
 └─────────────────────────────────┘        └─────────────────────────────────┘
         │
         ▼ (if count >= tau)
 ┌─────────────────────────────────┐
 │ Associative Stash E (K entries) │
 │ - Exact post-promotion count    │
 │ - Baseline at promotion tracked │
 │ - Max write-back on eviction    │
 └─────────────────────────────────┘
         │
         ▼ (Optional Wire Serialization)
 ┌─────────────────────────────────┐
 │ LightRanger Compression Engine  │
 │ - Equal Element Grouping (Lg=8) │
 │ - Base-Bit Reduction (BBR)      │
 │ - Dynamic bit-packing (2-4 bits)│
 └─────────────────────────────────┘
```

---

## 🚀 Reproduction & Usage Guide

### Prerequisites
- Python 3.11+
- MinGW GCC (`g++`) with C++17 support

### 1-Command Automated Reproduction
```bash
# Clone the repository
git clone https://github.com/Shobhit-20-04/randomized-approx-query-processing.git
cd randomized-approx-query-processing

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run complete reproduction pipeline (compiles C++, runs Exp 1-8, generates figures)
python reproduce.py
```

### Launch Interactive Analytics Dashboard
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser to inspect live streaming queries, parameter tuning, and comparative benchmarks.

---

## 📂 Repository File Tree

```
randomized-approx-query-processing/
├── README.md                           # Setup guide, architecture, benchmark summaries
├── report.md                           # Full paper-ready report with literature table and proofs
├── reproduce.py                        # Master 1-command reproduction script
├── pyproject.toml                      # Dependencies, build metadata
├── app.py                              # Interactive Streamlit analytics dashboard
├── adalog/                             # Python reference implementation of AdaLog-Sketch
│   ├── sketch.py                       # Unified AdaLogSketch class with toggleable ablations
│   ├── hash_utils.py                   # 128-bit hash derivation and Kirsch-Mitzenmacher double hashing
│   ├── stash.py                        # Associative elephant stash with baseline tracking and max() write-back
│   ├── hll_packed.py                   # 6-bit packed HyperLogLog registers with Linear Counting
│   └── compression.py                  # LightRanger wire-format compression engine (EEG + BBR)
├── core/                               # Compiled C++ high-performance engine
│   ├── adalog_core.cpp                 # C++ implementation of AdaLog, CMS, Bloom, HLL, Disjoint
│   ├── adalog_core.dll                 # Compiled native Windows DLL (-O3, static runtime)
│   ├── hash_xxh3.h                     # Inlined MurmurHash3_x64_128 hash core
│   └── bindings.py                     # Python ctypes wrappers for headline latency benchmarking
├── baselines/                          # Faithful implementations of classical algorithms
│   ├── bloom_filter.py                 # Standard Bloom Filter with optimal k
│   ├── counting_bloom_filter.py        # Counting Bloom Filter with deletion
│   ├── cuckoo_filter.py                # Cuckoo Filter with partial-key cuckoo hashing
│   ├── xor_filter.py                   # Xor Filter (3-way peeling)
│   ├── count_min_sketch.py             # Count-Min Sketch (8b, 16b, 32b) with Conservative Update
│   ├── count_sketch.py                 # Count-Sketch with random sign projections
│   ├── hyperloglog.py                  # Standard HLL with 6-bit packed registers
│   ├── augmented_sketch.py             # Augmented Sketch (Roy et al., SIGMOD 2016)
│   ├── elastic_sketch.py               # Elastic Sketch (Yang et al., ACM SIGCOMM 2018)
│   └── disjoint_stack.py               # Combined Disjoint Baseline Stack
├── planner/                            # Novel Contribution N1: AdaLog-Planner
│   ├── planner.py                      # Multi-objective constrained optimization engine
│   └── error_models.py                 # Analytical models for CMS-CU noise, FPR, and HLL RSE
├── controller/                         # Novel Contribution N2: Online Adaptive Controller
│   ├── adaptive_controller.py          # Closed-loop epoch controller for dynamic tau
│   └── telemetry_signals.py            # Internal state extractors (saturation, density, skew)
├── certificates/                       # Novel Contribution N3: Cross-Task Calibration
│   ├── debiaser.py                     # Count-Mean-Min residual frequency debiaser
│   ├── intervals.py                    # Certified [lo, hi] frequency intervals
│   └── live_certificates.py           # Real-time membership FPR and cardinality confidence intervals
├── theory/                             # Novel Contribution N4: Mathematical Proofs
│   ├── write_back_proof.md             # Formal induction proof of Theorem 1 and counterexample
│   ├── membership_analysis.md          # Variant A shared counters vs dedicated Bloom filter break-even
│   └── simulate_proofs.py              # Adversarial stress test simulator ($10^6$ updates)
├── experiments/                        # Comprehensive benchmark test suite
│   ├── datasets.py                     # Synthetic Zipfian generator and drifting stream generator
│   ├── exp1_memory_sweep.py            # Memory sweep Pareto curves (8 KB to 512 KB)
│   ├── exp2_skew_sweep.py              # Zipfian alpha sensitivity sweep (1.05 to 1.50)
│   ├── exp3_latency_benchmark.py       # Compiled C++ latency & throughput benchmark (ns/op, Mops/s)
│   ├── exp4_ablations.py               # Systematic ablation grid
│   ├── exp5_planner_eval.py            # Acceptance test evaluation for N1 (Planner)
│   ├── exp6_adaptive_eval.py           # Acceptance test evaluation for N2 (Adaptive Controller)
│   ├── exp7_certificates_eval.py       # Acceptance test evaluation for N3 (Certificates)
│   ├── exp8_compression.py            # LightRanger wire-format compression benchmark
│   └── plot_results.py                 # Publication-quality vector figure generator
└── results/                            # Raw data and generated figures
    ├── raw/                            # Machine-readable JSON results from all experiments
    └── figures/                        # Generated publication plots (PDF & PNG)
```

---

## 📜 Citation

```bibtex
@misc{agrawal2026adalog,
  title={Beyond Bloom Filter, Count-Min Sketch, and HyperLogLog: A Unified Randomized Algorithm for Approximate Query Processing over Skewed Data Streams},
  author={Agrawal, Shobhit and Pawar, Mayuri Rajendra},
  year={2026},
  publisher={GitHub},
  howpublished={\url{https://github.com/Shobhit-20-04/randomized-approx-query-processing}}
}
```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
