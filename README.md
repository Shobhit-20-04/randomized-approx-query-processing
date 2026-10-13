# Randomized Data Structures for Approximate Query Processing

[![CI - Unit Tests & Quick Benchmark](https://github.com/Shobhit-20-04/randomized-approx-query-processing/actions/workflows/tests.yml/badge.svg)](https://github.com/Shobhit-20-04/randomized-approx-query-processing/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

An empirical M.Tech Computer Science & Engineering research study comparing **Bloom Filter**, **Count-Min Sketch**, and **HyperLogLog** against exact hash-table baselines (`set` and `dict`) across varying dataset sizes and data distributions.

---

## 1. Project Overview & Research Objectives

High-velocity streaming systems (such as network routers, real-time analytics pipelines, and distributed databases) often face strict constraints on memory capacity and processing latency. Approximate Query Processing (AQP) utilizes randomized, probabilistic data structures that trade bounded approximation errors for dramatic reductions in space complexity ($O(1)$ or $O(m)$ where $m \ll N$) and constant-time latency.

### Research Question
> *"To what extent can Bloom Filter, Count-Min Sketch, and HyperLogLog reduce memory consumption and processing overhead compared with their exact counterparts, while maintaining their respective accuracy guarantees across different dataset sizes and data distributions?"*

### Tested Research Hypotheses
* **H1 (Bloom Filter):** Bloom Filter reduces memory footprint compared with an exact hash set with zero false negatives and a controlled empirical false-positive rate bounded by $p$.
* **H2 (Count-Min Sketch):** Count-Min Sketch reduces space relative to an exact frequency map, guaranteeing no underestimation ($\hat{f} \ge f$) and additive error within $\epsilon N$ with probability $\ge 1 - \delta$.
* **H3 (HyperLogLog):** HyperLogLog estimates distinct cardinality in constant register space ($O(2^p)$ bytes) with relative standard error closely following $1.04 / \sqrt{m}$.
* **H4 (Distribution Impact):** Skewed (Zipfian) streams concentrate collision noise on low-frequency items in Count-Min Sketch, whereas Bloom Filter and HyperLogLog exhibit distribution-invariant accuracy.
* **H5 (Trade-off Diversity):** Each algorithm targets fundamentally distinct query semantics (membership, frequency, and cardinality) with unique memory, update-time, and latency trade-offs.

---

## 2. Algorithms and Mathematical Formulations

### A. Bloom Filter (Bloom, 1970)
* **Semantics:** Approximate set membership queries ("Is item $q$ in set $S$?").
* **Optimal Bit-Array Sizing ($m$):**
  $$m = \left\lceil -\frac{n \ln p}{(\ln 2)^2} \right\rceil$$
* **Optimal Hash Function Count ($k$):**
  $$k = \max\left(1, \left\lfloor \frac{m}{n} \ln 2 \right\rceil\right)$$
* **Double Hashing (Kirsch & Mitzenmacher, 2006):**
  $$g_i(x) = (h_1(x) + i \cdot h_2(x)) \pmod m, \quad 0 \le i < k$$
* **Theoretical False Positive Probability:**
  $$p_{\text{theo}} \approx \left(1 - e^{-kn/m}\right)^k$$
* **Exact Baseline:** Python built-in `set`.

### B. Count-Min Sketch (Cormode & Muthukrishnan, 2005)
* **Semantics:** Approximate point frequency queries ("How many times did item $q$ appear in stream?").
* **Table Sizing:**
  * Width: $w = \lceil e / \epsilon \rceil$
  * Depth: $d = \lceil \ln(1 / \delta) \rceil$
* **Pairwise-Independent Universal Hashing:**
  $$h_j(x) = ((a_j \cdot \text{hash}_{64}(x) + b_j) \bmod (2^{61}-1)) \bmod w$$
* **Query Estimate:**
  $$\hat{f}(x) = \min_{0 \le j < d} C[j, h_j(x)]$$
* **Theoretical Bound:**
  $$\hat{f}(x) \ge f(x) \quad \text{and} \quad \Pr[\hat{f}(x) \le f(x) + \epsilon \|a\|_1] \ge 1 - \delta$$
* **Exact Baseline:** Python `collections.Counter` / `dict`.

### C. HyperLogLog (Flajolet et al., 2007)
* **Semantics:** Distinct element cardinality estimation ($|\{x \in S\}|$).
* **Register Bank:** $m = 2^p$ registers for precision parameter $p \in [4, 16]$.
* **Raw Harmonic Estimator:**
  $$E = \alpha_m \cdot m^2 \cdot \left(\sum_{j=0}^{m-1} 2^{-M[j]}\right)^{-1}$$
* **Linear Counting Small-Range Correction:** When $E \le 2.5m$ and $V = \sum \mathbb{I}(M[j] == 0) > 0$:
  $$E^* = m \ln(m / V)$$
* **Theoretical Relative Standard Error (RSE):**
  $$\text{RSE} \approx \frac{1.04}{\sqrt{m}}$$
* **Exact Baseline:** Python `set` cardinality (`len(set(stream))`).

---

## 3. Project Directory Structure

```text
D:\MTech\randomized-approx-query-processing\
│   README.md                        # Master documentation and experimental findings
│   requirements.txt                 # Pinned Python package dependencies
│   pyproject.toml                   # Standard package and pytest configuration
│   .gitignore                       # Git exclusion patterns
│   LICENSE                          # MIT open-source license
│   CITATION.cff                     # Citation metadata
│   app.py                           # Interactive Streamlit dashboard
│
├── configs\
│   ├── quick.yaml                   # Fast validation configuration
│   └── full.yaml                    # Full-scale M.Tech experiment configuration
│
├── src\
│   └── approx_query\
│       ├── __init__.py              # Package entry point
│       ├── bloom_filter.py          # Bloom filter with Kirsch-Mitzenmacher hashing
│       ├── count_min_sketch.py      # Count-Min sketch with 2-universal hash family
│       ├── hyperloglog.py           # HyperLogLog with Linear Counting correction
│       ├── datasets.py              # Synthetic stream & query workload generators
│       ├── metrics.py               # Memory, latency, and statistical evaluation
│       ├── benchmarking.py          # Benchmark trial runner and CSV aggregator
│       ├── plotting.py              # Publication-quality matplotlib generator (PNG/PDF)
│       └── reporting.py             # Academic research report synthesizer
│
├── tests\
│   ├── conftest.py                  # Pytest test discovery path setup
│   ├── test_bloom_filter.py         # BF property-based and correctness tests
│   ├── test_count_min_sketch.py     # CMS no-underestimation and bound tests
│   ├── test_hyperloglog.py          # HLL cardinality and small-range bias tests
│   ├── test_datasets.py             # Reproducibility and disjointness tests
│   └── test_metrics.py              # Timer and memory sizing unit tests
│
├── scripts\
│   ├── run_quick_benchmark.py       # Executes quick benchmark trial suite
│   ├── run_full_benchmark.py        # Executes full-scale research benchmark
│   ├── generate_report.py           # Re-synthesizes plots and report from CSVs
│   └── verify_results.py            # Automated mathematical invariant validator
│
├── results\
│   ├── raw\                         # Individual trial CSV records
│   ├── aggregated\                  # Grouped statistical summary CSVs
│   └── plots\                       # 11 publication-quality plots (PNG + PDF)
│
├── reports\
│   └── research_report.md           # Formatted academic research report
│
└── .github\
    └── workflows\
        └── tests.yml                # Multi-OS CI workflow
```

---

## 4. Installation & Setup (Windows PowerShell)

```powershell
# 1. Clone repository
git clone https://github.com/Shobhit-20-04/randomized-approx-query-processing.git
cd D:\MTech\randomized-approx-query-processing

# 2. Create Python virtual environment
python -m venv .venv

# 3. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

---

## 5. Execution Commands

### Run Unit Tests
```powershell
pytest -v tests/
```

### Run Quick Validation Benchmark
```powershell
python scripts/run_quick_benchmark.py
```

### Run Full Research Benchmark
```powershell
python scripts/run_full_benchmark.py
```

### Verify Mathematical Guarantees
```powershell
python scripts/verify_results.py
```

### Launch Interactive Streamlit Dashboard
```powershell
streamlit run app.py
```

---

## 6. Measured Experimental Findings

Based on actual benchmark measurements on Windows 11 (Python 3.11.9):

| Algorithm | Baseline | Memory Reduction | Accuracy / Error Status | Key Invariant Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Bloom Filter** | Python `set` | **17.7x** | Target FPR: 1-5% $\to$ Empirical: 0.9-4.8% | **0 False Negatives** |
| **Count-Min Sketch** | Python `dict` | **82.4x** | Additive bound compliance: **100.0%** | **0 Underestimations** |
| **HyperLogLog** | Python `set` | **54.2x** | Mean Relative Error: **1.35%** | **81.3% within 1-SE** |

---

## 7. Generated Visualizations

All 11 required publication figures are saved in both high-resolution PNG (300 DPI) and vector PDF formats inside `results/plots/`:
1. `01_memory_vs_dataset_size`: Memory footprint scaling across dataset sizes.
2. `02_insertion_time_vs_dataset_size`: Stream ingestion time across algorithms.
3. `03_update_throughput_vs_dataset_size`: Ingestion throughput (thousand ops/sec).
4. `04_query_latency_vs_dataset_size`: Point lookup latency scaling.
5. `05_bloom_filter_empirical_vs_target_fpr`: Empirical vs. theoretical false-positive rates.
6. `06_count_min_sketch_mae_vs_epsilon`: CMS Mean Absolute Error vs. error parameter $\epsilon$.
7. `07_count_min_sketch_error_by_distribution`: CMS estimation error across stream distributions.
8. `08_hyperloglog_error_vs_precision`: HyperLogLog relative cardinality error vs. precision $p$.
9. `09_accuracy_vs_memory_tradeoffs`: Memory-accuracy Pareto frontiers across structures.
10. `10_uniform_vs_zipfian_comparison`: Uniform vs. Zipfian skew effects.
11. `11_exact_vs_approx_memory_comparison`: Exact vs. approximate memory bar comparison at scale.

---

## 8. Limitations & Scope

1. **Deletion Support:** Standard Bloom Filter and Count-Min Sketch do not support element deletions without extensions (e.g. Counting Bloom Filters or Spectral Bloom Filters).
2. **Single-threaded Benchmarking:** Benchmarks evaluate single-threaded ingestion; concurrent multi-core locking overhead was not analyzed.
3. **Collision Noise on Heavy Tails:** Under high Zipfian skew, Count-Min Sketch error is concentrated on the long tail of low-frequency items.

---

## 9. Citation

If you use this research implementation or benchmark suite, please cite:

```bibtex
@misc{agrawal2026randomized,
  author = {Shobhit Agrawal},
  title = {Randomized Data Structures for Approximate Query Processing: A Comparative Experimental Study of Bloom Filter, Count-Min Sketch, and HyperLogLog},
  year = {2026},
  publisher = {GitHub},
  howpublished = {\url{https://github.com/Shobhit-20-04/randomized-approx-query-processing}}
}
```

---

## 10. References

1. Bloom, B. H. (1970). Space/time trade-offs in hash coding with allowable errors. *Communications of the ACM*, 13(7), 422–426. [DOI: 10.1145/362686.362692](https://doi.org/10.1145/362686.362692)
2. Cormode, G., & Muthukrishnan, S. (2005). An improved data stream summary: the count-min sketch and its applications. *Journal of Algorithms*, 55(1), 58–75. [DOI: 10.1016/j.jalgor.2003.12.001](https://doi.org/10.1016/j.jalgor.2003.12.001)
3. Flajolet, P., Fusy, É., Gandouet, O., & Meunier, F. (2007). HyperLogLog: the analysis of a near-optimal cardinality estimation algorithm. *DMTCS Proceedings*, AH, 137–156.
4. Kirsch, A., & Mitzenmacher, M. (2006). Less hashing, same performance: Building a better Bloom filter. *European Symposium on Algorithms (ESA)*, 456–467. [DOI: 10.1007/11841036_42](https://doi.org/10.1007/11841036_42)
5. Heule, S., Nunkesser, M., & Hall, A. (2013). HyperLogLog in practice: Algorithmic engineering of a state of the art cardinality estimation algorithm. *EDBT*, 683–692. [DOI: 10.1145/2452376.2452456](https://doi.org/10.1145/2452376.2452456)
