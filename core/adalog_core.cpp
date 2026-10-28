#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>
#include <string>
#include <algorithm>
#include "hash_xxh3.h"

// ============================================================================
// 1. COMPILED ADALOG CORE
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
    static const int STASH_TABLE_SIZE = 128;
    uint64_t stash_keys[STASH_TABLE_SIZE];
    uint32_t stash_base[STASH_TABLE_SIZE];
    uint32_t stash_exact[STASH_TABLE_SIZE];
    int stash_count;

    AdaLogCore(int w, int d, int bits, int scap, int thresh, uint32_t s)
        : width(w), depth(d), counter_bits(bits), seed(s), use_stash(scap > 0), stash_cap(scap), tau(thresh)
    {
        memset(stash_keys, 0, sizeof(stash_keys));
        memset(stash_base, 0, sizeof(stash_base));
        memset(stash_exact, 0, sizeof(stash_exact));
        stash_count = 0;

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

        hll_m = w;
        hll_bytes = (hll_m * 6 + 7) / 8;
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

    void update(const char* key, int len, uint32_t count) {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);

        if (use_stash && stash_count > 0) {
            int slot1 = h[0] & (STASH_TABLE_SIZE - 1);
            if (stash_keys[slot1] == h[0]) {
                stash_exact[slot1] += count;
                return;
            }
            int slot2 = (slot1 + 1) & (STASH_TABLE_SIZE - 1);
            if (stash_keys[slot2] == h[0]) {
                stash_exact[slot2] += count;
                return;
            }
        }

        uint32_t h1 = (uint32_t)(h[0] & 0xFFFFFFFF);
        uint32_t h2 = (uint32_t)((h[0] >> 32) & 0xFFFFFFFF) | 1;

        int col0 = h1 % width;
        int clz = (h[1] == 0) ? 64 : __builtin_clzll(h[1]);
        update_hll(col0, clz + 1);

        uint32_t v_min = 0xFFFFFFFF;
        uint32_t indices[16];
        for (int j = 0; j < depth; j++) {
            indices[j] = (h1 + j * h2) % width;
            uint32_t v = get_cell(j, indices[j]);
            if (v < v_min) v_min = v;
        }

        uint32_t v_new = (v_min + count > (uint32_t)max_val) ? max_val : (v_min + count);
        for (int j = 0; j < depth; j++) {
            if (get_cell(j, indices[j]) == v_min) {
                set_cell(j, indices[j], v_new);
            }
        }

        if (use_stash && v_new >= tau) {
            int slot1 = h[0] & (STASH_TABLE_SIZE - 1);
            int slot2 = (slot1 + 1) & (STASH_TABLE_SIZE - 1);

            if (stash_keys[slot1] == h[0] || stash_keys[slot2] == h[0]) {
                // Already stashed
            } else if (stash_keys[slot1] == 0) {
                stash_keys[slot1] = h[0];
                stash_base[slot1] = v_new;
                stash_exact[slot1] = 0;
                stash_count++;
            } else if (stash_keys[slot2] == 0) {
                stash_keys[slot2] = h[0];
                stash_base[slot2] = v_new;
                stash_exact[slot2] = 0;
                stash_count++;
            } else {
                int evict_slot = (stash_base[slot1] + stash_exact[slot1] <= stash_base[slot2] + stash_exact[slot2]) ? slot1 : slot2;
                uint32_t min_tot = stash_base[evict_slot] + stash_exact[evict_slot];
                if (v_new > min_tot) {
                    uint64_t evict_h = stash_keys[evict_slot];
                    uint32_t eh1 = (uint32_t)(evict_h & 0xFFFFFFFF);
                    uint32_t eh2 = (uint32_t)((evict_h >> 32) & 0xFFFFFFFF) | 1;
                    for (int j = 0; j < depth; j++) {
                        uint32_t idx = (eh1 + j * eh2) % width;
                        uint32_t cur = get_cell(j, idx);
                        if (min_tot > cur) set_cell(j, idx, min_tot);
                    }
                    stash_keys[evict_slot] = h[0];
                    stash_base[evict_slot] = v_new;
                    stash_exact[evict_slot] = 0;
                }
            }
        }
    }

    uint32_t estimate(const char* key, int len) const {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);

        if (use_stash && stash_count > 0) {
            int slot1 = h[0] & (STASH_TABLE_SIZE - 1);
            if (stash_keys[slot1] == h[0]) return stash_base[slot1] + stash_exact[slot1];
            int slot2 = (slot1 + 1) & (STASH_TABLE_SIZE - 1);
            if (stash_keys[slot2] == h[0]) return stash_base[slot2] + stash_exact[slot2];
        }

        uint32_t h1 = (uint32_t)(h[0] & 0xFFFFFFFF);
        uint32_t h2 = (uint32_t)((h[0] >> 32) & 0xFFFFFFFF) | 1;

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

        if (use_stash && stash_count > 0) {
            int slot1 = h[0] & (STASH_TABLE_SIZE - 1);
            if (stash_keys[slot1] == h[0]) return true;
            int slot2 = (slot1 + 1) & (STASH_TABLE_SIZE - 1);
            if (stash_keys[slot2] == h[0]) return true;
        }

        uint32_t h1 = (uint32_t)(h[0] & 0xFFFFFFFF);
        uint32_t h2 = (uint32_t)((h[0] >> 32) & 0xFFFFFFFF) | 1;

        for (int j = 0; j < depth; j++) {
            uint32_t idx = (h1 + j * h2) % width;
            if (get_cell(j, idx) == 0) return false;
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

        uint32_t v_new = v_min + count;
        for (int j = 0; j < depth; j++) {
            if (table[j * width + indices[j]] == v_min) {
                table[j * width + indices[j]] = v_new;
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
    uint8_t* bit_array;
    uint32_t seed;

    BloomCore(int m, int k, uint32_t s) : m_bits(m), k_hashes(k), seed(s) {
        int bytes = (m + 7) / 8;
        bit_array = (uint8_t*)calloc(bytes, sizeof(uint8_t));
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
// 4. COMPILED HYPERLOGLOG
// ============================================================================

class HLLCore {
public:
    int p;
    int m;
    uint8_t* registers;
    double alpha;
    uint32_t seed;

    HLLCore(int prec, uint32_t s) : p(prec), m(1 << prec), seed(s) {
        registers = (uint8_t*)calloc(m, sizeof(uint8_t));
        if (m >= 128) alpha = 0.7213 / (1.0 + 1.079 / m);
        else if (m >= 64) alpha = 0.709;
        else alpha = 0.697;
    }
    ~HLLCore() { free(registers); }

    void add(const char* key, int len) {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);
        int idx = h[0] & (m - 1);
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
// 5. COMPILED DISJOINT STACK (RUNS BF + CMS-CU + HLL SIMULTANEOUSLY)
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
// EXPORTED C API
// ============================================================================

extern "C" {
    __declspec(dllexport) void* adalog_create(int width, int depth, int bits, int scap, int thresh, uint32_t seed) {
        return new AdaLogCore(width, depth, bits, scap, thresh, seed);
    }
    __declspec(dllexport) void adalog_destroy(void* ptr) { delete (AdaLogCore*)ptr; }
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

    // CMS
    __declspec(dllexport) void* cms_create(int width, int depth, uint32_t seed) {
        return new CMSCore(width, depth, seed);
    }
    __declspec(dllexport) void cms_destroy(void* ptr) { delete (CMSCore*)ptr; }
    __declspec(dllexport) void cms_update(void* ptr, const char* key, int len, uint32_t count) {
        ((CMSCore*)ptr)->update(key, len, count);
    }

    // Bloom
    __declspec(dllexport) void* bloom_create(int m, int k, uint32_t seed) {
        return new BloomCore(m, k, seed);
    }
    __declspec(dllexport) void bloom_destroy(void* ptr) { delete (BloomCore*)ptr; }
    __declspec(dllexport) void bloom_add(void* ptr, const char* key, int len) {
        ((BloomCore*)ptr)->add(key, len);
    }

    // HLL
    __declspec(dllexport) void* hll_create(int p, uint32_t seed) {
        return new HLLCore(p, seed);
    }
    __declspec(dllexport) void hll_destroy(void* ptr) { delete (HLLCore*)ptr; }
    __declspec(dllexport) void hll_add(void* ptr, const char* key, int len) {
        ((HLLCore*)ptr)->add(key, len);
    }

    // Disjoint Stack
    __declspec(dllexport) void* disjoint_create(int bf_m, int bf_k, int cms_w, int cms_d, int hll_p, uint32_t seed) {
        return new DisjointCore(bf_m, bf_k, cms_w, cms_d, hll_p, seed);
    }
    __declspec(dllexport) void disjoint_destroy(void* ptr) { delete (DisjointCore*)ptr; }
    __declspec(dllexport) void disjoint_update(void* ptr, const char* key, int len, uint32_t count) {
        ((DisjointCore*)ptr)->update(key, len, count);
    }
}
