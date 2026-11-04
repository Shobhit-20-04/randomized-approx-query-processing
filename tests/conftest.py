import os
import sys

# Ensure project root, src, src/python, and benchmarks are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in [root_dir, os.path.join(root_dir, "src"), os.path.join(root_dir, "src", "python"), os.path.join(root_dir, "benchmarks")]:
    if p not in sys.path:
        sys.path.insert(0, p)
