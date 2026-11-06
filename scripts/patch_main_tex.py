def patch_main_tex():
    tex_path = 'paper/manuscript/main.tex'
    with open(tex_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Preamble: replace balance with flushend and add float controls
    old_balance = r'\usepackage{balance}'
    new_balance = (
        r'\usepackage{flushend}' + '\n\n' +
        r'% Float placement parameters to avoid float-only pages' + '\n' +
        r'\renewcommand{\topfraction}{0.95}' + '\n' +
        r'\renewcommand{\bottomfraction}{0.85}' + '\n' +
        r'\renewcommand{\textfraction}{0.05}' + '\n' +
        r'\renewcommand{\floatpagefraction}{0.85}' + '\n' +
        r'\setcounter{topnumber}{4}' + '\n' +
        r'\setcounter{bottomnumber}{3}' + '\n' +
        r'\setcounter{totalnumber}{6}' + '\n' +
        r'\setcounter{dbltopnumber}{2}' + '\n' +
        r'\renewcommand{\dbltopfraction}{0.95}' + '\n' +
        r'\renewcommand{\dblfloatpagefraction}{0.85}'
    )
    assert old_balance in content, 'balance package not found'
    content = content.replace(old_balance, new_balance, 1)

    # 2. Abstract: clarify hash accounting and latencies
    old_abs_lat = r'a $1.11\times$ speedup over disjoint execution (19.84~Mops/s, 50.4~ns/op; $2+4+1=7$ disjoint hashes vs. 1 128-bit hash), with 13.0~ns point query latency and 26.0~ns membership query latency.'
    new_abs_lat = r'a $1.11\times$ speedup over disjoint execution (19.84~Mops/s, 50.4~ns/op; 3 separate 128-bit hashes in modular baselines or $7$--$12$ unshared hashes in disjoint stacks vs. 1 unified 128-bit pipeline in AdaLog), with 13.0~ns point frequency estimation latency and 26.0~ns approximate membership query latency.'
    assert old_abs_lat in content, 'old_abs_lat not found'
    content = content.replace(old_abs_lat, new_abs_lat, 1)

    # 3. Intro: hash accounting
    old_intro_hash = r'\item \textbf{Redundant hashing computations:} Each arrival triggers $k_{BF} + d_{CMS} + 1_{HLL}$ independent hash evaluations (typically $7 + 4 + 1 = 12$ calls), consuming 40--60\% of per-packet processing budgets.'
    new_intro_hash = r'\item \textbf{Redundant hashing computations:} Each arrival in an unoptimized disjoint stack triggers $k_{\mathrm{BF}} + d_{\mathrm{CMS}} + 1_{\mathrm{HLL}} = 7 + 4 + 1 = 12$ independent hash evaluations (or $2 + 4 + 1 = 7$ evaluations when Kirsch-Mitzenmacher double hashing is applied to the Bloom filter), consuming 40--60\% of per-packet processing budgets.'
    assert old_intro_hash in content, 'old_intro_hash not found'
    content = content.replace(old_intro_hash, new_intro_hash, 1)

    # 4. Line 154: KM row indices uint64_t syntax fix
    old_km = r'where $h_{1,\text{low}} = (uint64\_t)(h_1 \ \& \ \text{0xFFFFFFFF})$ and $h_{1,\text{high}} = (uint64\_t)((h_1 \gg 32) \ \& \ \text{0xFFFFFFFF})$. When $w$ is a power of two, the odd multiplier $(h_{1,\text{high}} \mid 1)$ is coprime to $w$, generating a full cycle of length $w$. For composite widths, cycle length $w / \gcd(h_{1,\text{high}} \mid 1, w) \gg d=4$ guarantees non-repeating row indices.'
    new_km = r'where $h_{1,\text{low}} = (h_1 \mathbin{\&} \mathtt{0xFFFFFFFF})$ and $h_{1,\text{high}} = ((h_1 \gg 32) \mathbin{\&} \mathtt{0xFFFFFFFF})$ (both evaluated as 64-bit unsigned integers). When $w$ is a power of two, the odd multiplier $(h_{1,\text{high}} \mid 1)$ is coprime to $w$, generating a full cycle of length $w$. For composite widths, cycle length $w / \gcd(h_{1,\text{high}} \mid 1, w) \gg d=4$ guarantees non-repeating row indices.'
    assert old_km in content, 'old_km not found'
    content = content.replace(old_km, new_km, 1)

    # 5. Line 155: HLL register index reg_idx syntax fix
    old_hll = r'select the register index: $reg\_idx = (h_2 \gg 54) \ \& \ (m - 1)$. The rank $\rho$'
    new_hll = r'select the register index: $idx_{\mathrm{reg}} = (h_2 \gg 54) \mathbin{\&} (m - 1)$. The rank $\rho$'
    assert old_hll in content, 'old_hll not found'
    content = content.replace(old_hll, new_hll, 1)

    # 6. Bitwise typography on tags
    old_tag1 = r'secondary 31-bit tag $tag = h_2 \ \& \ \text{0x7FFFFFFF}$'
    new_tag1 = r'secondary 31-bit tag $tag = h_2 \mathbin{\&} \mathtt{0x7FFFFFFF}$'
    assert old_tag1 in content, 'old_tag1 not found'
    content = content.replace(old_tag1, new_tag1, 1)

    old_tag2 = r'$tag = (h_2 \ \& \ \text{0x7FFFFFFF}) \mid \text{0x80000000}$'
    new_tag2 = r'$tag = (h_2 \mathbin{\&} \mathtt{0x7FFFFFFF}) \mid \mathtt{0x80000000}$'
    assert old_tag2 in content, 'old_tag2 not found'
    content = content.replace(old_tag2, new_tag2, 1)

    # 7. Algorithm 1 replacements (line by line)
    old_a1 = r'$reg\_idx \leftarrow (h_2 \gg (64 - p)) \ \& \ (m - 1)$'
    new_a1 = r'$idx_{\mathrm{reg}} \leftarrow (h_2 \gg (64 - p)) \mathbin{\&} (m - 1)$'
    assert old_a1 in content, 'old_a1 not found'
    content = content.replace(old_a1, new_a1, 1)

    old_a2 = r'$M[reg\_idx] \leftarrow \max(M[reg\_idx], \rho)$'
    new_a2 = r'$M[idx_{\mathrm{reg}}] \leftarrow \max(M[idx_{\mathrm{reg}}], \rho)$'
    assert old_a2 in content, 'old_a2 not found'
    content = content.replace(old_a2, new_a2, 1)

    old_a3 = r'$tag \leftarrow h_2 \ \& \ \text{0x7FFFFFFF}$'
    new_a3 = r'$tag \leftarrow h_2 \mathbin{\&} \mathtt{0x7FFFFFFF}$'
    assert old_a3 in content, 'old_a3 not found'
    content = content.replace(old_a3, new_a3, 1)

    old_a4 = r'$h_{1,\text{low}} \leftarrow h_1 \ \& \ \text{0xFFFFFFFF}, \ h_{1,\text{high}} \leftarrow (h_1 \gg 32) \mid 1$'
    new_a4 = r'$h_{1,\text{low}} \leftarrow h_1 \mathbin{\&} \mathtt{0xFFFFFFFF}, \ h_{1,\text{high}} \leftarrow (h_1 \gg 32) \mid 1$'
    assert old_a4 in content, 'old_a4 not found'
    content = content.replace(old_a4, new_a4, 1)

    # 8. Move Fig 5 into Section IV and remove duplicate from Section V
    old_sec4_end = r'Sizing $K \ge K_{\mathrm{plan}}$ ensures that the conditional prerequisite $K \ge K_{sat}^*$ of Theorem~\ref{thm:conservative} holds with probability $\ge 1 - \delta_{sat} \ge 99.9\%$. At 32~KB, with $K = 128$ ($3{,}072$ B), width is $w = \lfloor (32{,}768 - 3{,}072 - 768) / 4 \rfloor = 7{,}232$ columns.'
    new_sec4_end = (
        r'Sizing $K \ge K_{\mathrm{plan}}$ ensures that the conditional prerequisite $K \ge K_{sat}^*$ of Theorem~\ref{thm:conservative} holds with probability $\ge 1 - \delta_{sat} \ge 99.9\%$. At 32~KB, with $K = 128$ ($3{,}072$ B), width is $w = \lfloor (32{,}768 - 3{,}072 - 768) / 4 \rfloor = 7{,}232$ columns. As demonstrated in Fig.~\ref{fig:planner}, the analytical closed-form equations formulated in AdaLog-Planner accurately predict measured empirical frequency MAE, AMQ false positive rate, and cardinality error across memory allocations from 8~KB to 128~KB.' + '\n\n' +
        r'\begin{figure}[!tbp]' + '\n' +
        r'\centering' + '\n' +
        r'\includegraphics[width=\columnwidth,keepaspectratio]{fig5_planner_accuracy.pdf}' + '\n' +
        r'\caption{AdaLog-Planner analytical prediction accuracy vs. measured empirical metrics across memory budgets ($8 \dots 128$~KB). (a) Frequency MAE; (b) AMQ False Positive Rate; (c) Cardinality Relative Standard Error.}' + '\n' +
        r'\label{fig:planner}' + '\n' +
        r'\end{figure}'
    )
    assert old_sec4_end in content, 'old_sec4_end not found'
    content = content.replace(old_sec4_end, new_sec4_end, 1)

    # Remove fig5 from Section V
    fig5_block = (
        r'\begin{figure}[!tbp]' + '\n' +
        r'\centering' + '\n' +
        r'\includegraphics[width=\columnwidth,keepaspectratio]{fig5_planner_accuracy.pdf}' + '\n' +
        r'\caption{AdaLog-Planner analytical prediction accuracy vs. measured empirical metrics across memory budgets ($8 \dots 128$~KB). (a) Frequency MAE; (b) AMQ False Positive Rate; (c) Cardinality Relative Standard Error.}' + '\n' +
        r'\label{fig:planner}' + '\n' +
        r'\end{figure}'
    )
    # Notice there are now two occurrences (one we just added in sec4, one in sec5).
    # We want to remove the second one!
    first_idx = content.find(fig5_block)
    assert first_idx != -1, 'first fig5 block not found'
    second_idx = content.find(fig5_block, first_idx + len(fig5_block))
    assert second_idx != -1, 'second fig5 block in sec5 not found'
    content = content[:second_idx] + content[second_idx + len(fig5_block):]

    # 9. Theorem 2 proof repair for rejected-eviction branch
    old_case2 = r'\textbf{Case 2 (Stash admission, $x \notin E$ and $v_{min} + c \ge \tau$):} Here $v_{min} \ge f_{t-1}(x)$ by hypothesis. (2a) If $|E| < K$, entry $(x, v_{min}, c)$ is inserted; $\hat{f}_{raw,t}(x) = v_{min} + c \ge f_t(x)$. (2b) If $|E| = K$, non-saturated victim $e = \arg\min_{y \in \mathcal{E}} y.total$ ($c_{evict} < \MV$) is evicted. Lossless monotonic write-back sets $T_t[j, idx_{j,e}] \leftarrow \max(T_{t-1}[j, idx_{j,e}], c_{evict}) \ge f_t(e)$. Candidate $x$ is inserted with $c_{base} = v_{min}, c_{exact} = c$, preserving $\hat{f}_{raw,t}(x) \ge f_t(x)$.'
    new_case2 = (
        r'\textbf{Case 2 (Stash admission, $x \notin E$ and $v_{min} + c \ge \tau$):} Here $v_{min} \ge f_{t-1}(x)$ by hypothesis. ' + '\n' +
        r'(2a) If $|E| < K$, entry $(x, v_{min}, c)$ is inserted into $E$; then $\hat{f}_{raw,t}(x) = v_{min} + c \ge f_t(x)$. ' + '\n' +
        r'(2b) If $|E| = K$, candidate count is $v_{cand} = v_{min} + c$. If non-saturated resident entries exist ($\mathcal{E} = \{y \in E \mid y.c_{base} + y.c_{exact} < \MV\} \neq \emptyset$), victim $e = \arg\min_{y \in \mathcal{E}} (y.c_{base} + y.c_{exact})$ has count $c_{evict} < \MV$. If $v_{cand} > c_{evict}$, item $e$ is evicted via lossless monotonic write-back ($T_t[j, idx_{j,e}] \leftarrow \max(T_{t-1}[j, idx_{j,e}], c_{evict}) \ge f_t(e)$), and candidate $x$ enters the stash with $\hat{f}_{raw,t}(x) = v_{cand} \ge f_t(x)$. If $v_{cand} \le c_{evict}$, candidate $x$ is rejected from stash admission; crucially, because $v_{min} + c \le c_{evict} < \MV$, candidate count is strictly below saturation. Matrix CU fallback records $T_t[j, idx_j(x)] \leftarrow \max(T_{t-1}[j, idx_j(x)], v_{min} + c) \ge f_t(x)$ without truncation error.'
    )
    assert old_case2 in content, 'old_case2 not found'
    content = content.replace(old_case2, new_case2, 1)

    old_case3 = r'\textbf{Case 3 (Matrix CU fallback):} Candidate $x$ updates $T_t[j, idx_j(x)] \leftarrow \max(T_{t-1}[j, idx_j(x)], \min(\MV, v_{min} + c))$. (3a) If $f_t(x) \le \MV$, $\min(\MV, v_{min} + c) \ge f_t(x)$, preserving the invariant. (3b) If $f_t(x) > \MV$, $x$ must have arrived at earlier steps where count was in $[\tau, \MV - 1]$. Candidate $x$ can only be rejected if all $K$ stash slots hold entries with total count $\ge \MV$. Because exact counts only increment on true arrivals ($c_{exact} \le f(y)$), all $K$ resident keys must have saturated. Along with $x$, this implies at least $K + 1$ keys have saturated, contradicting premise $K \ge K_{sat}^*$. Hence, no key reaching saturation can remain outside the stash. Combining Cases 1--3, $\hat{f}_{raw,t}(y) \ge f_t(y)$ holds for all $y \in U$ at every step $t$.'
    new_case3 = (
        r'\textbf{Case 3 (Matrix CU update without stash admission):} Candidate $x$ updates $T_t[j, idx_j(x)] \leftarrow \max(T_{t-1}[j, idx_j(x)], \min(\MV, v_{min} + c))$. ' + '\n' +
        r'If $v_{min} + c < \MV$, no counter truncation occurs: $\min(\MV, v_{min} + c) = v_{min} + c \ge f_t(x)$. ' + '\n' +
        r'Truncation error can only occur if $v_{min} + c \ge \MV$ while $x \notin E$. Because $\MV > \tau$, $x$ must have requested stash admission; rejection while $v_{cand} \ge \MV$ can only occur if no non-saturated victim exists ($\mathcal{E} = \emptyset$), requiring all $K$ resident entries to have reached saturation ($y.total \ge \MV$). Because exact counts accumulate strictly from stream arrivals ($c_{exact} \le f(y)$), all $K$ resident keys plus candidate $x$ would constitute at least $K + 1$ distinct keys reaching saturation, directly contradicting premise $K \ge K_{sat}^*$. Hence, no key reaching saturation can remain outside the stash. ' + '\n' +
        r'Combining Cases 1--3, $\hat{f}_{raw,t}(y) \ge f_t(y)$ holds for all $y \in U$ at every step $t$.'
    )
    assert old_case3 in content, 'old_case3 not found'
    content = content.replace(old_case3, new_case3, 1)

    # 10. Exp 1 & Exp 2 text figure references
    old_exp1_text = r'Across budgets $\ge 32$~KB ($K = 128 \ge 100$), AdaLog-Sketch achieves strictly 1.00 precision and 1.00 recall for global top-100 heavy hitters'
    new_exp1_text = r'As depicted in Fig.~\ref{fig:pareto}, across budgets $\ge 32$~KB ($K = 128 \ge 100$), AdaLog-Sketch achieves strictly 1.00 precision and 1.00 recall for global top-100 heavy hitters'
    assert old_exp1_text in content, 'old_exp1_text not found'
    content = content.replace(old_exp1_text, new_exp1_text, 1)

    old_exp2_text = r'Table~\ref{tab:skew} reports frequency MAE across Zipfian skews $\alpha \in [1.05, 1.50]$ at fixed 32~KB.'
    new_exp2_text = r'Table~\ref{tab:skew} and Fig.~\ref{fig:skew} report frequency MAE across Zipfian skews $\alpha \in [1.05, 1.50]$ at fixed 32~KB.'
    assert old_exp2_text in content, 'old_exp2_text not found'
    content = content.replace(old_exp2_text, new_exp2_text, 1)

    # 11. CAIDA provenance
    old_caida = r'(1) \textbf{CAIDA network backbone trace:} Packet headers from the CAIDA 2016 Equinix Chicago backbone ($N = 300{,}000$ packets, $n = 41{,}824$ flows; 5-tuple keys).'
    new_caida = r'(1) \textbf{Synthetic CAIDA-modeled network trace:} Synthetic 5-tuple packet flows generated to match the heavy-tailed flow-size distribution of the CAIDA 2016 Equinix Chicago backbone ($N = 300{,}000$ packets, $n = 41{,}824$ flows; 5-tuple keys).'
    assert old_caida in content, 'old_caida not found'
    content = content.replace(old_caida, new_caida, 1)

    # 12. Remove \balance call
    old_balance_call = r'\balance' + '\n' + r'\subsection{Threats to validity}\label{sec:threats}'
    new_balance_call = r'\subsection{Threats to validity}\label{sec:threats}'
    assert old_balance_call in content, 'old_balance_call not found'
    content = content.replace(old_balance_call, new_balance_call, 1)

    # 13. Conclusion query latency
    old_concl_lat = r'with 12.3~ns/op membership query latency.'
    new_concl_lat = r'with 26.0~ns/op membership query latency and 13.0~ns/op point estimation latency.'
    assert old_concl_lat in content, 'old_concl_lat not found'
    content = content.replace(old_concl_lat, new_concl_lat, 1)

    with open('paper/manuscript/main.tex', 'w', encoding='utf-8') as f:
        f.write(content)

    with open('paper/main.tex', 'w', encoding='utf-8') as f:
        f.write(content)

    print('Successfully applied all 13 updates to paper/manuscript/main.tex and paper/main.tex!')

if __name__ == '__main__':
    patch_main_tex()
