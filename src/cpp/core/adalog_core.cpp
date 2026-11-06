#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>
#include <queue>
#include <string>
#include <algorithm>
#include <stdexcept>
#include "hash_murmur3.h"

// ============================================================================
// 1. RE-ENGINEERED ADALOG CORE (C++17)
// ============================================================================

struct StashItem {
    uint64_t key_hash;    // 8 bytes: primary 64-bit hash (Lane 0)
    uint32_t tag;         // 4 bytes: MSB (0x80000000U) is occupied flag; lower 31 bits are secondary tag (Lane 1)
    uint32_t base_count;  // 4 bytes: baseline matrix counter value at promotion
    uint64_t exact_count; // 8 bytes: 64-bit exact increments while resident in stash
    // Total: exactly 24 bytes per entry, natural 8-byte alignment, zero padding bytes.

    static constexpr uint32_t OCCUPIED_MASK = 0x80000000U;
    static constexpr uint32_t TAG_MASK = 0x7FFFFFFFU;

    inline bool is_occupied() const { return (tag & OCCUPIED_MASK) != 0; }
    inline uint32_t get_tag() const { return tag & TAG_MASK; }
    inline void set(uint64_t kh, uint32_t t, uint32_t base, uint64_t exact) {
        key_hash = kh;
        tag = (t & TAG_MASK) | OCCUPIED_MASK;
        base_count = base;
        exact_count = exact;
    }
    inline void clear() {
        key_hash = 0;
        tag = 0;
        base_count = 0;
        exact_count = 0;
    }
    inline uint64_t total() const {
        uint64_t bc = base_count;
        uint64_t ec = exact_count;
        return (ec > UINT64_MAX - bc) ? UINT64_MAX : (bc + ec);
    }
};

static_assert(sizeof(StashItem) == 24, "StashItem must be exactly 24 bytes");

class AdaLogCore {
public:
    int width;
    int depth;
    int counter_bits;
    uint32_t max_val;
    uint32_t seed;
    uint64_t total_volume;

    uint8_t* table8;
    uint16_t* table16;
    uint32_t* table32;

    int hll_m;
    int hll_p;
    int hll_bytes;
    uint8_t* hll_reg;
    double hll_alpha;

    bool use_stash;
    int stash_cap;
    uint32_t tau;
    StashItem* stash_items;   // Exactly 24 bytes per slot, single contiguous array
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
        // Parameter Validation
        if (w <= 0) {
            throw std::invalid_argument("AdaLogCore width must be positive");
        }
        if (d <= 0 || d > 64) {
            throw std::invalid_argument("AdaLogCore depth must be between 1 and 64");
        }
        if (bits != 8 && bits != 16 && bits != 32) {
            throw std::invalid_argument("AdaLogCore counter_bits must be 8, 16, or 32");
        }
        if (scap < 0) {
            throw std::invalid_argument("AdaLogCore stash_capacity cannot be negative");
        }
        if (scap > 1000000) {
            throw std::invalid_argument("AdaLogCore stash_cap exceeds maximum supported capacity (1,000,000)");
        }
        if (thresh < 0) {
            throw std::invalid_argument("AdaLogCore tau cannot be negative");
        }
        if (hll_regs < 16 || hll_regs > 262144) {
            throw std::invalid_argument("AdaLogCore hll_regs must be between 16 and 262144 (precision p in [4, 18])");
        }

        uint64_t total_cells = (uint64_t)w * (uint64_t)d;
        if (total_cells / (uint64_t)w != (uint64_t)d || total_cells > 2000000000ULL) {
            throw std::invalid_argument("AdaLogCore matrix allocation size overflow");
        }

        // 1. Configure Counter Matrix
        if (bits == 8) {
            max_val = 255U;
            table8 = (uint8_t*)calloc(w * d, sizeof(uint8_t));
            table16 = nullptr;
            table32 = nullptr;
        } else if (bits == 16) {
            max_val = 65535U;
            table8 = nullptr;
            table16 = (uint16_t*)calloc(w * d, sizeof(uint16_t));
            table32 = nullptr;
        } else {
            max_val = 0xFFFFFFFFU;
            table8 = nullptr;
            table16 = nullptr;
            table32 = (uint32_t*)calloc(w * d, sizeof(uint32_t));
        }

        // 2. Configure Fully Associative Stash (Genuinely 24 bytes per slot)
        if (use_stash && scap > 0) {
            stash_items = (StashItem*)calloc(stash_cap, sizeof(StashItem));
        } else {
            stash_items = nullptr;
        }

        // 3. Configure Decoupled HyperLogLog Subsketch
        hll_m = (hll_regs > 0) ? hll_regs : 1024;
        hll_p = 4;
        while ((1 << hll_p) < hll_m) {
            hll_p++;
        }
        hll_m = 1 << hll_p; // Align to power of two
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
        if (stash_items) free(stash_items);
    }

    inline uint32_t get_cell(int row, int col) const {
        int idx = row * width + col;
        if (counter_bits == 8) return table8[idx];
        if (counter_bits == 16) return table16[idx];
        return table32[idx];
    }

    inline void set_cell(int row, int col, uint32_t val) {
        int idx = row * width + col;
        uint32_t b_val = (val > max_val) ? max_val : val;
        if (counter_bits == 8) table8[idx] = (uint8_t)b_val;
        else if (counter_bits == 16) table16[idx] = (uint16_t)b_val;
        else table32[idx] = b_val;
    }

    inline void update_hll(int idx, int rank) {
        if (idx < 0 || idx >= hll_m) return;
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

    // Fully associative search over stash_cap slots
    inline int find_stash_slot(uint64_t key_hash, uint32_t tag) const {
        if (!use_stash || stash_count == 0) return -1;
        uint32_t t_match = tag & StashItem::TAG_MASK;
        for (int i = 0; i < stash_cap; i++) {
            if (stash_items[i].is_occupied() &&
                stash_items[i].key_hash == key_hash &&
                stash_items[i].get_tag() == t_match) {
                return i;
            }
        }
        return -1;
    }

    void update(const char* key, int len, uint64_t count) {
        if (count <= 0) return;
        // Saturating total_volume accumulation
        if (total_volume > UINT64_MAX - count) {
            total_volume = UINT64_MAX;
        } else {
            total_volume += count;
        }

        uint64_t h[2];
        murmur3_128(key, len, seed, h);

        // 64-bit arithmetic prevents intermediate 32-bit integer overflow before modulo
        uint64_t h1 = (uint64_t)(h[0] & 0xFFFFFFFFULL);
        uint64_t h2 = (uint64_t)((h[0] >> 32) & 0xFFFFFFFFULL) | 1ULL;
        uint32_t tag = (uint32_t)(h[1] & 0xFFFFFFFFULL);

        // --- Fast Path: Fully Associative Stash Hit ---
        if (use_stash && stash_count > 0) {
            int slot = find_stash_slot(h[0], tag);
            if (slot >= 0) {
                // Saturating 64-bit addition prevents integer overflow
                if (stash_items[slot].exact_count > UINT64_MAX - count) {
                    stash_items[slot].exact_count = UINT64_MAX;
                } else {
                    stash_items[slot].exact_count += count;
                }
                return;
            }
        }

        // --- HLL Cardinality Update (Aligned bit-for-bit with Python) ---
        int rem = 64 - hll_p;
        int hll_reg_idx = (int)(h[1] >> rem) & (hll_m - 1);
        uint64_t w_bits = h[1] & ((1ULL << rem) - 1);
        int rank = (w_bits == 0) ? (rem + 1) : (__builtin_clzll(w_bits) - hll_p + 1);
        if (rank > 63) rank = 63;
        update_hll(hll_reg_idx, rank);

        // --- Matrix Conservative Update with 64-bit Index Calculation ---
        uint32_t v_min = 0xFFFFFFFFU;
        uint32_t indices[64];
        for (int j = 0; j < depth; j++) {
            indices[j] = (uint32_t)((h1 + (uint64_t)j * h2) % (uint64_t)width);
            uint32_t v = get_cell(j, indices[j]);
            if (v < v_min) v_min = v;
        }

        uint64_t v_target_64 = (uint64_t)v_min + (uint64_t)count;
        uint32_t v_target = (v_target_64 > (uint64_t)max_val) ? max_val : (uint32_t)v_target_64;

        // --- Sequence A: Fully Associative Stash Promotion (Bypasses Matrix Write) ---
        // An item qualifies for promotion when candidate frequency reaches tau: v_min + count >= tau
        if (use_stash && stash_cap > 0 && v_target_64 >= (uint64_t)tau) {
            // Case A: Stash not full - admit into first open slot
            if (stash_count < stash_cap) {
                for (int i = 0; i < stash_cap; i++) {
                    if (!stash_items[i].is_occupied()) {
                        uint32_t base = (v_min > max_val) ? max_val : v_min;
                        stash_items[i].set(h[0], tag, base, count);
                        stash_count++;
                        stash_insertions++;
                        return; // Sequence A: Stash admitted, bypass matrix update!
                    }
                }
            }

            // Case B: Stash full - globally find non-saturated victim with minimum total count
            int evict_slot = -1;
            uint64_t min_tot = UINT64_MAX;
            for (int i = 0; i < stash_cap; i++) {
                if (stash_items[i].is_occupied()) {
                    uint64_t tot = stash_items[i].total();
                    if (tot < (uint64_t)max_val && tot < min_tot) {
                        min_tot = tot;
                        evict_slot = i;
                    }
                }
            }

            uint64_t candidate_tot = (count > UINT64_MAX - (uint64_t)v_min) ? UINT64_MAX : ((uint64_t)v_min + count);
            if (evict_slot >= 0 && candidate_tot > min_tot) {
                // Lossless monotonic write-back to matrix using 64-bit row indexing
                uint64_t evict_h = stash_items[evict_slot].key_hash;
                uint64_t eh1 = (uint64_t)(evict_h & 0xFFFFFFFFULL);
                uint64_t eh2 = (uint64_t)((evict_h >> 32) & 0xFFFFFFFFULL) | 1ULL;
                uint32_t wb_val = (min_tot > (uint64_t)max_val) ? max_val : (uint32_t)min_tot;

                for (int j = 0; j < depth; j++) {
                    uint32_t idx = (uint32_t)((eh1 + (uint64_t)j * eh2) % (uint64_t)width);
                    uint32_t cur = get_cell(j, idx);
                    if (wb_val > cur) set_cell(j, idx, wb_val);
                }

                uint32_t base = (v_min > max_val) ? max_val : v_min;
                stash_items[evict_slot].set(h[0], tag, base, count);
                stash_evictions++;
                return; // Sequence A: Victim written back, candidate admitted, bypass matrix update!
            } else {
                stash_rejections++;
                // Saturated / heavy stash: candidate cannot evict, falls through to matrix update below
            }
        }

        // --- Matrix Conservative Update with 64-bit Index Calculation ---
        // Executed only for unpromoted items (below tau or rejected from full saturated stash)
        for (int j = 0; j < depth; j++) {
            uint32_t cur = get_cell(j, indices[j]);
            if (cur < v_target) {
                set_cell(j, indices[j], v_target);
            }
        }
    }

    uint64_t estimate(const char* key, int len) const {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);

        uint64_t h1 = (uint64_t)(h[0] & 0xFFFFFFFFULL);
        uint64_t h2 = (uint64_t)((h[0] >> 32) & 0xFFFFFFFFULL) | 1ULL;
        uint32_t tag = (uint32_t)(h[1] & 0xFFFFFFFFULL);

        if (use_stash && stash_count > 0) {
            int slot = find_stash_slot(h[0], tag);
            if (slot >= 0) {
                return stash_items[slot].total();
            }
        }

        uint32_t v_min = 0xFFFFFFFFU;
        for (int j = 0; j < depth; j++) {
            uint32_t idx = (uint32_t)((h1 + (uint64_t)j * h2) % (uint64_t)width);
            uint32_t val = get_cell(j, idx);
            if (val < v_min) v_min = val;
        }
        return (uint64_t)v_min;
    }

    // Zero false negatives guaranteed: AMQ returns true iff in stash or all d matrix cells > 0
    bool contains(const char* key, int len) const {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);

        uint64_t h1 = (uint64_t)(h[0] & 0xFFFFFFFFULL);
        uint64_t h2 = (uint64_t)((h[0] >> 32) & 0xFFFFFFFFULL) | 1ULL;
        uint32_t tag = (uint32_t)(h[1] & 0xFFFFFFFFULL);

        if (use_stash && stash_count > 0) {
            if (find_stash_slot(h[0], tag) >= 0) return true;
        }

        for (int j = 0; j < depth; j++) {
            uint32_t idx = (uint32_t)((h1 + (uint64_t)j * h2) % (uint64_t)width);
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

    // Top-k heavy hitter extraction directly from stash.
    // API Contract: Returns 64-bit primary key fingerprints (h1) and exact counts.
    // In hardware/kernel environments where dynamic string memory allocation is avoided,
    // keys are identified by their 64-bit hash; an application-level key registry
    // maps hashes to original string keys when human-readable labels are required.
    int get_top_k(int k, uint64_t* out_hashes, uint64_t* out_counts) const {
        if (!use_stash || stash_count == 0 || k <= 0) return 0;

        // O(K log k) extraction using a size-k min-heap of pairs (count, key_hash)
        using Entry = std::pair<uint64_t, uint64_t>;
        std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> min_heap;

        for (int i = 0; i < stash_cap; i++) {
            if (stash_items[i].is_occupied()) {
                Entry e = {stash_items[i].total(), stash_items[i].key_hash};
                if ((int)min_heap.size() < k) {
                    min_heap.push(e);
                } else if (e.first > min_heap.top().first) {
                    min_heap.pop();
                    min_heap.push(e);
                }
            }
        }

        int ret_count = (int)min_heap.size();
        // Extract elements in descending order (largest first)
        for (int i = ret_count - 1; i >= 0; i--) {
            out_counts[i] = min_heap.top().first;
            out_hashes[i] = min_heap.top().second;
            min_heap.pop();
        }
        return ret_count;
    }

    // Actual allocated memory bytes: matrix + packed HLL + exactly 24 bytes per stash slot
    size_t get_memory_bytes() const {
        size_t mat_b = (size_t)width * depth * (counter_bits / 8);
        size_t hll_b = (size_t)hll_bytes;
        // Exactly 24 bytes per slot via sizeof(StashItem):
        // 8B key_hash + 4B tag (with MSB occupancy bit) + 4B base + 8B exact = 24B
        size_t st_b = (use_stash && stash_cap > 0) ? ((size_t)stash_cap * sizeof(StashItem)) : 0;
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
        if (w <= 0 || d <= 0 || d > 64) {
            throw std::invalid_argument("CMSCore parameters invalid");
        }
        table = (uint32_t*)calloc(w * d, sizeof(uint32_t));
    }
    ~CMSCore() { free(table); }

    void update(const char* key, int len, uint64_t count) {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);
        uint64_t h1 = (uint64_t)(h[0] & 0xFFFFFFFFULL);
        uint64_t h2 = (uint64_t)((h[0] >> 32) & 0xFFFFFFFFULL) | 1ULL;

        uint32_t v_min = 0xFFFFFFFFU;
        uint32_t indices[64];
        for (int j = 0; j < depth; j++) {
            indices[j] = (uint32_t)((h1 + (uint64_t)j * h2) % (uint64_t)width);
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
        uint64_t h1 = (uint64_t)(h[0] & 0xFFFFFFFFULL);
        uint64_t h2 = (uint64_t)((h[0] >> 32) & 0xFFFFFFFFULL) | 1ULL;

        uint32_t v_min = 0xFFFFFFFFU;
        for (int j = 0; j < depth; j++) {
            uint32_t idx = (uint32_t)((h1 + (uint64_t)j * h2) % (uint64_t)width);
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
        if (m <= 0 || k <= 0 || k > 64) {
            throw std::invalid_argument("BloomCore parameters invalid");
        }
        bit_array = (uint8_t*)calloc((m + 7) / 8, sizeof(uint8_t));
    }
    ~BloomCore() { free(bit_array); }

    void add(const char* key, int len) {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);
        uint64_t h1 = (uint64_t)(h[0] & 0xFFFFFFFFULL);
        uint64_t h2 = (uint64_t)((h[0] >> 32) & 0xFFFFFFFFULL) | 1ULL;

        for (int i = 0; i < k_hashes; i++) {
            uint32_t bit_idx = (uint32_t)((h1 + (uint64_t)i * h2) % (uint64_t)m_bits);
            bit_array[bit_idx >> 3] |= (1 << (bit_idx & 7));
        }
    }

    bool contains(const char* key, int len) const {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);
        uint64_t h1 = (uint64_t)(h[0] & 0xFFFFFFFFULL);
        uint64_t h2 = (uint64_t)((h[0] >> 32) & 0xFFFFFFFFULL) | 1ULL;

        for (int i = 0; i < k_hashes; i++) {
            uint32_t bit_idx = (uint32_t)((h1 + (uint64_t)i * h2) % (uint64_t)m_bits);
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
        if (p < 4 || p > 18) {
            throw std::invalid_argument("HLLCore precision must be between 4 and 18");
        }
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
        int rem = 64 - p;
        int idx = (int)(h[1] >> rem) & (m - 1);
        uint64_t w_bits = h[1] & ((1ULL << rem) - 1);
        int rank = (w_bits == 0) ? (rem + 1) : (__builtin_clzll(w_bits) - p + 1);
        if (rank > 63) rank = 63;
        if (rank > registers[idx]) registers[idx] = (uint8_t)rank;
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

    void update(const char* key, int len, uint64_t count) {
        bf.add(key, len);
        cms.update(key, len, count);
        hll.add(key, len);
    }
};

// ============================================================================
// EXPORTED C API FOR BINDINGS
// ============================================================================

#if defined(_WIN32) || defined(__CYGWIN__)
  #define ADALOG_API __declspec(dllexport)
#else
  #define ADALOG_API __attribute__((visibility("default")))
#endif

extern "C" {
    ADALOG_API void* adalog_create(int width, int depth, int bits, int scap, int thresh, uint32_t seed) {
        try {
            return new AdaLogCore(width, depth, bits, scap, thresh, 1024, seed);
        } catch (...) {
            return nullptr;
        }
    }
    ADALOG_API void* adalog_create_full(int width, int depth, int bits, int scap, int thresh, int hll_m, uint32_t seed) {
        try {
            return new AdaLogCore(width, depth, bits, scap, thresh, hll_m, seed);
        } catch (...) {
            return nullptr;
        }
    }
    ADALOG_API void adalog_destroy(void* ptr) {
        delete (AdaLogCore*)ptr;
    }
    ADALOG_API void adalog_update(void* ptr, const char* key, int len, uint64_t count) {
        if (ptr) ((AdaLogCore*)ptr)->update(key, len, count);
    }
    ADALOG_API uint64_t adalog_estimate(void* ptr, const char* key, int len) {
        if (!ptr) return 0;
        return ((AdaLogCore*)ptr)->estimate(key, len);
    }
    ADALOG_API bool adalog_contains(void* ptr, const char* key, int len) {
        if (!ptr) return false;
        return ((AdaLogCore*)ptr)->contains(key, len);
    }
    ADALOG_API double adalog_cardinality(void* ptr) {
        if (!ptr) return 0.0;
        return ((AdaLogCore*)ptr)->cardinality();
    }
    ADALOG_API int adalog_top_k(void* ptr, int k, uint64_t* out_hashes, uint64_t* out_counts) {
        if (!ptr) return 0;
        return ((AdaLogCore*)ptr)->get_top_k(k, out_hashes, out_counts);
    }
    ADALOG_API int adalog_get_stash_count(void* ptr) {
        if (!ptr) return 0;
        return ((AdaLogCore*)ptr)->stash_count;
    }
    ADALOG_API uint64_t adalog_get_stash_evictions(void* ptr) {
        if (!ptr) return 0;
        return ((AdaLogCore*)ptr)->stash_evictions;
    }
    ADALOG_API uint64_t adalog_get_stash_rejections(void* ptr) {
        if (!ptr) return 0;
        return ((AdaLogCore*)ptr)->stash_rejections;
    }
    ADALOG_API size_t adalog_get_memory_bytes(void* ptr) {
        if (!ptr) return 0;
        return ((AdaLogCore*)ptr)->get_memory_bytes();
    }
    ADALOG_API void adalog_hash128(const char* key, int len, uint32_t seed, uint64_t* out_h1, uint64_t* out_h2) {
        uint64_t h[2];
        murmur3_128(key, len, seed, h);
        if (out_h1) *out_h1 = h[0];
        if (out_h2) *out_h2 = h[1];
    }
    // Native row-index function (Issue 2)
    ADALOG_API void adalog_get_matrix_indices(uint64_t h_low, int depth, int width, uint32_t* out_indices) {
        if (width <= 0 || depth <= 0 || !out_indices) return;
        uint64_t h1 = (uint64_t)(h_low & 0xFFFFFFFFULL);
        uint64_t h2 = (uint64_t)((h_low >> 32) & 0xFFFFFFFFULL) | 1ULL;
        for (int j = 0; j < depth; j++) {
            out_indices[j] = (uint32_t)((h1 + (uint64_t)j * h2) % (uint64_t)width);
        }
    }

    // CMS
    ADALOG_API void* cms_create(int width, int depth, uint32_t seed) {
        try {
            return new CMSCore(width, depth, seed);
        } catch (...) {
            return nullptr;
        }
    }
    ADALOG_API void cms_destroy(void* ptr) {
        delete (CMSCore*)ptr;
    }
    ADALOG_API void cms_update(void* ptr, const char* key, int len, uint32_t count) {
        if (ptr) ((CMSCore*)ptr)->update(key, len, count);
    }
    ADALOG_API uint32_t cms_estimate(void* ptr, const char* key, int len) {
        if (!ptr) return 0;
        return ((CMSCore*)ptr)->estimate(key, len);
    }

    // Bloom
    ADALOG_API void* bloom_create(int m, int k, uint32_t seed) {
        try {
            return new BloomCore(m, k, seed);
        } catch (...) {
            return nullptr;
        }
    }
    ADALOG_API void bloom_destroy(void* ptr) {
        delete (BloomCore*)ptr;
    }
    ADALOG_API void bloom_add(void* ptr, const char* key, int len) {
        if (ptr) ((BloomCore*)ptr)->add(key, len);
    }
    ADALOG_API bool bloom_contains(void* ptr, const char* key, int len) {
        if (!ptr) return false;
        return ((BloomCore*)ptr)->contains(key, len);
    }

    // HLL
    ADALOG_API void* hll_create(int p, uint32_t seed) {
        try {
            return new HLLCore(p, seed);
        } catch (...) {
            return nullptr;
        }
    }
    ADALOG_API void hll_destroy(void* ptr) {
        delete (HLLCore*)ptr;
    }
    ADALOG_API void hll_add(void* ptr, const char* key, int len) {
        if (ptr) ((HLLCore*)ptr)->add(key, len);
    }
    ADALOG_API double hll_cardinality(void* ptr) {
        if (!ptr) return 0.0;
        return ((HLLCore*)ptr)->cardinality();
    }

    // Disjoint Stack
    ADALOG_API void* disjoint_create(int bf_m, int bf_k, int cms_w, int cms_d, int hll_p, uint32_t seed) {
        try {
            return new DisjointCore(bf_m, bf_k, cms_w, cms_d, hll_p, seed);
        } catch (...) {
            return nullptr;
        }
    }
    ADALOG_API void disjoint_destroy(void* ptr) {
        delete (DisjointCore*)ptr;
    }
    ADALOG_API void disjoint_update(void* ptr, const char* key, int len, uint32_t count) {
        if (ptr) ((DisjointCore*)ptr)->update(key, len, count);
    }
}
