# AdaLog-Sketch: A Contiguous-Memory Approximate Query Processing Synopsis for Multi-Task Stream Analytics

[![CI - Unit Tests & Quick Benchmark](https://github.com/Shobhit-20-04/randomized-approx-query-processing/actions/workflows/ci.yml/badge.svg)](https://github.com/Shobhit-20-04/randomized-approx-query-processing/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11 | 3.12](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](pyproject.toml)
[![C++: 17](https://img.shields.io/badge/C%2B%2B-17-blue.svg)](CMakeLists.txt)

---

## 1. Executive Summary & Project Description

**AdaLog-Sketch** is a unified, contiguous-memory streaming data synopsis engineered for high-velocity approximate query processing (AQP). It simultaneously answers four fundamental streaming query primitives from a single shared state block:
1. **Approximate Membership Queries (AMQ):** Set membership testing with zero false negatives ($\mathrm{FN} = 0$) and bounded false positives.
2. **Point-Frequency Estimation:** Heavy-tailed frequency estimation with zero underestimation for raw queries ($\hat{f}(x) \ge f(x)$) when the stash is sized $K \ge K_{sat}^*$.
3. **Distinct-Cardinality Estimation:** Logarithmic unique-key cardinality estimation via packed 6-bit HyperLogLog registers.
4. **Heavy Hitter & Top-$k$ Identification:** Exact frequency extraction over resident elephants in $O(K \log k)$ time via a min-heap.

Conventionally, streaming systems deploy isolated synopses for each primitive (e.g., a Bloom filter, a Count-Min sketch, and a HyperLogLog register array). This disjoint design duplicates hash evaluations, scatters memory access across disconnected heap structures, and fragments processor cache hierarchies. AdaLog-Sketch eliminates disjoint allocations by coupling a single 128-bit hash pipeline with a contiguous memory layout.

---

## 2. Research Problem & Motivation

Modern network telemetry, financial anomaly monitoring, and distributed stream processors ingest tens of millions of events per second. Evaluating membership, frequency, and cardinality concurrently via independent structures imposes severe bottlenecks:
- **Redundant Hash Computation:** Independent synopses calculate separate hash functions ($k_{\text{BF}} + d_{\text{CMS}} + 1_{\text{HLL}} \approx 7 \dots 12$ hash evaluations per packet).
- **Cache-Line Thrashing:** Accessing disconnected heap blocks causes independent L1/L2/L3 cache misses per incoming item.
- **Rigid Memory Fragmentation:** Memory statically partitioned across disjoint synopses cannot adapt dynamically between cardinality tracking and frequency tracking.

AdaLog-Sketch solves this by unifying all query primitives into a single contiguous memory block driven by a single 128-bit MurmurHash3 digest.

---

## 3. System Architecture & Memory Layout

```
+---------------------------------------------------------------------------------------------------+
|                                  AdaLog-Sketch Contiguous Layout                                  |
+===================================================================================================+
|  Component 1: Counter Matrix (CMS-CU)    | Component 2: Elephant Stash   | Component 3: Packed HLL|
|  - d rows x w columns (8-bit saturating) | - K slots x 24 bytes/slot     | - m registers (6-bit)  |
|  - Kirsch-Mitzenmacher 64-bit indexing   | - 95-bit composite fingerprint| - Dense 6-bit packing  |
|  - Lossless monotonic write-back victim  | - 64-bit exact counters       | - Leading-zero rank    |
+------------------------------------------+-------------------------------+------------------------+
|                                      Single 128-Bit Digest                                        |
|  Lane 0: h1 (Primary 64-bit Hash)        | Lane 1: h2 (Secondary 64-bit Hash)                     |
|  -> CMS row indices: (h1_low + j*h1_high)| -> HLL: reg = h2 >> 54; rank = clz64(h2 << 10) + 1     |
|  -> Stash primary fingerprint: h1        | -> Stash tag: h2 & 0x7FFFFFFF (MSB = occupancy flag)   |
+---------------------------------------------------------------------------------------------------+
```

### 3.1 Logical & Physical Memory Breakdown (32 KB Budget)
For a standard $32\text{ KB} = 32,768\text{ byte}$ budget:
- **Packed HyperLogLog Array:** $m = 1024$ registers $\times 6\text{ bits} = 6,144\text{ bits} = \mathbf{768\text{ bytes}}$.
- **Elephant Stash:** $K = 128$ slots $\times 24\text{ bytes/slot} = \mathbf{3,072\text{ bytes}}$ ($48 \times 64$-byte cache lines).
- **Counter Matrix:** $32,768 - 768 - 3,072 = 28,928\text{ bytes}$. At depth $d = 4$ with 8-bit saturating counters ($C_{\max} = 255$), width is $w = 28,928 / 4 = \mathbf{7,232\text{ counters/row}}$.
- **Total Physical Footprint:** Exactly $32,768\text{ bytes}$ (strictly zero padding).

### 3.2 Exact 24-Byte StashItem Struct
In native compiled C++ (`src/cpp/core/adalog_core.cpp`), each stash slot is packed into an aligned 24-byte struct:
```cpp
struct StashItem {
    uint64_t key_hash;    // 8 bytes: primary 64-bit hash (Lane 0)
    uint32_t tag;         // 4 bytes: MSB (0x80000000U) is occupancy flag; lower 31 bits are tag (Lane 1)
    uint32_t base_count;  // 4 bytes: matrix baseline counter value at promotion
    uint64_t exact_count; // 8 bytes: 64-bit exact accumulator while resident in stash
};
static_assert(sizeof(StashItem) == 24, "StashItem must be exactly 24 bytes");
```

---

## 4. Algorithmic Pipeline: Sequence A Promotion Order

AdaLog-Sketch executes a single-pass update that shields the counter matrix from heavy-hitter pollution:

```
Algorithm 1: AdaLog-Sketch Update Pipeline (Sequence A)
Input: Key x, increment count c (default c = 1)
  1. (h1, h2) <- MurmurHash3_128(x)
  2. Update HLL: reg_idx <- h2 >> 54; rank <- clz64(h2 << 10) + 1; M[reg_idx] <- max(M[reg_idx], rank)
  3. Stash Fast Path:
       If (h1, tag) in Stash:
           Stash[(h1, tag)].exact_count += c
           RETURN
  4. Compute Row Indices via Kirsch-Mitzenmacher 64-bit arithmetic:
       For j = 0 to d-1: idx_j <- (h1_low + j * h1_high) mod w
       v_min <- min_j T[j, idx_j]
  5. Sequence A Stash Admission Check:
       If v_min + c >= tau:
           If Stash has space (|E| < K):
               Insert (h1, tag, base=v_min, exact=c) into Stash
               RETURN  <-- Bypasses matrix update!
           If Stash is full:
               Find evictable victim e with min total count (e.total < C_max)
               If v_min + c > e.total:
                   Write-back e to matrix: For j = 0 to d-1: T[j, idx_j(e)] <- max(T[j, idx_j(e)], e.total)
                   Replace e with candidate (h1, tag, base=v_min, exact=c) in Stash
                   RETURN  <-- Bypasses matrix update!
  6. Matrix Conservative Update (for items < tau or rejected from saturated stash):
       v_target <- min(C_max, v_min + c)
       For j = 0 to d-1: T[j, idx_j] <- max(T[j, idx_j], v_target)
```

### Why Sequence A Preserves Correctness
- **Matrix Noise Isolation:** When an item qualifies as an elephant ($v_{\min} + c \ge \tau$), writing to the matrix is bypassed. The heavy item's high volume is stored exclusively in the stash, preventing other colliding keys from absorbing massive noise.
- **Zero Underestimation (Theorem 2):** Resident elephants return $\hat{f}(x) = c_{\text{base}} + c_{\text{exact}} \ge f(x)$. If an elephant is later evicted, its full total count is written back to the matrix with $\max$, ensuring no count is ever lost.
- **Zero False Negatives (AMQ):** If an item is in the stash, membership returns `True`. If evicted, write-back set all $d$ cells to $\ge \tau \ge 1 > 0$. If never promoted, the matrix update set all $d$ cells to $\ge 1 > 0$. In all cases, $\forall x \in S: \mathrm{contains}(x) \equiv \text{True}$.

---

## 5. Mathematical & Theoretical Guarantees

### 5.1 95-Bit Composite Fingerprint & Collision Bounds
The stash combines primary 64-bit hash $h_1$ (Lane 0) and secondary 31-bit tag $tag = h_2 \ \& \ \text{0x7FFFFFFF}$ (Lane 1, bit 31 stores occupancy) to form a **95-bit composite fingerprint**.
- Under the standard Simple Uniform Hashing Assumption (SUHA) / random oracle model:
  $$\mathbb{P}(\text{Single-Key Collision}) = \frac{1}{2^{95}} \approx 2.52 \times 10^{-29}$$
- Union bound over $N = 10^6$ stream arrivals across $K = 128$ resident stash slots:
  $$\mathbb{P}(\text{False Match}) \le \frac{K \cdot N}{2^{95}} \approx 3.23 \times 10^{-21}$$
- Even under a strictly conservative 64-bit bound (ignoring Lane 1 entirely):
  $$\mathbb{P}_{64}(\text{False Match}) \le \frac{K \cdot N}{2^{64}} \approx 6.94 \times 10^{-12} \ll 10^{-11}$$

### 5.2 Stash Sizing via Bennett Concentration Bound
To guarantee Theorem 2 zero underestimation, the stash capacity $K$ must bound the number of saturated keys $K \ge K_{sat}^*$. Under Zipfian skew $\alpha = 1.25$, expected saturation is $\mathbb{E}[K_{sat}] \approx 88$. Applying the Chernoff-Bennett concentration bound with confidence $1 - \delta = 0.999$ ($\delta = 10^{-3}$):
$$t(\delta) \le \sqrt{2 \mathbb{E}[K_{sat}] \ln(1/\delta)} + \frac{1}{3} \ln(1/\delta) = \sqrt{2 \cdot 88 \cdot 6.9078} + \frac{1}{3}(6.9078) \approx 34.87 + 2.30 = 37.17$$
$$K_{\text{plan}} = \lceil 88 + 37.17 \rceil = \mathbf{126} \le \mathbf{128}$$
Thus, $K = 128$ guarantees zero underestimation with $> 99.9\%$ mathematical confidence.

### 5.3 Asymptotic Time & Space Complexity

| Operation | Worst-Case Time | Expected Time | Auxiliary Space |
|:---|:---|:---|:---|
| **Stream Ingestion (`update`)** | $O(d + K)$ | $O(d)$ | $O(1)$ |
| **Membership Query (`contains`)** | $O(K + d)$ | $O(1)$ | $O(1)$ |
| **Point Query (`estimate`)** | $O(K + d)$ | $O(d)$ | $O(1)$ |
| **Top-$k$ Extraction (`get_top_k`)** | $O(K \log k)$ | $O(K \log k)$ | $O(k)$ min-heap |
| **Cardinality (`cardinality`)** | $O(m)$ | $O(m)$ | $O(1)$ |

---

## 6. Repository Architecture

```text
AdaLog-Sketch/
├── README.md                          # Master documentation (this file)
├── LICENSE                            # MIT License
├── CITATION.cff                       # Citation metadata
├── pyproject.toml                     # Python packaging configuration
├── CMakeLists.txt                     # Native C++ build configuration
│
├── src/                               # Authoritative Source Code
│   ├── cpp/
│   │   ├── core/                      # adalog_core.cpp, bench_core.cpp
│   │   ├── include/                   # adalog_core.h C-API header
│   │   └── bindings/                  # Python ctypes binding layer
│   └── python/
│       └── adalog/                    # Canonical Python package
│
├── tests/                             # Comprehensive Test Suite (46 Tests)
│   ├── cpp/                           # Native C++ unit tests (test_adalog_core.cpp)
│   ├── python/                        # Component-level Python unit tests
│   ├── differential/                  # C++ vs Python bit-identical verification
│   ├── regression/                    # Theorem 2 and invariant regression tests
│   └── adversarial/                   # Pathological collisions and extreme skew
│
├── benchmarks/                        # Empirical Benchmarks & Baselines
│   ├── baselines/                     # Fair budget-matched implementations (BF, CMS, HLL, Elastic)
│   ├── scripts/                       # Experiment scripts (exp1 to exp9)
│   └── configurations/                # Sweep parameter definitions
│
├── datasets/                          # Dataset Provenance & Generation
│   ├── synthetic/                     # Synthetic Zipfian trace generator
│   └── README.md                      # Provenance documentation (CAIDA & Gutenberg)
│
├── experiments/                       # Experiment Execution & Artifacts
│   ├── runners/                       # Batch execution wrappers
│   └── results/                       # Raw JSON / aggregated CSV datasets
│       ├── raw/
│       └── processed/
│
├── analysis/                          # Mathematical & Statistical Modeling
│   ├── mathematical/                  # AdaLog-Planner and error models
│   ├── statistical/                   # Confidence intervals & certificates
│   └── visualizations/                # Matplotlib publication plotting scripts
│
├── figures/                           # Publication Vector PDFs and PNGs
├── docs/                              # Research Documentation
│   ├── architecture/                  # Layout and pipeline documentation
│   ├── algorithms/                    # Sequence A promotion & write-back
│   └── reproducibility/               # Step-by-step reproduction guide
│
├── paper/                             # IEEE Manuscript Source & Package
│   ├── manuscript/                    # main.tex (Strict 11-Page IEEE Conference format)
│   ├── bibliography/                  # references.bib, main.bbl
│   ├── figures/                       # Embedded vector PDFs
│   └── overleaf/                      # AdaLog_Sketch_Overleaf_Package.zip
│
└── scripts/                           # Build & Verification Scripts
    ├── build/                         # build_core.bat, build_core.sh
    └── validation/                    # verify_results.py
```

---

## 7. Installation & Quick Start

### 7.1 Prerequisites
- **C++ Compiler:** GCC $\ge 9.0$, Clang $\ge 10.0$, or MSVC $\ge 2019$ (C++17 support required).
- **Python:** Python $\ge 3.11$ (verified on 3.11 and 3.12).
- **CMake:** CMake $\ge 3.16$ (optional, direct batch/sh scripts provided).

### 7.2 Native C++ Library Build
```bash
# On Linux / macOS
chmod +x scripts/build/build_core.sh
./scripts/build/build_core.sh

# On Windows (Command Prompt / PowerShell)
cmd.exe /c "call scripts\build\build_core.bat"
```

### 7.3 Python Package Installation
```bash
# Install in editable development mode
pip install -e .
```

### 7.4 Python Quick Start Example
```python
from adalog.sketch import AdaLogSketch

# Initialize AdaLog-Sketch with a 32 KB budget (width=7232, depth=4, K=128, m=1024)
sketch = AdaLogSketch(width=7232, depth=4, counter_bits=8, stash_capacity=128, stash_tau=15, seed=42)

# Stream ingestion
stream = ["user_101", "user_204", "user_101", "user_305", "user_101"]
for item in stream:
    sketch.update(item)

# Query Primitives
print("AMQ Contains ('user_101'):", sketch.contains("user_101"))      # True
print("AMQ Contains ('user_999'):", sketch.contains("user_999"))      # False (or low FPR)
print("Frequency Estimate ('user_101'):", sketch.estimate("user_101")) # 3
print("Distinct Cardinality:", sketch.cardinality())                  # ~3.0
print("Top-1 Heavy Hitters:", sketch.top_k(1))                        # [('user_101', 3)]
```

### 7.5 Native C++ Direct Example
```cpp
#include "adalog_core.h"
#include <iostream>

int main() {
    // Create 32 KB synopsis
    AdaLogHandle sketch = adalog_create(7232, 4, 8, 128, 15, 1024, 42);

    adalog_update(sketch, "packet_flow_A", 13, 100);
    uint64_t freq = adalog_estimate(sketch, "packet_flow_A", 13);
    bool exists = adalog_contains(sketch, "packet_flow_A", 13);

    std::cout << "Frequency: " << freq << ", Exists: " << exists << std::endl;
    adalog_destroy(sketch);
    return 0;
}
```

---

## 8. Running Tests & Benchmarks

### 8.1 Execute Comprehensive Test Suite (46 Tests)
```bash
pytest -v tests/
```

### 8.2 Run Native C++ Tests
```bash
g++ -O3 -std=c++17 -Isrc/cpp/core tests/cpp/test_adalog_core.cpp -o tests/cpp/test_adalog_core.exe
./tests/cpp/test_adalog_core.exe
```

### 8.3 Verify Theoretical Invariants & Benchmark Integrity
```bash
python scripts/validation/verify_results.py
```

### 8.4 Run Full Memory Sweep Benchmark
```bash
python benchmarks/scripts/exp1_memory_sweep.py
```

---

## 9. Validated Experimental Results

### 9.1 Multi-Task Performance Across Memory Budgets ($N = 300{,}000, \alpha = 1.25$)

| Budget | Synopsis Architecture | Frequency MAE | Cardinality RSE | AMQ FPR | Top-100 Recall | Total Ingestion Speed |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **32 KB** | **AdaLog-Sketch (Unified)** | **0.61 $\pm$ 0.02** | **0.024** | **73.25%** | **1.00** | **21.97 Mops/s** (45.5 ns) |
| 32 KB | Disjoint+Stash (Fair Baseline) | 1.05 $\pm$ 0.03 | 0.024 | 36.12% | 0.88 | 19.84 Mops/s (50.4 ns) |
| 32 KB | Elastic Sketch (Yang et al.) | 11.85 $\pm$ 0.12 | --- | --- | 0.76 | 14.20 Mops/s (70.4 ns) |
| **128 KB** | **AdaLog-Sketch (Unified)** | **0.18 $\pm$ 0.01** | **0.024** | **3.86%** | **1.00** | **21.97 Mops/s** (45.5 ns) |
| 128 KB | Disjoint+Stash (Fair Baseline) | 0.29 $\pm$ 0.01 | 0.024 | 0.96% | 1.00 | 19.84 Mops/s (50.4 ns) |
| 128 KB | Elastic Sketch (Yang et al.) | 4.12 $\pm$ 0.08 | --- | --- | 0.94 | 14.20 Mops/s (70.4 ns) |

### 9.2 Headline Throughput & Latency (Compiled C++ Native Core)
- **Ingestion Throughput:** **21.97 Mops/s** ($45.52\text{ ns/op}$), achieving a **1.11x speedup** over Disjoint Core ($19.84\text{ Mops/s}$, $50.43\text{ ns/op}$).
- **Point Query Latency:** **14.0 ns/op** (`adalog_estimate`, raw 13.999 ns).
- **Membership Query Latency:** **13.7 ns/op** (`adalog_contains`, raw 13.713 ns).

---

## 10. Honest Research Limitations & Threats to Validity

1. **AMQ Coarse Filtering at Constrained Budgets:** Because AdaLog-Sketch does not allocate a dedicated bit-array for membership testing, AMQ checks whether $\min_j T[j, idx_j] > 0$. At tight budgets ($32\text{ KB}$), counter density causes a high false positive rate ($73.25\%$). As memory scales to $128\text{ KB}$, FPR drops rapidly to $3.86\%$. AdaLog-Sketch is optimized for environments where AMQ serves as a coarse filter or where zero marginal memory for membership is required.
2. **Infinite Stream Saturation ($N > 10^7$):** Narrow 8-bit saturating counters ($C_{\max} = 255$) require periodic sliding-window resets or decay operations when stream volume $N$ exceeds $10^7$ operations. Unbounded accuracy without windowing is not claimed.
3. **Top-$k$ Hash vs. Key Output:** The native C++ top-$k$ engine extracts 64-bit primary fingerprints to maintain zero dynamic heap allocations. Recovering original UTF-8 strings requires an application-level key registry or using the Python synopsis wrapper.

---

## 11. Citation & Authors

If you utilize AdaLog-Sketch in your research, please cite:

```bibtex
@inproceedings{agrawal2026adalog,
  title={{AdaLog-Sketch: A Contiguous-Memory Approximate Query Processing Synopsis for Multi-Task Stream Analytics}},
  author={Agrawal, Shobhit and Pawar, Mayuri Rajendra and Sultana H, Parveen},
  booktitle={Proceedings of the IEEE International Conference on Data Engineering / Networking (ICDE)},
  year={2026},
  organization={Vellore Institute of Technology}
}
```

### Authors
- **Shobhit Agrawal** — `shobhit.agrawal2026@vitstudent.ac.in`
- **Mayuri Rajendra Pawar** — `mayuri.rajendra2026@vitstudent.ac.in`
- **Parveen Sultana H** — `hparveensultana@vit.ac.in`  
*School of Computer Science and Engineering, Vellore Institute of Technology, Vellore, Tamil Nadu, India.*

---

## 12. License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
