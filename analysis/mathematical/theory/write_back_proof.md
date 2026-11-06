# Theorem & Formal Proof: Stash Write-Back Zero-Underestimate Invariant

**Authors:** Shobhit Agrawal & Mayuri Rajendra Pawar (VIT Vellore)  
**Topic:** Exactness and Invariant Preservation in AdaLog-Sketch

---

## 1. Theorem Statement

**Theorem 1 (Never-Underestimate Invariant under Stash Lifecycle and Dynamic $\tau$).**  
Let $\mathcal{S} = \langle x_1, x_2, \dots, x_N \rangle$ be a stream of items, where $f_t(y) = \sum_{i=1}^t \mathbb{I}(x_i = y)$ denotes the true frequency of key $y$ at time step $t$.  
Let the AdaLog-Sketch maintain:
1. A counter matrix $T$ of size $d \times w$ with Conservative Update.
2. An associative stash $E$ of capacity $K$ with dynamic promotion threshold $\tau_t$ governed by an online controller.
3. On stash eviction of entry $(x, c_{base}, c_{exact})$, the write-back rule:
   $$\forall j \in \{0, \dots, d-1\}, \quad T[j, idx_j(x)] \leftarrow \max\big(T[j, idx_j(x)], \; c_{base} + c_{exact}\big)$$

Then, for all items $y$, at every time step $t \in \{1, \dots, N\}$, the frequency estimate satisfies:
$$\hat{f}_t(y) \ge f_t(y)$$
Furthermore, no item inserted into $\mathcal{S}$ ever yields a false negative in membership queries (`contains` returns `True`).

---

## 2. Formal Proof

We proceed by mathematical induction on the stream step $t$.

### Base Case ($t = 0$)
Before any insertions, $\forall y, f_0(y) = 0$, $T[j, k] = 0$, and stash $E = \emptyset$.  
$\hat{f}_0(y) = 0 \ge f_0(y)$. The base case holds trivially.

### Inductive Hypothesis
Assume that at step $t-1$, $\forall y, \hat{f}_{t-1}(y) \ge f_{t-1}(y)$.

### Inductive Step (Step $t$, arriving item $x_t = x$)
At step $t$, $f_t(x) = f_{t-1}(x) + 1$, and for all $y \ne x$, $f_t(y) = f_{t-1}(y)$.

We examine all possible execution branches:

#### Branch A: Item $x$ is already present in Stash $E$
The stash increments the exact counter:
$$c_{exact}'(x) = c_{exact}(x) + 1$$
The estimate returned for $x$ is:
$$\hat{f}_t(x) = c_{base}(x) + c_{exact}'(x) = c_{base}(x) + c_{exact}(x) + 1 = \hat{f}_{t-1}(x) + 1$$
By the inductive hypothesis:
$$\hat{f}_t(x) \ge f_{t-1}(x) + 1 = f_t(x)$$
For all $y \ne x$, no counters or stash entries change, so $\hat{f}_t(y) = \hat{f}_{t-1}(y) \ge f_{t-1}(y) = f_t(y)$.

#### Branch B: Item $x$ is not in Stash $E$ and $\hat{f}(x) < \tau_t$
Item $x$ is updated in matrix $T$ via Conservative Update (CU).
Let $v_{\min} = \min_{j} T[j, idx_j(x)]$.
Only rows $j$ where $T[j, idx_j(x)] = v_{\min}$ are incremented:
$$T'[j, idx_j(x)] = \min(v_{\min} + 1, \text{MAX\_VAL})$$
Since every true update of $x$ causes $v_{\min}$ to increment by at least 1 (unless saturated at $255$), and other colliding keys can only increase cell values, we have:
$$\min_j T'[j, idx_j(x)] \ge f_t(x)$$
For all $y \ne x$, either $T'[j, idx_j(y)] = T[j, idx_j(y)]$ or $T'[j, idx_j(y)] = T[j, idx_j(y)] + 1$.  
Monotonicity guarantees $\hat{f}_t(y) \ge \hat{f}_{t-1}(y) \ge f_t(y)$.

#### Branch C: Item $x$ reaches promotion threshold $\tau_t$
When $\hat{f}(x) \ge \tau_t$, $x$ is promoted to $E$:
1. If stash has free capacity ($|E| < K$):
   $x$ is inserted with $c_{base}(x) = \hat{f}_{t-1}(x) + 1$ and $c_{exact}(x) = 0$.
   Then $\hat{f}_t(x) = c_{base}(x) + 0 \ge f_t(x)$.
2. If stash is full ($|E| = K$), eviction is triggered:
   Let $e = \arg\min_{k \in E} (c_{base}(k) + c_{exact}(k))$ be the victim item with count $c_{evict} = c_{base}(e) + c_{exact}(e)$.
   
   **Write-Back Operation:**
   $$\forall j \in \{0, \dots, d-1\}, \quad T'[j, idx_j(e)] = \max\big(T[j, idx_j(e)], \; c_{evict}\big)$$
   
   - **For the evicted victim $e$:**
     In every row $j$, $T'[j, idx_j(e)] \ge c_{evict} \ge f_t(e)$.
     Therefore:
     $$\hat{f}_t(e) = \min_j T'[j, idx_j(e)] \ge c_{evict} \ge f_t(e)$$
     No underestimation occurs for victim $e$.
   
   - **For all other items $y \ne e$:**
     In every row $j$, the counter value satisfies:
     $$T'[j, k] = \max(T[j, k], \dots) \ge T[j, k]$$
     Because the $\max()$ operator is monotonic non-decreasing, no cell in $T$ can decrease in value:
     $$T'[j, k] \ge T[j, k], \quad \forall j, k$$
     Consequently, for all $y$:
     $$\hat{f}_t(y) = \min_j T'[j, idx_j(y)] \ge \min_j T[j, idx_j(y)] = \hat{f}_{t-1}(y) \ge f_t(y)$$
   
   - **For promoted item $x$:**
     Inserted with $c_{base}(x) = \hat{f}_{t-1}(x) + 1 \ge f_t(x)$, $c_{exact}(x) = 0$.

#### Branch D: Online Adaptive Controller modifies $\tau_t \to \tau_{t+1}$
The controller updates the promotion threshold $\tau$ at epoch boundaries.
Modifying $\tau$ only shifts the gate condition for future promotions in Step C.
It does not mutate any existing matrix counter $T[j, k]$ or stash entry $(c_{base}, c_{exact})$.
Therefore, $\hat{f}_t(y)$ is identical immediately before and after the $\tau$ adjustment:
$$\hat{f}_{t^+}(y) = \hat{f}_t(y) \ge f_t(y)$$

By mathematical induction, the invariant $\hat{f}_t(y) \ge f_t(y)$ holds for all $y \in \mathcal{S}$ and all $t \ge 0$. $\blacksquare$

---

## 3. Analysis of the Flawed Additive Draft Rule

In earlier literature drafts, write-back was erroneously formulated as:
$$T[j, idx_j(e)] \leftarrow T[j, idx_j(e)] + c_{evict} \quad \text{[FLAWED]}$$

### Failure Mechanism:
Prior to promotion, the cells $T[j, idx_j(e)]$ had already accumulated $c_{base} \ge \tau$.
Adding $c_{evict} = c_{base} + c_{exact}$ resulted in:
$$T[j, idx_j(e)] \approx c_{base} + (c_{base} + c_{exact}) = 2 c_{base} + c_{exact}$$
This caused catastrophic double-counting of baseline volume, inflating estimates by up to $+100\%$.

Conversely, a naive overwrite rule:
$$T[j, idx_j(e)] \leftarrow c_{evict} \quad \text{[FLAWED]}$$
violates the invariant whenever a colliding item $z$ had a higher counter in that cell ($T[j, k] > c_{evict}$), resulting in $T'[j, k] < T[j, k]$ and causing an illegal **underestimate** for $z$.

**Conclusion:** The $\max()$ write-back rule is both necessary and sufficient for zero-underestimation invariance.

---

## 4. Counterexample Under Narrow 8-bit Counters & The Sizing Fix

### 4.1 The Counterexample
Consider an 8-bit saturating counter matrix ($T[j, k] \in [0, 255]$) coupled with a small stash of capacity $K = 16$.
Suppose the stream $\mathcal{S}$ exhibits Zipfian skew where $M = 40$ distinct items achieve true frequency $f(x) \ge 256$.
Since the stash capacity $K = 16 < 40$, at least $40 - 16 = 24$ heavy items cannot reside in the stash.
When updates for these items hash to matrix cells, the 8-bit counters increment until reaching $255$.
Subsequent updates for these items are clipped by saturation arithmetic:
$$\hat{f}(x) = 255 < f(x)$$
resulting in an underestimate!

### 4.2 The Architectural Fix (AdaLog-Planner Sizing & Sticky Retention)
To guarantee zero underestimation in 8-bit deployments:
1. **AdaLog-Planner Sizing Guarantee (N1):**  
   The planner calculates the expected heavy hitter count from the Zipfian skew model:
   $$K_{\text{sat}} = \left\{ i \in [1, n] : N \cdot \frac{i^{-\alpha}}{H_{n, \alpha}} \ge 255 \right\}$$
   AdaLog-Planner configures $K \ge K_{\text{sat}}$ so that every item capable of saturating an 8-bit cell is promoted to and retained within the stash.
2. **Sticky Elephant Retention Rule:**  
   If an item in the stash accumulates $c \ge 255$, it is marked non-evictable into an 8-bit matrix, ensuring $c_{evict}$ never suffers truncation.
3. **16-bit / 32-bit Dynamic Elevation:**  
   For streams exceeding $10^7$ updates where $K_{\text{sat}}$ exceeds available SRAM, AdaLog-Planner automatically transitions the matrix to 16-bit counters ($[0, 65535]$).
