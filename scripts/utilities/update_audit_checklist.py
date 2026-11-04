"""Update docs/AUDIT.md with Step 1 and Step 2 explicit review checklist.
"""

import os

AUDIT_PATH = os.path.abspath("docs/AUDIT.md")
with open(AUDIT_PATH, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("\r\n", "\n")

checklist_section = r"""## Reviewer Action Checklist: Step 1 (Baseline Fairness) & Step 2 (Correctness)

### Step 1: Baseline Fairness

#### 1.1 16-Bit Disjoint Stack Overflow & Artificial Headline Gains
- **Status:** **CONFIRMED**
- **Evidence & File Location:**
  - Base counter configuration: [`baselines/disjoint_stack.py:38-44`](file:///D:/VIT/DSA%20Case%20Study/randomized-approx-query-processing/baselines/disjoint_stack.py#L38-L44) allocates `counter_bits=16`, giving `max_val = 65,535`.
  - Stream Ground Truth: Under Zipfian skew $\alpha = 1.25$ and $1.50$ ($N = 300\text{k}, |\mathcal{U}| = 100\text{k}$), the top keys reach $f = 68,593$ ($\alpha=1.25$) and $f = 114,894$ ($\alpha=1.50$).
  - Error Pathology: For the top key at $\alpha = 1.50$, the 16-bit counter saturates at 65,535, causing an automatic underestimation error of $114,894 - 65,535 = 49,359$.
  - Averaged across the top 100 head keys, Head MAE reaches:
    - $\alpha = 1.05$: Head MAE = 0.03 (no overflow, top count = 32,220)
    - $\alpha = 1.15$: Head MAE = 0.02 (no overflow, top count = 49,612)
    - $\alpha = 1.25$: Head MAE = 31.35 (overflow starts, top count = 68,593)
    - $\alpha = 1.35$: Head MAE = 225.17 (severe overflow, top count = 87,874)
    - $\alpha = 1.50$: Head MAE = 496.14 (catastrophic overflow, top count = 114,894)
- **Reviewer Finding Verified:** The apparent $13.3\times$ and $267.9\times$ gains and the claimed "64.1% memory saving" were largely artifacts of 16-bit counter truncation on the disjoint baseline.
- **Action Taken:**
  - `Disjoint+Stash` (`DisjointStashStack` in `baselines/disjoint_stack.py`) is now established as the fair, primary baseline across all tables (Tables III, IV, V).
  - The 16-bit disjoint baseline is retained strictly as a labeled counter-overflow illustration.

#### 1.2 Disjoint+Stash as Primary Baseline & Equal-Accuracy Search
- **Status:** **CONFIRMED & IMPLEMENTED**
- **Evidence & File Location:**
  - Automated Binary Search: [`scripts/search_equal_accuracy.py`](file:///D:/VIT/DSA%20Case%20Study/randomized-approx-query-processing/scripts/search_equal_accuracy.py) and [`results/raw/equal_accuracy_search.json`](file:///D:/VIT/DSA%20Case%20Study/randomized-approx-query-processing/results/raw/equal_accuracy_search.json).
  - Budget search results for $\mathrm{MAE} \le 0.40$ ($\alpha=1.25, N=300\text{k}$):
    - **AdaLog-Sketch (Unified):** **37.8 KB** (Baseline)
    - **Disjoint + Stash ($K=128$):** **45.2 KB** (**16.4% memory reduction**)
    - **Disjoint Stack (16-bit CU):** 105.2 KB (64.1% reduction, labeled as overflow artifact)
    - **Disjoint Stack (32-bit Standard CMS):** $> 256.0$ KB ($> 85.2\%$ memory reduction)
    - **Elastic Sketch:** 80.5 KB (53.0% memory reduction)
    - **Augmented Sketch:** 79.9 KB (52.7% memory reduction)
- **Action Taken:**
  - Recomputed Table IV (`tab:eq`) in `paper/main.tex` and updated all text claims to report the honest 16.4% reduction against `Disjoint+Stash`.

#### 1.3 Reconcile AdaLog at 32 KB, $\alpha=1.25$ (Table V vs. Table III)
- **Status:** **CONFIRMED & RESOLVED**
- **Evidence & File Location:**
  - Discrepancy Cause: [`scripts/run_all.py:285`](file:///D:/VIT/DSA%20Case%20Study/randomized-approx-query-processing/scripts/run_all.py#L285) hardcoded $w = 6682$ for Exp 2 (yielding $\mathrm{MAE} = 0.729 \pm 0.010$), whereas Exp 1 calculated $w = (32768 - 3840) // 4 = 7232$ (yielding $\mathrm{MAE} = 0.610 \pm 0.004$).
- **Action Taken:**
  - Updated `scripts/run_all.py:run_exp2_skew_sweep()` to evaluate exact budget-derived width $w = 7232$.
  - Added both `Disjoint+Stash` and `AugmentedSketch` to Exp 2 across all skews.
  - Regenerated results in [`results/raw/exp2_skew_sweep.json`](file:///D:/VIT/DSA%20Case%20Study/randomized-approx-query-processing/results/raw/exp2_skew_sweep.json):
    - $\alpha = 1.05$: AdaLog = **3.009 $\pm$ 0.017** | Disjoint+Stash = 4.113 $\pm$ 0.027 | Elastic = 9.996 | Augmented = 9.747
    - $\alpha = 1.15$: AdaLog = **1.502 $\pm$ 0.009** | Disjoint+Stash = 2.128 $\pm$ 0.011 | Elastic = 5.554 | Augmented = 5.407
    - $\alpha = 1.25$: AdaLog = **0.610 $\pm$ 0.004** | Disjoint+Stash = 0.917 $\pm$ 0.012 | Elastic = 2.693 | Augmented = 2.611
    - $\alpha = 1.35$: AdaLog = **0.198 $\pm$ 0.005** | Disjoint+Stash = 0.317 $\pm$ 0.006 | Elastic = 1.113 | Augmented = 1.077
    - $\alpha = 1.50$: AdaLog = **0.027 $\pm$ 0.003** | Disjoint+Stash = 0.047 $\pm$ 0.005 | Elastic = 0.204 | Augmented = 0.193
  - Table V and Table III are now reconciled to the third decimal digit ($0.610 \pm 0.004$).

---

### Step 2: Correctness (Code, Algorithms & Proofs)

#### 2.1 Conservative Update Increment Rule for $c > 1$
- **Status:** **CONFIRMED & RESOLVED**
- **Evidence & File Location:**
  - Counter-example: Cell values $(5, 6, 6)$ updated with $c = 3$.
    - Naive rule: $v_{min} = 5, v_{new} = 5 + 3 = 8$. Only cells matching $v_{min}$ are updated, resulting in $(8, 6, 6)$. Point query $\min(8, 6, 6) = 6 < 8$ produces an underestimation.
    - Correct monotonic rule: $T[j, idx_j] \leftarrow \max(T[j, idx_j], \min(\MV, v_{min} + c))$ for all $j$. Cells become $(8, 8, 8)$, ensuring $\min = 8$ (no underestimation).
- **Code & Test Verification:**
  - Verified in C++ kernel: [`core/adalog_core.cpp:164`](file:///D:/VIT/DSA%20Case%20Study/randomized-approx-query-processing/core/adalog_core.cpp#L164) (`if (cur < v_new) set_cell(..., v_new)`).
  - Verified in Python kernel: [`adalog/sketch.py:136`](file:///D:/VIT/DSA%20Case%20Study/randomized-approx-query-processing/adalog/sketch.py#L136).
  - Unit test added in [`tests/test_adalog_sketch.py:154-195`](file:///D:/VIT/DSA%20Case%20Study/randomized-approx-query-processing/tests/test_adalog_sketch.py#L154-L195) passes with pytest.
  - Paper synchronization: Algorithm 1 line 18 in `paper/main.tex` and Section IV.B text were updated to explicitly state the monotonic $\max()$ update rule.

#### 2.2 Proof Case 2 & Stash Sizing ($K \ge K_{sat}$)
- **Status:** **CONFIRMED & ANALYZED**
- **Ground Truth $K_{sat}$ Stream Measurement:**
  - We measured the exact number of unique keys reaching true frequency $f \ge 255$ ($K_{sat}$) on the test streams ($|\mathcal{U}| = 100\text{k}$, seed 42):
  
| Skew $\alpha$ | $N = 300\text{k}$ $K_{sat}$ | $N = 300\text{k}$ Max Freq | $N = 1\text{M}$ $K_{sat}$ | $N = 1\text{M}$ Max Freq |
| :---: | :---: | :---: | :---: | :---: |
| 1.05 | 102 | 32,220 | 314 | 107,088 |
| 1.15 | 99 | 49,612 | 278 | 164,785 |
| 1.25 | 88 | 68,593 | 235 | 228,311 |
| 1.35 | 76 | 87,874 | 183 | 292,939 |
| 1.50 | 58 | 114,894 | 132 | 383,660 |

- **Analysis:**
  - For the accuracy sweep stream ($N = 300\text{k}$), $K_{sat} \in [58, 102]$. Since $K = 128 \ge 102$, the invariant $K \ge K_{sat}$ holds across all skews, resulting in strictly 0 underestimations.
  - For the latency benchmark stream ($N = 1\text{M}$), $K_{sat} \in [132, 314] > 128$. This confirms the reviewer's insight: with fixed $K = 128$, keys with true count $\ge 255$ cannot all reside in the stash at $N = 1\text{M}$, leading to saturation unless $K$ scales or a runtime flag is raised.
- **Proof & Paper Updates:**
  - Theorem 2 was updated to explicitly require $K \ge K_{sat}$ as a formal precondition.
  - Scope was explicitly restricted to raw estimates ($\hat{f}_{raw}(x) \ge f(x)$), documenting that debiased estimates $\tilde{f}(x)$ can underestimate if estimated noise exceeds actual collision noise.
  - Proved that write-back clipping to $\min(\MV, c_{min})$ is harmless under $K \ge K_{sat}$ because saturated keys are never evicted.

#### 2.3 Proposition 1 and Theorem 1 Formalization
- **Status:** **CONFIRMED & RESOLVED**
- **Proposition 1 Fix:**
  - In `paper/main.tex`: An item promoted at $c_{base} = 20$ that gains $c_{exact} = 10$ increments ($c_{evict} = 30$) evicted under an additive rule becomes $20 + 30 = 50$. True count is 30, so overestimation is $(50 - 30)/30 = 20/30 = +66.7\%$ ($+67\%$), not $+100\%$.
  - Dropped the word "unique": an incremental write-back rule $T[j] \leftarrow T[j] + c_{exact}$ is also valid and non-double-counting.
- **Theorem 1 Fix:**
  - Renamed the heavy-hitter count parameter from $K$ to $H$ in Theorem 1 and its proof to prevent notation clash with the stash capacity $K$.
  - Stated the lower bound that strictly follows from the proof: $\mathbb{E}[\hat{f}(x_m) - f(x_m)] \ge \frac{C_\alpha N}{w} (\sum_{k=1}^H k^{-\alpha}) (1 - (1 - 1/w)^H)^d$.

#### 2.4 Table II Formatting & Multi-Column Collision
- **Status:** **CONFIRMED & RESOLVED**
- **Evidence:** Table II (`tab:capabilities`) had 7 columns and was set as a single-column table `\begin{table}[!t]`, overflowing into the right column and colliding with text.
- **Action Taken:** Wrapped with `\resizebox{\columnwidth}{!}{% ... }`, guaranteeing clean single-column fitting without overflow.

---
"""

# Insert checklist right after Executive Summary
target = "## Phase 1: Correctness (Code & Proofs)\n"
assert target in text, "Target anchor not found in AUDIT.md"
text = text.replace(target, checklist_section + "\n" + target)

with open(AUDIT_PATH, "w", encoding="utf-8") as f:
    f.write(text)

print("AUDIT.md updated successfully with Step 1 and Step 2 Reviewer Checklist!")
