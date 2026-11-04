# AdaLog-Sketch Benchmarks & Baseline Suite

This directory contains benchmark execution scripts, baseline streaming synopses, and workload evaluation configurations for AdaLog-Sketch.

---

## 1. Directory Structure

```text
benchmarks/
├── scripts/
│   ├── exp1_memory_sweep.py         # Memory budget sweep (8 KB to 512 KB)
│   ├── exp2_skew_sweep.py           # Zipfian skew sensitivity (alpha in [1.05, 1.50])
│   ├── exp3_latency_benchmark.py    # Native C++ ingestion latency and throughput
│   ├── exp4_ablations.py            # Architectural component ablations (stash, CU, HLL)
│   ├── exp5_planner_eval.py         # Analytical joint memory planner validation
│   ├── exp6_adaptive_eval.py        # Adaptive threshold controller (negative result)
│   ├── exp7_certificates_eval.py    # Interval error certificate empirical coverage
│   ├── exp8_compression.py          # LightRanger bit-plane residual coding
│   ├── exp9_real_dataset.py         # CAIDA network backbone & Project Gutenberg traces
│   ├── plot_results.py              # Publication figure generator (Figs 1, 2, 3, 5, 8)
│   └── plot_ci_figures.py           # 95% Confidence Interval error bar figures
│
└── baselines/
    ├── count_min_sketch.py          # Count-Min Sketch with Conservative Update
    ├── bloom_filter.py              # Standard bit-array Bloom Filter
    ├── hyperloglog.py               # 6-bit packed HyperLogLog cardinality estimator
    ├── disjoint_stack.py            # Disjoint+Stash (strict 32 KB calibrated: w=5785)
    ├── elastic_sketch.py            # Elastic Sketch (Yang et al., SIGCOMM 2018)
    ├── augmented_sketch.py          # Augmented Sketch (Roy et al., SIGMOD 2016)
    ├── cuckoo_filter.py             # Cuckoo Filter (Fan et al., CoNEXT 2014)
    ├── counting_bloom_filter.py     # Counting Bloom Filter
    ├── count_sketch.py              # Classical Count-Sketch (L2 error)
    └── xor_filter.py                # Xor Filter (Graf & Lemire, 2020)
```

---

## 2. Running Benchmarks

### Quick Benchmark (Synthetic Stream Verification):
```bash
python scripts/benchmark/run_quick_benchmark.py
```

### Full Benchmark Suite (All 9 Experiments):
```bash
python scripts/benchmark/run_all.py
```

### Native C++ Core Throughput:
```bash
./core/bench_core.exe results/raw/exp3_latency_benchmark.json
```

All benchmark logs are written to `results/raw/` in structured JSON format.
