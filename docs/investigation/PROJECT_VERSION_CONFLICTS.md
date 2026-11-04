# AdaLog-Sketch: Project Version Conflicts & Authoritative Truth Mapping

**Investigation Date:** November 2026  
**Status:** Read-Only Forensic Architecture Analysis  
**Repository:** `D:\VIT\DSA Case Study\randomized-approx-query-processing`  

---

## 1. Authoritative Component Matrix

The table below resolves all version discrepancies across the project. It explicitly distinguishes between historical drafts, superseded implementations, and the current authoritative source of truth.

| Component | Available Versions in Workspace | Current Authoritative Version | Verified? | Forensic Reason & Action |
| :--- | :--- | :--- | :---: | :--- |
| **C++ Core Engine** | 1. Pre-Path C: Fixed $K=128$, $hll\_m=w=7,232$ (5,424 B memory bug), missing `top_k()`.<br>2. Current: Dynamic stash capacity, native `get_top_k()`, decoupled HLL ($m=1024$, 768 B), 2-choice fast path. | `core/adalog_core.cpp` (Commit `fca9a1c`) | **YES** | Sizing bug fixed; native top-$k$ min-heap implemented; verified at 21.97 Mops/s via `core/bench_core.exe`. |
| **Python Implementation** | 1. `adalog/sketch.py` + `adalog/stash.py` (Core modules).<br>2. `src/approx_query/adalog_sketch.py` (Legacy import wrapper). | `adalog/sketch.py` and `adalog/stash.py` | **YES** | Authoritative reference used by all benchmarks and pytest suite (`tests/test_adalog_sketch.py`). `src/` wrapper is a legacy packaging shim. |
| **Hashing Engine** | 1. C++ `core/hash_xxh3.h`: Implements MurmurHash3_128.<br>2. Python `adalog/hash_utils.py`: Uses `xxhash.xxh3_128` (default) + `murmur3_hash128` (parity). | C++ uses `murmur3_128`; Python uses `xxh3_128` (default) & `murmur3_128` (audit). | **YES** | Historical misnaming: `core/hash_xxh3.h` contains MurmurHash3. Divergence verified in Test T10. Python now has exact Murmur3 parity function. |
| **Elephant Stash** | 1. C++: 2-choice hash table (128 slots) with local eviction ($slot_1$ vs $slot_2$).<br>2. Python: Fully associative dictionary with candidate filter ($c < 255$). | Python for theoretical modeling; C++ for throughput benchmarks. | **YES** | Both correctly protect saturated keys from demotion into 8-bit counters, but both reject candidates when all slots reach $\ge 255$ (failure boundary). |
| **HyperLogLog (HLL)** | 1. Coupled HLL ($m = w = 6,251$ or $7,232$): Distorts width, over-allocates up to 5,424 B.<br>2. Decoupled HLL ($m = 1024$, 768 B packed): Fixed constant size. | Decoupled HLL ($m = 1024$, 768 B packed 6-bit registers) | **YES** | 100-trial Monte Carlo validation (`cardinality_100trials.json`) confirms empirical RSE = 0.0239 (2.39%). |
| **Membership Query (AMQ)** | 1. Static threshold ($T > 0$ or 1-bit presence plane).<br>2. Dynamic threshold $\theta(N) = \min(254, \lfloor\ln(N/w + 1) + 1\rfloor)$. | Dynamic threshold in C++ (`core/adalog_core.cpp:310`) and Python (`adalog/sketch.py:165`). | **YES** | Guarantees zero false negatives ($FN = 0$). Empirical FPR is 73.25% at 32 KB and 100% at 8 KB. Correctly qualified as a soft pre-filter. |
| **Top-$k$ Extraction** | 1. Python `stash.top_k()` (Dictionary sort).<br>2. C++ historical: Missing.<br>3. C++ current: `get_top_k` min-heap. | `core/adalog_core.cpp` (`get_top_k`) and `adalog/stash.py` (`top_k`) | **YES** | Operates over resident stash ($K=128$). Must be documented as resident-only top-$k$, not full-stream universal recovery. |
| **Benchmark Pipeline** | 1. Python sweep scripts (`experiments/exp1_memory_sweep.py`, etc.).<br>2. Standalone audit suite (`audit/run_audit_tests.py`).<br>3. Standalone C++ binary (`core/bench_core.exe`). | All three form a coherent pipeline. | **YES** | `audit/run_audit_tests.py` verifies invariants; `bench_core.exe` measures throughput; `experiments/` generates paper figures. |
| **Raw Experimental Data** | 1. Original assignment CSVs (`results/raw/bloom_filter_raw.csv`, etc.).<br>2. AdaLog JSON logs (`results/raw/exp*.json`). | `results/raw/exp1` through `exp9` (Untouched) | **YES** | All 14 raw benchmark outputs in `results/raw/` are genuine, preserved, and match paper tables. |
| **Mathematical Claims** | 1. Unconditional Theorem 2 ($\hat{f} \ge f$ always).<br>2. Conditional Theorem 2 ($K \ge K_{sat}^*$). | Conditional Theorem 2 ($K \ge K_{sat}^*$) in `reports/AdaLog_Theorem2_Correction.md` | **YES** | Unconditional claim is mathematically false under stash overflow (Test T05). Conditional formulation is rigorous and defensible. |
| **Research Paper Manuscript** | 1. `Downloads/AdaLog_Sketch (12).pdf` (Historical PDF).<br>2. `paper/main_original_backup.tex` (34 KB).<br>3. `paper/main_before_fixes.tex` (74 KB).<br>4. `AdaLog_Sketch_Final_Research_Paper.tex` (88.6 KB draft with TODOs).<br>5. `research_paper_final/main.tex` and `paper/main.tex` (812 lines, clean).<br>6. `research_paper_final/AdaLog_Sketch_Final_Research_Paper.pdf` (502 KB). | **Source:** `research_paper_final/main.tex`<br>**Compiled PDF:** `AdaLog_Sketch_Final_Research_Paper.pdf` | **YES** | All TODO comments removed; matches raw experimental results; passed `validate_paper.py`; 44 clean references. |

---

## 2. Detailed Conflict Analysis & Resolution

### Conflict 1: Hash Function Naming vs Implementation
- **Symptom:** Header `core/hash_xxh3.h` was expected to contain XXH3_128, but lines 15–75 actually implement `murmur3_128`. Python default `hash128` called `xxhash.xxh3_128()`.
- **Resolution:** Rather than destabilizing the high-performance C++ kernel (which runs at 21.97 Mops/s), we added an identical `murmur3_hash128` implementation into `adalog/hash_utils.py` for parity testing. The paper accurately discloses that C++ utilizes MurmurHash3 while Python reference benchmarks use XXH3.

### Conflict 2: Stash Eviction Architecture (CAM vs 2-Choice)
- **Symptom:** The paper described a fully associative Content-Addressable Memory (CAM) with global minimum-count eviction. The C++ kernel implemented a 2-choice hash table with local eviction between $slot_1$ and $slot_2$.
- **Resolution:** A hardware-level CAM in software would require $O(K)$ linear scans per update, which previously cratered throughput from 21 Mops/s down to 6.37 Mops/s. The 2-choice hash table is essential for maintaining constant-time ($O(1)$) cache-line updates. The paper text has been clarified to describe the C++ engine as a 2-choice bounded stash with local candidate eviction.

### Conflict 3: Memory Budget Sizing (32 KB vs 33.8 KB Baseline)
- **Symptom:** Historical Disjoint+Stash benchmarks allocated 33,790 bytes (+3.1% over budget) due to calculating stash memory at 16 B/entry instead of 24 B/entry.
- **Resolution:** In `baselines/disjoint_stack.py`, the strict baseline was calibrated to $w = 5,785$ (23,140 B CMS + 5,788 B BF + 3,072 B Stash + 768 B HLL = 32,765 B $\le 32,768$ B). Both historical (33.8 KB) and strict (32.0 KB) baseline numbers are transparently reported in Table IV of the paper.
