# AdaLog-Sketch: Algorithmic Auditing & C++/Python Implementation Corrections

**Audit Date:** November 2026  
**Auditor:** Senior Systems Engineer & Algorithm Reviewer  
**Scope:** Algorithm 1 specification (Sequence A), Conservative Update interactions, 95-bit fingerprint stash layout (24B zero-padding), dynamic stash capacity, and native $O(K \log k)$ top-k query support.  

---

## 1. Audited Algorithm 1 Specification (Sequence A Promotion Order)

The stream update workflow strictly enforces **Sequence A** promotion: qualifying heavy keys ($v_{\min} + c \ge \tau$) enter the stash immediately, bypassing the counter matrix to shield narrow 8-bit cells from heavy-hitter inflation:

```
Algorithm 1: Audited AdaLog-Sketch Stream Ingestion (Sequence A)
Input: Key x, Increment c >= 1, Stash E (capacity K), Counter Matrix T[d x w], HLL Registers M[m], Threshold tau (default 15), Max Counter C_max (255)
Output: Void (In-place sketch state update)

1:  (h1, h2) <- Hash128(x)
2:  reg_idx <- (h2 >> 54) & (m - 1)
3:  rho <- min(54, clz64(h2 << 10)) + 1
4:  M[reg_idx] <- max(M[reg_idx], rho)          // Decoupled 6-bit HLL update
5:  tag <- (h2 & 0x7FFFFFFF)                    // 31-bit secondary tag (MSB dedicated to occupancy)
6:  if (h1, tag) in E then                      // Stash hit: exact 64-bit counter tracking
7:      E[(h1, tag)].exact_count <- E[(h1, tag)].exact_count + c
8:      return
9:  end if
10: for j <- 0 to d - 1 do                      // Kirsch-Mitzenmacher 64-bit row indexing
11:     idx_j <- (h1_low + j * h1_high) mod w
12: end for
13: v_min <- min(T[0, idx_0], ..., T[d-1, idx_{d-1}])
14: if v_min + c >= tau then                    // Sequence A: Stash admission check
15:     if |E| < K then
16:         Insert ((h1, tag), v_min, c) into E
17:         return                               // Bypass matrix write
18:     else
19:         non_sat <- {y in E | y.total < C_max}
20:         if non_sat is not empty then
21:             e <- argmin_{y in non_sat} y.total
22:             if v_min + c > e.total then
23:                 Monotonic_Write_Back(T, e)   // Lossless monotonic write-back
24:                 Replace e with ((h1, tag), v_min, c) in E
25:                 return                       // Bypass matrix write
26:             end if
27:         end if
28:     end if
29: end if
30: v_target <- min(C_max, v_min + c)           // Sequence A Fallback: Matrix Conservative Update
31: for j <- 0 to d - 1 do
32:     if T[j, idx_j] < v_target then
33:         T[j, idx_j] <- v_target
34:     end if
35: end for
```

---

## 2. Critical Implementation Corrections Applied

### 2.1 C++ Core (`src/cpp/core/adalog_core.cpp` and `core/adalog_core.cpp`)
1. **95-Bit Composite Fingerprint & 24-Byte Zero-Padding Stash Layout:**
   - Stash entries store:
     - `uint64_t key_hash`: 8 bytes (Lane 0 primary hash $h_1$)
     - `uint32_t tag`: 4 bytes (Lane 1 secondary tag masked with `0x7FFFFFFF`; bit 31 indicates occupancy)
     - `uint32_t base_count`: 4 bytes (baseline count $v_{\min}$ captured at admission)
     - `uint64_t exact_count`: 8 bytes (64-bit exact arrival counter)
   - Total memory layout is verified at compile time: `static_assert(sizeof(StashItem) == 24)`.
   - Zero padding bytes exist.
   - Together, the 64-bit primary hash and 31-bit secondary tag form an effective **95-bit composite key fingerprint**, yielding a single-key collision probability of $1/2^{95} \approx 2.52 \times 10^{-29}$ and union bound $K N / 2^{95} \approx 3.23 \times 10^{-21}$ across $N = 10^6$ arrivals over $K = 128$ slots.
   - At $K = 128$, the stash consumes exactly $128 \times 24 = 3,072$ bytes. Synopsis total: Matrix ($28,928$ B) + HLL ($768$ B) + Stash ($3,072$ B) = **32,768 bytes (32.0 KB exact)**.

2. **Sequence A Promotion Order:**
   - Enforced Sequence A: when an incoming key qualifies for stash admission ($v_{\min} + c \ge \tau$) and is admitted (either into an empty slot or via victim eviction), the function inserts the item into the stash and **returns immediately**.
   - Matrix counter writes are bypassed for promoted items, shielding the narrow 8-bit counters from heavy-hitter pollution and preserving $O(1)$ fast-path execution.

3. **Lossless Monotonic Write-Back:**
   - When an unpromoted key evicts a resident victim $e$, the victim's total count $c_{\text{evict}} = e.c_{base} + e.c_{exact}$ is written back monotonically to its $d$ matrix cells:
     $$T[j, idx_{j,e}] \leftarrow \max(T[j, idx_{j,e}], \min(C_{\max}, c_{\text{evict}}))$$
   - This ensures $\hat{f}(e) \ge f(e)$ is preserved inductively upon eviction.

4. **Native $O(K \log k)$ Top-$k$ Extraction:**
   - Replaced full $O(K \log K)$ sorting with a size-$k$ min-heap (`std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>>`), guaranteeing optimal $O(K \log k)$ complexity.
   - Exported C API function `adalog_top_k(void* ptr, int k, uint64_t* out_hashes, uint64_t* out_counts)`.

5. **HLL Register Decoupling:**
   - Decoupled `hll_m` from matrix width $w = 7,232$. Fixed $m = 1024$ (768 bytes packed 6-bit registers), achieving fixed cardinality precision ($\mathrm{RSE} \approx 0.0239$) independent of matrix width.
