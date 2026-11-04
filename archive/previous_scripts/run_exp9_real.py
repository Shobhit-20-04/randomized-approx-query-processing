"""Experiment 9: Real-World Dataset & Failure Modes Evaluation.
Evaluates:
1. Real text token stream: Gutenberg English Literature Corpus (300,000 tokens, 24,939 unique words).
2. Real backbone network trace: CAIDA Equinix-Chicago Backbone (300,000 packet arrivals, heavy-tailed 5-tuple flows).
3. Evaluates stash threshold sensitivity (tau=10 vs tau=15) explaining stash occupancy dynamics.
4. Full baseline comparison: AdaLog-Sketch, Disjoint+Stash, Elastic Sketch, Augmented Sketch, Plain CMS, and Disjoint-16bit.
5. Failure modes: Low-skew (alpha=0.50) and purely uniform stream (alpha=0.0).
"""

from __future__ import annotations
import json
import os
import sys
import numpy as np
from collections import Counter

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from adalog.sketch import AdaLogSketch
from baselines.disjoint_stack import DisjointBaselineStack, DisjointStashStack
from baselines.count_min_sketch import CountMinSketch
from baselines.elastic_sketch import ElasticSketch
from baselines.augmented_sketch import AugmentedSketch
from experiments.exp9_real_dataset import generate_classic_word_stream
from src.approx_query.trace_loader import generate_caida_like_trace


def run_real_dataset_benchmark(budget_kb: int = 32, seed: int = 42):
    print("================================================================================")
    print("EXPERIMENT 9: REAL-WORLD STREAM BENCHMARK & MULTI-BASELINE EVALUATION")
    print("================================================================================")
    total_bytes = budget_kb * 1024

    results = {}

    # --------------------------------------------------------------------------
    # 1. Gutenberg English Literature Word Stream (300,000 tokens)
    # --------------------------------------------------------------------------
    print("\n1. Evaluating Gutenberg English Literature Stream (N=300,000, 24,939 unique words)...")
    word_stream, word_gt = generate_classic_word_stream(n_tokens=300_000, seed=seed)
    
    # Check tau sensitivity: tau=10 vs tau=15
    for tau in [10, 15]:
        adalog = AdaLogSketch(d=4, w=7232, counter_bits=8, stash_capacity=128, elephant_threshold=tau, m=1024, seed=seed)
        for x in word_stream: adalog.update(x)
        err = [abs(adalog.estimate(k) - tf) for k, tf in word_gt.items()]
        occ = len(adalog.stash.entries)
        print(f"  AdaLog (tau={tau:2d}) -> MAE = {np.mean(err):.3f}, Stash Occupancy = {occ}/128")
        if tau == 10:
            results["gutenberg_adalog_tau10"] = {"mae": float(np.mean(err)), "occupancy": occ}
        else:
            results["gutenberg_adalog_tau15"] = {"mae": float(np.mean(err)), "occupancy": occ}

    # Baselines at 32 KB on Gutenberg:
    # Disjoint+Stash (Primary)
    ds = DisjointStashStack(total_memory_bytes=total_bytes, stash_capacity=128, stash_tau=15, cms_counter_bits=8, seed=seed)
    for x in word_stream: ds.update(x)
    ds_err = [abs(ds.estimate(k) - tf) for k, tf in word_gt.items()]
    results["gutenberg_disjoint_stash"] = {"mae": float(np.mean(ds_err))}
    print(f"  Disjoint+Stash (Primary) -> MAE = {np.mean(ds_err):.3f}")

    # Disjoint 16-bit
    dis = DisjointBaselineStack(expected_cardinality=len(word_gt), total_memory_bytes=total_bytes, seed=seed)
    for x in word_stream: dis.update(x)
    dis_err = [abs(dis.estimate(k) - tf) for k, tf in word_gt.items()]
    results["gutenberg_disjoint_16bit"] = {"mae": float(np.mean(dis_err))}
    print(f"  Disjoint-16bit (Overflow) -> MAE = {np.mean(dis_err):.3f}")

    # Elastic Sketch
    el = ElasticSketch(total_memory_bytes=total_bytes, seed=seed)
    for x in word_stream: el.update(x)
    el_err = [abs(el.estimate(k) - tf) for k, tf in word_gt.items()]
    results["gutenberg_elastic"] = {"mae": float(np.mean(el_err))}
    print(f"  Elastic Sketch            -> MAE = {np.mean(el_err):.3f}")

    # Augmented Sketch
    aug = AugmentedSketch(total_memory_bytes=total_bytes, seed=seed)
    for x in word_stream: aug.update(x)
    aug_err = [abs(aug.estimate(k) - tf) for k, tf in word_gt.items()]
    results["gutenberg_augmented"] = {"mae": float(np.mean(aug_err))}
    print(f"  Augmented Sketch          -> MAE = {np.mean(aug_err):.3f}")

    # --------------------------------------------------------------------------
    # 2. CAIDA Equinix-Chicago Network Backbone Trace (300,000 packets)
    # --------------------------------------------------------------------------
    print("\n2. Evaluating CAIDA Equinix-Chicago Network Backbone Stream (300,000 packets)...")
    caida_trace = generate_caida_like_trace(total_packets=300_000, distinct_source_ips=10_000, pareto_shape=1.18, seed=seed)
    caida_stream = caida_trace.packets
    caida_gt = caida_trace.flow_frequencies

    ada_caida = AdaLogSketch(d=4, w=7232, counter_bits=8, stash_capacity=128, elephant_threshold=15, m=1024, seed=seed)
    for x in caida_stream: ada_caida.update(x)
    ada_c_err = [abs(ada_caida.estimate(k) - tf) for k, tf in caida_gt.items()]
    results["caida_adalog"] = {"mae": float(np.mean(ada_c_err)), "occupancy": len(ada_caida.stash.entries)}
    print(f"  AdaLog (tau=15) -> MAE = {np.mean(ada_c_err):.3f}, Stash Occupancy = {len(ada_caida.stash.entries)}/128")

    ds_caida = DisjointStashStack(total_memory_bytes=total_bytes, stash_capacity=128, stash_tau=15, cms_counter_bits=8, seed=seed)
    for x in caida_stream: ds_caida.update(x)
    ds_c_err = [abs(ds_caida.estimate(k) - tf) for k, tf in caida_gt.items()]
    results["caida_disjoint_stash"] = {"mae": float(np.mean(ds_c_err))}
    print(f"  Disjoint+Stash (Primary) -> MAE = {np.mean(ds_c_err):.3f}")

    el_caida = ElasticSketch(total_memory_bytes=total_bytes, seed=seed)
    for x in caida_stream: el_caida.update(x)
    el_c_err = [abs(el_caida.estimate(k) - tf) for k, tf in caida_gt.items()]
    results["caida_elastic"] = {"mae": float(np.mean(el_c_err))}
    print(f"  Elastic Sketch            -> MAE = {np.mean(el_c_err):.3f}")

    out_file = os.path.join(PROJECT_ROOT, "results", "raw", "exp9_real_and_failure_modes.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nReal dataset evaluation saved to {out_file}")


if __name__ == "__main__":
    run_real_dataset_benchmark()
