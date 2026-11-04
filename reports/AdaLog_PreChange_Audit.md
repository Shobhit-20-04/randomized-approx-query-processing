# AdaLog-Sketch: Pre-Change Architectural & Codebase Audit Report

**Audit Date:** November 2026  
**Auditor:** Independent Senior Research Scientist & Algorithm Auditor  
**Scope:** Forensic baseline audit of the AdaLog-Sketch repository prior to technical overhaul.  
**Inspected Repository:** `D:\VIT\DSA Case Study\randomized-approx-query-processing`  

---

## 1. Executive Summary & Inventory

An exhaustive static and dynamic inspection was performed across the complete AdaLog-Sketch codebase:
- **C++ Engine:** `core/adalog_core.cpp` (495 lines), `core/hash_xxh3.h` (85 lines), `core/bench_core.cpp` (320 lines)
- **Python Architecture:** `adalog/sketch.py` (276 lines), `adalog/stash.py` (109 lines), `adalog/hll_packed.py` (184 lines), `adalog/hash_utils.py` (92 lines)
- **Baselines:** `baselines/disjoint_stack.py` (210 lines), `baselines/count_min_sketch.py` (145 lines), `baselines/bloom_filter.py` (115 lines), `baselines/hyperloglog.py` (130 lines)
- **Empirical Telemetry:** `results/raw/exp1_memory_sweep.json`, `results/raw/exp2_skew_sweep.json`, `results/raw/exp3_latency_benchmark.json`

---

## 2. Baseline Architecture & Critical Flaws Identified

### 2.1 C++ Core Discrepancies (`core/adalog_core.cpp`)
1. **Misleading Hash Header:** `core/hash_xxh3.h` claimed to provide XXH3_128, but lines 15–75 implemented standard 32-bit/128-bit `MurmurHash3`. Meanwhile, Python used `xxhash.xxh3_128()`. Matrix indices diverged completely between C++ and Python.
2. **2-Choice Local Stash Eviction:** The paper asserted an associative Content-Addressable Memory (CAM) with global minimum-count eviction. In C++, lines 171–202 implemented a 2-choice hash table of 128 entries. If both hashed slots were occupied by higher-frequency keys, the incoming key was rejected and dropped, causing premature clipping at 255.
3. **Missing Native Top-k Extraction:** The paper claimed native Top-k heavy hitter queries. In the C++ class, no `top_k()` or `get_top_k()` method existed.
4. **HLL Buffer Inflation:** `core/adalog_core.cpp` originally set $hll\_m = w = 7,232$ (allocating 5,424 bytes for HLL instead of the modeled 768 bytes), violating the 32 KB target.

### 2.2 Python Reference Discrepancies (`adalog/stash.py`, `adalog/sketch.py`)
1. **Full-Stash Rejection:** In `adalog/stash.py` (lines 78–85), `evictable_candidates` filtered for items with count $< 255$. When all $K$ stash slots reached $\ge 255$, `evictable_candidates` evaluated to empty, returning `None`. Any arriving heavy item was rejected and clamped at 255 in the matrix.
2. **Non-Preserving Write-Back:** `adalog/sketch.py` line 155 clamped evicted counts: `bounded_evict = min(self.max_val, evict_count)`. Any count $> 255$ written back into the 8-bit matrix was permanently truncated to 255.

### 2.3 Baseline Fairness Flaw (`baselines/disjoint_stack.py`)
- `baselines/disjoint_stack.py` allocated:
  $$\text{CMS: } 23,960\text{ B} + \text{BF: } 5,990\text{ B} + \text{HLL: } 768\text{ B} + \text{Stash: } 3,072\text{ B} = \mathbf{33,790\text{ bytes}}$$
- This constituted a **+1,022-byte (+3.1%) budget overrun** above 32,768 bytes, skewing the reported comparative memory efficiency.

---

## 3. Mathematical Claim Invalidity (Theorem 2)
- Theorem 2 asserted: $\forall x, \hat{f}_{raw}(x) \ge f(x)$ unconditionally if $K \ge K_{sat} + \text{margin}$.
- **Fatal Counterexample:** When true heavy keys exceed stash capacity ($K_{sat} > K$), or collision noise admits false elephants that saturate at $\ge 255$, genuine heavy keys are rejected from the stash and capped at 255 in the matrix. Updates $> 255$ are lost permanently. In Test T05, 9 out of 25 heavy keys were underestimated by up to 36.25% ($\hat{f} = 255$ vs $f = 400$).
