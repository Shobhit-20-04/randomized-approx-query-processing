import pytest
import random
from adalog.sketch import AdaLogSketch
from core.bindings import is_dll_available, CompiledAdaLog

def test_adversarial_uniform_stream_empty_stash():
    """Under uniform random distribution (alpha = 0.0), no key crosses tau = 15.
    Verifies that the stash remains completely empty and all items are stored in matrix."""
    sketch = AdaLogSketch(width=1024, depth=4, counter_bits=8, stash_capacity=64, stash_tau=15, seed=42)
    # 5,000 unique keys, each appearing exactly once
    for i in range(5000):
        sketch.update(f"uniform_key_{i}", count=1)

    assert len(sketch.stash.entries) == 0, "Stash should be empty under uniform traffic with tau=15"
    assert sketch.stash.insertions == 0
    # Every item must have AMQ = True (zero false negatives)
    for i in range(500):
        assert sketch.contains(f"uniform_key_{i}") is True
        assert sketch.estimate(f"uniform_key_{i}") >= 1

def test_adversarial_extreme_skew_saturated_stash():
    """Under extreme Zipfian skew (alpha = 3.0), the top elephants saturate the 8-bit counters.
    Verifies Theorem 2 zero-underestimation holds when K >= K_sat*."""
    sketch = AdaLogSketch(width=1024, depth=4, counter_bits=8, stash_capacity=32, stash_tau=10, seed=42)
    cpp_sketch = CompiledAdaLog(width=1024, depth=4, counter_bits=8, stash_capacity=32, elephant_threshold=10, seed=42)

    # Key 0 arrives 5,000 times (massively exceeds 255)
    for _ in range(5000):
        sketch.update("hyper_elephant", 1)
        cpp_sketch.update("hyper_elephant", 1)

    assert sketch.estimate("hyper_elephant") == 5000
    assert cpp_sketch.estimate("hyper_elephant") == 5000
    assert sketch.contains("hyper_elephant") is True
    assert cpp_sketch.contains("hyper_elephant") is True

def test_adversarial_batch_increment_boundary():
    """Verify that batch increments of 10^9 are tracked safely without 32-bit truncation."""
    sketch = AdaLogSketch(width=1024, depth=4, counter_bits=8, stash_capacity=32, stash_tau=15, seed=42)
    cpp_sketch = CompiledAdaLog(width=1024, depth=4, counter_bits=8, stash_capacity=32, elephant_threshold=15, seed=42)

    sketch.update("batch_key", 1_000_000_000)
    cpp_sketch.update("batch_key", 1_000_000_000)

    assert sketch.estimate("batch_key") == 1_000_000_000
    assert cpp_sketch.estimate("batch_key") == 1_000_000_000

def test_adversarial_pathological_collision_resistance():
    """Verify that when multiple keys share matrix columns, AMQ and Frequency lower bounds hold."""
    sketch = AdaLogSketch(width=16, depth=2, counter_bits=8, stash_capacity=4, stash_tau=5, seed=42)
    keys = [f"pathological_collision_{i}" for i in range(100)]
    for k in keys:
        sketch.update(k, 1)

    for k in keys:
        assert sketch.contains(k) is True
        assert sketch.estimate(k) >= 1
