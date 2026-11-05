import re
import json
import os
import sys

def audit():
    latex_path = 'paper_local/latex/main.tex'
    bib_path = 'paper_local/latex/references.bib'
    latex_dir = 'paper_local/latex'

    with open(latex_path, 'r', encoding='utf-8') as f:
        latex = f.read()

    print("=" * 70)
    print("1. LABELS AND REFERENCES AUDIT")
    print("=" * 70)
    labels = set(re.findall(r'\\label\{([^}]+)\}', latex))
    refs = set(re.findall(r'\\ref\{([^}]+)\}', latex))
    missing_refs = refs - labels
    print(f"Total labels defined: {len(labels)}")
    print(f"Total references used: {len(refs)}")
    if missing_refs:
        print(f"CRITICAL: Missing labels (referenced but not defined): {missing_refs}")
    else:
        print("PASS: Zero missing labels!")

    print("\n" + "=" * 70)
    print("2. CITATIONS AND BIBLIOGRAPHY AUDIT")
    print("=" * 70)
    with open(bib_path, 'r', encoding='utf-8') as f:
        bib = f.read()
    bib_keys = set(re.findall(r'@[A-Za-z]+\s*\{\s*([^,]+),', bib))
    cites = set()
    for m in re.finditer(r'\\cite\{([^}]+)\}', latex):
        for k in m.group(1).split(','):
            cites.add(k.strip())
    missing_cites = cites - bib_keys
    print(f"Total bib entries in .bib: {len(bib_keys)}")
    print(f"Total cited keys in .tex: {len(cites)}")
    if missing_cites:
        print(f"CRITICAL: Undefined citations in .tex: {missing_cites}")
    else:
        print("PASS: All citations present in .bib!")
    unused_cites = bib_keys - cites
    print(f"Bib entries not cited in text ({len(unused_cites)}): {sorted(list(unused_cites))}")

    print("\n" + "=" * 70)
    print("3. GRAPHICS AND FIGURE FILES AUDIT")
    print("=" * 70)
    pattern = r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}'
    fig_includes = re.findall(pattern, latex)
    print(f"Total includegraphics calls: {len(fig_includes)}")
    for fig in fig_includes:
        # Check in latex_dir with and without extensions
        base = os.path.join(latex_dir, fig)
        exists = os.path.exists(base) or os.path.exists(base + '.pdf') or os.path.exists(base + '.png')
        status = "EXISTS" if exists else "MISSING!"
        print(f"  {fig:35s} -> {status}")

    print("\n" + "=" * 70)
    print("4. FIGURE NUMBERING & IN-TEXT REFERENCE ORDER AUDIT")
    print("=" * 70)
    # Find all figure environments and their labels
    fig_envs = re.findall(r'\\begin\{figure\*?\}.*?\\caption\{([^}]+)\}.*?\\label\{([^}]+)\}.*?\\end\{figure\*?\}', latex, re.DOTALL)
    if not fig_envs:
        # try label before caption
        fig_envs = re.findall(r'\\begin\{figure\*?\}.*?\\label\{([^}]+)\}.*?\\caption\{([^}]+)\}.*?\\end\{figure\*?\}', latex, re.DOTALL)
    print(f"Figure environments found: {len(fig_envs)}")
    for i, item in enumerate(fig_envs):
        print(f"  Figure {i+1}: {item}")

    print("\n" + "=" * 70)
    print("5. TABLE NUMBERING & LABELS AUDIT")
    print("=" * 70)
    table_labels = re.findall(r'\\begin\{table\*?\}.*?\\label\{([^}]+)\}', latex, re.DOTALL)
    print(f"Table labels found ({len(table_labels)}): {table_labels}")

    print("\n" + "=" * 70)
    print("6. ASCII DOUBLE QUOTES AUDIT (LaTeX style `` '')")
    print("=" * 70)
    # Find lines with ascii double quotes "
    lines = latex.splitlines()
    quote_lines = []
    for line_no, line in enumerate(lines, 1):
        # strip comments
        non_comment = line.split('%')[0]
        if '"' in non_comment:
            quote_lines.append((line_no, line.strip()))
    print(f"Lines with unescaped ASCII double-quotes: {len(quote_lines)}")
    for lno, text in quote_lines[:10]:
        print(f"  Line {lno}: {text[:80]}")

    print("\n" + "=" * 70)
    print("7. THEOREM, LEMMA, DEFINITION CONSISTENCY AUDIT")
    print("=" * 70)
    theorems = re.findall(r'\\begin\{(theorem|lemma|definition|corollary|proposition)\}(\[.*?\])?', latex)
    print(f"Theorems/Lemmas/Defs found ({len(theorems)}): {theorems}")

if __name__ == '__main__':
    audit()
