#ifndef ADALOG_CORE_H
#define ADALOG_CORE_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(_WIN32) || defined(_WIN64)
    #define ADALOG_EXPORT __declspec(dllexport)
#else
    #define ADALOG_EXPORT __attribute__((visibility("default")))
#endif

// Opaque synopsis handle
typedef void* AdaLogHandle;

// Lifecycle
ADALOG_EXPORT AdaLogHandle adalog_create(int width, int depth, int counter_bits, int stash_capacity, int elephant_threshold, int hll_regs, uint32_t seed);
ADALOG_EXPORT void adalog_destroy(AdaLogHandle handle);

// Operations
ADALOG_EXPORT void adalog_update(AdaLogHandle handle, const char* key, int len, uint64_t count);
ADALOG_EXPORT uint64_t adalog_estimate(AdaLogHandle handle, const char* key, int len);
ADALOG_EXPORT bool adalog_contains(AdaLogHandle handle, const char* key, int len);
ADALOG_EXPORT double adalog_cardinality(AdaLogHandle handle);
ADALOG_EXPORT void adalog_decay(AdaLogHandle handle, double decay_factor);

// Telemetry & Extraction
ADALOG_EXPORT int adalog_get_top_k(AdaLogHandle handle, int k, uint64_t* out_hashes, uint64_t* out_counts);
ADALOG_EXPORT size_t adalog_get_memory_bytes(AdaLogHandle handle);
ADALOG_EXPORT uint64_t adalog_get_stash_count(AdaLogHandle handle);
ADALOG_EXPORT uint64_t adalog_get_stash_insertions(AdaLogHandle handle);
ADALOG_EXPORT uint64_t adalog_get_stash_evictions(AdaLogHandle handle);
ADALOG_EXPORT uint64_t adalog_get_stash_rejections(AdaLogHandle handle);
ADALOG_EXPORT uint64_t adalog_get_total_volume(AdaLogHandle handle);

// Diagnostics & Verification
ADALOG_EXPORT void adalog_get_matrix_indices(uint64_t h_low, int depth, int width, uint32_t* out_indices);
ADALOG_EXPORT void adalog_hash128(const char* key, int len, uint32_t seed, uint64_t* out_h);

#ifdef __cplusplus
}
#endif

#endif // ADALOG_CORE_H
