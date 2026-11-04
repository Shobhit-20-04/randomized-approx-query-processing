# Datasets & Stream Workload Generators

This directory documents the streaming datasets, synthetic traffic generators, and trace loaders used in AdaLog-Sketch evaluations.

---

## 1. Synthetic Stream Workloads (`experiments/datasets.py`)

- **Zipfian Power-Law Streams:**
  - Evaluated across skew parameters $\alpha \in [1.05, 1.50]$ (default $\alpha = 1.25$).
  - Universe sizes: $|\mathcal{U}| = 100,000$ distinct keys.
  - Stream volumes: $N = 300,000$ (memory/skew sweeps) to $N = 1,000,000$ (C++ throughput).
  - Seed-controlled: 10 independent random seeds (42 to 51) for computing 95% confidence intervals.

- **Uniform Random Streams:**
  - Adversarial uniform traffic ($\alpha \to 0$) used to evaluate worst-case behavior with no heavy hitters ($|E| \to 0$).

---

## 2. Real-World Datasets (`experiments/exp9_real_dataset.py`)

- **CAIDA Anonymized Internet Traces (2016):**
  - High-speed passive network packet headers from Equinix Chicago/San Jose backbone monitors.
  - Stream keys: 5-tuple flow identifiers (Source IP, Destination IP, Source Port, Destination Port, Protocol).
  - Traffic characteristics: Extreme heavy-tailed flow distribution ($\alpha \approx 1.28$). Top 100 flows represent $> 40\%$ of byte volume.

- **Project Gutenberg Text Corpora:**
  - Aggregated English literary works tokenized into individual word frequency streams.
  - Traffic characteristics: Natural language Zipfian distribution ($\alpha \approx 1.08$), $N = 300,000$ tokens, distinct vocabulary $|\mathcal{U}_{obs}| \approx 38,400$ words.
