"""
Python ctypes wrapper for the compiled high-performance C++ AdaLogCore kernel.
Used for headline latency and throughput benchmarking.
"""

from __future__ import annotations
import ctypes
import os
import sys

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CORE_DIR, "..", "..")) if "src" in CORE_DIR else os.path.abspath(os.path.join(CORE_DIR, ".."))

def _find_library() -> str | None:
    if sys.platform.startswith("win"):
        exts = [".dll"]
        names = ["adalog_core"]
    elif sys.platform.startswith("darwin"):
        exts = [".dylib", ".so"]
        names = ["libadalog_core", "adalog_core"]
    else:
        exts = [".so"]
        names = ["libadalog_core", "adalog_core"]

    search_dirs = [
        CORE_DIR,
        os.path.join(PROJECT_ROOT, "core"),
        os.path.join(PROJECT_ROOT, "build"),
        os.path.join(PROJECT_ROOT, "src", "cpp", "core"),
        os.path.join(PROJECT_ROOT, "src", "cpp", "bindings"),
    ]
    for d in search_dirs:
        for name in names:
            for ext in exts:
                candidate = os.path.join(d, f"{name}{ext}")
                if os.path.isfile(candidate):
                    return candidate
    return None

DLL_PATH = _find_library()

try:
    lib = ctypes.CDLL(DLL_PATH) if DLL_PATH else None
except Exception:
    lib = None

def is_dll_available() -> bool:
    return lib is not None

if lib:
    # Function prototypes
    lib.adalog_create.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint32]
    lib.adalog_create.restype = ctypes.c_void_p

    lib.adalog_create_full.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint32]
    lib.adalog_create_full.restype = ctypes.c_void_p

    lib.adalog_destroy.argtypes = [ctypes.c_void_p]
    lib.adalog_destroy.restype = None

    lib.adalog_update.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_uint64]
    lib.adalog_update.restype = None

    lib.adalog_estimate.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    lib.adalog_estimate.restype = ctypes.c_uint64

    lib.adalog_contains.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    lib.adalog_contains.restype = ctypes.c_bool

    lib.adalog_cardinality.argtypes = [ctypes.c_void_p]
    lib.adalog_cardinality.restype = ctypes.c_double

    lib.adalog_top_k.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint64)]
    lib.adalog_top_k.restype = ctypes.c_int

    lib.adalog_top_k_composite.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint64)]
    lib.adalog_top_k_composite.restype = ctypes.c_int

    lib.adalog_get_stash_count.argtypes = [ctypes.c_void_p]
    lib.adalog_get_stash_count.restype = ctypes.c_int

    lib.adalog_get_stash_evictions.argtypes = [ctypes.c_void_p]
    lib.adalog_get_stash_evictions.restype = ctypes.c_uint64

    lib.adalog_get_stash_rejections.argtypes = [ctypes.c_void_p]
    lib.adalog_get_stash_rejections.restype = ctypes.c_uint64

    lib.adalog_get_memory_bytes.argtypes = [ctypes.c_void_p]
    lib.adalog_get_memory_bytes.restype = ctypes.c_size_t

    lib.adalog_hash128.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint64)]
    lib.adalog_hash128.restype = None

    lib.adalog_get_matrix_indices.argtypes = [ctypes.c_uint64, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_uint32)]
    lib.adalog_get_matrix_indices.restype = None

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
    def __init__(
        self,
        width: int = 1024,
        depth: int = 4,
        counter_bits: int = 8,
        stash_capacity: int = 64,
        elephant_threshold: int = 20,
        hll_m: int = 1024,
        seed: int = 42,
    ):
        if not lib:
            raise RuntimeError("adalog_core library is not loaded")
        self._ptr = lib.adalog_create_full(
            width, depth, counter_bits, stash_capacity, elephant_threshold, hll_m, seed
        )
        if not self._ptr:
            raise ValueError(f"Failed to initialize AdaLogCore with parameters (w={width}, d={depth}, bits={counter_bits}, scap={stash_capacity})")

    def __del__(self):
        if hasattr(self, "_ptr") and self._ptr and lib:
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

    def top_k(
        self,
        k: int,
        key_registry: dict | None = None,
        return_composite: bool = False,
    ) -> list[tuple[int | tuple[int, int] | str | bytes, int]]:
        """
        Extracts top-k heavy hitters from the resident elephant stash in O(K log k) time.
        By default returns (64-bit primary hash, count) pairs.
        If return_composite=True, returns ((primary_hash_64, tag_31), count) pairs (full 95-bit composite fingerprint).
        If key_registry is provided, maps composite (hash, tag) or hash to original string/bytes key.
        """
        out_hashes = (ctypes.c_uint64 * k)()
        out_tags = (ctypes.c_uint32 * k)()
        out_counts = (ctypes.c_uint64 * k)()
        n = lib.adalog_top_k_composite(self._ptr, k, out_hashes, out_tags, out_counts)
        res = []
        for i in range(n):
            h_val = int(out_hashes[i])
            tag_val = int(out_tags[i])
            c_val = int(out_counts[i])
            composite_fp = (h_val, tag_val)

            if key_registry:
                if composite_fp in key_registry:
                    key_val = key_registry[composite_fp]
                elif h_val in key_registry:
                    key_val = key_registry[h_val]
                else:
                    key_val = composite_fp if return_composite else h_val
            else:
                key_val = composite_fp if return_composite else h_val

            res.append((key_val, c_val))
        return res

    def stash_stats(self) -> dict[str, int]:
        return {
            "count": int(lib.adalog_get_stash_count(self._ptr)),
            "evictions": int(lib.adalog_get_stash_evictions(self._ptr)),
            "rejections": int(lib.adalog_get_stash_rejections(self._ptr)),
        }

    def memory_bytes(self) -> int:
        return int(lib.adalog_get_memory_bytes(self._ptr))

    @staticmethod
    def hash128(key: str | bytes, seed: int = 42) -> tuple[int, int]:
        if not lib:
            raise RuntimeError("adalog_core library is not loaded")
        kb = key.encode("utf-8") if isinstance(key, str) else key
        h1 = ctypes.c_uint64()
        h2 = ctypes.c_uint64()
        lib.adalog_hash128(kb, len(kb), seed, ctypes.byref(h1), ctypes.byref(h2))
        return (int(h1.value), int(h2.value))

    @staticmethod
    def get_matrix_indices(h_low: int, depth: int, width: int) -> list[int]:
        if not lib:
            raise RuntimeError("adalog_core library is not loaded")
        out_indices = (ctypes.c_uint32 * depth)()
        lib.adalog_get_matrix_indices(ctypes.c_uint64(h_low), depth, width, out_indices)
        return [int(out_indices[i]) for i in range(depth)]


class CompiledCMS:
    def __init__(self, width: int = 1024, depth: int = 4, seed: int = 42):
        if not lib:
            raise RuntimeError("adalog_core library is not loaded")
        self._ptr = lib.cms_create(width, depth, seed)
        if not self._ptr:
            raise ValueError("Failed to create CMSCore with given parameters")

    def __del__(self):
        if hasattr(self, "_ptr") and self._ptr and lib:
            lib.cms_destroy(self._ptr)
            self._ptr = None

    def update(self, key: str | bytes, count: int = 1) -> None:
        kb = key.encode("utf-8") if isinstance(key, str) else key
        lib.cms_update(self._ptr, kb, len(kb), count)


class CompiledBloom:
    def __init__(self, m_bits: int = 8192, k_hashes: int = 7, seed: int = 42):
        if not lib:
            raise RuntimeError("adalog_core library is not loaded")
        self._ptr = lib.bloom_create(m_bits, k_hashes, seed)
        if not self._ptr:
            raise ValueError("Failed to create BloomCore with given parameters")

    def __del__(self):
        if hasattr(self, "_ptr") and self._ptr and lib:
            lib.bloom_destroy(self._ptr)
            self._ptr = None

    def add(self, key: str | bytes) -> None:
        kb = key.encode("utf-8") if isinstance(key, str) else key
        lib.bloom_add(self._ptr, kb, len(kb))


class CompiledHLL:
    def __init__(self, p: int = 10, seed: int = 42):
        if not lib:
            raise RuntimeError("adalog_core library is not loaded")
        self._ptr = lib.hll_create(p, seed)
        if not self._ptr:
            raise ValueError("Failed to create HLLCore with given parameters")

    def __del__(self):
        if hasattr(self, "_ptr") and self._ptr and lib:
            lib.hll_destroy(self._ptr)
            self._ptr = None

    def add(self, key: str | bytes) -> None:
        kb = key.encode("utf-8") if isinstance(key, str) else key
        lib.hll_add(self._ptr, kb, len(kb))


class CompiledDisjoint:
    def __init__(self, bf_m: int = 8192, bf_k: int = 7, cms_w: int = 1024, cms_d: int = 4, hll_p: int = 10, seed: int = 42):
        if not lib:
            raise RuntimeError("adalog_core library is not loaded")
        self._ptr = lib.disjoint_create(bf_m, bf_k, cms_w, cms_d, hll_p, seed)
        if not self._ptr:
            raise ValueError("Failed to create DisjointCore with given parameters")

    def __del__(self):
        if hasattr(self, "_ptr") and self._ptr and lib:
            lib.disjoint_destroy(self._ptr)
            self._ptr = None

    def update(self, key: str | bytes, count: int = 1) -> None:
        kb = key.encode("utf-8") if isinstance(key, str) else key
        lib.disjoint_update(self._ptr, kb, len(kb), count)
