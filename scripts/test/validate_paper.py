"""Comprehensive validator for paper/main.tex.
"""

import re
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAIN_TEX = os.path.join(PROJECT_ROOT, "paper", "main.tex")

with open(MAIN_TEX, "r", encoding="utf-8") as f:
    text = f.read()

lines = text.splitlines()
print(f"Total lines: {len(lines)}")

# 1. Check for stale RSE values
stale_00424 = [i+1 for i, l in enumerate(lines) if "0.0424" in l]
stale_00376 = [i+1 for i, l in enumerate(lines) if "0.0376" in l]
print(f"Stale 0.0424 occurrences: {stale_00424}")
print(f"Stale 0.0376 occurrences: {stale_00376}")
assert len(stale_00424) == 0, f"Found stale 0.0424 at lines {stale_00424}"
assert len(stale_00376) == 0, f"Found stale 0.0376 at lines {stale_00376}"

# 2. Check 0.0239 occurrences
valid_00239 = [i+1 for i, l in enumerate(lines) if "0.0239" in l]
print(f"0.0239 occurrences ({len(valid_00239)}): {valid_00239}")
assert len(valid_00239) >= 14, f"Expected at least 14 occurrences of 0.0239 across tables, text, abstract, conclusion, got {len(valid_00239)}"

# 3. Check Variant B FPR
var_b_lines = [(i+1, l) for i, l in enumerate(lines) if "Variant B" in l]
print(f"Variant B mentions: {len(var_b_lines)}")
for ln, l in var_b_lines:
    print(f"  Line {ln}: {l[:80]}")

# 4. Check heading on page 10
has_old_heading = "Real word stream" in text
has_new_heading = ("Real-world stream evaluation and failure-mode analysis" in text) or ("Real-world stream evaluation and failure modes" in text)
print(f"Has old heading: {has_old_heading}")
print(f"Has new heading: {has_new_heading}")
assert not has_old_heading, "Old heading 'Real word stream' still present!"
assert has_new_heading, "New heading not found!"

# 5. Check math delimiter balance
dollar_count = 0
escaped_dollar = text.count(r"\$")
total_dollar = text.count("$")
actual_math_dollar = total_dollar - escaped_dollar
print(f"Math dollar signs: {actual_math_dollar} (is even: {actual_math_dollar % 2 == 0})")
assert actual_math_dollar % 2 == 0, "Unmatched math $ detected!"

# 6. Check environment matching
env_stack = []
env_regex = re.compile(r"\\(begin|end)\{([^}]+)\}")
for match in env_regex.finditer(text):
    op, env_name = match.group(1), match.group(2)
    if env_name == "@IEEEauthorhalign":
        continue
    if op == "begin":
        env_stack.append((env_name, match.start()))
    else:
        if not env_stack:
            raise ValueError(f"Unexpected \\end{{{env_name}}} at {match.start()}")
        last_env, start_pos = env_stack.pop()
        if last_env != env_name:
            raise ValueError(f"Mismatched env: began {last_env} at {start_pos}, ended {env_name} at {match.start()}")

print(f"Unclosed environments: {len(env_stack)}")
assert len(env_stack) == 0, f"Unclosed environments: {env_stack}"

# 7. Check bibliography closing quotes
bib_start = text.find(r"\begin{thebibliography}")
bib_end = text.find(r"\end{thebibliography}") + len(r"\end{thebibliography}")
bib_text = text[bib_start:bib_end]
bib_lines = [l for l in bib_text.splitlines() if l.startswith(r"\bibitem")]
unmatched_quotes = []
for l in bib_lines:
    if l.count("``") != l.count("''"):
        unmatched_quotes.append(l[:50])

print(f"Bibliography items checked: {len(bib_lines)}")
print(f"Bibitems with unmatched quotes: {len(unmatched_quotes)}")
assert len(bib_lines) == 44, f"Expected 44 bibitems, got {len(bib_lines)}"
assert len(unmatched_quotes) == 0, f"Unmatched quotes in bibitems: {unmatched_quotes}"

# 8. Check author block
assert r"\IEEEauthorblockN{Shobhit Agrawal}" in text
assert r"\IEEEauthorblockN{Mayuri Rajendra Pawar}" in text
assert r"\IEEEauthorblockN{Dr. Parveen Sultana H}" in text
assert "minipage" not in text[:text.find(r"\maketitle")], "Minipage still in author block!"
print("Author block verified: standard IEEEtran conference format, 0 minipages.")

print("\nALL VERIFICATION CHECKS PASSED PERFECTLY!")
