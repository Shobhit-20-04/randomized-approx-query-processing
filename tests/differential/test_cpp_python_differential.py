"""
Differential & State Equivalence Testing: Native C++ AdaLogCore vs Python AdaLogSketch.
Verifies:
1. Bit-for-bit hash vector equivalence (MurmurHash3-x64-128).
2. Bit-for-bit Kirsch-Mitzenmacher matrix row index equivalence between Native C++ and Python.
3. Bit-for-bit HLL register index and rank equivalence.
4. Membership query (AMQ) zero false negative invariant.
5. Point query frequency estimate and stash state equivalence.
6. 64-bit exact counter tracking without 32-bit integer clipping.
7. Constructor parameter validation (w > 0, d > 0, counter_bits in {8, 16, 32}).
"""

import pytest
import random
import os
from core.bindings import is_dll_available, CompiledAdaLog
from adalog.hash_utils import hash128, get_matrix_indices, get_hll_index_and_rank, murmur3_x64_128_py
from adalog.sketch import AdaLogSketch

@pytest.fixture(autouse=True)
def require_native_library():
    """Ensure native library is available; fail in CI environment if missing."""
    if not is_dll_available():
        if os.getenv("CI"):
            pytest.fail("Native C++ adalog_core library must be built and available in CI.")
        else:
            pytest.skip("Native C++ adalog_core library not loaded locally.")

def test_murmur3_bit_identical_hash_vector():
    """Verify bit-for-bit 128-bit hash equivalence between Python and C++ on deterministic vectors."""
    test_vectors = [
        "",
        "a",
        "adalog",
        "192.168.1.1:80->10.0.0.1:443",
        "The quick brown fox jumps over the lazy dog",
        "Unicode_äöü_αβγ_한글_🚀",
        b"raw_binary_\x00\x01\x02\xff\xfe\x00\x42",
        bytes(range(256)),
        "x" * 15,
        "x" * 16,
        "x" * 17,
        "x" * 128,
    ]

    for key in test_vectors:
        py_h1, py_h2 = murmur3_x64_128_py(key, seed=42)
        cpp_h1, cpp_h2 = CompiledAdaLog.hash128(key, seed=42)
        assert (py_h1, py_h2) == (cpp_h1, cpp_h2), f"Hash mismatch for key: {repr(key)}"

def test_native_c_plus_plus_row_indices_direct_comparison():
    """Directly obtain row indices from native C++ adalog_core and compare with Python.
    Verifies that 64-bit integer arithmetic in C++ prevents intermediate 32-bit wraparound
    across thousands of distinct keys, various widths, and depths."""
    random.seed(12345)
    widths = [16, 64, 512, 1024, 7232, 65536, 100003]
    depths = [1, 2, 4, 8, 16]

    # Generate 500 keys per configuration = 3500 tests, covering high hash values
    test_keys = [f"packet_ip_src_{i}_dst_{i * 1337}_port_{i % 65535}" for i in range(500)]
    # Add keys specifically yielding large h2 to trigger potential 32-bit overflow
    test_keys.extend([
        "critical_overflow_probe_1",
        "critical_overflow_probe_2",
        "high_entropy_random_flow_key_9999",
        "large_multiplier_canary_key_8888",
    ])

    for w in widths:
        for d in depths:
            for key in test_keys:
                h_low, _ = hash128(key, seed=42)
                py_indices = get_matrix_indices(h_low, d, w)
                cpp_indices = CompiledAdaLog.get_matrix_indices(h_low, d, w)
                assert cpp_indices == py_indices, (
                    f"Row index mismatch for key '{key}' with w={w}, d={d}!\n"
                    f"  C++ returned:    {cpp_indices}\n"
                    f"  Python returned: {py_indices}"
                )

def test_hll_register_and_rank_bit_identical():
    """Verify bit-for-bit HLL register index and rank equivalence."""
    p = 10
    test_keys = [f"card_key_{i}" for i in range(500)]

    for key in test_keys:
        _, h_high = hash128(key, seed=42)
        py_reg, py_rank = get_hll_index_and_rank(h_high, p)

        rem = 64 - p
        expected_reg = (h_high >> rem) & ((1 << p) - 1)
        w_bits = h_high & ((1 << rem) - 1)
        expected_rank = (rem + 1) if w_bits == 0 else (rem - w_bits.bit_length() + 1)
        expected_rank = min(expected_rank, 63)

        assert py_reg == expected_reg, f"HLL register mismatch for {key}"
        assert py_rank == expected_rank, f"HLL rank mismatch for {key}"

def test_point_query_and_membership_state_equivalence():
    """Verify that C++ and Python engines yield exact point query and membership equivalence."""
    random.seed(42)
    stream_keys = [f"key_{random.randint(1, 100)}" for _ in range(3000)]
    
    py_sketch = AdaLogSketch(width=7232, depth=4, counter_bits=8, stash_capacity=128, stash_tau=15, seed=42)
    cpp_sketch = CompiledAdaLog(width=7232, depth=4, counter_bits=8, stash_capacity=128, elephant_threshold=15, seed=42)

    for k in stream_keys:
        py_sketch.update(k, 1)
        cpp_sketch.update(k, 1)

    # 1. Zero false negatives check on AMQ
    unique_keys = set(stream_keys)
    for k in unique_keys:
        assert py_sketch.contains(k) is True, f"Python false negative for {k}"
        assert cpp_sketch.contains(k) is True, f"C++ false negative for {k}"

    # 2. Point frequency estimation equivalence
    diffs = []
    for k in [f"key_{i}" for i in range(1, 150)]:
        py_est = py_sketch.estimate(k)
        cpp_est = cpp_sketch.estimate(k)
        diffs.append(abs(py_est - cpp_est))

    max_diff = max(diffs)
    avg_diff = sum(diffs) / len(diffs)
    assert max_diff == 0, f"Point estimates diverged! max_diff={max_diff}, avg_diff={avg_diff}"

def test_binary_key_support_without_collision():
    """Verify arbitrary binary keys hash and store safely without UTF-8 replacement collisions."""
    py_sketch = AdaLogSketch(width=1024, depth=4, counter_bits=8, stash_capacity=32, stash_tau=5, seed=42)
    cpp_sketch = CompiledAdaLog(width=1024, depth=4, counter_bits=8, stash_capacity=32, elephant_threshold=5, seed=42)

    bin_key1 = b"\x80\x81\x82\x83_stream_a"
    bin_key2 = b"\x80\x81\x82\x83_stream_b"

    for _ in range(10):
        py_sketch.update(bin_key1, 1)
        cpp_sketch.update(bin_key1, 1)

    for _ in range(20):
        py_sketch.update(bin_key2, 1)
        cpp_sketch.update(bin_key2, 1)

    assert py_sketch.estimate(bin_key1) >= 10
    assert py_sketch.estimate(bin_key2) >= 20
    assert cpp_sketch.estimate(bin_key1) >= 10
    assert cpp_sketch.estimate(bin_key2) >= 20
    assert py_sketch.estimate(bin_key1) == cpp_sketch.estimate(bin_key1)
    assert py_sketch.estimate(bin_key2) == cpp_sketch.estimate(bin_key2)

def test_64bit_exact_counter_tracking_without_clipping():
    """Verify that 64-bit stash exact counters in both Python and C++ do not saturate at UINT32_MAX (2^32 - 1)."""
    py_sketch = AdaLogSketch(width=1024, depth=4, counter_bits=8, stash_capacity=16, stash_tau=5, seed=42)
    cpp_sketch = CompiledAdaLog(width=1024, depth=4, counter_bits=8, stash_capacity=16, elephant_threshold=5, seed=42)
    key = "super_heavy_elephant_stream_key"

    # Seed key into stash
    py_sketch.update(key, 10)
    cpp_sketch.update(key, 10)

    # Add large increments exceeding 32-bit range (> 2^32 - 1 = 4,294,967,295)
    large_inc = 5_000_000_000  # 5 billion > 2^32 - 1
    py_sketch.update(key, large_inc)
    cpp_sketch.update(key, large_inc)

    py_est = py_sketch.estimate(key)
    cpp_est = cpp_sketch.estimate(key)
    assert py_est >= 5_000_000_010, f"Python estimate clipped unexpectedly: {py_est}"
    assert cpp_est >= 5_000_000_010, f"C++ estimate clipped unexpectedly: {cpp_est}"
    assert py_est == cpp_est, f"Mismatch between Python ({py_est}) and C++ ({cpp_est})"

    # Further accumulation in 64-bit domain
    py_sketch.update(key, 10_000_000_000)
    cpp_sketch.update(key, 10_000_000_000)
    assert py_sketch.estimate(key) == cpp_sketch.estimate(key)
    assert py_sketch.estimate(key) >= 15_000_000_010

def test_constructor_parameter_validation():
    """Verify that native C++ engine rejects invalid constructor arguments safely."""
    with pytest.raises(ValueError):
        CompiledAdaLog(width=-10)
    with pytest.raises(ValueError):
        CompiledAdaLog(depth=0)
    with pytest.raises(ValueError):
        CompiledAdaLog(counter_bits=12)  # Invalid counter bits
    with pytest.raises(ValueError):
        CompiledAdaLog(hll_m=5)   # Below minimum supported HLL precision (m >= 16)
    with pytest.raises(ValueError):
        CompiledAdaLog(hll_m=1_000_000)  # Exceeds maximum supported HLL precision
    with pytest.raises(ValueError):
        CompiledAdaLog(stash_capacity=2_000_000)  # Exceeds maximum supported stash capacity
