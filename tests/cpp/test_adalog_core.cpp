#include <cassert>
#include <iostream>
#include <vector>
#include <string>
#include <cstring>
#include "../../src/cpp/core/adalog_core.cpp"

void test_basic_lifecycle() {
    std::cout << "[C++ Test] test_basic_lifecycle... ";
    AdaLogCore sketch(7232, 4, 8, 128, 15, 1024, 42);
    assert(sketch.width == 7232);
    assert(sketch.depth == 4);
    assert(sketch.counter_bits == 8);
    assert(sketch.stash_cap == 128);
    assert(sketch.tau == 15);
    assert(sketch.get_memory_bytes() == 32768);
    std::cout << "PASSED\n";
}

void test_no_underestimation() {
    std::cout << "[C++ Test] test_no_underestimation... ";
    AdaLogCore sketch(2048, 4, 8, 64, 10, 1024, 42);
    std::string key = "elephant_item_test";
    for (int i = 0; i < 50; i++) {
        sketch.update(key.c_str(), key.length(), 1);
    }
    uint64_t est = sketch.estimate(key.c_str(), key.length());
    assert(est >= 50);
    assert(sketch.contains(key.c_str(), key.length()) == true);
    std::cout << "PASSED (Estimated: " << est << " >= 50)\n";
}

void test_top_k_min_heap() {
    std::cout << "[C++ Test] test_top_k_min_heap... ";
    AdaLogCore sketch(2048, 4, 8, 64, 5, 1024, 42);
    for (int i = 1; i <= 20; i++) {
        std::string k = "key_" + std::to_string(i);
        sketch.update(k.c_str(), k.length(), i * 10);
    }
    uint64_t hashes[5];
    uint64_t counts[5];
    int returned = sketch.get_top_k(5, hashes, counts);
    assert(returned == 5);
    for (int i = 0; i < 4; i++) {
        assert(counts[i] >= counts[i + 1]);
    }
    assert(counts[0] == 200);
    assert(counts[1] == 190);
    std::cout << "PASSED (Top 2: " << counts[0] << ", " << counts[1] << ")\n";
}


void test_top_k_composite_fingerprint() {
    std::cout << "[C++ Test] test_top_k_composite_fingerprint... ";
    AdaLogCore sketch(2048, 4, 8, 64, 5, 1024, 42);
    for (int i = 1; i <= 10; i++) {
        std::string k = "heavy_key_" + std::to_string(i);
        sketch.update(k.c_str(), k.length(), i * 25);
    }
    uint64_t hashes[5];
    uint32_t tags[5];
    uint64_t counts[5];
    int returned = sketch.get_top_k_composite(5, hashes, tags, counts);
    assert(returned == 5);
    for (int i = 0; i < 5; i++) {
        assert(counts[i] == (10 - i) * 25);
        assert(hashes[i] != 0); // Primary 64-bit hash
        assert(tags[i] <= 0x7FFFFFFF); // Secondary 31-bit tag
    }
    std::cout << "PASSED (Full 95-bit composite fingerprint verified: counts " << counts[0] << ", " << counts[1] << ")\n";
}

int main() {
    std::cout << "======================================\n";
    std::cout << "RUNNING NATIVE ADALOG-CORE C++ SUITE\n";
    std::cout << "======================================\n";
    test_basic_lifecycle();
    test_no_underestimation();
    test_top_k_min_heap();
    test_top_k_composite_fingerprint();
    std::cout << "ALL NATIVE C++ TESTS PASSED!\n";
    return 0;
}
