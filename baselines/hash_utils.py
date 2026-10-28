"""
Unified Hashing Utilities for Fair Algorithmic Comparison.
Provides 128-bit hashing via xxh3 (fastest, high-entropy) with fallback to blake2b.
Implements Kirsch-Mitzenmacher double-hashing for d rows:
  idx_j = (h1 + j * h2) mod w
"""

from __future__ import annotations
import hashlib
from typing import Tuple

try:
    import xxhash
    HAS_XXHASH = True
except ImportError:
    HAS_XXHASH = False


def hash128(key: str | bytes, seed: int = 42) -> Tuple[int, int]:
    """
    Compute a 128-bit hash of key, returned as two 64-bit unsigned integers (h_low, h_high).
    Uses xxh3_128 if available, else blake2b.
    """
    if isinstance(key, str):
        key_bytes = key.encode("utf-8")
    else:
        key_bytes = key

    if HAS_XXHASH:
        val = xxhash.xxh3_128_intdigest(key_bytes, seed=seed)
        h_low = val & 0xFFFFFFFFFFFFFFFF
        h_high = (val >> 64) & 0xFFFFFFFFFFFFFFFF
        return h_low, h_high
    else:
        digest = hashlib.blake2b(key_bytes, digest_size=16, person=seed.to_bytes(4, "little")).digest()
        h_low = int.from_bytes(digest[:8], "little")
        h_high = int.from_bytes(digest[8:], "little")
        return h_low, h_high


def kirsch_mitzenmacher(h_low: int, d: int, w: int) -> list[int]:
    """
    Derive d row indices for a table of width w using Kirsch-Mitzenmacher double hashing:
      h1 = h_low & 0xFFFFFFFF
      h2 = (h_low >> 32) & 0xFFFFFFFF | 1  (ensure odd step size)
      idx_j = (h1 + j * h2) mod w
    """
    h1 = h_low & 0xFFFFFFFF
    h2 = ((h_low >> 32) & 0xFFFFFFFF) | 1
    return [(h1 + j * h2) % w for j in range(d)]


def extract_hll_bits(h_high: int, p: int) -> Tuple[int, int]:
    """
    Extract HLL register index (p bits) and leading-zero rank from the 64-bit high half:
      idx_hll = h_high mod (2^p)
      rank = clz(remaining (64 - p) bits) + 1
    """
    m = 1 << p
    idx_hll = h_high & (m - 1)
    w_bits = h_high >> p
    remaining_bits = 64 - p

    if w_bits == 0:
        rank = remaining_bits + 1
    else:
        # Count leading zeros in w_bits within remaining_bits
        rank = (remaining_bits - w_bits.bit_length()) + 1

    # Cap rank at 63 (for 6-bit packed registers)
    return idx_hll, min(rank, 63)
