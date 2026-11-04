# AdaLog-Sketch: Formal Analysis & Mathematical Correction of Theorem 2

**Audit Date:** November 2026  
**Auditor:** Senior Research Scientist & Algorithm Reviewer  
**Focus:** Derivation of $E[K_{sat}]$, concentration bounds, proof of conditional theorem, and failure boundary analysis.  

---

## 1. Deconstruction of the Original Claim

The original research manuscript claimed:
> **Theorem 2 (Unconditional Zero Underestimation):**  
> *If the elephant stash capacity satisfies $K \ge K_{sat} + \text{collision margin}$, then for all items $x \in \mathcal{U}$, raw frequency estimates guarantee zero underestimation: $\hat{f}_{raw}(x) \ge f(x)$.*

### 1.1 Structural Flaws in the Original Proof
1. **False Equivalence of Baseline:** When an item $x$ is promoted to the stash, its baseline is initialized to $c_{base} = \min_j T[j, \text{idx}_j(x)]$. Because matrix cells accumulate collision noise $\eta(x) \ge 0$, $c_{base} = f(x) + \eta(x) \ge f(x)$. Hence, an item can saturate at 255 even if its true frequency is $f(x) \ll 255$.
2. **False Elephant Hijacking:** These collision-inflated keys ("false elephants") occupy stash slots. If they receive further updates and reach $\ge 255$, they become permanent residents under the candidate eviction filter.
3. **Stash Rejection Boundary:** When all $K$ stash slots hold counts $\ge 255$, the evictable set $\mathcal{E} = \{y \in \mathcal{S} \mid \hat{f}(y) < 255\} = \emptyset$. When an arriving genuine heavy key $x_{heavy}$ reaches 255 in the matrix, stash promotion fails (`promote()` returns `None`). The key cannot enter the stash, and because matrix counters saturate at $\text{MAX\_VAL} = 255$, all subsequent arrivals of $x_{heavy}$ are permanently dropped.

---

## 2. Formal Derivation of Saturating Key Expectation $E[K_{sat}]$

Let stream $S$ have length $N$ over universe $\mathcal{U}$, with item frequencies following a Zipfian distribution with parameter $\alpha > 1$:
$$f(i) = N \cdot \frac{i^{-\alpha}}{\zeta(\alpha)}, \quad \text{where } \zeta(\alpha) = \sum_{k=1}^{|\mathcal{U}|} k^{-\alpha}$$

The true number of heavy hitters exceeding the saturation threshold $\theta_{sat} = 255$ is:
$$K_{true\_sat} = \left\lfloor \left( \frac{N}{255 \cdot \zeta(\alpha)} \right)^{1/\alpha} \right\rfloor$$

However, due to Conservative Update collision noise in a matrix of depth $d$ and width $w$, the expected noise per cell is bounded by $\frac{N_{matrix}}{w}$. Therefore, any key with true frequency:
$$f(i) \ge 255 - d \cdot \frac{N_{matrix}}{w}$$
can saturate the matrix counter.

Thus, the expected number of saturating keys $E[K_{sat}]$ entering the candidate pool is:
$$E[K_{sat}] = \sum_{i=1}^{|\mathcal{U}|} \Pr\left( f(i) + \min_{j=1}^d \eta_j(i) \ge 255 \right)$$

Applying Markov's inequality to the collision noise under $d$ independent hash functions:
$$\Pr\left( \min_{j=1}^d \eta_j(i) \ge \tau \right) \le \left( \frac{N_{matrix}}{w \cdot \tau} \right)^d$$

---

## 3. The Corrected Theorem Statement & Proof

### Theorem 2 (Conditional Zero Underestimation Invariant)
*Let $\mathcal{S}$ be an arbitrary stream of $N$ arrivals processed by AdaLog-Sketch with $d$ hash functions, matrix width $w$, counter bit-width $b=8$ ($\text{MAX\_VAL}=255$), and stash capacity $K$. Suppose that:*
1. *The stash eviction policy is globally associative with minimum-count replacement.*
2. *Monotonic write-back is enforced: upon eviction of key $y$, $T[j, \text{idx}_j(y)] \leftarrow \max(T[j, \text{idx}_j(y)], \min(\text{MAX\_VAL}, \hat{f}(y)))$ for all $j \in [1, d]$.*
3. *The stash capacity satisfies the noise-buffered sizing condition:*
   $$K \ge K_{sat}^* = \left| \left\{ x \in \mathcal{U} \;\middle|\; f(x) + \frac{d \cdot N_{matrix}}{w} \ge 255 \right\} \right|$$

*Then, for all items $x \in \mathcal{U}$, the raw frequency estimate satisfies:*
$$\hat{f}_{raw}(x) \ge f(x)$$

### Proof
1. **Case 1: $x$ never saturates in the matrix.**  
   If $\min_j T[j, \text{idx}_j(x)] < 255$ throughout the stream, no counter clipping occurs. By the standard Conservative Update property (Cormode & Muthukrishnan, 2005; Goyal et al., 2012), each counter satisfies $T[j, \text{idx}_j(x)] \ge f(x)$. Hence, $\hat{f}_{raw}(x) = \min_j T[j, \text{idx}_j(x)] \ge f(x)$.
2. **Case 2: $x$ saturates and resides in the stash.**  
   When $\min_j T[j, \text{idx}_j(x)]$ reaches 255, key $x$ is promoted to the stash. Since $K \ge K_{sat}^*$, the total number of candidate keys reaching saturation (including false elephants) is at most $K$. Thus, the stash never rejects $x$. In the stash, exact counting is maintained: $\hat{f}_{stash}(x) = c_{base} + c_{exact} \ge f(x) + c_{exact}$. Every arrival increments $c_{exact}$. Therefore, $\hat{f}_{raw}(x) = \hat{f}_{stash}(x) \ge f(x)$.
3. **Case 3: $x$ is evicted and written back.**  
   If $x$ is evicted to admit another item, its count $\hat{f}_{stash}(x) \ge f(x)$ is written back via $\max()$. Even though the 8-bit matrix cell cannot exceed 255, any key eligible for eviction must have had count $< 255$ (by the candidate eviction policy). Thus, no truncation occurs during write-back. Subsequent arrivals either increment the matrix or re-promote $x$.
4. **Conclusion:** Under conditions (1)–(3), no arrivals are lost to saturation clipping. Hence, $\hat{f}_{raw}(x) \ge f(x)$ holds universally. $\blacksquare$

---

## 4. Empirical Failure Boundary (Test T05 Evidence)

When condition (3) is violated ($K < K_{sat}^*$):
- In Test T05 ($K=16$, $M=25$ heavy keys, $f(x)=400$):
  - 16 keys entered the stash and tracked exact frequency: $\hat{f} = 400$.
  - 9 excess keys were rejected from the stash and clamped at matrix ceiling $\text{MAX\_VAL} = 255$.
  - Underestimation error: $\hat{f}_{raw} - f = 255 - 400 = \mathbf{-145}$ (**36.25% relative underestimation**).
- **Conclusion:** Theorem 2 CANNOT hold unconditionally. Academic honesty requires presenting Theorem 2 strictly as a conditional invariant.
