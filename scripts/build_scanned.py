"""
build_scanned.py — the two image-based members of the corpus.

1. A "scanned" shift handover log: a printed form with hand-written entries,
   then degraded the way a real office scanner degrades a page (skew, blur,
   speckle, uneven lighting, JPEG artefacts, punch holes, a staple shadow).
   This document has NO extractable text layer, so it forces the OCR branch of
   the pipeline. It is the document to put on screen when a judge asks whether
   the system can handle real plant paperwork.

2. A simplified P&ID-style flow schematic as a PNG, for the vision-model branch.

Both are generated with Pillow only, so there is no Poppler / Ghostscript /
ImageMagick dependency to install.
"""

import io
import math
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import corpus_spec as S  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "documents"
OUT.mkdir(parents=True, exist_ok=True)

DPI = 200
W, H = int(8.27 * DPI), int(11.69 * DPI)  # A4 at 200 dpi

FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/liberation2",
    "C:/Windows/Fonts",
    "/System/Library/Fonts/Supplemental",
]


def _font(names, size):
    """Find the first available font from a list of candidate filenames."""
    for d in FONT_DIRS:
        for n in names:
            p = Path(d) / n
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size)
                except OSError:
                    continue
    return ImageFont.load_default()


PRINT_B = lambda s: _font(["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf",
                           "arialbd.ttf"], s)
PRINT_R = lambda s: _font(["DejaVuSans.ttf", "LiberationSans-Regular.ttf",
                           "arial.ttf"], s)
# Oblique serif reads as "hand filled" once we add per-character jitter
HAND = lambda s: _font(["DejaVuSerif-Italic.ttf", "LiberationSerif-Italic.ttf",
                        "DejaVuSans-Oblique.ttf", "ariali.ttf"], s)


def _hand_text(draw, xy, text, size=25, colour=(28, 42, 92), jitter=1.6,
               max_width=None):
    """Draw text character by character with slight jitter and rotation drift
    so it reads as hand printing rather than a font. Wraps on max_width."""
    f = HAND(size)
    x0, y0 = xy
    x, y = x0, y0
    baseline_drift = 0.0
    for word in text.split(" "):
        wlen = draw.textlength(word + " ", font=f)
        if max_width and (x - x0) + wlen > max_width:
            x = x0
            y += size * 1.45
            baseline_drift = 0.0
        for ch in word:
            dy = random.uniform(-jitter, jitter) + baseline_drift
            dx = random.uniform(-jitter * 0.4, jitter * 0.4)
            c = (colour[0] + random.randint(-14, 14),
                 colour[1] + random.randint(-14, 14),
                 colour[2] + random.randint(-14, 14))
            draw.text((x + dx, y + dy), ch, font=f, fill=c)
            x += draw.textlength(ch, font=f) + random.uniform(-0.3, 0.7)
        x += draw.textlength(" ", font=f)
        baseline_drift += random.uniform(-0.35, 0.35)
        baseline_drift = max(-2.5, min(2.5, baseline_drift))
    return y + size * 1.45


def build_handover_scanned():
    """Printed form + hand entries, then scanner degradation, saved as PDF."""
    d = S.DOCS["handover"]
    Hv = S.HANDOVER
    random.seed(4242)

    img = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(img)

    ink = (35, 35, 40)
    m = 110  # margin

    # ---- printed form: masthead -------------------------------------------
    dr.rectangle([m, 90, W - m, 250], outline=ink, width=3)
    dr.text((m + 18, 108), S.PLANT["company"].upper(), font=PRINT_B(26), fill=ink)
    dr.text((m + 18, 146), f"{S.PLANT['unit_name']}  ({S.PLANT['unit_code']})",
            font=PRINT_R(21), fill=ink)
    dr.text((m + 18, 178), "SHIFT HANDOVER LOG  -  FORM OPS/CDU2/F-07 Rev 2",
            font=PRINT_B(22), fill=ink)
    dr.text((m + 18, 210), S.PLANT["doc_class"], font=PRINT_R(15),
            fill=(120, 30, 30))
    dr.text((W - m - 250, 108), d["id"], font=PRINT_B(20), fill=ink)
    dr.text((W - m - 250, 138), "Page 1 of 1", font=PRINT_R(16), fill=ink)

    # ---- printed form: identification boxes -------------------------------
    y = 275
    boxh = 58
    fields = [
        ("DATE", Hv["date"], 0.0, 0.30),
        ("SHIFT", Hv["shift"], 0.30, 0.70),
    ]
    for label, value, fx, fw in fields:
        x0 = m + int((W - 2 * m) * fx)
        x1 = m + int((W - 2 * m) * (fx + fw))
        dr.rectangle([x0, y, x1, y + boxh], outline=ink, width=2)
        dr.text((x0 + 10, y + 8), label, font=PRINT_B(15), fill=ink)
        _hand_text(dr, (x0 + 14, y + 26), value, size=24)
    y += boxh
    fields2 = [
        ("OUTGOING SHIFT IN-CHARGE", Hv["outgoing"], 0.0, 0.5),
        ("INCOMING SHIFT IN-CHARGE", Hv["incoming"], 0.5, 0.5),
    ]
    for label, value, fx, fw in fields2:
        x0 = m + int((W - 2 * m) * fx)
        x1 = m + int((W - 2 * m) * (fx + fw))
        dr.rectangle([x0, y, x1, y + boxh], outline=ink, width=2)
        dr.text((x0 + 10, y + 8), label, font=PRINT_B(15), fill=ink)
        _hand_text(dr, (x0 + 14, y + 26), value, size=24)
    y += boxh + 26

    # ---- printed form: log table ------------------------------------------
    dr.text((m, y), "SECTION A - CHRONOLOGICAL LOG OF EVENTS",
            font=PRINT_B(19), fill=ink)
    y += 32
    tcol = m + 150
    dr.rectangle([m, y, W - m, y + 40], outline=ink, width=2)
    dr.line([tcol, y, tcol, y + 40], fill=ink, width=2)
    dr.text((m + 30, y + 11), "TIME", font=PRINT_B(16), fill=ink)
    dr.text((tcol + 20, y + 11), "OBSERVATION / ACTION TAKEN",
            font=PRINT_B(16), fill=ink)
    y += 40

    rowh = 118
    for t, txt in Hv["rows"]:
        dr.rectangle([m, y, W - m, y + rowh], outline=ink, width=1)
        dr.line([tcol, y, tcol, y + rowh], fill=ink, width=1)
        # faint ruled writing lines inside the cell
        for k in range(1, 3):
            dr.line([tcol + 12, y + k * 38, W - m - 12, y + k * 38],
                    fill=(205, 205, 210), width=1)
        _hand_text(dr, (m + 26, y + 40), t, size=25)
        _hand_text(dr, (tcol + 18, y + 16), txt, size=24,
                   max_width=W - m - tcol - 44)
        y += rowh

    # ---- printed form: standby status section -----------------------------
    y += 22
    dr.text((m, y), "SECTION B - STANDBY EQUIPMENT STATUS",
            font=PRINT_B(19), fill=ink)
    y += 32
    dr.rectangle([m, y, W - m, y + 100], outline=ink, width=2)
    _hand_text(dr, (m + 18, y + 16), Hv["notes"], size=24,
               max_width=W - 2 * m - 40)

    # ---- printed form: sign-off ------------------------------------------
    y += 124
    dr.text((m, y), "SECTION C - SIGN OFF", font=PRINT_B(19), fill=ink)
    y += 30
    for label, name, fx in [("Outgoing (sign)", Hv["outgoing"], 0.0),
                            ("Incoming (sign)", Hv["incoming"], 0.5)]:
        x0 = m + int((W - 2 * m) * fx)
        x1 = x0 + int((W - 2 * m) * 0.46)
        dr.line([x0, y + 62, x1, y + 62], fill=ink, width=2)
        dr.text((x0, y + 68), label, font=PRINT_R(15), fill=ink)
        # scrawled signature: a couple of random bezier-ish strokes
        sx, sy = x0 + 24, y + 46
        pts = [(sx, sy)]
        for k in range(9):
            pts.append((sx + 22 * k + random.randint(-7, 7),
                        sy - random.randint(0, 30) + random.randint(-8, 8)))
        dr.line(pts, fill=(22, 34, 96), width=3, joint="curve")
        dr.text((x0 + 230, y + 30), name, font=HAND(20), fill=(22, 34, 96))

    # ---- printed footer ---------------------------------------------------
    dr.text((m, H - 120), "Form OPS/CDU2/F-07 Rev 2  -  retain for 3 years",
            font=PRINT_R(14), fill=(90, 90, 90))
    dr.text((m, H - 96), S.PLANT["synthetic_notice"], font=PRINT_R(13),
            fill=(140, 140, 140))

    # =======================================================================
    # Scanner degradation. Order matters: geometry, then optics, then sensor.
    # =======================================================================
    # punch holes on the left edge
    for cy in (int(H * 0.30), int(H * 0.50), int(H * 0.70)):
        dr.ellipse([34, cy - 26, 86, cy + 26], fill=(246, 246, 246),
                   outline=(200, 200, 200), width=2)

    # staple shadow, top left
    dr.line([(120, 62), (172, 96)], fill=(150, 150, 150), width=5)

    # slight skew, as fed through a sheet feeder
    img = img.rotate(-0.65, resample=Image.BICUBIC, expand=False,
                     fillcolor=(255, 255, 255))

    # lens softness
    img = img.filter(ImageFilter.GaussianBlur(radius=0.65))

    # uneven platen lighting: darker toward the binding edge
    grad = Image.new("L", (W, H), 255)
    gd = ImageDraw.Draw(grad)
    for x in range(0, W, 4):
        shade = 255 - int(30 * math.exp(-x / (W * 0.10)))
        gd.rectangle([x, 0, x + 4, H], fill=shade)
    for yy in range(0, H, 4):
        pass
    img = Image.composite(img, Image.new("RGB", (W, H), (198, 198, 196)),
                          grad.point(lambda v: 255 if v > 246 else v))

    # paper tint + sensor speckle
    px = img.load()
    for _ in range(int(W * H * 0.0022)):
        x, y_ = random.randrange(W), random.randrange(H)
        v = random.randint(120, 205)
        px[x, y_] = (v, v, v - random.randint(0, 8))
    # a few dust specks
    d2 = ImageDraw.Draw(img)
    for _ in range(38):
        x, y_ = random.randrange(W), random.randrange(H)
        r = random.randint(1, 3)
        d2.ellipse([x, y_, x + r, y_ + r], fill=(105, 105, 105))
    # scanner streak
    d2.line([(int(W * 0.72), 0), (int(W * 0.72), H)], fill=(232, 230, 228),
            width=3)

    img = img.convert("L").convert("RGB")  # greyscale scan

    # JPEG generation loss, then back to a PDF page. Done entirely in memory:
    # writing a temp file into the corpus folder would leave a stray document
    # behind, because PIL keeps the handle open and the unlink fails on Windows.
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=62)
    buf.seek(0)
    img = Image.open(buf).convert("RGB")

    path = OUT / f"{d['id']}_Shift_Handover_SCANNED.pdf"
    img.save(str(path), "PDF", resolution=DPI)
    return path


# ===========================================================================
# P&ID-style schematic
# ===========================================================================
def build_pid_png():
    d = S.DOCS["pid"]
    w, h = 1750, 1320
    img = Image.new("RGB", (w, h), (252, 252, 250))
    dr = ImageDraw.Draw(img)
    ink = (30, 30, 35)
    line = (45, 60, 90)
    inst = (20, 60, 130)
    warn = (150, 80, 10)
    fb, fr, fs = PRINT_B(22), PRINT_R(19), PRINT_R(15)

    # ---- sheet border and title block -------------------------------------
    dr.rectangle([12, 12, w - 12, h - 12], outline=ink, width=3)
    tb_y = h - 150
    dr.rectangle([12, tb_y, w - 12, h - 12], outline=ink, width=3)
    dr.line([(w - 620, tb_y), (w - 620, h - 12)], fill=ink, width=2)
    dr.text((32, tb_y + 16), S.PLANT["company"], font=fb, fill=ink)
    dr.text((32, tb_y + 48), f"{S.PLANT['unit_name']} ({S.PLANT['unit_code']})",
            font=fr, fill=ink)
    dr.text((32, tb_y + 76), d["title"], font=fr, fill=ink)
    dr.text((32, tb_y + 108), S.PLANT["synthetic_notice"], font=fs,
            fill=(140, 140, 140))
    dr.text((w - 600, tb_y + 16), f"DRAWING No.  {d['id']}", font=fb, fill=ink)
    dr.text((w - 600, tb_y + 48), "REV  3        SCALE  NTS", font=fr, fill=ink)
    dr.text((w - 600, tb_y + 76), "DATE  2026-04-12", font=fr, fill=ink)
    dr.text((w - 600, tb_y + 104), f"APPROVED  {S.PEOPLE['rot_eng']}",
            font=fr, fill=ink)
    dr.text((40, 34), "SIMPLIFIED FLOW SCHEMATIC  -  COLUMN BOTTOMS CIRCUIT",
            font=fb, fill=ink)
    dr.text((40, 66), f"{S.PLANT['doc_class']}", font=fs, fill=(140, 30, 30))

    # ---- primitives --------------------------------------------------------
    def tag(x, y, text, sub=None):
        dr.text((x, y), text, font=fb, fill=(140, 20, 20))
        if sub:
            dr.text((x, y + 26), sub, font=fs, fill=(70, 70, 70))

    def pipe(pts, width=5, colour=None):
        dr.line(pts, fill=colour or line, width=width, joint="curve")

    def arrow(x, y, direction="r", size=14):
        if direction == "r":
            dr.polygon([(x, y - size // 2), (x + size, y), (x, y + size // 2)],
                       fill=line)
        elif direction == "d":
            dr.polygon([(x - size // 2, y), (x, y + size), (x + size // 2, y)],
                       fill=line)
        else:
            dr.polygon([(x, y - size // 2), (x - size, y), (x, y + size // 2)],
                       fill=line)

    def valve(x, y, size=20):
        dr.polygon([(x - size, y - size), (x + size, y + size),
                    (x - size, y + size), (x + size, y - size)],
                   outline=line, width=3, fill=(252, 252, 250))

    def nrv(x, y):
        dr.rectangle([x, y - 22, x + 50, y + 22], outline=line, width=3,
                     fill=(252, 252, 250))
        dr.polygon([(x + 6, y + 16), (x + 44, y - 16), (x + 44, y + 16)],
                   fill=line)

    def bubble(x, y, top, bot, colour=inst, r=30):
        dr.ellipse([x - r, y - r, x + r, y + r], outline=colour, width=3,
                   fill=(252, 252, 250))
        dr.text((x - dr.textlength(top, font=fs) / 2, y - 21), top, font=fs,
                fill=colour)
        dr.text((x - dr.textlength(bot, font=fs) / 2, y + 1), bot, font=fs,
                fill=colour)

    def pump(cx, cy, label, running):
        r = 52
        fill = (214, 236, 214) if running else (238, 238, 238)
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ink, width=4,
                   fill=fill)
        dr.polygon([(cx - 14, cy - 26), (cx + 30, cy), (cx - 14, cy + 26)],
                   fill=(90, 90, 95))
        tag(cx - 50, cy + r + 10, label)
        dr.text((cx - 48, cy + r + 38), "RUNNING" if running else "STANDBY",
                font=fs, fill=((20, 110, 20) if running else (130, 130, 130)))

    # ---- C-2101 column ----------------------------------------------------
    cx0, cy0, cx1, cy1 = 90, 130, 258, 620
    dr.rounded_rectangle([cx0, cy0, cx1, cy1], radius=68, outline=ink, width=4,
                         fill=(238, 242, 246))
    for ty in range(cy0 + 95, cy1 - 55, 42):
        dr.line([(cx0 + 14, ty), (cx1 - 14, ty)], fill=(160, 165, 175), width=2)
    tag(cx0 + 4, cy1 + 14, "C-2101", "Atmos. Distillation Column, 42 trays")
    dr.text((cx0 + 14, cy0 + 18), "TOP", font=fs, fill=(70, 70, 70))
    dr.text((cx0 + 6, cy1 - 44), "FLASH ZONE", font=fs, fill=(70, 70, 70))
    dr.text((cx1 + 14, cy0 + 44), "TI-2101   118 degC", font=fs, fill=inst)
    dr.text((cx1 + 14, cy1 - 92), "TI-2102   352 degC", font=fs, fill=inst)
    bubble(cx1 + 62, cy1 - 190, "LIC", "2101")
    dr.line([(cx1, cy1 - 190), (cx1 + 32, cy1 - 190)], fill=inst, width=2)

    # ---- bottoms line to the pump suction header --------------------------
    hy = 700
    pipe([(cx0 + 84, cy1), (cx0 + 84, hy)])
    arrow(cx0 + 84, hy - 56, "d")
    pipe([(cx0 + 84, hy), (560, hy)])
    dr.text((430, hy - 44), "RCO  345 degC", font=fs, fill=(70, 70, 70))
    dr.text((300, hy + 16), '10"-RC-2101-A1A', font=fs, fill=(70, 70, 70))

    pA_x, pA_y = 700, 640
    pB_x, pB_y = 700, 900
    pipe([(560, hy), (560, pA_y), (pA_x - 52, pA_y)])
    pipe([(560, hy), (560, pB_y), (pB_x - 52, pB_y)])
    valve(618, pA_y)
    valve(618, pB_y)
    dr.text((588, pA_y - 62), "SUCTION", font=fs, fill=(70, 70, 70))
    dr.text((588, pB_y + 36), "SUCTION", font=fs, fill=(70, 70, 70))

    pump(pA_x, pA_y, "P-2104A", running=True)
    pump(pB_x, pB_y, "P-2104B", running=False)

    # ---- discharge legs ---------------------------------------------------
    HDR_X = 1130
    for (px_, py_, nm, above) in ((pA_x, pA_y, "NRV-2104A", True),
                                  (pB_x, pB_y, "NRV-2104B", False)):
        pipe([(px_ + 52, py_), (px_ + 150, py_)])
        nrv(px_ + 150, py_)
        dr.text((px_ + 146, py_ + (-56 if above else 32)), nm, font=fs,
                fill=(70, 70, 70))
        pipe([(px_ + 200, py_), (px_ + 300, py_)])
        valve(px_ + 330, py_)
        dr.text((px_ + 296, py_ + (-58 if above else 34)), "DISCHARGE",
                font=fs, fill=(70, 70, 70))
        pipe([(px_ + 360, py_), (HDR_X, py_)])
        arrow(px_ + 285, py_, "r")

    pipe([(HDR_X, pA_y), (HDR_X, pB_y)])
    mid = (pA_y + pB_y) // 2
    dr.text((HDR_X - 156, mid - 62), "COMMON DISCHARGE", font=fs,
            fill=(70, 70, 70))
    dr.text((HDR_X - 156, mid - 38), "HEADER  Design 24 kg/cm2g", font=fs,
            fill=(70, 70, 70))

    # ---- PSV-2141 on the header ------------------------------------------
    pipe([(HDR_X, mid), (1206, mid)])
    dr.polygon([(1206, mid - 28), (1264, mid), (1206, mid + 28)], outline=ink,
               width=3, fill=(255, 236, 200))
    dr.line([(1264, mid), (1264, mid - 82)], fill=line, width=5)
    dr.line([(1240, mid - 82), (1288, mid - 82)], fill=line, width=5)
    dr.text((1298, mid - 96), "TO FLARE", font=fs, fill=(70, 70, 70))
    tag(1196, mid + 42, "PSV-2141", "Set 26.4 kg/cm2g")

    # ---- header up to E-2107 ---------------------------------------------
    pipe([(HDR_X, pA_y), (HDR_X, 420)])
    arrow(HDR_X, 470, "u" if False else "d")
    dr.polygon([(HDR_X - 7, 500), (HDR_X, 486), (HDR_X + 7, 500)], fill=line)
    pipe([(HDR_X, 420), (1330, 420)])
    arrow(1300, 420, "r")

    ex0, ey0, ex1, ey1 = 1330, 320, 1616, 500
    dr.rectangle([ex0, ey0, ex1, ey1], outline=ink, width=4,
                 fill=(240, 244, 248))
    for k in range(4):
        yy = ey0 + 34 + k * 30
        dr.line([(ex0 + 20, yy), (ex1 - 20, yy)], fill=(150, 155, 165), width=3)
    tag(ex0 + 2, ey1 + 14, "E-2107", "Crude / RCO Heat Exchanger")
    dr.text((ex0 + 8, ey0 - 34), "SHELL: RCO      TUBE: CRUDE", font=fs,
            fill=(70, 70, 70))
    bubble(ex1 + 52, ey0 + 34, "TAH", "2107")

    # crude side
    pipe([(1240, ey1 - 40), (ex0, ey1 - 40)])
    arrow(ex0 - 34, ey1 - 40, "r")
    dr.text((1240, ey1 - 74), "CRUDE IN", font=fs, fill=(70, 70, 70))
    pipe([(ex0 + 210, ey0), (ex0 + 210, 214), (1704, 214)])
    arrow(1690, 214, "r")
    dr.text((1360, 178), "CRUDE OUT  ->  F-2101", font=fs, fill=(70, 70, 70))

    # RCO product out
    pipe([(ex1, ey1 - 60), (1704, ey1 - 60), (1704, 640)])
    arrow(1704, 618, "d")
    dr.text((1452, 660), "RCO TO SECONDARY", font=fs, fill=(70, 70, 70))
    dr.text((1452, 684), "UNITS   160 degC", font=fs, fill=(70, 70, 70))

    # ---- gas detectors ----------------------------------------------------
    bubble(880, pA_y - 150, "GD", "", colour=(140, 20, 20), r=28)
    dr.text((836, pA_y - 118), "GD-2104-1", font=fs, fill=(140, 20, 20))
    dr.line([(880, pA_y - 122), (880, pA_y - 26)], fill=(140, 20, 20), width=2)
    bubble(1010, pB_y + 132, "GD", "", colour=(140, 20, 20), r=28)
    dr.text((966, pB_y + 166), "GD-2104-2", font=fs, fill=(140, 20, 20))
    dr.line([(1010, pB_y + 22), (1010, pB_y + 104)], fill=(140, 20, 20),
            width=2)

    # ---- seal support system: the subject of the MOC ----------------------
    bx0, by0, bx1, by1 = 300, 1046, 610, 1128
    dr.rectangle([bx0, by0, bx1, by1], outline=warn, width=3,
                 fill=(255, 246, 230))
    dr.text((bx0 + 12, by0 + 12), "API PLAN 52 RESERVOIR", font=fs, fill=warn)
    dr.text((bx0 + 12, by0 + 38), "MANUAL TOP-UP - NO LEVEL SWITCH", font=fs,
            fill=warn)
    pipe([(bx1, by0 + 20), (pB_x - 20, by0 + 20), (pB_x - 20, pB_y + 52)],
         width=3, colour=warn)
    dr.text((bx1 + 96, by0 + 12), "TO BE REPLACED BY PLAN 53B", font=fs,
            fill=warn)
    dr.text((bx1 + 96, by0 + 38), f"UNDER {S.DOCS['moc']['id']}", font=fs,
            fill=warn)

    # ---- legend -----------------------------------------------------------
    lx, ly = 1352, 760
    dr.rectangle([lx, ly, lx + 352, ly + 214], outline=ink, width=2,
                 fill=(248, 248, 246))
    dr.text((lx + 14, ly + 12), "LEGEND", font=fb, fill=ink)
    for i, (txt, kind) in enumerate([
            ("Gate / isolation valve", "valve"),
            ("Non-return valve", "nrv"),
            ("Pressure safety valve", "psv"),
            ("Instrument loop", "inst"),
            ("Seal support (to be replaced)", "seal")]):
        yy = ly + 56 + i * 32
        if kind == "valve":
            valve(lx + 34, yy, size=12)
        elif kind == "nrv":
            dr.rectangle([lx + 18, yy - 12, lx + 50, yy + 12], outline=line,
                         width=2)
            dr.polygon([(lx + 22, yy + 9), (lx + 46, yy - 9),
                        (lx + 46, yy + 9)], fill=line)
        elif kind == "psv":
            dr.polygon([(lx + 20, yy - 12), (lx + 48, yy), (lx + 20, yy + 12)],
                       outline=ink, width=2, fill=(255, 236, 200))
        elif kind == "inst":
            dr.ellipse([lx + 20, yy - 13, lx + 48, yy + 13], outline=inst,
                       width=2)
        else:
            dr.rectangle([lx + 20, yy - 11, lx + 48, yy + 11], outline=warn,
                         width=2, fill=(255, 246, 230))
        dr.text((lx + 66, yy - 10), txt, font=fs, fill=ink)

    path = OUT / f"{d['id']}_Column_Bottoms_Schematic.png"
    img.save(str(path), "PNG", dpi=(150, 150))
    return path
