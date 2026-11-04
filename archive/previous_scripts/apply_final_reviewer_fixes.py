"""Script to apply all final reviewer-requested fixes to paper/main.tex.
"""

import os
import re

MAIN_TEX = r"D:/VIT/DSA Case Study/randomized-approx-query-processing/paper/main.tex"

with open(MAIN_TEX, "r", encoding="utf-8") as f:
    text = f.read()

# 1. FIX AUTHOR BLOCK (Eliminate minipage / makebox which threw 21 errors in IEEEtran)
old_author_block = r"""\author{
  \makebox[\textwidth][c]{%
    \begin{minipage}[t]{0.32\textwidth}
      \centering
      \textbf{Shobhit Agrawal} \\
      \textit{School of Computer Science and Engineering} \\
      \textit{Vellore Institute of Technology}\\
      Vellore, Tamil Nadu, India \\
      shobhitagrawal2004@gmail.com
    \end{minipage}%
    \hfill
    \begin{minipage}[t]{0.32\textwidth}
      \centering
      \textbf{Mayuri Rajendra Pawar} \\
      \textit{School of Computer Science and Engineering} \\
      \textit{Vellore Institute of Technology}\\
      Vellore, Tamil Nadu, India \\
      mayuripawar2603@gmail.com
    \end{minipage}%
    \hfill
    \begin{minipage}[t]{0.34\textwidth}
      \centering
      \textbf{Dr. Parveen Sultana H} \\
      \textit{Associate Dean in-charge \& Faculty Guide} \\
      \textit{School of Computer Science and Engineering} \\
      \textit{(SCOPE)}\\
      \textit{Vellore Institute of Technology}\\
      Vellore, Tamil Nadu, India \\
      hparveensultana@vit.ac.in
    \end{minipage}%
  }
}"""

new_author_block = r"""\author{\IEEEauthorblockN{Shobhit Agrawal}
\IEEEauthorblockA{\textit{School of Computer Science and Engineering} \\
\textit{Vellore Institute of Technology}\\
Vellore, Tamil Nadu, India \\
shobhitagrawal2004@gmail.com}
\and
\IEEEauthorblockN{Mayuri Rajendra Pawar}
\IEEEauthorblockA{\textit{School of Computer Science and Engineering} \\
\textit{Vellore Institute of Technology}\\
Vellore, Tamil Nadu, India \\
mayuripawar2603@gmail.com}
\and
\IEEEauthorblockN{Dr. Parveen Sultana H}
\IEEEauthorblockA{\textit{Associate Dean in-charge \& Faculty Guide} \\
\textit{School of Computer Science and Engineering (SCOPE)}\\
\textit{Vellore Institute of Technology}\\
Vellore, Tamil Nadu, India \\
hparveensultana@vit.ac.in}}"""

assert old_author_block in text, "Author block not found!"
text = text.replace(old_author_block, new_author_block)
print("1. Author block updated to standard IEEEtran conference format.")

# 2. PROOF ENVIRONMENT IN PREAMBLE
old_proof_def = r"""\ifcsname IEEEproof\endcsname
  \newenvironment{proof}{\begin{IEEEproof}}{\end{IEEEproof}}
\else
  \newenvironment{proof}{\par\noindent\textit{Proof:}\ \ignorespaces}{\hfill$\blacksquare$\par\medskip}
\fi"""

new_proof_def = r"""\ifcsname IEEEproof\endcsname
  \let\proof\IEEEproof
  \let\endproof\endIEEEproof
\else
  \newenvironment{proof}{\par\noindent\textit{Proof:}\ \ignorespaces}{\hfill$\blacksquare$\par\medskip}
\fi"""

if old_proof_def in text:
    text = text.replace(old_proof_def, new_proof_def)
    print("2. Proof environment updated to robust let mapping.")

# 3. FIX CARDINALITY RSE IN TABLE IV
# Replace 0.0424 and 0.0376 with 0.0239 in Table IV
old_tab_main = r"""\begin{table}[!t]
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

new_tab_main = r"""\begin{table}[!t]
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
AdaLog-Sketch (Unified) & \textbf{15.88 $\pm$ 0.09} & \textbf{0.194} & 100.0\% & 0.0239 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Disjoint Stack (16-bit) & 30.24 $\pm$ 0.89 & 0.368 & 76.12\% & 0.0239 & N/A & 1\\ 
Disjoint+Stash ($K = 128$) & 16.13 $\pm$ 0.09 & 0.198 & 88.41\% & 0.0239 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Elastic Sketch~\cite{b16} & 23.37 $\pm$ 0.13 & 0.285 & N/A & N/A & 0.68 / 0.55 & \textbf{0}\\ 
Augmented Sketch~\cite{b15} & 22.98 $\pm$ 0.09 & 0.281 & N/A & N/A & \textbf{1.00 / 1.00} & \textbf{0}\\ 
\hline
\multicolumn{7}{l}{\textit{\textbf{16 KB budget}}} \\
AdaLog-Sketch (Unified) & \textbf{3.10 $\pm$ 0.02} & \textbf{0.038} & 98.99\% & 0.0239 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Disjoint Stack (16-bit) & 10.15 $\pm$ 0.22 & 0.124 & 51.08\% & 0.0239 & N/A & 1\\ 
Disjoint+Stash ($K = 128$) & 3.94 $\pm$ 0.02 & 0.048 & 67.32\% & 0.0239 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Elastic Sketch~\cite{b16} & 8.44 $\pm$ 0.04 & 0.103 & N/A & N/A & 0.70 / 0.70 & \textbf{0}\\ 
Augmented Sketch~\cite{b15} & 8.20 $\pm$ 0.04 & 0.100 & N/A & N/A & \textbf{1.00 / 1.00} & \textbf{0}\\ 
\hline
\multicolumn{7}{l}{\textit{\textbf{32 KB budget}}} \\
AdaLog-Sketch (Unified) & \textbf{0.61 $\pm$ 0.00} & \textbf{0.007} & 73.25\% & 0.0239 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Disjoint Stack (16-bit) & 3.31 $\pm$ 0.22 & 0.040 & 25.90\% & 0.0239 & N/A & 1\\ 
Disjoint+Stash ($K = 128$) & 0.92 $\pm$ 0.01 & 0.011 & 32.67\% & 0.0239 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Elastic Sketch~\cite{b16} & 2.69 $\pm$ 0.02 & 0.033 & N/A & N/A & 0.83 / 0.83 & \textbf{0}\\ 
Augmented Sketch~\cite{b15} & 2.61 $\pm$ 0.02 & 0.032 & N/A & N/A & \textbf{1.00 / 1.00} & \textbf{0}\\ 
\hline
\multicolumn{7}{l}{\textit{\textbf{64 KB budget}}} \\
AdaLog-Sketch (Unified) & \textbf{0.09 $\pm$ 0.00} & \textbf{0.001} & 24.12\% & 0.0239 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Disjoint Stack (16-bit) & 0.95 $\pm$ 0.01 & 0.012 & 6.58\% & 0.0239 & N/A & 1\\ 
Disjoint+Stash ($K = 128$) & 0.16 $\pm$ 0.00 & 0.002 & 10.75\% & 0.0239 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Elastic Sketch~\cite{b16} & 0.69 $\pm$ 0.01 & 0.008 & N/A & N/A & 0.90 / 0.90 & \textbf{0}\\ 
Augmented Sketch~\cite{b15} & 0.67 $\pm$ 0.00 & 0.008 & N/A & N/A & \textbf{1.00 / 1.00} & \textbf{0}\\ 
\hline
\multicolumn{7}{l}{\textit{\textbf{128 KB budget}}} \\
AdaLog-Sketch (Unified) & \textbf{0.01 $\pm$ 0.00} & \textbf{0.000} & 3.86\% & 0.0239 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Disjoint Stack (16-bit) & 0.31 $\pm$ 0.01 & 0.004 & 0.45\% & 0.0239 & N/A & 1\\ 
Disjoint+Stash ($K = 128$) & 0.02 $\pm$ 0.00 & 0.000 & 0.96\% & 0.0239 & \textbf{1.00 / 1.00} & \textbf{0}\\ 
Elastic Sketch~\cite{b16} & 0.11 $\pm$ 0.00 & 0.001 & N/A & N/A & 0.95 / 0.95 & \textbf{0}\\ 
Augmented Sketch~\cite{b15} & 0.11 $\pm$ 0.00 & 0.001 & N/A & N/A & \textbf{1.00 / 1.00} & \textbf{0}\\ 
\hline
\end{tabular}%
}
\end{table}"""

assert old_tab_main in text, "Table IV not found!"
text = text.replace(old_tab_main, new_tab_main)
print("3. Table IV updated to 0.0239 cardinality RSE across all rows.")

# 4. FIX CARDINALITY RSE IN TABLE VIII
old_tab_abl = r"""\begin{table}[!t]
\caption{Systematic component ablation matrix (32 KB budget, $\alpha = 1.25$, mean $\pm$ std over 10 seeds)}
\label{tab:abl}
\centering
\resizebox{\columnwidth}{!}{%
\small
\begin{tabular}{lccccc}
\hline
\textbf{Ablation variant} & \textbf{Width $w$} & \textbf{Raw MAE} & \textbf{Peak error} & \textbf{AMQ FPR} & \textbf{Card. RSE}\\ 
\hline
\textbf{AdaLog-Default (Decoupled)} & \textbf{7,232} & \textbf{0.61 $\pm$ 0.00} & \textbf{18} & \textbf{73.36\%} & \textbf{0.0424}\\ 
Coupled HLL ($m = w$) & 6,251 & 0.83 $\pm$ 0.01 & 19 & 81.13\% & 0.0152\\ 
No Stash ($-$Stash) & 8,000 & 11.42 $\pm$ 0.06 & 34 & 66.34\% & 0.0424\\ 
No CU ($-$Conservative Update) & 7,232 & 1.52 $\pm$ 0.02 & 28 & 73.36\% & 0.0424\\ 
16-bit Narrow Counters & 3,616 & 2.41 $\pm$ 0.02 & 49 & 97.82\% & 0.0424\\ 
32-bit Classical Counters & 1,808 & 7.53 $\pm$ 0.06 & 82 & 99.99\% & 0.0424\\ 
Membership Variant B (1-bit) & 7,012 & 0.66 $\pm$ 0.01 & 23 & 99.99\% & 0.0424\\ 
\hline
\end{tabular}%
}
\end{table}"""

new_tab_abl = r"""\begin{table}[!t]
\caption{Systematic component ablation matrix (32 KB budget, $\alpha = 1.25$, mean $\pm$ std over 10 seeds)}
\label{tab:abl}
\centering
\resizebox{\columnwidth}{!}{%
\small
\begin{tabular}{lccccc}
\hline
\textbf{Ablation variant} & \textbf{Width $w$} & \textbf{Raw MAE} & \textbf{Peak error} & \textbf{AMQ FPR} & \textbf{Card. RSE}\\ 
\hline
\textbf{AdaLog-Default (Decoupled)} & \textbf{7,232} & \textbf{0.61 $\pm$ 0.00} & \textbf{18} & \textbf{73.36\%} & \textbf{0.0239}\\ 
Coupled HLL ($m = w$) & 6,251 & 0.83 $\pm$ 0.01 & 19 & 81.13\% & 0.0152\\ 
No Stash ($-$Stash) & 8,000 & 11.42 $\pm$ 0.06 & 34 & 66.34\% & 0.0239\\ 
No CU ($-$Conservative Update) & 7,232 & 1.52 $\pm$ 0.02 & 28 & 73.36\% & 0.0239\\ 
16-bit Narrow Counters & 3,616 & 2.41 $\pm$ 0.02 & 49 & 97.82\% & 0.0239\\ 
32-bit Classical Counters & 1,808 & 7.53 $\pm$ 0.06 & 82 & 99.99\% & 0.0239\\ 
Membership Variant B (1-bit) & 7,012 & 0.66 $\pm$ 0.01 & 23 & 99.99\% & 0.0239\\ 
\hline
\end{tabular}%
}
\end{table}"""

assert old_tab_abl in text, "Table VIII not found!"
text = text.replace(old_tab_abl, new_tab_abl)
print("4. Table VIII updated to 0.0239 for all decoupled variants.")

# 5. FIX SECTION VI.D DISCUSSION OF HLL RSE
old_hll_disc = r"""\item \textbf{Coupled versus decoupled HLL:} The default decoupled HLL ($m = 1024$) dedicates 768~B to registers, which gives matrix width $w = 7{,}232$, $\mathrm{MAE} = 0.61 \pm 0.00$, and cardinality $\mathrm{RSE} = 0.0424$. The coupled layout ($m = w = 6{,}251$) has better cardinality precision ($\mathrm{RSE} = 0.0152$, in line with Flajolet's bound $1.04/\sqrt{6251} = 0.0131$) but slightly narrower counters, which raises frequency MAE to $0.83 \pm 0.01$."""

new_hll_disc = r"""\item \textbf{Coupled versus decoupled HLL:} The default decoupled HLL ($m = 1024$) dedicates 768~B to registers, which gives matrix width $w = 7{,}232$, $\mathrm{MAE} = 0.61 \pm 0.00$, and measured cardinality $\mathrm{RSE} = 0.0239 \pm 0.0183$ (consistent with Flajolet's bound $1.04/\sqrt{1024} = 0.0325$). The coupled layout ($m = w = 6{,}251$) has better cardinality precision ($\mathrm{RSE} = 0.0152$, in line with Flajolet's bound $1.04/\sqrt{6251} = 0.0131$) but slightly narrower counters, which raises frequency MAE to $0.83 \pm 0.01$."""

assert old_hll_disc in text, "HLL discussion text not found!"
text = text.replace(old_hll_disc, new_hll_disc)
print("5. HLL discussion in Section VI.D updated to 0.0239.")

# 6. FIX SECTION VI.D DISCUSSION OF VARIANT B
old_varb_disc = r"""\item \textbf{Membership Variant B:} Dedicating $w/8$ bytes to an explicit presence plane reduces matrix width to $w = 7{,}012$ ($\mathrm{MAE} = 0.66 \pm 0.01$). When 18,700 distinct stream keys map into 7,012 bits, bit saturation causes 99.99\% FPR, so single-bit planes need dynamic scaling or decoupled allocation under high stream cardinality."""

new_varb_disc = r"""\item \textbf{Membership Variant B:} Dedicating $w/8$ bytes (876~B) to an explicit presence plane reduces matrix width to $w = 7{,}012$ ($\mathrm{MAE} = 0.66 \pm 0.01$). When $n \approx 18{,}700$ distinct stream keys map into 7,012 bits across $d = 4$ hashes, the zero-bit probability is $(1 - 1/w)^{nd} \approx e^{-4 \times 18700 / 7012} = e^{-10.67} \approx 2.3 \times 10^{-5}$. Complete bit saturation produces a measured 99.99\% AMQ FPR (raw 0.99989), confirming that in-band 1-bit presence planes are ineffective under high distinct cardinality within a fixed 32~KB budget."""

assert old_varb_disc in text, "Variant B discussion text not found!"
text = text.replace(old_varb_disc, new_varb_disc)
print("6. Variant B discussion in Section VI.D refined and verified consistent.")

# 7. FIX HEADING ON PAGE 10 ("Real word stream evaluation" -> "Real-world stream evaluation")
old_heading = r"\subsection{Real word stream evaluation and failure-mode analysis}"
new_heading = r"\subsection{Real-world stream evaluation and failure-mode analysis}"

assert old_heading in text, "Heading 'Real word stream evaluation' not found!"
text = text.replace(old_heading, new_heading)
print("7. Heading corrected to 'Real-world stream evaluation and failure-mode analysis'.")

# 8. UPDATE BIBLIOGRAPHY WITH STRICT CLOSING QUOTES AND CLEAN FORMATTING
from generate_clean_bib import corrected_bib

old_bib_start = text.find(r"\begin{thebibliography}{00}")
old_bib_end = text.find(r"\end{thebibliography}") + len(r"\end{thebibliography}")
assert old_bib_start != -1 and old_bib_end != -1, "Bibliography block not found!"

new_bib_lines = [r"\begin{thebibliography}{00}"]
for i in range(1, 45):
    key = f"b{i}"
    new_bib_lines.append(corrected_bib[key])
new_bib_lines.append(r"\end{thebibliography}")

new_bib_block = "\n".join(new_bib_lines)
text = text[:old_bib_start] + new_bib_block + text[old_bib_end:]
print("8. Bibliography updated with perfectly formatted closing quotes for all 44 entries.")

# Write updated file
with open(MAIN_TEX, "w", encoding="utf-8", newline="\r\n") as f:
    f.write(text)

print("\nAll updates successfully written to paper/main.tex!")
