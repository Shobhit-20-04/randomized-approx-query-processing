# CHANGELOG: Rigorous Revision and Paper Reconciliation

**Paper Title:** AdaLog-Sketch: A Unified Approximate Query Processing Data Structure for Multi-Task Stream Analytics  
**Branch:** `audit-rigor-fixes`  
**Date:** October 31, 2026  
**Testbed:** 13th Gen Intel Core i5-13450HX (10 cores, 16 threads, 20 MB cache), 16 GB DDR4, MinGW-w64 GCC 16.1.0 (-O3), Python 3.11.9  

---

## 1. Quantitative Discrepancy Reconciliation (Old Value $\to$ New Value)

Every number below was regenerated directly by executable scripts in the repository (`scripts/run_all.py`, `scripts/search_equal_accuracy.py`, `core/bench_core.exe`, `scripts/measure_cardinality_100trials.py`, `scripts/run_exp9_real.py`) and recorded in `results/raw/*.json`. No numbers have been hand-edited or invented.

| Metric / Result Location | Old Paper Claim | New Measured Result | Root Cause & Scientific Rationale |
| :--- | :--- | :--- | :--- |
| **Headline Memory Saving ($\mathrm{MAE} \le 0.40$)** (Abstract, Table IV, Sec. VI.B) | $64.1\%$ memory reduction ($37.8$ KB vs. $105.2$ KB) | **$16.4\%$** memory reduction vs. `Disjoint+Stash` ($37.8$ KB vs. $45.2$ KB); $53.0\%$ vs. Elastic ($80.5$ KB); $52.7\%$ vs. Augmented ($79.9$ KB) | The $64.1\%$ claim was an artifact of 16-bit counter saturation on the disjoint baseline ($f > 65,535$ causing massive head error). `Disjoint+Stash` is now the honest primary baseline; $16.4\%$ represents genuine savings from unifying Bloom filter memory. |
| **Skew Sweep Error Reduction** ($\alpha = 1.05$ to $1.50$, Table V, Sec. VI.C) | $3.2\times$ to $267.9\times$ ($99.6\%$) error reduction vs. Disjoint Stack | **$26.8\%$ to $40.0\%$** reduction vs. `Disjoint+Stash` (MAE: $3.01 \to 0.03$ vs. $4.11 \to 0.05$) | The $267.9\times$ advantage at $\alpha=1.50$ was caused by the top key ($f = 114,894$) overflowing the 16-bit baseline (Head $\mathrm{MAE} = 496.14$). Against the fair stashed baseline, AdaLog achieves a solid $26.8\%$--$40.0\%$ advantage due to $39.5\%$ wider matrix rows. |
| **Exp 2 AdaLog MAE at 32 KB, $\alpha = 1.25$** (Table V, Fig. 3 vs. Table III, VII) | $0.73 \pm 0.01$ (Table V) vs. $0.61 \pm 0.00$ (Table III/VII) | **$0.610 \pm 0.004$** across all tables | Table V previously hardcoded an uncoordinated width $w = 6682$. Re-evaluating with the exact budget-derived width $w = 7232$ matches Table III to the third decimal place. |
| **C++ Ingestion Throughput** (Abstract, Table VI, Sec. VI.D) | $22.22 \pm 0.46$ Mops/s ($45.0$ ns) vs. $20.27 \pm 0.24$ Mops/s ($49.3$ ns) | **$21.97 \pm 0.38$ Mops/s** ($45.52 \pm 0.79$ ns) vs. **$19.84 \pm 0.45$ Mops/s** ($50.43 \pm 1.18$ ns) | Measured over 10 consecutive warm runs on 13th Gen Intel Core i5-13450HX. AdaLog achieves a statistically robust $1.11\times$ speedup ($9.7\%$ latency reduction) over the disjoint stack. |
| **AMQ Query Latency** (Sec. VI.D, Table VI) | $0.2$ ns/op (sub-cycle) | **$12.26$ ns/op** | Previous benchmark contained `amq_hit = amq_hit \|\| adalog->contains(...)`, which short-circuited after the first hit and was eliminated by compiler optimizations. Fixed by accumulating and consuming hits. |
| **Point Query Latency** (Sec. VI.D, Table VI) | $12.8$ ns/op | **$13.43$ ns/op** | Validated via non-inlined tight loop benchmark in compiled C++ (-O3). |
| **Cardinality Precision (RSE)** (Abstract, Table I, Table III, Sec. VII.B) | Flat $0.0424$ across budgets; baseline $0.0098$ at all budgets | **$0.0239 \pm 0.0183$** ($m=1024$, 768 B, 100 trials, 95% CI: $[0.0203, 0.0276]$); dedicated HLL **$0.0053 \pm 0.0043$** ($m=16384$, 12 KB, 100 trials, 95% CI: $[0.0045, 0.0062]$) | Evaluated over 100 independent trials (10 seeds cannot statistically distinguish 0.0424 from 0.0376). Clearly documents the memory cost: reaching $\mathrm{RSE} < 0.01$ requires 12 KB (37.5% of a 32 KB budget), whereas AdaLog spends only 768 B (2.4%). |
| **Membership False Positive Rate** (Abstract, Sec. VII.A) | "$1.37\%$ vs $0.06\%$ at 128 KB; Bloom wins only $\le 32$ KB" | **$3.86\%$ vs. $0.45\%$** at 128 KB; Bloom wins at **every budget** (gap widens to $8.6\times$ at 128 KB) | Honest characterization: A dedicated 1-bit Bloom filter packs $8\times$ more cells per byte than 8-bit counters and achieves lower FPR across all allocations. AdaLog explicitly trades higher FPR for 0 marginal memory bytes. |
| **Additive Write-Back Error (Proposition 1)** (Sec. V.A) | Double-counting inflates count by "up to $+100\%$"; "unique" write-back | Double-counting inflates count by **$+66.7\%$ ($+67\%$)**; dropped "unique" claim | Counter-example with $c_{base} = 20, c_{exact} = 10, c_{evict} = 30$: additive rule gives $20 + 30 = 50$, an inflation of $(50 - 30)/30 = +66.7\%$ ($+67\%$, not $+100\%$). Monotonic $\max()$ is sufficient, but incremental $T + c_{exact}$ is also valid. |
| **Stash Sizing vs. Saturation ($K$ vs. $K_{sat}$)** (Theorem 2, Sec. V.A) | Unconditional zero underestimation ($\hat{f} \ge f$) | **Conditional guarantee:** strictly holds for raw queries when **$K \ge K_{sat} = \#\{x \mid f(x) \ge 255\}$** | At $N=300\text{k}$, $K_{sat} \le 102 \le 128$, so strictly 0 underestimations occur. At $N=1\text{M}$, $K_{sat} \le 314 > 128$, meaning keys with $f \ge 255$ saturate if $K$ is not scaled. Debiased estimates $\tilde{f}(x)$ can also underestimate if noise is over-predicted. |
| **Real Gutenberg Literature Stream** (Sec. VII.D) | $\mathrm{MAE} = 3.18$, stash occupancy $98/128$ | **$\mathrm{MAE} = 3.17$**, occupancy **$128/128$** ($\tau = 10$); outperforms `Disjoint+Stash` ($4.53$), Elastic ($11.85$), and Disjoint-16 ($12.55$) | At $\tau = 15$, exactly 98 vocabulary items exceeded 15 occurrences. Setting $\tau = 10$ admits items with frequencies 10–14, reaching full occupancy 128/128 with virtually identical MAE ($3.174$ vs. $3.175$). |
| **Real CAIDA IP Backbone Trace** (Sec. VII.D) | Not reported | AdaLog $\mathrm{MAE} = \mathbf{13.47}$ (128/128 occupancy) vs. `Disjoint+Stash` $\mathbf{17.02}$ and Elastic $\mathbf{34.93}$ | Verified on high-velocity packet trace (300,000 packets) demonstrating 20.8% error reduction over Disjoint+Stash and 2.59x over Elastic Sketch. |
| **Empirical Confidence Intervals** (Sec. V.B, Exp 6) | "Certified intervals" with unexplained $1+0.15d$ | **Empirical confidence intervals** with **$100.0\%$ coverage** across all skews, average width **$3.1$ to $5.3$ counts** | Renamed from "certified" to "empirical confidence intervals" because rows in double hashing and CU are not statistically independent. Empirically validated across all Zipfian skews. |
| **Planner Error Across Budgets** (Abstract, Contributions, Sec. V.B) | Stale claim: "within 2.74%" | Measured across budgets: **$5.40\%$** at 8 KB, **$38.39\%$** at 16 KB, **$9.45\%$** at 128 KB | Closed-form model correctly predicts order-of-magnitude error scaling across budgets, but conservative model overestimates error at 32–64 KB where elephant stash clears heavy hitters more effectively than modeled. |

---

## 2. Text, Formatting, and Reference Corrections

1. **LaTeX Overleaf Errors Fully Resolved:**
   - **`@IEEEauthorhalign` Mismatch:** Removed fragile `\linebreakand` hack from preamble. Implemented clean, robust `minipage` author layout matching the exact design: Shobhit Agrawal & Mayuri Rajendra Pawar on the top row, and Dr. Parveen Sultana H centered on the bottom row.
   - **`amsthm` Conflict:** Added `\let\proof\relax \let\endproof\relax` before loading `amsthm`, preventing internal macro collisions with `IEEEtran.cls`.
   - **Undefined Environments:** Defined `\newtheorem{proposition}{Proposition}` cleanly in the preamble.
   - **Table II Layout Overlap:** Replaced wide 7-column table with compact column headers (`Synopsis`, `AMQ`, `Freq.`, `Card.`, `Top-k`, `Shared`, `Hashes`) wrapped in `\resizebox{\columnwidth}{!}{% ... }`, completely eliminating float collisions and column gutter bleeding into the second column.
   - **Tab Character in `\textit`:** Replaced all 43 occurrences of raw `\t` tab characters in `\bibitem` bibliography entries with valid `\textit`.
   - **Equation Overflow:** Condensed Equation (4) ($P_{\mathrm{all\_coll}} = (1 - (1 - 1/w)^H)^d$) and split Equation (6) across lines to prevent 2-column margin overflow.

2. **Citations & Literature Alignment:**
   - Removed orphaned names: "Li et al. [3]", "Siva [5]", and "Aladiyan [4]" from Sections II.B and II.D.
   - Restored references `[3]`, `[4]`, `[5]` to their true citations in computer architecture (Ailamaki et al., Manegold et al., Drepper).
   - Corrected Estan & Varghese to 2003 in Table I to match `\bibitem{b9}` (TOCS 2003).
   - Standardized single-hash pipeline to **XXH3-128** (removed "MurmurHash3 or XXH3").
   - Removed all occurrences of "strict DSA principles" from prose.
   - Fixed Algorithm 1 walkthrough line numbers: Arrival 1 (lines 6–9, 15–19), Promotion (lines 21–23), Stash residence (lines 2–4), Eviction (lines 25–32).
   - Corrected experiment numbering: Exp 8 renamed to Exp 5.

3. **Reproducibility & Testbed Documentation:**
   - Added Table `tab:params` documenting exact parameter configurations across all 5 evaluated architectures.
   - Documented processor hardware: 13th Gen Intel Core i5-13450HX, 16 GB DDR4, MinGW-w64 GCC 16.1.0 (-O3).
   - Documented the exact 10 evaluation seeds: `{42, 100, 2024, 31415, 27182, 16180, 57721, 14142, 17320, 22360}`.
   - Formally defined all metrics: MAE, ARE, Peak Overestimation Error, AMQ False Positive Rate (10,000 probe keys), Cardinality RSE.

---

## 3. Decisions for Human Author Judgment

The following design decisions are surfaced for your final review:

1. **Baseline Naming in Publication Text:**
   - *Current choice:* We have designated the fair baseline as **`Disjoint+Stash`** in Table IV, Table V, and the main text.
   - *Alternative:* You could designate it as **`Disjoint Stack (Stashed)`** or **`Augmented Disjoint Baseline`**.
   - *Recommendation:* Keep `Disjoint+Stash` as it clearly conveys that an elephant stash was added to the disjoint stack to prevent unfair counter overflow.

2. **Stash Sizing Policy for Large Streams ($N \ge 1\text{M}$):**
   - *Current choice:* We proved that the zero-underestimate invariant holds whenever $K \ge K_{sat} = \#\{x \mid f(x) \ge 255\}$. At $N = 300\text{k}$, $K = 128 \ge 102$, so the invariant holds unconditionally. At $N = 1\text{M}$, $K_{sat} \approx 314 > 128$.
   - *Options:*
     - (A) Recommend dynamic stash scaling ($K \propto N^{1 - 1/\alpha}$) for unbounded streams.
     - (B) State the condition $K \ge K_{sat}$ as a formal operational requirement and raise an overflow flag when the stash is saturated.
   - *Recommendation:* Option (B) is mathematically rigorous, honest, and directly answers the reviewer's concern without altering the 32 KB embedded budget.

3. **Membership Framing:**
   - *Current choice:* We explicitly state that dedicated Bloom filters achieve lower FPR at every budget ($8.6\times$ lower at 128 KB, 0.45% vs. 3.86%), and frame AdaLog's contribution as **zero marginal memory bytes** and single-hash cache efficiency for pre-filtering pipelines.
   - *Recommendation:* Retain this honest framing. Reviewers respect acknowledging trade-offs over claiming universal dominance.
