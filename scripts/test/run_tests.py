#!/usr/bin/env python
"""
Unified Test Runner for AdaLog-Sketch.
Executes both the standard pytest unit test suite and the independent invariant audit suite.
"""

import sys
import subprocess
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def run_pytest():
    print("=" * 70)
    print("RUNNING PYTEST UNIT & SYSTEM TEST SUITE")
    print("=" * 70)
    cmd = [sys.executable, "-m", "pytest", "-v", os.path.join(REPO_ROOT, "tests")]
    ret = subprocess.run(cmd, cwd=REPO_ROOT)
    return ret.returncode == 0

def run_audit_invariants():
    print("\n" + "=" * 70)
    print("RUNNING INDEPENDENT INVARIANT AUDIT SUITE")
    print("=" * 70)
    cmd = [sys.executable, os.path.join(REPO_ROOT, "tests", "regression", "test_audit_invariants.py")]
    ret = subprocess.run(cmd, cwd=REPO_ROOT)
    return ret.returncode == 0

def main():
    p1 = run_pytest()
    p2 = run_audit_invariants()
    print("\n" + "=" * 70)
    print(f"TEST SUMMARY: Pytest: {'PASS' if p1 else 'FAIL'} | Invariants Audit: {'PASS' if p2 else 'FAIL'}")
    print("=" * 70)
    if not (p1 and p2):
        sys.exit(1)

if __name__ == "__main__":
    main()
