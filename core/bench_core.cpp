#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <algorithm>
#include <numeric>
#include <fstream>
#include <cmath>
#include <functional>

// Include core classes directly
#include "adalog_core.cpp"

struct BenchmarkResult {
    std::string name;
    std::vector<double> latencies_ns;
    std::vector<double> throughputs_mops;
    double mean_ns;
    double std_ns;
    double median_ns;
    double p25_ns;
    double p75_ns;
    double iqr_ns;
    double mean_mops;
    double std_mops;
};

template<typename ResetFn, typename UpdateFn>
BenchmarkResult run_benchmark(const std::string& name, 
                              const std::vector<std::string>& keys, 
                              int n_warmup, 
                              int n_runs, 
                              ResetFn reset_fn, 
                              UpdateFn update_fn) {
    size_t n_keys = keys.size();

    // Warm-up runs
    for (int w = 0; w < n_warmup; ++w) {
        reset_fn();
        for (const auto& k : keys) {
            update_fn(k.data(), (int)k.size());
        }
    }

    std::vector<double> lats;
    std::vector<double> mops;

    for (int r = 0; r < n_runs; ++r) {
        reset_fn();
        auto start = std::chrono::high_resolution_clock::now();
        for (const auto& k : keys) {
            update_fn(k.data(), (int)k.size());
        }
        auto end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double, std::nano> diff = end - start;
        double total_ns = diff.count();
        double ns_per_op = total_ns / (double)n_keys;
        double mops_val = ((double)n_keys / (total_ns / 1e9)) / 1e6;

        lats.push_back(ns_per_op);
        mops.push_back(mops_val);
    }

    std::vector<double> sorted_lats = lats;
    std::sort(sorted_lats.begin(), sorted_lats.end());

    double mean_ns = std::accumulate(lats.begin(), lats.end(), 0.0) / lats.size();
    double sq_sum = 0.0;
    for (double v : lats) sq_sum += (v - mean_ns) * (v - mean_ns);
    double std_ns = std::sqrt(sq_sum / (lats.size() - 1));

    double median_ns = sorted_lats[sorted_lats.size() / 2];
    double p25_ns = sorted_lats[sorted_lats.size() / 4];
    double p75_ns = sorted_lats[(sorted_lats.size() * 3) / 4];
    double iqr_ns = p75_ns - p25_ns;

    double mean_mops = std::accumulate(mops.begin(), mops.end(), 0.0) / mops.size();
    double sq_mops = 0.0;
    for (double v : mops) sq_mops += (v - mean_mops) * (v - mean_mops);
    double std_mops = std::sqrt(sq_mops / (mops.size() - 1));

    BenchmarkResult res;
    res.name = name;
    res.latencies_ns = lats;
    res.throughputs_mops = mops;
    res.mean_ns = mean_ns;
    res.std_ns = std_ns;
    res.median_ns = median_ns;
    res.p25_ns = p25_ns;
    res.p75_ns = p75_ns;
    res.iqr_ns = iqr_ns;
    res.mean_mops = mean_mops;
    res.std_mops = std_mops;
    return res;
}

int main(int argc, char* argv[]) {
    int n_keys = 1000000;
    int n_runs = 10;
    int n_warmup = 2;
    std::string out_path = "results/raw/exp3_latency_benchmark.json";
    if (argc > 1) out_path = argv[1];

    std::cout << "=================================================================\n";
    std::cout << " NATIVE C++ INGESTION LATENCY & THROUGHPUT BENCHMARK (" << n_keys << " ops)\n";
    std::cout << "=================================================================\n";

    std::cout << "Pre-generating " << n_keys << " keys in memory...\n";
    std::vector<std::string> keys;
    keys.reserve(n_keys);
    for (int i = 0; i < n_keys; ++i) {
        keys.push_back("key_" + std::to_string(i % 50000) + "_test");
    }

    // 1. AdaLog-Core (32 KB: w=6682, d=4, bits=8, stash=128, tau=15)
    AdaLogCore* adalog = nullptr;
    auto adalog_res = run_benchmark(
        "AdaLog-Core", keys, n_warmup, n_runs,
        [&]() { if (adalog) delete adalog; adalog = new AdaLogCore(6682, 4, 8, 128, 15, 42); },
        [&](const char* k, int len) { adalog->update(k, len, 1); }
    );
    if (adalog) { delete adalog; adalog = nullptr; }

    // 2. Disjoint-Core (32 KB: BF=6.4KB, CMS=24.8KB, HLL=768B)
    DisjointCore* disjoint = nullptr;
    auto disjoint_res = run_benchmark(
        "Disjoint-Core", keys, n_warmup, n_runs,
        [&]() { if (disjoint) delete disjoint; disjoint = new DisjointCore(6400 * 8, 4, 3100, 4, 10, 42); },
        [&](const char* k, int len) { disjoint->update(k, len, 1); }
    );
    if (disjoint) { delete disjoint; disjoint = nullptr; }

    // 3. CMS-Core (Standalone CMS-CU)
    CMSCore* cms = nullptr;
    auto cms_res = run_benchmark(
        "CMS-Core", keys, n_warmup, n_runs,
        [&]() { if (cms) delete cms; cms = new CMSCore(8192, 4, 42); },
        [&](const char* k, int len) { cms->update(k, len, 1); }
    );
    if (cms) { delete cms; cms = nullptr; }

    // 4. Bloom-Core (Standalone BF)
    BloomCore* bloom = nullptr;
    auto bloom_res = run_benchmark(
        "Bloom-Core", keys, n_warmup, n_runs,
        [&]() { if (bloom) delete bloom; bloom = new BloomCore(32768 * 8, 4, 42); },
        [&](const char* k, int len) { bloom->add(k, len); }
    );
    if (bloom) { delete bloom; bloom = nullptr; }

    // 5. HLL-Core (Standalone HLL)
    HLLCore* hll = nullptr;
    auto hll_res = run_benchmark(
        "HLL-Core", keys, n_warmup, n_runs,
        [&]() { if (hll) delete hll; hll = new HLLCore(10, 42); },
        [&](const char* k, int len) { hll->add(k, len); }
    );
    if (hll) { delete hll; hll = nullptr; }

    // Query Latency Benchmark
    std::cout << "\nBenchmarking Query Latencies...\n";
    adalog = new AdaLogCore(6682, 4, 8, 128, 15, 42);
    for (int i = 0; i < 50000; ++i) adalog->update(keys[i].data(), (int)keys[i].size(), 1);

    auto q_start = std::chrono::high_resolution_clock::now();
    volatile uint32_t sum = 0;
    for (int i = 0; i < 100000; ++i) {
        sum += adalog->estimate(keys[i % 50000].data(), (int)keys[i % 50000].size());
    }
    auto q_end = std::chrono::high_resolution_clock::now();
    double est_ns = std::chrono::duration<double, std::nano>(q_end - q_start).count() / 100000.0;

    auto amq_start = std::chrono::high_resolution_clock::now();
    volatile bool amq_hit = false;
    for (int i = 0; i < 100000; ++i) {
        amq_hit = amq_hit || adalog->contains(keys[i % 50000].data(), (int)keys[i % 50000].size());
    }
    auto amq_end = std::chrono::high_resolution_clock::now();
    double contains_ns = std::chrono::duration<double, std::nano>(amq_end - amq_start).count() / 100000.0;
    delete adalog;

    std::vector<BenchmarkResult> all_results;
    all_results.push_back(adalog_res);
    all_results.push_back(disjoint_res);
    all_results.push_back(cms_res);
    all_results.push_back(bloom_res);
    all_results.push_back(hll_res);

    std::cout << "\n----------------------------------------------------------------------------------------------------\n";
    std::cout << "Kernel                       | Throughput (Mops/s)  | Update Latency (ns)   | Median (ns) | IQR (ns)\n";
    std::cout << "----------------------------------------------------------------------------------------------------\n";
    for (const auto& r : all_results) {
        printf("%-28s | %6.2f +/- %5.2f     | %6.1f +/- %5.1f ns   | %6.1f ns    | %6.1f ns\n",
               r.name.c_str(), r.mean_mops, r.std_mops, r.mean_ns, r.std_ns, r.median_ns, r.iqr_ns);
    }
    std::cout << "----------------------------------------------------------------------------------------------------\n";
    printf("Point Query Latency (estimate) : %6.1f ns/op\n", est_ns);
    printf("Membership Query Latency (AMQ) : %6.1f ns/op\n", contains_ns);

    // Save JSON output
    std::ofstream ofs(out_path);
    ofs << "{\n";
    for (size_t i = 0; i < all_results.size(); ++i) {
        const auto& r = all_results[i];
        ofs << "  \"" << r.name << "\": {\n";
        ofs << "    \"name\": \"" << r.name << "\",\n";
        ofs << "    \"mean_mops\": " << r.mean_mops << ",\n";
        ofs << "    \"std_mops\": " << r.std_mops << ",\n";
        ofs << "    \"mean_ns_op\": " << r.mean_ns << ",\n";
        ofs << "    \"std_ns_op\": " << r.std_ns << ",\n";
        ofs << "    \"median_ns_op\": " << r.median_ns << ",\n";
        ofs << "    \"iqr_ns_op\": " << r.iqr_ns << ",\n";
        ofs << "    \"p25_ns_op\": " << r.p25_ns << ",\n";
        ofs << "    \"p75_ns_op\": " << r.p75_ns << ",\n";
        ofs << "    \"raw_latencies_ns\": [";
        for (size_t j = 0; j < r.latencies_ns.size(); ++j) {
            ofs << r.latencies_ns[j] << (j + 1 < r.latencies_ns.size() ? ", " : "");
        }
        ofs << "],\n";
        ofs << "    \"raw_throughputs_mops\": [";
        for (size_t j = 0; j < r.throughputs_mops.size(); ++j) {
            ofs << r.throughputs_mops[j] << (j + 1 < r.throughputs_mops.size() ? ", " : "");
        }
        ofs << "]\n";
        ofs << "  },\n";
    }
    ofs << "  \"query_latencies\": {\n";
    ofs << "    \"estimate_ns_op\": " << est_ns << ",\n";
    ofs << "    \"contains_ns_op\": " << contains_ns << "\n";
    ofs << "  },\n";
    ofs << "  \"summary\": {\n";
    ofs << "    \"speedup_vs_disjoint\": " << (disjoint_res.mean_ns / adalog_res.mean_ns) << ",\n";
    ofs << "    \"latency_reduction_pct\": " << ((disjoint_res.mean_ns - adalog_res.mean_ns) / disjoint_res.mean_ns * 100.0) << "\n";
    ofs << "  }\n";
    ofs << "}\n";
    ofs.close();

    std::cout << "\nResults successfully written to " << out_path << "\n";
    return 0;
}
