import re
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAIN_TEX = os.path.join(PROJECT_ROOT, "paper", "main.tex")

with open(MAIN_TEX, "r", encoding="utf-8") as f:
    text = f.read()

bib_start = text.find(r"\begin{thebibliography}")
bib_text = text[bib_start:]

lines = bib_text.splitlines()
missing_quotes = []
total_bib = 0
prefix = r"\bibitem"
for idx, line in enumerate(lines):
    if line.startswith(prefix):
        total_bib += 1
        open_count = line.count("``")
        close_count = line.count("''")
        if open_count != close_count:
            missing_quotes.append((line[:60], open_count, close_count))

print("Total bibitems checked:", total_bib)
print("Bibitems with unmatched quotes:", len(missing_quotes))
for item in missing_quotes:
    print(" ", item)
