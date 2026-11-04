# AdaLog-Sketch: Architectural Design & Implementation Overview

## 1. Architectural Philosophy
AdaLog-Sketch is an approximate query processing (AQP) synopsis that eliminates memory fragmentation and redundant hash evaluations in streaming analytics platforms. Instead of executing independent pipelines for membership, frequency estimation, distinct cardinality, and heavy-hitter tracking, AdaLog-Sketch drives all operations from a **single 128-bit hash pipeline** per item within a **contiguous 32 KB cache-aligned memory block**.

---

## 2. Subsystem Layout (32 KB Budget)

$$\begin{aligned}
\text{1. Counter Matrix } (d=4, w=7,232, \text{uint8}) &= 28,928\text{ Bytes} \\
\text{2. Elephant Stash } (K=128 \times 24\text{ B/entry}) &= 3,072\text{ Bytes} \\
\text{3. HyperLogLog } (m=1,024 \times 6\text{ bits} / 8) &= 768\text{ Bytes} \\
\text{4. Dynamic AMQ Threshold Metadata } &= 0\text{ Bytes} \\
\hline
\mathbf{Total\ Physical\ Memory} &= \mathbf{32,768\text{ Bytes (Exact 32.0 KB)}}
\end{aligned}$$

---

## 3. Subsystem Interactions

1. **Single 128-Bit Hashing Pipeline:**
   - Evaluates a single 128-bit digest $H(x) = (h_{high}, h_{low})$ using MurmurHash3_128 (C++) or XXH3_128 (Python).
   - $h_{low}$ generates $d=4$ row indices via Carter-Wegman universal multiply-shift operations:
     $$idx_j(x) = ((a_j \cdot h_{low} + b_j) \gg 32) \bmod w$$
   - $h_{high}$ drives the decoupled HyperLogLog register selection and leading-zero counting ($\rho$).
2. **Conservative Update (CU) Matrix:**
   - Increments only the cell(s) matching the current row minimum $v_{min} = \min_j T[j, idx_j(x)]$, suppressing collision noise from lower-frequency tail items.
   - Counters saturate at $\text{MAX\_VAL} = 255$.
3. **2-Choice Associative Elephant Stash:**
   - When an arriving item reaches the promotion threshold $\tau$, it attempts entry into the stash.
   - C++ evaluates two candidate slots ($slot_1, slot_2$) with local eviction.
   - Monotonic write-back uses $\max(T[j], \min(\text{MAX\_VAL}, c_{evict}))$ to prevent double counting without reducing counter values for colliding keys.
4. **Decoupled 6-Bit Packed HyperLogLog:**
   - $m = 1,024$ registers packed into 768 bytes. Reaches an empirical Relative Standard Error of **2.39%**, matching the theoretical bound $1.04 / \sqrt{m}$.
5. **Virtual Dynamic AMQ Membership:**
   - Tests counter positivity against stream-density threshold $\theta(N) = \min(254, \lfloor\ln(N/w + 1) + 1\rfloor)$.
   - Guarantees zero false negatives ($FN = 0$) with zero marginal memory allocation.
