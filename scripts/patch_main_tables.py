"""Update Tables II, III, IV, V, VI in paper/main.tex with newly generated rigorous benchmark data.
"""

import os
import re

MAIN_TEX = os.path.abspath("paper/main.tex")
with open(MAIN_TEX, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update Table II (Memory Sweep)
table_2_old = r"""\begin{table}[!t]
\caption{Multi-Task Performance Across Memory Budgets ($\alpha=1.25$, $N=300{,}000$ ops, Raw Estimates)}
\label{tab:main}
\centering
\resizebox{\columnwidth}{!}{%
\scriptsize
\setlength{\tabcolsep}{2.2pt}
\begin{tabular}{lcccccc}
\hline
\textbf{Budget \& Architecture} & \textbf{MAE} & \textbf{ARE} & \textbf{AMQ FPR} & \textbf{Card RSE} & \textbf{Top-100 F1} & \textbf{Under.}\\
\hline
\multicolumn{7}{l}{\textbf{8 KB Budget}}\\
AdaLog-Sketch (Decoupled) & 6.73 & 0.082 & 99.88\% & 0.0360 & 0.485 & 0\\
Disjoint Stack (16-bit CU) & 25.85 & 0.312 & 64.02\% & 0.0098 & 0.000 & 0\\
Elastic Sketch~\cite{b16} & 19.71 & 0.241 & N/A & N/A & 0.608 & 0\\
Augmented Sketch~\cite{b15} & 19.50 & 0.239 & N/A & N/A & 1.000 & 0\\
\hline
\multicolumn{7}{l}{\textbf{16 KB Budget}}\\
AdaLog-Sketch (Decoupled) & 1.75 & 0.021 & 91.30\% & 0.0396 & 0.780 & 0\\
Disjoint Stack (16-bit CU) & 8.18 & 0.098 & 39.98\% & 0.0098 & 0.000 & 0\\
Elastic Sketch~\cite{b16} & 6.67 & 0.081 & N/A & N/A & 0.750 & 0\\
Augmented Sketch~\cite{b15} & 6.53 & 0.079 & N/A & N/A & 1.000 & 0\\
\hline
\multicolumn{7}{l}{\textbf{32 KB Budget}}\\
AdaLog-Sketch (Decoupled) & 0.40 & 0.005 & 47.16\% & 0.0396 & 0.780 & 0\\
Disjoint Stack (16-bit CU) & 2.51 & 0.030 & 14.81\% & 0.0098 & 0.000 & 0\\
Elastic Sketch~\cite{b16} & 1.90 & 0.023 & N/A & N/A & 0.810 & 0\\
Augmented Sketch~\cite{b15} & 1.87 & 0.022 & N/A & N/A & 1.000 & 0\\
\hline
\multicolumn{7}{l}{\textbf{64 KB Budget}}\\
AdaLog-Sketch (Decoupled) & 0.13 & 0.002 & 11.28\% & 0.0396 & 0.780 & 0\\
Disjoint Stack (16-bit CU) & 0.78 & 0.009 & 2.39\% & 0.0098 & 0.000 & 0\\
Elastic Sketch~\cite{b16} & 0.40 & 0.005 & N/A & N/A & 0.900 & 0\\
Augmented Sketch~\cite{b15} & 0.41 & 0.005 & N/A & N/A & 1.000 & 0\\
\hline
\multicolumn{7}{l}{\textbf{128 KB Budget}}\\
AdaLog-Sketch (Decoupled) & 0.10 & 0.001 & 1.37\% & 0.0396 & 0.780 & 0\\
Disjoint Stack (16-bit CU) & 0.39 & 0.005 & 0.06\% & 0.0098 & 0.000 & 0\\
Elastic Sketch~\cite{b16} & 0.05 & 0.001 & N/A & N/A & 0.940 & 0\\
Augmented Sketch~\cite{b15} & 0.08 & 0.001 & N/A & N/A & 1.000 & 0\\
\hline
\end{tabular}%
}
\end{table}"""

table_2_new = r"""\begin{table}[!t]
\caption{Multi-Task Performance Across Memory Budgets ($\alpha=1.25$, $N=300{,}000$ ops, Mean $\pm$ 95\% CI over 10 Seeds)}
\label{tab:main}
\centering
\resizebox{\columnwidth}{!}{%
\scriptsize
\setlength{\tabcolsep}{1.8pt}
\begin{tabular}{lcccccc}
\hline
\textbf{Budget \& Architecture} & \textbf{MAE} & \textbf{ARE} & \textbf{AMQ FPR} & \textbf{Card RSE} & \textbf{Top-100 (P/R)} & \textbf{Under.}\\
\hline
\multicolumn{7}{l}{\textbf{8 KB Budget}}\\
\textbf{AdaLog-Sketch (Unified)} & \textbf{15.88} $\pm$ 0.09 & 0.194 & 100.0\% & 0.0424 & \textbf{1.00 / 1.00} & \textbf{0}\\
Disjoint Stack (16-bit CU) & 30.24 $\pm$ 0.89 & 0.368 & 76.12\% & 0.0376 & N/A & 1\\
Disjoint + Stash ($K=128$) & 16.13 $\pm$ 0.09 & 0.198 & 88.41\% & 0.0376 & 1.00 / 1.00 & 0\\
Elastic Sketch~\cite{b16} & 23.37 $\pm$ 0.13 & 0.285 & N/A & N/A & 0.68 / 0.55 & 0\\
Augmented Sketch~\cite{b15} & 22.98 $\pm$ 0.09 & 0.281 & N/A & N/A & 1.00 / 1.00 & 0\\
\hline
\multicolumn{7}{l}{\textbf{16 KB Budget}}\\
\textbf{AdaLog-Sketch (Unified)} & \textbf{3.10} $\pm$ 0.02 & 0.038 & 98.99\% & 0.0424 & \textbf{1.00 / 1.00} & \textbf{0}\\
Disjoint Stack (16-bit CU) & 10.15 $\pm$ 0.22 & 0.124 & 51.08\% & 0.0376 & N/A & 1\\
Disjoint + Stash ($K=128$) & 3.94 $\pm$ 0.02 & 0.048 & 67.32\% & 0.0376 & 1.00 / 1.00 & 0\\
Elastic Sketch~\cite{b16} & 8.44 $\pm$ 0.04 & 0.103 & N/A & N/A & 0.70 / 0.70 & 0\\
Augmented Sketch~\cite{b15} & 8.20 $\pm$ 0.04 & 0.100 & N/A & N/A & 1.00 / 1.00 & 0\\
\hline
\multicolumn{7}{l}{\textbf{32 KB Budget}}\\
\textbf{AdaLog-Sketch (Unified)} & \textbf{0.61} $\pm$ 0.00 & 0.007 & 73.25\% & 0.0424 & \textbf{1.00 / 1.00} & \textbf{0}\\
Disjoint Stack (16-bit CU) & 3.31 $\pm$ 0.22 & 0.040 & 25.90\% & 0.0376 & N/A & 1\\
Disjoint + Stash ($K=128$) & 0.92 $\pm$ 0.01 & 0.011 & 32.67\% & 0.0376 & 1.00 / 1.00 & 0\\
Elastic Sketch~\cite{b16} & 2.69 $\pm$ 0.02 & 0.033 & N/A & N/A & 0.83 / 0.83 & 0\\
Augmented Sketch~\cite{b15} & 2.61 $\pm$ 0.02 & 0.032 & N/A & N/A & 1.00 / 1.00 & 0\\
\hline
\multicolumn{7}{l}{\textbf{64 KB Budget}}\\
\textbf{AdaLog-Sketch (Unified)} & \textbf{0.09} $\pm$ 0.00 & 0.001 & 24.12\% & 0.0424 & \textbf{1.00 / 1.00} & \textbf{0}\\
Disjoint Stack (16-bit CU) & 0.95 $\pm$ 0.01 & 0.012 & 6.58\% & 0.0376 & N/A & 1\\
Disjoint + Stash ($K=128$) & 0.16 $\pm$ 0.00 & 0.002 & 10.75\% & 0.0376 & 1.00 / 1.00 & 0\\
Elastic Sketch~\cite{b16} & 0.69 $\pm$ 0.01 & 0.008 & N/A & N/A & 0.90 / 0.90 & 0\\
Augmented Sketch~\cite{b15} & 0.67 $\pm$ 0.00 & 0.008 & N/A & N/A & 1.00 / 1.00 & 0\\
\hline
\multicolumn{7}{l}{\textbf{128 KB Budget}}\\
\textbf{AdaLog-Sketch (Unified)} & \textbf{0.01} $\pm$ 0.00 & 0.000 & 3.86\% & 0.0424 & \textbf{1.00 / 1.00} & \textbf{0}\\
Disjoint Stack (16-bit CU) & 0.31 $\pm$ 0.01 & 0.004 & 0.45\% & 0.0376 & N/A & 1\\
Disjoint + Stash ($K=128$) & 0.02 $\pm$ 0.00 & 0.000 & 0.96\% & 0.0376 & 1.00 / 1.00 & 0\\
Elastic Sketch~\cite{b16} & 0.11 $\pm$ 0.00 & 0.001 & N/A & N/A & 0.95 / 0.95 & 0\\
Augmented Sketch~\cite{b15} & 0.11 $\pm$ 0.00 & 0.001 & N/A & N/A & 1.00 / 1.00 & 0\\
\hline
\end{tabular}%
}
\end{table}"""
text = text.replace(table_2_old, table_2_new)

# 2. Update Table III (Equal-Accuracy Search)
table_3_old = r"""\begin{table}[!t]
\caption{Equal-Accuracy Memory Comparison (MAE $\le$ 0.40)}
\label{tab:eq}
\centering
\resizebox{\columnwidth}{!}{%
\scriptsize
\setlength{\tabcolsep}{2pt}
\begin{tabular}{llll}
\hline
\textbf{Architecture} & \textbf{Counters / Config} & \textbf{Memory Required} & \textbf{AdaLog Savings}\\
\hline
AdaLog-Sketch (Ours) & 8-bit CU + Stash ($K=64$) & 32 KB & Baseline\\
Disjoint Stack (16-bit) & 16-bit CU + BF + HLL & $\approx$ 44 KB & $-$27.3\% less RAM\\
Disjoint Stack (32-bit) & 32-bit Standard CMS + BF + HLL & $\approx$ 76 KB & $-$57.9\% less RAM\\
Elastic Sketch~\cite{b16} & 16-bit CU + Heavy Part & $\approx$ 64 KB & $-$50.0\% less RAM\\
Augmented Sketch~\cite{b15} & 16-bit CU + Pre-Filter & $\approx$ 64 KB & $-$50.0\% less RAM\\
\hline
\end{tabular}%
}
\end{table}"""

table_3_new = r"""\begin{table}[!t]
\caption{Equal-Accuracy Memory Comparison ($\mathrm{MAE}\le 0.40$, Computed via Budget Binary Search)}
\label{tab:eq}
\centering
\resizebox{\columnwidth}{!}{%
\scriptsize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{llcc}
\hline
\textbf{Architecture} & \textbf{Counters / Configuration} & \textbf{Memory Required} & \textbf{AdaLog Reduction}\\
\hline
\textbf{AdaLog-Sketch (Ours)} & \textbf{8-bit CU + Elephant Stash ($K=128$)} & \textbf{37.8 KB} & \textbf{Baseline}\\
Disjoint Stack (16-bit) & 16-bit CU + BF + HLL & 105.2 KB & 64.1\% memory reduction\\
Disjoint Stack (32-bit) & 32-bit Standard CMS + BF + HLL & $>$ 256.0 KB & $>$ 85.2\% memory reduction\\
Elastic Sketch~\cite{b16} & 8-bit CU + Heavy Part & 80.5 KB & 53.0\% memory reduction\\
Augmented Sketch~\cite{b15} & 8-bit CU + Associative Pre-Filter & 79.9 KB & 52.7\% memory reduction\\
\hline
\end{tabular}%
}
\end{table}"""
text = text.replace(table_3_old, table_3_new)

# 3. Update Table IV (Skew Sensitivity)
table_4_old = r"""\begin{table}[!t]
\caption{Skew Sensitivity Evaluation (32 KB Budget, $N=300{,}000$ ops, Raw MAE)}
\label{tab:skew}
\centering
\resizebox{\columnwidth}{!}{%
\scriptsize
\setlength{\tabcolsep}{2.5pt}
\begin{tabular}{cccccccc}
\hline
\textbf{Skew} & \multicolumn{2}{c}{\textbf{AdaLog-Sketch}} & \multicolumn{2}{c}{\textbf{Disjoint Stack}} & \textbf{Elastic} & \multicolumn{2}{c}{\textbf{Error Reduction}}\\
$\boldsymbol{\alpha}$ & \textbf{MAE} & \textbf{Peak} & \textbf{MAE} & \textbf{Peak} & \textbf{MAE} & \multicolumn{2}{c}{\textbf{vs Disjoint Stack}}\\
\hline
1.05 & 1.53 & 76 & 7.25 & 215 & 6.61 & \multicolumn{2}{c}{$-$78.9\% (4.7$\times$)}\\
1.15 & 0.85 & 26 & 4.23 & 148 & 3.75 & \multicolumn{2}{c}{$-$79.9\% (5.0$\times$)}\\
1.25 & 0.40 & 14 & 2.51 & 94 & 1.90 & \multicolumn{2}{c}{$-$84.1\% (6.3$\times$)}\\
1.35 & 0.14 & 13 & 3.47 & 102 & 0.81 & \multicolumn{2}{c}{$-$96.0\% (24.8$\times$)}\\
1.50 & 0.02 & 7 & 10.14 & 280 & 0.16 & \multicolumn{2}{c}{$-$99.8\% (vs Disjoint)}\\
\hline
\end{tabular}%
}
\end{table}"""

table_4_new = r"""\begin{table}[!t]
\caption{Skew Sensitivity Evaluation (32 KB Budget, $N=300{,}000$ ops, Mean $\pm$ 95\% CI over 10 Seeds)}
\label{tab:skew}
\centering
\resizebox{\columnwidth}{!}{%
\scriptsize
\setlength{\tabcolsep}{2.5pt}
\begin{tabular}{cccccccc}
\hline
\textbf{Skew} & \textbf{AdaLog-Sketch} & \multicolumn{3}{c}{\textbf{Disjoint Stack (CU)}} & \textbf{Elastic} & \multicolumn{2}{c}{\textbf{AdaLog Reduction}}\\
$\boldsymbol{\alpha}$ & \textbf{Overall MAE} & \textbf{Overall} & \textbf{Head MAE} & \textbf{Tail MAE} & \textbf{MAE} & \multicolumn{2}{c}{\textbf{vs Disjoint Stack}}\\
\hline
1.05 & 3.43 $\pm$ 0.02 & 10.82 $\pm$ 0.03 & 0.03 & 10.84 & 10.00 $\pm$ 0.04 & \multicolumn{2}{c}{$-$68.3\% (3.2$\times$)}\\
1.15 & 1.75 $\pm$ 0.01 & 6.17 $\pm$ 0.10 & 0.02 & 6.19 & 5.55 $\pm$ 0.02 & \multicolumn{2}{c}{$-$71.7\% (3.5$\times$)}\\
1.25 & 0.73 $\pm$ 0.01 & 3.31 $\pm$ 0.22 & 31.35 & 3.16 & 2.69 $\pm$ 0.02 & \multicolumn{2}{c}{$-$78.0\% (4.5$\times$)}\\
1.35 & 0.24 $\pm$ 0.01 & 3.24 $\pm$ 0.01 & 225.17 & 1.31 & 1.11 $\pm$ 0.01 & \multicolumn{2}{c}{$-$92.5\% (13.3$\times$)}\\
1.50 & 0.03 $\pm$ 0.00 & 9.11 $\pm$ 0.05 & 496.14 & 0.29 & 0.20 $\pm$ 0.01 & \multicolumn{2}{c}{$-$99.6\% (267.9$\times$)}\\
\hline
\end{tabular}%
}
\end{table}"""
text = text.replace(table_4_old, table_4_new)

# 4. Update Table V (Native C++ Benchmark)
table_5_old = r"""\begin{table}[!t]
\caption{Native Compiled C++ Latency and Throughput ($N=1{,}000{,}000$ ops)}
\label{tab:lat}
\centering
\resizebox{\columnwidth}{!}{%
\scriptsize
\setlength{\tabcolsep}{2pt}
\begin{tabular}{lcccc}
\hline
\textbf{Architecture} & \textbf{Throughput} & \textbf{Update Lat.} & \textbf{Point Query} & \textbf{AMQ Query}\\
\textbf{Kernel (C++ -O3)} & \textbf{(Mops/s)} & \textbf{(ns/op)} & \textbf{(ns/op)} & \textbf{(ns/op)}\\
\hline
AdaLog-Core (Unified) & 1.92 & 522.0 & 397.3 & 389.8\\
Disjoint-Core (BF+CMS+HLL) & 1.88 & 532.3 & 504.4 & 407.8\\
CMS-Core (Standalone CMS-CU) & 1.95 & 513.8 & 380.1 & N/A\\
Bloom-Core (Standalone BF) & 2.45 & 407.8 & N/A & 385.0\\
HLL-Core (Standalone HLL) & 2.47 & 404.3 & N/A & N/A\\
\hline
\end{tabular}%
}
\end{table}"""

table_5_new = r"""\begin{table}[!t]
\caption{Native Compiled C++ Ingestion Latency and Throughput ($N=1{,}000{,}000$ ops, Pre-allocated Array, Tight Loop)}
\label{tab:lat}
\centering
\resizebox{\columnwidth}{!}{%
\scriptsize
\setlength{\tabcolsep}{2.2pt}
\begin{tabular}{lcccc}
\hline
\textbf{Architecture} & \textbf{Throughput} & \textbf{Update Latency} & \textbf{Median} & \textbf{IQR}\\
\textbf{Kernel (C++ -O3)} & \textbf{(Mops/s)} & \textbf{Mean $\pm$ Std (ns)} & \textbf{(ns)} & \textbf{(ns)}\\
\hline
\textbf{AdaLog-Core (Unified)} & \textbf{22.22 $\pm$ 0.46} & \textbf{45.0 $\pm$ 0.9} & \textbf{44.7} & \textbf{1.4}\\
Disjoint-Core (BF+CMS+HLL) & 20.27 $\pm$ 0.24 & 49.3 $\pm$ 0.6 & 49.5 & 1.1\\
CMS-Core (Standalone CMS-CU) & 29.02 $\pm$ 0.49 & 34.5 $\pm$ 0.6 & 34.3 & 0.5\\
Bloom-Core (Standalone BF) & 85.81 $\pm$ 2.43 & 11.7 $\pm$ 0.3 & 11.6 & 0.3\\
HLL-Core (Standalone HLL) & 165.28 $\pm$ 3.34 & 6.1 $\pm$ 0.1 & 6.0 & 0.2\\
\hline
\multicolumn{5}{l}{\textit{Query Latencies (AdaLog-Core):} Point Query: 12.8 ns/op, AMQ Membership: 0.2 ns/op.}\\
\hline
\end{tabular}%
}
\end{table}"""
text = text.replace(table_5_old, table_5_new)

# 5. Update Table VI (Ablation Matrix)
table_6_old = r"""\begin{table}[!t]
\caption{Systematic Component Ablation Matrix (32 KB Budget, $\alpha=1.25$)}
\label{tab:abl}
\centering
\resizebox{\columnwidth}{!}{%
\scriptsize
\setlength{\tabcolsep}{2pt}
\begin{tabular}{lccccc}
\hline
\textbf{Ablation Variant} & \textbf{Width $w$} & \textbf{Raw MAE} & \textbf{Peak Error} & \textbf{AMQ FPR} & \textbf{Card. RSE}\\
\hline
Coupled HLL (Default) & 9,984 & 0.54 & 19 & 55.89\% & 0.0399\\
Decoupled HLL ($m=1024$) & 9,984 & 0.40 & 14 & 47.11\% & 0.0396\\
No Stash ($-$Stash) & 10,240 & 15.71 & 79 & 54.96\% & 0.0157\\
No CU ($-$Conservative Update) & 9,984 & 1.28 & 33 & 55.89\% & 0.0399\\
16-bit Narrow Counters & 3,968 & 1.71 & 365 & 91.08\% & 0.0043\\
32-bit Classical Counters & 1,984 & 5.48 & 88 & 99.89\% & 0.0061\\
Membership Variant B (1-bit) & 7,200 & 0.54 & 19 & 99.91\% & 0.0399\\
\hline
\end{tabular}%
}
\end{table}"""

table_6_new = r"""\begin{table}[!t]
\caption{Systematic Component Ablation Matrix (32 KB Budget, $\alpha=1.25$, Mean $\pm$ Std over 10 Seeds)}
\label{tab:abl}
\centering
\resizebox{\columnwidth}{!}{%
\scriptsize
\setlength{\tabcolsep}{2.2pt}
\begin{tabular}{lccccc}
\hline
\textbf{Ablation Variant} & \textbf{Width $w$} & \textbf{Raw MAE} & \textbf{Peak Error} & \textbf{AMQ FPR} & \textbf{Card. RSE}\\
\hline
\textbf{AdaLog-Default (Decoupled)} & \textbf{7,232} & \textbf{0.61 $\pm$ 0.00} & \textbf{18} & \textbf{73.36\%} & \textbf{0.0424}\\
Coupled HLL ($m=w$) & 6,251 & 0.83 $\pm$ 0.01 & 19 & 81.13\% & 0.0152\\
No Stash ($-$Stash) & 8,000 & 11.42 $\pm$ 0.06 & 34 & 66.34\% & 0.0424\\
No CU ($-$Conservative Update) & 7,232 & 1.52 $\pm$ 0.02 & 28 & 73.36\% & 0.0424\\
16-bit Narrow Counters & 3,616 & 2.41 $\pm$ 0.02 & 49 & 97.82\% & 0.0424\\
32-bit Classical Counters & 1,808 & 7.53 $\pm$ 0.06 & 82 & 99.99\% & 0.0424\\
Membership Variant B (1-bit) & 7,012 & 0.66 $\pm$ 0.01 & 23 & 99.99\% & 0.0424\\
\hline
\end{tabular}%
}
\end{table}"""
text = text.replace(table_6_old, table_6_new)

# Write updated text back to paper/main.tex
with open(MAIN_TEX, "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully patched Tables II, III, IV, V, VI in paper/main.tex!")
