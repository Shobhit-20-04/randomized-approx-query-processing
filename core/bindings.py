"""
Python ctypes wrapper for the compiled high-performance C++ AdaLogCore kernel.
Used for headline latency and throughput benchmarking.
"""

from __future__ import annotations
import ctypes
import os
import sys

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
DLL_PATH = os.path.join(CORE_DIR, "adalog_core.dll")


def is_dll_available() -> bool:
    return os.path.exists(DLL_PATH)


try:
    lib = ctypes.CDLL(DLL_PATH) if os.path.exists(DLL_PATH) else None
except Exception:
    lib = None

if lib:
    # Function prototypes
    lib.adalog_create.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint32]
    lib.adalog_create.restype = ctypes.c_void_p

lib.adalog_destroy.argtypes = [ctypes.c_void_p]
lib.adalog_destroy.restype = None

lib.adalog_update.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_uint32]
lib.adalog_update.restype = None

lib.adalog_estimate.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
lib.adalog_estimate.restype = ctypes.c_uint32

lib.adalog_contains.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
lib.adalog_contains.restype = ctypes.c_bool

lib.adalog_cardinality.argtypes = [ctypes.c_void_p]
lib.adalog_cardinality.restype = ctypes.c_double

# CMS prototypes
lib.cms_create.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint32]
lib.cms_create.restype = ctypes.c_void_p
lib.cms_destroy.argtypes = [ctypes.c_void_p]
lib.cms_destroy.restype = None
lib.cms_update.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_uint32]
lib.cms_update.restype = None

# Bloom prototypes
lib.bloom_create.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint32]
lib.bloom_create.restype = ctypes.c_void_p
lib.bloom_destroy.argtypes = [ctypes.c_void_p]
lib.bloom_destroy.restype = None
lib.bloom_add.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
lib.bloom_add.restype = None

# HLL prototypes
lib.hll_create.argtypes = [ctypes.c_int, ctypes.c_uint32]
lib.hll_create.restype = ctypes.c_void_p
lib.hll_destroy.argtypes = [ctypes.c_void_p]
lib.hll_destroy.restype = None
lib.hll_add.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
lib.hll_add.restype = None

# Disjoint prototypes
lib.disjoint_create.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint32]
lib.disjoint_create.restype = ctypes.c_void_p
lib.disjoint_destroy.argtypes = [ctypes.c_void_p]
lib.disjoint_destroy.restype = None
lib.disjoint_update.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_uint32]
lib.disjoint_update.restype = None


class CompiledAdaLog:
    def __init__(self, width: int = 1024, depth: int = 4, counter_bits: int = 8, stash_capacity: int = 64, elephant_threshold: int = 20, seed: int = 42):
        self._ptr = lib.adalog_create(width, depth, counter_bits, stash_capacity, elephant_threshold, seed)

    def __del__(self):
        if hasattr(self, "_ptr") and self._ptr:
            lib.adalog_destroy(self._ptr)
            self._ptr = None

    def update(self, key: str | bytes, count: int = 1) -> None:
        if isinstance(key, str):
            kb = key.encode("utf-8")
        else:
            kb = key
        lib.adalog_update(self._ptr, kb, len(kb), count)

    def update_batch(self, keys: list[str]) -> None:
        for k in keys:
            kb = k.encode("utf-8")
            lib.adalog_update(self._ptr, kb, len(kb), 1)

    def estimate(self, key: str | bytes) -> int:
        if isinstance(key, str):
            kb = key.encode("utf-8")
        else:
            kb = key
        return int(lib.adalog_estimate(self._ptr, kb, len(kb)))

    def contains(self, key: str | bytes) -> bool:
        if isinstance(key, str):
            kb = key.encode("utf-8")
        else:
            kb = key
        return bool(lib.adalog_contains(self._ptr, kb, len(kb)))

    def cardinality(self) -> float:
        return float(lib.adalog_cardinality(self._ptr))


class CompiledCMS:
    def __init__(self, width: int = 1024, depth: int = 4, seed: int = 42):
        self._ptr = lib.cms_create(width, depth, seed)

    def __del__(self):
        if hasattr(self, "_ptr") and self._ptr:
            lib.cms_destroy(self._ptr)
            self._ptr = None

    def update(self, key: str | bytes, count: int = 1) -> None:
        kb = key.encode("utf-8") if isinstance(key, str) else key
        lib.cms_update(self._ptr, kb, len(kb), count)


class CompiledBloom:
    def __init__(self, m_bits: int = 8192, k_hashes: int = 7, seed: int = 42):
        self._ptr = lib.bloom_create(m_bits, k_hashes, seed)

    def __del__(self):
        if hasattr(self, "_ptr") and self._ptr:
            lib.bloom_destroy(self._ptr)
            self._ptr = None

    def add(self, key: str | bytes) -> None:
        kb = key.encode("utf-8") if isinstance(key, str) else key
        lib.bloom_add(self._ptr, kb, len(kb))


class CompiledHLL:
    def __init__(self, p: int = 10, seed: int = 42):
        self._ptr = lib.hll_create(p, seed)

    def __del__(self):
        if hasattr(self, "_ptr") and self._ptr:
            lib.hll_destroy(self._ptr)
            self._ptr = None

    def add(self, key: str | bytes) -> None:
        kb = key.encode("utf-8") if isinstance(key, str) else key
        lib.hll_add(self._ptr, kb, len(kb))


class CompiledDisjoint:
    def __init__(self, bf_m: int = 8192, bf_k: int = 7, cms_w: int = 1024, cms_d: int = 4, hll_p: int = 10, seed: int = 42):
        self._ptr = lib.disjoint_create(bf_m, bf_k, cms_w, cms_d, hll_p, seed)

    def __del__(self):
        if hasattr(self, "_ptr") and self._ptr:
            lib.disjoint_destroy(self._ptr)
            self._ptr = None

    def update(self, key: str | bytes, count: int = 1) -> None:
        kb = key.encode("utf-8") if isinstance(key, str) else key
        lib.disjoint_update(self._ptr, kb, len(kb), count)
