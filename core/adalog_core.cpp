#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>
#include <string>
#include <algorithm>
#include "hash_xxh3.h"

// ============================================================================
// 1. RE-ENGINEERED ADALOG CORE (C++17)
// ============================================================================

struct StashItem {
    uint64_t key_hash;
    uint32_t base_count;
    uint32_t exact_count;
};

class AdaLogCore {
public:
    int width;
    int depth;
    int counter_bits;
    int max_val;
    uint32_t seed;
    uint64_t total_volume;
    
    uint8_t* table8;
    uint16_t* table16;
    uint32_t* table32;
    
    int hll_m;
    int hll_bytes;
    uint8_t* hll_reg;
    double hll_alpha;
    
    bool use_stash;
    int stash_cap;
    uint32_t tau;
    int stash_table_size;
    uint64_t stash_mask;
    uint64_t* stash_keys;
    uint32_t* stash_base;
    uint32_t* stash_exact;
    int stash_count;
    uint64_t stash_insertions;
    uint64_t stash_evictions;
    uint64_t stash_rejections;

    AdaLogCore(int w, int d, int bits, int scap, int thresh, uint32_t s)
        : AdaLogCore(w, d, bits, scap, thresh, 1024, s) {}

    AdaLogCore(int w, int d, int bits, int scap, int thresh, int hll_regs, uint32_t s)
        : width(w), depth(d), counter_bits(bits), seed(s), total_volume(0),
          use_stash(scap > 0), stash_cap(scap), tau(thresh),
          stash_count(0), stash_insertions(0), stash_evictions(0), stash_rejections(0)
    {
        // 1. Configure Counter Matrix
        if (bits == 8) {
            max_val = 255;
            table8 = (uint8_t*)calloc(w * d, sizeof(uint8_t));
            table16 = nullptr;
            table32 = nullptr;
        } else if (bits == 16) {
            max_val = 65535;
            table8 = nullptr;
            table16 = (uint16_t*)calloc(w * d, sizeof(uint16_t));
            table32 = nullptr;
        } else {
            max_val = 0x7FFFFFFF;
            table8 = nullptr;
            table16 = nullptr;
            table32 = (uint32_t*)calloc(w * d, sizeof(uint32_t));
        }

        // 2. Configure Stash (Dynamic Configurable Capacity)
        if (use_stash && scap > 0) {
            // Find power of 2 >= scap
            int tsize = 16;
            while (tsize < scap) {
                tsize <<= 1;
            }
            stash_table_size = tsize;
            stash_mask = (uint64_t)(stash_table_size - 1);
            stash_keys = (uint64_t*)calloc(stash_table_size, sizeof(uint64_t));
            stash_base = (uint32_t*)calloc(stash_table_size, sizeof(uint32_t));
            stash_exact = (uint32_t*)calloc(stash_table_size, sizeof(uint32_t));
        } else {
            stash_table_size = 0;
            stash_mask = 0;
            stash_keys = nullptr;
            stash_base = nullptr;
            stash_exact = nullptr;
        }

        // 3. Configure HyperLogLog Subsketch (Decoupled from width w: default 1024 registers)
        hll_m = (hll_regs > 0) ? hll_regs : 1024;
        hll_bytes = (hll_m * 6 + 7) / 8; // Exactly 768 bytes for m=1024
        hll_reg = (uint8_t*)calloc(hll_bytes, sizeof(uint8_t));

        if (hll_m >= 128) hll_alpha = 0.7213 / (1.0 + 1.079 / hll_m);
        else if (hll_m >= 64) hll_alpha = 0.709;
        else if (hll_m >= 32) hll_alpha = 0.697;
        else hll_alpha = 0.673;
    }



    ~AdaLogCore() {
        if (table8) free(table8);
        if (table16) free(table16);
        if (table32) free(table32);
        if (hll_reg) free(hll_reg);
        if (stash_keys) free(stash_keys);
        if (stash_base) free(stash_base);
        if (stash_exact) free(stash_exact);
    }

    inline uint32_t get_cell(int row, int col) const {
        int idx = row * width + col;
        if (counter_bits == 8) return table8[idx];
        if (counter_bits == 16) return table16[idx];
        return table32[idx];
    }

    inline void set_cell(int row, int col, uint32_t val) {
        int idx = row * width + col;
        uint32_t b_val = (val > (uint32_t)max_val) ? max_val : val;
        if (counter_bits == 8) table8[idx] = (uint8_t)b_val;
        else if (counter_bits == 16) table16[idx] = (uint16_t)b_val;
        else table32[idx] = b_val;
    }

    inline void update_hll(int idx, int rank) {
        int bit_pos = idx * 6;
        int byte_pos = bit_pos >> 3;
        int offset = bit_pos & 7;

        int cur;
        if (offset + 6 <= 8) {
            cur = (hll_reg[byte_pos] >> offset) & 0x3F;
        } else {
            cur = ((hll_reg[byte_pos] | (hll_reg[byte_pos + 1] << 8)) >> offset) & 0x3F;
        }

        if (rank <= cur) return;
        if (rank > 63) rank = 63;

        if (offset + 6 <= 8) {
            uint8_t mask = 0x3F << offset;
            hll_reg[byte_pos] = (hll_reg[byte_pos] & ~mask) | (rank << offset);
        } else {
            uint16_t cur16 = hll_reg[byte_pos] | (hll_reg[byte_pos + 1] << 8);
            uint16_t mask16 = 0x3F << offset;
            cur16 = (cur16 & ~mask16) | (rank << offset);
            hll_reg[byte_pos] = cur16 & 0xFF;
            hll_reg[byte_pos + 1] = (cur16 >> 8) & 0xFF;
        }
    }

    inline int find_stash_slot(uint64_t key_hash) const {
        if (!use_stash || stash_count == 0 || stash_table_size <= 0) return -1;
        int base_slot = (int)(key_hash & stash_mask);
        #pragma GCC unroll 8
        for (int p = 0; p < 8; p++) {
            int slot = (base_slot + p) & (int)stash_mask;
            if (stash_keys[slot] == key_hash) return slot;
            if (stash_keys[slot] == 0) return -1;
        }
        return -1;
    }
    void update(const char* key, int len, uint32_t count) {
        if (count <= 0) return;
        total_volume += count;

        uint64_t h[2];
        murmur3_128(key, len, seed, h);

        uint32_t h1 = (uint32_t)(h[0] & 0xFFFFFFFF);
        uint32_t h2 = (uint32_t)((h[0] >> 32) & 0xFFFFFFFF) | 1;

        // --- Fast Path: 2-Choice Stash Hit ---
        if (use_stash && stash_count > 0 && stash_table_size > 0) {
            int slot1 = (int)(h1 & stash_mask);
            if (stash_keys[slot1] == h[0]) {
                stash_exact[slot1] += count;
                return;
            }
            int slot2 = (int)(h2 & stash_mask);
            if (slot2 == slot1) slot2 = (slot1 + 1) & (int)stash_mask;
            if (stash_keys[slot2] == h[0]) {
                stash_exact[slot2] += count;
                return;
            }
        }

        // --- HLL Cardinality Update ---
        int hll_reg_idx = (int)(h1 % hll_m);
        int clz = (h[1] == 0) ? 64 : __builtin_clzll(h[1]);
        update_hll(hll_reg_idx, clz + 1);

        // --- Matrix Conservative Update ---
        uint32_t v_min = 0xFFFFFFFF;
        uint32_t indices[16];
        for (int j = 0; j < depth; j++) {
            indices[j] = (h1 + j * h2) % width;
            uint32_t v = get_cell(j, indices[j]);
            if (v < v_min) v_min = v;
        }

        uint32_t v_target = (v_min + count > (uint32_t)max_val) ? max_val : (v_min + count);
        for (int j = 0; j < depth; j++) {
            uint32_t cur = get_cell(j, indices[j]);
            if (cur < v_target) {
                set_cell(j, indices[j], v_target);
            }
        }

        // --- Stash Admission & Eviction ---
        if (use_stash && stash_table_size > 0 && v_target >= tau) {
            int slot1 = (int)(h1 & stash_mask);
            int slot2 = (int)(h2 & stash_mask);
            if (slot2 == slot1) slot2 = (slot1 + 1) & (int)stash_mask;

            if (stash_keys[slot1] == h[0] || stash_keys[slot2] == h[0]) {
                return;
            }

            if (stash_keys[slot1] == 0) {
                stash_keys[slot1] = h[0];
                stash_base[slot1] = v_target;
                stash_exact[slot1] = 0;
                stash_count++;
                stash_insertions++;
            } else if (stash_keys[slot2] == 0) {
                stash_keys[slot2] = h[0];
                stash_base[slot2] = v_target;
                stash_exact[slot2] = 0;
                stash_count++;
                stash_insertions++;
            } else {
                // 2-choice eviction policy: compare slot1 vs slot2
                int evict_slot = (stash_base[slot1] + stash_exact[slot1] <= stash_base[slot2] + stash_exact[slot2]) ? slot1 : slot2;
                uint32_t min_tot = stash_base[evict_slot] + stash_exact[evict_slot];

                if (v_target > min_tot) {
                    // Evict min candidate and write back to matrix
                    uint64_t evict_h = stash_keys[evict_slot];
                    uint32_t eh1 = (uint32_t)(evict_h & 0xFFFFFFFF);
                    uint32_t eh2 = (uint32_t)((evict_h >> 32) & 0xFFFFFFFF) | 1;
                    uint32_t wb_val = (min_tot > (uint32_t)max_val) ? max_val : min_tot;

                    for (int j = 0; j < depth; j++) {
                        uint32_t idx = (eh1 + j * eh2) % width;
                        uint32_t cur = get_cell(j, idx);
                        if (wb_val > cur) set_cell(j, idx, wb_val);
                    }

                    stash_keys[evict_slot] = h[0];
                    stash_base[evict_slot] = v_target;
                    stash_exact[evict_slot] = 0;
                    stash_evictions++;
                } else {
                    stash_rejections++;
                }
            }
        }
    }

    uint32_t estimate(const char* key, int len) const {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);

        uint32_t h1 = (uint32_t)(h[0] & 0xFFFFFFFF);
        uint32_t h2 = (uint32_t)((h[0] >> 32) & 0xFFFFFFFF) | 1;

        if (use_stash && stash_count > 0 && stash_table_size > 0) {
            int slot1 = (int)(h1 & stash_mask);
            if (stash_keys[slot1] == h[0]) return stash_base[slot1] + stash_exact[slot1];
            int slot2 = (int)(h2 & stash_mask);
            if (slot2 == slot1) slot2 = (slot1 + 1) & (int)stash_mask;
            if (stash_keys[slot2] == h[0]) return stash_base[slot2] + stash_exact[slot2];
        }

        uint32_t v_min = 0xFFFFFFFF;
        for (int j = 0; j < depth; j++) {
            uint32_t idx = (h1 + j * h2) % width;
            uint32_t val = get_cell(j, idx);
            if (val < v_min) v_min = val;
        }
        return v_min;
    }

    bool contains(const char* key, int len) const {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);

        uint32_t h1 = (uint32_t)(h[0] & 0xFFFFFFFF);
        uint32_t h2 = (uint32_t)((h[0] >> 32) & 0xFFFFFFFF) | 1;

        if (use_stash && stash_count > 0 && stash_table_size > 0) {
            int slot1 = (int)(h1 & stash_mask);
            if (stash_keys[slot1] == h[0]) return true;
            int slot2 = (int)(h2 & stash_mask);
            if (slot2 == slot1) slot2 = (slot1 + 1) & (int)stash_mask;
            if (stash_keys[slot2] == h[0]) return true;
        }

        uint32_t theta = (uint32_t)std::min(254.0, floor(log((double)total_volume / (double)width + 1.0) + 1.0));
        if (theta < 1) theta = 1;

        for (int j = 0; j < depth; j++) {
            uint32_t idx = (h1 + j * h2) % width;
            if (get_cell(j, idx) < theta) return false;
        }
        return true;
    }

    double cardinality() const {
        double z_sum = 0.0;
        int v_zeros = 0;

        for (int i = 0; i < hll_m; i++) {
            int bit_pos = i * 6;
            int byte_pos = bit_pos >> 3;
            int offset = bit_pos & 7;

            int val;
            if (offset + 6 <= 8) {
                val = (hll_reg[byte_pos] >> offset) & 0x3F;
            } else {
                val = ((hll_reg[byte_pos] | (hll_reg[byte_pos + 1] << 8)) >> offset) & 0x3F;
            }

            z_sum += ldexp(1.0, -val);
            if (val == 0) v_zeros++;
        }

        double raw = hll_alpha * (double)hll_m * (double)hll_m / z_sum;
        if (raw <= 2.5 * hll_m) {
            if (v_zeros > 0) return (double)hll_m * log((double)hll_m / (double)v_zeros);
        }
        return raw;
    }

    // Top-k heavy hitter extraction directly from stash
    int get_top_k(int k, uint64_t* out_hashes, uint32_t* out_counts) const {
        if (!use_stash || stash_count == 0 || k <= 0 || stash_table_size == 0) return 0;

        std::vector<std::pair<uint32_t, uint64_t>> candidates;
        candidates.reserve(stash_count);

        for (int i = 0; i < stash_table_size; i++) {
            if (stash_keys[i] != 0) {
                candidates.push_back({stash_base[i] + stash_exact[i], stash_keys[i]});
            }
        }

        std::sort(candidates.begin(), candidates.end(), std::greater<std::pair<uint32_t, uint64_t>>());
        int ret_count = std::min((int)candidates.size(), k);
        for (int i = 0; i < ret_count; i++) {
            out_counts[i] = candidates[i].first;
            out_hashes[i] = candidates[i].second;
        }
        return ret_count;
    }

    size_t get_memory_bytes() const {
        size_t mat_b = (size_t)width * depth * (counter_bits / 8);
        size_t hll_b = (size_t)hll_bytes;
        size_t st_b = (use_stash && stash_table_size > 0) ? 
            ((size_t)stash_table_size * (sizeof(uint64_t) + 2 * sizeof(uint32_t))) : 0;
        return mat_b + hll_b + st_b;
    }
};

// ============================================================================
// 2. COMPILED COUNT-MIN SKETCH WITH CONSERVATIVE UPDATE
// ============================================================================

class CMSCore {
public:
    int width;
    int depth;
    uint32_t* table;
    uint32_t seed;

    CMSCore(int w, int d, uint32_t s) : width(w), depth(d), seed(s) {
        table = (uint32_t*)calloc(w * d, sizeof(uint32_t));
    }
    ~CMSCore() { free(table); }

    void update(const char* key, int len, uint32_t count) {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);
        uint32_t h1 = (uint32_t)(h[0] & 0xFFFFFFFF);
        uint32_t h2 = (uint32_t)((h[0] >> 32) & 0xFFFFFFFF) | 1;

        uint32_t v_min = 0xFFFFFFFF;
        uint32_t indices[16];
        for (int j = 0; j < depth; j++) {
            indices[j] = (h1 + j * h2) % width;
            uint32_t v = table[j * width + indices[j]];
            if (v < v_min) v_min = v;
        }

        uint32_t v_target = v_min + count;
        for (int j = 0; j < depth; j++) {
            uint32_t idx = j * width + indices[j];
            if (table[idx] < v_target) {
                table[idx] = v_target;
            }
        }
    }

    uint32_t estimate(const char* key, int len) const {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);
        uint32_t h1 = (uint32_t)(h[0] & 0xFFFFFFFF);
        uint32_t h2 = (uint32_t)((h[0] >> 32) & 0xFFFFFFFF) | 1;

        uint32_t v_min = 0xFFFFFFFF;
        for (int j = 0; j < depth; j++) {
            uint32_t idx = (h1 + j * h2) % width;
            uint32_t v = table[j * width + idx];
            if (v < v_min) v_min = v;
        }
        return v_min;
    }
};

// ============================================================================
// 3. COMPILED BLOOM FILTER
// ============================================================================

class BloomCore {
public:
    int m_bits;
    int k_hashes;
    uint32_t seed;
    uint8_t* bit_array;

    BloomCore(int m, int k, uint32_t s) : m_bits(m), k_hashes(k), seed(s) {
        bit_array = (uint8_t*)calloc((m + 7) / 8, sizeof(uint8_t));
    }
    ~BloomCore() { free(bit_array); }

    void add(const char* key, int len) {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);
        uint32_t h1 = (uint32_t)(h[0] & 0xFFFFFFFF);
        uint32_t h2 = (uint32_t)((h[0] >> 32) & 0xFFFFFFFF) | 1;

        for (int i = 0; i < k_hashes; i++) {
            uint32_t bit_idx = (h1 + i * h2) % m_bits;
            bit_array[bit_idx >> 3] |= (1 << (bit_idx & 7));
        }
    }

    bool contains(const char* key, int len) const {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);
        uint32_t h1 = (uint32_t)(h[0] & 0xFFFFFFFF);
        uint32_t h2 = (uint32_t)((h[0] >> 32) & 0xFFFFFFFF) | 1;

        for (int i = 0; i < k_hashes; i++) {
            uint32_t bit_idx = (h1 + i * h2) % m_bits;
            if (!(bit_array[bit_idx >> 3] & (1 << (bit_idx & 7)))) return false;
        }
        return true;
    }
};

// ============================================================================
// 4. COMPILED HYPERLOGLOG (6-BIT REGISTERS)
// ============================================================================

class HLLCore {
public:
    int p;
    int m;
    uint32_t seed;
    uint8_t* registers;
    double alpha;

    HLLCore(int precision, uint32_t s) : p(precision), seed(s) {
        m = 1 << p;
        registers = (uint8_t*)calloc(m, sizeof(uint8_t));
        if (m >= 128) alpha = 0.7213 / (1.0 + 1.079 / m);
        else if (m >= 64) alpha = 0.709;
        else if (m >= 32) alpha = 0.697;
        else alpha = 0.673;
    }
    ~HLLCore() { free(registers); }

    void add(const char* key, int len) {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);
        int idx = (int)(h[0] & (m - 1));
        int clz = (h[1] == 0) ? 64 : __builtin_clzll(h[1]);
        uint8_t rank = (uint8_t)(clz + 1);
        if (rank > registers[idx]) registers[idx] = rank;
    }

    double cardinality() const {
        double z_sum = 0.0;
        int v_zeros = 0;
        for (int i = 0; i < m; i++) {
            z_sum += ldexp(1.0, -registers[i]);
            if (registers[i] == 0) v_zeros++;
        }
        double raw = alpha * (double)m * (double)m / z_sum;
        if (raw <= 2.5 * m && v_zeros > 0) return (double)m * log((double)m / (double)v_zeros);
        return raw;
    }
};

// ============================================================================
// 5. COMPILED DISJOINT STACK
// ============================================================================

class DisjointCore {
public:
    BloomCore bf;
    CMSCore cms;
    HLLCore hll;

    DisjointCore(int bf_m, int bf_k, int cms_w, int cms_d, int hll_p, uint32_t s)
        : bf(bf_m, bf_k, s), cms(cms_w, cms_d, s ^ 0x55555555), hll(hll_p, s ^ 0xAAAAAAAA) {}

    void update(const char* key, int len, uint32_t count) {
        bf.add(key, len);
        cms.update(key, len, count);
        hll.add(key, len);
    }
};

// ============================================================================
// EXPORTED C API FOR BINDINGS
// ============================================================================

extern "C" {
    __declspec(dllexport) void* adalog_create(int width, int depth, int bits, int scap, int thresh, uint32_t seed) {
        return new AdaLogCore(width, depth, bits, scap, thresh, 1024, seed);
    }
    __declspec(dllexport) void* adalog_create_full(int width, int depth, int bits, int scap, int thresh, int hll_m, uint32_t seed) {
        return new AdaLogCore(width, depth, bits, scap, thresh, hll_m, seed);
    }
    __declspec(dllexport) void adalog_destroy(void* ptr) {
        delete (AdaLogCore*)ptr;
    }
    __declspec(dllexport) void adalog_update(void* ptr, const char* key, int len, uint32_t count) {
        ((AdaLogCore*)ptr)->update(key, len, count);
    }
    __declspec(dllexport) uint32_t adalog_estimate(void* ptr, const char* key, int len) {
        return ((AdaLogCore*)ptr)->estimate(key, len);
    }
    __declspec(dllexport) bool adalog_contains(void* ptr, const char* key, int len) {
        return ((AdaLogCore*)ptr)->contains(key, len);
    }
    __declspec(dllexport) double adalog_cardinality(void* ptr) {
        return ((AdaLogCore*)ptr)->cardinality();
    }
    __declspec(dllexport) int adalog_top_k(void* ptr, int k, uint64_t* out_hashes, uint32_t* out_counts) {
        return ((AdaLogCore*)ptr)->get_top_k(k, out_hashes, out_counts);
    }
    __declspec(dllexport) int adalog_get_stash_count(void* ptr) {
        return ((AdaLogCore*)ptr)->stash_count;
    }
    __declspec(dllexport) uint64_t adalog_get_stash_evictions(void* ptr) {
        return ((AdaLogCore*)ptr)->stash_evictions;
    }
    __declspec(dllexport) uint64_t adalog_get_stash_rejections(void* ptr) {
        return ((AdaLogCore*)ptr)->stash_rejections;
    }
    __declspec(dllexport) size_t adalog_get_memory_bytes(void* ptr) {
        return ((AdaLogCore*)ptr)->get_memory_bytes();
    }
    __declspec(dllexport) void adalog_hash128(const char* key, int len, uint32_t seed, uint64_t* out_h1, uint64_t* out_h2) {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);
        if (out_h1) *out_h1 = h[0];
        if (out_h2) *out_h2 = h[1];
    }

    // CMS
    __declspec(dllexport) void* cms_create(int width, int depth, uint32_t seed) {
        return new CMSCore(width, depth, seed);
    }
    __declspec(dllexport) void cms_destroy(void* ptr) {
        delete (CMSCore*)ptr;
    }
    __declspec(dllexport) void cms_update(void* ptr, const char* key, int len, uint32_t count) {
        ((CMSCore*)ptr)->update(key, len, count);
    }

    // Bloom
    __declspec(dllexport) void* bloom_create(int m, int k, uint32_t seed) {
        return new BloomCore(m, k, seed);
    }
    __declspec(dllexport) void bloom_destroy(void* ptr) {
        delete (BloomCore*)ptr;
    }
    __declspec(dllexport) void bloom_add(void* ptr, const char* key, int len) {
        ((BloomCore*)ptr)->add(key, len);
    }

    // HLL
    __declspec(dllexport) void* hll_create(int p, uint32_t seed) {
        return new HLLCore(p, seed);
    }
    __declspec(dllexport) void hll_destroy(void* ptr) {
        delete (HLLCore*)ptr;
    }
    __declspec(dllexport) void hll_add(void* ptr, const char* key, int len) {
        ((HLLCore*)ptr)->add(key, len);
    }

    // Disjoint Stack
    __declspec(dllexport) void* disjoint_create(int bf_m, int bf_k, int cms_w, int cms_d, int hll_p, uint32_t seed) {
        return new DisjointCore(bf_m, bf_k, cms_w, cms_d, hll_p, seed);
    }
    __declspec(dllexport) void disjoint_destroy(void* ptr) {
        delete (DisjointCore*)ptr;
    }
    __declspec(dllexport) void disjoint_update(void* ptr, const char* key, int len, uint32_t count) {
        ((DisjointCore*)ptr)->update(key, len, count);
    }
}
