# AdaLog-Sketch: Research Paper Status & Section-by-Section Audit

**Audit Date:** November 2026  
**Audited Artifacts:**  
- Primary Source: [`research_paper_final/main.tex`](file:///D:/VIT/DSA%20Case%20Study/randomized-approx-query-processing/research_paper_final/main.tex) (812 lines)
- Duplicate Source: [`paper/main.tex`](file:///D:/VIT/DSA%20Case%20Study/randomized-approx-query-processing/paper/main.tex) (Identical hash `fd44...`)
- Compiled Manuscript PDF: [`research_paper_final/AdaLog_Sketch_Final_Research_Paper.pdf`](file:///D:/VIT/DSA%20Case%20Study/randomized-approx-query-processing/research_paper_final/AdaLog_Sketch_Final_Research_Paper.pdf) (13 Pages, Overleaf build)
- Historical Comparison: `Downloads/AdaLog_Sketch (12).pdf` (Original PDF before technical overhaul)

---

## 1. Executive Status of the Research Paper

The research paper has been overhauled to eliminate all unsupported mathematical claims, reconcile experimental values with raw benchmark data, and provide complete scientific transparency:
1. **Unconditional Theorem 2 Removed:** Replaced with a mathematically rigorous **conditional invariant** requiring $K \ge K_{sat}^*$ alongside an explicit counterexample when $K < K_{sat}^*$.
2. **Confidence Intervals Qualified:** Clarified as practical empirical heuristics rather than distribution-free Gaussian bounds due to Conservative Update non-linearities.
3. **AMQ FPR Honestly Disclosed:** Empirical false-positive rates (73.25% at 32 KB, 100% at 8 KB) are reported directly; claims of "Bloom filter replacement" are qualified as a lightweight soft pre-filter.
4. **Baseline Memory Overrun Acknowledged:** The 1,022-byte (+3.1%) historical Disjoint+Stash overrun is explicitly documented in Table IV, alongside the strictly calibrated 32 KB baseline.
5. **Throughput Grounded:** Standardized on the verified C++ benchmark of **21.97 ± 0.38 Mops/s** (45.52 ns/op).
6. **Editorial Polish:** All `% TODO(author)` comments stripped; all 44 citations verified; passed `scripts/validate_paper.py` with zero errors.

---

## 2. Section-by-Section Forensic Audit Table

| Section | Current Condition | Identified Problem / Risk in Earlier Drafts | Corrective Action Applied | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Title & Authorship** | Standard IEEEtran conference format with 3 author blocks: Shobhit Agrawal, Mayuri Rajendra Pawar, and Dr. Parveen Sultana H (Faculty Guide). | Earlier drafts had minipage alignment conflicts and missing advisor affiliations. | Cleaned up using `\linebreakand` and standard IEEE formatting. | **READY** |
| **Abstract** | Concise summary of unified contiguous memory, 16.4% memory saving vs Disjoint+Stash, 21.97 Mops/s throughput, conditional zero-underestimation ($K \ge K_{sat}$), and higher AMQ FPR (73.25%). | Claimed unconditional zero-underestimation and Bloom filter equivalence. | Rewritten with exact empirical measurements and explicit trade-off disclosures. | **READY** |
| **Introduction** | Motivates AQP across 4 analytical tasks and details the 4 operational drawbacks of disjoint memory silos. | None. Strong conceptual motivation. | Preserved cleanly; citations verified. | **READY** |
| **Contributions** | 5 specific contributions: unified architecture, zero-marginal-memory AMQ, packed 6-bit HLL, conservative update with monotonic write-back, and empirical benchmarks. | Claimed universal zero-underestimation proof. | Qualified contribution 4 to specify the $K \ge K_{sat}$ sizing condition. | **READY** |
| **Taxonomy & Survey** | Tables I & II provide taxonomy and capability matrix across streaming synopses. | Table II claimed unconditional zero-underestimation. | Updated Table II to explicitly state `Yes ($K \ge K_{sat}$)`. | **READY** |
| **Theoretical Modeling of Skew** | Formulates stream model and proves Theorem 1 (Zipfian collision lower bound in standard CMS). | Theorem 1 bound is practically vacuous for wide sketches ($w \ge 4096$). | Added analytical note explaining that cumulative intermediate collisions dominate in practice. | **READY** |
| **System Architecture** | Details 128-bit XXH3 pipeline, Carter-Wegman multiply-shift row indexing, and Fig. 1 architecture diagram. | Diagram and text previously assumed CAM associative stash for C++. | Clarified software implementation as 2-choice bounded hash table. | **READY** |
| **Proposed Algorithm** | Algorithm 1 details stream update, HLL update, Conservative Update, and stash promotion/eviction with monotonic write-back. | Pseudocode previously showed additive write-back which causes double counting. | Aligned with monotonic $\max()$ write-back logic. | **READY** |
| **Theoretical Invariants & Proofs** | Formulates Proposition 1 ($E[K_{sat}]$ bound), Theorem 2 (Conditional Zero Underestimation), Proposition 2 (Monotonic Write-back), and Alg. 2 (LightRanger). | Theorem 2 claimed unconditional zero underestimation, which fails when stash overflows (Test T05). | Reformulated Theorem 2 with noise safety margin $K \ge K_{sat}^*$ and included explicit counterexample trace. | **READY** |
| **Empirical Setup & Memory Table** | Table III defines parameter configurations. Discloses both historical over-budget Disjoint+Stash (33,790 B) and strict baseline (32,768 B). | Stash memory was historically calculated as 16 B/entry instead of 24 B/entry. | Full byte-level breakdown provided with transparent footnote explanations. | **READY** |
| **Exp 1: Memory Budget Sweep** | Table IV reports MAE, ARE, FPR, Card. MARE, Top-100, and Underestimate counts across 8 KB to 512 KB (10 seeds). Fig. 2 Pareto curve. | Conflated Bloom filter FPR with AdaLog AMQ FPR. | Correctly reports AdaLog AMQ FPR (73.25% at 32 KB) and notes zero underestimations under $K \ge K_{sat}$. | **READY** |
| **Exp 2: Skew Sensitivity** | Table V reports performance across $\alpha \in [1.05, 1.50]$. Confirms 26.8% to 41.7% MAE reduction over Disjoint+Stash. | Heavy-tier counter overflow in 16-bit baseline was not separated from tail error. | Explicitly separates Heavy (H) and Tail (T) tiers in Table V notes. | **READY** |
| **Exp 3: C++ Latency & Throughput** | Table VI & Fig. 3 report 21.97 ± 0.38 Mops/s (45.52 ns/op) and query latencies (13.43 ns point, 12.26 ns membership). | Conflicted with synthetic draft numbers (7.4–11.8 Mops/s). | Standardized on verified empirical C++ measurements. | **READY** |
| **Exp 4: Component Ablations** | Table VII isolates HLL coupling, Stash removal, CU removal, counter bit widths, and Variant B presence plane. | Coupling test previously had unverified statistical significance claims. | Clarified that the $1.45\times$ gap lies within $\approx 1.9$ standard errors. | **READY** |
| **Exp 5: LightRanger Compression** | Evaluates bit-plane residual coding across matrix sizes. Demonstrates 36.9% reduction at 256 KB. | Negative compression at small sizes was not explained. | Transparently explains header overhead at 16 KB ($-11.9\%$). | **READY** |
| **Discussion & Limitations** | Discusses AMQ FPR trade-offs, fixed cardinality precision (2.39%), adaptive controller negative result, CAIDA/Gutenberg, and 4 threats to validity. | Limitations were previously omitted or minimized. | Thorough and honest discussion of all operational boundaries. | **READY** |
| **Conclusion** | Summarizes validated contributions, verified 1.11x throughput speedup, 16.4% honest memory saving, and accepted trade-offs. | Abstract and conclusion previously claimed conflicting numbers. | 100% numerical consistency between Abstract and Conclusion. | **READY** |
| **References** | 44 references formatted according to IEEE standards. Zero missing citations or unmatched keys. | Several bibitems had unmatched quotation marks or unescaped characters. | Verified and validated via `scripts/verify_paper_bib.py`. | **READY** |

---

## 3. PDF vs Source Synchronization Check
- **LaTeX Source:** `research_paper_final/main.tex` (812 lines).
- **Compiled PDF:** `research_paper_final/AdaLog_Sketch_Final_Research_Paper.pdf` (13 pages, 502,906 bytes).
- **Synchronization Verdict:** Fully synchronized. The PDF compiles directly from `main.tex` in Overleaf without warnings, bad citations, or undefined environments.
