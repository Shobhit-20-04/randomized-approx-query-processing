# AdaLog-Sketch: Final Technical Audit & Synthesis Report

**Audit Date:** November 2026  
**Auditor:** Senior Principal Research Scientist & Lead Forensic Reviewer  
**Classification:** Definitive Technical Certification & Roadmap Assessment  

---

## 1. Executive Synthesis & Direct Answers to Strategic Questions

This comprehensive audit evaluated the AdaLog-Sketch research project across four pillars: formal mathematics, C++ systems implementation, empirical baseline fairness, and manuscript accuracy.

### Question 1: Is the algorithm mathematically correct?
**Verdict: NO (Unconditionally) / CONDITIONAL ONLY.**
- **Theorem 2 Invalidation:** The claim that AdaLog-Sketch guarantees zero underestimation $\forall x$ is mathematically false when heavy keys exceed stash capacity ($K_{sat} > K$) or when matrix collision noise admits false elephants that saturate at $\ge 255$. Under stash overflow, arrivals are rejected and clipped at 255 in the 8-bit matrix.
- **Condition for Validity:** Zero underestimation holds **if and only if** $K \ge K_{sat}^* = |\{x \mid f(x) + d \cdot \frac{N_{matrix}}{w} \ge 255\}|$ with monotonic write-back and global minimum eviction.
- **Confidence Intervals:** Intervals are heuristic empirical bounds due to Conservative Update non-linearities.

### Question 2: Does the actual C++ implementation behave as the paper describes?
**Verdict: NO (Pre-Audit) -> YES (Post-Audit Corrections Applied).**
- **Original Divergences Identified:**
  1. *Stash Architecture:* Paper claimed CAM global-min; C++ implemented 2-choice hash table (128 slots) with local eviction (Test T06: 30/30 heavy keys clipped).
  2. *Top-k Query:* Completely absent in C++ core despite paper claims.
  3. *Hash Family:* `core/hash_xxh3.h` implemented MurmurHash3_128, while Python used XXH3_128.
  4. *HLL Sizing:* C++ hardcoded $hll\_m = w = 7,232$ (5,424 B) instead of 768 B.
- **Engine Corrections Implemented:** Dynamic stash capacity, true 2-choice fast-path hashing, native top-k query min-heap, decoupled 768 B HLL registers, and dynamic AMQ threshold $\theta(N)$.

### Question 3: Are the reported experimental results genuine and reproducible?
**Verdict: PARTIALLY GENUINE, WITH UNFAIR HISTORICAL BASELINES.**
- **Verified Headline Throughput:** Sustained **21.97 ± 0.38 Mops/s (45.52 ns/op)** confirmed on Intel i5-13450HX.
- **Baseline Memory Overrun:** The historical Disjoint+Stash baseline consumed 33,790 bytes (+3.1% overrun) due to an erroneous 16 B/entry assumption. Calibrated to strict 32,765 bytes ($w=5,785$).
- **AMQ FPR Disclosure:** AdaLog-Sketch dynamic threshold AMQ achieves empirical FPR of 73.25% at 32 KB, 98.99% at 16 KB, and 100% at 8 KB. The claimed 0.98% was an isolated Bloom filter target.

---

## 2. Test Suite Certification Matrix (audit/AdaLog_Sketch_Audit_Test_Results.csv)

All 14 independent verification test cases were executed and logged:
- **T01 (Single-Key Saturation):** PASS (Exact count 500 preserved in stash).
- **T02 (Conservative Update Noise):** PASS (CU suppresses collision noise).
- **T03 (8-bit Counter Saturation):** PASS (Matrix saturates at 255 without stash).
- **T04 (Stash Promotion at Tau):** PASS (Promoted at count $\ge 25$).
- **T05 (Theorem 2 Invariant Under Overflow):** FAIL / CRITICAL (9 of 25 heavy keys clipped at 255; 36.25% underestimation).
- **T06 (C++ 2-Choice Stash Overflow):** FAIL / CRITICAL (2-choice slot conflict clips keys).
- **T07 (Stash Write-Back Lower Bound):** PASS (Lower bound preserved for counts $\le 255$).
- **T08 (Heavy-Hitter Recovery):** PASS (Evicted keys recover upon arrival).
- **T09 (Variable-Length Keys):** PASS (String keys hash without memory faults).
- **T10 (C++ vs Python Hash Equivalence):** FAIL / HIGH (Murmur3 vs XXH3 divergence).
- **T11 (C++ vs Python Differential Stream):** PASS (Point estimates diverge by $\le 2$).
- **T12 (Membership Query FPR):** FAIL / HIGH (0 FN, but FPR = 6.18% to 73.25%).
- **T13 (Counter Boundary Conditions):** PASS (Zero and negative counts safely ignored).
- **T14 (Top-k Extraction Under Capacity):** PASS (Top-10 recall = 1.00 when $K \ge k$).

---

## 3. Final Strategic Decision: Improve Algorithm vs. Reconsider Claims

**Strategic Recommendation: Execute Path C (Comprehensive Synthesis).**
1. **Algorithm Improvements:** Maintain the corrected C++ engine with dynamic stash sizing, native top-k query min-heap, decoupled 768 B HLL registers, and verified 21.97 Mops/s throughput.
2. **Theoretical Reconsiderations:** Rephrase Theorem 2 as a conditional invariant with explicit buffer margins $K \ge K_{sat}^*$, honestly disclose the AMQ FPR trade-off (73.25% at 32 KB), and benchmark against the strict 32 KB Disjoint+Stash baseline.
