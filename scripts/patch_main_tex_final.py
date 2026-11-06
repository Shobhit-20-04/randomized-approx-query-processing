# -*- coding: utf-8 -*-
"""Patch paper/main.tex and paper/manuscript/main.tex with final forensic corrections."""
import os

files_to_patch = [
    os.path.join("paper", "main.tex"),
    os.path.join("paper", "manuscript", "main.tex"),
]

for fpath in files_to_patch:
    if not os.path.exists(fpath):
        print(f"Skipping missing file: {fpath}")
        continue

    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Algorithm 1 evictable-set notation
    old_alg_part = r"""        \STATE $\mathcal{E} \leftarrow \{y \in E \mid y.c_{base} + y.c_{exact} < \MV\}$
        \IF{$\mathcal{E} \neq \emptyset$}
            \STATE $e \leftarrow \arg\min_{y \in \mathcal{E}} (y.c_{base} + y.c_{exact})$"""

    new_alg_part = r"""        \STATE $E_{\mathrm{evictable}} \leftarrow \{y \in E \mid y.c_{base} + y.c_{exact} < \MV\}$
        \IF{$E_{\mathrm{evictable}} \neq \emptyset$}
            \STATE $e \leftarrow \arg\min_{y \in E_{\mathrm{evictable}}} (y.c_{base} + y.c_{exact})$"""

    if old_alg_part in content:
        content = content.replace(old_alg_part, new_alg_part)
        print(f"Replaced Algorithm 1 evictable notation in {fpath}")
    else:
        print(f"Algorithm 1 target not found in {fpath}")

    # 2. Theorem 2 proof notation synchronization
    old_thm2_part = r"(\mathcal{E} = \{y \in E \mid y.c_{base} + y.c_{exact} < \MV\} \neq \emptyset\)"
    new_thm2_part = r"(E_{\mathrm{evictable}} = \{y \in E \mid y.c_{base} + y.c_{exact} < \MV\} \neq \emptyset\)"
    content = content.replace(r"(\mathcal{E} = \{y \in E \mid y.c_{base} + y.c_{exact} < \MV\} \neq \emptyset)",
                              r"(E_{\mathrm{evictable}} = \{y \in E \mid y.c_{base} + y.c_{exact} < \MV\} \neq \emptyset)")
    content = content.replace(r"\mathcal{E} = \emptyset", r"E_{\mathrm{evictable}} = \emptyset")
    content = content.replace(r"y \in \mathcal{E}", r"y \in E_{\mathrm{evictable}}")

    # 3. Query Latencies
    # Abstract:
    old_abs_lat = "with 13.0~ns point frequency estimation latency and 26.0~ns approximate membership query latency."
    new_abs_lat = "with 14.0~ns point frequency estimation latency and 13.7~ns approximate membership query latency."
    content = content.replace(old_abs_lat, new_abs_lat)

    # Section V-C:
    old_sec_lat = "Point queries execute in 13.0~ns (frequency estimation) and 26.0~ns (membership testing)"
    new_sec_lat = "Point queries execute in 14.0~ns (frequency estimation) and 13.7~ns (membership testing)"
    content = content.replace(old_sec_lat, new_sec_lat)

    # Conclusion:
    old_concl_lat = "with 26.0~ns/op membership query latency and 13.0~ns/op point estimation latency."
    new_concl_lat = "with 13.7~ns/op membership query latency and 14.0~ns/op point estimation latency."
    content = content.replace(old_concl_lat, new_concl_lat)

    # 4. Dataset Provenance and Contribution 5
    old_contrib5 = r"\item \textbf{Empirical evaluation (Section~\ref{sec:experiments}):} Rigorous benchmarks against budget-matched disjoint and unified baselines across memory sweeps, skew sensitivity, native C++ throughput, and real-world network traces."
    new_contrib5 = r"\item \textbf{Empirical evaluation (Section~\ref{sec:experiments}):} Rigorous benchmarks against budget-matched disjoint and unified baselines across memory sweeps, skew sensitivity, native C++ throughput, synthetic CAIDA-modeled flow traces, and real-world English Gutenberg text."
    content = content.replace(old_contrib5, new_contrib5)

    old_sec5_intro = r"We evaluated AdaLog-Sketch against five baseline architectures on heavy-tailed synthetic streams and real-world network traces:"
    new_sec5_intro = r"We evaluated AdaLog-Sketch against five baseline architectures on heavy-tailed synthetic streams, synthetic CAIDA-modeled flow traces, and real-world English Gutenberg text:"
    content = content.replace(old_sec5_intro, new_sec5_intro)

    # 5. Fig. 1 vs Table II budget range
    old_fig1_text = r"Table~\ref{tab:main} presents multi-task metrics across allocations from 8~KB to 128~KB."
    new_fig1_text = r"Table~\ref{tab:main} details multi-task metrics across embedded operating allocations from 8~KB to 128~KB, while Fig.~\ref{fig:pareto} extends the evaluation up to 512~KB to demonstrate asymptotic scaling."
    content = content.replace(old_fig1_text, new_fig1_text)

    old_fig1_cap = r"\caption{Memory budget sweep comparison across synopses under heavy-tailed Zipfian stream ($\alpha = 1.25, N = 300{,}000$, budgets $8 \dots 512$~KB). (a) Mean Absolute Error (MAE) vs. memory budget; (b) Heavy hitter recovery F1 score ($k = \min(100, K)$ for resident stash; global top-100 heavy hitters for $K \ge 128$).}"
    new_fig1_cap = r"\caption{Memory budget sweep comparison across synopses under heavy-tailed Zipfian stream ($\alpha = 1.25, N = 300{,}000$, budgets $8 \dots 512$~KB, extending beyond Table~\ref{tab:main}'s embedded range to verify asymptotic scaling). (a) Mean Absolute Error (MAE) vs. memory budget; (b) Heavy hitter recovery F1 score ($k = \min(100, K)$ for resident stash; global top-100 heavy hitters for $K \ge 128$).}"
    content = content.replace(old_fig1_cap, new_fig1_cap)

    # 6. Cache locality qualification
    old_cache_p1 = r"To eliminate pointer indirection, zero dynamic memory allocation and strict cache locality, resident entries are identified by their primary 64-bit key fingerprints ($h_1$)"
    new_cache_p1 = r"To eliminate pointer indirection, eliminate dynamic heap allocations, and optimize for cache-line locality, resident entries are identified by their primary 64-bit key fingerprints ($h_1$)"
    content = content.replace(old_cache_p1, new_cache_p1)

    old_cache_p2 = r"eliminates auxiliary hash calls and keeps the state within L1/L2 cache lines."
    new_cache_p2 = r"eliminates auxiliary hash calls and is architected to maximize L1/L2 cache-line locality."
    content = content.replace(old_cache_p2, new_cache_p2)

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Successfully saved patched {fpath}")
