# -*- coding: utf-8 -*-
"""Update test_audit_invariants.py with the complete 6 scenarios suite."""
import os

fpath = os.path.join("tests", "regression", "test_audit_invariants.py")
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find test_rejected_eviction_zero_truncation
start_idx = None
for i, line in enumerate(lines):
    if line.startswith("def test_rejected_eviction_zero_truncation():"):
        start_idx = i
        break

if start_idx is None:
    raise RuntimeError("Could not find test_rejected_eviction_zero_truncation")

# Find the end of test_rejected_eviction_zero_truncation
end_idx = None
for i in range(start_idx, len(lines)):
    if lines[i].startswith("if __name__ =="):
        end_idx = i
        break

if end_idx is None:
    end_idx = len(lines)

new_tests = '''def test_rejected_eviction_unsaturated_victim():
    """Scenario 1: Candidate reaches tau but count <= min_tot < C_max.
    Promotion is rejected; candidate falls through to matrix CU with zero truncation.
    Tested on both Python and native C++."""
    assert is_dll_available(), "C++ core DLL must be available for audit tests"

    # Python
    py = AdaLogSketch(d=4, w=1024, counter_bits=8, stash_capacity=2, stash_tau=5, use_stash=True, seed=42)
    py.update("h1", 50)
    py.update("h2", 40)
    py.update("cand", 10)
    assert "cand" not in py.stash.entries
    assert py.estimate("cand") >= 10

    # C++
    cpp = CompiledAdaLog(1024, 4, 8, 2, 5, 42)
    cpp.update("h1", 50)
    cpp.update("h2", 40)
    cpp.update("cand", 10)
    assert cpp.estimate("cand") >= 10


def test_rejected_eviction_zero_truncation():
    """Backward-compatible alias for Scenario 1."""
    test_rejected_eviction_unsaturated_victim()


def test_successful_eviction_and_writeback():
    """Scenario 2: Candidate exceeds lightest evictable entry (min_tot < C_max).
    Victim is evicted with monotonic matrix write-back; candidate enters stash.
    Tested on both Python and native C++."""
    assert is_dll_available(), "C++ core DLL must be available for audit tests"

    # Python
    py = AdaLogSketch(d=4, w=1024, counter_bits=8, stash_capacity=2, stash_tau=5, use_stash=True, seed=42)
    py.update("h1", 30)
    py.update("h2", 40)
    py.update("cand", 60)
    assert "h1" not in py.stash.entries
    assert "cand" in py.stash.entries
    assert py.estimate("h1") >= 30
    assert py.estimate("cand") >= 60

    # C++
    cpp = CompiledAdaLog(1024, 4, 8, 2, 5, 42)
    cpp.update("h1", 30)
    cpp.update("h2", 40)
    cpp.update("cand", 60)
    assert cpp.estimate("h1") >= 30
    assert cpp.estimate("cand") >= 60


def test_all_stash_entries_saturated():
    """Scenario 3: All K resident stash entries have reached C_max (tot >= 255).
    E_evictable is empty; arriving candidates cannot evict saturated elephants and fall back to matrix CU.
    Tested on both Python and native C++."""
    assert is_dll_available(), "C++ core DLL must be available for audit tests"

    # Python
    py = AdaLogSketch(d=4, w=1024, counter_bits=8, stash_capacity=2, stash_tau=5, use_stash=True, seed=42)
    py.update("sat1", 300)
    py.update("sat2", 300)
    py.update("cand", 100)
    assert "cand" not in py.stash.entries
    assert "sat1" in py.stash.entries
    assert "sat2" in py.stash.entries
    assert py.estimate("cand") >= 100

    # C++
    cpp = CompiledAdaLog(1024, 4, 8, 2, 5, 42)
    cpp.update("sat1", 300)
    cpp.update("sat2", 300)
    cpp.update("cand", 100)
    assert cpp.estimate("sat1") >= 300
    assert cpp.estimate("sat2") >= 300
    assert cpp.estimate("cand") >= 100


def test_saturated_entry_retention():
    """Scenario 4: Saturated stash entries are strictly retained indefinitely,
    even under sustained intermediate traffic bursts.
    Tested on both Python and native C++."""
    assert is_dll_available(), "C++ core DLL must be available for audit tests"

    # Python
    py = AdaLogSketch(d=4, w=1024, counter_bits=8, stash_capacity=2, stash_tau=5, use_stash=True, seed=42)
    py.update("sat1", 400)
    py.update("sat2", 400)
    for i in range(50):
        py.update(f"noise_{i}", 15)
    assert "sat1" in py.stash.entries
    assert "sat2" in py.stash.entries
    assert py.estimate("sat1") >= 400
    assert py.estimate("sat2") >= 400

    # C++
    cpp = CompiledAdaLog(1024, 4, 8, 2, 5, 42)
    cpp.update("sat1", 400)
    cpp.update("sat2", 400)
    for i in range(50):
        cpp.update(f"noise_{i}", 15)
    assert cpp.estimate("sat1") >= 400
    assert cpp.estimate("sat2") >= 400


def test_matrix_fallback():
    """Scenario 5: Items below tau bypass stash promotion and update matrix CU directly.
    Tested on both Python and native C++."""
    assert is_dll_available(), "C++ core DLL must be available for audit tests"

    # Python
    py = AdaLogSketch(d=4, w=1024, counter_bits=8, stash_capacity=2, stash_tau=10, use_stash=True, seed=42)
    for i in range(20):
        py.update(f"small_{i}", 3)
        assert py.estimate(f"small_{i}") >= 3

    # C++
    cpp = CompiledAdaLog(1024, 4, 8, 2, 10, 42)
    for i in range(20):
        cpp.update(f"small_{i}", 3)
        assert cpp.estimate(f"small_{i}") >= 3


def test_frequency_estimates_after_later_writeback():
    """Scenario 6: Cascading evictions and subsequent matrix updates preserve f_hat(x) >= f(x).
    Tested on both Python and native C++."""
    assert is_dll_available(), "C++ core DLL must be available for audit tests"

    # Python
    py = AdaLogSketch(d=4, w=1024, counter_bits=8, stash_capacity=2, stash_tau=5, use_stash=True, seed=42)
    py.update("A", 20)
    py.update("B", 25)
    py.update("C", 30)
    py.update("D", 35)
    py.update("E", 40)
    for i in range(500):
        py.update(f"bg_{i}", 1)
    for k, expected in [("A", 20), ("B", 25), ("C", 30), ("D", 35), ("E", 40)]:
        assert py.estimate(k) >= expected, f"Python underestimation for {k}"

    # C++
    cpp = CompiledAdaLog(1024, 4, 8, 2, 5, 42)
    cpp.update("A", 20)
    cpp.update("B", 25)
    cpp.update("C", 30)
    cpp.update("D", 35)
    cpp.update("E", 40)
    for i in range(500):
        cpp.update(f"bg_{i}", 1)
    for k, expected in [("A", 20), ("B", 25), ("C", 30), ("D", 35), ("E", 40)]:
        assert cpp.estimate(k) >= expected, f"C++ underestimation for {k}"


'''

modified = lines[:start_idx] + [new_tests] + lines[end_idx:]
with open(fpath, "w", encoding="utf-8") as f:
    f.writelines(modified)

print("Successfully updated test_audit_invariants.py with all 6 regression test scenarios!")
