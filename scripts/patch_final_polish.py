"""Final polish for paper/main.tex resolving all remaining reviewer audit details.
"""

import os
import re

MAIN_TEX = os.path.abspath("paper/main.tex")
with open(MAIN_TEX, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update Planner Normalizers and explain fixed m=1024
old_planner_text = r"""\begin{equation}
\min_{d,w,bits,m,K,\tau}\;L=w_{mae}\frac{\mathrm{MAE}_{pred}}{\mathrm{MAE}_0}+w_{fpr}\frac{\mathrm{FPR}_{pred}}{\mathrm{FPR}_0}+w_{rse}\frac{\mathrm{RSE}_{pred}}{\mathrm{RSE}_0}
\end{equation}
subject to $\mathrm{Memory}(d,w,bits,m,K)\le B$."""

new_planner_text = r"""\begin{equation}
\min_{d,w,bits,m,K,\tau}\;L=w_{mae}\frac{\mathrm{MAE}_{pred}}{\mathrm{MAE}_0}+w_{fpr}\frac{\mathrm{FPR}_{pred}}{\mathrm{FPR}_0}+w_{rse}\frac{\mathrm{RSE}_{pred}}{\mathrm{RSE}_0}
\end{equation}
subject to $\mathrm{Memory}(d,w,bits,m,K)\le B$. Here, $w_{mae}, w_{fpr}, w_{rse}$ are user-specified task priority weights ($w_{mae}=0.50, w_{fpr}=0.25, w_{rse}=0.25$ by default, $\sum w=1$), and $\mathrm{MAE}_0=1.0, \mathrm{FPR}_0=0.05, \mathrm{RSE}_0=0.05$ are baseline scale normalizers bringing each metric onto a dimensionless unit scale. While the planner jointly optimizes register count $m\in\{512,1024,2048,4096\}$, our headline evaluations fix $m=1{,}024$ (768~bytes) to evaluate the decoupled layout under a controlled, constant-cardinality allocation against disjoint baselines."""

text = text.replace(old_planner_text, new_planner_text)

# 2. Rename Section V.B and fix certificate terminology
text = text.replace(r"\subsection{Cross-Task Calibration \& Error Certificates}",
                    r"\subsection{Cross-Task Calibration \& Empirical Confidence Intervals}")
text = text.replace("The certified intervals reached", "The empirical confidence intervals reached")

# 3. Update Line 617 (AMQ trade-off numbers)
old_amq_tradeoff = r"causing Variant A FPR to drop to 1.37\% (128~KB) and 0.11\% (256~KB) at zero marginal memory cost."
new_amq_tradeoff = r"causing Variant A FPR to drop to 3.86\% (128~KB) and 0.44\% (256~KB) at zero marginal memory cost."
text = text.replace(old_amq_tradeoff, new_amq_tradeoff)

# 4. Update Line 620 (Cardinality RSE)
old_card_text = r"producing a flat cardinality RSE of 0.0396 (close to the asymptotic bound $1.04/\sqrt{1024}=0.0325$)."
new_card_text = r"producing a flat cardinality RSE of 0.0424 across seeds (close to the asymptotic bound $1.04/\sqrt{1024}=0.0325$)."
text = text.replace(old_card_text, new_card_text)

# 5. Update Line 622 (Replace label N2)
text = text.replace(r"\subsection{Negative Result: Online Adaptive Controller (N2)}",
                    r"\subsection{Negative Result: Online Adaptive Threshold Controller}")

# 6. Update Conclusion
old_concl = r"""At equivalent memory, AdaLog-Sketch cuts frequency error by approximately $3\times$ versus same-width Conservative Update sketches and $3\text{--}5\times$ versus Elastic and Augmented Sketches up to 64~KB, with zero underestimations. It trades this for higher membership false positives and lower cardinality precision than dedicated single-purpose structures, while sustaining matching C++ ingestion throughput (1.92~Mops/s)."""

new_concl = r"""At equivalent memory, AdaLog-Sketch reduces frequency error by up to $3.8\text{--}6.3\times$ versus disjoint sketches and $3\text{--}5\times$ versus Elastic and Augmented Sketches up to 64~KB, with strictly zero underestimations ($K \ge K_{sat}$). It trades this for higher membership false positives and lower cardinality precision than dedicated single-purpose structures, while sustaining matching or superior C++ ingestion throughput ($22.2\text{ Mops/s}$ vs. $20.3\text{ Mops/s}$)."""

text = text.replace(old_concl, new_concl)

# Write back
with open(MAIN_TEX, "w", encoding="utf-8") as f:
    f.write(text)

print("Final polish applied successfully to paper/main.tex!")
