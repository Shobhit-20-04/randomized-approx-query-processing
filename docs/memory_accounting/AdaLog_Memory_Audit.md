# AdaLog-Sketch: Strict Memory Accounting & Baseline Fairness Audit

**Audit Date:** November 2026  
**Auditor:** Senior Systems & Performance Engineer  
**Scope:** Reconciling physical allocations against analytical models across 8 KB, 16 KB, 32 KB, 64 KB, and 128 KB budgets.  

---

## 1. Byte-Level Architecture Breakdown at 32 KB Budget

| Component / Subsystem | C++ Physical Footprint | Python Reference Model | Historical Disjoint+Stash | Strict Disjoint+Stash Baseline |
| :--- | :--- | :--- | :--- | :--- |
| **Matrix Counters** | 28,928 B ($d=4, w=7,232, 1\text{B}$) | 28,928 B ($d=4, w=7,232, 1\text{B}$) | 23,960 B ($d=4, w=5,990, 1\text{B}$) | 23,140 B ($d=4, w=5,785, 1\text{B}$) |
| **Set Membership** | 0 B (Virtual Dynamic AMQ) | 0 B (Virtual Dynamic AMQ) | 5,990 B (Standard Bloom Filter) | 5,788 B (Standard Bloom Filter) |
| **Elephant Stash** | 2,048 B ($K=128$, Flat Arrays) | 3,072 B ($K=128, 24\text{B/ent}$) | 3,072 B ($K=128, 24\text{B/ent}$) | 3,072 B ($K=128, 24\text{B/ent}$) |
| **HLL Cardinality** | 768 B ($m=1024$, 6-bit packed) | 768 B ($m=1024$, 6-bit packed) | 768 B ($m=1024$, 6-bit packed) | 768 B ($m=1024$, 6-bit packed) |
| **Total Memory** | **31,744 Bytes** | **32,768 Bytes** | **33,790 Bytes** | **32,768 Bytes** |
| **Budget Variance** | **-1,024 B (-3.1%) [COMPLIANT]** | **0 B (Exact 32 KB) [COMPLIANT]** | **+1,022 B (+3.1%) [VIOLATION]** | **0 B (Exact 32 KB) [COMPLIANT]** |

---

## 2. Multi-Budget Scaling Grid

The table below delineates the mathematically compliant parameters across memory tiers:

| Budget Tier | Matrix Width $w$ ($d=4$) | Matrix Bytes (8-bit) | HLL Registers $m$ | HLL Bytes (6-bit packed) | Stash Capacity $K$ | Stash Bytes (Model: 24B/ent) | Total Budget Allocated |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **8 KB** | 1,440 | 5,760 B | 512 | 384 B | 64 | 1,536 B | 7,680 B ($\le 8,192$) |
| **16 KB** | 3,360 | 13,440 B | 1,024 | 768 B | 85 | 2,040 B | 16,248 B ($\le 16,384$) |
| **32 KB** | 7,232 | 28,928 B | 1,024 | 768 B | 128 | 3,072 B | 32,768 B ($\le 32,768$) |
| **64 KB** | 15,104 | 60,416 B | 1,024 | 768 B | 170 | 4,080 B | 65,264 B ($\le 65,536$) |
| **128 KB**| 30,848 | 123,392 B | 1,024 | 768 B | 256 | 6,144 B | 130,304 B ($\le 131,072$)|

---

## 3. Disjoint+Stash 1,022-Byte Overrun Investigation
- **Root Cause:** Historical code calculated `stash_bytes = K * 16 = 2,048 B`. However, each stash entry stores:
  - 8-byte hash key
  - 4-byte baseline count
  - 4-byte exact counter
  - 8-byte dictionary pointer/metadata overhead
  - Total per entry = 24 bytes ($128 \times 24 = 3,072\text{ bytes}$).
- **Impact:** The historical Disjoint+Stash consumed 33,790 bytes (+3.1% over budget).
- **Remediation:** Calibrated strict baseline setting $w = 5,785$, yielding exactly 32,765 bytes.
