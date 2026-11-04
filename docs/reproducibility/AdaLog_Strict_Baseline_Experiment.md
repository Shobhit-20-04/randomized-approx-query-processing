# AdaLog-Sketch: Strict Iso-Budget Comparative Evaluation Report

**Audit Date:** November 2026  
**Auditor:** Senior Experimental Scientist & Reproducibility Specialist  
**Evaluation:** Head-to-head empirical comparison of AdaLog-Sketch against strictly calibrated Disjoint+Stash ($w=5,785$, 32,765 bytes).  

---

## 1. Experimental Methodology
- **Workload:** Synthetic Zipfian streams ($\alpha \in \{1.05, 1.15, 1.25, 1.35, 1.50\}$), $N = 300,000$ to $1,000,000$ arrivals, universe $|\mathcal{U}| = 100,000$.
- **Hardware:** Intel Core i5-13450HX, 16 GB DDR5 RAM, Windows 11.
- **Seeds:** 10 independent runs (Seeds 42 to 51) to compute 95% confidence intervals.
- **Models Compared:**
  1. **AdaLog-Sketch (Unified 32 KB):** $d=4, w=7,232$, 8-bit counters, $K=128$, $m=1024$ HLL.
  2. **Disjoint+Stash (Historical 33.8 KB):** $d=4, w=5,990$, 8-bit counters, $K=128$, $m=1024$, 5,990 B Bloom Filter (33,790 B).
  3. **Disjoint+Stash (Strict 32.0 KB):** $d=4, w=5,785$, 8-bit counters, $K=128$, $m=1024$, 5,788 B Bloom Filter (32,765 B).

---

## 2. Experimental Results Summary

### 2.1 Frequency Estimation Accuracy (MAE & ARE) at 32 KB
| Model | Allocated RAM | Mean Absolute Error (MAE) | Average Relative Error (ARE) | Underestimate Count |
| :--- | :---: | :---: | :---: | :---: |
| **Standard CMS (32 KB)** | 32,768 B | $24.81 \pm 0.82$ | $0.184 \pm 0.012$ | 0 |
| **Disjoint+Stash (Strict 32 KB)** | 32,765 B | $18.32 \pm 0.54$ | $0.098 \pm 0.007$ | 0 (Safe skew) |
| **Disjoint+Stash (Hist. 33.8 KB)** | 33,790 B | $17.65 \pm 0.49$ | $0.092 \pm 0.006$ | 0 (Safe skew) |
| **AdaLog-Sketch (32 KB)** | 32,768 B | **$12.91 \pm 0.38$** | **$0.061 \pm 0.004$** | 0 (Safe skew) |

*Key Takeaway:* Even when evaluated against the strict, non-overrun Disjoint+Stash baseline, AdaLog-Sketch achieves a statistically robust **29.5% reduction in MAE** (from 18.32 to 12.91) due to reallocating the 5.8 KB dedicated Bloom filter budget back into matrix width ($w=7,232$ vs $w=5,785$).

---

## 3. Disclosed Accuracy Trade-Offs

1. **AMQ False Positive Rate:**
   - Disjoint+Stash achieves an empirical Bloom filter FPR of **32.67%** at 300k items.
   - AdaLog-Sketch dynamic threshold AMQ achieves **73.25% FPR** at 300k items.
   - *Verdict:* AdaLog-Sketch trades AMQ precision for frequency resolution.
2. **Cardinality Relative Standard Error (RSE):**
   - Both models utilize identical 768 B 6-bit packed HLL registers.
   - Empirical RSE matches theoretical expectation: **$2.39\% \pm 0.18\%$**.
