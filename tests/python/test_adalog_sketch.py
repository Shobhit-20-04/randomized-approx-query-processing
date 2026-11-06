"""
Unit test suite for AdaLog-Sketch.
Validates:
  1. Parameter checking and bounds.
  2. No-underestimation invariant.
  3. Elephant stash heavy-hitter tracking and extraction.
  4. Conservative Update (CU) noise reduction compared to standard CMS.
  5. Integrated distinct cardinality estimation.
  6. Approximate set membership (AMQ) behavior.
  7. Time-decay sliding-window behavior.
  8. LightRanger compression and lossless matrix reconstruction.
"""

import collections
import pytest
import numpy as np

from approx_query.adalog_sketch import AdaLogSketch
from approx_query.count_min_sketch import CountMinSketch


def test_adalog_sketch_invalid_parameters():
    """Verify ValueError is raised on non-positive parameters."""
    with pytest.raises(ValueError):
        AdaLogSketch(width=0)
    with pytest.raises(ValueError):
        AdaLogSketch(depth=0)
    with pytest.raises(ValueError):
        AdaLogSketch(stash_capacity=0)
    with pytest.raises(ValueError):
        AdaLogSketch(elephant_threshold=0)


def test_adalog_sketch_no_underestimation():
    """Verify estimate(x) >= true_count(x) for all items."""
    sketch = AdaLogSketch(width=256, depth=4, stash_capacity=32, elephant_threshold=5, seed=123)
    stream = ["apple"] * 20 + ["banana"] * 7 + ["cherry"] * 1 + ["date"] * 4 + ["fig"] * 12
    sketch.update_many(stream)

    true_counts = collections.Counter(stream)
    for item, true_f in true_counts.items():
        est_f = sketch.query(item)
        assert est_f >= true_f, f"Underestimation for {item}: est={est_f}, true={true_f}"


def test_adalog_sketch_elephant_stash_promotion():
    """Verify items exceeding elephant_threshold are promoted to stash."""
    sketch = AdaLogSketch(width=128, depth=4, stash_capacity=10, elephant_threshold=10, seed=42)
    # "elephant" has frequency 50 > 10
    # "mouse" has frequency 3 < 10
    sketch.update_many(["elephant"] * 50)
    sketch.update_many(["mouse"] * 3)

    assert "elephant" in sketch.elephant_stash
    assert sketch.elephant_stash["elephant"] == 50
    assert "mouse" not in sketch.elephant_stash

    heavy = sketch.heavy_hitters(min_freq=10)
    assert len(heavy) >= 1
    assert heavy[0] == ("elephant", 50)


def test_adalog_sketch_conservative_update_accuracy():
    """
    Verify AdaLogSketch with Conservative Update achieves lower MAE than
    unconstrained standard Count-Min Sketch on a skewed distribution.
    """
    np.random.seed(42)
    vocab = [f"key_{i}" for i in range(1000)]
    # Skewed Zipfian distribution
    weights = 1.0 / np.arange(1, 1001) ** 1.1
    weights /= weights.sum()
    stream = np.random.choice(vocab, size=10000, p=weights).tolist()
    true_counts = collections.Counter(stream)

    # Standard CMS with matching width & depth
    cms = CountMinSketch(epsilon=0.01, delta=0.01, width=256, depth=4, seed=42)
    cms.update_many(stream)
    cms_metrics = cms.compute_errors(true_counts)

    # AdaLogSketch
    adalog = AdaLogSketch(width=256, depth=4, stash_capacity=64, elephant_threshold=15, seed=42)
    adalog.update_many(stream)
    adalog_metrics = adalog.compute_metrics(true_counts)

    # AdaLogSketch should have significantly lower Mean Absolute Error (MAE)
    assert adalog_metrics["mae"] <= cms_metrics["mae"]
    assert adalog_metrics["underestimations"] == 0


def test_adalog_sketch_cardinality_estimation():
    """Verify integrated cardinality estimation captures distinct items within reasonable bounds."""
    sketch = AdaLogSketch(width=512, depth=4, seed=99)
    distinct_keys = [f"item_{i}" for i in range(2000)]
    sketch.update_many(distinct_keys)

    est_card = sketch.cardinality()
    rel_error = abs(est_card - 2000) / 2000
    # Expected relative error around ~1.04 / sqrt(512) ~ 4.6%, safely within 15%
    assert rel_error < 0.15, f"Cardinality error too high: est={est_card}, true=2000, rel={rel_error:.3f}"


def test_adalog_sketch_contains():
    """Verify approximate membership query behavior."""
    sketch = AdaLogSketch(width=256, depth=4, seed=42)
    sketch.update_many(["cat", "dog", "bird"])

    assert "cat" in sketch
    assert "dog" in sketch
    assert "bird" in sketch
    assert "dinosaur" not in sketch


def test_adalog_sketch_decay():
    """Verify time-decay reduces counts correctly."""
    sketch = AdaLogSketch(width=128, depth=4, stash_capacity=10, elephant_threshold=10, seed=42)
    sketch.update_many(["alpha"] * 40)
    assert sketch.query("alpha") == 40

    sketch.decay(factor=0.5)
    assert sketch.query("alpha") == 20
    assert sketch.total_volume == 20


def test_adalog_sketch_lightranger_compression():
    """Verify LightRanger compression and lossless counter matrix decompression."""
    sketch = AdaLogSketch(width=128, depth=4, seed=77)
    np.random.seed(77)
    items = [f"flow_{i % 50}" for i in np.random.randint(0, 50, size=500)]
    sketch.update_many(items)

    compressed_bytes = sketch.compress_lightranger(group_size=8)
    # Raw table bytes = 128 * 4 * 4 = 2048 bytes
    raw_size = sketch.table.nbytes
    comp_size = len(compressed_bytes)

    # Decompress
    depth, width, decompressed_table = AdaLogSketch.decompress_lightranger(compressed_bytes)

    assert depth == sketch.depth
    assert width == sketch.width
    np.testing.assert_array_equal(decompressed_table, sketch.table)
    # Compression should achieve size reduction
    assert comp_size < raw_size


def test_adalog_sketch_memory_usage():
    """Verify memory_usage_bytes returns a positive realistic byte count."""
    sketch = AdaLogSketch(width=256, depth=4, stash_capacity=64)
    mem = sketch.memory_usage_bytes()
    assert mem > 256 * 4 * 4  # Greater than raw matrix size


def test_conservative_update_batch_increment_counterexample():
    """
    Reviewer Issue 1.1: Verify Conservative Update with increment c > 1
    does NOT underestimate when cell values differ across rows.
    Counter-example: cells (5, 6, 6) updated with c = 3.
    Under naive rule, cells become (8, 6, 6), so min is 6 < 8 (underestimate).
    Under corrected rule, cells become (8, 8, 8), so min is 8 (no underestimate).
    """
    import os
    import sys
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from adalog.sketch import AdaLogSketch as ModularAdaLog
    from baselines.count_min_sketch import CountMinSketch as BaselineCMS

    # 1. Test Modular AdaLogSketch
    sketch = ModularAdaLog(w=64, d=3, counter_bits=8, use_stash=False, use_conservative_update=True, seed=42)
    # Manually configure cells for item "test_key" to (5, 6, 6)
    from adalog.hash_utils import hash128, get_matrix_indices
    h_low, _ = hash128("test_key", seed=42)
    indices = get_matrix_indices(h_low, 3, 64)
    sketch.table[0, indices[0]] = 5
    sketch.table[1, indices[1]] = 6
    sketch.table[2, indices[2]] = 6

    # Update with increment c = 3
    sketch.update("test_key", count=3)

    # All cells must be at least 5 + 3 = 8
    est = sketch.estimate("test_key")
    assert est >= 8, f"CU underestimated with c>1: est={est}, expected at least 8"
    for j in range(3):
        assert sketch.table[j, indices[j]] >= 8, f"Row {j} was not updated properly: {sketch.table[j, indices[j]]}"

    # 2. Test Baseline CountMinSketch with Conservative Update
    cms = BaselineCMS(width=64, depth=3, counter_bits=16, conservative_update=True, seed=42)
    cms_indices = cms._get_indices("test_key")
    cms.table[0, cms_indices[0]] = 5
    cms.table[1, cms_indices[1]] = 6
    cms.table[2, cms_indices[2]] = 6

    cms.update("test_key", count=3)
    cms_est = cms.query("test_key")
    assert cms_est >= 8, f"Baseline CMS CU underestimated with c>1: est={cms_est}, expected at least 8"
    for j in range(3):
        assert cms.table[j, cms_indices[j]] >= 8, f"CMS Row {j} was not updated properly: {cms.table[j, cms_indices[j]]}"

