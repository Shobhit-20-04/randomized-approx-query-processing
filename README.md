# Randomized Data Structures for Approximate Query Processing

[![CI - Unit Tests & Quick Benchmark](https://github.com/Shobhit-20-04/randomized-approx-query-processing/actions/workflows/tests.yml/badge.svg)](https://github.com/Shobhit-20-04/randomized-approx-query-processing/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit App](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg)](http://localhost:8501)

A rigorous empirical performance comparison of **Bloom Filter**, **Count-Min Sketch**, and **HyperLogLog** against exact hash-table baselines (`set` and `dict`) across varying dataset sizes and data distributions.

**Author:** Shobhit Agrawal  
**Repository:** [https://github.com/Shobhit-20-04/randomized-approx-query-processing](https://github.com/Shobhit-20-04/randomized-approx-query-processing)

---

## ⚡ Executive Performance Summary

All metrics are derived from actual benchmark measurements on Windows 11 (Python 3.11.9):

| Algorithm | Query Type | Exact Baseline | Space Reduction | Accuracy / Error Metric | Mathematical Invariant Verified |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **Bloom Filter** | Set Membership (`contains`) | Python `set` | **17.7x** | Empirical FPR: **0.024** (Target: 0.01–0.05) | **0 False Negatives** (Strict zero guarantee) |
| **Count-Min Sketch** | Point Frequency (`query`) | Python `dict` | **82.4x** | MAE: **6.34** | **0 Underestimations**; **100%** within additive bound |
| **HyperLogLog** | Distinct Cardinality (`estimate`) | Python `set` | **54.2x** | Mean Relative Error: **1.35%** | Constant $2^p$ bytes; **81.3%** within $1 \times \text{RSE}$ |

---

## 🔬 Core Algorithms & Formulations

### 1. Bloom Filter (Bloom, 1970)
* **Goal:** Approximate set membership queries ("Is item $q$ in set $S$?").
* **Optimal Bit-Array Sizing ($m$):**
  $$m = \left\lceil -\frac{n \ln p}{(\ln 2)^2} \right\rceil$$
* **Optimal Hash Function Count ($k$):**
  $$k = \max\left(1, \left\lfloor \frac{m}{n} \ln 2 \right\rceil\right)$$
* **Kirsch-Mitzenmacher Double Hashing:**
  $$g_i(x) = (h_1(x) + i \cdot h_2(x)) \pmod m, \quad 0 \le i < k$$
* **Theoretical False Positive Probability:**
  $$p_{\text{theo}} \approx \left(1 - e^{-kn/m}\right)^k$$
* **Guaranteed Invariant:** Zero false negatives for inserted elements.

### 2. Count-Min Sketch (Cormode & Muthukrishnan, 2005)
* **Goal:** Point frequency estimation on continuous data streams.
* **Table Sizing:**
  * Width: $w = \lceil e / \epsilon \rceil$
  * Depth: $d = \lceil \ln(1 / \delta) \rceil$
* **Pairwise-Independent 2-Universal Hashing:**
  $$h_j(x) = ((a_j \cdot \text{hash}_{64}(x) + b_j) \bmod (2^{61}-1)) \bmod w$$
* **Query Estimate:**
  $$\hat{f}(x) = \min_{0 \le j < d} C[j, h_j(x)]$$
* **Theoretical Guarantee:**
  $$\hat{f}(x) \ge f(x) \quad \text{and} \quad \Pr[\hat{f}(x) \le f(x) + \epsilon \|a\|_1] \ge 1 - \delta$$
* **Guaranteed Invariant:** No underestimation ($\hat{f} \ge f$) under nonnegative updates.

### 3. HyperLogLog (Flajolet et al., 2007)
* **Goal:** Distinct-element cardinality estimation ($|\{x \in S\}|$).
* **Register Bank:** $m = 2^p$ registers ($p \in [4, 16]$).
* **Harmonic Mean Estimator:**
  $$E = \alpha_m \cdot m^2 \cdot \left(\sum_{j=0}^{m-1} 2^{-M[j]}\right)^{-1}$$
* **Linear Counting Small-Range Correction:** When $E \le 2.5m$ and $V = \sum \mathbb{I}(M[j] == 0) > 0$:
  $$E^* = m \ln(m / V)$$
* **Theoretical Relative Standard Error (RSE):**
  $$\text{RSE} \approx \frac{1.04}{\sqrt{m}}$$
* **Guaranteed Invariant:** Strict $O(2^p)$ constant byte memory regardless of stream length.

---

## 📊 Experimental Visualizations

All 11 publication figures are generated at **300 DPI PNG** and **Vector PDF** in `results/plots/`:

| Analysis Figure | Description |
| :--- | :--- |
| **Figure 1: Memory Footprint vs. Dataset Size** | Log-log memory scaling of BF, CMS, and HLL vs exact baselines |
| **Figure 2: Stream Ingestion Latency** | Processing duration across stream sizes |
| **Figure 3: Ingestion Throughput** | Ingestion speed (thousand operations per second) |
| **Figure 4: Query Latency Scaling** | Nanosecond-scale point query latency |
| **Figure 5: Bloom Filter Empirical vs Target FPR** | Parity line comparison of theoretical vs empirical false positives |
| **Figure 6: Count-Min Sketch MAE vs Epsilon** | Error scaling against error tolerance parameter $\epsilon$ |
| **Figure 7: CMS Error Across Stream Distributions** | Skew effects: Uniform vs. Zipfian heavy-tail noise |
| **Figure 8: HyperLogLog Relative Error vs Precision** | Empirical error convergence against the $1.04 / \sqrt{m}$ theoretical curve |
| **Figure 9: Accuracy vs. Memory Pareto Frontiers** | Multi-algorithm trade-off frontiers |
| **Figure 10: Uniform vs. Zipfian Performance** | Distribution sensitivity across all three algorithms |
| **Figure 11: Exact vs Approximate Memory Bar** | Direct orders-of-magnitude memory comparison at scale |

---

## 🚀 Quickstart & Setup

### 1. Installation
```powershell
# Clone repository
git clone https://github.com/Shobhit-20-04/randomized-approx-query-processing.git
cd randomized-approx-query-processing

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install pinned dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

### 2. Run Tests & Validation
```powershell
# Run the 23-test test suite
pytest -v tests/

# Verify mathematical guarantees against saved results
python scripts/verify_results.py
```

### 3. Run Benchmarks
```powershell
# Quick validation benchmark (fast parameter sweep)
python scripts/run_quick_benchmark.py

# Full benchmark (complete parameter sweep up to 1,000,000 items)
python scripts/run_full_benchmark.py
```

### 4. Launch Interactive Dashboard
```powershell
streamlit run app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your browser to inspect interactive tables, scaling curves, and the live testing sandbox.

---

## 🗂️ Project Structure

```text
randomized-approx-query-processing/
├── app.py                           # Interactive Streamlit analysis dashboard
├── requirements.txt                 # Constrained dependencies
├── pyproject.toml                   # Packaging & pytest configuration
├── CITATION.cff                     # Citation metadata
├── LICENSE                          # MIT License
│
├── configs/
│   ├── quick.yaml                   # Fast validation configuration
│   └── full.yaml                    # Full-scale experiment configuration
│
├── src/approx_query/
│   ├── bloom_filter.py              # Bloom Filter with double hashing
│   ├── count_min_sketch.py          # Count-Min Sketch with 2-universal hash family
│   ├── hyperloglog.py               # HyperLogLog with Linear Counting correction
│   ├── datasets.py                  # Synthetic stream generator (Uniform, Zipfian, etc.)
│   ├── metrics.py                   # High-precision timing & memory measurement
│   ├── benchmarking.py              # Trial runner & statistical CSV aggregator
│   ├── plotting.py                  # Publication-quality matplotlib generator (PNG/PDF)
│   └── reporting.py                 # Academic research report synthesizer
│
├── tests/
│   ├── test_bloom_filter.py         # Zero-FN & theoretical sizing unit tests
│   ├── test_count_min_sketch.py     # No-underestimation & additive bound tests
│   ├── test_hyperloglog.py          # Cardinality estimation & bias correction tests
│   ├── test_datasets.py             # Reproducibility & query disjointness tests
│   └── test_metrics.py              # Latency & memory sizing tests
│
├── scripts/
│   ├── run_quick_benchmark.py       # Executes quick benchmark suite
│   ├── run_full_benchmark.py        # Executes full-scale research benchmark
│   ├── generate_report.py           # Re-synthesizes plots and report
│   └── verify_results.py            # Automated mathematical invariant validator
│
├── results/
│   ├── raw/                         # Raw trial CSVs (BF, CMS, HLL)
│   ├── aggregated/                  # Statistical summary CSVs (mean, std, CI)
│   └── plots/                       # 11 generated figures (PNG + PDF)
│
├── reports/
│   └── research_report.md           # Synthesized academic report
│
└── .github/workflows/
    └── tests.yml                    # Multi-OS CI workflow (Ubuntu & Windows)
```

---

## 📝 Citation

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

## 📚 References

1. **Bloom, B. H.** (1970). Space/time trade-offs in hash coding with allowable errors. *Communications of the ACM*, 13(7), 422–426. [DOI: 10.1145/362686.362692](https://doi.org/10.1145/362686.362692)
2. **Cormode, G., & Muthukrishnan, S.** (2005). An improved data stream summary: the count-min sketch and its applications. *Journal of Algorithms*, 55(1), 58–75. [DOI: 10.1016/j.jalgor.2003.12.001](https://doi.org/10.1016/j.jalgor.2003.12.001)
3. **Flajolet, P., Fusy, É., Gandouet, O., & Meunier, F.** (2007). HyperLogLog: the analysis of a near-optimal cardinality estimation algorithm. *DMTCS Proceedings*, AH, 137–156.
4. **Kirsch, A., & Mitzenmacher, M.** (2006). Less hashing, same performance: Building a better Bloom filter. *European Symposium on Algorithms (ESA)*, 456–467. [DOI: 10.1007/11841036_42](https://doi.org/10.1007/11841036_42)
5. **Heule, S., Nunkesser, M., & Hall, A.** (2013). HyperLogLog in practice: Algorithmic engineering of a state of the art cardinality estimation algorithm. *EDBT*, 683–692. [DOI: 10.1145/2452376.2452456](https://doi.org/10.1145/2452376.2452456)
