"""
Convert PAPER_DRAFT.md to a properly formatted academic PDF.
Output: Ott_2026_SyntheticPersonalityDrift.pdf
"""
import re, os, textwrap
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Image
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUT = "Ott_2026_SyntheticPersonalityDrift.pdf"
MD  = "PAPER_DRAFT.md"
FIG_DIR = "figures"

# ── Colours ───────────────────────────────────────────────────────────────────
ACCENT   = HexColor("#1a1a2e")
LIGHT    = HexColor("#f5f5f7")
MID_GREY = HexColor("#888888")
RULE     = HexColor("#cccccc")

# ── Styles ────────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    base = kw.pop("base", "Normal")
    s = ParagraphStyle(name, parent=styles[base], **kw)
    return s

TITLE_S   = S("Title",    fontSize=20, leading=26, textColor=ACCENT,
               alignment=TA_CENTER, spaceAfter=6, fontName="Helvetica-Bold")
AUTHOR_S  = S("Author",   fontSize=11, leading=14, textColor=MID_GREY,
               alignment=TA_CENTER, spaceAfter=2)
DATE_S    = S("Date",     fontSize=10, leading=13, textColor=MID_GREY,
               alignment=TA_CENTER, spaceAfter=18)
ABSTRACT_LABEL = S("AbsLabel", fontSize=9, leading=12, textColor=ACCENT,
               fontName="Helvetica-Bold", spaceAfter=2)
ABSTRACT_S = S("Abstract", fontSize=9.5, leading=14, leftIndent=18,
               rightIndent=18, spaceAfter=14, alignment=TA_JUSTIFY)
H1_S      = S("H1",       fontSize=14, leading=18, textColor=ACCENT,
               fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=6)
H2_S      = S("H2s",      fontSize=11, leading=15, textColor=ACCENT,
               fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=4)
H3_S      = S("H3s",      fontSize=10, leading=14, textColor=ACCENT,
               fontName="Helvetica-BoldOblique", spaceBefore=8, spaceAfter=3)
BODY_S    = S("Body",     fontSize=10, leading=15, spaceAfter=6,
               alignment=TA_JUSTIFY)
BULLET_S  = S("Bullet",   fontSize=10, leading=14, leftIndent=16,
               firstLineIndent=-10, spaceAfter=3, alignment=TA_JUSTIFY)
CODE_S    = S("Code",     fontSize=8.5, leading=12, fontName="Courier",
               leftIndent=18, rightIndent=8, spaceAfter=6, textColor=HexColor("#333333"))
CAPTION_S = S("Caption",  fontSize=8.5, leading=12, textColor=MID_GREY,
               alignment=TA_CENTER, spaceAfter=8, fontName="Helvetica-Oblique")
TABLE_HDR = S("TblHdr",   fontSize=8.5, leading=11, fontName="Helvetica-Bold",
               alignment=TA_CENTER)
TABLE_CEL = S("TblCell",  fontSize=8.5, leading=11, alignment=TA_CENTER)
TABLE_CEL_L = S("TblCellL", fontSize=8.5, leading=11, alignment=TA_LEFT)
REF_S     = S("Ref",      fontSize=8.5, leading=12, spaceAfter=3,
               leftIndent=18, firstLineIndent=-18, alignment=TA_JUSTIFY)
FIGCAP_S  = S("FigCap",   fontSize=8.5, leading=12, textColor=MID_GREY,
               spaceAfter=12, fontName="Helvetica-Oblique", alignment=TA_JUSTIFY)


# ── Inline markdown → ReportLab HTML ─────────────────────────────────────────
def inline(text):
    # bold+italic ***
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
    # bold **
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # italic * or _
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
    # inline code `
    text = re.sub(r'`(.+?)`', r'<font name="Courier" size="9">\1</font>', text)
    # em dash
    text = text.replace('—', '—')
    return text


def bullet_text(line):
    line = re.sub(r'^[-*]\s+', '', line)
    return inline(line)


# ── Table parser ──────────────────────────────────────────────────────────────
def parse_table(lines):
    rows = []
    for line in lines:
        if re.match(r'^\|[-| :]+\|$', line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        rows.append(cells)
    if not rows:
        return None
    col_n = max(len(r) for r in rows)
    for r in rows:
        while len(r) < col_n:
            r.append('')
    # Build paragraph cells
    tdata = []
    for i, row in enumerate(rows):
        style = TABLE_HDR if i == 0 else TABLE_CEL_L
        tdata.append([Paragraph(inline(c), style) for c in row])

    col_w = [1.2 * inch] + [(6.5 - 1.2) / max(col_n - 1, 1) * inch] * (col_n - 1)
    t = Table(tdata, colWidths=col_w, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT),
        ('TEXTCOLOR',  (0, 0), (-1, 0), ACCENT),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT]),
        ('GRID', (0, 0), (-1, -1), 0.4, RULE),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


# ── Figure insertion ──────────────────────────────────────────────────────────
FIGURE_MAP = {
    "fig2": "fig2_nge_convergence.png",
    "fig3": "fig3_attractor_pull.png",
    "fig4": "fig4_sentiment_neuroticism.png",
    "fig5": "fig5_spaghetti.png",
}

def figure_block(fig_id, caption):
    path = os.path.join(FIG_DIR, FIGURE_MAP.get(fig_id, ""))
    elems = []
    if os.path.exists(path):
        img = Image(path, width=6.5 * inch, kind='proportional')
        elems.append(img)
    elems.append(Paragraph(caption, FIGCAP_S))
    elems.append(Spacer(1, 6))
    return elems


# ── Main parser ───────────────────────────────────────────────────────────────
def parse_md(text):
    lines = text.split('\n')
    story = []
    i = 0
    in_abstract = False
    in_refs = False
    in_fig_captions = False
    skip_yaml = False

    while i < len(lines):
        line = lines[i]

        # Skip title block (already rendered via header)
        if line.startswith('# ') and not line.startswith('## '):
            # Main title — skip, rendered separately
            i += 1
            continue

        # Author / date lines after title
        if re.match(r'^Alice Ott', line) or re.match(r'^Independent Research', line) or \
           re.match(r'^\[alice', line):
            i += 1
            continue

        # HR
        if line.strip() == '---':
            story.append(HRFlowable(width="100%", thickness=0.5, color=RULE,
                                    spaceAfter=6, spaceBefore=6))
            i += 1
            continue

        # H2
        if line.startswith('## '):
            txt = line[3:].strip()
            in_abstract = txt.lower() == 'abstract'
            in_refs = txt.lower() == 'references'
            in_fig_captions = 'figure caption' in txt.lower()
            story.append(Paragraph(inline(txt), H1_S))
            i += 1
            continue

        # H3
        if line.startswith('### '):
            story.append(Paragraph(inline(line[4:].strip()), H2_S))
            i += 1
            continue

        # H4
        if line.startswith('#### '):
            story.append(Paragraph(inline(line[5:].strip()), H3_S))
            i += 1
            continue

        # Figure caption block — detect "**Figure N**" lines
        if in_fig_captions and line.startswith('**Figure'):
            m = re.match(r'\*\*Figure (\d+)\*\*[^:]*:(.*)', line)
            if m:
                fig_num = m.group(1)
                cap_text = m.group(2).strip()
                # Collect continuation lines
                j = i + 1
                while j < len(lines) and lines[j].strip() and not lines[j].startswith('**Figure'):
                    cap_text += ' ' + lines[j].strip()
                    j += 1
                fig_id = f"fig{fig_num}"
                if fig_id in FIGURE_MAP:
                    story.extend(figure_block(fig_id, f"<b>Figure {fig_num}.</b> {inline(cap_text)}"))
                else:
                    story.append(Paragraph(f"<b>Figure {fig_num}</b> (placeholder — requires additional data). {inline(cap_text)}", FIGCAP_S))
                i = j
                continue

        # Table
        if line.startswith('|') and i + 1 < len(lines) and lines[i+1].startswith('|---'):
            table_lines = []
            while i < len(lines) and lines[i].startswith('|'):
                table_lines.append(lines[i])
                i += 1
            t = parse_table(table_lines)
            if t:
                story.append(Spacer(1, 4))
                story.append(t)
                story.append(Spacer(1, 8))
            continue

        # Code block
        if line.startswith('```'):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1
            code_text = '\n'.join(code_lines)
            story.append(Paragraph(code_text.replace('\n', '<br/>'), CODE_S))
            continue

        # Numbered list
        if re.match(r'^\d+\.\s', line):
            txt = re.sub(r'^\d+\.\s+', '', line)
            story.append(Paragraph('• ' + inline(txt), BULLET_S))
            i += 1
            continue

        # Bullet list
        if re.match(r'^[-*]\s', line):
            story.append(Paragraph('• ' + bullet_text(line), BULLET_S))
            i += 1
            continue

        # Blockquote
        if line.startswith('> '):
            story.append(Paragraph('<i>' + inline(line[2:]) + '</i>',
                                   S("BQ", base="Normal", leftIndent=24, rightIndent=8,
                                     fontSize=10, leading=15, alignment=TA_JUSTIFY,
                                     textColor=HexColor("#444444"))))
            i += 1
            continue

        # Abstract special style
        if in_abstract and line.strip() and not line.startswith('#'):
            story.append(Paragraph(inline(line), ABSTRACT_S))
            i += 1
            continue

        # References
        if in_refs and line.strip() and not line.startswith('#'):
            story.append(Paragraph(inline(line), REF_S))
            i += 1
            continue

        # Empty line
        if not line.strip():
            story.append(Spacer(1, 4))
            i += 1
            continue

        # Default body paragraph
        story.append(Paragraph(inline(line), BODY_S))
        i += 1

    return story


# ── Header/footer ─────────────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(MID_GREY)
    w, h = letter
    # Footer
    canvas.drawCentredString(w / 2, 0.5 * inch, f"— {doc.page} —")
    if doc.page > 1:
        canvas.drawString(inch, h - 0.6 * inch,
                          "Ott (2026) — Synthetic Personality Drift")
        canvas.drawRightString(w - inch, h - 0.6 * inch,
                               "Preprint — Not Peer Reviewed")
    canvas.restoreState()


# ── Title page elements ───────────────────────────────────────────────────────
def title_block():
    elems = []
    elems.append(Spacer(1, 0.6 * inch))
    elems.append(Paragraph(
        "Synthetic Personality Drift: Behaviorally-Grounded Psychometric<br/>"
        "Measurement of OCEAN Dynamics in LLM Agent Networks",
        TITLE_S))
    elems.append(Spacer(1, 8))
    elems.append(Paragraph("Alice Ott", AUTHOR_S))
    elems.append(Paragraph("Independent Research · alice@lurkr.net", AUTHOR_S))
    elems.append(Paragraph("April 2026 · Preprint", DATE_S))
    elems.append(HRFlowable(width="100%", thickness=1, color=ACCENT,
                             spaceAfter=12, spaceBefore=4))
    return elems


# ── Build ─────────────────────────────────────────────────────────────────────
def build():
    doc = SimpleDocTemplate(
        OUT,
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=0.85 * inch,
        bottomMargin=0.85 * inch,
        title="Synthetic Personality Drift",
        author="Alice Ott",
        subject="LLM personality dynamics, OCEAN measurement, social simulation",
        creator="Lurkr Research",
    )

    with open(MD, encoding="utf-8") as f:
        text = f.read()

    story = title_block() + parse_md(text)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"✓ Written: {OUT}")


if __name__ == "__main__":
    build()
