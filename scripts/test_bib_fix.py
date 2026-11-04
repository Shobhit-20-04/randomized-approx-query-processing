import re

MAIN_TEX = r"D:/VIT/DSA Case Study/randomized-approx-query-processing/paper/main.tex"

with open(MAIN_TEX, "r", encoding="utf-8") as f:
    text = f.read()

bib_start = text.find(r"\begin{thebibliography}")
bib_end = text.find(r"\end{thebibliography}") + len(r"\end{thebibliography}")
bib_text = text[bib_start:bib_end]

lines = bib_text.splitlines()
new_lines = []

for line in lines:
    if line.startswith(r"\bibitem"):
        # Match pattern: \bibitem{key} Authors, ``Title, in \textit{... or ``, \textit{...
        # We want: \bibitem{key} Authors, ``Title,'' in \textit{... or ``, '' \textit{...
        m = re.match(r"(\\bibitem\{[^}]+\}\s+[^,]+(?:,[^,]+)*,\s+``)([^,]+(?:,[^,]+)*?)(,\s*(?:in\s+)?\\textit\{.*)", line)
        if m:
            prefix, title, suffix = m.group(1), m.group(2), m.group(3)
            # if suffix starts with ', in \textit', turn into ',\'\' in \\textit'
            # or if suffix starts with ', \textit', turn into ',\'\' \\textit'
            # Note: in standard IEEE style: ``Title,'' in \textit{...}
            if suffix.startswith(","):
                new_suffix = ",''" + suffix[1:]
            else:
                new_suffix = "''" + suffix
            new_line = prefix + title + new_suffix
            new_lines.append(new_line)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

print("Sample transformed lines:")
for l in new_lines[1:10]:
    print(l)
