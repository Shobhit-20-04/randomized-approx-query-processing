"""Update discussion text in paper/main.tex to align with newly generated experimental data.
"""

import os

MAIN_TEX = os.path.abspath("paper/main.tex")
with open(MAIN_TEX, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update Exp 1 Discussion (Pareto & Memory Comparison)
old_exp1_text = r"""Fig.~\ref{fig:pareto}(a) plots the memory Pareto curves across architectures. Up to 64~KB, AdaLog-Sketch achieves the lowest raw MAE. At 32~KB, it reaches an MAE of 0.40, versus 2.51 for the Disjoint Stack with 16-bit CU ($6.28\times$ lower) and 1.90 for Elastic Sketch ($4.75\times$ lower).

\textbf{128 KB Crossover (Elastic Wins):} At 128~KB, Elastic Sketch reaches a lower MAE (0.05) than AdaLog-Sketch (0.10). Once the matrix is sufficiently wide ($w>30{,}000$), base collision noise approaches zero, reducing the marginal gain of the stash. Elastic Sketch's heavy part dedicates more bits directly to primary flow counters at large budgets.

\subsection{Equal-Accuracy Memory Comparison}
Table~\ref{tab:eq} evaluates memory footprint required to reach an identical accuracy threshold ($\mathrm{MAE}\le 0.40$). AdaLog-Sketch requires about 27.3\% less memory than a 16-bit Conservative Update stack and 57.9\% less than a classical 32-bit stack to reach equivalent frequency precision."""

new_exp1_text = r"""Fig.~\ref{fig:pareto}(a) plots the memory Pareto curves across architectures with 95\% confidence error bars across 10 random seeds. Across all budgets up to 128~KB, AdaLog-Sketch ($K=128$) achieves the lowest frequency estimation error. At 32~KB, it reaches an MAE of 0.61 $\pm$ 0.00, versus 3.31 $\pm$ 0.22 for Disjoint Stack with 16-bit CU ($5.43\times$ lower error) and 2.69 $\pm$ 0.02 for Elastic Sketch ($4.41\times$ lower error). The Disjoint+Stash ablation reaches 0.92 $\pm$ 0.01, demonstrating that unifying Bloom filter memory into the primary CMS matrix yields an additional 33.7\% error reduction beyond the stash alone.

\textbf{Underestimation Guarantees ($K \ge K_{sat}$):} With $K=128 \ge \max(K_{sat})$, AdaLog-Sketch records strictly 0 underestimations across all 10 evaluation seeds and all memory allocations, empirically validating Theorem~\ref{thm:conservative}. Conversely, the 16-bit disjoint baseline records 1 underestimation per run because its top heavy key ($f \approx 68{,}000$) exceeds the 16-bit saturation limit (65,535).

\subsection{Equal-Accuracy Memory Comparison}
Table~\ref{tab:eq} reports the exact memory footprint required by each structure to reach an identical accuracy target ($\mathrm{MAE}\le 0.40$), computed via empirical binary search over memory budgets. AdaLog-Sketch requires only 37.8~KB, yielding a 64.1\% memory reduction compared to the 16-bit Disjoint Stack (105.2~KB), $>$ 85.2\% reduction versus the 32-bit Disjoint Stack ($>$ 256~KB), and a 53.0\% reduction versus Elastic Sketch (80.5~KB)."""

text = text.replace(old_exp1_text, new_exp1_text)

# 2. Update Exp 2 Discussion (Head vs Tail Breakdown)
old_exp2_text = r"""\textbf{Why Disjoint Error Rises While Elastic and AdaLog Fall:} In the disjoint stack without a stash, higher skew concentrates more mass in the top few keys. When an infrequent tail item collides with a dominant key, its counter picks up a large spike, raising Disjoint MAE from 2.51 at $\alpha=1.25$ to 10.14 at $\alpha=1.50$. Sketches with an elephant stash (AdaLog) or heavy part (Elastic) intercept heavy keys. As skew increases, the stash absorbs a larger share of total volume, so residual volume entering the base matrix ($N_{res}=N-V_{stash}$) drops sharply. Matrix collision noise falls accordingly, driving AdaLog MAE down from 1.53 at $\alpha=1.05$ to 0.02 at $\alpha=1.50$."""

new_exp2_text = r"""\textbf{Per-Key Error Decomposition (Head vs. Tail):} As skew parameter $\alpha$ increases from 1.05 to 1.50, the disjoint stack exhibits a non-monotonic error trajectory: overall MAE decreases from 10.82 to 3.24 between $\alpha=1.05$ and $\alpha=1.35$, but sharply rises to 9.11 at $\alpha=1.50$. Decomposing errors across keys reveals the root cause: tail collision error monotonically decreases from 10.84 to 0.29 because fewer elements populate the tail. However, error on the top-100 head keys explodes from 0.03 at $\alpha=1.05$ to 496.14 at $\alpha=1.50$. Under extreme skew, top flows exceed 16-bit saturation and collide with one another in the un-stashed matrix. In contrast, AdaLog-Sketch absorbs all heavy keys into its 32-bit associative elephant stash, isolating matrix counters from head collisions and driving overall MAE monotonically down to 0.034 at $\alpha=1.50$ (a 99.6\% error reduction, $267.9\times$ lower error vs. Disjoint)."""

text = text.replace(old_exp2_text, new_exp2_text)

# 3. Update Exp 3 Discussion (Tight C++ Benchmark)
old_exp3_text = r"""\subsection{Exp 3: Native Compiled C++ Latency \& Throughput}
Table~\ref{tab:lat} and Fig.~\ref{fig:lat} present benchmarks for the native compiled C++ kernel executing 1,000,000 streaming operations. AdaLog-Core reaches an update throughput of 1.92~Mops/s (522.0~ns/op), comparable to the disjoint C++ baseline (1.88~Mops/s, 532.3~ns/op); the 1.9\% difference is within measurement noise. While AdaLog-Sketch eliminates multiple hash computations, updating $d$ matrix rows across cache lines and checking the stash balance the throughput."""

new_exp3_text = r"""\subsection{Exp 3: Native Compiled C++ Latency \& Throughput}
Table~\ref{tab:lat} and Fig.~\ref{fig:lat} present tight-loop execution benchmarks evaluated in native compiled C++ across 1,000,000 pre-generated stream keys in memory (warm-up followed by 10 measured runs, reporting mean, std, median, and IQR). AdaLog-Core reaches an update throughput of 22.22 $\pm$ 0.46~Mops/s (45.0 $\pm$ 0.9~ns/op, median 44.7~ns, IQR 1.4~ns), sustaining 9.6\% higher throughput than the Disjoint C++ baseline (20.27 $\pm$ 0.24~Mops/s, 49.3 $\pm$ 0.6~ns/op). Evaluating single-purpose components in isolation reveals standalone CMS-CU at 29.02~Mops/s (34.5~ns/op), Bloom filter at 85.81~Mops/s (11.7~ns/op), and packed HLL at 165.28~Mops/s (6.1~ns/op). AdaLog-Sketch executes point frequency queries in 12.8~ns/op and membership checks in 0.2~ns/op."""

text = text.replace(old_exp3_text, new_exp3_text)

# 4. Update Exp 4 Discussion (Ablation Matrix)
old_exp4_text = r"""\subsection{Exp 4: Systematic Component Ablations}
Table~\ref{tab:abl} isolates each architectural mechanism under an identical 32~KB budget:
\begin{itemize}
\item \textbf{Coupled vs. Decoupled HLL:} Decoupled HLL ($m=1024$) achieves $\mathrm{MAE}=0.40$ and $\mathrm{FPR}=47.11\%$. The Coupled layout ($m=w$) yields $\mathrm{MAE}=0.54$ and $\mathrm{FPR}=55.89\%$.
\item \textbf{Stash Isolation:} Removing the stash inflates MAE by $29.1\times$ ($0.54 \to 15.71$).
\item \textbf{Conservative Update:} Disabling CU increases MAE by $2.37\times$ ($0.54 \to 1.28$).
\item \textbf{Narrow Counters:} 16-bit counters reduce column width by 60\% and raise MAE to 1.71; 32-bit counters raise MAE to 5.48.
\item \textbf{Membership Variant B:} Adding an explicit 1-bit plane narrows matrix width ($w=7{,}200$), maintains MAE at 0.54, and yields 99.91\% FPR at 32~KB.
\end{itemize}"""

new_exp4_text = r"""\subsection{Exp 4: Systematic Component Ablations}
Table~\ref{tab:abl} isolates each architectural mechanism under an identical 32~KB budget across 10 independent random seeds:
\begin{itemize}
\item \textbf{Coupled vs. Decoupled HLL:} Decoupled HLL ($m=1024$) dedicates 768~B to registers, yielding matrix width $w=7{,}232$, $\mathrm{MAE}=0.61 \pm 0.00$, and cardinality $\mathrm{RSE}=0.0424$. The Coupled layout ($m=w=6{,}251$) achieves superior cardinality precision ($\mathrm{RSE}=0.0152$, conforming to Flajolet's bound $1.04/\sqrt{6251}=0.0131$), but slightly narrows counter width, increasing frequency MAE to 0.83 $\pm$ 0.01.
\item \textbf{Elephant Stash Isolation:} Removing the elephant stash forces all heavy flows directly into the counter matrix, inflating MAE by $18.7\times$ ($0.61 \to 11.42 \pm 0.06$) and increasing peak overestimation error from 18 to 34.
\item \textbf{Conservative Update:} Disabling CU increases collision error across all $d$ rows unconditionally, elevating MAE by $2.49\times$ ($0.61 \to 1.52 \pm 0.02$).
\item \textbf{Narrow Counter Scaling:} Allocating 16-bit counters halves matrix width ($w=3{,}616$), raising MAE to 2.41 $\pm$ 0.02. Allocating 32-bit counters quarters matrix width ($w=1{,}808$), raising MAE to 7.53 $\pm$ 0.06 ($12.3\times$ higher error than 8-bit counters), confirming the thesis that saturating 8-bit cells maximize width.
\item \textbf{Membership Variant B (1-bit Presence Plane):} Dedicating $w/8$ bytes to an explicit presence plane reduces matrix width to $w=7{,}012$ ($\mathrm{MAE}=0.66 \pm 0.01$). When 18,700 distinct stream keys map into 7,012 bits, bit saturation causes 99.99\% FPR, demonstrating that single-bit planes require dynamic scaling or decoupled allocation under high stream cardinality.
\end{itemize}"""

text = text.replace(old_exp4_text, new_exp4_text)

# 5. Add Subsection VI.F: Real Word Streams & Failure-Mode Analysis
old_sec_future = r"""\subsection{Future Work with Real-World Streaming Datasets}
While our evaluations used synthetic Zipfian streams across multiple seeds and skews, future work will benchmark AdaLog-Sketch on real-world stream traces, such as CAIDA Internet backbone traces, Wikimedia pageview logs, and Twitter stream feeds. Testing against real-world traffic will evaluate robustness against non-stationary multi-modal distributions, temporal locality, and adversarial key insertions."""

new_sec_real = r"""\subsection{Real Word Stream Evaluation \& Failure-Mode Analysis}
\textbf{Real Natural-Language Word Stream:} We evaluated AdaLog-Sketch on a classic stream of 300,000 text tokens exhibiting natural linguistic Zipfian rank frequencies across 24,939 unique vocabulary items. At a 32~KB budget, AdaLog-Sketch achieved an MAE of 3.18 with stash occupancy 98/128, outperforming the Disjoint Stack (MAE = 12.55) by $3.95\times$.

\textbf{Failure-Mode Characterization (Where AdaLog Does Not Win):} Under low skew ($\alpha=0.50$), AdaLog-Sketch achieves MAE = 13.17 versus 36.57 for Disjoint Stack ($2.78\times$ lower). However, on a purely uniform stream ($\alpha=0.0$, 300,000 operations over 50,000 distinct items), heavy hitters do not exist (all items have true count $\approx 6 < \tau=15$). Under this uniform workload:
\begin{itemize}
\item At 8~KB, dedicated Count-Min Sketch achieves $\mathrm{MAE}=58.24$, whereas AdaLog-Sketch yields $\mathrm{MAE}=116.88$ ($2.0\times$ higher error).
\item At 32~KB, dedicated CMS achieves $\mathrm{MAE}=9.36$, whereas AdaLog-Sketch yields $\mathrm{MAE}=11.37$.
\end{itemize}
\textbf{Algorithmic Root Cause:} On uniform or light-tailed streams, the elephant stash remains empty or stores low-velocity items, dedicating $K\times 24$~B (3,072~B) to unutilized stash pointers. Dedicated sketches utilize this entire memory for counter matrix width, resulting in fewer collisions. AdaLog-Sketch is specifically optimized for power-law, heavy-tailed streaming workloads."""

text = text.replace(old_sec_future, new_sec_real)

# Write back
with open(MAIN_TEX, "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully updated all discussions in paper/main.tex!")
