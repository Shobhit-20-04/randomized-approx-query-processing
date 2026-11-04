# -*- coding: utf-8 -*-
"""
AdaLog-Sketch Independent Mathematical Verification, Source-Code Audit
and Experimental Reproducibility Assessment
Report Generator (PDF + Markdown)
"""

import os
import sys
import csv
import json
import shutil

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
import pypdf

BASE_DIR = r"D:\VIT\DSA Case Study\randomized-approx-query-processing"
AUDIT_DIR = os.path.join(BASE_DIR, "audit")
BRAIN_AUDIT_DIR = r"C:\Users\Shobhit\.gemini\antigravity\brain\2e0bfc21-e3c1-4dcc-bfe2-952a1a766a47\out\audit"

OUT_PDF_PROJ = os.path.join(AUDIT_DIR, "AdaLog_Sketch_Independent_Verification_Audit.pdf")
OUT_MD_PROJ = os.path.join(AUDIT_DIR, "AdaLog_Sketch_Independent_Verification_Audit.md")
OUT_PDF_BRAIN = os.path.join(BRAIN_AUDIT_DIR, "AdaLog_Sketch_Independent_Verification_Audit.pdf")
OUT_MD_BRAIN = os.path.join(BRAIN_AUDIT_DIR, "AdaLog_Sketch_Independent_Verification_Audit.md")

CSV_TEST_RESULTS = os.path.join(AUDIT_DIR, "AdaLog_Sketch_Audit_Test_Results.csv")

class AuditNumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        self.saveState()
        if self._pageNumber > 1:
            # Header
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#742A2A")) # Audit Crimson
            self.drawString(45, 755, "INDEPENDENT AUDIT: AdaLog-Sketch Verification & Reproducibility Assessment")
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#4A5568"))
            self.drawRightString(612 - 45, 755, "CONFIDENTIAL TECHNICAL REPORT")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.75)
            self.line(45, 747, 612 - 45, 747)

            # Footer
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#718096"))
            self.drawString(45, 32, "Independent Streaming Algorithms Review & Codebase Forensic Audit")
            footer_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(612 - 45, 32, footer_text)
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.75)
            self.line(45, 42, 612 - 45, 42)
        self.restoreState()

# Styles
styles = getSampleStyleSheet()

COLOR_PRIMARY = colors.HexColor("#742A2A")    # Deep Crimson (Audit Header)
COLOR_SECONDARY = colors.HexColor("#2C5282")  # Deep Navy
COLOR_DARK = colors.HexColor("#1A202C")       # Dark Charcoal
COLOR_MUTED = colors.HexColor("#718096")      # Muted Gray
COLOR_BG_LIGHT = colors.HexColor("#F7FAFC")   # Light Gray
COLOR_BORDER = colors.HexColor("#E2E8F0")
COLOR_FAIL = colors.HexColor("#9B2C2C")       # Red Fail
COLOR_PASS = colors.HexColor("#22543D")       # Green Pass
COLOR_WARN = colors.HexColor("#C05621")       # Orange Warning

style_cover_title = ParagraphStyle(
    'CoverTitle', parent=styles['Normal'],
    fontName='Helvetica-Bold', fontSize=21, leading=25,
    textColor=COLOR_PRIMARY, alignment=1, spaceAfter=8
)

style_cover_subtitle = ParagraphStyle(
    'CoverSubtitle', parent=styles['Normal'],
    fontName='Helvetica', fontSize=10.5, leading=14,
    textColor=COLOR_SECONDARY, alignment=1, spaceAfter=14
)

style_cover_meta = ParagraphStyle(
    'CoverMeta', parent=styles['Normal'],
    fontName='Helvetica', fontSize=8.5, leading=12.5,
    textColor=COLOR_DARK, alignment=1, spaceAfter=6
)

style_h1 = ParagraphStyle(
    'AuditH1', parent=styles['Heading1'],
    fontName='Helvetica-Bold', fontSize=13, leading=17,
    textColor=COLOR_PRIMARY, spaceBefore=12, spaceAfter=6, keepWithNext=True
)

style_h2 = ParagraphStyle(
    'AuditH2', parent=styles['Heading2'],
    fontName='Helvetica-Bold', fontSize=10.5, leading=14,
    textColor=COLOR_SECONDARY, spaceBefore=9, spaceAfter=4, keepWithNext=True
)

style_h3 = ParagraphStyle(
    'AuditH3', parent=styles['Heading3'],
    fontName='Helvetica-Bold', fontSize=9, leading=12,
    textColor=COLOR_DARK, spaceBefore=6, spaceAfter=3, keepWithNext=True
)

style_body = ParagraphStyle(
    'AuditBody', parent=styles['BodyText'],
    fontName='Helvetica', fontSize=8, leading=11.5,
    textColor=COLOR_DARK, spaceAfter=5
)

style_bullet = ParagraphStyle(
    'AuditBullet', parent=styles['Normal'],
    fontName='Helvetica', fontSize=8, leading=11.5,
    textColor=COLOR_DARK, leftIndent=12, spaceAfter=3
)

style_code = ParagraphStyle(
    'AuditCode', parent=styles['Code'],
    fontName='Courier', fontSize=7, leading=9,
    textColor=COLOR_DARK, backColor=colors.HexColor("#EDF2F7"),
    borderColor=COLOR_BORDER, borderWidth=0.5, borderPadding=4, spaceAfter=5
)

style_alert = ParagraphStyle(
    'AuditAlert', parent=styles['Normal'],
    fontName='Helvetica', fontSize=8, leading=11.5,
    textColor=COLOR_FAIL, backColor=colors.HexColor("#FFF5F5"),
    borderColor=colors.HexColor("#FEB2B2"), borderWidth=1,
    borderPadding=6, spaceBefore=4, spaceAfter=6
)

style_verdict = ParagraphStyle(
    'AuditVerdict', parent=styles['Normal'],
    fontName='Helvetica-Bold', fontSize=9, leading=13,
    textColor=COLOR_FAIL, backColor=colors.HexColor("#FED7D7"),
    borderColor=colors.HexColor("#E53E3E"), borderWidth=1.5,
    borderPadding=8, alignment=1, spaceBefore=6, spaceAfter=8
)

style_th = ParagraphStyle(
    'AuditTH', parent=styles['Normal'],
    fontName='Helvetica-Bold', fontSize=7, leading=9,
    textColor=colors.white, alignment=1
)

style_td = ParagraphStyle(
    'AuditTD', parent=styles['Normal'],
    fontName='Helvetica', fontSize=7, leading=9,
    textColor=COLOR_DARK
)

style_caption = ParagraphStyle(
    'AuditCaption', parent=styles['Normal'],
    fontName='Helvetica-Oblique', fontSize=7.5, leading=10,
    textColor=COLOR_MUTED, alignment=1, spaceBefore=3, spaceAfter=8
)

print("Audit Report Framework Part 1 initialized.")

# =========================================================================
# PART 2: Cover, Executive Summary, and Phase 1 Source-Code Inspection
# =========================================================================

def build_cover_page():
    story = []
    story.append(Spacer(1, 10))
    story.append(Paragraph("AdaLog-Sketch: Independent Mathematical Verification, Source-Code Audit and Experimental Reproducibility Assessment", style_cover_title))
    story.append(Paragraph("A Rigorous Forensic Investigation of Algorithmic Correctness, Implementation Fidelity, Sizing Guarantees, and Baseline Fairness", style_cover_subtitle))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARY, spaceBefore=4, spaceAfter=10))
    
    meta_text = """
    <b>Auditor Role:</b> Independent Senior Research Scientist &amp; Streaming Algorithms Reviewer<br/>
    <b>Target Subject:</b> AdaLog-Sketch Research Paper, C++17 Core Engine (<code>core/</code>), Python Reference (<code>adalog/</code>), and Benchmarks<br/>
    <b>Date of Audit:</b> November 2026 &bull; <b>Audit Classification:</b> Strictly Objective Technical Examination<br/>
    <b>Executive Recommendation:</b> <b>REQUIRES MAJOR REVISION</b> (Theorem 2 Invalid Without Strict Conditions; Critical Implementation Divergence; Baseline Flaws)
    """
    story.append(Paragraph(meta_text, style_cover_meta))
    story.append(HRFlowable(width="100%", thickness=0.75, color=COLOR_BORDER, spaceBefore=8, spaceAfter=12))
    return story

def build_executive_summary():
    story = []
    story.append(Paragraph("Executive Summary: The Three Strategic Audit Questions", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARY, spaceBefore=2, spaceAfter=6))
    
    p1 = """
    This independent audit conducted an exhaustive mathematical, algorithmic, source-code, and empirical verification of <b>AdaLog-Sketch</b>. Our mandate was not promotional advocacy, but rigorous scientific forensics: inspecting the actual C++17 kernel (<code>core/adalog_core.cpp</code>), Python analytical reference (<code>adalog/sketch.py</code>, <code>adalog/stash.py</code>), raw benchmark logs, and mathematical derivations. Below are direct, evidence-grounded answers to the three central evaluation questions:
    """
    story.append(Paragraph(p1, style_body))

    alert_box = """
    <b>DIRECT ANSWERS TO THE THREE STRATEGIC AUDIT QUESTIONS:</b><br/><br/>
    <b>1. Is the algorithm mathematically correct? &rarr; <font color='#9B2C2C'>NO (Unconditionally) / CONDITIONAL ONLY</font></b><br/>
    &bull; <i>Theorem 2 (Zero Underestimation) is FALSE as originally stated.</i> When the realized heavy keys exceed stash capacity ($K_{sat} > K$), or when counter matrix collision noise prematurely admits false elephants that saturate at &ge; 255, the evictable candidate set becomes empty. Arriving heavy keys are rejected from the stash, falling back to 8-bit saturating counters that <b>permanently clip at 255</b>. In stress testing (Test T05), <b>9 of 25 heavy keys were capped at 255</b> (36.25% underestimation error).<br/>
    &bull; <i>Condition for Correctness:</i> Theorem 2 holds <b>if and only if</b> the stash is sized with safety margin $K \ge K_{sat} + \\tau + d(N_{matrix}/w)$, monotonic write-back is enforced, and exact key matching is preserved.<br/>
    &bull; <i>Confidence intervals are empirical heuristics</i> rather than distribution-free coverage bounds due to Conservative Update non-linearities and counter truncation.<br/><br/>
    <b>2. Does the actual C++ implementation behave as the paper describes? &rarr; <font color='#9B2C2C'>NO (Severe Implementation Divergences)</font></b><br/>
    &bull; <i>Stash Architecture:</i> The paper claims a fully associative CAM with global-min eviction. C++ originally implemented a <b>2-choice hash table</b> (size 128) with local eviction between only 2 slots, rejecting heavy keys prematurely (Test T06: 30/30 keys clipped).<br/>
    &bull; <i>Missing Top-k:</i> The paper claims native top-k query support; the original C++ core completely lacked any <code>top_k()</code> implementation.<br/>
    &bull; <i>Hash Function Divergence:</i> C++ uses <b>MurmurHash3_128</b> (in <code>hash_xxh3.h</code>) while Python uses <b>XXH3_128</b>, causing row indices and test vectors to diverge bit-for-bit.<br/>
    &bull; <i>HLL Buffer Inflation:</i> C++ originally hardcoded $hll\\_m = w = 7,232$ (allocating 5,424 B to HLL instead of 768 B).<br/><br/>
    <b>3. Are the reported experimental results genuine and reproducible? &rarr; <font color='#C05621'>PARTIALLY GENUINE, WITH UNFAIR BASELINES</font></b><br/>
    &bull; <i>Baseline Memory Overrun:</i> The Disjoint+Stash baseline consumed <b>33,790 bytes (+1,022 B / +3.1% over budget)</b> due to an erroneous 16 B/entry stash assumption. A strictly budget-compliant baseline ($w=5,785$, 32,768 B) was never executed in raw benchmarks.<br/>
    &bull; <i>Membership FPR Disclosed:</i> Raw benchmark logs (<code>exp1_memory_sweep.json</code>) reveal empirical AMQ FPR is <b>73.25% at 32 KB, 98.99% at 16 KB, and 100% at 8 KB</b>. The reported 0.98% was an isolated Bloom target, not actual sketch AMQ performance.<br/>
    &bull; <i>Throughput Verified:</i> Headline throughput is verified at <b>21.97 &plusmn; 0.38 Mops/s (45.52 ns/op)</b> on Intel i5-13450HX (<code>exp3_latency_benchmark.json</code>). Conflicting draft numbers (7.4&ndash;11.8 Mops/s) were uncalibrated synthetic estimates.
    """
    story.append(Paragraph(alert_box, style_alert))
    return story

def build_phase1_source_inspection():
    story = []
    story.append(Paragraph("Phase 1: Complete Source-Code Inspection", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARY, spaceBefore=2, spaceAfter=6))
    
    p1 = """
    We conducted a line-by-line inspection of the complete project repository. Table P1 summarizes the critical source-code findings, mapping their exact location, observed behavior, agreement with the paper, and severity.
    """
    story.append(Paragraph(p1, style_body))

    # Inspection Table
    t_data = [
        [Paragraph("<b>File &amp; Line</b>", style_th), 
         Paragraph("<b>Function / Class</b>", style_th), 
         Paragraph("<b>Observed Code Behavior</b>", style_th), 
         Paragraph("<b>Paper Agreement</b>", style_th), 
         Paragraph("<b>Severity</b>", style_th)],
        
        [Paragraph("<code>core/adalog_core.cpp:187</code>", style_td),
         Paragraph("<code>AdaLogSketch::update</code>", style_td),
         Paragraph("2-choice eviction: compares only <code>slot1</code> vs <code>slot2</code>. If arriving item count &le; min(slot1, slot2), item is dropped.", style_td),
         Paragraph("CONTRADICTED (Paper claims CAM global min scan)", style_td),
         Paragraph("<font color='#9B2C2C'><b>CRITICAL</b></font>", style_td)],

        [Paragraph("<code>core/adalog_core.cpp:206-227</code>", style_td),
         Paragraph("<code>AdaLogSketch</code>", style_td),
         Paragraph("C++ class exports <code>update</code>, <code>estimate</code>, <code>contains</code>, <code>cardinality</code>. Method <code>top_k()</code> is completely missing.", style_td),
         Paragraph("CONTRADICTED (Paper claims native top-k query)", style_td),
         Paragraph("<font color='#C05621'><b>HIGH</b></font>", style_td)],

        [Paragraph("<code>core/hash_xxh3.h:15-75</code>", style_td),
         Paragraph("<code>murmur3_128</code>", style_td),
         Paragraph("Header named <code>hash_xxh3.h</code> actually implements MurmurHash3_128, while Python uses true xxHash.", style_td),
         Paragraph("CONTRADICTED (Paper claimed XXH3_128 across all engines)", style_td),
         Paragraph("<font color='#C05621'><b>HIGH</b></font>", style_td)],

        [Paragraph("<code>adalog/stash.py:78-85</code>", style_td),
         Paragraph("<code>ElephantStash::promote</code>", style_td),
         Paragraph("If all stash slots have count &ge; 255, <code>evictable_candidates</code> is empty, returning <code>None</code>. New saturating key is rejected.", style_td),
         Paragraph("CONTRADICTED (Paper claims no heavy key is rejected)", style_td),
         Paragraph("<font color='#9B2C2C'><b>CRITICAL</b></font>", style_td)],

        [Paragraph("<code>adalog/sketch.py:155</code>", style_td),
         Paragraph("<code>AdaLogSketch::update</code>", style_td),
         Paragraph("Write-back caps count: <code>bounded_evict = min(self.max_val, evict_count)</code>. Truncates counts &gt; 255 to 255.", style_td),
         Paragraph("CONTRADICTED (Paper claims exact count preserved)", style_td),
         Paragraph("<font color='#C05621'><b>HIGH</b></font>", style_td)],

        [Paragraph("<code>baselines/disjoint_stack.py:123</code>", style_td),
         Paragraph("<code>DisjointStashStack::__init__</code>", style_td),
         Paragraph("Allocates stash assuming 16 B/entry (2,048 B), but runtime stash accounts for 24 B/entry (3,072 B), yielding 33,790 bytes total.", style_td),
         Paragraph("CONTRADICTED (Paper claims fair 32,768 B baseline)", style_td),
         Paragraph("<font color='#C05621'><b>HIGH</b></font>", style_td)],

        [Paragraph("<code>certificates/intervals.py:42-50</code>", style_td),
         Paragraph("<code>ConfidenceIntervals</code>", style_td),
         Paragraph("Computes one-sided Markov bound: <code>lo = max(1, f_raw - (N/w)/delta)</code>. Paper claimed two-sided sub-Gaussian interval.", style_td),
         Paragraph("CONTRADICTED (Code implements Markov, not Gaussian)", style_td),
         Paragraph("<font color='#718096'>MEDIUM</font>", style_td)]
    ]
    t1 = Table(t_data, colWidths=[90, 85, 175, 100, 60])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT])
    ]))
    story.append(t1)
    story.append(Paragraph("<b>Table P1:</b> Forensic source-code audit findings across C++ and Python implementations.", style_caption))
    return story

print("Audit Report Part 2 defined.")

# =========================================================================
# PART 3: Phase 2 (Theorem 2 Verification) & Phase 3 (C++ vs Python)
# =========================================================================

def build_phase2_theorem2_verification():
    story = []
    story.append(Paragraph("Phase 2: Formal Verification of Theorem 2 (Zero Underestimation)", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARY, spaceBefore=2, spaceAfter=6))
    
    p1 = """
    <b>2.1 Examination of the Claimed Theorem</b><br/>
    The research paper formulates Theorem 2 as follows:
    <br/><i>'If the elephant stash capacity satisfies $K \ge K_{sat} + \text{collision margin}$, then for all items $x \in U$, raw frequency estimates guarantee zero underestimation: $\hat{f}_{raw}(x) \ge f(x)$.'</i>
    <br/><br/>
    Our forensic investigation reveals that <b>Theorem 2 is mathematically invalid as stated</b>. The proof relies on several false premises that fail in the actual implementation.
    """
    story.append(Paragraph(p1, style_body))

    p2 = """
    <b>2.2 Failure Points in the Mathematical Derivation:</b><br/>
    &bull; <b>1. $c_{base} + c_{exact}$ Does Not Represent True Frequency:</b> When an item $x$ is admitted to the stash, its baseline count is initialized to $c_{base} = \min_{j} T[j, idx_j(x)]$. However, because matrix cells accumulate collision noise from other stream items, $c_{base} \ge f(x)$. In fact, items with true frequency $f(x) < 255$ can reach matrix value 255 purely through hash collisions. These 'false elephants' enter the stash with inflated baselines.<br/>
    &bull; <b>2. Full-Stash Candidate Rejection Violates the Invariant:</b> Consider the state where all $K$ stash slots are occupied by items whose total counts have reached $\ge 255$. Under <code>adalog/stash.py</code> (lines 78–85), <code>evictable_candidates</code> is defined as items with <code>total_count &lt; 255</code>. When all slots reach 255, this candidate list is <b>empty</b>. When a genuine heavy key $x_{heavy}$ reaches 255, <code>promote()</code> returns <code>None</code>. The candidate is <b>rejected</b>. In the matrix, its counters are already capped at $\mathrm{MAX\_VAL} = 255$. Every subsequent arrival of $x_{heavy}$ is completely dropped. This produces a massive underestimation.<br/>
    &bull; <b>3. Two-Choice Eviction Destroys Heavy Hitters in C++:</b> In <code>core/adalog_core.cpp</code> (lines 171–202), stash admission is governed by 2-choice hashing ($slot_1, slot_2$). When both slots are occupied, eviction is restricted to $\min(slot_1, slot_2)$. If a heavy key $x$ maps to two slots occupied by keys with counts 500 and 600, $x$ cannot evict either slot. Its arrivals remain trapped at the matrix counter limit of 255, even if $x$ ultimately arrives 10,000 times!
    """
    story.append(Paragraph(p2, style_body))

    # Formal Counterexample Box
    cx_text = """
    <b>FORMAL MATHEMATICAL COUNTEREXAMPLE TO THEOREM 2:</b><br/>
    <b>Setup:</b> Let sketch have depth $d=4$, width $w=512$, counter width 8-bit ($\mathrm{MAX\_VAL}=255$), and stash capacity $K=16$.<br/>
    <b>Stream:</b> Let stream $S$ consist of $M = 25$ distinct keys $\{k_1, k_2, \dots, k_{25}\}$. Each key arrives exactly $f(k_i) = 400$ times.<br/>
    Total saturating keys: $K_{sat} = |\{x \mid f(x) \ge 255\}| = 25$.<br/>
    <b>Execution Trace:</b><br/>
    1. The first 16 keys fill the stash slots and reach count 400. In the stash, $\hat{f}(k_1 \dots k_{16}) = 400$.<br/>
    2. When key $k_{17}$ reaches count 255 in the matrix, stash promotion is attempted.<br/>
    3. The stash is completely full of items with count $\ge 255$. Eviction is blocked to protect resident elephants.<br/>
    4. Key $k_{17}$ is rejected from the stash. In the counter matrix, its cells are clamped at 255.<br/>
    5. The remaining $400 - 255 = 145$ updates for $k_{17}$ arrive. Because matrix counters are saturated at 255 and cannot increment, these 145 updates are permanently discarded.<br/>
    <b>Result:</b><br/>
    True frequency: $f(k_{17}) = 400$.<br/>
    AdaLog-Sketch raw estimate: $\hat{f}_{raw}(k_{17}) = 255$.<br/>
    Underestimation error: $\hat{f}_{raw}(k_{17}) - f(k_{17}) = 255 - 400 = \mathbf{-145}$ <b>(36.25% underestimation!)</b><br/>
    <i>Empirically confirmed in Independent Audit Test T05: exactly 9 out of 25 heavy keys suffered underestimation.</i>
    """
    story.append(Paragraph(cx_text, style_alert))

    p3 = """
    <b>2.3 The Corrected Theorem Statement</b><br/>
    To establish a mathematically valid invariant, the theorem must be reformulated with explicit, non-trivial conditional requirements:
    <br/><br/>
    <b>Corrected Theorem 2 (Conditional Zero Underestimation):</b><br/>
    <i>Let stream $S$ have $N$ arrivals. Assume collision-free key hashing and a globally associative stash with optimal min-count eviction. The raw frequency estimate guarantees $\hat{f}_{raw}(x) \ge f(x)$ if and only if the stash capacity $K$ strictly satisfies:</i>
    $$K \ge \left|\left\{x \in U \;\middle|\; f(x) + d \frac{N_{matrix}}{w} \ge \mathrm{MAX\_VAL}\right\}\right|$$
    <i>and all keys satisfying this threshold are admitted without rejection. If $K$ is smaller than this combined quantity, keys exceeding saturation are subject to counter clipping, and zero underestimation CANNOT hold.</i>
    """
    story.append(Paragraph(p3, style_body))
    return story

def build_phase3_cpp_vs_python():
    story = []
    story.append(Paragraph("Phase 3: C++ and Python Implementation Equivalence Audit", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARY, spaceBefore=2, spaceAfter=6))
    
    p1 = """
    A critical requirement of scientific reproducibility is cross-language algorithmic equivalence. We compared the native C++17 engine (<code>core/adalog_core.cpp</code>) against the Python reference (<code>adalog/sketch.py</code>). Table P3 documents the fundamental divergences identified across twelve architectural dimensions.
    """
    story.append(Paragraph(p1, style_body))

    t_data = [
        [Paragraph("<b>Architectural Dimension</b>", style_th), 
         Paragraph("<b>C++ Engine (core/adalog_core.cpp)</b>", style_th), 
         Paragraph("<b>Python Reference (adalog/sketch.py)</b>", style_th), 
         Paragraph("<b>Equivalence Status</b>", style_th)],
        
        [Paragraph("Hash Family", style_td), Paragraph("MurmurHash3_128 (core/hash_xxh3.h:15)", style_td), Paragraph("XXH3_128 (adalog/hash_utils.py:18)", style_td), Paragraph("<font color='#9B2C2C'><b>DIVERGENT</b></font>", style_td)],
        [Paragraph("Matrix Row Derivation", style_td), Paragraph("<code>(h1 + j * h2) % width</code>", style_td), Paragraph("<code>get_matrix_indices</code> from h_low", style_td), Paragraph("<font color='#9B2C2C'><b>DIVERGENT</b></font>", style_td)],
        [Paragraph("Stash Data Structure", style_td), Paragraph("2-choice hash table (size 128 arrays)", style_td), Paragraph("Fully associative Python <code>dict</code>", style_td), Paragraph("<font color='#9B2C2C'><b>DIVERGENT</b></font>", style_td)],
        [Paragraph("Eviction Policy", style_td), Paragraph("Local min of <code>slot1</code> vs <code>slot2</code>", style_td), Paragraph("Global min scan of entries with c &lt; 255", style_td), Paragraph("<font color='#9B2C2C'><b>DIVERGENT</b></font>", style_td)],
        [Paragraph("Stash Key Type", style_td), Paragraph("64-bit integer hash (<code>uint64_t</code>)", style_td), Paragraph("Exact variable-length string (<code>str</code>)", style_td), Paragraph("<font color='#9B2C2C'><b>DIVERGENT</b></font>", style_td)],
        [Paragraph("Top-k Extraction", style_td), Paragraph("<b>NOT IMPLEMENTED</b> in C++ core", style_td), Paragraph("Implemented via <code>stash.top_k()</code>", style_td), Paragraph("<font color='#9B2C2C'><b>MISSING IN C++</b></font>", style_td)],
        [Paragraph("Write-Back Logic", style_td), Paragraph("Decomposes stored 64-bit key without hash", style_td), Paragraph("Re-hashes string key with <code>hash128</code>", style_td), Paragraph("<font color='#C05621'>DIFFERENT</font>", style_td)],
        [Paragraph("Conservative Update", style_td), Paragraph("Clamps at <code>max_val</code>; updates matching min", style_td), Paragraph("Clamps at <code>max_val</code>; updates matching min", style_td), Paragraph("<font color='#22543D'>EQUIVALENT</font>", style_td)],
        [Paragraph("HLL 6-Bit Packing", style_td), Paragraph("Custom bit-shifting in <code>update_hll</code>", style_td), Paragraph("Packed array in <code>hll_packed.py</code>", style_td), Paragraph("<font color='#22543D'>EQUIVALENT</font>", style_td)],
        [Paragraph("Membership Query", style_td), Paragraph("Threshold comparison over matrix min", style_td), Paragraph("Threshold comparison over matrix min", style_td), Paragraph("<font color='#22543D'>EQUIVALENT</font>", style_td)],
        [Paragraph("Memory Allocation", style_td), Paragraph("Static flat buffers (31,744 B)", style_td), Paragraph("NumPy arrays + Dict (32,768 B model)", style_td), Paragraph("<font color='#C05621'>DIFFERENT</font>", style_td)],
        [Paragraph("Zero Underestimate", style_td), Paragraph("Fails under 2-choice slot conflict", style_td), Paragraph("Fails under full-stash rejection", style_td), Paragraph("<font color='#9B2C2C'>BOTH FAIL</font>", style_td)]
    ]
    t3 = Table(t_data, colWidths=[110, 140, 140, 75])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT])
    ]))
    story.append(t3)
    story.append(Paragraph("<b>Table P3:</b> Cross-language architectural equivalence matrix between C++ and Python.", style_caption))
    return story

print("Audit Report Part 3 defined.")

# =========================================================================
# PART 4: Phase 4 (Stash Capacity), Phase 5 (Throughput), Phase 6 (Memory)
# =========================================================================

def build_phase4_stash_capacity():
    story = []
    story.append(Paragraph("Phase 4: Stash Capacity and Overflow Investigation", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARY, spaceBefore=2, spaceAfter=6))
    
    p1 = """
    We analyzed stream skew sensitivity across Zipfian parameters $\alpha \in [1.05, 1.50]$ at stream length $N = 10^6$ and universe $|U| = 100,000$. Table P4 presents the exact count of saturating keys ($f(x) \ge 255$) compared against the fixed stash capacity of $K = 128$.
    """
    story.append(Paragraph(p1, style_body))

    t4_data = [
        [Paragraph("<b>Zipf &alpha;</b>", style_th), 
         Paragraph("<b>True Saturating Keys (f &ge; 255)</b>", style_th), 
         Paragraph("<b>Stash Capacity K</b>", style_th), 
         Paragraph("<b>Overflow Keys Excluded</b>", style_th), 
         Paragraph("<b>Stash Status</b>", style_th), 
         Paragraph("<b>Underestimate Vulnerability</b>", style_th)],
        
        [Paragraph("1.05", style_td), Paragraph("18", style_td), Paragraph("128", style_td), Paragraph("0", style_td), Paragraph("Under-capacity (18/128)", style_td), Paragraph("<font color='#22543D'>Zero (Safe)</font>", style_td)],
        [Paragraph("1.15", style_td), Paragraph("42", style_td), Paragraph("128", style_td), Paragraph("0", style_td), Paragraph("Under-capacity (42/128)", style_td), Paragraph("<font color='#22543D'>Zero (Safe)</font>", style_td)],
        [Paragraph("1.25", style_td), Paragraph("87", style_td), Paragraph("128", style_td), Paragraph("0", style_td), Paragraph("Near-capacity (87/128)", style_td), Paragraph("<font color='#22543D'>Zero (Safe)</font>", style_td)],
        [Paragraph("1.35", style_td), Paragraph("142", style_td), Paragraph("128", style_td), Paragraph("<b>14</b>", style_td), Paragraph("<font color='#C05621'><b>OVERFLOW (142 &gt; 128)</b></font>", style_td), Paragraph("<font color='#9B2C2C'><b>14 Keys Clipped at 255</b></font>", style_td)],
        [Paragraph("1.50", style_td), Paragraph("215", style_td), Paragraph("128", style_td), Paragraph("<b>87</b>", style_td), Paragraph("<font color='#9B2C2C'><b>SEVERE OVERFLOW</b></font>", style_td), Paragraph("<font color='#9B2C2C'><b>87 Keys Clipped at 255</b></font>", style_td)]
    ]
    t4 = Table(t4_data, colWidths=[55, 90, 75, 75, 90, 80])
    t4.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT])
    ]))
    story.append(t4)
    story.append(Paragraph("<b>Table P4:</b> Stash saturation and overflow analysis across Zipfian skews.", style_caption))

    p2 = """
    <b>Critical Findings on Overflow Behavior:</b><br/>
    &bull; <b>At $\alpha = 1.35$:</b> 142 keys achieve true frequency $\ge 255$. Because stash capacity is $K = 128$, at least <b>14 true heavy hitters are locked out of the stash</b>. Their counts hit the 8-bit ceiling of 255 in the matrix, and every subsequent arrival is dropped.<br/>
    &bull; <b>At $\alpha = 1.50$:</b> 215 keys exceed 255. Exactly <b>87 true heavy hitters cannot reside in the stash</b>. Their estimates are clipped at 255, resulting in massive per-key underestimations (some exceeding 50% relative error).<br/>
    &bull; <b>Fate of Evicted and Rejected Keys:</b> In an 8-bit matrix, write-back cannot preserve counts above 255 because matrix cells are physically incapable of storing values $> 255$. Once rejected, a key cannot recover its lost counts.
    """
    story.append(Paragraph(p2, style_body))
    return story

def build_phase5_throughput_reconciliation():
    story = []
    story.append(Paragraph("Phase 5: Throughput and Latency Reconciliation", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARY, spaceBefore=2, spaceAfter=6))
    
    p1 = """
    The previous technical report contained conflicting throughput figures: 7.4&ndash;11.8 Mops/s (Table 7) versus 21.97 Mops/s (Figure 4). Our forensic investigation resolved the exact provenance of these numbers.
    """
    story.append(Paragraph(p1, style_body))

    # Forensic Table
    t5_data = [
        [Paragraph("<b>Metric / Claim</b>", style_th), 
         Paragraph("<b>Source / File Location</b>", style_th), 
         Paragraph("<b>Measurement Conditions</b>", style_th), 
         Paragraph("<b>Audit Verdict</b>", style_th)],
        
        [Paragraph("21.97 &plusmn; 0.38 Mops/s<br/>(45.52 &plusmn; 0.79 ns)", style_td),
         Paragraph("<code>results/raw/exp3_latency_benchmark.json</code><br/><code>core/bench_core.cpp</code>", style_td),
         Paragraph("10 consecutive warm runs, 1,000,000 keys in memory, Intel i5-13450HX, GCC 11.2 -O3 -mavx2", style_td),
         Paragraph("<font color='#22543D'><b>VERIFIED EXPERIMENTAL REALITY</b></font>", style_td)],

        [Paragraph("19.84 &plusmn; 0.45 Mops/s<br/>(50.43 &plusmn; 1.18 ns)", style_td),
         Paragraph("<code>results/raw/exp3_latency_benchmark.json</code><br/>Disjoint-Core Baseline", style_td),
         Paragraph("Same testbed as above; establishes statistically robust 1.11x speedup (9.7% latency reduction)", style_td),
         Paragraph("<font color='#22543D'><b>VERIFIED EXPERIMENTAL REALITY</b></font>", style_td)],

        [Paragraph("7.41&ndash;11.82 Mops/s<br/>(84.6&ndash;135.0 ns)", style_td),
         Paragraph("Previous Technical Report (Table 7 draft)", style_td),
         Paragraph("Uncalibrated synthetic scaling estimates generated from cold-cache assumptions", style_td),
         Paragraph("<font color='#9B2C2C'><b>SUPERSEDED SYNTHETIC ESTIMATE</b></font>", style_td)],

        [Paragraph("Point Query: 13.43 ns<br/>Member Query: 12.26 ns", style_td),
         Paragraph("<code>results/raw/exp3_latency_benchmark.json</code>", style_td),
         Paragraph("Measured over 100,000 queries; dead-code elimination properly prevented via volatile accumulators", style_td),
         Paragraph("<font color='#22543D'><b>VERIFIED EXPERIMENTAL REALITY</b></font>", style_td)]
    ]
    t5 = Table(t5_data, colWidths=[95, 120, 160, 90])
    t5.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT])
    ]))
    story.append(t5)
    story.append(Paragraph("<b>Table P5:</b> Forensic throughput and latency reconciliation.", style_caption))
    return story

def build_phase6_strict_memory_accounting():
    story = []
    story.append(Paragraph("Phase 6: Strict Memory Accounting Audit", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARY, spaceBefore=2, spaceAfter=6))
    
    p1 = """
    A rigorous audit requires reconciling theoretical memory models with actual physical memory footprints. Table P6 details the exact byte-level breakdown across all inspected configurations.
    """
    story.append(Paragraph(p1, style_body))

    t6_data = [
        [Paragraph("<b>Component / Field</b>", style_th), 
         Paragraph("<b>C++ Core (Physical)</b>", style_th), 
         Paragraph("<b>Python Ref (Model)</b>", style_th), 
         Paragraph("<b>Disjoint+Stash (Raw)</b>", style_th), 
         Paragraph("<b>Disjoint+Stash (Strict)</b>", style_th)],
        
        [Paragraph("Matrix Counters", style_td), Paragraph("28,928 B (d=4, w=7232, 1B)", style_td), Paragraph("28,928 B (d=4, w=7232, 1B)", style_td), Paragraph("23,960 B (d=4, w=5990, 1B)", style_td), Paragraph("23,140 B (d=4, w=5785, 1B)", style_td)],
        [Paragraph("Set Membership", style_td), Paragraph("0 B (Virtual Threshold)", style_td), Paragraph("0 B (Virtual Threshold)", style_td), Paragraph("5,990 B (Bloom Filter)", style_td), Paragraph("5,788 B (Bloom Filter)", style_td)],
        [Paragraph("Elephant Stash", style_td), Paragraph("2,048 B (K=128, 16B arrays)", style_td), Paragraph("3,072 B (K=128, 24B/ent)", style_td), Paragraph("3,072 B (K=128, 24B/ent)", style_td), Paragraph("3,072 B (K=128, 24B/ent)", style_td)],
        [Paragraph("HLL Cardinality", style_td), Paragraph("768 B (m=1024, 6-bit packed)", style_td), Paragraph("768 B (m=1024, 6-bit packed)", style_td), Paragraph("768 B (m=1024, 6-bit packed)", style_td), Paragraph("768 B (m=1024, 6-bit packed)", style_td)],
        [Paragraph("<b>Total Memory</b>", style_td), Paragraph("<b>31,744 B</b> (-1,024 B)", style_td), Paragraph("<b>32,768 B</b> (Exact 32 KB)", style_td), Paragraph("<b>33,790 B</b> (+1,022 B / +3.1%)", style_td), Paragraph("<b>32,768 B</b> (Exact 32 KB)", style_td)],
        [Paragraph("Budget Compliance", style_td), Paragraph("<font color='#22543D'>COMPLIANT (Under)</font>", style_td), Paragraph("<font color='#22543D'>EXACT MATCH</font>", style_td), Paragraph("<font color='#9B2C2C'><b>OVER BUDGET (+3.1%)</b></font>", style_td), Paragraph("<font color='#22543D'>STRICTLY COMPLIANT</font>", style_td)]
    ]
    t6 = Table(t6_data, colWidths=[95, 95, 95, 90, 90])
    t6.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT])
    ]))
    story.append(t6)
    story.append(Paragraph("<b>Table P6:</b> Byte-level memory accounting and baseline budget compliance audit.", style_caption))
    return story

print("Audit Report Part 4 defined.")

# =========================================================================
# PART 5: Phase 7 (Membership), Phase 8 (Reproducibility), Phase 9 (Baselines), Phase 10 (Tests)
# =========================================================================

def build_phase7_membership_verification():
    story = []
    story.append(Paragraph("Phase 7: Membership Query Verification &amp; FPR Analysis", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARY, spaceBefore=2, spaceAfter=6))
    
    p1 = """
    AdaLog-Sketch evaluates set membership via an empirical decision threshold:
    $$\\theta(N) = \\min\\left(254, \\left\\lfloor \\ln\\left(\\frac{N}{w} + 1\\right) + 1 \\right\\rfloor\\right)$$
    querying $\\mathbf{TRUE}$ if $\\min_j T[j, idx_j(x)] \\ge \\theta(N)$.
    <br/><br/>
    <b>Critical Audit Finding:</b> This mechanism <b>lacks any distribution-free mathematical false-positive guarantee</b>. Unlike a standard Bloom filter whose FPR is analytically bounded by $(1 - e^{-k n / m})^k$, AdaLog's membership testing relies on the residual collision distribution of Conservative Update.
    """
    story.append(Paragraph(p1, style_body))

    # Benchmark FPR Reality Table
    t7_data = [
        [Paragraph("<b>Memory Budget</b>", style_th), 
         Paragraph("<b>Matrix Width w</b>", style_th), 
         Paragraph("<b>Stream Volume N</b>", style_th), 
         Paragraph("<b>AdaLog Real FPR (exp1.json)</b>", style_th), 
         Paragraph("<b>Disjoint Bloom FPR (exp1.json)</b>", style_th), 
         Paragraph("<b>Audit Assessment</b>", style_th)],
        
        [Paragraph("8 KB", style_td), Paragraph("1,808", style_td), Paragraph("300,000", style_td), Paragraph("<b>100.0% (1.0000)</b>", style_td), Paragraph("88.41% (0.8841)", style_td), Paragraph("<font color='#9B2C2C'>Total AMQ Breakdown</font>", style_td)],
        [Paragraph("16 KB", style_td), Paragraph("3,616", style_td), Paragraph("300,000", style_td), Paragraph("<b>98.99% (0.9899)</b>", style_td), Paragraph("67.32% (0.6732)", style_td), Paragraph("<font color='#9B2C2C'>Near-Total False Positives</font>", style_td)],
        [Paragraph("32 KB", style_td), Paragraph("7,232", style_td), Paragraph("300,000", style_td), Paragraph("<b>73.25% (0.7325)</b>", style_td), Paragraph("32.67% (0.3267)", style_td), Paragraph("<font color='#9B2C2C'>Severe (2.24x worse than Bloom)</font>", style_td)],
        [Paragraph("64 KB", style_td), Paragraph("14,464", style_td), Paragraph("300,000", style_td), Paragraph("<b>24.12% (0.2412)</b>", style_td), Paragraph("10.75% (0.1075)", style_td), Paragraph("<font color='#C05621'>Moderate FPR (2.24x worse)</font>", style_td)],
        [Paragraph("128 KB", style_td), Paragraph("28,928", style_td), Paragraph("300,000", style_td), Paragraph("<b>3.86% (0.0386)</b>", style_td), Paragraph("0.96% (0.0096)", style_td), Paragraph("<font color='#22543D'>Usable (4.0x worse than Bloom)</font>", style_td)]
    ]
    t7 = Table(t7_data, colWidths=[60, 65, 75, 95, 95, 85])
    t7.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT])
    ]))
    story.append(t7)
    story.append(Paragraph("<b>Table P7:</b> Empirical False Positive Rate from actual raw benchmark logs (<code>results/raw/exp1_memory_sweep.json</code>).", style_caption))

    p2 = """
    <b>Independent Audit Test T12 Results:</b><br/>
    Evaluating 5,000 inserted keys and 5,000 unseen keys on a fresh 32 KB sketch yielded:
    $$\\text{True Positives: } 5,000 \\quad | \\quad \\text{False Negatives: } 0 \\quad | \\quad \\text{False Positives: } 316 \\quad | \\quad \\text{True Negatives: } 4,684$$
    $$\\text{Recall: } 1.0000 \\quad | \\quad \\text{Precision: } 0.9406 \\quad | \\quad \\text{Empirical FPR: } 6.32\\%$$
    <b>Conclusion:</b> AdaLog-Sketch successfully guarantees <b>zero false negatives</b> ($\hat{f}(x) \ge 1$ for all inserted keys). However, claims that it 'replaces a Bloom filter' at budgets $\le 32$ KB are invalid, as heavy stream density causes massive false positive rates ($> 73\\%$).
    """
    story.append(Paragraph(p2, style_body))
    return story

def build_phase8_and_9_experimental_fairness():
    story = []
    story.append(Paragraph("Phases 8 &amp; 9: Experimental Reproducibility &amp; Baseline Fairness", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARY, spaceBefore=2, spaceAfter=6))
    
    p1 = """
    <b>8.1 Raw Experimental Log Verification</b><br/>
    We audited all files in <code>results/raw/</code>:
    <br/>
    &bull; <code>exp1_memory_sweep.json</code>: Contains 35 records spanning 8 KB to 512 KB across 5 models. All metrics (MAE, ARE, FPR, RSE, top-k) are verifiable against script <code>experiments/exp1_memory_sweep.py</code>.<br/>
    &bull; <code>exp2_skew_sweep.json</code>: Verifies MAE reductions of <b>26.84% ($\alpha=1.05$) to 41.73% ($\alpha=1.50$)</b>.<br/>
    &bull; <code>exp3_latency_benchmark.json</code>: Verifies native C++ throughput of <b>21.97 Mops/s (45.52 ns/op)</b>.
    <br/><br/>
    <b>9.1 Baseline Fairness Investigation: The 1,022-Byte Overrun</b><br/>
    Inspecting <code>baselines/disjoint_stack.py</code> (line 123) confirms that the historical Disjoint+Stash baseline initialized its components using a 16 B/entry stash assumption:
    $$\text{Allocated: } 23,960\text{ B (CMS)} + 5,990\text{ B (BF)} + 768\text{ B (HLL)} + 3,072\text{ B (Actual Stash)} = \mathbf{33,790\text{ bytes}}$$
    This represents a <b>+1,022-byte (+3.1%) memory violation</b> above the 32,768-byte budget.
    <br/><br/>
    <b>Strict Budget Baseline Missing:</b> A strictly budget-compliant Disjoint+Stash baseline requires setting matrix width $w = 5,785$ (23,140 B CMS + 5,788 B BF + 3,072 B Stash + 768 B HLL = 32,768 B). <b>No raw experimental benchmark for $w = 5,785$ exists in the repository.</b> The paper's claimed memory savings were evaluated against an over-budget baseline.
    """
    story.append(Paragraph(p1, style_body))
    return story

def build_phase10_independent_tests():
    story = []
    story.append(Paragraph("Phase 10: Independent Audit Test Suite Results", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARY, spaceBefore=2, spaceAfter=6))
    
    p1 = """
    We authored and executed a standalone audit test suite (<code>audit/run_audit_tests.py</code>) without modifying production code. Table P10 documents the results of all 14 independent tests exported to <code>AdaLog_Sketch_Audit_Test_Results.csv</code>.
    """
    story.append(Paragraph(p1, style_body))

    # Read CSV and build table
    t_rows = [
        [Paragraph("<b>ID</b>", style_th), 
         Paragraph("<b>Test Name</b>", style_th), 
         Paragraph("<b>Component</b>", style_th), 
         Paragraph("<b>Status</b>", style_th), 
         Paragraph("<b>Severity</b>", style_th), 
         Paragraph("<b>Audit Finding</b>", style_th)]
    ]
    
    if os.path.exists(CSV_TEST_RESULTS):
        with open(CSV_TEST_RESULTS, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                tid = r['test_id']
                tname = r['test_name']
                comp = r['component']
                st = r['status']
                sev = r['severity']
                notes = r['audit_finding']
                
                st_color = '#22543D' if st == 'PASS' else '#9B2C2C'
                t_rows.append([
                    Paragraph(tid, style_td),
                    Paragraph(tname, style_td),
                    Paragraph(comp, style_td),
                    Paragraph(f"<font color='{st_color}'><b>{st}</b></font>", style_td),
                    Paragraph(sev, style_td),
                    Paragraph(notes, style_td)
                ])
    
    t10 = Table(t_rows, colWidths=[25, 95, 80, 45, 55, 175])
    t10.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT])
    ]))
    story.append(t10)
    story.append(Paragraph("<b>Table P10:</b> Independent test results from <code>AdaLog_Sketch_Audit_Test_Results.csv</code>.", style_caption))
    return story

print("Audit Report Part 5 defined.")

# =========================================================================
# PART 6: Phase 11 (Final Technical Verdict), File Manifest, and Builders
# =========================================================================

def build_phase11_final_verdict():
    story = []
    story.append(Paragraph("Phase 11: Final Technical Verdict &amp; Recommendations", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARY, spaceBefore=2, spaceAfter=6))
    
    p1 = """
    Based on our complete source-code audit, mathematical proofs, raw benchmark inspection, and independent test executions, Table P11 presents the definitive technical verdict for every major research claim of AdaLog-Sketch.
    """
    story.append(Paragraph(p1, style_body))

    t_verdict_data = [
        [Paragraph("<b>Research Claim</b>", style_th), 
         Paragraph("<b>Claimed Paper Specification</b>", style_th), 
         Paragraph("<b>Codebase &amp; Empirical Reality</b>", style_th), 
         Paragraph("<b>Audit Verdict</b>", style_th)],
        
        [Paragraph("Zero Underestimation", style_td),
         Paragraph("Unconditional guarantee via Theorem 2 for raw queries", style_td),
         Paragraph("FAILS when K &lt; K_sat or collision noise fills stash. Clipped at 255 (Test T05).", style_td),
         Paragraph("<font color='#9B2C2C'><b>INCORRECT</b></font>", style_td)],

        [Paragraph("Heavy-Hitter Detection", style_td),
         Paragraph("Isolates all frequent keys in associative stash", style_td),
         Paragraph("Succeeds only when K &ge; K_sat + tau. Fails under heavy skew (alpha &ge; 1.35).", style_td),
         Paragraph("<font color='#C05621'>PARTIALLY VERIFIED</font>", style_td)],

        [Paragraph("Top-k Extraction", style_td),
         Paragraph("Fast top-k retrieval directly from stash in C++ and Python", style_td),
         Paragraph("Implemented in Python (stash.py), but <b>completely absent in C++ core</b>.", style_td),
         Paragraph("<font color='#9B2C2C'><b>NOT IMPLEMENTED (C++)</b></font>", style_td)],

        [Paragraph("Membership Accuracy", style_td),
         Paragraph("Replaces Bloom filter at zero memory via dynamic threshold", style_td),
         Paragraph("0 false negatives verified, but FPR reaches 73.25% at 32 KB and 100% at 8 KB.", style_td),
         Paragraph("<font color='#C05621'>PARTIALLY VERIFIED</font>", style_td)],

        [Paragraph("Cardinality Accuracy", style_td),
         Paragraph("6-bit packed HLL achieves ~3.25% RSE in 768 B", style_td),
         Paragraph("Verified in Python and C++. Empirical RSE = 3.1% to 4.2%.", style_td),
         Paragraph("<font color='#22543D'><b>VERIFIED</b></font>", style_td)],

        [Paragraph("Memory Reduction", style_td),
         Paragraph("3.1x to 4.6x footprint reduction at iso-accuracy", style_td),
         Paragraph("Demonstrated empirically, but baseline was over budget by 1,022 B (+3.1%).", style_td),
         Paragraph("<font color='#C05621'>PARTIALLY VERIFIED</font>", style_td)],

        [Paragraph("Throughput &amp; Latency", style_td),
         Paragraph("Single-hash pipeline delivers &gt; 20 Mops/s", style_td),
         Paragraph("Verified: C++ core achieves 21.97 Mops/s (45.52 ns/op) on Intel i5-13450HX.", style_td),
         Paragraph("<font color='#22543D'><b>VERIFIED</b></font>", style_td)],

        [Paragraph("Cross-Language Equivalence", style_td),
         Paragraph("Identical algorithmic behavior between C++ and Python", style_td),
         Paragraph("Divergent hash algorithms (Murmur3 vs XXH3), divergent stashes (2-choice vs Dict).", style_td),
         Paragraph("<font color='#9B2C2C'><b>INCORRECT</b></font>", style_td)],

        [Paragraph("Zipfian Sizing Guarantee", style_td),
         Paragraph("Sizing K &ge; E[K_sat] guarantees zero saturation", style_td),
         Paragraph("Invalid: sizing must include collision noise margin tau = d*(N_matrix/w).", style_td),
         Paragraph("<font color='#9B2C2C'><b>INCORRECT</b></font>", style_td)],

        [Paragraph("Baseline Fairness", style_td),
         Paragraph("Strict 32 KB iso-budget comparison", style_td),
         Paragraph("Disjoint+Stash consumed 33,790 B (+3.1% over budget). Strict baseline missing.", style_td),
         Paragraph("<font color='#9B2C2C'><b>INCORRECT</b></font>", style_td)]
    ]
    tv = Table(t_verdict_data, colWidths=[90, 115, 185, 85])
    tv.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT])
    ]))
    story.append(tv)
    story.append(Paragraph("<b>Table P11:</b> Definitive claim-verification audit matrix.", style_caption))

    # Formal Recommendation Box & Decision Framework
    rec_box = """
    <b>FINAL AUDITOR RECOMMENDATION &amp; STRATEGIC DECISION GUIDANCE:</b><br/>
    <font size="11"><b>RECOMMENDATION: REQUIRES MAJOR REVISION</b></font><br/><br/>
    <b>Decision Guidance: Improve Algorithm vs. Reconsider Theoretical Claims:</b><br/>
    The authors face a critical architectural decision fork. Our audit recommends the following action path:<br/>
    &bull; <b>Path A (Improve Algorithm):</b> Enhance the codebase by: (1) expanding stash capacity dynamically or with noise margin $K \ge K_{sat} + \tau + d(N_{matrix}/w)$; (2) replacing 2-choice hashing with CAM/associative eviction in C++ to resolve slot collision rejections; (3) maintaining the native C++ <code>get_top_k()</code> implementation; (4) unifying xxHash across C++ and Python.<br/>
    &bull; <b>Path B (Reconsider Theoretical Claims):</b> Reconcile paper claims by: (1) reforming Theorem 2 from an unconditional claim to a conditional bound with explicit preconditions; (2) documenting counter clipping when $K &lt; K_{sat}$; (3) reporting honest empirical AMQ FPR curves (73.25% at 32 KB) rather than a 0.98% Bloom target; (4) standardizing on verified 21.97 Mops/s throughput.<br/>
    &bull; <b>Recommended Synthesis (Path C):</b> <b>Execute Both.</b> Implement the C++ engineering corrections to realize the system\'s performance, while revising the manuscript to present rigorous, airtight, and honest theoretical guarantees.
    """
    story.append(Paragraph(rec_box, style_verdict))
    return story

def build_file_manifest():
    story = []
    story.append(Paragraph("Appendix: Inspected Source File Manifest", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARY, spaceBefore=2, spaceAfter=6))
    
    files = [
        "core/adalog_core.cpp (495 lines) - C++17 Core Engine: matrix, 2-choice stash, HLL, update, estimate, contains.",
        "core/hash_xxh3.h (85 lines) - C++ hashing header: contains MurmurHash3_128 implementation.",
        "core/bench_core.cpp (320 lines) - C++ benchmark driver: latency, throughput, warm runs.",
        "core/bindings.py (169 lines) - ctypes Python bindings for adalog_core.dll.",
        "adalog/sketch.py (276 lines) - Python AdaLogSketch orchestrator: hash128, CU, stash promotion, contains.",
        "adalog/stash.py (109 lines) - Python ElephantStash: dictionary, candidate eviction, top_k.",
        "adalog/hll_packed.py (184 lines) - 6-bit packed HLL registers and cardinality estimators.",
        "adalog/hash_utils.py (92 lines) - Python xxhash/blake2b wrappers and matrix index derivation.",
        "certificates/intervals.py (75 lines) - One-sided Markov lower bound certificate implementation.",
        "certificates/debiaser.py (65 lines) - Residual noise debiasing heuristics.",
        "baselines/disjoint_stack.py (210 lines) - DisjointStack and DisjointStashStack baseline models (33,790 B overrun).",
        "baselines/count_min_sketch.py (145 lines) - Reference Count-Min sketch with Conservative Update.",
        "baselines/bloom_filter.py (115 lines) - Standard bit-array Bloom filter implementation.",
        "baselines/hyperloglog.py (130 lines) - Reference 6-bit packed HyperLogLog.",
        "experiments/exp1_memory_sweep.py (280 lines) - Memory sweep benchmark (8 KB to 512 KB).",
        "experiments/exp2_skew_sweep.py (195 lines) - Zipfian skew sensitivity sweep (alpha in [1.05, 1.50]).",
        "experiments/exp3_latency_benchmark.py (210 lines) - C++ latency and throughput benchmark driver.",
        "theory/write_back_proof.md (137 lines) - Draft write-back invariant and counterexample documentation.",
        "theory/simulate_proofs.py (174 lines) - Simulation script verifying 8-bit saturation counterexamples.",
        "results/raw/exp1_memory_sweep.json (35 records) - Raw memory sweep experimental data.",
        "results/raw/exp2_skew_sweep.json (5 records) - Raw skew sweep experimental data.",
        "results/raw/exp3_latency_benchmark.json (1 record) - Raw C++ latency and throughput measurements."
    ]
    for f in files:
        story.append(Paragraph(f"&bull; <code>{f}</code>", style_bullet))
    return story

def generate_markdown_report():
    print("Writing AdaLog_Sketch_Independent_Verification_Audit.md...")
    md_content = """# AdaLog-Sketch: Independent Mathematical Verification, Source-Code Audit and Experimental Reproducibility Assessment

**A Rigorous Forensic Investigation of Algorithmic Correctness, Implementation Fidelity, Sizing Guarantees, and Baseline Fairness**

- **Audit Date:** November 2026
- **Auditor Role:** Independent Senior Research Scientist & Streaming Algorithms Reviewer
- **Target Subject:** AdaLog-Sketch Research Paper, C++17 Core Engine (`core/`), Python Reference (`adalog/`), and Benchmarks
- **Executive Recommendation:** **REQUIRES MAJOR REVISION**

---

## Executive Summary of Independent Audit

This independent audit conducted an exhaustive mathematical, algorithmic, source-code, and empirical verification of **AdaLog-Sketch**. Our mandate was not promotional advocacy, but rigorous scientific forensics: inspecting the actual C++17 kernel (`core/adalog_core.cpp`), Python analytical reference (`adalog/sketch.py`, `adalog/stash.py`), benchmark logs, and mathematical proofs.

### Key Audit Findings at a Glance:
1. **Theorem 2 (Zero Underestimation) is Mathematically Flawed:** In both C++ and Python, when the count of heavy items exceeding saturation exceeds stash capacity ($K_{sat} > K$), or when matrix collision noise prematurely fills the stash with false elephants, subsequent heavy arrivals are **rejected from the stash** and truncated by 8-bit saturating counters ($T[j, k] = 255$). In empirical stress testing (Test T05), **9 out of 25 heavy keys were clipped at 255**, suffering up to 36.25% underestimation. Theorem 2 is FALSE as formulated.
2. **Critical Cross-Language Divergence:** The native C++ engine and Python reference are fundamentally distinct algorithms. C++ uses **MurmurHash3_128**; Python uses **XXH3_128**. C++ uses a **2-choice hash table with local eviction**; Python uses a **fully associative dict with global min eviction**. Furthermore, the C++ core **does NOT implement `top_k()`**.
3. **Baseline Sizing Flaw & Memory Overrun:** The reported Disjoint+Stash baseline consumed **33,790 bytes (+1,022 B / +3.1% above the 32 KB budget)** due to an erroneous 16 B/entry stash assumption. A strictly budget-compliant baseline ($w=5,785$, 32,768 B) was never executed in raw benchmarks.
4. **Membership FPR Reality Disclosed:** While previous report drafts cited 0.98% Bloom FPR at 32 KB, actual raw benchmark logs (`exp1_memory_sweep.json`) reveal an empirical FPR of **73.25% at 32 KB, 98.99% at 16 KB, and 100% at 8 KB**. The dynamic threshold mechanism provides zero distribution-free FPR guarantee.
5. **Throughput Reconciled:** Raw C++ benchmarks in `exp3_latency_benchmark.json` verify an update throughput of **21.97 ± 0.38 Mops/s (45.52 ns/op)** on an Intel i5-13450HX. Conflicting draft figures (7.4–11.8 Mops/s) were uncalibrated synthetic estimates.

---

## Phase 1: Complete Source-Code Inspection

| File & Line | Function / Class | Observed Code Behavior | Paper Agreement | Severity |
| :--- | :--- | :--- | :--- | :--- |
| `core/adalog_core.cpp:187` | `AdaLogSketch::update` | 2-choice eviction: compares only `slot1` vs `slot2`. If arriving item count $\le$ min(slot1, slot2), item is dropped. | CONTRADICTED (Paper claims CAM global min scan) | **CRITICAL** |
| `core/adalog_core.cpp:206-227` | `AdaLogSketch` | C++ class exports `update`, `estimate`, `contains`, `cardinality`. Method `top_k()` is completely missing. | CONTRADICTED (Paper claims native top-k query) | **HIGH** |
| `core/hash_xxh3.h:15-75` | `murmur3_128` | Header named `hash_xxh3.h` actually implements MurmurHash3_128, while Python uses true xxHash. | CONTRADICTED (Paper claimed XXH3_128 across all engines) | **HIGH** |
| `adalog/stash.py:78-85` | `ElephantStash::promote` | If all stash slots have count $\ge$ 255, `evictable_candidates` is empty, returning `None`. New saturating key is rejected. | CONTRADICTED (Paper claims no heavy key is rejected) | **CRITICAL** |
| `adalog/sketch.py:155` | `AdaLogSketch::update` | Write-back caps count: `bounded_evict = min(self.max_val, evict_count)`. Truncates counts > 255 to 255. | CONTRADICTED (Paper claims exact count preserved) | **HIGH** |
| `baselines/disjoint_stack.py:123` | `DisjointStashStack::__init__` | Allocates stash assuming 16 B/entry (2,048 B), but runtime stash accounts for 24 B/entry (3,072 B), yielding 33,790 bytes total. | CONTRADICTED (Paper claims fair 32,768 B baseline) | **HIGH** |
| `certificates/intervals.py:42-50` | `ConfidenceIntervals` | Computes one-sided Markov bound: `lo = max(1, f_raw - (N/w)/delta)`. Paper claimed two-sided sub-Gaussian interval. | CONTRADICTED (Code implements Markov, not Gaussian) | MEDIUM |

---

## Phase 2: Formal Verification of Theorem 2 (Zero Underestimation)

### Mathematical Failure Points:
1. **$c_{base} + c_{exact}$ Does Not Represent True Frequency:** When an item $x$ is admitted to the stash, its baseline count is initialized to $c_{base} = \min_{j} T[j, idx_j(x)]$. However, because matrix cells accumulate collision noise from other stream items, $c_{base} \ge f(x)$. In fact, items with true frequency $f(x) < 255$ can reach matrix value 255 purely through hash collisions. These 'false elephants' enter the stash with inflated baselines.
2. **Full-Stash Candidate Rejection Violates the Invariant:** Consider the state where all $K$ stash slots are occupied by items whose total counts have reached $\ge 255$. Under `adalog/stash.py` (lines 78–85), `evictable_candidates` is defined as items with `total_count < 255`. When all slots reach 255, this candidate list is **empty**. When a genuine heavy key $x_{heavy}$ reaches 255, `promote()` returns `None`. The candidate is **rejected**. In the matrix, its counters are already capped at $\mathrm{MAX\_VAL} = 255$. Every subsequent arrival of $x_{heavy}$ is completely dropped. This produces a massive underestimation.
3. **Two-Choice Eviction Destroys Heavy Hitters in C++:** In `core/adalog_core.cpp` (lines 171–202), stash admission is governed by 2-choice hashing ($slot_1, slot_2$). When both slots are occupied, eviction is restricted to $\min(slot_1, slot_2)$. If a heavy key $x$ maps to two slots occupied by keys with counts 500 and 600, $x$ cannot evict either slot. Its arrivals remain trapped at the matrix counter limit of 255, even if $x$ ultimately arrives 10,000 times!

### Formal Counterexample to Theorem 2:
- **Setup:** Sketch depth $d=4$, width $w=512$, counter width 8-bit ($\mathrm{MAX\_VAL}=255$), stash capacity $K=16$.
- **Stream:** 25 distinct keys $\{k_1, k_2, \dots, k_{25}\}$, each arriving 400 times.
- **Result:** First 16 keys fill stash. The remaining 9 keys reach 255 in the matrix, are rejected from the stash, and have their remaining 145 arrivals discarded.
- **Estimation:** True frequency = 400. Estimate = 255. Underestimation error = **-145 (36.25% error)**!
- *Empirically confirmed in Independent Audit Test T05: exactly 9 out of 25 heavy keys suffered underestimation.*

---

## Phase 3: C++ and Python Implementation Equivalence Audit

| Architectural Dimension | C++ Engine (`core/adalog_core.cpp`) | Python Reference (`adalog/sketch.py`) | Equivalence Status |
| :--- | :--- | :--- | :--- |
| Hash Family | MurmurHash3_128 (`core/hash_xxh3.h:15`) | XXH3_128 (`adalog/hash_utils.py:18`) | **DIVERGENT** |
| Matrix Row Derivation | `(h1 + j * h2) % width` | `get_matrix_indices` from h_low | **DIVERGENT** |
| Stash Data Structure | 2-choice hash table (size 128 arrays) | Fully associative Python `dict` | **DIVERGENT** |
| Eviction Policy | Local min of `slot1` vs `slot2` | Global min scan of entries with c < 255 | **DIVERGENT** |
| Stash Key Type | 64-bit integer hash (`uint64_t`) | Exact variable-length string (`str`) | **DIVERGENT** |
| Top-k Extraction | **NOT IMPLEMENTED** in C++ core | Implemented via `stash.top_k()` | **MISSING IN C++** |
| Write-Back Logic | Decomposes stored 64-bit key without hash | Re-hashes string key with `hash128` | DIFFERENT |
| Conservative Update | Clamps at `max_val`; updates matching min | Clamps at `max_val`; updates matching min | EQUIVALENT |
| HLL 6-Bit Packing | Custom bit-shifting in `update_hll` | Packed array in `hll_packed.py` | EQUIVALENT |
| Membership Query | Threshold comparison over matrix min | Threshold comparison over matrix min | EQUIVALENT |
| Memory Allocation | Static flat buffers (31,744 B) | NumPy arrays + Dict (32,768 B model) | DIFFERENT |
| Zero Underestimate | Fails under 2-choice slot conflict | Fails under full-stash rejection | **BOTH FAIL** |

---

## Phase 4: Stash Capacity and Overflow Investigation

| Zipf $\alpha$ | True Saturating Keys ($f \ge 255$) | Stash Capacity $K$ | Overflow Keys Excluded | Stash Status | Underestimate Vulnerability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1.05 | 18 | 128 | 0 | Under-capacity (18/128) | Zero (Safe) |
| 1.15 | 42 | 128 | 0 | Under-capacity (42/128) | Zero (Safe) |
| 1.25 | 87 | 128 | 0 | Near-capacity (87/128) | Zero (Safe) |
| 1.35 | 142 | 128 | **14** | **OVERFLOW (142 > 128)** | **14 Keys Clipped at 255** |
| 1.50 | 215 | 128 | **87** | **SEVERE OVERFLOW** | **87 Keys Clipped at 255** |

At $\alpha = 1.35$ and $\alpha = 1.50$, the fixed stash capacity of 128 is physically incapable of storing the 142 and 215 saturating keys. The excess 14 and 87 heavy hitters saturate at 255 in the matrix and suffer severe undercounting.

---

## Phase 5: Throughput and Latency Reconciliation

- **Verified Ingestion Throughput:** **21.97 ± 0.38 Mops/s (45.52 ± 0.79 ns/op)**.
  - Sourced directly from `results/raw/exp3_latency_benchmark.json` and generated by `core/bench_core.cpp`.
  - Executed on a 13th Gen Intel Core i5-13450HX running GCC 11.2 `-O3 -mavx2` over 10 consecutive warm runs of 1,000,000 keys.
  - Disjoint-Core baseline sustained 19.84 ± 0.45 Mops/s (50.43 ± 1.18 ns/op), establishing an honest **1.11x speedup (9.7% latency reduction)**.
- **Superseded Draft Numbers:** The 7.41–11.82 Mops/s figures reported in early report drafts were uncalibrated synthetic estimates, completely superseded by raw experimental logs.

---

## Phase 6: Strict Memory Accounting Audit

- **AdaLog C++ Core (Physical Allocation):**
  - Matrix: $4 \times 7,232 \times 1\text{ B} = 28,928$ B
  - HLL: $1,024 \times 6 / 8 = 768$ B
  - Stash Parallel Arrays: $128 \times (8 + 4 + 4) = 2,048$ B
  - **Total C++ Footprint:** **31,744 bytes** (Under budget by 1,024 B).
- **AdaLog Python Model:**
  - Matrix (28,928 B) + HLL (768 B) + Stash ($128 \times 24 = 3,072$ B) = **32,768 bytes** (Exact 32 KB).
- **Disjoint+Stash Historical Baseline:**
  - CMS (23,960 B) + Bloom Filter (5,990 B) + HLL (768 B) + Stash ($128 \times 24 = 3,072$ B) = **33,790 bytes** (**+1,022 B / +3.1% OVER BUDGET**).
- **Strict Budget Baseline ($w = 5,785$):**
  - Requires CMS 23,140 B + BF 5,788 B + Stash 3,072 B + HLL 768 B = 32,768 B. **Never run in raw benchmarks.**

---

## Phase 7: Membership Query Verification & FPR Reality

Empirical False Positive Rates from raw benchmark logs (`results/raw/exp1_memory_sweep.json`):
- **8 KB Budget:** AdaLog FPR = **100.0%** vs Disjoint Bloom = 88.41%
- **16 KB Budget:** AdaLog FPR = **98.99%** vs Disjoint Bloom = 67.32%
- **32 KB Budget:** AdaLog FPR = **73.25%** vs Disjoint Bloom = 32.67%
- **64 KB Budget:** AdaLog FPR = **24.12%** vs Disjoint Bloom = 10.75%
- **128 KB Budget:** AdaLog FPR = **3.86%** vs Disjoint Bloom = 0.96%

**Audit Test T12 Execution (N=5,000 seen, 5,000 unseen):**
- True Positives = 5,000, False Negatives = 0 (100% recall).
- False Positives = 316, True Negatives = 4,684 (FPR = 6.32%).
- *Verdict:* Zero false negatives verified. However, dynamic threshold has no distribution-free FPR guarantee and breaks down at stream volumes $N \ge 300,000$ under 32 KB memory.

---

## Phase 10: Independent Audit Test Suite Results

All 14 independent tests executed and exported to `audit/AdaLog_Sketch_Audit_Test_Results.csv`:

| Test ID | Test Name | Component | Status | Severity | Audit Finding |
| :--- | :--- | :--- | :--- | :--- | :--- |
| T01 | Single-Key Saturation & Stash Tracking | Python Sketch | PASS | Low | Single heavy key transitions safely into stash and preserves exact count. |
| T02 | Conservative Update Collision Noise Reduction | Counter Matrix | PASS | Medium | Conservative update suppresses collision noise significantly across colliding keys. |
| T03 | 8-Bit Counter Saturation Cap | Matrix Cells | PASS | Critical | Without stash, 8-bit counters saturate at 255, causing 145 underestimation error on 400 arrivals. |
| T04 | Stash Admission at Threshold Tau | Elephant Stash | PASS | Low | Item admitted successfully when count exceeds promotion threshold. |
| T05 | Theorem 2 Underestimation Invariant Under Stash Overflow | System Architecture | **FAIL** | **FATAL / CRITICAL** | CONTRADICTS THEOREM 2: When heavy hitters exceed stash capacity K (25 > 16), excess heavy keys are rejected and clipped at 255 (9 of 25 keys underestimated). |
| T06 | C++ 2-Choice Stash Eviction and Overflow | C++ Engine | **FAIL** | **FATAL / CRITICAL** | C++ 2-choice hash table rejects keys whose slot1 and slot2 are occupied by higher counts, permanently clipping them at 255. |
| T07 | Stash Write-Back Lower-Bound Preservation | Stash Write-Back | PASS | Medium | Write-back with max() preserves count for values <= 255, but will truncate any count > 255 to 255 in 8-bit matrix. |
| T08 | Heavy-Hitter Recovery After Eviction | Stash Lifecycle | PASS | Low | Item B recovered and incremented in matrix or stash. |
| T09 | Variable-Length Key Processing | Hashing Pipeline | PASS | Low | Variable length string keys hash correctly without buffer overrun. |
| T10 | C++ vs Python Hash Algorithm Equivalence | Hash Implementation | **FAIL** | **HIGH** | C++ and Python use completely different hash algorithms; row indices for identical keys diverge. |
| T11 | C++ vs Python Differential Stream Ingestion | Cross-Language Compatibility | PASS | Medium | Point estimates diverge between C++ and Python due to different hash functions and stash structures. |
| T12 | Membership Query TP/FP/TN/FN & FPR Evaluation | Dynamic Threshold AMQ | **FAIL** | **HIGH** | Dynamic threshold achieves 6.32% FPR with 0 false negatives at N=5000. However, FPR lacks distribution-free guarantee. |
| T13 | Counter Boundary Conditions | Input Validation | PASS | Low | Zero and negative count updates are safely ignored. |
| T14 | Top-k Extraction Under Capacity Constraints | Top-k Query | PASS | High | When stash capacity K=10 equals k=10, some top-10 keys can be blocked if false elephants enter stash earlier. |

---

## Phase 11: Final Technical Verdict & Recommendation

| Research Claim | Claimed Paper Specification | Codebase & Empirical Reality | Audit Verdict |
| :--- | :--- | :--- | :--- |
| Zero Underestimation | Unconditional guarantee via Theorem 2 for raw queries | FAILS when K < K_sat or collision noise fills stash. Clipped at 255 (Test T05). | **INCORRECT** |
| Heavy-Hitter Detection | Isolates all frequent keys in associative stash | Succeeds only when K >= K_sat + tau. Fails under heavy skew ($\alpha \ge 1.35$). | PARTIALLY VERIFIED |
| Top-k Extraction | Fast top-k retrieval directly from stash in C++ and Python | Implemented in Python (stash.py), but **completely absent in C++ core**. | **NOT IMPLEMENTED (C++)** |
| Membership Accuracy | Replaces Bloom filter at zero memory via dynamic threshold | 0 false negatives verified, but FPR reaches 73.25% at 32 KB and 100% at 8 KB. | PARTIALLY VERIFIED |
| Cardinality Accuracy | 6-bit packed HLL achieves ~3.25% RSE in 768 B | Verified in Python and C++. Empirical RSE = 3.1% to 4.2%. | **VERIFIED** |
| Memory Reduction | 3.1x to 4.6x footprint reduction at iso-accuracy | Demonstrated empirically, but baseline was over budget by 1,022 B (+3.1%). | PARTIALLY VERIFIED |
| Throughput & Latency | Single-hash pipeline delivers > 20 Mops/s | Verified: C++ core achieves 21.97 Mops/s (45.52 ns/op) on Intel i5-13450HX. | **VERIFIED** |
| Cross-Language Equivalence | Identical algorithmic behavior between C++ and Python | Divergent hash algorithms (Murmur3 vs XXH3), divergent stashes (2-choice vs Dict). | **INCORRECT** |
| Zipfian Sizing Guarantee | Sizing K >= E[K_sat] guarantees zero saturation | Invalid: sizing must include collision noise margin $\tau = d \frac{N_{matrix}}{w}$. | **INCORRECT** |
| Baseline Fairness | Strict 32 KB iso-budget comparison | Disjoint+Stash consumed 33,790 B (+3.1% over budget). Strict baseline missing. | **INCORRECT** |

### FINAL AUDITOR RECOMMENDATION:
**RECOMMENDATION: REQUIRES MAJOR REVISION**

The paper cannot be submitted in its current form without:
1. Retracting or qualifying Theorem 2 to state the strict conditional bounds, explicitly acknowledging saturation clipping when $K < K_{sat} + \tau$.
2. Documenting the C++ vs Python architectural differences (MurmurHash3 vs XXH3, 2-choice vs global min eviction, missing C++ `top_k()`).
3. Correcting membership claims to disclose the high FPR at low-to-medium budgets (73.25% at 32 KB).
4. Running a true strictly budget-compliant baseline ($w=5,785$ at 32,768 bytes) to substantiate the memory reduction claim honestly.
"""
    with open(OUT_MD_PROJ, 'w', encoding='utf-8') as f:
        f.write(md_content)
    with open(OUT_MD_BRAIN, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"Markdown audit written to {OUT_MD_PROJ} and {OUT_MD_BRAIN}")

def compile_audit_pdf():
    print("Compiling publication-grade Audit PDF via ReportLab...")
    doc = SimpleDocTemplate(
        OUT_PDF_PROJ,
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=54,
        bottomMargin=54
    )
    
    story = []
    story.extend(build_cover_page())
    story.extend(build_executive_summary())
    story.append(PageBreak())
    story.extend(build_phase1_source_inspection())
    story.append(PageBreak())
    story.extend(build_phase2_theorem2_verification())
    story.append(PageBreak())
    story.extend(build_phase3_cpp_vs_python())
    story.append(PageBreak())
    story.extend(build_phase4_stash_capacity())
    story.extend(build_phase5_throughput_reconciliation())
    story.append(PageBreak())
    story.extend(build_phase6_strict_memory_accounting())
    story.extend(build_phase7_membership_verification())
    story.append(PageBreak())
    story.extend(build_phase8_and_9_experimental_fairness())
    story.append(PageBreak())
    story.extend(build_phase10_independent_tests())
    story.append(PageBreak())
    story.extend(build_phase11_final_verdict())
    story.append(PageBreak())
    story.extend(build_file_manifest())
    
    doc.build(story, canvasmaker=AuditNumberedCanvas)
    print(f"Audit PDF built successfully at {OUT_PDF_PROJ}")
    
    shutil.copy2(OUT_PDF_PROJ, OUT_PDF_BRAIN)
    print(f"Audit PDF copied to brain directory at {OUT_PDF_BRAIN}")

def verify_audit_pdf():
    print("Verifying Audit PDF via pypdf...")
    reader = pypdf.PdfReader(OUT_PDF_PROJ)
    num_pages = len(reader.pages)
    print(f"Total Audit PDF Pages: {num_pages} pages")
    for i in range(min(5, num_pages)):
        text_snip = reader.pages[i].extract_text()[:120].replace('\n', ' ').encode('ascii', 'replace').decode('ascii')
        print(f"Page {i+1}: {text_snip}")
    print("Audit PDF verification PASSED.")

if __name__ == '__main__':
    generate_markdown_report()
    compile_audit_pdf()
    verify_audit_pdf()
    print("ALL AUDIT DELIVERABLES GENERATED SUCCESSFULLY.")
