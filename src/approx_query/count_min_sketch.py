"""
Count-Min Sketch implementation for approximate frequency query processing.
Implements Cormode-Muthukrishnan (2005) 2D counter table, 2-universal hash family,
point query frequency estimation, and theoretical additive error bound verification.
"""

from __future__ import annotations

import math
import struct
import sys
import hashlib
import numpy as np
from typing import Any, Dict, Iterable, List, Sequence, Tuple


class CountMinSketch:
    """
    Randomized data structure for point-frequency estimation on data streams.
    Guarantees:
      1. No underestimation: estimate(x) >= true_frequency(x)
      2. With probability at least 1 - delta:
         estimate(x) <= true_frequency(x) + epsilon * ||a||_1
         where ||a||_1 is the total stream length (sum of all increments).
    """

    # Large Mersenne prime 2^61 - 1 for universal hashing
    MERSENNE_PRIME_61: int = (1 << 61) - 1

    def __init__(
        self,
        epsilon: float,
        delta: float,
        width: int | None = None,
        depth: int | None = None,
        seed: int = 42,
    ) -> None:
        """
        Initialize Count-Min Sketch.

        Args:
            epsilon: Error tolerance factor (0 < epsilon < 1).
                     width = ceil(e / epsilon).
            delta: Probability of error exceeding epsilon * ||a||_1 (0 < delta < 1).
                   depth = ceil(ln(1 / delta)).
            width: Optional explicit width w (number of counter columns).
            depth: Optional explicit depth d (number of hash functions / rows).
            seed: Random seed for generating pairwise-independent hash coefficients.
        """
        if not (0.0 < epsilon < 1.0):
            raise ValueError(f"epsilon must be in (0, 1), got {epsilon}")
        if not (0.0 < delta < 1.0):
            raise ValueError(f"delta must be in (0, 1), got {delta}")

        self.epsilon: float = epsilon
        self.delta: float = delta
        self.seed: int = seed

        # Width w = ceil(e / epsilon)
        if width is None:
            self.width: int = math.ceil(math.e / epsilon)
        else:
            if width <= 0:
                raise ValueError(f"width must be positive, got {width}")
            self.width = width

        # Depth d = ceil(ln(1 / delta))
        if depth is None:
            self.depth: int = math.ceil(math.log(1.0 / delta))
        else:
            if depth <= 0:
                raise ValueError(f"depth must be positive, got {depth}")
            self.depth = depth

        # Counter table: shape (depth, width) with 64-bit unsigned/signed integers
        self.table: np.ndarray = np.zeros((self.depth, self.width), dtype=np.int64)

        # Total stream volume ||a||_1 = sum of all increments
        self.total_count: int = 0

        # Generate pairwise-independent hash coefficients (a_j, b_j) for 2-universal hash family:
        # h_j(x) = ((a_j * hash64(x) + b_j) % MERSENNE_PRIME_61) % width
        import random
        py_rng = random.Random(seed)
        self._hash_a: List[int] = [
            py_rng.randint(1, self.MERSENNE_PRIME_61 - 1) for _ in range(self.depth)
        ]
        self._hash_b: List[int] = [
            py_rng.randint(0, self.MERSENNE_PRIME_61 - 1) for _ in range(self.depth)
        ]

    def _hash_item_64(self, item: Any) -> int:
        """Hash item to 64-bit integer using BLAKE2b."""
        if isinstance(item, bytes):
            data = item
        elif isinstance(item, str):
            data = item.encode("utf-8")
        else:
            data = str(item).encode("utf-8")

        digest = hashlib.blake2b(data, digest_size=8).digest()
        (val,) = struct.unpack("<Q", digest)
        # Constrain to 61 bits to stay strictly below Mersenne prime 2^61 - 1
        return val & self.MERSENNE_PRIME_61

    def _row_column_index(self, row: int, item_hash: int) -> int:
        """Compute column index for a given row using 2-universal hashing."""
        a = self._hash_a[row]
        b = self._hash_b[row]
        val = (a * item_hash + b) % self.MERSENNE_PRIME_61
        return val % self.width

    def update(self, item: Any, count: int = 1) -> None:
        """
        Increment the frequency of an item by count (default 1).
        Standard CMS assumes count >= 0 for insertion-only stream.
        """
        if count < 0:
            raise ValueError(f"count must be non-negative for standard CMS, got {count}")
        if count == 0:
            return

        h = self._hash_item_64(item)
        for row in range(self.depth):
            col = self._row_column_index(row, h)
            self.table[row, col] += count
        self.total_count += count

    def update_many(self, items: Iterable[Any]) -> None:
        """Update multiple items from stream."""
        for item in items:
            self.update(item, 1)

    def query(self, item: Any) -> int:
        """
        Estimate point frequency of item.
        Returns the minimum counter across all rows:
        min_{0 <= j < depth} table[j, h_j(item)].
        """
        h = self._hash_item_64(item)
        min_val = sys.maxsize
        for row in range(self.depth):
            col = self._row_column_index(row, h)
            val = int(self.table[row, col])
            if val < min_val:
                min_val = val
        return min_val

    def batch_query(self, items: Sequence[Any]) -> List[int]:
        """Query multiple items returning a list of frequency estimates."""
        return [self.query(item) for item in items]

    def theoretical_bound(self, true_frequency: int) -> float:
        """
        Upper bound guaranteed with probability 1 - delta:
        bound = true_frequency + epsilon * ||a||_1
        """
        return true_frequency + self.epsilon * self.total_count

    def compute_errors(
        self, ground_truth: Dict[Any, int]
    ) -> Dict[str, float]:
        """
        Compute comprehensive error metrics against exact ground truth frequencies.

        Returns:
            Dictionary with MAE, RMSE, max_overestimation, bound_compliance_ratio, etc.
        """
        if not ground_truth:
            return {
                "mae": 0.0,
                "rmse": 0.0,
                "max_overestimation": 0.0,
                "bound_compliance_ratio": 1.0,
                "underestimation_count": 0,
                "total_queried": 0,
            }

        absolute_errors: List[float] = []
        squared_errors: List[float] = []
        max_overest: int = 0
        bound_satisfied: int = 0
        underestimations: int = 0
        epsilon_n = self.epsilon * self.total_count

        for item, true_freq in ground_truth.items():
            est_freq = self.query(item)
            error = est_freq - true_freq

            if error < 0:
                underestimations += 1

            abs_err = abs(error)
            absolute_errors.append(abs_err)
            squared_errors.append(error * error)

            if error > max_overest:
                max_overest = error

            # Check if estimate <= true_freq + epsilon * N
            if error <= epsilon_n:
                bound_satisfied += 1

        n_queries = len(ground_truth)
        mae = float(np.mean(absolute_errors))
        rmse = float(np.sqrt(np.mean(squared_errors)))
        compliance_ratio = bound_satisfied / n_queries

        return {
            "mae": mae,
            "rmse": rmse,
            "max_overestimation": float(max_overest),
            "bound_compliance_ratio": compliance_ratio,
            "underestimation_count": underestimations,
            "total_queried": n_queries,
        }

    def memory_usage_bytes(self) -> int:
        """
        Return the exact memory footprint of the internal NumPy table
        plus object overhead in bytes.
        """
        return self.table.nbytes + sys.getsizeof(self)
