"""
AdaLog-Sketch Single 128-bit Hash Pipeline.
Derives all d matrix row indices and HLL register index + rank from one 128-bit hash.
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
    Returns (h_low, h_high) as two 64-bit unsigned integers.
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


def get_matrix_indices(h_low: int, d: int, w: int) -> list[int]:
    """
    Kirsch-Mitzenmacher double hashing for d rows:
      h1 = h_low & 0xFFFFFFFF
      h2 = (h_low >> 32) & 0xFFFFFFFF | 1
      idx_j = (h1 + j * h2) mod w
    """
    h1 = h_low & 0xFFFFFFFF
    h2 = ((h_low >> 32) & 0xFFFFFFFF) | 1
    return [(h1 + j * h2) % w for j in range(d)]


def get_hll_index_and_rank(h_high: int, p: int) -> Tuple[int, int]:
    """
    Derives register index (p bits) and rank (leading zeros) from h_high:
      idx_hll = h_high mod (2^p)
      rank = clz(remaining bits) + 1, capped at 63.
    """
    m = 1 << p
    idx_hll = h_high & (m - 1)
    w_bits = h_high >> p
    remaining_bits = 64 - p

    if w_bits == 0:
        rank = remaining_bits + 1
    else:
        rank = (remaining_bits - w_bits.bit_length()) + 1

    return idx_hll, min(rank, 63)
