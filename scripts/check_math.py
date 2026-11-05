import re

with open('paper_local/latex/main.tex', 'r', encoding='utf-8') as f:
    text = f.read()

display_eqs = re.findall(r'\\begin\{equation\}(.*?)\\end\{equation\}', text, re.DOTALL)
print(f'Display equations: {len(display_eqs)}')

align_eqs = re.findall(r'\\begin\{align\*?\}(.*?)\\end\{align\*?\}', text, re.DOTALL)
print(f'Align equations: {len(align_eqs)}')

# Check balanced parentheses and brackets in equations
for i, eq in enumerate(display_eqs):
    # filter out commands like \left( \right) or comments
    clean_eq = re.sub(r'\\(left|right|big|Big|bigg|Bigg)', '', eq)
    clean_eq = re.sub(r'\\begin\{.*?\}|\\end\{.*?\}', '', clean_eq)
    # count
    parens = clean_eq.count('(') - clean_eq.count(')')
    brackets = clean_eq.count('[') - clean_eq.count(']')
    braces = clean_eq.count('{') - clean_eq.count('}')
    if parens != 0 or brackets != 0 or braces != 0:
        print(f'Equation {i+1} discrepancy: parens={parens}, brackets={brackets}, braces={braces}')
        print(eq)

for i, eq in enumerate(align_eqs):
    clean_eq = re.sub(r'\\(left|right|big|Big|bigg|Bigg)', '', eq)
    parens = clean_eq.count('(') - clean_eq.count(')')
    brackets = clean_eq.count('[') - clean_eq.count(']')
    braces = clean_eq.count('{') - clean_eq.count('}')
    if parens != 0 or brackets != 0 or braces != 0:
        print(f'Align {i+1} discrepancy: parens={parens}, brackets={brackets}, braces={braces}')
        print(eq)

print("Math check complete.")
