# Beyond Bloom Filter, Count-Min Sketch, and HyperLogLog: AdaLog-Sketch

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![C++ Core: 21.97 Mops/s](https://img.shields.io/badge/C++%20Native-21.97%20Mops%2Fs-success.svg)](src/cpp/)
[![Tests: 42 Passed](https://img.shields.io/badge/Tests-42%20Passed-brightgreen.svg)](tests/)
[![Audit: 14/14 Invariants](https://img.shields.io/badge/Audit-14%2F14%20Invariants-brightgreen.svg)](audit/)

A reproducible research codebase and benchmark case study evaluating classical probabilistic data structures (**Bloom Filter**, **Count-Min Sketch**, **HyperLogLog**, **Elastic Sketch**, **Augmented Sketch**) alongside **AdaLog-Sketch**—a unified randomized algorithm that executes Approximate Membership Queries (AMQ), Point Frequency Estimation, Distinct Cardinality Counting, and Heavy Hitters from a **single shared memory block driven by a single 128-bit hash computation per stream item**.

**Authors:** Shobhit Agrawal & Mayuri Rajendra Pawar (Vellore Institute of Technology, Vellore)  
**Faculty Guide:** Dr. Parveen Sultana H (Associate Dean in-charge, School of Computer Science and Engineering - SCOPE, VIT Vellore)  
**Repository:** [https://github.com/Shobhit-20-04/randomized-approx-query-processing](https://github.com/Shobhit-20-04/randomized-approx-query-processing)

---

> [!NOTE]
> **Research Paper & Academic Manuscript Notice**  
> In accordance with repository release standards, complete LaTeX sources (`main.tex`, `references.bib`, vector figures) and the camera-ready research paper PDF (`AdaLog_Sketch_Final_Research_Paper.pdf`) are maintained locally in `paper_local/` (and archived) and strictly decoupled from the public code release to facilitate independent peer review.

---

## ⚡ Executive Performance Matrix

All metrics are grounded in reproducible benchmarks on 64-bit Windows / Linux (x86-64, compiled C++ with GCC/MinGW `-O3 -mavx2`):

| Streaming Data Structure | Unified Query Support | Ingestion Latency (Native C++) | Ingestion Throughput (Native C++) | Frequency MAE (32 KB Budget) | AMQ False Positive Rate | Zero Underestimate Guarantee |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **AdaLog-Sketch (Ours)** | **Membership + Frequency + Cardinality + Top-$k$** | **45.52 ns/op** | **21.97 Mops/s** | **0.40** | **47.16% (Var A) / 0.11% (256KB)** | **Strictly 0 Underestimates** ($K \ge K_{sat}^*$) |
| **Disjoint Stack (BF+CMS+HLL)** | Membership + Frequency + Cardinality | 50.09 ns/op | 19.96 Mops/s | 2.51 | 14.81% | Bounded by CMS |
| **Augmented Sketch** (SIGMOD 2016) | Frequency + Top-$k$ | ~48 ns/op | ~20.8 Mops/s | 1.87 | N/A | Bounded |
| **Elastic Sketch** (SIGCOMM 2018) | Frequency + Top-$k$ | ~48 ns/op | ~20.8 Mops/s | 1.90 | N/A | Bounded |
| **Count-Min Sketch (CMS-CU)** | Frequency only | 35.04 ns/op | 28.55 Mops/s | 2.85 | N/A | Strictly $\hat{f} \ge f$ |
| **Standard Bloom Filter** | Membership only | 12.73 ns/op | 79.04 Mops/s | N/A | Target FPR | Zero False Negatives |
| **HyperLogLog (HLL)** | Cardinality only | 6.57 ns/op | 153.01 Mops/s | N/A | N/A | $\text{RSE} \approx 1.04/\sqrt{m}$ |

*Note: Native compiled C++ achieves 21.97 Mops/s; Python ctypes bindings operate at ~1.92 Mops/s due to cross-language FFI boundary overhead.*

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
 │ - Membership: all d > 0 (Var A) │        │ - Decoupled (768 B register set)│
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
- C++17 compatible compiler (GCC, Clang, or MSVC)
- CMake 3.16+ (optional, build scripts provided)

### 1-Command Automated Reproduction
```bash
# Clone the repository
git clone https://github.com/Shobhit-20-04/randomized-approx-query-processing.git
cd randomized-approx-query-processing

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux / macOS
.\.venv\Scripts\activate        # On Windows

# Install dependencies and package
pip install -r requirements.txt
pip install -e .

# Run complete test suite (Unit tests + Invariant audit)
python scripts/test/run_tests.py

# Build and run native C++ performance engine
bash scripts/build/build_core.sh   # On Linux
scripts\build\build_core.bat       # On Windows
./core/bench_core                 # On Linux (./core/bench_core.exe on Windows)
```

### Launch Interactive Analytics Dashboard
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser to inspect live streaming queries, parameter tuning, and comparative benchmarks.

---

## 📂 Standardized Repository Hierarchy

```
randomized-approx-query-processing/
├── CMakeLists.txt                      # C++17 build definition (libadalog_core, bench_core)
├── README.md                           # Release documentation, architecture, benchmark summaries
├── pyproject.toml                      # Standard packaging metadata, pytest configuration
├── requirements.txt                    # Python runtime and scientific dependencies
├── app.py                              # Interactive Streamlit analytics dashboard
├── reproduce.py                        # Top-level reproduction driver
│
├── src/                                # Canonical source code
│   ├── cpp/                            # C++17 high-performance engine
│   │   ├── core/                       # Core algorithms (adalog_core.cpp, bench_core.cpp)
│   │   ├── hashing/                    # Hash implementations (hash_murmur3.h)
│   │   └── bindings/                   # Cross-platform ctypes bindings with auto-loader
│   └── python/                         # Python reference implementation
│       └── adalog/                     # Modular AdaLog-Sketch library
│           ├── sketch.py               # Unified AdaLogSketch with modular components
│           ├── stash.py                # Associative elephant stash with max() write-back (24-byte layout, 64-bit exact counters)
│           ├── hash_utils.py           # Kirsch-Mitzenmacher 64-bit double-hashing
│           ├── hll_packed.py           # 6-bit packed HyperLogLog registers
│           └── compression.py          # LightRanger wire-format compression engine
│
├── benchmarks/                         # Benchmarking infrastructure
│   ├── baselines/                      # Implementations of classical sketches (BF, CMS, HLL, etc.)
│   └── scripts/                        # Experiment execution scripts (Exp 1 through 8)
│
├── tests/                              # Rigorous verification suite (42 automated tests + 14 audit tests)
│   ├── regression/                     # Invariant preservation and mathematical checks
│   └── differential/                   # C++ vs. Python cross-language differential tests (native parity)
│
├── datasets/                           # Stream trace loaders and synthetic generators
│   ├── raw/                            # Reference datasets (CAIDA, synthetic)
│   └── processed/                      # Pre-tokenized traces
│
├── results/                            # Experimental evaluation artifacts
│   ├── raw/                            # Untouched machine-readable JSON/CSV benchmark data
│   ├── processed/                      # Certified audit test matrix and aggregated metrics
│   └── figures/                        # Publication vector plots (PDF/PNG)
│
├── docs/                               # Comprehensive research and engineering documentation
│   ├── architecture/                   # High-level component designs and dataflow
│   ├── algorithms/                     # Step-by-step algorithmic specifications
│   ├── mathematical_analysis/          # Formal proofs and invariant bounds
│   ├── memory_accounting/              # Exact bit-level memory accounting breakdowns
│   ├── reproducibility/                # Audit reports (AdaLog_Final_Technical_Audit.md)
│   └── changelog/                      # Version history and audit issue resolutions
│
├── scripts/                            # Operational scripts
│   ├── build/                          # C++ build scripts (build_core.bat, build_core.sh)
│   ├── test/                           # Test runners (run_tests.py, validate_paper.py)
│   ├── benchmark/                      # Benchmark execution scripts
│   └── utilities/                      # Plotting and verification utilities
│
└── archive/                            # Archived legacy scripts, documentation, and history
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
