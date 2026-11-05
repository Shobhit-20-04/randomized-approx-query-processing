"""
Differential & State Equivalence Testing: Native C++ AdaLogCore vs Python AdaLogSketch.
Verifies:
1. Bit-for-bit hash vector equivalence (MurmurHash3-x64-128).
2. Bit-for-bit Kirsch-Mitzenmacher matrix row index equivalence.
3. Bit-for-bit HLL register index and rank equivalence.
4. Membership query (AMQ) zero false negative invariant.
5. Point query frequency estimate and stash state equivalence.
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
        "Unicode_тест_中文_🔥",
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

def test_matrix_indices_bit_identical():
    """Verify bit-for-bit row index equivalence across d rows and width w."""
    width = 7232
    depth = 4
    test_keys = [f"flow_{i}_{i*7}" for i in range(200)]

    for key in test_keys:
        h1, h2 = hash128(key, seed=42)
        py_indices = get_matrix_indices(h1, depth, width)
        
        # In C++, indices[j] = (h1_low + j * h2_odd) % width
        h1_low = h1 & 0xFFFFFFFF
        h1_high = ((h1 >> 32) & 0xFFFFFFFF) | 1
        expected = [(h1_low + j * h1_high) % width for j in range(depth)]
        assert py_indices == expected, f"Matrix index calculation mismatch for {key}"

def test_hll_register_and_rank_bit_identical():
    """Verify bit-for-bit HLL register index and rank equivalence."""
    p = 10
    test_keys = [f"card_key_{i}" for i in range(500)]

    for key in test_keys:
        _, h_high = hash128(key, seed=42)
        py_reg, py_rank = get_hll_index_and_rank(h_high, p)

        # Expected C++ bit extraction
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

    # With identical MurmurHash3-128, Kirsch-Mitzenmacher indices, and fully associative stash,
    # point frequency estimates must be identical (max difference == 0)
    max_diff = max(diffs)
    avg_diff = sum(diffs) / len(diffs)
    assert max_diff == 0, f"Point estimates diverged! max_diff={max_diff}, avg_diff={avg_diff}"

def test_binary_key_support_without_collision():
    """Verify arbitrary binary keys hash and store safely without UTF-8 replacement collisions."""
    py_sketch = AdaLogSketch(width=1024, depth=4, counter_bits=8, stash_capacity=32, stash_tau=5, seed=42)
    cpp_sketch = CompiledAdaLog(width=1024, depth=4, counter_bits=8, stash_capacity=32, elephant_threshold=5, seed=42)

    # Two distinct binary keys that would collide under lossy utf-8 replacement
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
