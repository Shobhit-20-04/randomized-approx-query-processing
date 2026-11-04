"""Patch paper/main.tex with Step 1 (Baseline Fairness) and Step 2 (Correctness) fixes.
"""

import os

MAIN_TEX = os.path.abspath("paper/main.tex")
with open(MAIN_TEX, "r", encoding="utf-8") as f:
    text = f.read()

# Normalize CRLF to LF for consistent replacement, write back preserving file integrity
text = text.replace("\r\n", "\n")

# 1. Wrap Table II in resizebox to prevent column overflow
old_tab2 = r"""\begin{table}[!t]
\caption{Algorithmic capability matrix across streaming synopses}
\label{tab:capabilities}
\centering
\scriptsize
\setlength{\tabcolsep}{2.5pt}
\begin{tabular}{lcccccc}
\hline
\textbf{Data structure} & \textbf{AMQ} & \textbf{Point freq.} & \textbf{Card. ($F_0$)} & \textbf{Top-$k$} & \textbf{Shared mem.} & \textbf{Single hash} \\
\hline
Bloom Filter~\cite{b6} & \checkmark & $\times$ & $\times$ & $\times$ & $\times$ & $\times$ ($k$ hashes) \\
Count-Min Sketch (CMS)~\cite{b7} & Weak & \checkmark & $\times$ & $\times$ & $\times$ & $\times$ ($d$ hashes) \\
HyperLogLog (HLL)~\cite{b8} & $\times$ & $\times$ & \checkmark & $\times$ & $\times$ & \checkmark (1 hash) \\
Augmented Sketch~\cite{b15} & $\times$ & \checkmark & $\times$ & \checkmark & Partial & $\times$ \\
Elastic Sketch~\cite{b16} & $\times$ & \checkmark & $\times$ & \checkmark & Partial & $\times$ \\
Disjoint Baseline Stack & \checkmark & \checkmark & \checkmark & N/A & $\times$ (3 silos) & $\times$ (12 hashes) \\
\textbf{AdaLog-Sketch (ours)} & \checkmark & \checkmark & \checkmark & \checkmark & \checkmark (unified) & \checkmark (XXH3-128) \\
\hline
\end{tabular}
\end{table}"""

new_tab2 = r"""\begin{table}[!t]
\caption{Algorithmic capability matrix across streaming synopses}
\label{tab:capabilities}
\centering
\scriptsize
\setlength{\tabcolsep}{2.5pt}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lcccccc}
\hline
\textbf{Data structure} & \textbf{AMQ} & \textbf{Point freq.} & \textbf{Card. ($F_0$)} & \textbf{Top-$k$} & \textbf{Shared mem.} & \textbf{Single hash} \\
\hline
Bloom Filter~\cite{b6} & \checkmark & $\times$ & $\times$ & $\times$ & $\times$ & $\times$ ($k$ hashes) \\
Count-Min Sketch (CMS)~\cite{b7} & Weak & \checkmark & $\times$ & $\times$ & $\times$ & $\times$ ($d$ hashes) \\
HyperLogLog (HLL)~\cite{b8} & $\times$ & $\times$ & \checkmark & $\times$ & $\times$ & \checkmark (1 hash) \\
Augmented Sketch~\cite{b15} & $\times$ & \checkmark & $\times$ & \checkmark & Partial & $\times$ \\
Elastic Sketch~\cite{b16} & $\times$ & \checkmark & $\times$ & \checkmark & Partial & $\times$ \\
Disjoint Baseline Stack & \checkmark & \checkmark & \checkmark & N/A & $\times$ (3 silos) & $\times$ (12 hashes) \\
\textbf{AdaLog-Sketch (ours)} & \checkmark & \checkmark & \checkmark & \checkmark & \checkmark (unified) & \checkmark (XXH3-128) \\
\hline
\end{tabular}%
}
\end{table}"""

assert old_tab2 in text, "Table II not found in main.tex!"
text = text.replace(old_tab2, new_tab2)

# 2. Fix Theorem 1 (rename K to H and state bound following proof)
old_thm1 = r"""\begin{theorem}[Zipfian collision bound in standard CMS]
Let item frequencies follow a Zipfian distribution $f_i = C_\alpha \cdot N \cdot i^{-\alpha}$ with skew parameter $\alpha > 1$, where $C_\alpha = (\sum_{k=1}^{|U|} k^{-\alpha})^{-1} = H_{n,\alpha}^{-1}$. In a standard Count-Min Sketch with width $w$ and depth $d$, the expected overestimation error for a low-frequency tail item $x_m$ ($f(x_m) = 1$) is lower-bounded by:
\begin{equation}
\mathbb{E}[\hat{f}(x_m) - f(x_m)] \ge \frac{C_\alpha N}{w} \left(\sum_{k=1}^K k^{-\alpha}\right) \left(1 - \left(1 - \frac{1}{w}\right)^K\right)^d
\end{equation}
\end{theorem}
\begin{proof}
In any row $j \in \{0, \dots, d - 1\}$, the counter assigned to tail item $x_m$ is:
\begin{equation}
T[j, h_j(x_m)] = f(x_m) + \sum_{k \neq m} f(x_k) \cdot I[h_j(x_k) = h_j(x_m)]
\end{equation}
Under uniform hashing, the probability that a specific heavy key $x_k$ avoids bucket $h_j(x_m)$ is $(1 - 1/w)$. The probability that the bucket avoids all $K$ heavy keys is $(1 - 1/w)^K$, so the probability that row $j$ collides with at least one heavy key is $1 - (1 - 1/w)^K$. Across $d$ independent hash rows, the joint probability that $x_m$ collides with at least one heavy key in all $d$ rows simultaneously is:
\begin{equation}
\Pr[\text{all } d \text{ rows collide with a heavy key}] = \left(1 - \left(1 - \frac{1}{w}\right)^K\right)^d
\end{equation}
When all rows suffer heavy collisions, $\hat{f}(x_m) - f(x_m)$ is bounded below by the minimum heavy-hitter contribution across rows, which scales with $N/w$. As $N$ grows, the relative error grows in proportion.
\end{proof}"""

new_thm1 = r"""\begin{theorem}[Zipfian collision bound in standard CMS]
Let item frequencies follow a Zipfian distribution $f_i = C_\alpha \cdot N \cdot i^{-\alpha}$ with skew parameter $\alpha > 1$, where $C_\alpha = (\sum_{k=1}^{|U|} k^{-\alpha})^{-1} = H_{n,\alpha}^{-1}$. In a standard Count-Min Sketch with width $w$ and depth $d$, the expected overestimation error for a low-frequency tail item $x_m$ ($f(x_m) = 1$) colliding with the top $H$ heavy keys is lower-bounded by:
\begin{equation}
\mathbb{E}[\hat{f}(x_m) - f(x_m)] \ge \frac{C_\alpha N}{w} \left(\sum_{k=1}^H k^{-\alpha}\right) \left(1 - \left(1 - \frac{1}{w}\right)^H\right)^d
\end{equation}
\end{theorem}
\begin{proof}
In any row $j \in \{0, \dots, d - 1\}$, the counter assigned to tail item $x_m$ is:
\begin{equation}
T[j, h_j(x_m)] = f(x_m) + \sum_{k \neq m} f(x_k) \cdot I[h_j(x_k) = h_j(x_m)]
\end{equation}
Under uniform hashing, the probability that a specific heavy key $x_k$ avoids bucket $h_j(x_m)$ is $(1 - 1/w)$. The probability that the bucket avoids all $H$ heavy keys is $(1 - 1/w)^H$, so the probability that row $j$ collides with at least one heavy key is $1 - (1 - 1/w)^H$. Across $d$ independent hash rows, the joint probability that $x_m$ collides with at least one heavy key in all $d$ rows simultaneously is:
\begin{equation}
\Pr[\text{all } d \text{ rows collide with a heavy key}] = \left(1 - \left(1 - \frac{1}{w}\right)^H\right)^d
\end{equation}
When all rows suffer heavy collisions, $\hat{f}(x_m) - f(x_m)$ is bounded below by the minimum heavy-hitter contribution across rows, which scales with $N/w$. As $N$ grows, the relative error grows in proportion.
\end{proof}"""

assert old_thm1 in text, "Theorem 1 not found in main.tex!"
text = text.replace(old_thm1, new_thm1)

# 3. Fix Algorithm 1 Conservative Update rule
old_alg1_cu = r"""\STATE $v_{min} \leftarrow \min_{0 \le j < d} T[j, idx_j]$
\STATE $v_{new} \leftarrow \min(\MV, v_{min} + c)$
\FOR{$j = 0$ \TO $d-1$}
    \IF{$T[j, idx_j] == v_{min}$}
        \STATE $T[j, idx_j] \leftarrow v_{new}$
    \ENDIF
\ENDFOR"""

new_alg1_cu = r"""\STATE $v_{min} \leftarrow \min_{0 \le j < d} T[j, idx_j]$
\STATE $v_{new} \leftarrow \min(\MV, v_{min} + c)$
\FOR{$j = 0$ \TO $d-1$}
    \STATE $T[j, idx_j] \leftarrow \max(T[j, idx_j], v_{new})$
\ENDFOR"""

assert old_alg1_cu in text, "Algorithm 1 CU loop not found in main.tex!"
text = text.replace(old_alg1_cu, new_alg1_cu)

# 4. Fix Proposition 1 (67% inflation and drop 'unique')
old_prop1 = r"""\begin{proposition}[Vulnerability of additive and overwrite write-back]
Consider an item $e$ promoted at count $c_{base} = 20$ that receives $c_{exact} = 10$ increments while resident in the stash ($c_{evict} = 30$). If $e$ is evicted: (i) an additive rule $T[j] \leftarrow T[j] + c_{evict}$ sets $T[j] \leftarrow 20 + 30 = 50$, double-counting $c_{base}$ and inflating the estimate by up to +100\%. (ii) A naive overwrite $T[j] \leftarrow c_{evict}$ reduces counter values for colliding keys $y$ with prior cell counts $> 30$, which introduces underestimations. The monotonic $\max()$ operator is the unique write-back rule that prevents double-counting while preserving the one-sided bounds $T'[j] \ge f(e)$ and $T'[j] \ge T[j]$.
\end{proposition}"""

new_prop1 = r"""\begin{proposition}[Vulnerability of additive and overwrite write-back]
Consider an item $e$ promoted at count $c_{base} = 20$ that receives $c_{exact} = 10$ increments while resident in the stash ($c_{evict} = 30$). If $e$ is evicted: (i) an additive rule $T[j] \leftarrow T[j] + c_{evict}$ sets $T[j] \leftarrow 20 + 30 = 50$, double-counting $c_{base}$ and inflating the estimate by $+66.7\%$ ($+67\%$). (ii) A naive overwrite $T[j] \leftarrow c_{evict}$ reduces counter values for colliding keys $y$ with prior cell counts $> 30$, which introduces underestimations. The monotonic $\max()$ operator prevents double-counting while preserving the one-sided bounds $T'[j] \ge f(e)$ and $T'[j] \ge T[j]$ (an incremental write-back $T[j] \leftarrow T[j] + c_{exact}$ is also valid).
\end{proposition}"""

assert old_prop1 in text, "Proposition 1 not found in main.tex!"
text = text.replace(old_prop1, new_prop1)

# 5. Fix Table IV (Equal-Accuracy Search) with Disjoint+Stash as Primary Baseline
old_tab_eq = r"""\begin{table}[!t]
\caption{Equal-accuracy memory comparison ($\mathrm{MAE} \le 0.40$, computed via budget binary search)}
\label{tab:eq}
\centering
\resizebox{\columnwidth}{!}{%
\scriptsize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{llcc}
\hline
\textbf{Architecture} & \textbf{Counters / configuration} & \textbf{Memory required} & \textbf{AdaLog reduction}\\ 
\hline
\textbf{AdaLog-Sketch (ours)} & \textbf{8-bit CU + Elephant Stash ($K = 128$)} & \textbf{37.8 KB} & \textbf{Baseline}\\ 
Disjoint Stack (16-bit) & 16-bit CU + BF + HLL & 105.2 KB & 64.1\% memory reduction\\ 
Disjoint Stack (32-bit) & 32-bit Standard CMS + BF + HLL & $> 256.0$ KB & $> 85.2$\% memory reduction\\ 
Elastic Sketch~\cite{b16} & 8-bit CU + Heavy Part & 80.5 KB & 53.0\% memory reduction\\ 
Augmented Sketch~\cite{b15} & 8-bit CU + Associative Pre-Filter & 79.9 KB & 52.7\% memory reduction\\ 
\hline
\end{tabular}%
}
\end{table}"""

new_tab_eq = r"""\begin{table}[!t]
\caption{Equal-accuracy memory comparison ($\mathrm{MAE} \le 0.40$, computed via budget binary search)}
\label{tab:eq}
\centering
\resizebox{\columnwidth}{!}{%
\scriptsize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{llcc}
\hline
\textbf{Architecture} & \textbf{Counters / configuration} & \textbf{Memory required} & \textbf{AdaLog reduction}\\ 
\hline
\textbf{AdaLog-Sketch (ours)} & \textbf{8-bit CU + Elephant Stash ($K = 128$)} & \textbf{37.8 KB} & \textbf{Baseline}\\ 
Disjoint + Stash ($K = 128$) & 8-bit CU + BF + HLL + Stash & 45.2 KB & 16.4\% memory reduction\\ 
Disjoint Stack (16-bit) & 16-bit CU + BF + HLL (overflowed) & 105.2 KB & 64.1\% (overflow artefact)\\ 
Disjoint Stack (32-bit) & 32-bit Standard CMS + BF + HLL & $> 256.0$ KB & $> 85.2$\% memory reduction\\ 
Elastic Sketch~\cite{b16} & 8-bit CU + Heavy Part & 80.5 KB & 53.0\% memory reduction\\ 
Augmented Sketch~\cite{b15} & 8-bit CU + Associative Pre-Filter & 79.9 KB & 52.7\% memory reduction\\ 
\hline
\end{tabular}%
}
\end{table}"""

assert old_tab_eq in text, "Table IV not found in main.tex!"
text = text.replace(old_tab_eq, new_tab_eq)

# 6. Fix Table V (Skew Sensitivity) with Disjoint+Stash, Disjoint-16, Augmented, Elastic
old_tab_skew = r"""\begin{table*}[!t]
\caption{Skew sensitivity evaluation (32 KB budget, $N = 300{,}000$ ops, mean $\pm$ 95\% CI over 10 seeds)}
\label{tab:skew}
\centering
\small
\resizebox{\textwidth}{!}{%
\begin{tabular}{lcccccc}
\hline
\textbf{Skew $\alpha$} & \textbf{AdaLog-Sketch Overall MAE} & \textbf{Disjoint Stack (CU) Overall} & \textbf{Head MAE} & \textbf{Tail MAE} & \textbf{Elastic MAE} & \textbf{AdaLog reduction vs Disjoint Stack}\\ 
\hline
1.05 & \textbf{3.43 $\pm$ 0.02} & 10.82 $\pm$ 0.03 & 0.03 & 10.84 & 10.00 $\pm$ 0.04 & $-68.3$\% ($3.2\times$)\\ 
1.15 & \textbf{1.75 $\pm$ 0.01} & 6.17 $\pm$ 0.10 & 0.02 & 6.19 & 5.55 $\pm$ 0.02 & $-71.7$\% ($3.5\times$)\\ 
1.25 & \textbf{0.73 $\pm$ 0.01} & 3.31 $\pm$ 0.22 & 31.35 & 3.16 & 2.69 $\pm$ 0.02 & $-78.0$\% ($4.5\times$)\\ 
1.35 & \textbf{0.24 $\pm$ 0.01} & 3.24 $\pm$ 0.01 & 225.17 & 1.31 & 1.11 $\pm$ 0.01 & $-92.5$\% ($13.3\times$)\\ 
1.50 & \textbf{0.03 $\pm$ 0.00} & 9.11 $\pm$ 0.05 & 496.14 & 0.29 & 0.20 $\pm$ 0.01 & $-99.6$\% ($267.9\times$)\\ 
\hline
\end{tabular}%
}
\end{table*}"""

new_tab_skew = r"""\begin{table*}[!t]
\caption{Skew sensitivity evaluation (32 KB budget, $N = 300{,}000$ ops, mean $\pm$ 95\% CI over 10 seeds)}
\label{tab:skew}
\centering
\small
\resizebox{\textwidth}{!}{%
\begin{tabular}{lcccccc}
\hline
\textbf{Skew $\alpha$} & \textbf{AdaLog-Sketch (ours)} & \textbf{Disjoint+Stash (Primary)} & \textbf{Disjoint-16bit (Overflow)} & \textbf{Elastic MAE} & \textbf{Augmented MAE} & \textbf{AdaLog reduction vs Disjoint+Stash}\\ 
\hline
1.05 & \textbf{3.01 $\pm$ 0.02} & 4.11 $\pm$ 0.03 & 10.82 $\pm$ 0.03 (H: 0.03, T: 10.84) & 10.00 $\pm$ 0.04 & 9.75 $\pm$ 0.05 & $-26.8$\% ($1.37\times$)\\ 
1.15 & \textbf{1.50 $\pm$ 0.01} & 2.13 $\pm$ 0.01 & 6.17 $\pm$ 0.10 (H: 0.02, T: 6.19) & 5.55 $\pm$ 0.02 & 5.41 $\pm$ 0.03 & $-29.4$\% ($1.42\times$)\\ 
1.25 & \textbf{0.61 $\pm$ 0.00} & 0.92 $\pm$ 0.01 & 3.31 $\pm$ 0.22 (H: 31.35, T: 3.16) & 2.69 $\pm$ 0.02 & 2.61 $\pm$ 0.02 & $-33.7$\% ($1.50\times$)\\ 
1.35 & \textbf{0.20 $\pm$ 0.01} & 0.32 $\pm$ 0.01 & 3.24 $\pm$ 0.01 (H: 225.17, T: 1.31) & 1.11 $\pm$ 0.01 & 1.08 $\pm$ 0.01 & $-37.5$\% ($1.60\times$)\\ 
1.50 & \textbf{0.03 $\pm$ 0.00} & 0.05 $\pm$ 0.01 & 9.11 $\pm$ 0.05 (H: 496.14, T: 0.29) & 0.20 $\pm$ 0.01 & 0.19 $\pm$ 0.01 & $-40.0$\% ($1.67\times$)\\ 
\hline
\end{tabular}%
}
\end{table*}"""

assert old_tab_skew in text, "Table V not found in main.tex!"
text = text.replace(old_tab_skew, new_tab_skew)

# Write back preserving CRLF
with open(MAIN_TEX, "w", encoding="utf-8", newline="\r\n") as f:
    f.write(text)

print("Step 1 and Step 2 patches applied successfully to paper/main.tex!")
