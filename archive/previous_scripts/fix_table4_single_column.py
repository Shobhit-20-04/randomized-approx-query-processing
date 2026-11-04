"""Fix Table IV in paper/main.tex to be a clean, compact single-column table.
Preserves all numbers and baselines exactly, ensuring zero powershell variable expansion.
"""

import os

MAIN_TEX = os.path.abspath("paper/main.tex")

with open(MAIN_TEX, "r", encoding="utf-8") as f:
    text = f.read()

# Locate the table with tab:main
idx = text.find(r"\label{tab:main}")
start = text.rfind(r"\begin{table", 0, idx)
end = text.find(r"\end{table", idx)
end = text.find("}", end) + 1
old_table = text[start:end]

single_col_t4 = r"""\begin{table}[!t]
\caption{Multi-task performance across memory budgets ($\alpha = 1.25$, $N = 300{,}000$ ops, mean $\pm$ 95\% CI over 10 seeds)}
\label{tab:main}
\centering
\scriptsize
\setlength{\tabcolsep}{2pt}
\renewcommand{\arraystretch}{0.95}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lcccccc}
\hline
\textbf{Architecture} & \textbf{MAE} & \textbf{ARE} & \textbf{FPR} & \textbf{RSE} & \textbf{Top-100} & \textbf{Und.}\\ 
\hline
\multicolumn{7}{l}{\textit{\textbf{8 KB budget}}} \\
AdaLog-Sketch (Unified) & \textbf{15.88 $\pm$ 0.09} & \textbf{0.194} & 100.0\% & 0.0424 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Disjoint Stack (16-bit) & 30.24 $\pm$ 0.89 & 0.368 & 76.12\% & \textbf{0.0376} & N/A & 1\\ 
Disjoint+Stash ($K = 128$) & 16.13 $\pm$ 0.09 & 0.198 & 88.41\% & \textbf{0.0376} & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Elastic Sketch~\cite{b16} & 23.37 $\pm$ 0.13 & 0.285 & N/A & N/A & 0.68 / 0.55 & \textbf{0}\\ 
Augmented Sketch~\cite{b15} & 22.98 $\pm$ 0.09 & 0.281 & N/A & N/A & \textbf{1.00 / 1.00} & \textbf{0}\\ 
\hline
\multicolumn{7}{l}{\textit{\textbf{16 KB budget}}} \\
AdaLog-Sketch (Unified) & \textbf{3.10 $\pm$ 0.02} & \textbf{0.038} & 98.99\% & 0.0424 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Disjoint Stack (16-bit) & 10.15 $\pm$ 0.22 & 0.124 & 51.08\% & \textbf{0.0376} & N/A & 1\\ 
Disjoint+Stash ($K = 128$) & 3.94 $\pm$ 0.02 & 0.048 & 67.32\% & \textbf{0.0376} & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Elastic Sketch~\cite{b16} & 8.44 $\pm$ 0.04 & 0.103 & N/A & N/A & 0.70 / 0.70 & \textbf{0}\\ 
Augmented Sketch~\cite{b15} & 8.20 $\pm$ 0.04 & 0.100 & N/A & N/A & \textbf{1.00 / 1.00} & \textbf{0}\\ 
\hline
\multicolumn{7}{l}{\textit{\textbf{32 KB budget}}} \\
AdaLog-Sketch (Unified) & \textbf{0.61 $\pm$ 0.00} & \textbf{0.007} & 73.25\% & 0.0424 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Disjoint Stack (16-bit) & 3.31 $\pm$ 0.22 & 0.040 & 25.90\% & \textbf{0.0376} & N/A & 1\\ 
Disjoint+Stash ($K = 128$) & 0.92 $\pm$ 0.01 & 0.011 & 32.67\% & \textbf{0.0376} & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Elastic Sketch~\cite{b16} & 2.69 $\pm$ 0.02 & 0.033 & N/A & N/A & 0.83 / 0.83 & \textbf{0}\\ 
Augmented Sketch~\cite{b15} & 2.61 $\pm$ 0.02 & 0.032 & N/A & N/A & \textbf{1.00 / 1.00} & \textbf{0}\\ 
\hline
\multicolumn{7}{l}{\textit{\textbf{64 KB budget}}} \\
AdaLog-Sketch (Unified) & \textbf{0.09 $\pm$ 0.00} & \textbf{0.001} & 24.12\% & 0.0424 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Disjoint Stack (16-bit) & 0.95 $\pm$ 0.01 & 0.012 & 6.58\% & \textbf{0.0376} & N/A & 1\\ 
Disjoint+Stash ($K = 128$) & 0.16 $\pm$ 0.00 & 0.002 & 10.75\% & \textbf{0.0376} & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Elastic Sketch~\cite{b16} & 0.69 $\pm$ 0.01 & 0.008 & N/A & N/A & 0.90 / 0.90 & \textbf{0}\\ 
Augmented Sketch~\cite{b15} & 0.67 $\pm$ 0.00 & 0.008 & N/A & N/A & \textbf{1.00 / 1.00} & \textbf{0}\\ 
\hline
\multicolumn{7}{l}{\textit{\textbf{128 KB budget}}} \\
AdaLog-Sketch (Unified) & \textbf{0.01 $\pm$ 0.00} & \textbf{0.000} & 3.86\% & 0.0424 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Disjoint Stack (16-bit) & 0.31 $\pm$ 0.01 & 0.004 & 0.45\% & \textbf{0.0376} & N/A & 1\\ 
Disjoint+Stash ($K = 128$) & 0.02 $\pm$ 0.00 & 0.000 & 0.96\% & \textbf{0.0376} & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Elastic Sketch~\cite{b16} & 0.11 $\pm$ 0.00 & 0.001 & N/A & N/A & 0.95 / 0.95 & \textbf{0}\\ 
Augmented Sketch~\cite{b15} & 0.11 $\pm$ 0.00 & 0.001 & N/A & N/A & \textbf{1.00 / 1.00} & \textbf{0}\\ 
\hline
\end{tabular}%
}
\end{table}"""

text = text.replace(old_table, single_col_t4)

with open(MAIN_TEX, "w", encoding="utf-8") as f:
    f.write(text)

print("Saved clean single-column Table IV in paper/main.tex")
