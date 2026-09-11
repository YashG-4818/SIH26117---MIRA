"""
core/outputs.py — turn an answer into a document a plant engineer can actually
send: Word, Excel, PowerPoint, PDF or a chart.

The differentiator here is the provenance block. Every file this module produces
carries, on its face:

  * the exact question that was asked
  * the model that answered, running locally
  * every source document and page the answer was grounded in
  * the head hash of the audit chain at the moment of generation

That last line is the one that matters. It means the document points back into
the tamper-evident log, so months later you can prove which retrieval and which
approval produced it. A "download as Word" button is a feature; a document that
carries its own chain of custody is an argument.
"""

from __future__ import annotations

import re
import textwrap
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import config

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
MRPL_BLUE = (0x0B, 0x3C, 0x5D)
MRPL_ACCENT = (0xC0, 0x4A, 0x1E)
GREY = (0x55, 0x5F, 0x6B)


def _slug(text: str, limit: int = 44) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", (text or "output").strip())
    return s.strip("_")[:limit] or "output"


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _outpath(kind: str, title: str, ext: str) -> Path:
    return Path(config.GENERATED) / f"{kind}_{_slug(title)}_{_stamp()}.{ext}"


def provenance(question: str, citations: Iterable[str] | None = None,
               model: str | None = None) -> dict:
    """The chain-of-custody block stamped onto every generated file."""
    from core import audit
    v = audit.verify()
    cites = [c for c in (citations or []) if c]
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": (question or "").strip(),
        "model": model or config.CHAT_MODEL,
        "host": config.OLLAMA_HOST,
        "sources": cites,
        "source_count": len(cites),
        "audit_records": v.get("records", 0),
        "audit_head_hash": (v.get("head_hash") or "")[:32],
        "audit_intact": v.get("ok", False),
        "session": audit.SESSION_ID,
        "notice": config.OUTPUT_FOOTER,
    }


def _prov_lines(prov: dict) -> list[tuple[str, str]]:
    return [
        ("Generated", f"{prov['generated_at']} (on-premise)"),
        ("Model", f"{prov['model']} served locally at {prov['host']}"),
        ("Question", prov["question"] or "-"),
        ("Sources cited", f"{prov['source_count']} document reference(s)"),
        ("Audit chain", f"{prov['audit_records']} records, "
                        f"{'intact' if prov['audit_intact'] else 'BROKEN'}, "
                        f"head {prov['audit_head_hash'] or 'n/a'}"),
        ("Session", prov["session"]),
    ]


def _split_sections(markdown: str) -> list[tuple[str, list[str]]]:
    """Turn the model's markdown-ish answer into (heading, paragraphs) pairs."""
    sections: list[tuple[str, list[str]]] = []
    heading = ""
    body: list[str] = []
    for raw in (markdown or "").split("\n"):
        line = raw.rstrip()
        m = re.match(r"^\s*#{1,4}\s+(.*)$", line)
        m2 = re.match(r"^\*\*(.{3,80}?)\*\*:?\s*$", line.strip())
        if m or m2:
            if heading or body:
                sections.append((heading, body))
            heading = (m.group(1) if m else m2.group(1)).strip()
            body = []
            continue
        if line.strip():
            body.append(line.strip())
        elif body and body[-1] != "":
            body.append("")
    if heading or body:
        sections.append((heading, body))
    return sections or [("", [markdown or ""])]


def _clean_inline(text: str) -> str:
    """Strip markdown emphasis; keep the citation brackets, they are the point."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text.strip()


def _is_bullet(line: str) -> bool:
    return bool(re.match(r"^\s*(?:[-*•]|\d{1,2}[.)])\s+\S", line))


def _debullet(line: str) -> str:
    return re.sub(r"^\s*(?:[-*•]|\d{1,2}[.)])\s+", "", line).strip()


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------
def make_docx(title: str, answer_markdown: str, *, question: str = "",
              citations: Iterable[str] | None = None,
              model: str | None = None,
              subtitle: str = "") -> dict:
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor, Inches

    prov = provenance(question, citations, model)
    doc = Document()

    # Page setup and a readable base style.
    for s in doc.sections:
        s.top_margin = Inches(0.85)
        s.bottom_margin = Inches(0.8)
        s.left_margin = Inches(0.95)
        s.right_margin = Inches(0.95)
    base = doc.styles["Normal"]
    base.font.name = "Calibri"
    base.font.size = Pt(10.5)
    base.paragraph_format.space_after = Pt(6)
    base.paragraph_format.line_spacing = 1.12

    # Masthead
    p = doc.add_paragraph()
    r = p.add_run(config.ORG.upper())
    r.font.size = Pt(8.5)
    r.font.bold = True
    r.font.color.rgb = RGBColor(*GREY)
    p.paragraph_format.space_after = Pt(0)

    p = doc.add_paragraph()
    r = p.add_run(title)
    r.font.size = Pt(19)
    r.font.bold = True
    r.font.color.rgb = RGBColor(*MRPL_BLUE)
    p.paragraph_format.space_after = Pt(2)

    if subtitle:
        p = doc.add_paragraph()
        r = p.add_run(subtitle)
        r.font.size = Pt(10.5)
        r.font.italic = True
        r.font.color.rgb = RGBColor(*GREY)

    # A rule under the masthead.
    pr = doc.add_paragraph()
    pPr = pr._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "12")
    bottom.set(qn("w:color"), "0B3C5D")
    bdr.append(bottom)
    pPr.append(bdr)

    # Body
    for heading, lines in _split_sections(answer_markdown):
        if heading:
            hp = doc.add_paragraph()
            hr = hp.add_run(heading)
            hr.font.size = Pt(12)
            hr.font.bold = True
            hr.font.color.rgb = RGBColor(*MRPL_BLUE)
            hp.paragraph_format.space_before = Pt(12)
            hp.paragraph_format.space_after = Pt(3)
        for line in lines:
            if not line.strip():
                continue
            if _is_bullet(line):
                bp = doc.add_paragraph(_clean_inline(_debullet(line)),
                                       style="List Bullet")
                bp.paragraph_format.space_after = Pt(3)
            else:
                doc.add_paragraph(_clean_inline(line))

    # Provenance
    hp = doc.add_paragraph()
    hr = hp.add_run("PROVENANCE AND CHAIN OF CUSTODY")
    hr.font.size = Pt(11)
    hr.font.bold = True
    hr.font.color.rgb = RGBColor(*MRPL_ACCENT)
    hp.paragraph_format.space_before = Pt(18)

    rows = _prov_lines(prov)
    t = doc.add_table(rows=0, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    for k, v in rows:
        cells = t.add_row().cells
        kr = cells[0].paragraphs[0].add_run(k)
        kr.font.bold = True
        kr.font.size = Pt(8.5)
        vr = cells[1].paragraphs[0].add_run(str(v))
        vr.font.size = Pt(8.5)
    t.columns[0].width = Inches(1.35)
    t.columns[1].width = Inches(5.0)

    if prov["sources"]:
        sp = doc.add_paragraph()
        sr = sp.add_run("Sources")
        sr.font.bold = True
        sr.font.size = Pt(9)
        sp.paragraph_format.space_before = Pt(8)
        for c in prov["sources"]:
            bp = doc.add_paragraph(c, style="List Number")
            bp.runs[0].font.size = Pt(8.5)

    fp = doc.add_paragraph()
    fr = fp.add_run(config.OUTPUT_FOOTER)
    fr.font.size = Pt(7.5)
    fr.font.italic = True
    fr.font.color.rgb = RGBColor(*GREY)
    fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    fp.paragraph_format.space_before = Pt(10)

    path = _outpath("report", title, "docx")
    doc.save(str(path))
    return _finish(path, "docx", title, prov)


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------
def make_xlsx(title: str, table: list[dict] | list[list[Any]], *,
              question: str = "", citations: Iterable[str] | None = None,
              model: str | None = None, chart: dict | None = None,
              notes: str = "") -> dict:
    """Write a table to Excel with real formatting, an optional line chart and a
    Provenance sheet.

    `chart` is {"x": "Column name", "y": ["Col A", "Col B"], "title": "..."}.
    """
    import openpyxl
    from openpyxl.chart import LineChart, Reference
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    prov = provenance(question, citations, model)

    # Normalise input to header + rows.
    if table and isinstance(table[0], dict):
        headers = list(table[0].keys())
        rows = [[r.get(h, "") for h in headers] for r in table]  # type: ignore
    elif table:
        headers = [str(c) for c in table[0]]                      # type: ignore
        rows = [list(r) for r in table[1:]]                       # type: ignore
    else:
        headers, rows = ["(no data)"], []

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"

    thin = Side(style="thin", color="BFC7D1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws["A1"] = title
    ws["A1"].font = Font(size=14, bold=True, color="0B3C5D")
    ws["A2"] = f"{config.ORG} - generated on-premise {prov['generated_at']}"
    ws["A2"].font = Font(size=9, italic=True, color="555F6B")
    if notes:
        ws["A3"] = notes
        ws["A3"].font = Font(size=9, color="555F6B")
    header_row = 5 if notes else 4

    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=c, value=h)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor="0B3C5D")
        cell.alignment = Alignment(horizontal="center", vertical="center",
                                   wrap_text=True)
        cell.border = border
    for r_i, row in enumerate(rows, header_row + 1):
        for c_i, val in enumerate(row, 1):
            cell = ws.cell(row=r_i, column=c_i, value=val)
            cell.border = border
            cell.font = Font(size=10)
            if isinstance(val, (int, float)):
                cell.alignment = Alignment(horizontal="right")
                cell.number_format = "#,##0.00" if isinstance(val, float) \
                    else "#,##0"
    # Banding, so a long log is readable.
    band = PatternFill("solid", fgColor="F4F7FA")
    for r_i in range(header_row + 1, header_row + 1 + len(rows)):
        if (r_i - header_row) % 2 == 0:
            for c_i in range(1, len(headers) + 1):
                if ws.cell(row=r_i, column=c_i).fill.fgColor.rgb in \
                        ("00000000", None):
                    ws.cell(row=r_i, column=c_i).fill = band

    for c_i, h in enumerate(headers, 1):
        longest = max([len(str(h))] +
                      [len(str(r[c_i - 1])) for r in rows if c_i <= len(r)]
                      or [8])
        ws.column_dimensions[get_column_letter(c_i)].width = \
            min(46, max(11, longest + 3))
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    ws.auto_filter.ref = (f"A{header_row}:"
                          f"{get_column_letter(len(headers))}"
                          f"{header_row + len(rows)}")

    # Optional chart
    if chart and rows:
        try:
            x_name = chart.get("x")
            y_names = [y for y in (chart.get("y") or []) if y in headers]
            if x_name in headers and y_names:
                lc = LineChart()
                lc.title = chart.get("title") or title
                lc.height, lc.width = 8.5, 19
                lc.y_axis.title = chart.get("y_title") or ""
                lc.x_axis.title = x_name
                for y in y_names:
                    col = headers.index(y) + 1
                    ref = Reference(ws, min_col=col, min_row=header_row,
                                    max_row=header_row + len(rows))
                    lc.add_data(ref, titles_from_data=True)
                cats = Reference(ws, min_col=headers.index(x_name) + 1,
                                 min_row=header_row + 1,
                                 max_row=header_row + len(rows))
                lc.set_categories(cats)
                ws.add_chart(lc, f"A{header_row + len(rows) + 3}")
        except Exception:  # noqa: BLE001 - a missing chart must not lose the data
            pass

    # Provenance sheet
    ps = wb.create_sheet("Provenance")
    ps["A1"] = "PROVENANCE AND CHAIN OF CUSTODY"
    ps["A1"].font = Font(size=12, bold=True, color="C04A1E")
    r_i = 3
    for k, v in _prov_lines(prov):
        ps.cell(row=r_i, column=1, value=k).font = Font(bold=True, size=10)
        ps.cell(row=r_i, column=2, value=str(v)).font = Font(size=10)
        r_i += 1
    if prov["sources"]:
        r_i += 1
        ps.cell(row=r_i, column=1, value="Sources").font = Font(bold=True,
                                                                size=10)
        r_i += 1
        for n, c in enumerate(prov["sources"], 1):
            ps.cell(row=r_i, column=1, value=n).font = Font(size=10)
            ps.cell(row=r_i, column=2, value=c).font = Font(size=10)
            r_i += 1
    r_i += 1
    ps.cell(row=r_i, column=1, value=config.OUTPUT_FOOTER).font = \
        Font(size=8, italic=True, color="555F6B")
    ps.column_dimensions["A"].width = 18
    ps.column_dimensions["B"].width = 88

    path = _outpath("workbook", title, "xlsx")
    wb.save(str(path))
    return _finish(path, "xlsx", title, prov, rows=len(rows))


# ---------------------------------------------------------------------------
# PowerPoint
# ---------------------------------------------------------------------------
def make_pptx(title: str, answer_markdown: str, *, question: str = "",
              citations: Iterable[str] | None = None,
              model: str | None = None,
              image_paths: Iterable[str | Path] | None = None) -> dict:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Emu, Inches, Pt

    prov = provenance(question, citations, model)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    SW, SH = prs.slide_width, prs.slide_height
    blank = prs.slide_layouts[6]

    def band(slide, height=Inches(0.16), color=MRPL_BLUE):
        from pptx.enum.shapes import MSO_SHAPE
        s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, height)
        s.fill.solid()
        s.fill.fore_color.rgb = RGBColor(*color)
        s.line.fill.background()
        s.shadow.inherit = False

    def textbox(slide, left, top, width, height, text, size, *, bold=False,
                color=(0x1A, 0x1A, 0x1A), italic=False, align=None):
        from pptx.enum.text import PP_ALIGN
        tb = slide.shapes.add_textbox(left, top, width, height)
        tf = tb.text_frame
        tf.word_wrap = True
        lines = text.split("\n")
        for i, ln in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            r = p.add_run()
            r.text = ln
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.italic = italic
            r.font.color.rgb = RGBColor(*color)
            r.font.name = "Calibri"
            if align == "center":
                p.alignment = PP_ALIGN.CENTER
        return tb

    # --- Title slide ---
    s = prs.slides.add_slide(blank)
    band(s, Inches(0.22))
    textbox(s, Inches(0.9), Inches(2.15), SW - Inches(1.8), Inches(1.5),
            title, 40, bold=True, color=MRPL_BLUE)
    textbox(s, Inches(0.9), Inches(3.5), SW - Inches(1.8), Inches(0.9),
            config.ORG, 16, color=GREY)
    textbox(s, Inches(0.9), Inches(4.05), SW - Inches(1.8), Inches(1.4),
            f"{config.APP_NAME} - {config.APP_SUBTITLE}\n"
            f"Generated on-premise {prov['generated_at']} | "
            f"model {prov['model']}", 12, color=GREY, italic=True)

    # --- Content slides ---
    sections = [(h, b) for h, b in _split_sections(answer_markdown)
                if h or any(x.strip() for x in b)]
    MAX_BULLETS = 6
    for heading, lines in sections:
        bullets = [_clean_inline(_debullet(x)) if _is_bullet(x)
                   else _clean_inline(x)
                   for x in lines if x.strip()]
        bullets = [b for b in bullets if b]
        if not bullets and not heading:
            continue
        for page in range(0, max(1, len(bullets)), MAX_BULLETS):
            part = bullets[page:page + MAX_BULLETS]
            sl = prs.slides.add_slide(blank)
            band(sl)
            head = heading or "Findings"
            if page:
                head += " (cont.)"
            textbox(sl, Inches(0.75), Inches(0.5), SW - Inches(1.5),
                    Inches(0.85), head, 26, bold=True, color=MRPL_BLUE)
            body = "\n".join("•  " + textwrap.fill(b, 96).replace("\n", "\n    ")
                             for b in part)
            textbox(sl, Inches(0.85), Inches(1.6), SW - Inches(1.7),
                    SH - Inches(2.4), body, 15)

    # --- Images ---
    for img in (image_paths or []):
        ip = Path(img)
        if not ip.exists():
            continue
        sl = prs.slides.add_slide(blank)
        band(sl)
        textbox(sl, Inches(0.75), Inches(0.45), SW - Inches(1.5), Inches(0.7),
                ip.stem.replace("_", " ")[:70], 22, bold=True, color=MRPL_BLUE)
        try:
            from PIL import Image as PILImage
            with PILImage.open(ip) as im:
                iw, ih = im.size
            avail_w, avail_h = SW - Inches(1.6), SH - Inches(2.0)
            scale = min(avail_w / Emu(int(iw * 9525)),
                        avail_h / Emu(int(ih * 9525)))
            w = Emu(int(iw * 9525 * scale))
            h = Emu(int(ih * 9525 * scale))
            sl.shapes.add_picture(str(ip), int((SW - w) / 2), Inches(1.35),
                                  width=w, height=h)
        except Exception:  # noqa: BLE001
            sl.shapes.add_picture(str(ip), Inches(1.2), Inches(1.4),
                                  width=SW - Inches(2.4))

    # --- Provenance slide ---
    sl = prs.slides.add_slide(blank)
    band(sl, color=MRPL_ACCENT)
    textbox(sl, Inches(0.75), Inches(0.5), SW - Inches(1.5), Inches(0.8),
            "Provenance and chain of custody", 26, bold=True, color=MRPL_ACCENT)
    body = "\n".join(f"{k}:  {v}" for k, v in _prov_lines(prov))
    if prov["sources"]:
        body += "\n\nSources:\n" + "\n".join(
            f"  {i}. {c}" for i, c in enumerate(prov["sources"][:9], 1))
    textbox(sl, Inches(0.85), Inches(1.5), SW - Inches(1.7), SH - Inches(2.3),
            body, 12)
    textbox(sl, Inches(0.85), SH - Inches(0.72), SW - Inches(1.7),
            Inches(0.5), config.OUTPUT_FOOTER, 9, italic=True, color=GREY)

    path = _outpath("briefing", title, "pptx")
    slide_count = len(prs.slides)
    prs.save(str(path))
    return _finish(path, "pptx", title, prov, slides=slide_count)


# ---------------------------------------------------------------------------
# Chart
# ---------------------------------------------------------------------------
def make_chart(title: str, x: list[Any], series: dict[str, list[float]], *,
               y_label: str = "", x_label: str = "",
               hlines: list[dict] | None = None,
               question: str = "", kind: str = "line") -> dict:
    """A publication-quality PNG. hlines draws limit lines, e.g. alert and trip,
    which is what makes a vibration chart mean something."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    prov = provenance(question, [], None)
    fig, ax = plt.subplots(figsize=(11.5, 5.6), dpi=150)
    palette = ["#0B3C5D", "#C04A1E", "#2E7D32", "#6A1B9A", "#00695C"]

    idx = list(range(len(x)))
    for i, (name, vals) in enumerate(series.items()):
        col = palette[i % len(palette)]
        if kind == "bar":
            width = 0.8 / max(1, len(series))
            ax.bar([v + i * width for v in idx], vals, width=width,
                   label=name, color=col, alpha=0.9)
        else:
            ax.plot(idx[:len(vals)], vals, marker="o", markersize=5,
                    linewidth=2.1, label=name, color=col)

    for hl in (hlines or []):
        ax.axhline(hl["y"], linestyle="--", linewidth=1.5,
                   color=hl.get("color", "#B3261E"), alpha=0.85)
        ax.annotate(hl.get("label", ""), xy=(0.995, hl["y"]),
                    xycoords=("axes fraction", "data"),
                    ha="right", va="bottom", fontsize=8.5,
                    color=hl.get("color", "#B3261E"), fontweight="bold")

    ax.set_title(title, fontsize=14, fontweight="bold", color="#0B3C5D",
                 pad=13)
    ax.set_ylabel(y_label, fontsize=10.5)
    ax.set_xlabel(x_label, fontsize=10.5)
    ax.set_xticks(idx)
    ax.set_xticklabels([str(v) for v in x], rotation=30, ha="right",
                       fontsize=9)
    ax.grid(axis="y", alpha=0.28, linestyle=":")
    ax.spines[["top", "right"]].set_visible(False)

    # Headroom, so a limit line sitting at the top of the range still has room
    # for its label instead of being clipped against the axes.
    all_vals = [v for vals in series.values() for v in vals] + \
               [hl["y"] for hl in (hlines or [])]
    if all_vals:
        lo, hi = min(all_vals), max(all_vals)
        span = (hi - lo) or (abs(hi) or 1.0)
        ax.set_ylim(min(0, lo - span * 0.08) if lo >= 0 else lo - span * 0.08,
                    hi + span * 0.14)

    # The legend goes above the plot, never inside it: limit lines live at the
    # top of the range and a boxed legend would sit right on top of them.
    if len(series) > 1 or hlines:
        ax.legend(fontsize=9, frameon=False, ncol=min(3, len(series)),
                  loc="lower left", bbox_to_anchor=(0.0, 1.015))
    fig.text(0.01, 0.008,
             f"{config.ORG} | generated on-premise {prov['generated_at']} | "
             f"audit head {prov['audit_head_hash'][:16] or 'n/a'}",
             fontsize=7, color="#555F6B")
    fig.tight_layout(rect=(0, 0.035, 1, 1))

    path = _outpath("chart", title, "png")
    fig.savefig(str(path), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return _finish(path, "png", title, prov)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
def make_pdf(title: str, answer_markdown: str, *, question: str = "",
             citations: Iterable[str] | None = None,
             model: str | None = None,
             image_paths: Iterable[str | Path] | None = None) -> dict:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (BaseDocTemplate, Frame, Image, PageTemplate,
                                    Paragraph, Spacer, Table, TableStyle)
    from xml.sax.saxutils import escape

    prov = provenance(question, citations, model)
    blue = colors.HexColor("#0B3C5D")
    accent = colors.HexColor("#C04A1E")
    grey = colors.HexColor("#555F6B")

    st = {
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=17,
                             leading=21, textColor=blue, spaceAfter=3),
        "sub": ParagraphStyle("sub", fontName="Helvetica-Oblique", fontSize=9.5,
                              leading=13, textColor=grey, spaceAfter=10),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5,
                             leading=14, textColor=blue, spaceBefore=11,
                             spaceAfter=3),
        "p": ParagraphStyle("p", fontName="Helvetica", fontSize=9.6,
                            leading=13.4, alignment=TA_LEFT, spaceAfter=5),
        "li": ParagraphStyle("li", fontName="Helvetica", fontSize=9.6,
                             leading=13.4, leftIndent=11, bulletIndent=2,
                             spaceAfter=3),
        "prov": ParagraphStyle("prov", fontName="Helvetica", fontSize=8,
                               leading=10.5, textColor=grey),
    }

    def decorate(canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(blue)
        canvas.rect(0, h - 6 * mm, w, 6 * mm, stroke=0, fill=1)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(grey)
        canvas.drawString(18 * mm, h - 12 * mm, config.ORG.upper())
        canvas.drawRightString(w - 18 * mm, h - 12 * mm,
                               f"{config.APP_NAME.upper()} | "
                               f"{config.PROBLEM_ID}")
        canvas.setFont("Helvetica", 6.8)
        canvas.drawString(18 * mm, 11 * mm, config.OUTPUT_FOOTER)
        canvas.drawRightString(w - 18 * mm, 11 * mm, f"Page {doc.page}")
        canvas.setStrokeColor(colors.HexColor("#D5DBE3"))
        canvas.line(18 * mm, 14 * mm, w - 18 * mm, 14 * mm)
        canvas.restoreState()

    path = _outpath("report", title, "pdf")
    doc = BaseDocTemplate(str(path), pagesize=A4,
                          leftMargin=18 * mm, rightMargin=18 * mm,
                          topMargin=18 * mm, bottomMargin=18 * mm,
                          title=title, author=config.APP_NAME)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  id="body")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame],
                                       onPage=decorate)])

    flow: list[Any] = [Paragraph(escape(title), st["h1"])]
    flow.append(Paragraph(f"Generated on-premise {prov['generated_at']} - "
                          f"model {escape(prov['model'])}", st["sub"]))

    for heading, lines in _split_sections(answer_markdown):
        if heading:
            flow.append(Paragraph(escape(heading), st["h2"]))
        for line in lines:
            if not line.strip():
                continue
            if _is_bullet(line):
                flow.append(Paragraph(escape(_clean_inline(_debullet(line))),
                                      st["li"], bulletText="•"))
            else:
                flow.append(Paragraph(escape(_clean_inline(line)), st["p"]))

    for img in (image_paths or []):
        ip = Path(img)
        if not ip.exists():
            continue
        try:
            from PIL import Image as PILImage
            with PILImage.open(ip) as im:
                iw, ih = im.size
            max_w = doc.width
            scale = min(1.0, max_w / iw)
            flow += [Spacer(1, 7 * mm),
                     Image(str(ip), width=iw * scale, height=ih * scale)]
        except Exception:  # noqa: BLE001
            pass

    flow += [Spacer(1, 9 * mm),
             Paragraph("PROVENANCE AND CHAIN OF CUSTODY",
                       ParagraphStyle("pv", parent=st["h2"], textColor=accent))]
    rows = [[Paragraph(f"<b>{escape(k)}</b>", st["prov"]),
             Paragraph(escape(str(v)), st["prov"])] for k, v in _prov_lines(prov)]
    t = Table(rows, colWidths=[32 * mm, doc.width - 32 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DBE3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F4F7FA")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    flow.append(t)
    if prov["sources"]:
        flow.append(Spacer(1, 4 * mm))
        flow.append(Paragraph("<b>Sources</b>", st["prov"]))
        for i, c in enumerate(prov["sources"], 1):
            flow.append(Paragraph(f"{i}. {escape(c)}", st["prov"]))

    doc.build(flow)
    return _finish(path, "pdf", title, prov)


# ---------------------------------------------------------------------------
# Bookkeeping
# ---------------------------------------------------------------------------
def _finish(path: Path, kind: str, title: str, prov: dict, **extra) -> dict:
    from core import audit
    rec = {
        "ok": True,
        "path": str(path),
        "filename": path.name,
        "kind": kind,
        "title": title,
        "size_kb": round(path.stat().st_size / 1024, 1),
        "provenance": prov,
        **extra,
    }
    audit.log("output.generated", {
        "kind": kind, "filename": path.name, "title": title,
        "size_kb": rec["size_kb"], "sources": prov["sources"],
        "audit_head_at_generation": prov["audit_head_hash"],
    }, actor="outputs")
    return rec


def list_generated() -> list[dict]:
    out = []
    for p in sorted(Path(config.GENERATED).glob("*"),
                    key=lambda q: q.stat().st_mtime, reverse=True):
        if p.is_file():
            out.append({"filename": p.name, "path": str(p),
                        "kind": p.suffix.lstrip("."),
                        "size_kb": round(p.stat().st_size / 1024, 1),
                        "modified": time.strftime(
                            "%Y-%m-%d %H:%M:%S",
                            time.localtime(p.stat().st_mtime))})
    return out
