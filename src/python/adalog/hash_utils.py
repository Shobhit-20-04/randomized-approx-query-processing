"""
AdaLog-Sketch Single 128-bit Hash Pipeline.
Derives all d matrix row indices and HLL register index + rank from one 128-bit hash.
Enforces MurmurHash3-x64-128 bit-for-bit equivalence between Python and C++ kernels.
"""

from __future__ import annotations
import struct
from typing import Tuple, List

def rotl64(x: int, r: int) -> int:
    return ((x << r) & 0xFFFFFFFFFFFFFFFF) | (x >> (64 - r))

def fmix64(k: int) -> int:
    k ^= k >> 33
    k = (k * 0xff51afd7ed558ccd) & 0xFFFFFFFFFFFFFFFF
    k ^= k >> 33
    k = (k * 0xc4ceb9fe1a85ec53) & 0xFFFFFFFFFFFFFFFF
    k ^= k >> 33
    return k

def murmur3_x64_128_py(data: str | bytes, seed: int = 42) -> Tuple[int, int]:
    """
    Pure Python implementation of Austin Appleby's MurmurHash3_x64_128.
    Guarantees 100% bit-for-bit output equivalence with native C++ murmur3_128
    across any arbitrary string or binary bytes input on any platform.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    elif not isinstance(data, (bytes, bytearray)):
        data = str(data).encode("utf-8")

    length = len(data)
    nblocks = length // 16

    h1 = seed & 0xFFFFFFFFFFFFFFFF
    h2 = seed & 0xFFFFFFFFFFFFFFFF

    c1 = 0x87c37b91114253d5
    c2 = 0x4cf5ad432745937f

    for i in range(nblocks):
        k1, k2 = struct.unpack_from("<QQ", data, i * 16)

        k1 = (k1 * c1) & 0xFFFFFFFFFFFFFFFF
        k1 = rotl64(k1, 31)
        k1 = (k1 * c2) & 0xFFFFFFFFFFFFFFFF
        h1 ^= k1

        h1 = rotl64(h1, 27)
        h1 = (h1 + h2) & 0xFFFFFFFFFFFFFFFF
        h1 = (h1 * 5 + 0x52dce729) & 0xFFFFFFFFFFFFFFFF

        k2 = (k2 * c2) & 0xFFFFFFFFFFFFFFFF
        k2 = rotl64(k2, 33)
        k2 = (k2 * c1) & 0xFFFFFFFFFFFFFFFF
        h2 ^= k2

        h2 = rotl64(h2, 31)
        h2 = (h2 + h1) & 0xFFFFFFFFFFFFFFFF
        h2 = (h2 * 5 + 0x38495ab5) & 0xFFFFFFFFFFFFFFFF

    tail = data[nblocks * 16:]
    tail_len = len(tail)
    k1 = 0
    k2 = 0

    if tail_len >= 15: k2 ^= tail[14] << 48
    if tail_len >= 14: k2 ^= tail[13] << 40
    if tail_len >= 13: k2 ^= tail[12] << 32
    if tail_len >= 12: k2 ^= tail[11] << 24
    if tail_len >= 11: k2 ^= tail[10] << 16
    if tail_len >= 10: k2 ^= tail[9] << 8
    if tail_len >= 9:
        k2 ^= tail[8]
        k2 = (k2 * c2) & 0xFFFFFFFFFFFFFFFF
        k2 = rotl64(k2, 33)
        k2 = (k2 * c1) & 0xFFFFFFFFFFFFFFFF
        h2 ^= k2

    if tail_len >= 8: k1 ^= tail[7] << 56
    if tail_len >= 7: k1 ^= tail[6] << 48
    if tail_len >= 6: k1 ^= tail[5] << 40
    if tail_len >= 5: k1 ^= tail[4] << 32
    if tail_len >= 4: k1 ^= tail[3] << 24
    if tail_len >= 3: k1 ^= tail[2] << 16
    if tail_len >= 2: k1 ^= tail[1] << 8
    if tail_len >= 1:
        k1 ^= tail[0]
        k1 = (k1 * c1) & 0xFFFFFFFFFFFFFFFF
        k1 = rotl64(k1, 31)
        k1 = (k1 * c2) & 0xFFFFFFFFFFFFFFFF
        h1 ^= k1

    h1 ^= length
    h2 ^= length

    h1 = (h1 + h2) & 0xFFFFFFFFFFFFFFFF
    h2 = (h2 + h1) & 0xFFFFFFFFFFFFFFFF

    h1 = fmix64(h1)
    h2 = fmix64(h2)

    h1 = (h1 + h2) & 0xFFFFFFFFFFFFFFFF
    h2 = (h2 + h1) & 0xFFFFFFFFFFFFFFFF

    return h1, h2

def murmur3_hash128(key: str | bytes, seed: int = 42) -> Tuple[int, int]:
    """
    Computes 128-bit MurmurHash3 digest matching native C++ adalog_core bit-for-bit.
    Fast-paths to compiled C++ kernel if available; otherwise uses pure Python MurmurHash3.
    """
    try:
        from core.bindings import CompiledAdaLog, is_dll_available
        if is_dll_available():
            return CompiledAdaLog.hash128(key, seed)
    except Exception:
        pass
    return murmur3_x64_128_py(key, seed)

def hash128(key: str | bytes, seed: int = 42, algorithm: str = "murmur3") -> Tuple[int, int]:
    """
    Unified 128-bit hash pipeline entry point.
    Defaults to MurmurHash3-x64-128 to ensure cross-language bit-identity with native C++.
    Returns (h_low, h_high) as two 64-bit unsigned integers.
    """
    return murmur3_hash128(key, seed)

def get_matrix_indices(h_low: int, d: int, w: int) -> List[int]:
    """
    Kirsch-Mitzenmacher double hashing for d rows:
      h1 = h_low & 0xFFFFFFFF
      h2 = ((h_low >> 32) & 0xFFFFFFFF) | 1
      idx_j = (h1 + j * h2) mod w
    """
    h1 = h_low & 0xFFFFFFFF
    h2 = ((h_low >> 32) & 0xFFFFFFFF) | 1
    return [(h1 + j * h2) % w for j in range(d)]

def get_hll_index_and_rank(h_high: int, p: int) -> Tuple[int, int]:
    """
    Derives register index (p bits) and rank (leading zeros + 1) from h_high:
      idx_hll = (h_high >> (64 - p)) & ((1 << p) - 1)
      w_bits = h_high & ((1 << (64 - p)) - 1)
      rank = clz(w_bits) + 1, capped at 63.
    Matches the native C++ bit extraction bit-for-bit.
    """
    m = 1 << p
    rem = 64 - p
    idx_hll = (h_high >> rem) & (m - 1)
    w_bits = h_high & ((1 << rem) - 1)

    if w_bits == 0:
        rank = rem + 1
    else:
        rank = (rem - w_bits.bit_length()) + 1

    return idx_hll, min(rank, 63)
