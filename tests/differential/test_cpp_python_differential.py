"""
Differential Testing: C++ AdaLogCore vs Python AdaLogSketch.
Verifies estimate correlation and consistency across synthetic streams.
"""

import pytest
import random
from core.bindings import is_dll_available, CompiledAdaLog
from adalog.sketch import AdaLogSketch

@pytest.mark.skipif(not is_dll_available(), reason="C++ adalog_core.dll not available")
def test_cpp_python_point_query_differential():
    """Verify that C++ and Python engines correlate closely on frequency estimation."""
    random.seed(42)
    stream_keys = [f"diff_key_{random.randint(1, 500)}" for _ in range(5000)]
    
    # Python sketch (32 KB equivalent)
    py_sketch = AdaLogSketch(width=7232, depth=4, counter_bits=8, stash_capacity=128, stash_tau=15, seed=42)
    for k in stream_keys:
        py_sketch.update(k, 1)

    # C++ sketch (32 KB equivalent)
    cpp_sketch = CompiledAdaLog(width=7232, depth=4, counter_bits=8, stash_capacity=128, elephant_threshold=15, seed=42)
    for k in stream_keys:
        cpp_sketch.update(k, 1)

    # Compare estimates on sample keys
    test_keys = [f"diff_key_{i}" for i in range(1, 100)]
    diffs = []
    for k in test_keys:
        py_est = py_sketch.estimate(k)
        cpp_est = cpp_sketch.estimate(k)
        diffs.append(abs(py_est - cpp_est))

    max_diff = max(diffs)
    avg_diff = sum(diffs) / len(diffs)
    
    # Average difference across different hash engines should be bounded by collision noise
    assert avg_diff < 5.0, f"Average differential error too high: {avg_diff}"
    assert max_diff < 20.0, f"Max differential error too high: {max_diff}"
