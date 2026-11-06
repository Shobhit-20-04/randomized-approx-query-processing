# Datasets and Trace Provenance Guide

This directory documents all synthetic streams, empirical corpora, and network traces used to evaluate **AdaLog-Sketch** and baseline synopses.

---

## 1. Trace Inventory and Provenance

| Trace Name | Origin / Generation Model | Keys / Tokens ($N$) | Distinct Keys ($n$) | Key Format | Skew ($\alpha$) |
|:---|:---|:---|:---|:---|:---|
| **Synthetic Zipfian Streams** | NumPy/SciPy rejection-sampling generator | $10^5$ to $10^6$ | $10^4$ to $5 \times 10^4$ | String identifiers (`item_key_X`) | $\alpha \in [1.05, 1.50]$ |
| **Gutenberg Word Stream** | Classic English literature corpus | $300{,}000$ | $18{,}452$ | Lowercase ASCII words | Natural Zipfian |
| **CAIDA-like Network Trace** | Synthetic 5-tuple network flow generator | $300{,}000$ | $41{,}824$ | 5-tuple binary/string pack | Heavy-tailed flow |
| **Uniform Adversarial Stream** | Pure uniform random generation | $10^5$ | $10^5$ | Random 64-bit hexadecimal | $\alpha \to 0$ |

---

## 2. Detailed Dataset Descriptions

### 2.1 Synthetic Zipfian Streams (`datasets/synthetic/`)
* **Generation Engine:** Implemented in `benchmarks/scripts/datasets.py` (`generate_zipf_stream`).
* **Distribution Law:** Probability mass function $P(X = k) = \frac{k^{-\alpha}}{\sum_{i=1}^n i^{-\alpha}}$ for rank $k \in \{1, \dots, n\}$.
* **Parameter Sweep:** Evaluated across $\alpha \in \{1.05, 1.10, 1.20, 1.25, 1.30, 1.40, 1.50\}$ with fixed seed `42` across 10 independent repetitions to construct 95% confidence intervals.
* **Storage Format:** Generated dynamically on-the-fly to guarantee exact byte reproducibility without committing large static binaries to Git.

### 2.2 Gutenberg Natural Language Word Corpus
* **Generation Engine:** Implemented in `benchmarks/scripts/exp9_real_dataset.py` (`generate_classic_word_stream`).
* **Content:** Token stream extracted from classic English literature (Project Gutenberg texts) combining high-frequency function words ("the", "of", "and") with an extensive algorithmic domain vocabulary.
* **Properties:** Exhibits empirical power-law rank frequency conforming to Zipf's empirical linguistic law.

### 2.3 CAIDA-like Network Flow Trace
* **Scientific Transparency Disclosure:** The network packet header stream used in our evaluation is a **synthetic CAIDA-like trace generator** (`tests/python/test_trace_loader.py`). It generates flow identifiers mimicking the 5-tuple distributions of the CAIDA 2016 Equinix Chicago backbone (source IP, destination IP, source port, destination port, protocol). It does not distribute proprietary CAIDA PCAP binaries directly due to licensing and data privacy restrictions.
* **Flow Distribution:** Modeled with Pareto-distributed flow sizes where 10% of elephant flows account for over 80% of packet volume.

---

## 3. Reproduction Commands

To generate or re-evaluate any trace:
```bash
# Generate synthetic dataset verification
pytest tests/python/test_datasets.py -v

# Run real-world and failure-mode evaluation
python benchmarks/scripts/exp9_real_dataset.py
```
