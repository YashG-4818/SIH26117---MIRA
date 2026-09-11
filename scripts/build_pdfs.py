"""
make_corpus.py — builds the synthetic MRPL demo document set.

Run once:  python scripts/make_corpus.py
Output:    data/documents/*.pdf|.docx|.xlsx|.png  +  data/documents/manifest.json

You do NOT normally need to run this — the documents are already generated and
shipped in data/documents/. Re-run it only if you want to change the facts in
corpus_spec.py and regenerate everything consistently.

Formats are mixed ON PURPOSE so that every branch of the document pipeline gets
exercised by the demo:
  - native-text PDF        -> fast text extraction path
  - table-heavy PDF        -> pdfplumber table extraction path
  - DOCX                   -> python-docx path
  - XLSX                   -> openpyxl path
  - rasterised "scanned" PDF -> Tesseract OCR path  (the wow document)
  - PNG schematic          -> vision-model path
"""

import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import corpus_spec as S  # noqa: E402

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether,  # noqa: E402
                                PageBreak, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle)

from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "documents"
OUT.mkdir(parents=True, exist_ok=True)

random.seed(26117)  # reproducible "scanner noise"

# ---------------------------------------------------------------------------
# Shared PDF styling
# ---------------------------------------------------------------------------
SS = getSampleStyleSheet()
ST = {
    "title": ParagraphStyle("t", parent=SS["Title"], fontName="Helvetica-Bold",
                            fontSize=14, leading=18, spaceAfter=2),
    "subtitle": ParagraphStyle("st", parent=SS["Normal"], fontSize=9.5,
                               alignment=TA_CENTER, textColor=colors.HexColor("#444444"),
                               spaceAfter=10),
    "h1": ParagraphStyle("h1", parent=SS["Heading1"], fontName="Helvetica-Bold",
                         fontSize=11.5, leading=14, spaceBefore=12, spaceAfter=5,
                         textColor=colors.HexColor("#0b3d5c")),
    "h2": ParagraphStyle("h2", parent=SS["Heading2"], fontName="Helvetica-Bold",
                         fontSize=10, leading=13, spaceBefore=8, spaceAfter=3),
    "body": ParagraphStyle("b", parent=SS["Normal"], fontSize=9.5, leading=13.5,
                           alignment=TA_JUSTIFY, spaceAfter=5),
    "cell": ParagraphStyle("c", parent=SS["Normal"], fontSize=8, leading=10.5),
    "cellb": ParagraphStyle("cb", parent=SS["Normal"], fontSize=8, leading=10.5,
                            fontName="Helvetica-Bold"),
    "step": ParagraphStyle("s", parent=SS["Normal"], fontSize=9.5, leading=13.5,
                           leftIndent=16, spaceAfter=4),
    "warn": ParagraphStyle("w", parent=SS["Normal"], fontSize=9, leading=12.5,
                           leftIndent=8, rightIndent=8, spaceBefore=4,
                           spaceAfter=6, textColor=colors.HexColor("#8a1c1c"),
                           fontName="Helvetica-Bold"),
}

GRID = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce6ef")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
])


def _decorate(canvas, doc, doc_id, title):
    """Header + footer stamped on every page."""
    canvas.saveState()
    w, h = A4
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(colors.HexColor("#0b3d5c"))
    canvas.drawString(18 * mm, h - 12 * mm, S.PLANT["short"])
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(32 * mm, h - 12 * mm, S.unit_header())
    canvas.drawRightString(w - 18 * mm, h - 12 * mm, f"{doc_id}")
    canvas.setStrokeColor(colors.HexColor("#0b3d5c"))
    canvas.setLineWidth(0.8)
    canvas.line(18 * mm, h - 14 * mm, w - 18 * mm, h - 14 * mm)

    canvas.setLineWidth(0.4)
    canvas.setStrokeColor(colors.HexColor("#999999"))
    canvas.line(18 * mm, 16 * mm, w - 18 * mm, 16 * mm)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(colors.HexColor("#8a1c1c"))
    canvas.drawString(18 * mm, 12 * mm, S.PLANT["doc_class"])
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawCentredString(w / 2, 8.5 * mm, S.PLANT["synthetic_notice"])
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawRightString(w - 18 * mm, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(filename, doc_id, title, story):
    path = OUT / filename
    d = BaseDocTemplate(str(path), pagesize=A4,
                        leftMargin=18 * mm, rightMargin=18 * mm,
                        topMargin=20 * mm, bottomMargin=20 * mm,
                        title=title, author=S.PLANT["short"],
                        subject=S.PLANT["synthetic_notice"])
    frame = Frame(d.leftMargin, d.bottomMargin, d.width, d.height, id="f")
    d.addPageTemplates([PageTemplate(id="p", frames=[frame],
                                     onPage=lambda c, dd: _decorate(c, dd, doc_id, title))])
    d.build(story)
    return path


def meta_table(rows, widths=(38 * mm, 58 * mm, 32 * mm, 46 * mm)):
    data = []
    for r in rows:
        data.append([Paragraph(str(c), ST["cellb"] if i % 2 == 0 else ST["cell"])
                     for i, c in enumerate(r)])
    t = Table(data, colWidths=list(widths))
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f6")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eef2f6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def head(title, subtitle):
    return [Paragraph(title, ST["title"]), Paragraph(subtitle, ST["subtitle"])]


def grid_table(header, rows, widths):
    data = [[Paragraph(h, ST["cellb"]) for h in header]]
    for r in rows:
        data.append([Paragraph(str(c), ST["cell"]) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(GRID)
    return t


# ===========================================================================
# 1. SOP  (native text PDF, numbered procedure)
# ===========================================================================
def build_sop():
    d = S.DOCS["sop"]
    st = []
    st += head(f"STANDARD OPERATING PROCEDURE",
               f"{d['id']} {d['rev']} &nbsp;|&nbsp; {d['title']}")
    st.append(meta_table([
        ("Document No.", d["id"], "Revision", d["rev"]),
        ("Effective Date", d["effective"], "Next Review", d["next_review"]),
        ("Unit", f"{S.PLANT['unit_code']} - {S.PLANT['unit_name']}",
         "Document Owner", d["owner"]),
        ("Equipment", "P-2104A / P-2104B (Column Bottoms RCO Pumps)",
         "Classification", "Safety Critical"),
    ]))
    st.append(Spacer(1, 8))

    st.append(Paragraph("1. PURPOSE", ST["h1"]))
    st.append(Paragraph(
        "This procedure defines the mandatory sequence for transferring duty "
        "between the two CDU-2 column bottoms pumps, P-2104A and P-2104B, "
        "while the unit remains on line. The service is Reduced Crude Oil "
        "(RCO) at a normal operating temperature of 345 degC, which is above "
        "the auto-ignition temperature of the fluid. Any loss of containment "
        "during changeover is therefore treated as a potential fire event.",
        ST["body"]))

    st.append(Paragraph("2. SCOPE AND APPLICABILITY", ST["h1"]))
    st.append(Paragraph(
        "Applicable to all CDU-2 shift personnel executing a planned or "
        "unplanned hot standby changeover of P-2104A/B. This procedure does "
        "not cover pump isolation for maintenance, which is addressed by the "
        "unit isolation and positive-isolation permit procedure.", ST["body"]))

    st.append(Paragraph("3. RESPONSIBILITIES", ST["h1"]))
    st.append(grid_table(
        ["Role", "Responsibility"],
        [("Shift In-Charge",
          "Authorises the changeover. Must hold a current 'Pump Changeover - "
          "Hot Standby' certification. Verifies all pre-start checks in "
          "Section 5 are signed before authorising."),
         ("Panel Operator",
          "Monitors column bottoms level on C-2101, discharge pressure and "
          "flow throughout. Acknowledges and records all alarms."),
         ("Field Operator",
          "Executes valve operations in the sequence given in Section 6. "
          "Confirms each step verbally to the Panel Operator."),
         ("Rotating Equipment Engineer",
          "Consulted where the pump being taken off line has any condition "
          "monitoring exceedance. Approves return to service after any "
          "corrective work.")],
        [38 * mm, 136 * mm]))

    st.append(Paragraph("4. VIBRATION AND TEMPERATURE LIMITS", ST["h1"]))
    st.append(Paragraph(
        f"Condition monitoring limits for P-2104A/B are set per "
        f"{S.VIB_LIMITS['standard']}. These limits are mandatory decision "
        f"points, not advisory values.", ST["body"]))
    st.append(grid_table(
        ["Parameter", "Normal", "Alert", "Trip / Remove from service"],
        [("Overall vibration velocity (mm/s RMS)",
          f"up to {S.VIB_LIMITS['normal_max_mm_s']}",
          f"{S.VIB_LIMITS['alert_mm_s']}", f"{S.VIB_LIMITS['trip_mm_s']}"),
         ("Bearing temperature (degC)", "up to 75",
          f"{S.VIB_LIMITS['bearing_temp_alert_c']}",
          f"{S.VIB_LIMITS['bearing_temp_trip_c']}"),
         ("Seal chamber leakage", "Nil", "Visible weeping",
          "Continuous drip or mist")],
        [64 * mm, 30 * mm, 30 * mm, 50 * mm]))
    st.append(Paragraph(
        "A reading at or above the alert value of "
        f"{S.VIB_LIMITS['alert_mm_s']} mm/s RMS requires a corrective work "
        "order to be raised within 24 hours and the standby pump to be "
        "confirmed available. A reading at or above the trip value of "
        f"{S.VIB_LIMITS['trip_mm_s']} mm/s RMS requires changeover at the "
        "earliest safe opportunity.", ST["warn"]))

    st.append(Paragraph("5. PRE-START CHECKS ON THE INCOMING PUMP", ST["h1"]))
    checks = [
        "Confirm the incoming pump casing is warm. Warm-up line to be cracked "
        "open for a minimum of 30 minutes before start. Casing temperature to "
        "be within 40 degC of the discharge header temperature.",
        "Confirm suction valve is FULLY OPEN and the discharge valve is CLOSED.",
        "Confirm the non-return valve (NRV-2104A or NRV-2104B as applicable) "
        "is in service and has not been isolated.",
        "Confirm bearing lubricant level is between the sight glass marks and "
        "the oil is clear with no water haze.",
        "Confirm the mechanical seal support system is healthy: barrier or "
        "buffer fluid level above minimum, no low level alarm standing. "
        "RECORD THE ACTUAL LEVEL, do not simply tick.",
        "Confirm laser alignment record exists and shows parallel offset not "
        "exceeding 0.05 mm, if the pump has been opened since last run.",
        "Confirm cooling water flow to the seal cooler is established and the "
        "return is warm to touch.",
        "Confirm the pump is selected to AUTO on the DCS and the auto-start "
        "permissive is healthy.",
        "Confirm the area is free of hot work and that no permit is active "
        "within 15 m. Refer to any standing safety circular for the circuit.",
    ]
    for i, c in enumerate(checks, 1):
        st.append(Paragraph(f"5.{i} &nbsp; {c}", ST["step"]))

    st.append(PageBreak())
    st.append(Paragraph("6. CHANGEOVER SEQUENCE", ST["h1"]))
    st.append(Paragraph(
        "Steps must be executed in the order given. Each step is confirmed "
        "verbally between the Field Operator and the Panel Operator before "
        "the next step begins. If any step cannot be completed as written, "
        "STOP and revert to the original line-up.", ST["body"]))
    steps = [
        ("6.1", "Shift In-Charge authorises the changeover and records the "
                "reason and time in the shift log."),
        ("6.2", "Panel Operator notes the current C-2101 bottoms level, "
                "bottoms flow and discharge pressure as the reference "
                "condition. Place the level controller LIC-2101 on MANUAL at "
                "the current output."),
        ("6.3", "Panel Operator raises the C-2101 bottoms level to the upper "
                "half of the normal band to provide inventory margin during "
                "the transfer."),
        ("6.4", "Start the incoming pump. Confirm discharge pressure develops "
                "to within 0.5 kg/cm2 of the running pump within 10 seconds. "
                "If pressure does not develop, STOP the pump immediately and "
                "investigate before any further attempt."),
        ("6.5", "Crack open the incoming pump discharge valve slowly, taking "
                "not less than 60 seconds to reach 25% open. Watch for "
                "discharge pressure interaction and for any change in motor "
                "current on both machines."),
        ("6.6", "Continue opening the incoming discharge valve to fully open "
                "while simultaneously throttling the outgoing pump discharge "
                "valve, maintaining total bottoms flow within 5% of the "
                "reference value throughout."),
        ("6.7", "When the incoming pump is carrying full flow, close the "
                "outgoing pump discharge valve fully."),
        ("6.8", "Stop the outgoing pump. Confirm it comes to rest without "
                "reverse rotation. If reverse rotation is observed, report "
                "immediately as a suspect non-return valve."),
        ("6.9", "Return LIC-2101 to AUTO once the level is stable for 10 "
                "minutes."),
        ("6.10", "Line up the stopped pump as the new standby: discharge "
                 "valve closed, suction open, warm-up line cracked open, "
                 "AUTO selected. Unless the pump is being handed over for "
                 "maintenance, in which case follow the isolation procedure "
                 "and do NOT select AUTO."),
        ("6.11", "Record in the shift log: time of changeover, reason, which "
                 "pump is now lead, final vibration and bearing temperature "
                 "readings on the running pump, and the name of the "
                 "authorising Shift In-Charge."),
    ]
    for n, txt in steps:
        st.append(Paragraph(f"<b>{n}</b> &nbsp; {txt}", ST["step"]))

    st.append(Paragraph("7. ABNORMAL CONDITIONS", ST["h1"]))
    st.append(grid_table(
        ["Condition observed", "Immediate action"],
        [("Incoming pump does not develop discharge pressure",
          "Stop the pump. Do not re-attempt. Suspect vapour lock or a closed "
          "suction. Verify warm-up and suction line-up. Inform Shift In-Charge."),
         ("Bottoms level falls below the low alarm during transfer",
          "Halt valve movement. Restore flow on whichever pump is developing "
          "pressure. Reduce heater firing on F-2101 if the level continues to "
          "fall."),
         ("Visible hydrocarbon release at either seal",
          "Declare an emergency per the unit emergency response procedure. "
          "Stop the leaking pump only if the other pump is confirmed carrying "
          "flow. Activate area gas detection acknowledgement and clear "
          "non-essential personnel from the pump house."),
         ("Vibration on the incoming pump exceeds "
          f"{S.VIB_LIMITS['alert_mm_s']} mm/s after start",
          "Do not transfer load. Restore the original line-up. Raise a "
          "corrective work order and inform the Rotating Equipment Engineer."),
         ("Both pumps unavailable",
          "Reduce F-2101 firing and cut unit rate immediately. Bottoms level "
          "high-high will trip the heater; anticipate and control rather than "
          "allow the trip.")],
        [58 * mm, 116 * mm]))

    st.append(Paragraph("8. REFERENCED DOCUMENTS", ST["h1"]))
    st.append(grid_table(
        ["Document", "Title"],
        [(S.DOCS["std"]["id"], S.DOCS["std"]["title"]),
         (S.DOCS["hazop"]["id"], f"{S.DOCS['hazop']['title']} ({S.DOCS['hazop']['node']})"),
         (S.DOCS["vib"]["id"], S.DOCS["vib"]["title"]),
         (S.DOCS["circular"]["id"], S.DOCS["circular"]["title"]),
         (S.DOCS["pid"]["id"], S.DOCS["pid"]["title"])],
        [42 * mm, 132 * mm]))

    st.append(Paragraph("9. REVISION HISTORY", ST["h1"]))
    st.append(grid_table(
        ["Rev", "Date", "Change", "Approved by"],
        [("1", "2019-05-10", "First issue", "Head of Operations"),
         ("2", "2021-08-22", "Added seal support system pre-start check",
          "Head of Operations"),
         ("3", "2024-01-30", "Vibration limits aligned to ISO 10816-3; "
          "abnormal conditions table added", S.PLANT["short"] + " Ops"),
         ("4", d["effective"], "Warm-up duration increased to 30 minutes; "
          "discharge valve opening rate specified; hot work check added to "
          "pre-start", d["owner"]),
         ("5 (draft)", "under review",
          "Pending: mandatory laser alignment record with 0.05 mm tolerance "
          "before return to service. Arising from CAPA-0042-2 of "
          f"{S.DOCS['incident']['id']}.", "Not yet approved")],
        [16 * mm, 24 * mm, 104 * mm, 30 * mm]))
    return build_pdf(f"{d['id']}_{d['rev'].replace(' ', '')}_Pump_Changeover.pdf",
                     d["id"], d["title"], st)


# ===========================================================================
# 2. Incident investigation report (native text PDF)
# ===========================================================================
def build_incident():
    d = S.DOCS["incident"]
    I = S.INCIDENT
    st = []
    st += head("INCIDENT INVESTIGATION REPORT", f"{d['id']} &nbsp;|&nbsp; {d['title']}")
    st.append(meta_table([
        ("Incident No.", d["id"], "Severity", d["severity"]),
        ("Date / Time of event", I["occurred"], "Reported at", I["reported"]),
        ("Location", I["location"], "Equipment", I["equipment"]),
        ("Investigation lead", S.PEOPLE["reliability"], "Report date", "2026-08-31"),
    ]))
    st.append(Spacer(1, 8))

    st.append(Paragraph("1. SUMMARY OF EVENT", ST["h1"]))
    st.append(Paragraph(
        f"At {I['occurred']} the inboard mechanical seal of {I['equipment']}, "
        f"the running CDU-2 column bottoms pump, failed and released "
        f"{I['release_qty'].lower()} at {I['release_temp']} to atmosphere "
        f"within the pump house at {I['location'].split(', ')[-1]}. The "
        f"release was detected by the field operator on routine round and by "
        f"area gas detector GD-2104-1. Injuries: {I['injuries']}. "
        f"Fire: {I['fire']} The unit was transferred to P-2104A in accordance "
        f"with {S.DOCS['sop']['id']} {S.DOCS['sop']['rev']}.", ST["body"]))
    st.append(Paragraph(f"<b>Production impact.</b> {I['production_impact']}",
                        ST["body"]))

    st.append(Paragraph("2. SEQUENCE OF EVENTS", ST["h1"]))
    st.append(grid_table(
        ["Date / Time", "Event"],
        [("2026-07-31", "Monthly vibration round records 7.8 mm/s RMS on "
          "P-2104B, exceeding the 7.1 mm/s alert limit. Reading signed off "
          "with the remark 'monitor'. No corrective work order raised."),
         ("2026-08-27 23:40", "Night shift handover log records oil mist and "
          "weeping at the P-2104B seal area, and an API Plan 52 reservoir "
          "level of approximately 20% against a minimum of 40%. Reservoir "
          "manually topped up with 2 litres."),
         ("2026-08-27 00:30", "Handheld vibration reading of 9.4 mm/s RMS "
          "taken by the shift team. Rotating Equipment Engineer informed by "
          "telephone."),
         ("2026-08-27 01:10", "Advice given to continue monitoring and keep "
          "P-2104A ready for changeover. No work order raised."),
         ("2026-08-28", "Day shift monthly reading logged as 9.6 mm/s RMS. "
          "P-2104A confirmed on auto-start."),
         ("2026-08-29 03:40", "Seal failure and loss of containment. Area gas "
          "detector GD-2104-1 alarms at 18% LEL."),
         ("2026-08-29 03:52", "Event reported to the control room. Emergency "
          "declared at unit level. Fire water monitor coverage confirmed, no "
          "ignition."),
         ("2026-08-29 04:05", "Changeover to P-2104A completed. Unit rate cut "
          "to 85% during transfer."),
         ("2026-08-29 04:15", "Area gas tested clear. Emergency stood down."),
         ("2026-08-29 10:20", "P-2104B positively isolated and handed over to "
          "maintenance under work order WO-26-15118."),
         ("2026-09-02", "Seal replaced with kit SK-682-2104 taken from site "
          "stock. Laser alignment corrected from 0.19 mm to 0.03 mm parallel "
          "offset. Pump returned to standby.")],
        [30 * mm, 144 * mm]))

    st.append(PageBreak())
    st.append(Paragraph("3. IMMEDIATE CAUSE", ST["h1"]))
    st.append(Paragraph(I["immediate_cause"], ST["body"]))

    st.append(Paragraph("4. FIVE WHY ANALYSIS", ST["h1"]))
    st.append(grid_table(
        ["#", "Question", "Finding"],
        [(str(i + 1), q, a) for i, (q, a) in enumerate(I["five_why"])],
        [10 * mm, 60 * mm, 104 * mm]))

    st.append(Paragraph("5. ROOT CAUSES", ST["h1"]))
    for i, rc in enumerate(I["root_causes"], 1):
        st.append(Paragraph(f"5.{i} &nbsp; {rc}", ST["step"]))

    st.append(Paragraph("6. EVIDENCE EXAMINED", ST["h1"]))
    st.append(grid_table(
        ["Evidence", "Observation"],
        [("Failed seal faces (stationary and rotating)",
          "Circumferential heat checking on the stationary face over "
          "approximately 60% of the contact band. Secondary sealing element "
          "hardened and lost elasticity. Consistent with intermittent dry "
          "running."),
         ("Laser alignment measurement, as found",
          "Parallel offset 0.19 mm; angular deviation 0.11 mm per 100 mm. "
          "Specification is 0.05 mm and 0.05 mm per 100 mm respectively."),
         ("Coupling disc pack",
          "Two of six discs showed fatigue cracking at the bolt hole. "
          "Element replaced."),
         ("API Plan 52 reservoir",
          "Level at 22% on inspection. No level switch fitted. No routine "
          "check sheet entry exists for this item."),
         ("Vibration spectra, WO-26-11876 dated 2026-05-06",
          "1x running speed amplitude dominant with a 2x component at "
          "approximately 40% of 1x, and axial amplitude comparable to radial. "
          "Classic misalignment signature. Report recommended alignment check; "
          "no corrective work order was raised against the recommendation."),
         ("Bearings",
          "Thrust bearing pair showed early stage fatigue spalling on the "
          "loaded race. Replaced with stock item BRG-7314-BECBM."),
         ("Shift roster and competency records",
          "The Shift In-Charge on duty held a 'Pump Changeover - Hot Standby' "
          "certification that expired on 2026-07-31. The roster system does "
          "not check certification validity.")],
        [56 * mm, 118 * mm]))

    st.append(PageBreak())
    st.append(Paragraph("7. CORRECTIVE AND PREVENTIVE ACTIONS", ST["h1"]))
    st.append(grid_table(
        ["CAPA No.", "Action", "Owner", "Due", "Status", "Remarks"],
        [(a, b, c, dd, e, f) for (a, b, c, dd, e, f) in I["capa"]],
        [20 * mm, 62 * mm, 22 * mm, 20 * mm, 20 * mm, 30 * mm]))

    st.append(Paragraph("8. LESSONS AND WIDER APPLICABILITY", ST["h1"]))
    st.append(Paragraph(
        "The failure mechanism was not sudden. An alert level vibration "
        "reading existed for a full month before the loss of containment, and "
        "a diagnostic report identifying misalignment existed for almost four "
        "months. The controlling weakness is not detection but the absence of "
        "a mandatory link between a detected exceedance and executed work. "
        "This weakness is generic to all rotating equipment on the site and is "
        "not specific to CDU-2.", ST["body"]))
    st.append(Paragraph(
        "A screening review is recommended for all Criticality A pumps in "
        "service above 260 degC to confirm whether the installed seal "
        "arrangement matches current engineering practice. Refer "
        f"{S.DOCS['std']['id']} clause 4.1 and HAZOP action H7-04 of "
        f"{S.DOCS['hazop']['id']}.", ST["body"]))

    st.append(Paragraph("9. INVESTIGATION TEAM AND ENDORSEMENT", ST["h1"]))
    st.append(grid_table(
        ["Name", "Role in investigation", "Signature", "Date"],
        [(S.PEOPLE["reliability"], "Investigation lead", "Signed", "2026-08-31"),
         (S.PEOPLE["rot_eng"], "Technical member - rotating equipment",
          "Signed", "2026-08-31"),
         (S.PEOPLE["safety_officer"], "Technical member - process safety",
          "Signed", "2026-08-31"),
         (S.PEOPLE["shift_incharge"], "Witness statement provided",
          "Signed", "2026-08-30"),
         (S.PEOPLE["dgm_ops"], "Endorsing authority", "Signed", "2026-09-01")],
        [40 * mm, 74 * mm, 30 * mm, 30 * mm]))
    return build_pdf(f"{d['id']}_Seal_Failure_P-2104B.pdf", d["id"], d["title"], st)


# ===========================================================================
# 3. HAZOP action register (deliberately table-heavy PDF)
# ===========================================================================
def build_hazop():
    d = S.DOCS["hazop"]
    st = []
    st += head("HAZOP ACTION TRACKING REGISTER",
               f"{d['id']} &nbsp;|&nbsp; {d['node']} &nbsp;|&nbsp; {d['title']}")
    st.append(meta_table([
        ("Study reference", d["id"], "Node", d["node"]),
        ("Node description", "C-2101 bottoms nozzle to E-2107 outlet, "
         "including P-2104A/B", "Revalidation due", d["revalidation_due"]),
        ("Register extracted", "2026-09-03", "Facilitator", S.PEOPLE["safety_officer"]),
    ]))
    st.append(Spacer(1, 6))
    st.append(Paragraph(
        "Status summary: 2 Closed, 1 In Progress, 2 Not Started, "
        "<b>1 OVERDUE</b>. Overdue actions are reportable in the monthly "
        "process safety review.", ST["body"]))
    st.append(Spacer(1, 4))
    st.append(grid_table(
        ["Action", "Deviation", "Cause", "Consequence", "Existing safeguard",
         "Recommendation", "Owner", "Due", "Status"],
        S.HAZOP_ACTIONS,
        [13 * mm, 18 * mm, 22 * mm, 27 * mm, 27 * mm, 34 * mm, 15 * mm,
         + 17 * mm, 15 * mm]))
    st.append(Spacer(1, 8))
    st.append(Paragraph("NOTES ON OVERDUE ACTION H7-03", ST["h1"]))
    st.append(Paragraph(
        "The relief load recalculation for the blocked discharge scenario on "
        "the P-2104 discharge header indicates that the required relief "
        "capacity exceeds the installed capacity of PSV-2141 by an estimated "
        "8%. The valve was pop tested and recertified under WO-26-13001 on "
        "2026-06-15 and passed at its set pressure of 26.4 kg/cm2g, but a pop "
        "test confirms set pressure only and does not address capacity. "
        "Re-rating requires either an orifice change or a second valve, and "
        "the tie-in would fall within the zone restricted by "
        f"{S.DOCS['circular']['id']}.", ST["body"]))
    st.append(Paragraph(
        "Because this action is now more than 60 days past its due date of "
        "2026-06-30, it must be escalated to the Refinery Process Safety "
        "Committee with a revised target date and an interim risk statement.",
        ST["warn"]))
    return build_pdf(f"{d['id']}_{d['node'].replace(' ', '')}_Action_Register.pdf",
                     d["id"], d["title"], st)


# ===========================================================================
# 4. Safety circular (native text PDF)
# ===========================================================================
def build_circular():
    d = S.DOCS["circular"]
    C = S.CIRCULAR
    st = []
    st += head("SAFETY CIRCULAR", f"{d['id']} &nbsp;|&nbsp; {d['title']}")
    st.append(meta_table([
        ("Circular No.", d["id"], "Date of issue", d["issued"]),
        ("Issued by", f"{S.PEOPLE['safety_officer']}, Safety Officer",
         "Valid until", d["valid_to"]),
        ("Distribution", "All CDU-2 shift personnel, Maintenance, Contractors, "
         "Permit issuing authorities", "Arising from", S.DOCS["incident"]["id"]),
    ]))
    st.append(Spacer(1, 8))
    st.append(Paragraph("1. BACKGROUND", ST["h1"]))
    st.append(Paragraph(C["background"], ST["body"]))
    st.append(Paragraph("2. RESTRICTIONS IMPOSED", ST["h1"]))
    for i, r in enumerate(C["restrictions"], 1):
        st.append(Paragraph(f"2.{i} &nbsp; {r}", ST["step"]))
    st.append(Paragraph("3. VALIDITY", ST["h1"]))
    st.append(Paragraph(C["validity"], ST["body"]))
    st.append(Paragraph("4. ACKNOWLEDGEMENT", ST["h1"]))
    st.append(Paragraph(
        "All permit issuing authorities must acknowledge receipt of this "
        "circular before issuing any permit in the CDU-2 area. Contractor "
        "supervisors must brief their crews and record the briefing in the "
        "daily toolbox talk register.", ST["body"]))
    st.append(Spacer(1, 6))
    st.append(grid_table(
        ["Zone", "Equipment covered", "Hot work status"],
        [("CDU-2 bottoms circuit, 15 m radius",
          "P-2104A, P-2104B, E-2107, C-2101 bottoms line, PSV-2141",
          "SUSPENDED - deviation permit only"),
         ("CDU-2 pump house, remaining bays",
          "P-2101A/B, P-2107A", "Permitted with normal permit and gas test"),
         ("CDU-2 heater area", "F-2101", "Permitted with normal permit and gas test")],
        [52 * mm, 74 * mm, 48 * mm]))
    return build_pdf(f"{d['id']}_Hot_Work_Restriction_CDU2.pdf", d["id"],
                     d["title"], st)


# ===========================================================================
# 5. Monthly operations report (native text PDF with numeric tables)
# ===========================================================================
def build_ops_report():
    d = S.DOCS["ops"]
    O = S.OPS_REPORT
    st = []
    st += head("MONTHLY OPERATIONS PERFORMANCE REPORT",
               f"{d['id']} &nbsp;|&nbsp; {S.PLANT['unit_name']} &nbsp;|&nbsp; {O['period']}")
    st.append(meta_table([
        ("Report No.", d["id"], "Period", O["period"]),
        ("Unit", f"{S.PLANT['unit_code']} ({S.PLANT['capacity']})",
         "Prepared by", S.PEOPLE["planner"]),
        ("Reviewed by", S.PEOPLE["dgm_ops"], "Issue date", "2026-09-03"),
    ]))
    st.append(Spacer(1, 8))
    st.append(Paragraph("1. KEY PERFORMANCE INDICATORS", ST["h1"]))
    rows = []
    for p, u, t, a, prev in O["kpis"]:
        try:
            dev = float(a.replace(",", "")) - float(t.replace(",", ""))
            devs = f"{dev:+,.2f}"
        except ValueError:
            devs = "-"
        rows.append((p, u, t, a, prev, devs))
    st.append(grid_table(
        ["Parameter", "Unit", "Target", "Actual", "Jul 2026", "Deviation"],
        rows, [58 * mm, 24 * mm, 22 * mm, 22 * mm, 22 * mm, 26 * mm]))

    st.append(Paragraph("2. PRODUCTION LOSS AND DOWNTIME", ST["h1"]))
    total = sum(h for _, _, h, _ in O["downtime"])
    st.append(grid_table(
        ["Date", "Description", "Hours lost", "Category"],
        [(a, b, f"{c:.2f}", dd) for a, b, c, dd in O["downtime"]] +
        [("", "TOTAL", f"{total:.2f}", "")],
        [22 * mm, 106 * mm, 22 * mm, 24 * mm]))

    st.append(Paragraph("3. NARRATIVE", ST["h1"]))
    for para in O["narrative"].split("\n\n"):
        st.append(Paragraph(para, ST["body"]))

    st.append(Paragraph("4. RELIABILITY AND SAFETY ITEMS CARRIED FORWARD", ST["h1"]))
    st.append(grid_table(
        ["Item", "Reference", "Status", "Target"],
        [("Overdue HAZOP action - PSV-2141 relief capacity re-rating",
          f"{S.DOCS['hazop']['id']} H7-03", "OVERDUE since 2026-06-30",
          "To be re-baselined"),
         ("Seal upgrade on column bottoms pumps",
          S.DOCS["moc"]["id"], S.DOCS["moc"]["status"],
          S.DOCS["moc"]["target_completion"]),
         ("Incident CAPA closure", f"{S.DOCS['incident']['id']} CAPA 1-5",
          "1 of 5 complete", "2026-10-01"),
         ("E-2107 preheat train fouling", "Monitoring only",
          "Third consecutive month adverse", "Next mini shutdown"),
         ("Operator competency re-certification", S.DOCS["training"]["id"],
          "2 of 6 shift in-charges lapsed", "2026-09-30")],
        [58 * mm, 34 * mm, 46 * mm, 36 * mm]))
    return build_pdf(f"{d['id']}_CDU2_Monthly_Report_Aug2026.pdf", d["id"],
                     d["title"], st)


# ===========================================================================
# 6. Internal engineering standard summary (native text PDF)
# ===========================================================================
def build_std_summary():
    d = S.DOCS["std"]
    T = S.STD_SUMMARY
    st = []
    st += head("INTERNAL ENGINEERING PRACTICE SUMMARY",
               f"{d['id']} &nbsp;|&nbsp; {d['title']}")
    st.append(meta_table([
        ("Document No.", d["id"], "Issue", "Issue 2, 2026-04-01"),
        ("Prepared by", f"{S.PEOPLE['rot_eng']}, Rotating Equipment",
         "Applicable to", "All units, pumps above 250 degC"),
    ]))
    st.append(Spacer(1, 8))
    st.append(Paragraph("SCOPE AND STATUS OF THIS DOCUMENT", ST["h1"]))
    st.append(Paragraph(T["scope"], ST["body"]))
    st.append(Paragraph(
        "This is an internal interpretation for training and prototype use. "
        "Where it differs from a governing external standard or statutory "
        "requirement, the external requirement prevails.", ST["warn"]))
    st.append(Paragraph("CONSOLIDATED REQUIREMENTS", ST["h1"]))
    st.append(grid_table(
        ["Clause", "Subject", "Requirement"],
        T["clauses"], [16 * mm, 34 * mm, 124 * mm]))
    st.append(Spacer(1, 8))
    st.append(Paragraph("APPLICATION TO CDU-2 COLUMN BOTTOMS PUMPS", ST["h1"]))
    st.append(grid_table(
        ["Clause", "Requirement", "P-2104A/B as installed", "Compliant?"],
        [("4.1", "Dual seal, Arrangement 3 default",
          "Category 1, Arrangement 1 (single unpressurised)", "NO"),
         ("4.2", "Plan 53B or 53C with DCS transmission",
          "Plan 52 external reservoir, manually replenished, no level switch",
          "NO"),
         ("4.3", "Laser alignment, 0.05 mm parallel max",
          "0.03 mm as left on 2026-09-02; was 0.19 mm as found", "YES (as left)"),
         ("5.1", "Corrective work order within 24 h of a 7.1 mm/s reading",
          "7.8 mm/s recorded 2026-07-31, no work order raised", "NO"),
         ("5.2", "Bearing alarm 85 degC, trip 95 degC",
          "Alarm configured at 85 degC; no trip configured", "PARTIAL"),
         ("6.1", "Two seal kits per pump pair in stock",
          "1 x SK-682-2104 and 0 x SK-682-2104-A3 in stock", "NO"),
         ("6.2", "Standby warm, lined up, test run every 14 days",
          "Complied; last test run of standby 2026-08-18", "YES")],
        [16 * mm, 48 * mm, 84 * mm, 26 * mm]))
    return build_pdf(f"{d['id']}_Hot_Service_Pump_Practice.pdf", d["id"],
                     d["title"], st)
