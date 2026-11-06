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

// Anti-optimization fence (prevents dead-code elimination and constant folding)
template <class T>
inline __attribute__((always_inline)) void do_not_optimize(T const& value) {
    asm volatile("" : : "g"(value) : "memory");
}

struct QueryBenchmarkResult {
    std::string name;
    std::vector<double> latencies_ns;
    double mean_ns;
    double std_ns;
    double median_ns;
    double p25_ns;
    double p75_ns;
    double iqr_ns;
};

template<typename QueryFn>
QueryBenchmarkResult run_query_benchmark(const std::string& name,
                                         const std::vector<std::string>& keys,
                                         size_t subset_size,
                                         int n_queries,
                                         int n_warmup,
                                         int n_runs,
                                         QueryFn query_fn) {
    // Warm-up runs
    for (int w = 0; w < n_warmup; ++w) {
        for (int i = 0; i < n_queries; ++i) {
            query_fn(keys[i % subset_size]);
        }
    }

    std::vector<double> lats;
    for (int r = 0; r < n_runs; ++r) {
        auto start = std::chrono::high_resolution_clock::now();
        for (int i = 0; i < n_queries; ++i) {
            query_fn(keys[i % subset_size]);
        }
        auto end = std::chrono::high_resolution_clock::now();
        double total_ns = std::chrono::duration<double, std::nano>(end - start).count();
        lats.push_back(total_ns / (double)n_queries);
    }

    std::vector<double> sorted = lats;
    std::sort(sorted.begin(), sorted.end());

    double mean_ns = std::accumulate(lats.begin(), lats.end(), 0.0) / lats.size();
    double sq_sum = 0.0;
    for (double v : lats) sq_sum += (v - mean_ns) * (v - mean_ns);
    double std_ns = std::sqrt(sq_sum / (lats.size() - 1));

    double median_ns = sorted[sorted.size() / 2];
    double p25_ns = sorted[sorted.size() / 4];
    double p75_ns = sorted[(sorted.size() * 3) / 4];
    double iqr_ns = p75_ns - p25_ns;

    return {name, lats, mean_ns, std_ns, median_ns, p25_ns, p75_ns, iqr_ns};
}

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

    // Query Latency Benchmark (10 repetitions x 100,000 queries with anti-optimization fences)
    std::cout << "\nBenchmarking Query Latencies (10 repetitions x 100,000 queries)...\n";
    adalog = new AdaLogCore(6682, 4, 8, 128, 15, 42);
    for (int i = 0; i < 50000; ++i) adalog->update(keys[i].data(), (int)keys[i].size(), 1);

    auto est_res = run_query_benchmark(
        "adalog_estimate", keys, 50000, 100000, n_warmup, n_runs,
        [&](const std::string& k) {
            uint64_t v = adalog->estimate(k.data(), (int)k.size());
            do_not_optimize(v);
        }
    );

    auto contains_res = run_query_benchmark(
        "adalog_contains", keys, 50000, 100000, n_warmup, n_runs,
        [&](const std::string& k) {
            bool v = adalog->contains(k.data(), (int)k.size());
            do_not_optimize(v);
        }
    );
    delete adalog;

    double est_ns = est_res.median_ns;
    double contains_ns = contains_res.median_ns;

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
    printf("Point Query (estimate)   | Median: %5.2f ns | Mean: %5.2f +/- %4.2f ns | IQR: %4.2f ns (10 runs x 100k)\n",
           est_res.median_ns, est_res.mean_ns, est_res.std_ns, est_res.iqr_ns);
    printf("Membership Query (AMQ)   | Median: %5.2f ns | Mean: %5.2f +/- %4.2f ns | IQR: %4.2f ns (10 runs x 100k)\n",
           contains_res.median_ns, contains_res.mean_ns, contains_res.std_ns, contains_res.iqr_ns);

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
    ofs << "    \"estimate_ns_op\": " << est_res.median_ns << ",\n";
    ofs << "    \"contains_ns_op\": " << contains_res.median_ns << ",\n";
    ofs << "    \"estimate_mean_ns\": " << est_res.mean_ns << ",\n";
    ofs << "    \"estimate_std_ns\": " << est_res.std_ns << ",\n";
    ofs << "    \"estimate_iqr_ns\": " << est_res.iqr_ns << ",\n";
    ofs << "    \"contains_mean_ns\": " << contains_res.mean_ns << ",\n";
    ofs << "    \"contains_std_ns\": " << contains_res.std_ns << ",\n";
    ofs << "    \"contains_iqr_ns\": " << contains_res.iqr_ns << "\n";
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
