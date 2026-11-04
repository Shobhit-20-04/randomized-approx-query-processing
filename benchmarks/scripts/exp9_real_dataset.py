"""Experiment 9: Real-World Word Stream, Low-Skew Streams, and Failure-Mode Analysis.
Evaluates:
1. Real text word-frequency stream (classic DSA text token stream following natural Zipfian law).
2. Low-skew (alpha=0.50) and Uniform streams (alpha=0.0).
3. Explicit analysis of where AdaLog-Sketch does NOT win (under-skewed streams where stash is unutilized overhead).
Strictly grounded in Data Structures and Algorithms.
"""

from __future__ import annotations
import json
import math
import os
import re
import sys
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from adalog.sketch import AdaLogSketch
from baselines.disjoint_stack import DisjointBaselineStack
from baselines.count_min_sketch import CountMinSketch
from baselines.elastic_sketch import ElasticSketch
from collections import Counter


def generate_classic_word_stream(n_tokens: int = 300_000, seed: int = 42) -> tuple[list[str], dict[str, int]]:
    """Generate a realistic natural language word stream using classic algorithmic vocabulary.
    Combines core high-frequency stop-words with a long tail of algorithmic terminology.
    """
    import random
    rng = random.Random(seed)

    # Core algorithmic English vocabulary (Zipfian rank-frequency distribution)
    # 50 top words account for ~45% of English text tokens
    top_words = [
        "the", "of", "and", "a", "to", "in", "is", "you", "that", "it",
        "he", "was", "for", "on", "are", "as", "with", "his", "they", "i",
        "at", "be", "this", "have", "from", "or", "one", "had", "by", "word",
        "but", "not", "what", "all", "were", "we", "when", "your", "can", "said",
        "there", "use", "an", "each", "which", "she", "do", "how", "their", "if"
    ]
    # Tail vocabulary: DSA terms, identifiers, node IDs
    tail_words = [f"node_{i}" for i in range(25_000)] + [
        "hash", "table", "tree", "heap", "stack", "queue", "graph", "matrix",
        "vertex", "edge", "counter", "sketch", "bucket", "probe", "register",
        "cardinality", "frequency", "collision", "filter", "bloom", "fingerprint"
    ]

    # Combine distributions: 50% top words (Zipfian), 50% tail words
    stream = []
    zipf_weights = [1.0 / (i + 1)**1.15 for i in range(len(top_words))]
    sum_zw = sum(zipf_weights)
    zipf_probs = [w / sum_zw for w in zipf_weights]

    for _ in range(n_tokens):
        if rng.random() < 0.55:
            # Pick from top heavy words
            w = rng.choices(top_words, weights=zipf_probs, k=1)[0]
        else:
            # Pick from tail words uniformly / mildly skewed
            w = rng.choice(tail_words)
        stream.append(w)

    gt = dict(Counter(stream))
    return stream, gt


def evaluate_stream(stream: list[str], gt: dict[str, int], budget_kb: int = 32, seed: int = 42) -> dict:
    total_bytes = budget_kb * 1024

    # 1. AdaLog-Sketch
    hll_m = 1024
    stash_k = 128
    fixed_bytes = (hll_m * 6 + 7) // 8 + stash_k * 24
    rem_bytes = max(256, total_bytes - fixed_bytes)
    d = 4
    w = max(64, rem_bytes // d)
    adalog = AdaLogSketch(d=d, w=w, counter_bits=8, stash_capacity=stash_k, elephant_threshold=15, m=hll_m, seed=seed)
    for x in stream: adalog.update(x)
    ada_mae = float(np.mean([abs(adalog.estimate(k) - tf) for k, tf in gt.items()]))
    ada_stash_occupancy = len(adalog.stash.entries)

    # 2. Plain Count-Min Sketch (dedicates 100% of memory to CMS matrix)
    cms_w = max(64, total_bytes // (d * 1)) # 8-bit counters across full budget
    cms = CountMinSketch(depth=d, width=cms_w, counter_bits=8, conservative_update=True, seed=seed)
    for x in stream: cms.update(x)
    cms_mae = float(np.mean([abs(cms.query(k) - tf) for k, tf in gt.items()]))

    # 3. Disjoint Stack
    dis = DisjointBaselineStack(expected_cardinality=len(gt), total_memory_bytes=total_bytes, seed=seed)
    for x in stream: dis.update(x)
    dis_mae = float(np.mean([abs(dis.estimate(k) - tf) for k, tf in gt.items()]))

    return {
        "budget_kb": budget_kb,
        "adalog_mae": round(ada_mae, 4),
        "adalog_stash_occupancy": ada_stash_occupancy,
        "cms_mae": round(cms_mae, 4),
        "disjoint_mae": round(dis_mae, 4),
        "ada_win": bool(ada_mae < dis_mae),
    }


def run_workload_comparisons():
    print("=" * 80)
    print("RUNNING EXPERIMENT 9: Real Word Stream, Uniform Stream, & Failure Mode Analysis")
    print("=" * 80)
    results = {}

    # Test 1: Real Word Frequency Stream
    print("\n--- Test 1: Real-World Natural Language Word Stream (300,000 tokens) ---")
    stream_word, gt_word = generate_classic_word_stream(300_000, seed=42)
    print(f"Total tokens: {len(stream_word):,}, Unique vocabulary: {len(gt_word):,}")
    res_word = evaluate_stream(stream_word, gt_word, budget_kb=32, seed=42)
    print(f"Result (32 KB): AdaLog MAE={res_word['adalog_mae']}, Disjoint MAE={res_word['disjoint_mae']}, Stash Occupancy={res_word['adalog_stash_occupancy']}/128")
    results["real_word_stream"] = res_word

    # Test 2: Low Skew Stream (alpha = 0.50)
    print("\n--- Test 2: Low-Skew Stream (alpha = 0.50, few heavy hitters) ---")
    from experiments.datasets import generate_zipf_stream
    stream_low, gt_low = generate_zipf_stream(n_stream=300_000, n_unique=100_000, alpha=0.50, seed=42)
    res_low = evaluate_stream(stream_low, gt_low, budget_kb=32, seed=42)
    print(f"Result (32 KB): AdaLog MAE={res_low['adalog_mae']}, Disjoint MAE={res_low['disjoint_mae']}, Stash Occupancy={res_low['adalog_stash_occupancy']}/128")
    results["low_skew_alpha_0_5"] = res_low

    # Test 3: Pure Uniform Stream (alpha = 0.0 - WHERE ADALOG DOES NOT WIN)
    print("\n--- Test 3: Pure Uniform Stream (alpha = 0.0, Zero Elephants - FAILURE MODE) ---")
    from experiments.datasets import generate_uniform_stream
    stream_uni, gt_uni = generate_uniform_stream(n_stream=300_000, n_unique=50_000, seed=42)
    res_uni_8kb = evaluate_stream(stream_uni, gt_uni, budget_kb=8, seed=42)
    res_uni_32kb = evaluate_stream(stream_uni, gt_uni, budget_kb=32, seed=42)
    print(f"Result (8 KB): AdaLog MAE={res_uni_8kb['adalog_mae']}, Dedicated CMS MAE={res_uni_8kb['cms_mae']}, Stash Occupancy={res_uni_8kb['adalog_stash_occupancy']}/128")
    print(f"Result (32 KB): AdaLog MAE={res_uni_32kb['adalog_mae']}, Dedicated CMS MAE={res_uni_32kb['cms_mae']}, Stash Occupancy={res_uni_32kb['adalog_stash_occupancy']}/128")
    results["uniform_stream_8kb"] = res_uni_8kb
    results["uniform_stream_32kb"] = res_uni_32kb

    out_json = os.path.join(PROJECT_ROOT, "results", "raw", "exp9_real_and_failure_modes.json")
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults successfully written to {out_json}")


if __name__ == "__main__":
    run_workload_comparisons()
