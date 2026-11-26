"""Builds "User Guide.pdf" (Help > User Guide) from the pictures and example values in docs/images.

    python docs/make_user_guide.py          (needs reportlab and pillow: pip install -r docs/requirements.txt)

Run docs/capture_screens.py first when the program changes, so the pictures and numbers are current.
The worked examples are calculated here again by hand (NCRP 147 formulas) and checked against the program.
"""
import json
import math
import os
import sys
from datetime import date

from openpyxl import load_workbook
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, ListFlowable, ListItem,
                                NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(ROOT, "docs", "images")
OUTPUT = os.path.join(ROOT, "User Guide.pdf")
EXCEL = os.path.join(ROOT, "Data Shielding.xlsx")
ICON = os.path.join(ROOT, "XRIFSC_code", "app_icon.png")
VALUES = json.load(open(os.path.join(IMAGES, "example_values.json"), encoding="utf-8"))

# ===================== look =====================
NAVY, ACCENT, TEXT, MUTED = "#14212e", "#1a73c8", "#121b25", "#4b5866"
NOTE_BG, NOTE_EDGE, RULE, ROW_BG = "#fff8d6", "#e3cf7a", "#c9d3de", "#f2f5f8"
OK, BAD = "#2e7d32", "#c62828"
FONTS = "C:/Windows/Fonts"


def register_fonts():
    faces = {"Body": "segoeui.ttf", "Body-Bold": "segoeuib.ttf", "Body-Italic": "segoeuii.ttf",
             "Body-BoldItalic": "segoeuiz.ttf", "Semibold": "seguisb.ttf", "Light": "segoeuil.ttf",
             "SegoeSymbol": "seguisym.ttf", "Mono": "consola.ttf"}
    for name, file in faces.items():
        pdfmetrics.registerFont(TTFont(name, os.path.join(FONTS, file)))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic",
                                  boldItalic="Body-BoldItalic")


register_fonts()
WIDTH = A4[0] - 40 * mm  # text width

S = {
    "body": ParagraphStyle("body", fontName="Body", fontSize=10, leading=14.2, textColor=TEXT, spaceAfter=5),
    "small": ParagraphStyle("small", fontName="Body", fontSize=8.6, leading=11.6, textColor=MUTED),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=8.8, leading=11.4, textColor=TEXT),
    "cellb": ParagraphStyle("cellb", fontName="Body-Bold", fontSize=8.8, leading=11.4, textColor=TEXT),
    "head": ParagraphStyle("head", fontName="Semibold", fontSize=8.8, leading=11.4, textColor="white"),
    "caption": ParagraphStyle("caption", fontName="Body-Italic", fontSize=8.6, leading=11.4, textColor=MUTED,
                              alignment=TA_CENTER, spaceBefore=3, spaceAfter=10),
    "H1": ParagraphStyle("H1", fontName="Semibold", fontSize=19, leading=24, textColor=NAVY, spaceBefore=4,
                         spaceAfter=10),
    "H2": ParagraphStyle("H2", fontName="Semibold", fontSize=13.5, leading=18, textColor=NAVY, spaceBefore=12,
                         spaceAfter=5),
    "H3": ParagraphStyle("H3", fontName="Body-Bold", fontSize=10.5, leading=14, textColor=TEXT, spaceBefore=8,
                         spaceAfter=3),
    "formula": ParagraphStyle("formula", fontName="Body", fontSize=11.5, leading=22, textColor=TEXT,
                              alignment=TA_CENTER),
    "note": ParagraphStyle("note", fontName="Body", fontSize=9.4, leading=13, textColor=TEXT),
    "toc1": ParagraphStyle("toc1", fontName="Body-Bold", fontSize=10.5, leading=15.5, textColor=NAVY, spaceBefore=3),
    "toc2": ParagraphStyle("toc2", fontName="Body", fontSize=9.6, leading=13, leftIndent=14, textColor=TEXT),
}


def sym(char):
    """Characters that Segoe UI lacks (check marks), from Segoe UI Symbol."""
    return f'<font name="SegoeSymbol">{char}</font>'


MET, EXCEEDED = f'<font color="{OK}">{sym("✓")} met</font>', f'<font color="{BAD}">{sym("✗")} exceeded</font>'


def P(text, style="body"):
    return Paragraph(text, S[style])


class Heading(Paragraph):
    """A heading that goes into the contents and the PDF bookmarks."""

    def __init__(self, text, level, key):
        super().__init__(text, S[f"H{level}"])
        self.level, self.key, self.plain = level, key, text


counters = {"section": 0, "sub": 0, "figure": 0, "table": 0}
FIGURES = {}  # figure key -> number, from a first pass over the content


def fig(key):
    return f"Figure {FIGURES.get(key, '?')}"


SECTIONS = {}  # heading -> its number, from a first pass over the content
UNKNOWN = set()  # headings referred to that do not exist


def sec(title):
    """The number of the section with this heading, e.g. '2.7'."""
    if title not in SECTIONS:
        UNKNOWN.add(title)
    return SECTIONS.get(title, "?")


def H1(text):
    counters["section"] += 1
    counters["sub"] = 0
    SECTIONS[text] = str(counters["section"])
    return [CondPageBreak(60 * mm), Heading(f"{counters['section']}&nbsp;&nbsp;{text}", 1,
                                            f"s{counters['section']}")]


def H2(text):
    counters["sub"] += 1
    number = f"{counters['section']}.{counters['sub']}"
    SECTIONS[text] = number
    return [CondPageBreak(35 * mm), Heading(f"{number}&nbsp;&nbsp;{text}", 2, f"s{number}")]


def H3(text):
    return P(text, "H3")


def bullets(items, style="body"):
    return ListFlowable([ListItem(P(item, style), leftIndent=12, value="•") for item in items], bulletType="bullet",
                        start="•", leftIndent=12, bulletFontName="Body", bulletFontSize=10, spaceAfter=4)


def steps(items):
    return ListFlowable([ListItem(P(item), leftIndent=16) for item in items], bulletType="1", leftIndent=16,
                        bulletFontName="Body-Bold", bulletFontSize=9.6, bulletFormat="%s.", spaceAfter=4)


def note(text, title="Tip"):
    box = Table([[P(f"<b>{title}.</b> {text}", "note")]], colWidths=[WIDTH])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(NOTE_BG)),
                             ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(NOTE_EDGE)),
                             ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                             ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return [Spacer(1, 2), box, Spacer(1, 8)]


def formula(text):
    box = Table([[P(text, "formula")]], colWidths=[WIDTH])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(ROW_BG)),
                             ("LINEBEFORE", (0, 0), (0, -1), 2.5, colors.HexColor(ACCENT)),
                             ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return [Spacer(1, 2), box, Spacer(1, 8)]


def figure(name, caption, width=WIDTH, crop=None, key=None):
    """A picture of the program with a thin frame and a numbered caption."""
    path = os.path.join(IMAGES, name)
    if crop:
        picture = PILImage.open(path)
        cropped = os.path.join(IMAGES, f"_{name}")
        left, top, right, bottom = crop  # inside the picture: outside it PIL would paint black
        picture.crop((left, top, min(right, picture.width), min(bottom, picture.height))).save(cropped)
        path = cropped
    w, h = PILImage.open(path).size
    height = width * h / w
    if height > 200 * mm:  # keep it on one page
        width, height = width * 200 * mm / height, 200 * mm
    counters["figure"] += 1
    FIGURES[key or name] = counters["figure"]
    frame = Table([[Image(path, width=width, height=height)]], colWidths=[width + 2])
    frame.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(RULE)),
                               ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
                               ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    return [KeepTogether([Spacer(1, 4), frame, P(f"Figure {counters['figure']}. {caption}", "caption")])]


def table(rows, widths, header=True, align=None, zebra=True, bold_first=False):
    """rows: lists of text (paragraph markup). widths in mm."""
    data = []
    for r, row in enumerate(rows):
        style = "head" if header and r == 0 else "cell"
        data.append([P(str(c), "cellb" if bold_first and c_i == 0 and style == "cell" else style)
                     for c_i, c in enumerate(row)])
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor(RULE)),
                ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)))
    if zebra:
        for r in range(1 if header else 0, len(rows)):
            if r % 2 == 0:
                commands.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor(ROW_BG)))
    t.setStyle(TableStyle(commands))
    return [t, Spacer(1, 8)]


# ===================== the NCRP 147 formulas, to check the examples =====================
def archer_thickness(params, B):
    a, b, g = params
    return (1 / (a * g)) * math.log((B ** (-g) + b / a) / (1 + b / a))


def archer_transmission(params, x):
    a, b, g = params
    return ((1 + b / a) * math.exp(a * g * x) - b / a) ** (-1 / g)


def through(params, layers, start=1.0):
    """Transmission of one radiation type through layers [(material, mm)], each starting at the equivalent thickness
    of what is in front of it ('start': what its preshielding lets through)."""
    transmission = start
    for material, x in layers:
        transmission = archer_transmission(params[material], archer_thickness(params[material], transmission) + x)
    return transmission


def solve(dose, goal):
    """The thickness at which dose (falling with it) comes down to goal, by halving an interval."""
    low, high = 0.0, 1.0
    while dose(high) > goal:
        low, high = high, 2 * high
    for _ in range(200):
        middle = (low + high) / 2
        low, high = (middle, high) if dose(middle) > goal else (low, middle)
    return (low + high) / 2


def close(a, b, tolerance=1e-6):
    assert abs(a - b) <= tolerance * max(1.0, abs(b)), (a, b)


def fmt(x, digits=3):
    """Numbers as a physicist writes them: 3 significant digits, × 10ⁿ for small ones."""
    if x == 0:
        return "0"
    if abs(x) < 1e-3:
        exponent = math.floor(math.log10(abs(x)))
        return f"{x / 10 ** exponent:.{digits - 1}f} × 10<super>{exponent}</super>".replace("-", "−")
    return f"{x:.{digits}g}"


def params_text(p):
    return f"α = {p[0]:g}, β = {p[1]:g}, γ = {p[2]:g}"


# ===================== pages =====================
class Guide(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(path, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=22 * mm,
                         bottomMargin=20 * mm, title="Shielding of X-ray Rooms — User Guide",
                         author="Shielding of X-ray Rooms", subject="User guide of the program (NCRP Report No. 147)")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        self.addPageTemplates([PageTemplate("cover", [frame], onPage=self.cover_page),
                               PageTemplate("page", [frame], onPageEnd=self.page)])
        self.section = ""

    def beforeDocument(self):
        self.section = ""  # multiBuild lays the document out several times

    def cover_page(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(NAVY))
        canvas.rect(0, A4[1] - 118 * mm, A4[0], 118 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor(ACCENT))
        canvas.rect(0, A4[1] - 120 * mm, A4[0], 2 * mm, stroke=0, fill=1)
        canvas.drawImage(ICON, 20 * mm, A4[1] - 62 * mm, 34 * mm, 34 * mm, mask="auto")
        canvas.setFillColor(colors.white)
        canvas.setFont("Light", 30)
        canvas.drawString(20 * mm, A4[1] - 82 * mm, "Shielding of X-ray Rooms")
        canvas.setFont("Semibold", 17)
        canvas.drawString(20 * mm, A4[1] - 94 * mm, "User Guide")
        canvas.setFont("Body", 10.5)
        canvas.setFillColor(colors.HexColor("#9fb3c8"))
        canvas.drawString(20 * mm, A4[1] - 106 * mm,
                          "Structural shielding design for medical X-ray imaging facilities  ·  NCRP Report No. 147")
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.setFont("Body", 9)
        canvas.drawString(20 * mm, 16 * mm, f"Edition {date.today():%B %Y}")
        canvas.restoreState()

    def page(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor(RULE))
        canvas.setLineWidth(0.5)
        canvas.line(20 * mm, A4[1] - 14 * mm, A4[0] - 20 * mm, A4[1] - 14 * mm)
        canvas.setFont("Body", 8)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(20 * mm, A4[1] - 12 * mm, "Shielding of X-ray Rooms  ·  User Guide")
        canvas.drawRightString(A4[0] - 20 * mm, A4[1] - 12 * mm, getattr(doc, "section", ""))
        canvas.drawRightString(A4[0] - 20 * mm, 11 * mm, str(doc.page))
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Heading):
            text = flowable.plain.replace("&nbsp;", " ")
            self.canv.bookmarkPage(flowable.key)
            self.canv.addOutlineEntry(text, flowable.key, level=flowable.level - 1, closed=flowable.level > 1)
            self.notify("TOCEntry", (flowable.level - 1, text, self.page, flowable.key))
            if flowable.level == 1:
                self.section = text


# ===================== content =====================
def cover():
    return [Spacer(1, 128 * mm),
            P("This guide shows how to design the shielding of X-ray, CT and mammography rooms, and of whole "
              "departments, with the program <b>Shielding of X-ray Rooms</b>: what every input means, what the "
              "program calculates and how, and how to read and check the results. Section 11 works through the "
              "built-in examples with every number, so that each result can be checked by hand."),
            Spacer(1, 4),
            P("The program follows <b>NCRP Report No. 147</b>, <i>Structural Shielding Design for Medical X-Ray "
              "Imaging Facilities</i> (2004). It is an aid to a qualified expert: the final shielding design and its "
              "verification remain the responsibility of the radiation protection expert or medical physicist.",
              "small"),
            NextPageTemplate("page"), PageBreak()]


def contents():
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    toc.dotsMinLevel = 0
    return [P("Contents", "H1"), toc, PageBreak()]


def introduction():
    story = H1("Introduction")
    story += H2("What the program does")
    story += [P("The program calculates the thickness of the protective barriers of a room with medical X-ray "
                "equipment: its walls, doors, floor and ceiling. For every barrier it finds the thickness of each "
                "material you choose (lead, concrete, gypsum wallboard, steel, plate glass or wood) that keeps the "
                "weekly air kerma beyond the barrier below the shielding design goal <i>P</i>. It can also count the "
                "shielding a barrier already has (a floor slab, an existing wall) and give what must be added to it, "
                "check a thickness you plan to install and how many patients per week it allows, protect an area "
                "further away than the one just beyond a barrier, scale the scatter to the field you use, give the "
                "height of the shielding of walls and doors, treat a wall between two rooms of a department as one "
                "wall for the radiation of both, show the rooms in 2D and 3D with the radiation around them, and "
                "write a complete report in Excel."),
              P("You can design:")]
    story += [bullets(["<b>X-Ray rooms</b>: radiography and chest rooms, with primary and secondary barriers; also "
                       "modern digital radiography (DR) rooms, general and pediatric.",
                       "<b>Fluoroscopy rooms</b>: R&amp;F rooms (fluoroscopy and radiographic tube), cardiac and "
                       "peripheral angiography, and five kinds of interventional room.",
                       "<b>CT rooms</b>: secondary radiation from the DLP of the body and head scans.",
                       "<b>Mammography rooms</b>: secondary radiation only, also digital breast tomosynthesis "
                       "(DBT).",
                       "<b>Departments</b>: several rooms of any type on one floor plan, each with its own results, "
                       "in one report."])]
    story += [P("The method and the data are those of NCRP Report No. 147. Newer published data are added where "
                "NCRP 147 has none or older ones, and are always named with their source:")]
    story += table([["Data of the literature", "What they add", "Section"],
                    ["Li et al. 2024", "Transmission of modern digital radiography beams at a given kVp, and of the "
                                       "table bucky of an orthopedic room (concrete)", "4.9"],
                    ["Kirby et al. 2023", "Workload distributions of modern digital radiography rooms, general and "
                                          "pediatric", "4.10"],
                    ["Biondi et al. 2024", "Workload distributions of interventional rooms", "4.11"],
                    ["Chen et al. 2013", "Workload distributions of radiographic rooms in Taiwan", "4.12"],
                    ["Yang et al. 2017", "Digital breast tomosynthesis: workload, scatter per view, transmission", "6.1"],
                    ["Li et al. 2013", "Digital breast tomosynthesis: workload and transmission; W/Ag beams at a kVp",
                     "6.1, 6.3"],
                    ["Yang et al. 2016", "Digital breast tomosynthesis: scatter toward a wall or door, the floor or "
                                         "the ceiling (with the workload of Li et al. 2013)", "6.1"],
                    ["Judge et al. 2013", "Digital mammography: the scatter of three full-field digital units", "6.2"],
                    ["Li et al. 2012", "W/Al and W/Rh mammography beams at a kVp", "6.3"]], [38, 112, 20])
    story += [P("In the list of workload distributions those of NCRP 147 come first; the others follow below a line "
                "and their names end with the source, e.g. <i>DR Room (floor) – Kirby 2023</i>. Every table of "
                "these papers that the program uses was checked against the paper, value by value or by reproducing "
                "it from the others, and their worked examples are compared with the program in section 11.10.")]
    story += H2("Files the program uses")
    story += [P("The setup (section 3.1) puts these files in the program's folder:")]
    story += table([["File", "What it is"],
                    ["Shielding of X-ray Rooms.exe", "The program. (From the source code: <font name='Mono'>"
                     "Shielding_of_X-Ray_rooms.py</font> in the folder <font name='Mono'>XRIFSC_code</font>, run "
                     "with Python.)"],
                    ["Data Shielding.xlsx", "The NCRP 147 data: workloads, unshielded air kerma, transmission "
                                            "parameters, occupancy and use factors; and the data of the literature, "
                                            "each in sheets named after its source. <b>Required</b>: keep it next to "
                                            "the program."],
                    ["Examples\\*.shield", "The built-in examples as project files."],
                    ["User Guide.pdf, 5_NCRP_147_2004.pdf", "This guide and NCRP Report No. 147, opened from the Help "
                                                            "menu."]], [55, 115])
    story += [P("BIR 2012 (<i>Radiation Shielding for Diagnostic Radiology</i>) is not distributed with the program. "
                "If you have its PDF, save it as <font name='Mono'>book.9780905749747.pdf</font> in the program's "
                "folder and it appears in the Help menu.", "small"), Spacer(1, 6)]
    story += H2("How this guide is organised")
    story += [P("Section 2 summarises the NCRP 147 method as the program applies it. Sections 3 to 10 describe the "
                "program screen by screen. Section 11 works through the examples by hand, section 12 lists the "
                "NCRP 147 data the program uses, and section 13 explains the messages you may see.")]
    return story


def method():
    story = H1("The calculation method (NCRP 147)")
    story += H2("Weekly air kerma beyond a barrier")
    story += [P("For each kind of radiation that reaches a barrier (a <i>workload distribution</i>, primary or "
                "secondary), the unshielded weekly air kerma at the occupied point beyond the barrier is")]
    story += formula("<i>K</i> = <i>N</i> · <i>U</i> · <i>T</i> · <i>K</i><super>1</super> / <i>d</i><super>2"
                     "</super>")
    story += table([["Symbol", "Meaning", "Unit"],
                    ["<i>N</i>", "Number of patients per week. With a total workload <i>W</i><sub>tot</sub>: "
                                 "<i>N</i> = <i>W</i><sub>tot</sub> / <i>W</i><sub>norm</sub>.", "patients/week"],
                    ["<i>U</i>", "Use factor: the fraction of the primary beam aimed at the barrier "
                                 "(1 for secondary radiation).", "–"],
                    ["<i>T</i>", "Occupancy factor of the area beyond the barrier (NCRP 147 Table 4.1).", "–"],
                    ["<i>K</i><super>1</super>", "Unshielded air kerma per patient at 1 m: primary "
                                                 "<i>K</i><super>1</super><sub>P</sub> or secondary (leakage and "
                                                 "scatter) <i>K</i><super>1</super><sub>sec</sub>.", "mGy/patient"],
                    ["<i>d</i>", "Distance from the source to the occupied point beyond the barrier.", "m"],
                    ["<i>K</i>", "Weekly air kerma at that point without shielding.", "mGy/week"]], [18, 122, 30])
    story += [P("When several workload distributions reach one barrier (for example a wall that is primary for the "
                "chest bucky and secondary for the table), their air kerma values are added: Σ<i>K</i>.")]
    story += H2("Transmission and thickness")
    story += [P("The barrier must let through no more than the fraction")]
    story += formula("<i>B</i> = <i>P</i> / Σ<i>K</i>")
    story += [P("If <i>B</i> ≥ 1 the barrier needs no shielding and the result says <b>none needed</b>. With one "
                "radiation type, the thickness of each material follows from the Archer equation, with the NCRP 147 "
                "fitting parameters α, β, γ of that material for the workload distribution (minus the preshielding, "
                "section 2.5):")]
    story += formula("<i>x</i> = (1 / αγ) · ln[ (<i>B</i><super>−γ</super> + β/α) / (1 + β/α) ]")
    story += [P("When several radiation types reach one barrier, each goes through it with the fitting parameters of "
                "its own workload distribution, primary or secondary, and its own preshielding, as NCRP 147 does in "
                "its examples (Sections 5.3.5 and 5.4.2). The program finds the thickness at which their air kerma "
                "beyond the barrier adds up to <i>P</i>:")]
    story += formula("Σ<sub><i>i</i></sub> <i>K</i><sub><i>i</i></sub> · <i>B</i><sub><i>i</i></sub>(<i>x</i> + "
                     "<i>x</i><sub>pre,<i>i</i></sub>) = <i>P</i>")
    story += [P("Every radiation type therefore needs its workload distribution (or kVp). A primary beam given by its "
                "kVp can use, instead of the NCRP 147 data, those of modern digital radiography (section 4.9); the "
                "workload distributions of the literature have their own (sections 4.10 to 4.12, 6.1 and 6.2).")]
    story += note("Earlier versions used the transmission of one radiation type, ticked <b>Set for the "
                  "calculation</b>, for the whole Σ<i>K</i>, and took its preshielding off the whole thickness. Where a "
                  "primary beam behind the image receptor and secondary radiation reach the same barrier, the "
                  "secondary radiation does not pass through the image receptor, so these barriers now come out "
                  "somewhat thicker, as in NCRP 147 (section 11.9). Projects of earlier versions open and are "
                  "calculated this way.", "Note")
    story += H2("Design goal P")
    story += table([["Area beyond the barrier", "P (air kerma)", "Annual"],
                    ["Controlled: occupied only by radiation workers", "0.1 mGy/week", "5 mSv/year"],
                    ["Uncontrolled: everyone else (public, other staff, patients)", "0.02 mGy/week", "1 mSv/year"]],
                   [100, 35, 35])
    story += [P("Choosing the <b>Shielding Area</b> fills in <i>P</i>. <i>Supervised</i> is not an NCRP 147 class; "
                "the program treats it as uncontrolled. If your national dose constraint is lower, type it in "
                "<b>Shielding Design Goal</b>.")]
    story += H2("Distances")
    story += [P("<i>d</i> goes to the person to protect. NCRP 147 names it after the radiation: "
                "<i>d</i><sub>P</sub> for primary radiation, <i>d</i><sub>L</sub> for leakage, <i>d</i><sub>S</sub> "
                "for scatter (from the patient) and <i>d</i><sub>sec</sub> for leakage and scatter together, when "
                "<i>d</i><sub>S</sub> = <i>d</i><sub>L</sub>. Each radiation type of a barrier has its own distance, "
                "under its radiation choices, and its label shows which one it is (<i>d</i><sub>P</sub>, <i>d</i><sub>L</sub>, <i>d</i><sub>S</sub> or <i>d</i><sub>sec</sub>; CT: <i>d</i><sub>sec</sub> from "
                "the isocenter).")]
    story += [P("You enter the <b>Distance from the Source to the Barrier</b> (focal spot; CT: the isocenter). "
                "Next to it, <b>+ to the person beyond it</b> is the distance from the barrier to that person, which "
                "the program adds, and then the sum, e.g. <b><i>d</i><sub>P</sub> = 2.30 m</b>. The distance beyond is one value per "
                "barrier, shown next to every distance of the barrier; change it there. NCRP 147 (section 4.1.2) "
                "places the person:")]
    story += table([["Barrier", "Where the person is (NCRP 147 4.1.2)", "Distance beyond the barrier"],
                    ["Walls and doors", "0.3 m beyond the wall or door", "0.3 m"],
                    ["Ceiling", "0.5 m above the floor of the room above", "0.5 m, plus any space above a "
                                                                          "suspended ceiling"],
                    ["Floor", "not more than 1.7 m above the floor below",
                     "floor-to-floor height − 1.7 m: <b>1.3 m</b> for a 3 m storey, 2.6 m for 4.3 m"]],
                   [30, 70, 70])
    story += [P("These are the values filled in; change them where the building differs. To type the whole "
                "distance yourself, from the source to the person, as NCRP 147 gives it in its examples, tick "
                "<b>Enter the whole distance, to the person beyond the barrier (nothing added)</b>: the labels then "
                "read <i>to the Person</i> and nothing is added. The floor plan (section 8) measures the distances "
                "to the barriers and sets the floor and ceiling values from the floor-to-floor height.")]
    story += note("Earlier versions of the program added 1.7 m below the floor. NCRP 147 puts the person 1.7 m "
                  "<i>above the floor below</i>, which for a 3 m storey is 1.3 m under the floor: closer to the "
                  "source, so the floor needs more shielding. Projects saved with an earlier version are converted "
                  "when you open them and show the corrected results.", "Note")
    story += H2("Preshielding")
    story += [P("Behind the image receptor the primary beam is already attenuated by the grid, the cassette and "
                "their supports. NCRP 147 credits this as an equivalent thickness <i>x</i><sub>pre</sub>: "
                "<b>Bucky</b> (table or wall bucky) 0.85 mm lead, 72 mm concrete or 7 mm steel; <b>Cross-table</b> "
                "(grid and cassette only) 0.3 mm lead, 30 mm concrete or 2 mm steel. Only that primary beam goes "
                "through it: for it the barrier is <i>x</i> + <i>x</i><sub>pre</sub> thick, while the secondary "
                "radiation that reaches the same barrier meets <i>x</i> alone. With one radiation type this is the "
                "calculated thickness minus <i>x</i><sub>pre</sub>. Use it only for primary barriers behind the "
                "image receptor.")]
    story += H2("CT rooms")
    story += [P("NCRP 147 finds the secondary air kerma of CT from the dose-length product (DLP). Per scan, at 1 m "
                "from the isocenter:")]
    story += formula("<i>K</i><super>1</super><sub>sec, body</sub> = 1.2 × 3×10<super>−4</super> cm<super>−1"
                     "</super> × DLP<sub>body</sub><br/><i>K</i><super>1</super><sub>sec, head</sub> = "
                     "9×10<super>−5</super> cm<super>−1</super> × DLP<sub>head</sub>")
    story += [P("A procedure can have several scans (phases), e.g. without and with contrast. For scan 1, 2, ... "
                "you give the % of the procedures that have it; their sum / 100 is the mean number of scans per "
                "procedure <i>s</i>. NCRP 147 assumes every procedure is scanned once and 40 % again with "
                "contrast: <i>s</i> = 1.4. The weekly air kerma is")]
    story += formula("<i>K</i> = <i>T</i> · (<i>N</i><sub>body</sub> <i>s</i><sub>body</sub> <i>K</i><super>1"
                     "</super><sub>body</sub> + <i>N</i><sub>head</sub> <i>s</i><sub>head</sub> <i>K</i><super>1"
                     "</super><sub>head</sub>) / <i>d</i><super>2</super>")
    story += [P("and the thickness comes from the NCRP 147 CT transmission data of lead and concrete at 120 or "
                "140 kVp.")]
    story += H2("Several materials in one barrier")
    story += [P("Under the materials of a barrier you choose how they are used:")]
    story += [bullets(["<b>Each one alone</b>: the thickness of each material as if it were the only one in the "
                       "barrier, e.g. lead <i>or</i> concrete. These are alternatives.",
                       "<b>Layers of one barrier</b>: one barrier made of all the materials, e.g. concrete <i>and</i> "
                       "lead. From the room side outwards, each material gives its share (%) of the attenuation of "
                       "the air kerma, from what the preshielding lets through down to <i>P</i>. For every radiation "
                       "type, each layer starts at the equivalent thickness of everything in front of it (its "
                       "preshielding included), so the order counts: the first layers harden the beam."])]
    story += H2("Checking a planned thickness")
    story += [P("When you tick <b>Check the dose beyond the barrier with a planned thickness</b> and type the "
                "thicknesses you intend to install, the program calculates the weekly air kerma beyond the "
                "barrier,")]
    story += formula("dose beyond = Σ<i>K</i> · <i>B</i>(<i>x</i><sub>planned</sub>)")
    story += [P("and compares it with <i>P</i>. Every material with a planned thickness is taken as installed: "
                "together they cut the radiation, one after the other from the room side out, with the existing "
                "shielding in its place. Leave empty a material that will not be there. Like <i>P</i>, the dose "
                "includes the occupancy factor <i>T</i>.")]
    story += H2("Existing shielding")
    story += [P("A barrier often has shielding already: the concrete slab of a floor or ceiling (NCRP 147 2.3.5), a "
                "concrete or brick wall, lead put in earlier. NCRP 147 asks for it to be counted and listed in the "
                "report (5.8), and to add shielding over what is there when a barrier is not enough (6.5). Give its "
                "materials and thicknesses: the program then calculates the thickness of each new material that "
                "must be <b>added</b> to it. The existing layers and the new ones are one barrier: every radiation "
                "type goes through all of them, each layer starting at the equivalent thickness of what is in front "
                f"of it, as for layers (section {sec('Several materials in one barrier')}):")]
    story += formula("Σ<sub><i>i</i></sub> <i>K</i><sub><i>i</i></sub> · <i>B</i><sub><i>i</i></sub>(existing, "
                     "then <i>x</i>) = <i>P</i>&nbsp;&nbsp;&nbsp;or&nbsp;&nbsp;&nbsp;Σ<sub><i>i</i></sub> "
                     "<i>K</i><sub><i>i</i></sub> · <i>B</i><sub><i>i</i></sub>(<i>x</i>, then existing) = <i>P</i>")
    story += [P("The first form is for new materials <b>outside</b> the existing shielding, the second for new "
                "materials on its <b>room side</b>. The order counts, because the first layers harden the beam: "
                "lead outside a concrete slab usually has to be thicker than lead on its room side (section "
                f"{sec('Existing shielding: lead on the floor slab of the CT room')}). "
                "With <b>Each one alone</b> every material gets the thickness that is enough on its own with the "
                "existing shielding; with <b>Layers of one barrier</b> the new layers share, as their % say, the "
                "attenuation that the existing shielding does not give. If the existing shielding is enough "
                "alone, the result is <b>none needed</b>. Preshielding counts as before: in front of everything, "
                "for the primary beam only.")]
    story += H2("How many patients a barrier allows")
    story += [P("NCRP 147 checks an installed barrier by the number of patients per week it allows without "
                "exceeding the design goal (6.3.3), and asks the survey report to state it (6.4). The air kerma of "
                "every radiation type grows with the workload, so a barrier whose dose beyond is "
                "Σ<i>K</i> · <i>B</i> with the present workload allows that workload multiplied by")]
    story += formula("<i>f</i> = <i>P</i> / (Σ<i>K</i> · <i>B</i>),&nbsp;&nbsp;&nbsp;&nbsp;"
                     "<i>N</i><sub>max</sub> = <i>f</i> · <i>N</i>")
    story += [P("with the barrier as it will be built: the planned thicknesses and the existing shielding, or the "
                "existing shielding alone. <i>f</i> &lt; 1 means that the barrier is not enough for the present "
                "workload. A CT room gives the body and head procedures per week; a workload given in mA·min per "
                "week is multiplied likewise.")]
    story += H2("A wall shared by two rooms")
    story += [P("A wall between two rooms of a department is one wall, but each room sees it from its own side: "
                "the radiation of room A crosses it toward room B, that of room B toward room A, each with its own "
                "workload, distances, occupancy and design goal. Each side must meet its own design goal, so the "
                "wall must be as thick as the more demanding side needs. When the two barriers are marked as the "
                "same wall (section "
                f"{sec('Walls shared by two rooms')}), the "
                "program calculates the materials of each side for both:")]
    story += [bullets(["from this room, as always: the thickness <i>x</i><sub>A</sub> of each material;",
                       "from the other room, the same wall seen from there: its layers (and the existing shielding) "
                       "in the reverse order, with the radiation, distances, <i>T</i> and <i>P</i> of the other "
                       "room's barrier: <i>x</i><sub>B</sub>;",
                       "with a further area on either side (section "
                       f"{sec('A further area beyond a barrier')}), that area too;",
                       "the wall gets the larger, <i>x</i> = max(<i>x</i><sub>A</sub>, <i>x</i><sub>B</sub>), for "
                       "each material (for layers, each layer), and its planned thickness is checked on both "
                       "sides."])]
    story += H2("A further area beyond a barrier")
    story += [P("NCRP 147 warns that the area just beyond a barrier is not always the one that sets its thickness: "
                "\"the actual limitation for shielding design may be a more distant, fully occupied area, such as an "
                "office across the corridor\" (4.1.3, and Table 4.1, note a). A corridor with <i>T</i> = 1/5 may "
                "need less than the office a few metres further, with <i>T</i> = 1. A barrier can therefore protect "
                "a second, further area, with its own occupancy factor <i>T</i><sub>2</sub> and design goal "
                "<i>P</i><sub>2</sub>, its person a distance Δ further from the source. Every radiation type reaches "
                "it with")]
    story += formula("<i>K</i><sub>2</sub> = <i>K</i> · (<i>T</i><sub>2</sub> / <i>T</i>) · "
                     "[<i>d</i> / (<i>d</i> + Δ)]<super>2</super>")
    story += [P("with <i>K</i>, <i>T</i> and <i>d</i> those of the area just beyond. The program finds the thickness of "
                "each material for the two areas, as always, and takes the larger; the planned-thickness check and "
                "the check of the patients look at both, and the results say which area governs.")]
    story += H2("Scatter and the size of the field")
    story += [P("The scattered air kerma grows with the area of the primary field on the patient (NCRP 147 4.1.7.2; "
                "Appendix C, Eq. C.2): it is proportional to <i>F</i> / <i>d</i><sub>F</sub><super>2</super>, the "
                "image-receptor area <i>F</i> at its distance <i>d</i><sub>F</sub> from the source, the field size "
                "at 1 m. The secondary air kerma of NCRP 147 Table 4.7, and those of the literature made with its "
                "method, assume one field for each workload distribution:")]
    workbook = load_workbook(EXCEL, data_only=True)
    rows = [["Workload distribution", "<i>F</i><sub>0</sub> (cm²)", "<i>d</i><sub>F0</sub> (m)",
             "<i>F</i><sub>0</sub> / <i>d</i><sub>F0</sub><super>2</super> (cm² at 1 m)"]]
    for r in workbook["Uns Air Kerma"].iter_rows(min_row=2, values_only=True):
        if r[0]:
            rows.append([r[0].replace("&", "&amp;"), f"{r[2]:g}", f"{r[3]:g}", f"{r[2] / r[3] ** 2:.0f}"])
    story += table(rows, [70, 30, 30, 40])
    story += [P("Modern image receptors are often larger (a 43 × 43 cm detector is 1849 cm²; a 30 × 40 cm flat panel "
                "of an angiography unit 1200 cm²). With <b>Field size</b> you give yours, and the program scales the "
                "scattered part of the suggested air kerma, not the leakage:")]
    story += formula("<i>K</i><super>1</super><sub>sec</sub> = <i>K</i><super>1</super><sub>L</sub> + "
                     "<i>K</i><super>1</super><sub>S</sub> · (<i>F</i> / <i>d</i><sub>F</sub><super>2</super>) / "
                     "(<i>F</i><sub>0</sub> / <i>d</i><sub>F0</sub><super>2</super>)")
    story += [P("The transmission stays that of NCRP 147 (Table C.1), whose curves were made with the fields above: "
                "scatter is most of the unshielded secondary air kerma (Appendix C.3), so the change of its mix with "
                "leakage is small. Measured scatter (digital breast tomosynthesis, Judge et al. 2013) has no field "
                "to scale.")]
    story += [P("An air kerma you write (<b>Write Unshielded Secondary Air Kerma</b>) has its own <b>Field size</b> "
                "under it: your field <i>F</i> at <i>d</i><sub>F</sub>, and the field <i>F</i><sub>0</sub> at "
                "<i>d</i><sub>F0</sub> your value was given for (at first that of the workload distribution in the "
                "table above; for a kVp that of the Rad Room, 1000 cm² at 1 m, or in a mammography room 720 cm² at "
                "0.58 m). The program cannot tell its leakage from its scatter, so it scales the whole value by "
                "(<i>F</i> / <i>d</i><sub>F</sub><super>2</super>) / (<i>F</i><sub>0</sub> / "
                "<i>d</i><sub>F0</sub><super>2</super>); if the leakage in it matters, give it as a radiation type of "
                f"its own ({fig('field_written.png')}).")]
    written = VALUES["field"]["written"]
    close(written, 0.0345 * 1505 / 1000)
    story += figure("field_written.png", "Wall 3 of the example X-ray room with an air kerma written, 0.0345 mGy per "
                                         "patient for 1000 cm² at 1 m, and a 35 × 43 cm field at 1 m: "
                                         f"{written:.4f} mGy per patient.",
                    width=150 * mm, crop=(0, 235, 1175, 820))

    # ----- the scatter at an angle, for a kVp: the method of NCRP 147 Appendix C, at one kVp -----
    angle = VALUES["angle"]
    v, theta, F, dF = angle["kvp"], angle["theta"], angle["F"], angle["dF"]
    k_w = 1.222 - 5.664e-2 * v + 1.227e-3 * v ** 2 - 3.136e-6 * v ** 3
    a_1 = 1.6e-2 * (v - 125) + 8.43 - 1.11e-1 * theta + 9.83e-4 * theta ** 2 - 1.74e-6 * theta ** 3
    scatter = k_w * 2.5 * a_1 * 1e-6 * F / dF ** 2
    leak = angle["K1"] - scatter
    story += H2("Scatter at an angle")
    story += [P("NCRP 147 makes the secondary air kerma of Table 4.7 from the scatter fraction <i>a</i><sub>1</sub>"
                "(θ, kVp) (× 10<super>−6</super>): the scattered air kerma 1 m from the patient over the primary air kerma 1 m from the tube, "
                "per cm² of primary field at 1 m (Appendix C.1). It comes from the measurements of Trout and Kelley "
                "(1972) at 100, 125 and 150 kVp, reanalysed by Simpkin and Dixon (1998) at their mean plus one "
                "standard deviation; below 100 kVp it falls linearly with the kVp (Dixon 1994). Figure C.1 draws it "
                "for tungsten-anode beams with this fit, from 20° to 140° (θ from the direction of the beam to the "
                "occupied point):")]
    story += formula("<i>a</i><sub>1</sub> = 1.6 × 10<super>−2</super> (kVp − 125) + 8.43 − 1.11 × 10<super>−1</super>"
                     " θ + 9.83 × 10<super>−4</super> θ<super>2</super> − 1.74 × 10<super>−6</super> θ<super>3</super>")
    story += [P("With <b>Give kVp</b> a secondary radiation type has, instead of the suggested air kerma, <b>At an "
                "angle (NCRP 147)</b>: you give the scattering angle θ, whether to add the leakage of the tube, and "
                "the field <i>F</i> at <i>d</i><sub>F</sub> (at first 1000 cm² at 1 m). Per patient, with the 2.5 "
                "mA·min the program takes for a kVp (NCRP 147 Rad Room), the scatter is that of Eq. C.2:")]
    story += formula("<i>K</i><super>1</super><sub>S</sub> = <i>K</i><super>1</super><sub>W</sub>(kVp) · 2.5 · "
                     "<i>a</i><sub>1</sub>(θ, kVp) · 10<super>−6</super> · <i>F</i> / <i>d</i><sub>F</sub>"
                     "<super>2</super>")
    story += [P("with <i>K</i><super>1</super><sub>W</sub> the primary air kerma at 1 m per mA·min of Figure B.1 "
                "(1.222 − 5.664 × 10<super>−2</super> kVp + 1.227 × 10<super>−3</super> kVp<super>2</super> − 3.136 × "
                "10<super>−6</super> kVp<super>3</super> mGy). The leakage is that of Appendix C.2: 0.876 mGy/h at "
                "1 m at 150 kVp and 3.3 mA, which at a lower kVp falls with kVp² and with the transmission of the "
                "2.32 mm lead of the housing (Eq. C.6-C.9). Summed over the workload distributions, the same "
                "formulas give the values of Table 4.7 (Rad Room: leakage 5.3 × 10<super>−4</super>, side-scatter "
                "0.033 against 0.034, forward/backscatter 0.048 mGy per patient). As in Table 4.7, the workload is "
                "not reduced by the use factor of a primary beam on the same barrier (Eq. C.4), unless you ask for "
                f"it (section {sec('Secondary radiation and the use factor: (1 − U)')}). "
                "Figure C.1 has no formula for the Mo/Mo beams of mammography, only measured points, so in a "
                "mammography room you write the air kerma.")]
    close(angle["K1"], scatter + leak)
    story += [P(f"For example, Wall 3 of the example X-ray room at {v:g} kVp and θ = {theta:g}°, with "
                f"{F:g} cm² at {dF:g} m ({fig('angle_kvp.png')}): <i>K</i><super>1</super><sub>W</sub> = "
                f"{k_w:.3f} mGy per mA·min, <i>a</i><sub>1</sub> = {a_1:.2f} × 10<super>−6</super>, so")]
    story += formula(f"<i>K</i><super>1</super><sub>sec</sub> = {k_w:.3f} × 2.5 × {a_1:.2f} × 10<super>−6</super> "
                     f"× {F:g} + {fmt(leak, 2)} = <b>{angle['K1']:.4f}</b> mGy per patient")
    story += figure("angle_kvp.png", f"A secondary radiation type at {v:g} kVp: the scatter at {theta:g}° with "
                                     "the leakage, for a field of 1000 cm² at 1 m.",
                    width=150 * mm, crop=(0, 235, 1175, 820))

    # ----- the same for a workload distribution, from its kVp spectrum ('At an angle' under 'Field size') -----
    rows = {(r["section"], r["barrier"]): r for r in json.load(open(os.path.join(IMAGES, "ncrp147_examples.json"),
                                                                    encoding="utf-8"))}
    wall_2, at_30 = rows[("5.3", "Wall 2")]["program"], rows[("5.3", "Wall 2, scatter at 30°")]["program"]
    ratio = (8.43 - 1.11e-1 * 30 + 9.83e-4 * 900 - 1.74e-6 * 27000) / (8.43 - 1.11e-1 * 90 + 9.83e-4 * 8100
                                                                    - 1.74e-6 * 729000)
    story += [P("A workload distribution with the workload of each kVp (NCRP 147 Table 4.2, and Kirby et al. 2023 and "
                "Chen et al. 2013) has, under <b>Field size</b> of the suggested air kerma, <b>At an angle θ</b> "
                f"({fig('angle_option.png')}). Ticked, its scatter is made as NCRP 147 made Table 4.7, at the "
                "angle you give instead of 90° (side-scatter) or 135° (forward/backscatter), summed over its kVp "
                "(Eq. C.5), for its field of Table 4.7 or the one you give; where the choice has leakage, that of "
                "each kVp is added (Eq. C.9):")]
    story += formula("<i>K</i><super>1</super><sub>S</sub>(θ) = Σ<sub>kVp</sub> <i>K</i><super>1</super><sub>W</sub>"
                     "(kVp) · <i>W</i>(kVp) · <i>a</i><sub>1</sub>(θ, kVp) · 10<super>−6</super> · <i>F</i> / "
                     "<i>d</i><sub>F</sub><super>2</super>")
    story += [P("Each kVp then goes through the barrier on its own: its scatter with the transmission of the primary "
                "beam at that kVp (Table A.1, Eq. C.3), its leakage, already hardened by the housing, by its HVL "
                "(Eq. C.8), instead of the one curve of Table C.1, which mixes scatter and leakage 1 m away. At 90° "
                "this gives Table 4.7 again (Rad Room, all barriers: 0.0339 against 0.034 mGy per patient).")]
    story += [P("It is the more realistic calculation of NCRP 147 5.3.3.2, the chest bucky wall outside the beam: the "
                "side-scatter of the chest patient 0.8 m away is scatter at about 30°. Its own transmission lets it "
                f"through more easily than the curve of Table C.1, and <i>a</i><sub>1</sub>(30°) is {100 * (ratio - 1):.0f} % "
                f"larger than <i>a</i><sub>1</sub>(90°): the lead goes from {wall_2:.2f} mm to <b>{at_30:.2f} mm</b>, the "
                "0.3 mm of NCRP 147 (the example 5.3 has both, as Wall 2 and Wall 2, scatter at 30°).")]
    story += figure("angle_option.png", "NCRP 147 5.3.3.2 with the side-scatter of the chest patient at 30° (At an "
                                        "angle θ, under Field size).", width=150 * mm)

    # ----- secondary radiation x (1 - U) (NCRP 147 Eq. C.4, C.8) -----
    share = VALUES["share"]
    U = share["U"]
    K_s = 0.023 * 125 / 2.0 ** 2  # NCRP 147 5.3.5: Rad Room (floor), leakage + side-scatter, 125 patients, 2 m
    close(share["K"][1], K_s * (1 - U))
    story += H2("Secondary radiation and the use factor: (1 − U)")
    story += [P("When a fraction <i>U</i> of a workload aims the primary beam at a barrier, NCRP 147 says that the "
                "scatter (Eq. C.4) and the leakage (Eq. C.8) that this workload sends to the same barrier should be "
                "counted only for the rest of it, (1 − <i>U</i>) <i>W</i>: while the beam points at the barrier, its "
                "primary radiation is far stronger and is shielded anyway. Table 4.7 and the examples of Section 5 do "
                "not do it, which is safe, so the program does not either, unless you ask:")]
    story += [bullets(["A barrier with both a primary and a secondary radiation type shows, under them, <b>Secondary "
                       "radiation × (1 − U)</b>, unticked at first.",
                       "Ticked, each secondary radiation type is paired with the primary ones of the <b>same workload "
                       "distribution</b> (or the same kVp) and the <b>same workload</b> (the room's, or the same "
                       "Different Workload): its <i>K</i> is multiplied by (1 − <i>U</i>), with <i>U</i> the sum of "
                       "their use factors. A secondary type without such a pair stays as it is, e.g. the fluoroscopy "
                       "tube under the table of an R&amp;F room, whose beam never aims at the floor.",
                       "Use it only for the point of the barrier that the beam reaches: the part of a wall outside "
                       "the beam (NCRP 147 5.3.3.2) is a barrier of its own, without it.",
                       "The results and the report show it after the source of <i>K</i><super>1</super>, e.g. "
                       f"<i>Leakage + side-scatter (NCRP 147) × (1 − {U:g})</i>."])]
    story += [P(f"In the cross-table wall of NCRP 147 5.3.5 (the example 5.3, Wall 4; {fig('share_option.png')}) the "
                f"radiographic tube aims {U:g} of its workload at the wall. Its secondary radiation, {K_s:.3f} "
                f"mGy/week, becomes {K_s:.3f} × (1 − {U:g}) = <b>{K_s * (1 - U):.3f}</b> mGy/week, and the lead "
                f"{share['before']:.3f} → <b>{share['after']:.3f} mm</b>. On the floor (<i>U</i> = 0.89) the "
                "secondary radiation of the same tube drops to 11 %, but there the primary beam sets the thickness.")]
    story += figure("share_option.png", "The cross-table wall of NCRP 147 5.3.5 with Secondary radiation × "
                                        "(1 − U) ticked: the secondary radiation of the Rad Room (floor) workload "
                                        f"counts for 1 − {U:g} of it.", width=150 * mm)
    return story


def getting_started():
    story = H1("Getting started")
    story += H2("Installing")
    story += [steps(["Run <b>Shielding_of_X-ray_Rooms_Setup</b> (Windows 10 or 11, 64-bit). It is not digitally "
                     "signed, so Windows may warn the first time: choose <b>More info › Run anyway</b>.",
                     "Choose <b>Install for me only</b> (no administrator rights needed) or <b>Install for all users"
                     "</b>.",
                     "Choose the extra tasks: a desktop icon, and whether <b>.shield</b> project files open with the "
                     "program when you double-click them.",
                     "Finish: the program has a Start menu folder with the program, the <b>User Guide</b>, the "
                     "<b>Examples</b> folder and <b>Uninstall</b>."])]
    story += [P("To remove the program use <b>Settings › Apps</b> or <b>Uninstall</b> in its Start menu folder. Your "
                "project files are not touched. The first start after installing can take a little longer while "
                "Windows and the program prepare their caches.")]
    story += H2("The start screen")
    story += [P("When the program opens it shows the start screen. Choose what to design, open a saved project, or "
                "open one of the examples (section 10.3).")]
    story += figure("start.png", "The start screen.", crop=(300, 200, 1640, 800))
    story += H2("Menus")
    story += table([["Menu", "Command", "What it does"],
                    ["File", "New... › Design Department / X-Ray Room / CT Room / Fluoroscopy Room / "
                             "Mammography Room",
                     "Adds a department or a room to the current project, each in its own tab."],
                    ["", "New project", "Closes everything and starts again (it asks to save first)."],
                    ["", "Open project... (Ctrl+O)", "Opens a project file (.shield)."],
                    ["", "Save project (Ctrl+S), Save project as...", "Saves every department and room, with all "
                                                                     "inputs and floor plans."],
                    ["", "Examples", "Opens a built-in example, or one from the Examples folder."],
                    ["", "Exit", "Closes the program (it asks to save first)."],
                    ["Help", "User Guide (F1)", "This guide."],
                    ["", "NCRP Report No. 147", "The report. BIR 2012 also appears if its PDF is in the program's "
                                                "folder (section 1.2)."]],
                   [17, 68, 85])
    story += H2("The workspace")
    story += [bullets(["Every department and room is a tab of the dark tab bar. <b>Double-click a tab</b> to "
                       "rename it; the name also appears in the results and the report.",
                       "The inputs are on the left and the results on the right. Drag the divider between them to "
                       "make either side wider. Both sides scroll with the mouse wheel.",
                       "The <b>×</b> button closes a room. In a department, <b>Design</b> shows it again with all its "
                       "inputs kept."])]
    story += note("Rest the pointer on any field, label or button: a short note says what to enter, with the main "
                  "NCRP 147 values; this guide has the details. Labels with a question-mark pointer have such a "
                  "note.")
    return story


def xray_room():
    story = H1("Designing an X-ray room")
    story += [P("Start with <b>X-Ray Room</b> on the start screen, or <b>File › New... › Design X-Ray Room</b>. "
                f"{fig('xray_overview.png')} shows the example X-ray room (File › Examples › X-Ray room) with its "
                "results.")]
    story += figure("xray_overview.png", "An X-ray room: room data at the top, one tab per barrier, results on the "
                                         "right.")
    story += H2("Room data, walls and doors")
    story += [bullets(["<b>Number of Barriers</b>: at least 7, one tab each: <b>Floor</b>, <b>Ceiling</b>, then the "
                       "walls and doors, at first <b>Door 1</b> and <b>Wall 1</b> to <b>Wall 4</b> (below).",
                       "<b>Workload</b>: either <b>Write total Workload</b> <i>W</i><sub>tot</sub> (mA·min/week) or "
                       "<b>The Number of Patients per week</b> <i>N</i> (NCRP 147 average for a radiographic room: "
                       "120), a whole number; an average, such as the patients of a year / 52, goes in the total "
                       "workload, which may have decimals. It applies to every barrier, unless a barrier ticks "
                       "<b>Different Workload</b>.",
                       "<b>Floor Plan</b> (section 8), <b>2D / 3D View</b> (section 9), <b>Calculate all barriers"
                       "</b> and <b>Export to Excel</b> (section 10)."])]
    story += [P("Every barrier other than the floor and the ceiling is a <b>wall</b> or a <b>door</b>, with a name:")]
    story += [bullets(["<b>Add a wall or a door</b>: the arrow up of <b>Number of Barriers</b> opens <b>Add a barrier"
                       "</b> (" + fig("barrier_dialog.png") + "). Choose <b>Wall</b> or <b>Door</b> and type its "
                       "name, or leave the name empty for the next one (<b>Wall 5</b>, <b>Door 2</b>, ...). Its tab "
                       "is added at the end when you press <b>Add</b>. Every click opens one more window (a double "
                       "click, two), one below the other, so you can add several barriers at once; the room keeps "
                       "working while they are open. The arrow down removes the last barrier. The mouse wheel over "
                       "the field, or an arrow held down, does not change the barriers.",
                       "<b>Rename</b>: double-click the tab of a wall or door (or right-click it). The same window "
                       "renames it and makes a wall a door, or a door a wall. The <b>Floor</b> and the <b>Ceiling"
                       "</b> keep their names. In a department the same window also says which wall of another room "
                       f"this one is (<b>Shared with</b>, section {sec('Walls shared by two rooms')}).",
                       "<b>Every barrier of a room has its own name</b>, whatever the capitals: a name already used "
                       "is shown in red and cannot be given. The names are those of the results, the floor plan, "
                       "the 2D / 3D view and the Excel report, and they are saved with the project.",
                       "<b>A new door</b> starts as a secondary barrier (X-ray and fluoroscopy rooms) of lead, a "
                       "lead-lined door (NCRP 147 2.3.3.1); in a mammography room of wood, a solid-core door "
                       "(NCRP 147 5.5). Change them as you need; a wall that becomes a door gets them only where "
                       "nothing is entered. A new wall starts empty. Walls and doors both take 0.3 m to the person "
                       "beyond them (section 2.4).",
                       "On the <b>floor plan</b> the walls traced are the walls of the room in the order of their "
                       "tabs, and the doors traced its doors (section 8). In the <b>2D / 3D view</b> a door lies on "
                       "a wall, 2.1 m high, and the radiation that crosses it goes through the door (section 9)."])]
    story += figure("barrier_dialog.png", "Adding a barrier: a wall or a door, and its name (empty: the next default "
                                          "name).", width=80 * mm)
    story += H2("Radiation on a barrier")
    story += [P("Each barrier tab starts with the radiation that reaches it. " + fig("xray_floor.png") + " shows the floor "
                "of the example: "
                "a primary barrier.")]
    story += figure("xray_floor.png", "A primary barrier (the floor) with bucky preshielding: its distance <i>d</i><sub>P</sub>, "
                                      "1.00 m to the floor plus 1.3 m beyond it, and two materials.")
    story += [steps(["<b>Select the number of types of radiation on the barrier</b>: how many workload "
                     "distributions irradiate it; each gets its own block (#1, #2, ...).",
                     "<b>Select Radiation Type</b>: <b>Primary</b> if the useful beam is aimed at the barrier (floor, "
                     "chest bucky wall, cross-table wall), otherwise <b>Secondary</b> (leakage and scatter only).",
                     "<b>Workload Distribution</b>: <b>X-Ray Room</b> and the room in the list (e.g. <i>Rad Room "
                     "(floor or other barriers)</i>), or <b>Give kVp</b> for a single-kVp transmission curve. The "
                     "list shows the NCRP 147 distributions first and, below a line, those of the literature, whose "
                     "names end with their source (table in section 4.8). With kVp you write a primary air kerma "
                     "yourself; a secondary one you write, or the program finds it at the scattering angle you give "
                     f"(section {sec('Scatter at an angle')}). For a primary beam you also choose the "
                     "transmission data, NCRP 147 or modern "
                     "digital radiography (section 4.9). Every radiation type needs it: it goes through the barrier "
                     "with these transmission data (section 2.2).",
                     "Primary radiation: <b>Use Factor</b> <i>U</i> (NCRP 147: floor 0.89, cross-table wall 0.09, "
                     "wall No. 3 0.02, chest bucky 1; Kirby et al. 2023: 1, section 4.10), the <b>Primary Unshielded "
                     "Air Kerma</b> <i>K</i><super>1</super><sub>P</sub> (filled in when the distribution has one) "
                     "and, behind an image receptor, <b>Preshielding</b>: <b>Bucky</b> or <b>Cross-table</b>. "
                     "Secondary radiation: the unshielded air kerma, below.",
                     "<b>Distance from the Source to the Barrier</b> (m), after the radiation choices; its label "
                     "names it, <b><i>d</i><sub>P</sub></b> for primary radiation (section 2.4). Next to it <b>+ to the person beyond "
                     "it</b> (walls and doors 0.3 m, ceiling 0.5 m, floor 1.3 m), which you can change, and the "
                     "distance the program calculates with, e.g. <b><i>d</i><sub>P</sub> = 2.30 m</b>. Under the first distance, "
                     "<b>Enter the whole distance, to the person beyond the barrier (nothing added)</b> lets you "
                     "type the whole distance instead."])]
    story += [P(f"For secondary radiation ({fig('xray_secondary.png')}) choose where the unshielded air kerma comes from:")]
    story += figure("xray_secondary.png", "A secondary barrier: the unshielded secondary air kerma suggested by NCRP "
                                          "147, leakage and side-scatter, so the distance is <i>d</i><sub>sec</sub>.",
                    crop=(0, 0, 1175, 732))
    story += [bullets(["<b>Select Unshielded Secondary Air Kerma — Suggested</b>: the value of the workload "
                       "distribution; the label names its source (NCRP 147, or the article of a distribution of the "
                       "literature). Then <b>Leakage "
                       "Radiation</b> with <b>Leakage and Side-Scatter</b> (walls and doors beside the patient), "
                       "<b>Leakage and Forward/Backscatter</b> (floor and ceiling, in line with the beam) or <b>Only "
                       "Leakage</b>; or <b>Side-Scatter</b> or <b>Forward/Backscatter</b> alone.",
                       "<b>Field size</b>, next to the scatter types: the suggested air kerma assumes the field of "
                       "NCRP 147 Table 4.7 for the workload distribution, shown in the two boxes. Tick it and give "
                       "your field <i>F</i> (cm², the image receptor) at <i>d</i><sub>F</sub> (m, e.g. the SID): the "
                       f"scatter is scaled to it, the leakage is not ({fig('field_size.png')}, section "
                       f"{sec('Scatter and the size of the field')}). It is there only when the air kerma has scatter "
                       "in it.",
                       "<b>At an angle θ</b>, under Field size: the scatter at the angle you give (20–140°) instead of "
                       "90° or 135°, made from the workload of each kVp of the distribution (NCRP 147, Kirby et al. "
                       f"2023, Chen et al. 2013; section {sec('Scatter at an angle')}).",
                       "<b>Write Unshielded Secondary Air Kerma</b>: your own <i>K</i><super>1</super><sub>sec</sub> "
                       "in mGy per patient at 1 m. Its <b>Field size</b>, under it, scales the whole value from the "
                       "field it was given for to yours (section "
                       f"{sec('Scatter and the size of the field')}).",
                       "The distance then follows, named after the choice: <b><i>d</i><sub>L</sub></b> for only leakage, <b><i>d</i><sub>S</sub></b> for "
                       "side-scatter or forward/backscatter alone, <b><i>d</i><sub>sec</sub></b> for leakage and scatter together "
                       "(and for an air kerma you write).",
                       "<b>Different Workload</b>: this distribution has its own workload instead of the room's."])]
    story += figure("field_size.png", "Wall 3 of the example X-ray room with the scatter of a 35 × 43 cm field at "
                                      "1 m (Field size), and the height of its shielding next to Select Materials.",
                    width=150 * mm, crop=(0, 235, 1175, 820))
    story += H2("Materials")
    story += [bullets(["<b>Select Materials</b>: how many materials, then choose each one (#1, #2, ...). You get a "
                       "thickness for each.",
                       "<b>The materials are</b>: <b>Each one alone</b> (alternatives) or <b>Layers of one barrier"
                       f"</b> (section {sec('Several materials in one barrier')})."])]
    story += [P(f"With layers ({fig('xray_layers.png')}), #1 is on the room side and the last material outside. Give "
                "each material its <b>% of the shielding</b>; the shares start equal and must add up to 100 %. "
                "<b>Reverse order</b> swaps inside and outside.")]
    story += figure("xray_layers.png", "Wall 4 of the example: concrete on the room side and lead outside, half "
                                       "of the shielding each, with the planned thicknesses.",
                    width=150 * mm, crop=(0, 355, 1175, 730))
    story += [H3("Shielding height")]
    story += [P("Walls and doors have, next to <b>Select Materials</b>, the <b>Shielding height (m)</b>: how high above "
                "the floor their shielding goes, which NCRP 147 asks to give to the builder (5.8). It is normally "
                "<b>2.1</b> m (2.3.6); <b>2.5</b> m for a darkroom wall; <b>Up to the ceiling</b> when the ceiling "
                "above the room needs shielding added to its slab, so that the wall shielding meets it. You can type "
                "any height. It does not change the thickness; the report gives it, and the 3D view draws the wall in "
                "its materials up to it. When the ceiling has its slab as existing shielding and still needs more, "
                "the results of a wall that stops below the ceiling say so.")]
    story += [H3("Existing shielding")]
    story += [P("Below the materials, tick <b>The barrier already has shielding (existing)</b> when the barrier "
                f"already has some: a floor slab, a concrete or brick wall, lead put in earlier ({fig('existing_floor.png')}, "
                f"section {sec('Existing shielding')}).")]
    story += [steps(["<b>Existing materials, from the room side out</b>: how many (1 to 3), then for each its "
                     "material and its thickness in mm. For a slab poured on a steel deck give its minimum "
                     "thickness (NCRP 147 2.3.5.3).",
                     "<b>Put the new materials</b>: <b>outside it</b> (beyond the existing shielding) or <b>on its "
                     "room side</b>. The order counts; while it is not decided, calculate both and take the "
                     "larger.",
                     "Press <b>Calculate</b>: the thickness of each material above is now the thickness to "
                     "<b>add</b> (<b>none needed</b> when the existing shielding is enough alone). The results say "
                     "<i>In addition to the existing ...</i>, and the planned-thickness check, the check of the "
                     "patients, the 2D / 3D view and the report count the existing shielding."])]
    story += figure("existing_floor.png", "The floor of the example CT room: an existing concrete slab of 100 mm, "
                                          "and the lead or concrete to add on its room side.", width=150 * mm)
    story += H2("Checking a planned thickness")
    story += [P("Tick <b>Check the dose beyond the barrier with a planned thickness</b> and type the thickness of "
                "each material you intend to install (mm). With layers the planned thicknesses go in the "
                "<b>planned</b> column. The results then show the weekly dose beyond the barrier, with the existing "
                "shielding in its place, and whether it meets <i>P</i>. Untick it to see only the required "
                "thickness; the values you typed are kept.")]
    story += H2("Area, occupancy and design goal")
    story += figure("xray_area.png", "The end of a barrier tab: area, occupancy factor, design goal, the option of "
                                     "a further area, Calculate, and under it the check of the patients (Wall 3 of "
                                     "the example: one gypsum board allows only some of the 120 patients a week).",
                    crop=(0, 0, 1175, 425))
    story += [bullets(["<b>Shielding Area</b>: Controlled, Uncontrolled or Supervised. It fills in the design goal "
                       "<i>P</i>.",
                       "<b>Write occupancy factor (T)</b>, <b>or select Location (Suggested NCRP 147)</b>: the "
                       "location beyond the barrier gives <i>T</i> from NCRP 147 Table 4.1 (section "
                       f"{sec('Occupancy factors T (Table 4.1)')}), or you type it: more than 0 and at most 1, as a "
                       "decimal or a fraction (0.2 or 1/5). <i>T</i> = 0.2 with <i>P</i> = 0.02 gives the same "
                       "thickness as <i>T</i> = 1 with <i>P</i>/<i>T</i> = 0.1. In a controlled area the box starts "
                       "with 1, selected, so that what you type replaces it.",
                       "<b>Shielding Design Goal</b> (mGy/week): filled in from the area; you can change it.",
                       "<b>Calculate</b>: calculates this barrier. <b>Calculate all barriers</b> at the top "
                       "calculates every barrier of the room."])]
    story += [H3("A further area")]
    story += [P("Tick <b>Also check an area further away (NCRP 147 4.1.3)</b> when the area just beyond the barrier is "
                "not the one that needs most: a corridor, say, with an office across it "
                f"({fig('further_area.png')}, section {sec('A further area beyond a barrier')}). Then give:")]
    story += [bullets(["<b>Further than the person beyond the barrier by (m)</b>: how much further from the source that "
                       "person is, e.g. the width of the corridor;",
                       "<b>Location</b> and <b>T</b>: what the area is; the location gives <i>T</i> from NCRP 147 "
                       "Table 4.1, and you can change it;",
                       "<b>Area</b> and <b>P</b>: controlled or uncontrolled, which gives its design goal."])]
    story += [P("The results give, for each material, the larger thickness of the two areas, and say which one governs "
                "(<i>Also the area 2 m further (Administrative or clerical offices, T 1, P 0.02): it governs</i>).")]
    story += figure("further_area.png", "Wall 3 of the example X-ray room: the corridor just beyond it, and an "
                                        "office across the corridor, 2 m further.", crop=(0, 30, 1175, 580))
    story += [H3("How many patients the barrier allows")]
    story += [P("Under <b>Calculate</b>, a check of its own: tick <b>Check how many patients per week the barrier "
                "allows</b> (CT: procedures). It answers under it, and in the results, with the barrier as it will "
                "be built: the planned thicknesses and the existing shielding, or the existing shielding alone "
                f"(section {sec('How many patients a barrier allows')}). For example <i>With the planned Gypsum "
                "Wallboard 15.9 mm: up to 54 patients/week (×0.45 the present workload)</i>: in red, because the "
                "barrier is not enough for the present workload. Without a planned thickness or existing "
                "shielding it says what to give. With a further area it takes the more demanding of the two and "
                "says so; a wall shared with another room gives the workload of each room.")]
    story += H2("Results")
    story += [P("The results tab has one line per barrier with the thickness of each material (" + fig("xray_results.png") + "). "
                "<font color='%s'>Green</font> means no shielding is needed. Layers show which material is inside "
                "and outside. Below them, when they apply: the existing shielding, the further area and which area "
                "governs, the room that shares the wall, the dose beyond with the planned thickness in every area "
                "(%s or %s) and the patients the barrier allows."
                % (OK, MET, EXCEEDED))]
    story += figure("xray_results.png", "The results of the example X-ray room.", width=88 * mm,
                    crop=(0, 0, 650, 680))
    story += H2("When something is missing")
    story += [P("If a barrier cannot be calculated, a window lists what is missing and how to fill it in "
                "(" + fig("missing_dialog.png") + "). The empty fields turn red, the barrier tab is opened, and the cursor goes to the first "
                "field when you close the window. The results tab shows <font color='%s'>Missing: ...</font> for "
                "that barrier until it is calculated." % BAD)]
    story += figure("missing_dialog.png", "The Missing data window, here for a barrier without distance.",
                    width=125 * mm)
    story += H2("Fluoroscopy rooms and the workload distributions of each room")
    story += [P("A <b>Fluoroscopy Room</b> (start screen or <b>File › New... › Design Fluoroscopy Room</b>) is "
                "designed exactly like an X-ray room; only its workload distributions differ. Each kind of room "
                "offers its own, NCRP 147 first and then, below a line in the list, those of the literature:")]
    story += table([["Room", "NCRP 147 (Table 4.3)", "Literature"],
                    ["X-Ray room", "Rad Room (chest bucky), Rad Room (floor or other barriers), Rad Room (all "
                                   "barriers), Chest Room",
                     "DR Room (chest bucky / floor / cross-table wall / all barriers) – Kirby 2023; Pediatric DR "
                     "(the same four) – Kirby 2023 (section 4.10); Rad Room (floor / chest bucky / all barriers) – "
                     "Chen 2013 (section 4.12); Orthopedic Room, table bucky (DR 600) – Li 2024 (section 4.9)"],
                    ["Fluoroscopy Room", "Fluoroscopy Tube (R&amp;F room), Rad Tube (R&amp;F room), Cardiac "
                                         "Angiography, Peripheral Angiography; below a line, Rad Room (chest "
                                         "bucky), Rad Room (floor or other barriers), Rad Room (all barriers)",
                     "Angiography, Electrophysiology, Haemodynamics, Neuroangiography, Vascular Surgery – Biondi "
                     "2024 (section 4.11)"],
                    ["Mammography Room", "Mammography Room", "Digital Mammography (FFDM) – Judge 2013 (section 6.2); "
                                                             "Digital Breast Tomosynthesis – Yang 2017 and – Li 2013 "
                                                             "(section 6.1)"]],
                   [32, 64, 74])
    story += [P("In an R&amp;F room the fluoroscopy tube gives secondary radiation only (the image receptor stops its "
                "beam), while the radiographic tube can aim at the floor or a wall: choose <b>Rad Tube (R&amp;F "
                "room)</b> as a primary radiation type there (NCRP 147: 5.9 mGy per patient at 1 m). A barrier "
                "reached by both tubes gets two radiation types. Patients who have only radiographs in the room take "
                "the <b>Rad Room</b> distributions, with their own number of patients (<b>Different Workload</b>), "
                "as the floor of the R&amp;F room of NCRP 147 (Section 5.4.2: 20 fluoroscopy and 60 radiographic "
                "patients a week; the example <b>5.4</b> of <b>File › Examples › NCRP 147 examples</b>).")]
    story += H2("Transmission data for a kVp: modern digital radiography")
    story += [P("The NCRP 147 transmission data of radiographic beams come from systems installed before 2000. "
                "Modern digital radiography (DR) units have more beam filtration, so their beams are harder. For a "
                "<b>primary</b> radiation type given by its kVp (<b>Give kVp</b>), the list next to the kVp chooses "
                "the transmission data:")]
    story += figure("kvp_data.png", "A primary beam at 80 kVp with the DR 600 data and the added copper filtration.")
    story += table([["Transmission data", "Source", "kVp", "Materials"],
                    ["NCRP 147", "NCRP Report No. 147 (Archer et al.)", "25–150 kVp", "all six"],
                    ["DR 600, default filtration (Li 2024)", "Li et al., Med. Phys. 2024, table 1",
                     "60–120 kV, every 10 kV", "lead, concrete, gypsum wallboard, steel"],
                    ["DR 600, +1 mm Al +0.1 mm Cu (Li 2024)", "Li et al., Med. Phys. 2024, table 2",
                     "60–120 kV, every 10 kV", "lead, concrete, gypsum wallboard, steel"]], [52, 50, 30, 38])
    story += [P("The DR data were calculated by Monte Carlo for broad beams matching the measured half-value layers "
                "of an Agfa DR 600 (a GE Revolution XR/d had similar values), with its default filtration or with "
                "1 mm Al + 0.1 mm Cu added. A kVp between the tabulated ones, or plate glass and wood, have no DR "
                "data: the program says so."),
              P("Li et al. also fit the transmission through concrete of a whole workload distribution, as an "
                "example: the primary beam of the table bucky of an orthopedic room with an AGFA DX-D 600 (their "
                "section 4: α = 0.04633 mm<super>−1</super>, β = 0.0644 mm<super>−1</super>, γ = 0.5964). It is the "
                "workload distribution <b>Orthopedic Room, table bucky (DR 600) – Li 2024</b> of the X-ray room. "
                "It has <b>concrete only</b> and <b>primary radiation only</b>; the article gives no air kerma per "
                "patient and no workload per patient, so write <i>K</i><super>1</super><sub>P</sub> yourself and "
                "give the workload as patients per week.")]
    kvp = VALUES["kvp_data"]
    rows = [["Transmission data", "Lead (mm)", "Concrete (mm)"]]
    for data, rec in kvp.items():
        thick = dict(rec["thickness"])
        rows.append([data, f"{thick['Lead']:.2f}", f"{thick['Concrete']:.0f}"])
    rec = next(iter(kvp.values()))
    story += [P(f"For example, the floor under a table at 80 kVp (120 patients/week, <i>U</i> = 0.89, "
                f"<i>K</i><super>1</super> = 5.2 mGy/patient, <i>d</i> = {rec['d']:.1f} m, an office below, "
                f"<i>P</i> = 0.02 mGy/week, no preshielding) needs:")]
    story += table(rows, [80, 35, 35])
    story += [P("The harder modern beams need noticeably more shielding than the NCRP 147 data suggest.")]
    story += kirby_section()
    story += biondi_section()
    story += chen_section()
    return story


def chen_section():
    workbook = load_workbook(EXCEL, data_only=True)
    kerma = {r[0]: r for r in literature_rows(workbook, "Chen 2013 kerma")}
    prim = {r[0]: r for r in literature_rows(workbook, "Chen 2013 prim abc")}
    sec = {r[0]: r for r in literature_rows(workbook, "Chen 2013 sec abc")}
    story = H2("Radiographic rooms in Taiwan: Chen et al. 2013")
    story += [P("Chen et al. (2013) surveyed for one week 10 750 projections of 6657 examinations in 13 radiographic "
                "rooms of nine hospitals in Taiwan (seven DR, five CR, one film). Their workload per patient is much "
                "lower than that of NCRP 147 (0.31 against 1.9 mA·min toward the floor, 0.11 against 0.6 toward the "
                "wall bucky), mainly because of fewer exposures per patient (1.6 against 3.4) and smaller patients. "
                "An <b>X-Ray room</b> offers their three workload distributions:")]
    story += [bullets(["<b>W<sub>norm</sub></b> (their table 1), <b>K</b><super>1</super><sub>P</sub> per patient at "
                       "1 m (table 4, calculated with PCXMC) and <b>use factors</b> (table 5: floor 0.98, cross-table "
                       "wall 0.02, wall bucky 1), filled in when the distribution is chosen.",
                       "<b>Transmission</b> through lead and concrete (their table 6); for secondary radiation their "
                       "<i>all barriers</i> fit, as they use it. The other materials have no data.",
                       "<b>Leakage and scatter</b>: the article gives none. They are made from their table 1 with the "
                       "method of NCRP 147 (Appendix C), as for Kirby et al., by <font name='Mono'>"
                       "tools/literature_data.py</font>. With the same method their table 1 gives their own "
                       "K<super>1</super><sub>P</sub> (0.88 against 0.89, 0.35 and 1.24) and their lead and concrete "
                       "transmission within 1 % (section 11.10)."])]
    rows = [["Workload distribution", "W<sub>norm</sub>", "K<super>1</super><sub>P</sub>",
             "K<super>1</super><sub>sec</sub> leakage + side / + forward", "Lead α, β, γ (primary / secondary)"]]
    for name, r in kerma.items():
        kp = "–" if r[9] is None else f"{r[9]:g}"
        rows.append([name, f"{r[1]:g}", kp, f"{fmt(r[6])} / {fmt(r[8])}",
                     f"{', '.join(f'{v:g}' for v in prim[name][1:4])} / {', '.join(f'{v:g}' for v in sec[name][1:4])}"])
    story += table(rows, [52, 18, 14, 40, 46])
    return story


def literature_rows(workbook, sheet):
    return [r for r in workbook[sheet].iter_rows(min_row=3, values_only=True)
            if isinstance(r[0], str) and isinstance(r[1], (int, float))]


def kirby_section():
    workbook = load_workbook(EXCEL, data_only=True)
    story = H2("Modern digital radiography: workloads of Kirby et al. 2023")
    story += [P("NCRP 147 took its workloads from a survey of film-screen rooms in the 1990s. Kirby et al. (2023) "
                "surveyed modern digital radiography (DR) from the DICOM header of every exposure: 203 294 exposures "
                "of four DR units of a general hospital (open 24 hours, 7 days a week; 2019 and 2021) and 25 415 of "
                "two units of a pediatric practice. For each barrier, the floor, the cross-table wall and the wall "
                "with the chest bucky, they give the workload in mA·min per patient in 5 kVp bins. Their mean "
                "workload, 1.36 mA·min per patient, is 44 % below that of NCRP 147 (2.45); the pediatric one is "
                "0.29. They counted on average 230 patients per week per room in the hospital and 57 in the "
                "pediatric practice."),
              P("The list of an X-ray room offers the three barriers and their sum, <i>all barriers</i>, for the "
                "general (<i>DR Room</i>) and the pediatric practice (<i>Pediatric DR</i>). Use them as the NCRP 147 "
                "ones: <i>chest bucky</i>, <i>floor</i> and <i>cross-table wall</i> for the primary beam on that "
                "barrier, <i>all barriers</i> for secondary radiation.")]
    story += figure("kirby_floor.png", "The floor of a DR room with the workload distribution of Kirby et al. 2023: "
                                       "the use factor and the primary air kerma are filled in.")
    story += [H3("From the spectrum to air kerma and transmission"),
              P("The article gives only the workload spectra. The program turns them into air kerma and "
                "transmission the way NCRP 147 made its own data from the spectra of its survey (Appendices B and "
                "C). This was computed once, by <font name='Mono'>tools/literature_data.py</font> of the source code, "
                "and stored in the sheets <i>Kirby 2023 kerma</i>, <i>Kirby 2023 prim abc</i> and <i>Kirby 2023 sec "
                "abc</i> of Data Shielding.xlsx:")]
    story += [bullets(["<b>Primary air kerma</b> per patient at 1 m: <i>K</i><super>1</super><sub>P</sub> = Σ "
                       "<i>K</i><super>1</super><sub>W</sub>(kVp) <i>W</i>(kVp), with the output of a tungsten-anode, "
                       "aluminium-filtered tube of NCRP 147 Fig. B.1: <i>K</i><super>1</super><sub>W</sub> = 1.222 − "
                       "5.664×10<super>−2</super> kVp + 1.227×10<super>−3</super> kVp<super>2</super> − "
                       "3.136×10<super>−6</super> kVp<super>3</super> mGy per mA·min.",
                       "<b>Scatter</b>: <i>K</i><super>1</super><sub>W</sub> <i>W</i> <i>a</i><sub>1</sub>(θ, kVp) × "
                       "10<super>−6</super> <i>F</i> / <i>d</i><sub>F</sub><super>2</super>, with the scatter fraction "
                       "of Fig. C.1, <i>a</i><sub>1</sub> = 1.6×10<super>−2</super> (kVp − 125) + 8.43 − 0.111 θ + "
                       "9.83×10<super>−4</super> θ<super>2</super> − 1.74×10<super>−6</super> θ<super>3</super>, at "
                       "90° (side-scatter) and 135° (forward/backscatter), and the fields of NCRP 147 Table 4.7: "
                       "1535 cm² at 1.83 m for the chest bucky, 1000 cm² at 1 m otherwise.",
                       "<b>Leakage</b>: 0.876 mGy/h at 1 m at 150 kVp and 3.3 mA through a 2.32 mm lead housing, "
                       "varying as kVp² (Equations C.6 to C.9).",
                       "<b>Transmission</b>: the transmission of each kVp (Table A.1) weighted by the air kerma of "
                       "that kVp and fitted to the Archer equation; for secondary radiation with 90° scatter and "
                       "leakage, as Table C.1. The kVp of a bin is its highest value, as in the article."])]
    story += [P("Applied to the NCRP 147 spectra (Table 4.2), the same calculation gives back NCRP 147: the primary "
                "air kerma within 4 % (Table 4.5), the secondary air kerma within 6 % (Table 4.7 has two significant "
                "digits), and the thickness for a transmission from 0.1 to 10<super>−5</super> within 1 % for lead, "
                "concrete and plate glass, 3 % for wood, 5 % for steel and 5.5 % for gypsum wallboard, the gypsum "
                "coming out thicker, on the safe side, at strong attenuation (Tables B.1 and C.1). <font "
                "name='Mono'>python tools/literature_data.py --check</font> prints the comparison.")]
    rows = [["Workload distribution", "W<sub>norm</sub> (mA·min/patient)", "K<super>1</super><sub>P</sub>",
             "K<super>1</super><sub>sec</sub> leakage + side-scatter",
             "K<super>1</super><sub>sec</sub> leakage + forward/back"]]
    for r in literature_rows(workbook, "Kirby 2023 kerma"):
        rows.append([r[0], f"{r[1]:.3g}", f"{r[9]:g}" if r[9] is not None else "–", fmt(r[6]), fmt(r[8])])
    story += table(rows, [62, 26, 18, 32, 32])
    story += [P("Air kerma in mGy per patient at 1 m.", "small"), Spacer(1, 4),
              H3("Use factor"),
              P("The workload of each barrier already includes how often the beam points at it (the workloads of "
                "the three barriers add up to the mean workload per patient), so <i>U</i> = 1 with all the patients "
                "of the room; the program fills it in. The use factors that Kirby et al. list separately (2021: "
                "floor 0.55, cross-table wall 0.03, chest bucky wall 0.42) must not be applied again."),
              P("Compared with NCRP 147, the floor needs less shielding (<i>K</i><super>1</super><sub>P</sub> 1.22 "
                "against 5.2 mGy per patient, with <i>U</i> = 1 against 0.89) but the chest bucky wall more (3.05 "
                "against 2.3): without dedicated chest rooms, the DR rooms take the chest images at 120 kVp. "
                "Section 11.7 works an example. For a pediatric room in a general hospital, which may later image "
                "adults, the general data are the safe choice (Kirby et al.).")]
    return story


def biondi_section():
    workbook = load_workbook(EXCEL, data_only=True)
    ncrp = {r[0]: r for r in workbook["Uns Air Kerma"].iter_rows(min_row=2, values_only=True) if r[0]}
    transmission = {r[0]: r for r in literature_rows(workbook, "Biondi 2024 sec abc")}
    story = H2("Interventional rooms: workloads of Biondi et al. 2024")
    story += [P("NCRP 147 has two workload distributions for angiography, cardiac and peripheral (the latter also for "
                "neuroangiography). Biondi et al. (2024) recorded with a dose monitoring system (DoseWatch) all "
                "214 697 exposures of the 3066 procedures of 2023 on a GE Innova IGS 540 and two Philips Azurion "
                "7M20, and give for five interventional rooms the workload per patient and the secondary "
                "transmission. A <b>Fluoroscopy Room</b> offers them:")]
    story += [bullets(["<b>Transmission</b>: their table 3, for lead, concrete and gypsum wallboard. Steel, plate "
                       "glass and wood have no data; the result says <i>No transmission data</i>.",
                       "<b>Unshielded secondary air kerma</b> per patient at 1 m: as their Equation 4 and NCRP 147 "
                       "(4.1.4), the NCRP 147 value of cardiac angiography (haemodynamics, electrophysiology) or of "
                       "peripheral angiography (angiography, neuroangiography, vascular surgery) times "
                       "<i>W</i><sub>site</sub> / <i>W</i><sub>norm</sub>. Every choice of the suggested air kerma "
                       "(leakage, side-scatter, forward/backscatter and their sums) is scaled so.",
                       "<b>Tube output</b>, under Field size: their Equation 3, when the output of the tube is known. "
                       "Type it in µGy/mAs at 1 m at 50, 70, 100 and 125 kVp, the kVp of NCRP 147 Table C.1 that "
                       "they give each range of their table 2: <i>K</i><super>1</super><sub>sec</sub> = Σ output × "
                       "workload of the range (mAs per patient) × 1/1000, their fraction of scatter.",
                       "<b>Workload</b>: the program takes <i>W</i><sub>site</sub> as the workload per patient, so a "
                       "total workload gives the same air kerma as the patients it stands for. Patients per week are "
                       "a whole number; an average, such as the procedures of a year / 52, goes in <b>Write total "
                       "Workload</b>: <i>W</i><sub>site</sub> × procedures / 52 mA·min.",
                       "<b>Secondary radiation only</b>: in fluoroscopy the image receptor stops the primary beam "
                       "(NCRP 147). With <b>Primary</b> the program asks for <i>Secondary radiation only</i>."])]
    rows = [["Workload distribution", "W<sub>norm</sub> (mA·min/patient)", "NCRP 147 scaled",
             "K<super>1</super><sub>sec</sub> leakage + side / + forward", "Lead α, β, γ"]]
    for r in literature_rows(workbook, "Biondi 2024"):
        w, base = r[6] / 60, ncrp[r[8]]
        rows.append([r[0], f"{w:.3g}", f"{r[8]} ({base[1]:g})", f"{fmt(base[6] * w / base[1])} / "
                                                                f"{fmt(base[8] * w / base[1])}",
                     ", ".join(f"{v:g}" for v in transmission[r[0]][1:4])])
    story += table(rows, [47, 28, 36, 33, 26])
    story += figure("biondi_barrier.png", "A wall of an angiography room with the data of Biondi et al. 2024 and "
                                          "their Equation 3: the tube output under Field size.",
                    crop=(0, 0, 1154, 640))
    story += [P("Their workloads per patient are much higher than those of NCRP 147 for peripheral work (angiography "
                "119 and vascular surgery 168 mA·min, against 64) and much lower for cardiac work (haemodynamics 21, "
                "against 160). Section 11.8 reproduces the example of the article.")]
    return story


def ct_and_mammography():
    story = H1("Designing a CT room")
    story += [P("Start with <b>CT Room</b> on the start screen or <b>File › New... › Design CT Room</b>. All CT "
                "barriers are secondary; the room data replace the workload of an X-ray room.")]
    story += figure("ct_room.png", "The example CT room: room data on the left, one tab per barrier.",
                    crop=(0, 0, 1180, 700))
    story += table([["Input", "Meaning", "NCRP 147 typical"],
                    ["Body / Head Procedures (weekly)", "Number of body and head CT procedures per week.", "–"],
                    ["Scans (phases) per procedure", "How many scans a procedure can have and, for scan 1, 2, ..., "
                                                     "the % of the procedures that have it, up to 20 scans "
                                                     "(section 2.6). The line below shows the mean number of "
                                                     "scans per procedure.",
                     "100 % + 40 % = 1.4"],
                    ["DLP per body / head scan (mGy·cm)", "Dose-length product of one scan (phase).",
                     "550 / 1200 mGy·cm"],
                    ["Tube voltage (kVp)", "The transmission data exist for 120 and 140 kVp.", "120 kVp"],
                    ["Distance from the CT Isocenter to the Barrier, <i>d</i><sub>sec</sub> (m)",
                     "To the barrier itself. Below it, <b>+ to the person beyond it</b> (walls 0.3 m, ceiling 0.5 m, "
                     "floor 1.3 m; you can change it) and the sum, or tick <b>Enter the whole distance</b> "
                     "(section 2.4).", "–"],
                    ["Materials", "NCRP 147 has CT transmission data for lead and concrete.", "–"]], [52, 88, 30])
    story += [P("Area, occupancy, design goal, layers, the existing shielding (" + fig("existing_floor.png") + "), "
                "the shielding height, a further area and the planned-thickness check work as in an X-ray room; "
                "the check under Calculate gives the body and head procedures per week that the barrier allows. "
                "The further area is that much further from the isocenter.")]

    story += H1("Designing a mammography room")
    story += [P("A mammography room is designed like an X-ray room, but every barrier is secondary: NCRP 147 "
                "assumes the image receptor stops the primary beam, so <b>Primary</b> cannot be chosen. Use the "
                "workload distribution <b>Mammography Room</b>, <b>Leakage and Side-Scatter</b> for the walls and "
                "door and <b>Leakage and Forward/Backscatter</b> for the floor and ceiling. The NCRP 147 average "
                "workload is 80 patients per week (<i>W</i><sub>norm</sub> = 6.7 mA·min per patient).")]
    story += figure("mammo_room.png", "The example mammography room: total workload 536 mA·min/week, i.e. 80 "
                                      "patients.", crop=(0, 0, 1175, 728))
    story += [P("If the chosen data have no transmission values for a material, the result says <i>No "
                "transmission data for</i> that material.")]
    story += H2("Digital breast tomosynthesis")
    story += [P("NCRP 147 has no DBT data. The program offers two workload distributions of a Hologic Selenia "
                "Dimensions, both from the MGH group: <b>Digital Breast Tomosynthesis – Yang 2017</b>, from a survey "
                "of 310 421 acquisitions on eight rooms, and <b>Digital Breast Tomosynthesis – Li 2013</b>, from 343 "
                "examinations in three rooms. With Yang 2017:")]
    story += [bullets(["<b>Transmission</b>: their table 8, scatter from a typical Hologic DBT room, for lead, "
                       "concrete, steel, gypsum wallboard, plate glass and wood. These beams are more penetrating "
                       "than the NCRP 147 mammography data.",
                       "<b>Unshielded scatter air kerma</b>: with <b>Select Unshielded Secondary Air Kerma — "
                       "Suggested (Yang et al. 2017)</b>, choose the examination: <b>2D</b>, <b>3D "
                       "(tomosynthesis)</b> or <b>2D + 3D</b>. Or choose <b>Write</b> and type your own value.",
                       "<b>Workload</b>: give <b>The Number of Patients per week</b>; Yang et al. give no workload "
                       "per patient (W<sub>norm</sub>)."])]
    story += figure("dbt_barrier.png", "A DBT barrier: the suggested scatter air kerma of a 2D + 3D examination.",
                    crop=(0, 0, 1154, 688))
    story += [P("Their table 9 gives the air kerma per view at 1 m. An examination has both breasts, each with a CC "
                "and an oblique (MLO) view; for a wall, one oblique view has the beam toward it (T) and one away "
                "(A), as in their example:")]
    story += table([["mGy per view at 1 m", "CC", "Oblique toward (T)", "Oblique away (A)", "Per patient (2 CC + T + A)"],
                    ["2D", "6.07 × 10<super>−3</super>", "4.83 × 10<super>−2</super>", "6.49 × 10<super>−3</super>",
                     "0.0669"],
                    ["3D", "7.85 × 10<super>−3</super>", "1.43 × 10<super>−2</super>", "7.89 × 10<super>−3</super>",
                     "0.0379"],
                    ["2D + 3D", "", "", "", "0.1048"]], [34, 30, 34, 34, 38])
    story += [P("The oblique view toward the barrier dominates: the scatter of Hologic DBT units peaks about 25° "
                "from the beam. Section 11 reproduces the example of the article.", "small"), Spacer(1, 6)]
    story += [P("With <b>Digital Breast Tomosynthesis – Li 2013</b>:")]
    story += [bullets(["<b>Workload</b>: W<sub>norm</sub> = 12.61 mA·min per patient (their table IV(c), 2D + 3D, "
                       "screening and diagnosis), so the total workload can be given too.",
                       "<b>Transmission</b>: their table V(a), the primary radiation of this workload (W/Rh, W/Ag and "
                       "W/Al), which they take for the secondary radiation as NCRP 147 does; six materials.",
                       "<b>Unshielded scatter air kerma</b>: <b>Toward the barrier (Yang 2016)</b>. Yang et al. (2016) "
                       "measured the scatter around the same unit with this workload (their reference 4) and give it "
                       "per patient at 1 m toward each barrier (table V, below). The choice starts with the kind of the "
                       "barrier (wall or door, floor, ceiling) and the average technique; Yang et al. 2016 give no "
                       "transmission of their own."])]
    story += table([["mGy per patient at 1 m", "Wall / door", "Floor", "Ceiling"],
                    ["Average technique: 30 kVp W/Ag (2D) + 30 kVp W/Al (3D)", "0.0176", "0.164", "0.0366"],
                    ["High technique: 35 kVp W/Ag (2D) + 40 kVp W/Al (3D)", "0.0332", "0.307", "0.0733"]],
                   [86, 28, 28, 28])
    story += [P("The peak of the scatter at about 25° falls on the floor, so its value is the highest. For the floor "
                "at 1.2 m, 100 patients a week and the high technique, Yang et al. find ~35 mm of concrete with the "
                "40 kVp W/Al transmission of Li et al. 2012 (section 6.3); with the transmission of the whole "
                "workload (Li 2013) the program finds about 23 mm.")]
    workbook = load_workbook(EXCEL, data_only=True)
    judge = [r for r in workbook["Judge 2013"].iter_rows(min_row=3, values_only=True) if isinstance(r[1], (int, float))]
    story += H2("Digital mammography (FFDM): Judge et al. 2013")
    story += [P("Judge et al. (2013) measured the scatter at 1 m around three full-field digital mammography units of "
                "the Irish screening programme, with a 6 cm breast phantom, in three planes and at 0–165°. The "
                "workload distribution <b>Digital Mammography (FFDM) – Judge 2013</b> offers, under the suggested "
                "secondary air kerma, the unit:")]
    rows = [["Unit", "Maximum scatter at 1 m, one exposure (µGy)", "K<super>1</super><sub>sec</sub> (mGy per "
                                                                     "patient)", "Transmission (Mo/Mo, Simpkin)"]]
    for unit, dose, exposures, k1, kvp in judge:
        rows.append([unit, f"{dose:g}", f"{k1:g}", f"{kvp} kVp"])
    story += table(rows, [40, 52, 40, 38])
    story += [P("K<super>1</super><sub>sec</sub> is their maximum scatter (at 100 mAs, 13.5 mAs for the Philips, more "
                "than clinical) times the 4 exposures of a patient, as they work out the annual scatter. For the "
                "barriers they used Simpkin's Mo/Mo transmission (that of NCRP 147) without saying at which kVp; 30 "
                "kVp reproduces their GE and Hologic results and 35 kVp their Philips results exactly (section "
                "11.10), so the program uses these. Give the workload as patients per week, a whole number: their "
                "example, 40 patients a day for 5 days, is 200 a week.")]
    story += H2("Transmission at a kVp: mammography and DBT beams")
    story += [P("In a mammography room, <b>Give kVp</b> has next to the kVp the choice of the transmission data, and "
                "the kVp list follows it. The secondary radiation is taken as attenuated like the primary beam (NCRP "
                "147, Li et al.). Write the unshielded air kerma yourself.")]
    story += table([["Transmission data", "Beams", "kVp"],
                    ["NCRP 147", "Its secondary data (unchanged)", "30 (mammography), 50–150"],
                    ["Mo/Mo (NCRP 147)", "Mo target and filter (Simpkin), NCRP 147 Table A.1", "25, 30, 35"],
                    ["W/Al (Li 2012)", "Hologic Selenia Dimensions, tomosynthesis (3D)", "25, 30, 35, 40, 45, 49"],
                    ["W/Rh (Li 2012)", "Hologic Selenia Dimensions, 2D", "25, 30, 35, 39"],
                    ["W/Ag (Li 2013)", "Hologic Selenia Dimensions, 2D", "25, 30, 35, 39"]], [40, 90, 40])
    story += [P("Li et al. calculated the broad-beam transmission by Monte Carlo from spectra measured on the unit, for "
                "the six materials. Their tables reproduce each other: weighting the single-kVp curves by the air "
                "kerma of each kVp bin of the Li 2013 workload gives their table V(a) within 0.3 % (section 11.10). "
                "With <b>Give kVp</b> in a mammography room and a total workload, W<sub>norm</sub> is that of the "
                "NCRP 147 mammography room, 6.7 mA·min per patient.")]
    return story


def department():
    story = H1("Departments")
    story += [P("A department holds several rooms of any type: one floor, one floor plan, one report. Start with "
                "<b>Department</b> on the start screen or <b>File › New... › Design Department</b>.")]
    story += figure("department_rooms.png", "The Rooms tab of the example department.", crop=(0, 0, 1210, 470))
    story += [steps(["Type the <b>Department Name</b>. <b>New Department</b> adds another department in its own tab.",
                     "Set the <b>Number of Rooms</b>. For each room type a <b>Room Description</b> (its name) and "
                     "choose its type: <i>X-Ray room</i>, <i>Fluoroscopy Room</i>, <i>CT Room</i> or <i>Mammography Room</i>.",
                     "Press <b>Design</b>: the room opens as a tab inside the department, and its results as a tab "
                     "on the right. The two tabs stay together: choosing one shows the other.",
                     "Design each room as in sections 4 to 6.",
                     "<b>Floor Plan</b>, <b>2D / 3D View</b> and <b>Export to Excel</b> on the Rooms tab work on all "
                     "the rooms of the department."])]
    story += figure("department_room.png", "A room of the department with its results.")
    story += H2("Walls shared by two rooms")
    story += [P("A wall between two rooms of the department is one wall: its thickness must protect the people of "
                "each room from the radiation of the other. Say so once, in either room "
                f"({fig('shared_dialog.png')}):")]
    story += [steps(["Double-click the tab of the wall (or door) to open its window, as to rename it.",
                     "At <b>Shared with</b> choose the wall or door of the other room that it is: the list has "
                     "every wall and door of the other designed rooms of the department. <i>— no other room —</i> "
                     "undoes it. Press <b>OK</b>.",
                     "Give the wall the same materials in both rooms, and calculate both: the radiation, distances, "
                     "occupancy and design goal of each side are those of its own tab."])]
    story += figure("shared_dialog.png", "Wall 2 of the CT room of the example department is Wall 4 of the "
                                         "mammography room.", width=80 * mm)
    story += [P("Each tab then shows, for each of its materials, the larger thickness of the two rooms (section "
                f"{sec('A wall shared by two rooms')}), and says which room governs ({fig('shared_results.png')}). "
                "The planned-thickness check gives the dose beyond on both sides, and the check of the patients the "
                "workload that each of the two rooms may have; a further area of either room counts too. While the "
                "other room is not calculated, or misses "
                "data, the results say so and count only the radiation of this room. Removing the wall, or the "
                "room, ends the link; renaming it does not.")]
    story += figure("shared_results.png", "The results of the CT room: Wall 2 is shared with the mammography room, "
                                          "and the CT room governs.", width=100 * mm, crop=(0, 0, 672, 360))
    return story


def floor_plan():
    story = H1("Floor plan")
    story += [P("<b>Floor Plan</b> opens the drawing of the room or department. Trace the walls on it, place the "
                "source and say what lies beyond each wall: the program measures the distances, suggests <i>T</i> "
                "and <i>P</i> and fills in the barriers.")]
    story += figure("plan_editor.png", "The floor plan of the example department, Wall 4 of the X-ray room "
                                       "selected.")
    story += [steps(["<b>Load drawing (PDF / PNG / JPG)</b>: the architect's drawing (for a PDF, choose the page). "
                     "Without a drawing you work on a 1 m grid.",
                     "<b>Set scale</b>: click two points whose real distance you know (e.g. a dimension line) and "
                     "type it in metres.",
                     "Choose the <b>Room</b> and give its <b>Floor-to-ceiling height</b>, the <b>Source height "
                     "above floor</b> and the <b>Floor-to-floor height</b> (3 to 5 m). The distance to the floor is "
                     "the source height and to the ceiling the rest; beyond them the people are 1.7 m above the "
                     "floor below and 0.5 m above the floor above (section 2.4).",
                     "<b>Draw walls</b>: click the corners in order; click the first corner or press Enter to close. "
                     "<b>Straight walls (90°)</b> keeps them square; Backspace removes the last corner, Esc cancels. "
                     "The walls traced are the walls of the room, in the order of their tabs: the first is "
                     "<b>Wall 1</b> (or the name you gave it), the next <b>Wall 2</b>, and so on.",
                     "<b>Place source</b>: the X-ray tube (CT: the isocenter; mammography: the unit).",
                     "<b>Add door</b>: click its two edges on a wall. Every door traced is one more door of the "
                     "room, in order: <b>Door 1</b>, then <b>Door 2</b>, ... <b>Remove door</b> (or Delete) removes "
                     "the selected door from the plan.",
                     "<b>Select a wall / door</b>: click a wall or a door and choose what is <b>Beyond it</b> (sets "
                     "<i>T</i>), "
                     "its <b>Area</b> (sets <i>P</i>) and whether the <b>Primary beam</b> is aimed at it. The yellow "
                     "note shows the distance and the suggested values; <b>Apply to this barrier</b> writes them in "
                     "(the distance to the barrier and the distance beyond it, so <b>Enter the whole distance</b> "
                     "is unticked).",
                     "<b>Floor and ceiling</b>: what is below and above, and whether the primary beam hits the floor.",
                     "<b>Apply everything to the room</b> fills in every barrier at once. When the plan has more "
                     "walls or doors than the room tab, they are added to the room."])]
    story += note("Mouse wheel: zoom. Right-drag: move the drawing. Walls of neighbouring rooms that touch are "
                  "recognised, so 'Adjacent x-ray rooms' is suggested for them.")
    return story


def viewer():
    story = H1("2D / 3D view")
    story += [P("<b>2D / 3D View</b> shows the room, or the whole department, with the materials of every barrier, "
                "the dose beyond it and, if you wish, the radiation around the source. Without a floor plan the "
                "room is drawn schematically, each wall at its entered distance from the source and each door on "
                "the wall whose distance is closest to its own (side by side when they share a wall).")]
    story += figure("viewer_materials.png", "The 2D plan of the example X-ray room, walls shown by their "
                                            "materials, and the list of barriers.")
    story += H2("Walls and materials")
    story += [bullets(["<b>Walls show: Materials</b>: every wall in the colours of its materials (the planned ones, "
                       "or else the required ones). <b>Bands across</b> a wall are layers, the inside one on the room "
                       "side; <b>stripes along</b> a wall are materials that are each enough alone. The label beside "
                       "each wall names its materials (e.g. <i>Concrete + Pb</i>, <i>Pb or Concrete</i>).",
                       "<b>Walls show: Dose beyond vs goal P</b>: green when the barrier meets <i>P</i>, red when it "
                       "exceeds it, with the weekly dose beyond.",
                       "The yellow bar on top counts the barriers that meet <i>P</i> and names those that do not."])]
    story += H2("The list of barriers")
    story += [P("On the right, <b>Barriers and their materials</b> lists every barrier of every room shown: its "
                "materials from the room side out (the existing shielding as <i>existing</i>, with its thickness "
                "under Planned), the <b>Required</b> and <b>Planned</b> thickness of each (mm) and "
                "the <b>Dose beyond</b>. Pick a barrier to mark it on the 2D plan; click a wall on the plan to find "
                "it in the list.")]
    story += H2("Pointing at a wall")
    story += [P("Rest the pointer on a wall or door, in 2D or 3D, to see its materials, their thicknesses and the "
                "dose beyond it (" + fig("viewer_note.png") + "). Inside a room the note gives the floor and ceiling; with the radiation "
                "map on, it also gives the air kerma at that point.")]
    story += figure("viewer_note.png", "The note of Wall 3: one planned gypsum board is not enough.",
                    crop=(500, 300, 1500, 960), width=130 * mm)
    story += H2("Radiation map")
    story += [P("<b>Radiation map</b> colours the weekly air kerma (mGy/week, logarithmic scale, without occupancy) "
                "around the source. Inside the room it falls as 1/<i>r</i><super>2</super>, with the primary beam "
                "toward the barriers it is aimed at. At each wall it crosses, it drops by the transmission of all "
                "the materials of that wall (planned, or the required thickness), the walls of other rooms "
                "included. The dashed lines mark 0.02 and 0.1 mGy/week, the NCRP 147 goals with <i>T</i> = 1.")]
    story += figure("viewer_goal.png", "Dose beyond vs goal P, with the radiation map.", crop=(0, 140, 1130, 1000))
    story += H2("3D view and options")
    story += [bullets(["Each wall is drawn in its materials up to its shielding height (2.1 m unless you give "
                       "another), and bare above it; a door up to its own height.",
                       "The <b>3D view</b> tab shows the same rooms in 3D. Drag to rotate; pointing at a wall gives "
                       "its note, as in 2D.","<b>Ceiling (3D)</b> shows the ceiling; <b>Drawing (2D)</b> shows the loaded floor plan "
                       "under the rooms.",
                       "<b>Refresh</b> redraws with the latest inputs: press Calculate in the room tabs first.",
                       "The toolbar under the drawing zooms, moves and saves the picture."])]
    story += figure("viewer_3d.png", "The 3D view (drag to rotate).", crop=(0, 140, 1130, 1000))
    return story


def report_and_projects():
    story = H1("Report, projects and examples")
    story += H2("Excel report")
    story += [P("<b>Export to Excel</b> (in a room, or on the Rooms tab of a department) saves a workbook with "
                "three sheets. It uses the last calculation of every barrier, so press Calculate first. It shows "
                "only what the rooms use: a column that would be empty in every row (a material not chosen, the "
                "preshielding when there is none, the CT data of X-ray rooms) is left out, and so is a note on "
                "something the rooms do not have. The columns are wide enough for their headings and values.")]
    story += table([["Sheet", "Contents"],
                    ["Summary", "One row per barrier: room, barrier, area, location (source of T), T, P, ΣK, B, the "
                                "thickness of each material chosen, the dose beyond, the goal P (also in a further "
                                "area and, for a shared wall, toward the other room), the materials, the shielding "
                                "height of walls and doors, the existing shielding, the further area, the room that "
                                "shares the wall, the workload the barrier allows (when its check is ticked) and the "
                                "status (OK, met, EXCEEDED or what is missing). Notes on the method follow."],
                    ["Details", "One row per radiation type: workload distribution, source of K¹ (with the field "
                                "of the scatter, when one is given), preshielding, N, "
                                "U, T, K¹, the distance (<i>d</i><sub>P</sub>, <i>d</i><sub>L</sub>, "
                                "<i>d</i><sub>S</sub> or <i>d</i><sub>sec</sub>, with their subscripts): from the "
                                "source to the barrier, what is added to the person beyond it, and <i>d</i>, which "
                                "the program calculates with (with <b>Enter the whole distance</b> the typed distance "
                                "is <i>d</i> and nothing is added); then K."],
                    ["Rooms", "Room type and workload; for CT rooms the procedures, scans per procedure, DLP and "
                              "kVp; the number of barriers and how many are calculated."]],
                   [25, 145])
    rep = VALUES["xray_report"]
    head = rep["header"]
    pick = ["Barrier", "T", "P (mGy/week)", "ΣK (mGy/week)", "B", "Lead (mm)", "Concrete (mm)",
            "Gypsum Wallboard (mm)", "Dose beyond (mGy/week)"]  # the report has all of them for this room
    index = [head.index(name) for name in pick]
    rows = [["Barrier", "T", "P", "ΣK", "B", "Lead", "Concrete", "Gypsum", "Dose beyond"]]
    for row in rep["rows"]:
        cells = []
        for k, i in enumerate(index):
            v = row[i]
            cells.append("" if v is None else (v if isinstance(v, str) else (f"{v:g}" if k in (1, 2) else
                                                                             fmt(v) if k in (3, 4, 8) else
                                                                             f"{v:.2f}")))
        rows.append(cells)
    story += [P("The Summary of the example X-ray room (thicknesses in mm, air kerma in mGy/week):")]
    story += table(rows, [20, 12, 12, 22, 24, 17, 20, 19, 24])
    story += H2("Projects")
    story += [P("<b>File › Save project</b> writes everything (departments, rooms, every input, the floor plans and "
                "their drawings) into one <b>.shield</b> file; <b>Open project</b> brings it back. <b>New project"
                "</b> and <b>Exit</b> ask whether to save the current work first.")]
    story += H2("Examples")
    story += [P("<b>File › Examples</b> and the start screen open four examples with NCRP 147 typical values, "
                "already calculated: a radiology department, an X-ray room, a CT room and a mammography room. The "
                "same examples are files in the <b>Examples</b> folder next to the program (<b>Open from the "
                "Examples folder...</b>). Change any value and press Calculate to see its effect."),
              P("<b>File › Examples › NCRP 147 examples</b> opens the worked examples of Section 5 of NCRP 147, one "
                "file each in the folder <b>Examples\\NCRP 147</b>. Each opens with a short note: what each barrier "
                "is, and the result of NCRP 147 next to that of the program "
                f"({fig('ncrp_note.png')}). Section 11.9 compares them all, and the workbook <b>NCRP 147 examples - "
                "comparison.xlsx</b> in the same folder gives each calculation in detail."),
              P("<b>File › Examples › Examples of the literature</b> opens the worked examples of the articles whose "
                "data the program offers (Yang et al. 2017 and 2016, Judge et al. 2013, Biondi et al. 2024, Li et al. "
                "2024), from the folder <b>Examples\\Literature</b>, each with a short note of the values of the "
                "article and of the program; section 11.10 compares them.")]
    story += figure("ncrp_note.png", "The note of the example of Section 5.3 of NCRP 147 (the radiographic room): "
                                     "each barrier, what NCRP 147 finds and what the program finds.",
                    width=140 * mm)
    return story


def worked_examples():
    x, ct, mammo = VALUES["xray"], VALUES["ct"], VALUES["mammography"]
    story = H1("Worked examples")
    story += [P("These examples follow the built-in examples step by step. Open the example, select the barrier and "
                "compare: the program gives the same numbers. Small differences in the last digit come from "
                "rounding here.")]

    # ---------- secondary barrier ----------
    b3 = x["Wall 3"]
    dist = b3["distributions"][0]
    K = dist["N"] * dist["U"] * dist["T"] * dist["K1"] / dist["d"] ** 2
    close(K, b3["K_total"])
    B = b3["P"] / K
    lead, gyp = b3["params"]["Lead"], b3["params"]["Gypsum Wallboard"]
    x_lead, x_gyp = archer_thickness(lead, B), archer_thickness(gyp, B)
    close(x_lead, dict(b3["thickness"])["Lead"])
    close(x_gyp, dict(b3["thickness"])["Gypsum Wallboard"])
    board = archer_transmission(gyp, 15.9)
    dose = K * board
    close(dose, b3["check"]["dose"])
    two = K * archer_transmission(gyp, 31.8)
    three = K * archer_transmission(gyp, 47.7)
    story += H2("Secondary barrier: X-ray room, Wall 3 (corridor)")
    story += table([["Input", "Value", "Where it comes from"],
                    ["N", f"{dist['N']:g} patients/week", "Room workload (NCRP 147 average for a Rad Room)"],
                    ["Workload distribution", dist["distribution"], "Secondary radiation from the whole room"],
                    ["K<super>1</super><sub>sec</sub>", f"{dist['K1']:g} mGy/patient",
                     "Leakage and side-scatter at 1 m (NCRP 147)"],
                    ["U", f"{dist['U']:g}", "Secondary radiation"],
                    ["T", f"{dist['T']:g}", f"Location beyond: {b3['location']} (1/5)"],
                    ["d", f"{dist['d'] - b3['beyond']:.2f} + {b3['beyond']:g} = {dist['d']:.2f} m",
                     f"Source to wall, plus {b3['beyond']:g} m beyond it"],
                    ["P", f"{b3['P']:g} mGy/week", "Uncontrolled area"]], [38, 50, 82])
    story += formula(f"<i>K</i> = {dist['N']:g} × {dist['U']:g} × {dist['T']:g} × {dist['K1']:g} / "
                     f"{dist['d']:.2f}<super>2</super> = <b>{fmt(K)}</b> mGy/week<br/><i>B</i> = {b3['P']:g} / "
                     f"{fmt(K)} = <b>{fmt(B)}</b>")
    story += [P(f"With the secondary transmission parameters of the Rad Room (all barriers) distribution, lead "
                f"({params_text(lead)}) and gypsum wallboard ({params_text(gyp)}), the Archer equation gives:")]
    story += formula(f"lead <b>{x_lead:.2f} mm</b>&nbsp;&nbsp;&nbsp;or&nbsp;&nbsp;&nbsp;gypsum wallboard "
                     f"<b>{x_gyp:.1f} mm</b>")
    story += [P(f"The example plans one standard gypsum board of 15.9 mm. Its transmission is {fmt(board)}, so the "
                f"dose beyond is {fmt(K)} × {fmt(board)} = <b>{fmt(dose)} mGy/week</b> &gt; 0.02: {EXCEEDED}. "
                f"Two boards (31.8 mm) still give {fmt(two)} mGy/week; three boards (47.7 mm) give {fmt(three)} "
                f"mGy/week, which meets the goal. So does {x_lead:.2f} mm of lead.")]

    # ---------- primary barrier with preshielding ----------
    fl = x["Floor"]
    dist = fl["distributions"][0]
    K = dist["N"] * dist["U"] * dist["T"] * dist["K1"] / dist["d"] ** 2
    close(K, fl["K_total"])
    B = fl["P"] / K
    conc, lead = fl["params"]["Concrete"], fl["params"]["Lead"]
    pre = fl["preshielding"]
    total_c, total_l = archer_thickness(conc, B), archer_thickness(lead, B)
    close(total_c - pre["Concrete"], dict(fl["thickness"])["Concrete"])
    close(total_l - pre["Lead"], dict(fl["thickness"])["Lead"])
    T100 = archer_transmission(conc, 100 + pre["Concrete"])
    close(K * T100, fl["check"]["dose"])
    story += H2("Primary barrier with preshielding: X-ray room, floor")
    story += table([["Input", "Value", "Where it comes from"],
                    ["N", f"{dist['N']:g} patients/week", "Room workload"],
                    ["Workload distribution", dist["distribution"], "Primary beam on the floor"],
                    ["U", f"{dist['U']:g}", "NCRP 147 use factor of the floor"],
                    ["K<super>1</super><sub>P</sub>", f"{dist['K1']:g} mGy/patient", "Primary air kerma at 1 m"],
                    ["T", f"{dist['T']:g}", f"Below: {fl['location']}"],
                    ["d", f"{dist['d'] - fl['beyond']:.2f} + {fl['beyond']:g} = {dist['d']:.2f} m",
                     f"Source height, plus {fl['beyond']:g} m under the floor (person 1.7 m above the floor below, "
                     f"3 m storey)"],
                    ["Preshielding", f"Bucky: {pre['Concrete']:g} mm concrete, {pre['Lead']:g} mm lead",
                     "Table bucky (NCRP 147)"],
                    ["P", f"{fl['P']:g} mGy/week", "Uncontrolled area"]], [38, 62, 70])
    story += formula(f"<i>K</i> = {dist['N']:g} × {dist['U']:g} × {dist['T']:g} × {dist['K1']:g} / "
                     f"{dist['d']:.2f}<super>2</super> = <b>{fmt(K)}</b> mGy/week<br/><i>B</i> = {fl['P']:g} / {fmt(K)} = "
                     f"<b>{fmt(B)}</b>")
    story += [P(f"The Archer equation (primary, Rad Room floor: concrete {params_text(conc)}) gives {total_c:.1f} mm "
                f"of concrete in all. The bucky already provides {pre['Concrete']:g} mm, so the floor needs "
                f"<b>{total_c - pre['Concrete']:.2f} mm</b> of concrete. In lead: {total_l:.2f} − {pre['Lead']:g} = "
                f"<b>{total_l - pre['Lead']:.2f} mm</b>.")]
    story += [P(f"With the planned 100 mm of concrete the beam meets 100 + {pre['Concrete']:g} = "
                f"{100 + pre['Concrete']:g} mm: transmission {fmt(T100)}, dose beyond {fmt(K)} × {fmt(T100)} = "
                f"<b>{fmt(K * T100)} mGy/week</b>, {MET}.")]

    # ---------- two radiation types and layers ----------
    b4 = x["Wall 4"]
    d1, d2 = b4["distributions"]
    K1 = d1["N"] * d1["U"] * d1["T"] * d1["K1"] / d1["d"] ** 2
    K2 = d2["N"] * d2["U"] * d2["T"] * d2["K1"] / d2["d"] ** 2
    K = K1 + K2
    close(K, b4["K_total"])
    P4 = b4["P"]
    c1, c2 = b4["components"]  # each with its own transmission data and preshielding
    p1, p2 = c1["params"], c2["params"]
    pre = c1["pre"]["Lead"]
    s1 = archer_transmission(p1["Lead"], pre)  # the bucky, for the primary beam only
    after_pre = K1 * s1 + K2
    total = math.log(after_pre / P4)
    goal = after_pre * math.exp(-0.5 * total)
    xc = solve(lambda v: K1 * through(p1, [("Concrete", v)], s1) + K2 * through(p2, [("Concrete", v)]), goal)
    xl = solve(lambda v: K1 * through(p1, [("Concrete", xc), ("Lead", v)], s1)
               + K2 * through(p2, [("Concrete", xc), ("Lead", v)]), P4)
    close(xc, dict(b4["thickness"])["Concrete"])
    close(xl, dict(b4["thickness"])["Lead"])
    planned = [("Concrete", 100), ("Lead", 1)]
    t1, t2 = through(p1, planned, s1), through(p2, planned)
    close(K1 * t1 + K2 * t2, b4["check"]["dose"])
    story += H2("Two radiation types and layers: X-ray room, Wall 4 (chest bucky wall)")
    story += [P(f"The wall behind the chest bucky receives the primary beam of the chest bucky distribution and the "
                f"secondary radiation of the whole room. Beyond it are offices (<i>T</i> = {b4['T']:g}, <i>P</i> = "
                f"{P4:g} mGy/week); the source is {d1['d'] - b4['beyond']:.2f} m away, so <i>d</i> = "
                f"{d1['d'] - b4['beyond']:.2f} + {b4['beyond']:g} = {d1['d']:.2f} m.")]
    story += table([["Radiation type", "N", "U", "K<super>1</super> (mGy/patient)", "K (mGy/week)"],
                    [f"#1 Primary, {d1['distribution']}, bucky", f"{d1['N']:g}", f"{d1['U']:g}", f"{d1['K1']:g}",
                     fmt(K1)],
                    [f"#2 Secondary, {d2['distribution']}", f"{d2['N']:g}", f"{d2['U']:g}", f"{d2['K1']:g}",
                     fmt(K2)],
                    ["<b>Total</b>", "", "", "", f"<b>{fmt(K)}</b>"]], [72, 16, 14, 34, 34])
    story += [P(f"Each goes through the wall with its own data: #1 with the primary transmission of the chest bucky "
                f"distribution, behind the wall bucky ({pre:g} mm lead), #2 with the secondary transmission of the "
                f"whole room, which the bucky does not stop. The wall is one barrier of concrete on the room side and "
                f"lead outside, half of the shielding each:")]
    story += [bullets([f"The bucky lets through {fmt(s1)} of #1, so {fmt(K1)} × {fmt(s1)} + {fmt(K2)} = "
                       f"{fmt(after_pre)} mGy/week reach the wall. Down to <i>P</i> = {P4:g} the attenuation is "
                       f"ln({fmt(after_pre)} / {P4:g}) = {total:.3f}, so each layer takes {total / 2:.3f}.",
                       f"After the concrete {fmt(after_pre)} × e<super>−{total / 2:.3f}</super> = {fmt(goal)} mGy/week "
                       f"may remain: the concrete <i>x</i> for which {fmt(K1)} · <i>B</i><sub>1</sub>(0.85 mm lead + "
                       f"<i>x</i>) + {fmt(K2)} · <i>B</i><sub>2</sub>(<i>x</i>) = {fmt(goal)}, i.e. <b>{xc:.2f} mm</b>.",
                       f"The lead then brings the sum down to {P4:g} mGy/week: <b>{xl:.2f} mm</b>."])]
    story += [P(f"Each thickness is found by trying thicknesses until the sum is right (it cannot be solved in closed "
                f"form). Planned: 100 mm concrete + 1 mm lead. Through all the layers #1 keeps {fmt(t1)} and #2 "
                f"{fmt(t2)}: the dose beyond is {fmt(K1)} × {fmt(t1)} + {fmt(K2)} × {fmt(t2)} = "
                f"{fmt(K1 * t1 + K2 * t2)} mGy/week, {MET}.")]

    # ---------- CT ----------
    flc = ct["Floor"]
    s_body, s_head = flc["scans"]["body"], flc["scans"]["head"]
    body = 1.2 * 3e-4 * 550
    head = 9e-5 * 1200
    weekly = 100 * s_body * body + 50 * s_head * head
    K = flc["T"] * weekly / flc["d"] ** 2
    close(K, flc["K_total"])
    B = flc["P"] / K
    lead, conc = flc["params"]["Lead"], flc["params"]["Concrete"]
    close(archer_thickness(lead, B), dict(flc["thickness"])["Lead"])
    close(archer_thickness(conc, B), dict(flc["thickness"])["Concrete"])
    story += H2("CT room, floor")
    story += [P(f"The example CT room has 100 body and 50 head procedures per week, DLP 550 and 1200 mGy·cm per "
                f"scan, 120 kVp, and the NCRP 147 scans per procedure: 100 % + 40 % = {s_body:g}. Below the floor "
                f"are offices (<i>T</i> = 1, <i>P</i> = 0.02 mGy/week); the isocenter is "
                f"{flc['d'] - flc['beyond']:.1f} m above the floor and the person below "
                f"{flc['beyond']:g} m under it, so <i>d</i> = {flc['d']:.2f} m.")]
    story += formula(f"<i>K</i><super>1</super><sub>body</sub> = 1.2 × 3×10<super>−4</super> × 550 = "
                     f"{body:.4f} mGy<br/><i>K</i><super>1</super><sub>head</sub> = 9×10<super>−5</super> × "
                     f"1200 = {head:.4f} mGy")
    story += formula(f"<i>K</i> = 1 × (100 × {s_body:g} × {body:.4f} + 50 × {s_head:g} × {head:.4f}) / "
                     f"{flc['d']:.2f}<super>2</super> = <b>{fmt(K)}</b> mGy/week<br/><i>B</i> = 0.02 / {fmt(K)} = "
                     f"<b>{fmt(B)}</b>")
    story += [P(f"With the NCRP 147 CT data at 120 kVp, lead ({params_text(lead)}) and concrete ({params_text(conc)}): "
                f"<b>{archer_thickness(lead, B):.2f} mm lead</b> or <b>{archer_thickness(conc, B):.0f} mm concrete"
                f"</b>.")]

    # ---------- mammography ----------
    m2 = mammo["Wall 2"]
    dist = m2["distributions"][0]
    K = dist["N"] * dist["U"] * dist["T"] * dist["K1"] / dist["d"] ** 2
    close(K, m2["K_total"])
    B = m2["P"] / K
    gyp, lead = m2["params"]["Gypsum Wallboard"], m2["params"]["Lead"]
    close(archer_thickness(gyp, B), dict(m2["thickness"])["Gypsum Wallboard"])
    story += H2("Mammography room, Wall 2 (offices)")
    story += [P(f"Total workload 536 mA·min/week with <i>W</i><sub>norm</sub> = 6.7 mA·min/patient gives <i>N</i> = "
                f"{dist['N']:g} patients/week. The wall is secondary (leakage and side-scatter, "
                f"<i>K</i><super>1</super><sub>sec</sub> = {dist['K1']:g} mGy/patient), offices beyond (<i>T</i> = 1), "
                f"source {dist['d'] - m2['beyond']:.1f} m away, plus {m2['beyond']:g} m beyond the wall "
                f"(<i>d</i> = {dist['d']:.1f} m):")]
    story += formula(f"<i>K</i> = {dist['N']:g} × {dist['K1']:g} / {dist['d']:.1f}<super>2</super> = "
                     f"<b>{fmt(K)}</b> mGy/week<br/><i>B</i> = 0.02 / {fmt(K)} = <b>{fmt(B)}</b>")
    story += [P(f"Mammography transmission data: <b>{archer_thickness(gyp, B):.2f} mm gypsum wallboard</b> or "
                f"<b>{archer_thickness(lead, B):.3f} mm lead</b>. One standard gypsum board is more than enough.")]

    # ---------- DBT (Yang et al. 2017) ----------
    dbt = VALUES["dbt"]["Wall 1"]
    dist = dbt["distributions"][0]
    views = 200 * (6.07e-3 + 7.85e-3) + 100 * (4.83e-2 + 1.43e-2 + 6.49e-3 + 7.89e-3)
    K = views / dist["d"] ** 2
    close(K, dbt["K_total"])
    B = dbt["P"] / K
    gyp = dbt["params"]["Gypsum Wallboard"]
    x_gyp = archer_thickness(gyp, B)
    close(x_gyp, dict(dbt["thickness"])["Gypsum Wallboard"])
    story += H2("Digital breast tomosynthesis (the example of Yang et al. 2017)")
    story += [P(f"A DBT room with 100 patients per week, all 2D + 3D screening of both breasts: 200 CC views and 100 "
                f"oblique views toward and 100 away from the wall, in each mode. Beyond the wall is an office "
                f"(<i>T</i> = 1, <i>P</i> = 0.02 mGy/week) {dist['d']:g} m from the gantry ({dist['d'] - dbt['beyond']:g} "
                f"m to the wall, plus {dbt['beyond']:g} m). In the program: 100 patients/week, <b>2D + 3D</b>.")]
    story += formula(f"<i>K</i> = [200 × (6.07 + 7.85) × 10<super>−3</super> + 100 × (4.83 × 10<super>−2</super> + "
                     f"1.43 × 10<super>−2</super> + 6.49 × 10<super>−3</super> + 7.89 × 10<super>−3</super>)] / "
                     f"{dist['d']:g}<super>2</super> = <b>{K:.2f}</b> mGy/week<br/><i>B</i> = 0.02 / {K:.2f} = "
                     f"<b>{fmt(B)}</b>")
    story += [P(f"With their gypsum data ({params_text(gyp)}): <b>{x_gyp:.1f} mm gypsum wallboard</b>, as the article "
                f"finds (\"a minimum of 23 mm gypsum is needed\").")]

    # ---------- modern digital radiography (Kirby et al. 2023) ----------
    kirby = VALUES["kirby"]
    story += H2("Digital radiography: NCRP 147 and Kirby et al. 2023")
    story += [P("A DR room with 120 patients per week (the NCRP 147 average). The floor: the source 1 m above it and "
                "an office below (<i>T</i> = 1, <i>P</i> = 0.02 mGy/week), <i>d</i> = 1 + 1.3 = 2.3 m. The chest "
                "bucky wall (Wall 1): 1.8 m from the source, an office beyond, <i>d</i> = 1.8 + 0.3 = 2.1 m. No "
                "preshielding. Each barrier is calculated with the NCRP 147 distribution and with that of Kirby et "
                "al.:")]
    rows = [["Barrier", "Workload distribution", "U", "K<super>1</super><sub>P</sub>", "K (mGy/week)", "Lead (mm)",
             "Concrete (mm)"]]
    for source in ("NCRP 147", "Kirby 2023"):
        for barrier, rec in kirby[source].items():
            K = 120 * rec["U"] * 1 * rec["K1"] / rec["d"] ** 2
            close(K, rec["K_total"])
            thick = dict(rec["thickness"])
            for material in ("Lead", "Concrete"):
                close(archer_thickness(rec["params"][material], 0.02 / K), thick[material])
            rows.append([barrier, rec["distribution"], f"{rec['U']:g}", f"{rec['K1']:g}", fmt(K),
                         f"{thick['Lead']:.2f}", f"{thick['Concrete']:.0f}"])
    story += table(rows, [20, 58, 10, 14, 22, 20, 26])
    floor = kirby["Kirby 2023"]["Floor"]
    lead_of = lambda source, barrier: dict(kirby[source][barrier]["thickness"])["Lead"]
    assert 0.6 < lead_of("Kirby 2023", "Floor") / lead_of("NCRP 147", "Floor") < 0.75  # "about a third less"
    assert lead_of("Kirby 2023", "Wall 1") > lead_of("NCRP 147", "Wall 1")  # "but more"
    K = 120 * floor["K1"] / floor["d"] ** 2
    story += formula(f"Floor, Kirby: <i>K</i> = 120 × 1 × 1 × {floor['K1']:g} / {floor['d']:.1f}<super>2</super> = "
                     f"<b>{fmt(K)}</b> mGy/week, <i>B</i> = 0.02 / {fmt(K)} = <b>{fmt(0.02 / K)}</b>")
    story += [P(f"and with the lead transmission of the floor spectrum ({params_text(floor['params']['Lead'])}): "
                f"<b>{dict(floor['thickness'])['Lead']:.2f} mm lead</b>. The modern DR workload needs about a third "
                f"less lead under the table, but more behind the chest bucky.")]

    # ---------- interventional room (Biondi et al. 2024) ----------
    bio = VALUES["biondi"]["Wall 1"]
    dist = bio["distributions"][0]
    k1 = 7155.262 / 60 / 64 * 0.95
    close(k1, dist["K1"])
    K = dist["N"] * dist["K1"] / dist["d"] ** 2
    close(K, bio["K_total"])
    B = bio["P"] / K
    lead = bio["params"]["Lead"]
    x_lead = archer_thickness(lead, B)
    close(x_lead, dict(bio["thickness"])["Lead"])
    peripheral = next(r for r in load_workbook(EXCEL, data_only=True)["sec abc"].iter_rows(min_row=3, values_only=True)
                      if r[0] == "Peripheral Angiography")[1:4]
    story += H2("Interventional room (the example of Biondi et al. 2024)")
    w_week = 7155.262 / 60 * 779 / 52
    story += [P(f"Biondi et al. work out an angiography room with 779 procedures a year and an uncontrolled area "
                f"(1 mSv a year, <i>T</i> = 1) 2 m from the patient, with their Equation 4: 345 mGy a year without "
                f"shielding and 1.5 mm of lead (their table 4). 779 / 52 is not a whole number of patients, so the "
                f"week is given as workload: <b>Write total Workload</b> = 119.25 mA·min × 779 / 52 = "
                f"<b>{w_week:.1f}</b> mA·min, which the program turns into {dist['N']:.2f} patients of 119.25 mA·min. "
                f"Then <b>Angiography – Biondi 2024</b>, <b>Leakage and Forward/Backscatter</b>, distance "
                f"{dist['d'] - bio['beyond']:g} m + {bio['beyond']:g} m, and <i>P</i> = 1/52 = {bio['P']:g} "
                f"mGy/week.")]
    story += formula(f"<i>K</i><super>1</super><sub>sec</sub> = (7155 mAs / 60) / 64 × 0.95 = {dist['K1']:.3f} "
                     f"mGy/patient<br/><i>K</i> = {dist['N']:.2f} × {dist['K1']:.3f} / {dist['d']:g}<super>2</super> = "
                     f"<b>{K:.2f}</b> mGy/week ({K * 52:.0f} mGy a year), <i>B</i> = {bio['P']:g} / {K:.2f} = "
                     f"<b>{fmt(B)}</b>")
    story += [P(f"With their lead data ({params_text(lead)}): <b>{x_lead:.2f} mm lead</b>, as the article; or "
                f"{dict(bio['thickness'])['Concrete']:.0f} mm concrete. The NCRP 147 transmission of peripheral "
                f"angiography would give {archer_thickness(peripheral, B):.2f} mm of lead for the same "
                f"<i>B</i>: their transmission data are more penetrating.")]
    tube = VALUES["biondi_tube"]["Wall 1"]
    t_dist = tube["distributions"][0]
    k1_tube = (0.096 * 21 + 318.608 * 46 + 5945.228 * 90 + 891.33 * 135) * 1e-6
    close(k1_tube, t_dist["K1"])
    close(t_dist["N"] * k1_tube / t_dist["d"] ** 2, tube["K_total"])
    story += [P(f"With their Equation 3, ticking <b>Tube output</b> and typing the output of their Fig. 1, 21, 46, 90 "
                f"and 135 µGy/mAs at 50, 70, 100 and 125 kVp:")]
    story += formula(f"<i>K</i><super>1</super><sub>sec</sub> = (0.096 × 21 + 318.6 × 46 + 5945.2 × 90 + 891.3 × 135) "
                     f"µGy × 1/1000 = {t_dist['K1']:.3f} mGy/patient<br/><i>K</i> = {tube['K_total']:.3f} mGy/week "
                     f"({tube['K_total'] * 52:.0f} mGy a year): <b>{dict(tube['thickness'])['Lead']:.2f} mm lead</b>")
    story += [P("as their table 4 (130 mGy a year, 1.1 mm).")]

    story += ncrp_examples()
    story += literature_examples()
    story += existing_and_shared_examples()
    story += further_and_field_examples()
    story += H2("A whole department")
    story += [P("The example department puts the three rooms on one floor plan, with a control room between the "
                "X-ray and CT rooms and a corridor below; the CT and the mammography room share a wall (section "
                f"{sec('A wall shared by two rooms: the CT and the mammography room')}). Its 2D / 3D view shows every "
                "barrier, and the radiation of each room crossing the walls of the others.")]
    story += figure("viewer_department.png", "The example department in the 2D / 3D view.",
                    width=94 * mm, crop=(0, 300, 1130, 985))
    return story


def existing_and_shared_examples():
    """The shielding a barrier already has, the patients a barrier allows and a wall shared by two rooms, worked out
    again by hand and checked against the program."""
    story = []
    # ---------- existing shielding: the floor slab of the CT room ----------
    inside, outside = VALUES["existing"]["inside"], VALUES["existing"]["outside"]
    K, goal = inside["K_total"], inside["P"]
    lead, conc = inside["params"]["Lead"], inside["params"]["Concrete"]
    alone = dict(VALUES["ct"]["Floor"]["thickness"])
    total_c, total_l = archer_thickness(conc, goal / K), archer_thickness(lead, goal / K)
    close(total_c, alone["Concrete"])
    close(total_l, alone["Lead"])
    slab = archer_transmission(conc, 100)
    x_in = solve(lambda v: K * through(inside["params"], [("Lead", v), ("Concrete", 100)]), goal)
    x_out = solve(lambda v: K * through(outside["params"], [("Concrete", 100), ("Lead", v)]), goal)
    close(x_in, dict(inside["thickness"])["Lead"])
    close(x_out, dict(outside["thickness"])["Lead"])
    close(total_c - 100, dict(inside["thickness"])["Concrete"])
    equivalent = archer_thickness(lead, slab)  # the slab, in lead (as the lead on its room side sees it)
    story += H2("Existing shielding: lead on the floor slab of the CT room")
    story += [P(f"The floor of the example CT room (section {sec('CT room, floor')}) needs "
                f"<b>{total_l:.2f} mm of lead</b> or <b>{total_c:.0f} mm of concrete</b>: <i>K</i> = {fmt(K)} "
                f"mGy/week, <i>B</i> = {goal:g} / {fmt(K)} = {fmt(goal / K)}. Suppose it is a concrete slab of 100 mm, "
                f"which the program is told under <b>The barrier already has shielding</b> "
                f"({fig('existing_floor.png')}). Alone the slab lets through {fmt(slab)} (CT concrete data, "
                f"{params_text(conc)}): {fmt(K)} × {fmt(slab)} = <b>{fmt(K * slab)} mGy/week</b>, more than "
                f"{goal:g}. What must be added?")]
    story += [bullets([f"<b>Concrete</b>: the same material, so {total_c:.2f} − 100 = <b>{total_c - 100:.2f} mm"
                       "</b>, wherever it goes.",
                       f"<b>Lead on the room side of the slab</b> (on the floor, under the floor covering): the "
                       f"beam meets the lead first; the slab after it starts at the concrete equivalent of that "
                       f"lead. The lead <i>x</i> for which {fmt(K)} · <i>B</i>(<i>x</i> mm lead, then 100 mm concrete) "
                       f"= {goal:g} is <b>{x_in:.2f} mm</b>.",
                       f"<b>Lead outside the slab</b> (on the ceiling of the room below): the slab comes first, "
                       f"{equivalent:.2f} mm of lead equivalent for this beam; the lead goes on from there, where the "
                       f"curve is flatter (the beam is harder). It needs <b>{x_out:.2f} mm</b>."])]
    story += [P(f"Both are much less than the {total_l:.2f} mm without the slab. The order counts: here the lead "
                f"beyond the slab must be {x_out / x_in:.1f} times as thick as the lead on it. While it is not "
                "decided where the lead will go, calculate both and take the larger.")]

    # ---------- the patients a barrier allows: Wall 3 of the X-ray room ----------
    b3 = VALUES["xray"]["Wall 3"]
    dist = b3["distributions"][0]
    K3, P3 = b3["K_total"], b3["P"]
    dose = b3["check"]["dose"]
    close(dose, K3 * archer_transmission(b3["params"]["Gypsum Wallboard"], 15.9))
    factor = P3 / dose
    close(factor, b3["allowed"]["rows"][0]["factor"])
    board3 = K3 * archer_transmission(b3["params"]["Gypsum Wallboard"], 47.7)
    story += H2("How many patients a barrier allows: X-ray room, Wall 3")
    story += [P(f"Wall 3 of the example X-ray room (section {sec('Secondary barrier: X-ray room, Wall 3 (corridor)')}) "
                f"plans one gypsum board of 15.9 mm, which lets {fmt(dose)} mGy/week through: more than "
                f"<i>P</i> = {P3:g}. Its check under Calculate ({fig('xray_area.png')}) answers how many patients it "
                "allows:")]
    story += formula(f"<i>f</i> = {P3:g} / {fmt(dose)} = <b>{factor:.3f}</b>,&nbsp;&nbsp;&nbsp;&nbsp;"
                     f"<i>N</i><sub>max</sub> = {factor:.3f} × {dist['N']:g} = <b>{factor * dist['N']:.0f}</b> "
                     "patients/week")
    story += [P(f"so the board would do for {factor * dist['N']:.0f} of the {dist['N']:g} patients a week. Three "
                f"boards (47.7 mm) let {fmt(board3)} mGy/week through and allow <b>{P3 / board3 * dist['N']:.0f}"
                "</b>.")]

    # ---------- a wall shared by two rooms ----------
    shared = VALUES["shared"]
    ct, mammo = shared["CT Scanner"], shared["Mammography"]
    x_ct = {m: archer_thickness(ct["params"][m], ct["P"] / ct["K"]) for m in ("Lead", "Concrete")}
    x_mammo = {m: archer_thickness(mammo["params"][m], mammo["P"] / mammo["K"]) for m in ("Lead", "Concrete")}
    for m, x in ct["thickness"]:
        close(x, max(x_ct[m], x_mammo[m]))
    for m, x in mammo["thickness"]:
        close(x, max(x_ct[m], x_mammo[m]))
    toward_mammo = max(mammo["K"] * archer_transmission(mammo["params"][m], x) for m, x in mammo["thickness"])
    close(toward_mammo, mammo["check"]["dose"])
    story += H2("A wall shared by two rooms: the CT and the mammography room")
    story += [P(f"In the example department the CT room and the mammography room share a wall: Wall 2 of the CT "
                f"room is Wall 4 of the mammography room ({fig('shared_dialog.png')}). Each tab gives its own "
                "side, with the same materials, lead or concrete:")]
    story += table([["Side", "Radiation toward the other room", "<i>K</i> (mGy/week)", "<i>B</i>", "Lead (mm)",
                     "Concrete (mm)"],
                    ["CT room, Wall 2", "CT secondary, 120 kVp (NCRP 147 CT data)", fmt(ct["K"]),
                     fmt(ct["P"] / ct["K"]), f"{x_ct['Lead']:.2f}", f"{x_ct['Concrete']:.1f}"],
                    ["Mammography, Wall 4", "Mammography Room, leakage + side-scatter", fmt(mammo["K"]),
                     fmt(mammo["P"] / mammo["K"]), f"{x_mammo['Lead']:.3f}", f"{x_mammo['Concrete']:.1f}"]],
                   [34, 52, 22, 20, 18, 22])
    story += [P(f"Both tabs show the larger: <b>{max(x_ct['Lead'], x_mammo['Lead']):.2f} mm of lead</b> or "
                f"<b>{max(x_ct['Concrete'], x_mammo['Concrete']):.1f} mm of concrete</b>, and say that the CT room "
                f"governs ({fig('shared_results.png')}). Through that wall the mammography unit sends only "
                f"{fmt(toward_mammo)} mGy/week into the CT room. Without the link the tab of the mammography room "
                f"would give {x_mammo['Lead']:.3f} mm of lead for this wall: enough for the mammography unit, far too "
                "little for the CT scanner on the other side.")]
    return story


def further_and_field_examples():
    """A further area beyond a barrier, and the scatter of a larger field, worked out again by hand."""
    story = []
    near, far = VALUES["further"]["near"], VALUES["further"]["far"]
    gyp, lead = near["params"]["Gypsum Wallboard"], near["params"]["Lead"]
    K2 = near["K"] * far["T"] / near["T"] * (near["d"] / (near["d"] + far["delta"])) ** 2
    close(K2, far["K"])
    x_near = {m: archer_thickness(near["params"][m], near["P"] / near["K"]) for m in ("Lead", "Gypsum Wallboard")}
    x_far = {m: archer_thickness(near["params"][m], far["P"] / K2) for m in ("Lead", "Gypsum Wallboard")}
    for m, x in far["thickness"]:
        close(x, max(x_near[m], x_far[m]))
    board = archer_transmission(gyp, 15.9)
    close(far["check"]["far"]["dose"], K2 * board)
    factor = far["P"] / (K2 * board)
    close(factor, far["allowed"]["rows"][0]["factor"])
    story += H2("A further area: the office across the corridor")
    story += [P(f"Beyond Wall 3 of the example X-ray room (section {sec('Secondary barrier: X-ray room, Wall 3 (corridor)')}) "
                f"is a corridor (<i>T</i> = {near['T']:g}). Across it, {far['delta']:g} m further, is an office "
                f"(<i>T</i> = {far['T']:g}, <i>P</i> = {far['P']:g} mGy/week): {fig('further_area.png')}. The corridor "
                f"point is <i>d</i> = {near['d']:.2f} m from the source, the office {near['d'] + far['delta']:.2f} m:")]
    story += formula(f"<i>K</i><sub>2</sub> = {fmt(near['K'])} × ({far['T']:g} / {near['T']:g}) × ({near['d']:.2f} / "
                     f"{near['d'] + far['delta']:.2f})<super>2</super> = <b>{fmt(K2)}</b> mGy/week")
    story += table([["Area", "<i>K</i> (mGy/week)", "<i>B</i>", "Lead (mm)", "Gypsum wallboard (mm)"],
                    [f"Corridor, <i>T</i> = {near['T']:g}", fmt(near["K"]), fmt(near["P"] / near["K"]),
                     f"{x_near['Lead']:.2f}", f"{x_near['Gypsum Wallboard']:.1f}"],
                    [f"Office, {far['delta']:g} m further, <i>T</i> = {far['T']:g}", fmt(K2), fmt(far["P"] / K2),
                     f"<b>{x_far['Lead']:.2f}</b>", f"<b>{x_far['Gypsum Wallboard']:.1f}</b>"]],
                   [52, 30, 26, 24, 38])
    story += [P(f"The office governs: {far['T'] / near['T']:g} times the occupancy outweighs the extra distance. "
                f"The one gypsum board "
                f"planned (15.9 mm) lets {fmt(K2 * board)} mGy/week reach the office, so the barrier allows "
                f"{factor:.2f} × 120 = <b>{factor * 120:.0f} patients/week</b>, fewer than the "
                f"{VALUES['xray']['Wall 3']['allowed']['rows'][0]['factor'] * 120:.0f} the corridor alone allows "
                f"(section {sec('How many patients a barrier allows: X-ray room, Wall 3')}).")]

    field = VALUES["field"]
    s = 1505 / 1.0 / (1000 / 1.0)
    K1 = 0.00053 + s * 0.034  # NCRP 147 Table 4.7, Rad Room (all barriers): leakage, side-scatter
    close(K1, field["K1"])
    K = field["N"] * field["T"] * K1 / field["d"] ** 2
    close(K, field["K"])
    x = {m: archer_thickness(field["params"][m], field["P"] / K) for m in ("Lead", "Gypsum Wallboard")}
    for m, value in field["thickness"]:
        close(value, x[m])
    story += H2("Scatter of a larger field: X-ray room, Wall 3")
    story += [P("NCRP 147 makes the secondary air kerma of the radiographic room with a field of 1000 cm² at 1 m. "
                "If the table radiography of the room uses mostly 35 × 43 cm receptors at 100 cm, the field is "
                f"1505 cm² at 1 m, {s:.3f} times larger ({fig('field_size.png')}). Only the side-scatter grows:")]
    story += formula(f"<i>K</i><super>1</super><sub>sec</sub> = 5.3 × 10<super>−4</super> + {s:.3f} × 0.034 = "
                     f"<b>{K1:.4f}</b> mGy/patient (instead of 0.034)")
    story += [P(f"For Wall 3 (120 patients/week, <i>T</i> = {field['T']:g}, <i>d</i> = {field['d']:.2f} m) "
                f"<i>K</i> = {fmt(K)} mGy/week and <i>B</i> = {fmt(field['P'] / K)}: <b>{x['Lead']:.2f} mm lead</b> or "
                f"<b>{x['Gypsum Wallboard']:.1f} mm gypsum wallboard</b>, against "
                f"{dict(VALUES['xray']['Wall 3']['thickness'])['Lead']:.2f} and "
                f"{dict(VALUES['xray']['Wall 3']['thickness'])['Gypsum Wallboard']:.1f} mm with the field of NCRP 147.")]
    return story


def ncrp_examples():
    rows = json.load(open(os.path.join(IMAGES, "ncrp147_examples.json"), encoding="utf-8"))
    story = H2("The examples of NCRP 147")
    story += [P("Section 5 of NCRP 147 works through the shielding of a cardiac angiography suite, a dedicated chest "
                "unit, a radiographic room, an R&amp;F room, a mammography room, two CT rooms and a bone densitometry "
                "unit. Each is a file in <b>Examples\\NCRP 147</b> (section 10.3), made and checked by "
                "<font name='Mono'>tools/ncrp147_examples.py</font> of the source code. A room holds all the "
                "calculations of its example; where the report "
                "calculates one wall or floor twice (e.g. behind the chest bucky and outside the beam), the second "
                "calculation is another barrier. NCRP 147 gives every distance from the source to the person beyond "
                "the barrier, so the files tick <b>Enter the whole distance</b> and type it as the report gives it "
                "(section 2.4).")]
    table_rows = [["§", "Example", "Barrier", "NCRP 147", "Program", "Difference"]]
    for row in rows:
        unit = row["material"].lower()
        ncrp = "no shielding" if row["ncrp"] == 0 else \
            f"{row['ncrp']:g} mm {unit}{'*' if row['bound'] else ''}"
        program = "no shielding" if row["program"] == 0 else f"{row['program']:.2f} mm"
        difference = "–" if row["ncrp"] == 0 else f"{row['program'] - row['ncrp']:+.2f} mm".replace("-", "−")
        example = row["example"].replace(" (Figures 5.1 and 5.2)", "").replace("&", "&amp;")
        table_rows.append([row["section"], example, row["barrier"], ncrp, program, difference])
    story += table(table_rows, [12, 46, 29, 38, 22, 23])
    story += [P("* With all the sources of the room; for the two sources of the example the report shows that "
                "0.8 mm is enough (below). Wall 2 is the simple calculation of 5.3.3.2, Wall 2, scatter at 30° its "
                f"more realistic one, with the chest patient's scatter at 30° (section {sec('Scatter at an angle')}). "
                "The same comparison, with the difference in %, the dose with the "
                "thicknesses the report tries and, in the sheet <i>Distances</i>, the distance of every radiation "
                "type (NCRP 147, entered, added beyond the barrier, d), is the Excel file <b>NCRP 147 examples - "
                "comparison.xlsx</b> in <b>Examples\\NCRP 147</b>.", "small"), Spacer(1, 4)]
    rf = next(r for r in rows if r["section"] == "5.4" and r["barrier"] == "Floor")
    cross = next(r for r in rows if r["section"] == "5.3" and r["barrier"] == "Wall 4")
    story += [P("The results agree. Where they differ a little, NCRP 147 read the thickness from a figure (e.g. "
                "0.53 against 0.51 mm lead for the darkroom; 62 mm concrete for the R&amp;F floor away from the "
                "table, where the report's own Figure 4.8c gives 65 mm), or rounded before subtracting the "
                "preshielding (1.4 against 1.31 mm for the chest unit)."),
              P("Two barriers receive a primary beam behind the image receptor and secondary radiation that does not "
                "pass through it. NCRP 147 follows each through its own thickness, and so does the program (section "
                f"2.2). For the R&amp;F floor under the table it finds {rf['program']:.1f} mm concrete, against "
                f"the 69 mm of NCRP 147; with the 72 mm that the report tries it lets {rf['planned_dose']:.3f} "
                "mGy/week through, as the report's 0.017. For the cross-table wall the report tries 0.8 mm lead, "
                "which lets 0.014 mGy/week through, below 0.02, so less is enough: the program finds "
                f"{cross['program']:.2f} mm, and {cross['planned_dose']:.3f} mGy/week with 0.8 mm (the report reads its "
                "transmissions from figures). The 0.78 mm that the report then quotes comes from a calculation with "
                "all the sources of the room, which the example does not give.")]
    return story


def literature_examples():
    data = json.load(open(os.path.join(IMAGES, "literature_examples.json"), encoding="utf-8"))
    story = H2("The examples of the literature")
    story += [P("The articles whose data the program offers work out their own examples. Each is a file in "
                "<b>Examples\\Literature</b>, made and checked by <font name='Mono'>tools/literature_examples.py"
                "</font> of the source code: Yang et al. 2017 (the DBT room above), Yang et al. 2016 (the floor of a "
                "DBT room, their Eq. 8 and 9, with the transmission of Li et al. 2012), Judge et al. 2013 (the "
                "barriers of their table 1 for three units), Biondi et al. 2024 (five interventional rooms, their "
                "table 4 with Eq. 4 and Eq. 3) and Li et al. 2024 (the lead that lets 0.001 through at each kV, with both "
                "filtrations). Kirby et al. 2023, Chen et al. 2013 and Li et al. 2013 give no worked example; for "
                "them see the end of this section.")]
    rows = [["Article", "Example", "Quantity", "In the article", "Program", "Same"]]
    for row in data["examples"]:
        unit = f" {row['unit']}" if row["unit"] else ""
        shown = (lambda v: fmt(v)) if row["quantity"] == "B" else (lambda v: f"{v:.2f}")
        what = f"{row['room']} · {row['barrier']}"
        quantity = {"K per year": "K (a year)", "Gypsum Wallboard": "Gypsum"}.get(row["quantity"], row["quantity"])
        same = ("no" if not row["ok"] else "≈" if row.get("approximate") else "yes") if row["compared"] else "–*"
        if row["quantity"] == "B":
            paper = fmt(row["paper_value"])
        else:  # as the article prints it
            paper = f"{row['paper_value']:.2f}" if row["paper"] == "Li 2024" else f"{row['paper_value']:g}"
        rows.append([row["paper"].replace(" ", " et al. "), what, quantity, paper + unit,
                     shown(row["program"]) + unit, same])
    story += table(rows, [31, 49, 22, 26, 26, 16])
    story += [P("≈ Yang et al. 2016 give \"~35 mm\" of concrete; the Archer equation with the 40 kVp W/Al data of Li "
                "et al. 2012 gives 32 mm. Biondi et al. 2024: each room has a week of workload, W<sub>site</sub> × "
                "procedures / 52 mA·min (patients are counted whole), a wall with their Eq. 4 and one with their Eq. "
                "3 (the tube output of their Fig. 1, 21, 46, 90, 135 µGy/mAs at 50, 70, 100, 125 kVp). Their table 4 "
                "comes out, with both equations, with 393, 523 and 172 procedures a year for electrophysiology, "
                "neuroangiography and vascular surgery, where their table 1 lists 523, 172 and 393; and its Eq. 3 "
                "values of haemodynamics and vascular surgery are interchanged (33 mGy and 0.60 mm belong to "
                "haemodynamics, 38 mGy and 0.7 mm to vascular surgery). Judge et al. 2013: 200 patients a week (40 a "
                "day, 5 days) and P = 0.3/50 mGy/week; they do not give the kVp of "
                "their transmission data: 30 kVp (GE, Hologic) and 35 kVp (Philips) reproduce all their values. The "
                "same comparison, with the difference in %, is the Excel file <b>Literature examples - "
                "comparison.xlsx</b> in <b>Examples\\Literature</b>.", "small"), Spacer(1, 4)]
    checks = [row for row in data["data"] if row["paper"] in ("Chen 2013", "Li 2013", "Kirby 2023")]
    story += [P("The articles without a worked example are checked through their own data, in the sheet <i>Data "
                "checks</i> of the same file. Chen et al.: their table 1, with the method of NCRP 147, gives their "
                "air kerma (table 4) and their transmission through lead and concrete (table 6). Li et al. 2013: "
                "the single-kVp transmission of Li 2012 (W/Rh, W/Al) and Li 2013 (W/Ag), weighted by the air kerma "
                "of each kVp bin of their table IV(c), gives their table V(a). Kirby et al.: the sum of each "
                "spectrum gives their total workload. Every check agrees:")]
    rows = [["Article", "Check", "In the article", "From the program's data"]]
    for row in checks:
        value = (lambda v: f"{v:.3g}") if abs(row["paper_value"]) < 10 else (lambda v: f"{v:.1f}")
        rows.append([row["paper"].replace(" ", " et al. "), row["what"].replace("&", "&amp;"),
                     value(row["paper_value"]), value(row["program"])])
    story += table(rows, [26, 88, 28, 28])
    return story


def reference():
    story = H1("NCRP 147 data used by the program")
    story += [P("The program reads these values from <b>Data Shielding.xlsx</b>; they are the NCRP Report No. 147 "
                "values (the report itself is in the Help menu). The data of the literature are in the same file, "
                "in sheets named after their source (sections 4.9 to 4.11 and 6.1).")]
    story += note("The file was checked value by value against NCRP 147 (Tables 4.1, 4.3, 4.5, 4.7, A.1, B.1, C.1 "
                  "and Figures A.2, A.3). This edition corrects transcription errors of earlier versions: the "
                  "occupancy factors 1/8 (corridor doors) and 1/40 (outdoors, stairways, attics, ...), which were "
                  "rounded to 0.13 and 0.03; the concrete α of secondary radiation at 70 kVp (0.0509, was 0.059) and "
                  "the lead β of primary radiation at 75 kVp (22.69, was 26.69), used with <b>Give kVp</b>; the "
                  "forward/backscatter alone of the mammography room (0.049 mGy, was 0.042); plate glass at 25 to "
                  "35 kVp, written as formulas that stopped the calculation of a primary beam at these kVp; and some "
                  "values that change no result of a usual design (steel at 25 and 125 kVp, gypsum at 35 kVp, wood "
                  "at 125 to 150 kVp, lead and wood of the primary mammography beam). Results of these cases differ "
                  "slightly from those of earlier versions.", "Note")
    workbook = load_workbook(EXCEL, data_only=True)

    story += H2("Occupancy factors T (Table 4.1)")
    rows = [["Location beyond the barrier", "T"]]
    for location, value in workbook["Occupancy Factor ( T )"].iter_rows(min_row=2, max_col=2, values_only=True):
        if location:
            rows.append([" ".join(str(location).split()), f"{value:g}"])
    story += table(rows, [150, 20])

    story += H2("Workload distributions")
    workload = {r[0]: r for r in workbook["Workload"].iter_rows(min_row=3, values_only=True) if r[0]}
    primary = {r[0]: r[2] for r in workbook["unshielding prim"].iter_rows(min_row=2, values_only=True) if r[0]}
    primary = {name.replace("R&F Room", "R&F room"): k for name, k in primary.items()}
    rows = [["Workload distribution", "W<sub>norm</sub> (mA·min/patient)", "N average / busy",
             "K<super>1</super><sub>P</sub>", "K<super>1</super><sub>sec</sub> leakage + side-scatter",
             "K<super>1</super><sub>sec</sub> leakage + forward/back"]]
    for r in workbook["Uns Air Kerma"].iter_rows(min_row=2, values_only=True):
        if not r[0]:
            continue
        w = workload.get(r[0])
        n = f"{w[2]:g} / {w[3]:g}" if w and w[2] else "–"
        rows.append([r[0].replace("&", "&amp;"), f"{r[1]:g}", n,
                     f"{primary[r[0]]:g}" if r[0] in primary else "–", f"{r[6]:g}", f"{r[8]:g}"])
    story += table(rows, [44, 27, 22, 13, 32, 32])
    story += [P("Air kerma in mGy per patient at 1 m. N: patients per 40-hour week.", "small"), Spacer(1, 6)]

    story += H2("Use factors and preshielding")
    story += table([["Primary barrier", "U", "Workload distribution"],
                    ["Floor", "0.89", "Rad Room (floor or other barriers)"],
                    ["Cross-table wall", "0.09", "Rad Room (floor or other barriers)"],
                    ["Wall No. 3", "0.02", "Rad Room (floor or other barriers)"],
                    ["Chest image receptor", "1", "Rad Room (chest bucky)"]], [55, 20, 95])
    story += table([["Preshielding", "Lead", "Concrete", "Steel"],
                    ["Bucky: image receptor in a table or wall-mounted cassette holder", "0.85 mm", "72 mm", "7 mm"],
                    ["Cross-table lateral: grid and cassette only", "0.3 mm", "30 mm", "2 mm"]], [104, 22, 22, 22])
    story += H2("Other values")
    story += table([["Quantity", "Value"],
                    ["Design goal P", "Controlled 0.1 mGy/week; uncontrolled 0.02 mGy/week"],
                    ["Occupied point beyond the barrier (4.1.2)", "Walls and doors 0.3 m; ceiling 0.5 m above the "
                                                                  "floor of the room above; floor: 1.7 m above the "
                                                                  "floor below (1.3 m under a floor with a 3 m storey)"],
                    ["CT secondary air kerma per mGy·cm of DLP at 1 m, per scan", "Body 1.2 × 3×10<super>−4</super> "
                                                                                  "cm<super>−1</super>; head "
                                                                                  "9×10<super>−5</super> cm<super>−1"
                                                                                  "</super>"],
                    ["CT scans per procedure", "1.4: every procedure once, 40 % again with contrast"],
                    ["CT typical DLP per scan", "Body 550 mGy·cm; head 1200 mGy·cm"],
                    ["Materials", "Lead, concrete (2.35 g/cm³), gypsum wallboard, steel, plate glass, wood; CT: "
                                  "lead and concrete"],
                    ["Digital breast tomosynthesis (not NCRP 147)", "Yang et al. 2017: transmission table 8 (sheet "
                                                                    "'DBT abc'), scatter air kerma per view table 9"],
                    ["Transmission of modern DR (not NCRP 147)", "Li et al. 2024, tables 1 and 2 (sheet 'prim abc DR "
                                                                 "600'): 60–120 kV, two filtrations"],
                    ["Workloads of modern DR (not NCRP 147)", "Kirby et al. 2023, table 3 (sheet 'Kirby 2023'); air "
                                                              "kerma and transmission made with the NCRP 147 method "
                                                              "(sheets 'Kirby 2023 kerma', 'Kirby 2023 prim abc', "
                                                              "'Kirby 2023 sec abc'), section 4.10"],
                    ["Interventional rooms (not NCRP 147)", "Biondi et al. 2024, tables 2 and 3 (sheets 'Biondi 2024', "
                                                            "'Biondi 2024 sec abc'), section 4.11"],
                    ["Radiographic rooms in Taiwan (not NCRP 147)", "Chen et al. 2013, tables 1, 4, 5, 6 (sheets 'Chen "
                                                                    "2013', 'Chen 2013 kerma', 'Chen 2013 prim abc', "
                                                                    "'Chen 2013 sec abc'), section 4.12"],
                    ["DBT of Li et al. 2013, FFDM (not NCRP 147)", "Li et al. 2013, table V(a) (sheet 'Li 2013 DBT "
                                                                   "abc'); Yang et al. 2016 table V; Judge et al. "
                                                                   "2013 table 1 (sheet 'Judge 2013'), sections 6.1, "
                                                                   "6.2"],
                    ["Mammography beams at a kVp (not NCRP 147)", "Li et al. 2012 tables I, II and Li et al. 2013 "
                                                                  "table VI (sheet 'Mammography kVp abc'), section 6.3"]],
                   [70, 100])
    return story


def troubleshooting():
    story = H1("Messages and tips")
    story += table([["You see", "Meaning", "What to do"],
                    [f"<font color='{OK}'>none needed</font>", "B ≥ 1: the air kerma beyond is already below P.",
                     "Nothing; the barrier needs no extra shielding."],
                    [f"<font color='{BAD}'>Missing: ...</font>", "An input of the barrier is empty.",
                     "Press Calculate: the Missing data window says what to fill in, and the fields turn red."],
                    ["No transmission data for ...", "The chosen data have no transmission values for that "
                                                     "material (e.g. plate glass or wood with the DR 600 data).",
                     "Choose another material, or other data."],
                    [f"<font color='{BAD}'>Missing: kVp for the DR 600 data</font>", "The DR 600 data exist only "
                                                                                    "for 60, 70, ... 120 kV.",
                     "Choose one of these kVp, or the NCRP 147 data."],
                    [f"<font color='{BAD}'>Missing: Secondary radiation only</font>", "A workload distribution of "
                                                                                     "Biondi et al. 2024 was chosen "
                                                                                     "for primary radiation; it has "
                                                                                     "secondary data only.",
                     "Choose Secondary, or another workload distribution."],
                    [f"<font color='{BAD}'>Missing: Select Material</font>", "A material list was left empty.",
                     "Choose the material under Select Materials."],
                    [f"<font color='{BAD}'>Missing: Existing shielding (material and thickness)</font>",
                     "The barrier already has shielding, but a material or its thickness is not given.",
                     "Choose each existing material and type its thickness, or untick the option."],
                    ["No transmission data for ... (existing)", "The data of a radiation type have no "
                                                                "transmission values for an existing "
                                                                "material (e.g. steel in a CT room).",
                     "Give the existing shielding as a material that has data (e.g. its lead or concrete "
                     "equivalent)."],
                    [f"<font color='{BAD}'>Missing: Further area (distance, T and P)</font>", "The further area "
                                                                                           "is ticked, but its "
                                                                                           "distance, T or P is not "
                                                                                           "valid.",
                     "Type how much further it is (0 or more), T (more than 0, at most 1) and P, or untick it."],
                    [f"<font color='{BAD}'>Missing: Field size (F and d_F)</font>", "The field of the scatter is "
                                                                                     "ticked, but F or d<sub>F</sub> "
                                                                                     "(or, for an air kerma written, "
                                                                                     "the field it is for) is not "
                                                                                     "more than 0.",
                     "Type the fields and their distances, or untick Field size."],
                    [f"<font color='{BAD}'>Missing: Occupancy Factor (T)</font>",
                     "No location is chosen, or the T typed is not more than 0 and at most 1 (e.g. 10.5).",
                     "Choose a location, or type T as 0.2 or 1/5."],
                    [f"<font color='{BAD}'>Missing: Patients per week: a whole number</font>",
                     "Patients (and CT procedures) are counted whole.",
                     "Type a whole number, or give an average as Write total Workload (mA·min/week)."],
                    [f"<font color='{BAD}'>Missing: Tube output (µGy/mAs at 1 m)</font>",
                     "Tube output (Biondi et al. Eq. 3) is ticked, but an output is missing.",
                     "Type the output of the tube at 50, 70, 100 and 125 kVp, or untick it."],
                    [f"<font color='{BAD}'>Missing: Scattering angle (20-140°)</font>", "A secondary radiation "
                                                                                         "type at a kVp, at an angle "
                                                                                         "outside Figure C.1.",
                     "Type an angle from 20 to 140°."],
                    [f"<font color='{BAD}'>Missing: Scatter at an angle: 50-150 kVp, not mammography</font>",
                     "Figure C.1 gives the scatter of tungsten-anode beams of 50 to 150 kVp only.",
                     "Choose such a kVp, or Write Unshielded Secondary Air Kerma."],
                    [f"<font color='{BAD}'>The ceiling needs shielding added to its slab ...</font>",
                     "The ceiling has its slab as existing shielding and needs more, but this wall stops below it.",
                     "Choose Up to the ceiling as the shielding height of the wall."],
                    [f"<font color='{BAD}'>Shared with ...: press Calculate there too</font>", "The wall is "
                                                                                     "shared, but the other "
                                                                                     "room has not calculated "
                                                                                     "it (or misses data).",
                     "Calculate the wall in the other room: both tabs then show the larger thickness."],
                    [f"<font color='{BAD}'>up to ... patients/week (×0.45 ...)</font>", "The barrier as "
                                                                                        "it will be built "
                                                                                        "allows less than "
                                                                                        "the present "
                                                                                        "workload.",
                     "Plan more shielding, or a smaller workload."],
                    [f"Total: 90 % <font color='{BAD}'>(must be 100 %)</font>", "The shares of the layers do not add "
                                                                               "up to 100 %.",
                     "Correct the % of the shielding of the layers."],
                    [f"<font color='{BAD}'>{sym('✗')} exceeded</font>", "The planned thickness lets through more "
                                                                         "than P.",
                     "Increase the planned thickness, or add another material."],
                    ["2D / 3D View not up to date", "It shows the last calculation.",
                     "Press Calculate (or Calculate all barriers), then Refresh."],
                    ["Cannot find the NCRP 147 data file", "Data Shielding.xlsx is not next to the program.",
                     "Install the program again (from the source code: keep it in the project folder)."],
                    ["Unexpected error", "Something went wrong inside the program; the details are saved in "
                                         "%LOCALAPPDATA%\\Shielding of X-ray Rooms\\errors.log.",
                     "Send that file with a description of what you did, so the problem can be fixed."]],
                   [42, 64, 64])
    story += H1("References")
    story += [bullets(["NCRP Report No. 147, <i>Structural Shielding Design for Medical X-Ray Imaging Facilities</i>. "
                       "National Council on Radiation Protection and Measurements, Bethesda, 2004.",
                       "Sutton D.G., Martin C.J., Williams J.R., Peet D.J. <i>Radiation Shielding for Diagnostic "
                       "Radiology</i>, 2nd edition. British Institute of Radiology, 2012.",
                       "Archer B.R., Thornby J.I., Bushong S.C. Diagnostic X-ray shielding design based on an "
                       "empirical model of photon attenuation. <i>Health Physics</i> 44:507–517, 1983.",
                       "Yang K., Schultz T.J., Li X., Liu B. Radiation shielding calculation for digital breast tomosynthesis rooms with an updated workload survey. <i>J. Radiol. Prot.</i> 37:230–246, 2017.",
                       "Yang K., Li X., Liu B. Scatter radiation intensities around a clinical digital breast "
                       "tomosynthesis unit and the impact on radiation shielding considerations. <i>Med. Phys.</i> "
                       "43:1096–1110, 2016, doi:10.1118/1.4940352.",
                       "Li X., Zhang D., Liu B. Transmission of broad W/Rh and W/Al (target/filter) x-ray beams "
                       "operated at 25–49 kVp through common shielding materials. <i>Med. Phys.</i> 39:4132–4138, "
                       "2012, doi:10.1118/1.4725755.",
                       "Li X., Zhang D., Liu B. Workload and transmission data for the installation of a digital "
                       "breast tomosynthesis system. <i>Med. Phys.</i> 40:063901, 2013, doi:10.1118/1.4803470.",
                       "Judge M.A., Keavey E., Phelan N. Scatter radiation intensities around full-field digital "
                       "mammography units. <i>Br. J. Radiol.</i> 86:20120130, 2013, doi:10.1259/bjr.20120130.",
                       "Chen T.R., Tyan Y.S., Chu C.H., Wu M.C., Tung C.J. Surveyed data for structural shielding "
                       "calculations of radiographic x-ray installations in Taiwan. <i>Health Phys.</i> 104(5 Suppl "
                       "2):S60–S67, 2013, doi:10.1097/HP.0b013e318286caeb.",
                       "Li X., Marschall T.A., Yang K., Liu B. Radiation shielding transmission data for modern digital radiography. <i>Med. Phys.</i> 51:8768–8775, 2024, doi:10.1002/mp.17449.",
                       "Kirby K.M., Schueler B.A., Littrell L.A., Long Z. Workload and use factor data for a modern "
                       "digital radiography system. <i>J. Appl. Clin. Med. Phys.</i> 24:e13962, 2023, "
                       "doi:10.1002/acm2.13962.",
                       "Biondi M., Bortoli E., Avitabile R., et al. Radiation shielding calculation for "
                       "interventional radiology: an updated workload survey using a dose monitoring software. "
                       "<i>Physica Medica</i> 125:104509, 2024, doi:10.1016/j.ejmp.2024.104509."])]
    return story


def check_glyphs(story):
    """Every character of the text must be in Segoe UI (or come from the symbol font)."""
    face = pdfmetrics.getFont("Body").face
    missing = set()

    def text_of(flowable):
        if isinstance(flowable, Paragraph):
            yield flowable.text
        for attribute in ("_content", "_cellvalues", "_flowables"):
            value = getattr(flowable, attribute, None)
            if isinstance(value, (list, tuple)):
                for item in value:
                    for sub in (item if isinstance(item, (list, tuple)) else [item]):
                        if hasattr(sub, "wrap"):
                            yield from text_of(sub)

    import re
    for flowable in story:
        for text in text_of(flowable):
            plain = re.sub(r'<font name="SegoeSymbol">.*?</font>', "", text)
            plain = re.sub(r"<[^>]+>", "", plain)
            missing |= {c for c in plain if ord(c) > 127 and ord(c) not in face.charToGlyph}
    assert not missing, f"characters missing from the font: {missing}"


def content():
    for name in counters:
        counters[name] = 0
    story = []
    story += cover()
    story += contents()
    for part in (introduction, method, getting_started, xray_room, ct_and_mammography, department, floor_plan,
                 viewer, report_and_projects, worked_examples, reference, troubleshooting):
        story += part()
    return story


def build():
    content()  # numbers the figures and the sections
    UNKNOWN.clear()
    story = content()
    if UNKNOWN:
        raise SystemExit(f"References to sections that do not exist: {sorted(UNKNOWN)}")
    check_glyphs(story)
    doc = Guide(OUTPUT)
    doc.multiBuild(story)
    for name in os.listdir(IMAGES):  # cropped copies
        if name.startswith("_"):
            os.remove(os.path.join(IMAGES, name))
    print("written", OUTPUT)


if __name__ == "__main__":
    sys.exit(build())
