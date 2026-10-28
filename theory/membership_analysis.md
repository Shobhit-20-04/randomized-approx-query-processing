# Theoretical Analysis: Shared Counter Membership (Variant A) vs Dedicated Bloom Filter

**Authors:** Shobhit Agrawal & Mayuri Rajendra Pawar (VIT Vellore)  
**Topic:** Trade-Off Analysis and Break-Even Frontier for Multi-Task AMQ

---

## 1. Problem Formulation

Under a fixed total memory budget $B$ (bytes), a streaming system supporting approximate membership queries (AMQ) and frequency queries faces two structural choices:

1. **Disjoint Stack (Dedicated Bloom Filter + CMS):**  
   Allocates a fraction $\theta \in (0, 1)$ of the total budget $B$ to a dedicated Bloom filter $B_{\text{BF}} = \theta B$ (with optimal $k = \frac{m_{\text{BF}}}{n} \ln 2$ hash functions), leaving $B_{\text{CMS}} = (1 - \theta) B$ for frequency estimation.
   
2. **AdaLog Unified Stack (Variant A - Shared Counters):**  
   Allocates 100% of the byte budget $B$ to the counter matrix $T$ ($d \times w$).  
   An item $x$ is queried for membership via:
   $$x \in \mathcal{S} \iff \bigwedge_{j=0}^{d-1} \big(T[j, idx_j(x)] > 0\big)$$
   Marginal memory allocation for membership = **0 bytes**.

---

## 2. False Positive Rate (FPR) Derivations

### 2.1 Dedicated Optimal Bloom Filter
With $m_{\text{BF}} = 8 \theta B$ bits and $n$ distinct keys:
$$\text{FPR}_{\text{BF}} = \left(\frac{1}{2}\right)^{k} = 2^{- \frac{8 \theta B}{n} \ln 2} \approx 2^{- 5.545 \frac{\theta B}{n}}$$
Each percentage of membership false-positive suppression requires:
$$b_{\text{key}} = \frac{8 \theta B}{n} \approx 1.44 \log_2\left(\frac{1}{\text{FPR}_{\text{BF}}}\right) \quad \text{bits/key}$$

### 2.2 AdaLog-Sketch Variant A (Shared Counters)
In AdaLog-Sketch, the matrix consists of $d \times w$ counters of width $b \in \{8, 16\}$ bits.  
With no dedicated filter, $w = \frac{8 B}{d \cdot b}$.  
Under uniform independent hashing across $d$ rows, the probability that a specific cell in row $j$ receives 0 increments from $n$ distinct keys is:
$$p_0 = \left(1 - \frac{1}{w}\right)^n \approx \exp\left(-\frac{n}{w}\right)$$
Thus, the row occupancy is:
$$D = 1 - p_0 = 1 - \exp\left(-\frac{n}{w}\right)$$
A non-member item false-positives if and only if all $d$ independent hash locations are non-zero:
$$\text{FPR}_{A} = D^d = \left(1 - \exp\left(-\frac{d \cdot b \cdot n}{8 B}\right)\right)^d$$

---

## 3. Break-Even Memory Frontier

To determine when Variant A matches or outperforms a disjoint stack, we equate $\text{FPR}_A = \text{FPR}_{\text{BF}}$ under equal total budget $B$.

Let $\lambda = \frac{B}{n}$ be the total available memory in bytes per distinct key.
For Variant A with $d = 4$ rows and $b = 8$ bits (1 byte) per counter:
$$w = \frac{B}{4} \implies \frac{n}{w} = \frac{4}{\lambda}$$
$$\text{FPR}_A = \left(1 - e^{-4/\lambda}\right)^4$$

For the Disjoint Stack, if $\theta = 0.25$ (25% of memory to Bloom filter, 75% to CMS):
$$\text{FPR}_{\text{BF}} \approx \left(\frac{1}{2}\right)^{\frac{8 \times 0.25 \lambda}{1} \ln 2} = 2^{-1.386 \lambda}$$

### Comparative Table:

| Memory Budget $\lambda$ (Bytes/Key) | Total Bits/Key | Variant A FPR ($d=4, b=8$) | Disjoint BF FPR ($\theta=0.25$) | Disjoint BF FPR ($\theta=0.50$) |
|---|---|---|---|---|
| **4 B/key** | 32 bits | $(1 - e^{-1.0})^4 \approx \mathbf{16.0\%}$ | $2^{-5.54} \approx 2.1\%$ | $2^{-11.09} \approx 0.05\%$ |
| **8 B/key** | 64 bits | $(1 - e^{-0.5})^4 \approx \mathbf{2.4\%}$ | $2^{-11.09} \approx 0.05\%$ | $2^{-22.18} \approx 0.0001\%$ |
| **16 B/key** | 128 bits | $(1 - e^{-0.25})^4 \approx \mathbf{0.24\%}$ | $2^{-22.18} \approx 10^{-7}$ | $2^{-44.36} \approx 10^{-14}$ |
| **32 B/key** | 256 bits | $(1 - e^{-0.125})^4 \approx \mathbf{0.019\%}$ | $\ll 10^{-9}$ | $\ll 10^{-18}$ |

---

## 4. Architectural Findings & Guidelines

1. **Information Density Penalty of 8-bit Counters:**  
   Because each cell in Variant A costs 8 bits instead of 1 bit in a bitmap, for ultra-low FPR targets ($< 0.1\%$) under tight budgets ($\lambda < 8$ B/key), a dedicated 1-bit Bloom plane (Variant B) or dedicated Bloom filter achieves a smaller FPR per byte.

2. **The Frequency Quality Dividend:**  
   However, dedicating 25%–50% of the budget to a Bloom filter catastrophically degrades frequency estimation in CMS. In the disjoint stack, shrinking CMS memory from $B$ to $0.75 B$ increases CMS collision noise by $+33\%$, while shrinking to $0.5 B$ doubles (+100%) collision noise.

3. **Optimal Selection Policy (AdaLog-Planner N1 Rule):**
   - When required $\text{FPR} \ge 2\%$: Use **Variant A** (shared counters). Frequency MAE drops by $35\text{--}50\%$ due to 100% budget utilization.
   - When required $\text{FPR} < 0.5\%$: AdaLog-Planner switches to **Variant B** (allocating a compact 1-bit presence plane) while retaining the single 128-bit hash pipeline.
