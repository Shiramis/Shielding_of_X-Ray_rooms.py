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
    "toc1": ParagraphStyle("toc1", fontName="Body-Bold", fontSize=10.5, leading=16, textColor=NAVY, spaceBefore=4),
    "toc2": ParagraphStyle("toc2", fontName="Body", fontSize=9.6, leading=13.4, leftIndent=14, textColor=TEXT),
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


def H1(text):
    counters["section"] += 1
    counters["sub"] = 0
    return [CondPageBreak(60 * mm), Heading(f"{counters['section']}&nbsp;&nbsp;{text}", 1,
                                            f"s{counters['section']}")]


def H2(text):
    counters["sub"] += 1
    number = f"{counters['section']}.{counters['sub']}"
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
        picture.crop(crop).save(cropped)
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
                "equipment: its walls, floor, ceiling and door. For every barrier it finds the thickness of each "
                "material you choose (lead, concrete, gypsum wallboard, steel, plate glass or wood) that keeps the "
                "weekly air kerma beyond the barrier below the shielding design goal <i>P</i>. It can also check a "
                "thickness you plan to install, show the rooms in 2D and 3D with the radiation around them, and "
                "write a complete report in Excel."),
              P("You can design:")]
    story += [bullets(["<b>X-Ray rooms</b>: radiography, R&amp;F, chest rooms and angiography, with primary and "
                       "secondary barriers.",
                       "<b>CT rooms</b>: secondary radiation from the DLP of the body and head procedures.",
                       "<b>Mammography rooms</b>: secondary radiation only.",
                       "<b>Departments</b>: several rooms of any type on one floor plan, each with its own results, "
                       "in one report."])]
    story += H2("Files the program uses")
    story += [P("The setup (section 3.1) puts these files in the program's folder:")]
    story += table([["File", "What it is"],
                    ["Shielding of X-ray Rooms.exe", "The program. (From the source code: <font name='Mono'>"
                     "Shielding_of_X-Ray_rooms.py</font> in the folder <font name='Mono'>XRIFSC_code</font>, run "
                     "with Python.)"],
                    ["Data Shielding.xlsx", "The NCRP 147 data: workloads, unshielded air kerma, transmission "
                                            "parameters, occupancy and use factors. <b>Required</b>: keep it next to "
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
    story += [P("If <i>B</i> ≥ 1 the barrier needs no shielding and the result says <b>none needed</b>. Otherwise "
                "the thickness of each material follows from the Archer equation, with the NCRP 147 fitting "
                "parameters α, β, γ of that material for the workload distribution:")]
    story += formula("<i>x</i> = (1 / αγ) · ln[ (<i>B</i><super>−γ</super> + β/α) / (1 + β/α) ]")
    story += [P("A barrier with several workload distributions takes α, β, γ from the one ticked <b>Set for the "
                "calculation</b>. Tick the distribution that gives the most air kerma, or the most penetrating one "
                "for a conservative result.")]
    story += H2("Design goal P")
    story += table([["Area beyond the barrier", "P (air kerma)", "Annual"],
                    ["Controlled: occupied only by radiation workers", "0.1 mGy/week", "5 mSv/year"],
                    ["Uncontrolled: everyone else (public, other staff, patients)", "0.02 mGy/week", "1 mSv/year"]],
                   [100, 35, 35])
    story += [P("Choosing the <b>Shielding Area</b> fills in <i>P</i>. <i>Supervised</i> is not an NCRP 147 class; "
                "the program treats it as uncontrolled. If your national dose constraint is lower, type it in "
                "<b>Shielding Design Goal</b>.")]
    story += H2("Distances")
    story += [P("<i>d</i> goes to the person to protect. For every barrier you enter the distance from the source "
                "(focal spot; CT: the isocenter) to the barrier and, under <b>Shielding Area</b>, the distance from "
                "the barrier to that person, the <b>occupied point beyond the barrier</b>. The program adds the two. "
                "NCRP 147 (section 4.1.2) places the person:")]
    story += table([["Barrier", "Where the person is (NCRP 147 4.1.2)", "Distance beyond the barrier"],
                    ["Walls and door", "0.3 m beyond the wall", "0.3 m"],
                    ["Ceiling", "0.5 m above the floor of the room above", "0.5 m, plus any space above a "
                                                                          "suspended ceiling"],
                    ["Floor", "not more than 1.7 m above the floor below",
                     "floor-to-floor height − 1.7 m: <b>1.3 m</b> for a 3 m storey, 2.6 m for 4.3 m"]],
                   [30, 70, 70])
    story += [P("These are the values filled in; change them where the building differs. The floor plan "
                "(section 8) measures the distances to the barriers and sets the floor and ceiling values from the "
                "floor-to-floor height.")]
    story += note("Earlier versions of the program added 1.7 m below the floor. NCRP 147 puts the person 1.7 m "
                  "<i>above the floor below</i>, which for a 3 m storey is 1.3 m under the floor: closer to the "
                  "source, so the floor needs more shielding. Projects saved with an earlier version are converted "
                  "when you open them and show the corrected results.", "Note")
    story += H2("Preshielding")
    story += [P("Behind the image receptor the primary beam is already attenuated by the grid, the cassette and "
                "their supports. NCRP 147 credits this as an equivalent thickness, which the program subtracts "
                "from the calculated thickness: <b>Bucky</b> (table or wall bucky) 0.85 mm lead, 72 mm concrete or "
                "7 mm steel; <b>Cross-table</b> (grid and cassette only) 0.3 mm lead, 30 mm concrete or 2 mm steel. "
                "Use it only for primary barriers behind the image receptor.")]
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
                       "lead. Each material gives its share (%) of the attenuation ln(1/<i>B</i>), from the room "
                       "side outwards. Each layer starts at the equivalent thickness of everything in front of it "
                       "(the preshielding included), so the order counts: the first layers harden the beam."])]
    story += H2("Checking a planned thickness")
    story += [P("When you tick <b>Check the dose beyond the barrier with a planned thickness</b> and type the "
                "thicknesses you intend to install, the program calculates the weekly air kerma beyond the "
                "barrier,")]
    story += formula("dose beyond = Σ<i>K</i> · <i>B</i>(<i>x</i><sub>planned</sub>)")
    story += [P("and compares it with <i>P</i>. Every material with a planned thickness is taken as installed: "
                "together they cut the radiation, one after the other from the room side out. Leave empty a "
                "material that will not be there. Like <i>P</i>, the dose includes the occupancy factor <i>T</i>.")]
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
                    ["File", "New... › Design Department / X-Ray Room / CT Room / Mammography Room",
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
    story += note("Rest the pointer on any field, label or button: a note explains what to enter, with the NCRP 147 "
                  "typical values. Labels with a question-mark pointer have such a note.")
    return story


def xray_room():
    story = H1("Designing an X-ray room")
    story += [P("Start with <b>X-Ray Room</b> on the start screen, or <b>File › New... › Design X-Ray Room</b>. "
                f"{fig('xray_overview.png')} shows the example X-ray room (File › Examples › X-Ray room) with its "
                "results.")]
    story += figure("xray_overview.png", "An X-ray room: room data at the top, one tab per barrier, results on the "
                                         "right.")
    story += H2("Room data")
    story += [bullets(["<b>Number of Barriers</b>: at least 7. The first three are always <b>Floor</b>, <b>Ceiling"
                       "</b> and <b>Door</b>; the others are the walls <b>Barrier 1, 2, ...</b>",
                       "<b>Workload</b>: either <b>Write total Workload</b> <i>W</i><sub>tot</sub> (mA·min/week) or "
                       "<b>The Number of Patients per week</b> <i>N</i> (NCRP 147 average for a radiographic room: "
                       "120). It applies to every barrier, unless a barrier ticks <b>Different Workload</b>.",
                       "<b>Floor Plan</b> (section 8), <b>2D / 3D View</b> (section 9), <b>Calculate all barriers"
                       "</b> and <b>Export to Excel</b> (section 10)."])]
    story += H2("Radiation on a barrier")
    story += [P("Each barrier tab starts with the radiation that reaches it. " + fig("xray_floor.png") + " shows the floor "
                "of the example: "
                "a primary barrier.")]
    story += figure("xray_floor.png", "A primary barrier (the floor) with bucky preshielding, two materials and a "
                                      "planned thickness.", crop=(0, 0, 1175, 880))
    story += [steps(["<b>Select the number of types of radiation on the barrier</b>: how many workload "
                     "distributions irradiate it; each gets its own block (#1, #2, ...).",
                     "<b>Select Radiation Type</b>: <b>Primary</b> if the useful beam is aimed at the barrier (floor, "
                     "chest bucky wall, cross-table wall), otherwise <b>Secondary</b> (leakage and scatter only).",
                     "<b>Distance from the Source to the Barrier</b> (m), to the barrier itself. The distance "
                     "beyond it to the person is set under Shielding Area (section 2.4).",
                     "<b>Workload Distribution</b>: <b>X-Ray Room (Suggested NCRP 147)</b> and the room in the list "
                     "(e.g. <i>Rad Room (floor or other barriers)</i>), or <b>Give kVp</b> for a single-kVp "
                     "transmission curve. With kVp you must write the unshielded air kerma yourself.",
                     "<b>Set for the calculation</b>: tick it on the distribution whose transmission data (α, β, γ) "
                     "are used. Only one per barrier.",
                     "Primary radiation: <b>Use Factor</b> <i>U</i> (floor 0.89, cross-table wall 0.09, wall No. 3 "
                     "0.02, chest bucky 1), the <b>Primary Unshielded Air Kerma</b> "
                     "<i>K</i><super>1</super><sub>P</sub> (filled in for the NCRP 147 rooms) and, behind an image "
                     "receptor, <b>Preshielding</b>: <b>Bucky</b> or <b>Cross-table</b>."])]
    story += [P(f"For secondary radiation ({fig('xray_secondary.png')}) choose where the unshielded air kerma comes from:")]
    story += figure("xray_secondary.png", "A secondary barrier: the unshielded secondary air kerma suggested by NCRP "
                                          "147.", crop=(0, 0, 1175, 700))
    story += [bullets(["<b>Select Unshielded Secondary Air Kerma — Suggested (NCRP 147)</b>, then <b>Leakage "
                       "Radiation</b> with <b>Leakage and Side-Scatter</b> (walls and doors beside the patient), "
                       "<b>Leakage and Forward/Backscatter</b> (floor and ceiling, in line with the beam) or <b>Only "
                       "Leakage</b>; or <b>Side-Scatter</b> or <b>Forward/Backscatter</b> alone.",
                       "<b>Write Unshielded Secondary Air Kerma</b>: your own <i>K</i><super>1</super><sub>sec</sub> "
                       "in mGy per patient at 1 m.",
                       "<b>Different Workload</b>: this distribution has its own workload instead of the room's."])]
    story += H2("Materials")
    story += [bullets(["<b>Select Materials</b>: how many materials, then choose each one (#1, #2, ...). You get a "
                       "thickness for each.",
                       "<b>The materials are</b>: <b>Each one alone</b> (alternatives) or <b>Layers of one barrier"
                       "</b> (section 2.8)."])]
    story += [P(f"With layers ({fig('xray_layers.png')}), #1 is on the room side and the last material outside. Give each material "
                "its <b>% of the shielding</b>; the shares start equal and must add up to 100 %. <b>Reverse order"
                "</b> swaps inside and outside.")]
    story += figure("xray_layers.png", "Barrier 4 of the example: concrete on the room side and lead outside, half "
                                       "of the shielding each, with the planned thicknesses.",
                    crop=(0, 380, 1175, 895))
    story += H2("Checking a planned thickness")
    story += [P("Tick <b>Check the dose beyond the barrier with a planned thickness</b> and type the thickness of "
                "each material you intend to install (mm). With layers the planned thicknesses go in the "
                "<b>planned</b> column. The results then show the weekly dose beyond the barrier and whether it "
                "meets <i>P</i>. Untick it to see only the required thickness; the values you typed are kept.")]
    story += H2("Area, occupancy and design goal")
    story += figure("xray_area.png", "The end of a barrier tab: area, occupancy factor, design goal and Calculate.",
                    crop=(0, 0, 1175, 420))
    story += [bullets(["<b>Shielding Area</b>: Controlled, Uncontrolled or Supervised. It fills in the design goal "
                       "<i>P</i>.",
                       "<b>Write occupancy factor (T)</b>, <b>or select Location (Suggested NCRP 147)</b>: the "
                       "location beyond the barrier gives <i>T</i> from NCRP 147 Table 4.1 (section 12.2).",
                       "<b>Shielding Design Goal</b> (mGy/week): filled in from the area; you can change it.",
                       "<b>Occupied point beyond the barrier</b> (m): where the person to protect is, beyond the "
                       "barrier: walls and door 0.3 m, ceiling 0.5 m, floor 1.3 m (section 2.4).",
                       "<b>Calculate</b>: calculates this barrier. <b>Calculate all barriers</b> at the top "
                       "calculates every barrier of the room."])]
    story += H2("Results")
    story += [P("The results tab has one line per barrier with the thickness of each material (" + fig("xray_results.png") + "). "
                "<font color='%s'>Green</font> means no shielding is needed. Layers show which material is inside "
                "and outside. With a planned thickness a second line gives the dose beyond and "
                "%s or %s." % (OK, MET, EXCEEDED))]
    story += figure("xray_results.png", "The results of the example X-ray room.", width=88 * mm,
                    crop=(0, 0, 650, 640))
    story += H2("When something is missing")
    story += [P("If a barrier cannot be calculated, a window lists what is missing and how to fill it in "
                "(" + fig("missing_dialog.png") + "). The empty fields turn red, the barrier tab is opened, and the cursor goes to the first "
                "field when you close the window. The results tab shows <font color='%s'>Missing: ...</font> for "
                "that barrier until it is calculated." % BAD)]
    story += figure("missing_dialog.png", "The Missing data window, here for a barrier without distance.",
                    width=125 * mm)
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
                                                     "the % of the procedures that have it (section 2.6). The line "
                                                     "below shows the mean number of scans per procedure.",
                     "100 % + 40 % = 1.4"],
                    ["DLP per body / head scan (mGy·cm)", "Dose-length product of one scan (phase).",
                     "550 / 1200 mGy·cm"],
                    ["Tube voltage (kVp)", "The transmission data exist for 120 and 140 kVp.", "120 kVp"],
                    ["Distance from the CT Unit Isocenter to the Barrier (m)", "To the barrier itself; the distance "
                                                                               "beyond it is set under Shielding "
                                                                               "Area.", "–"],
                    ["Materials", "NCRP 147 has CT transmission data for lead and concrete.", "–"]], [52, 88, 30])
    story += [P("Area, occupancy, design goal, layers and the planned-thickness check work as in an X-ray room.")]

    story += H1("Designing a mammography room")
    story += [P("A mammography room is designed like an X-ray room, but every barrier is secondary: NCRP 147 "
                "assumes the image receptor stops the primary beam, so <b>Primary</b> cannot be chosen. Use the "
                "workload distribution <b>Mammography Room</b>, <b>Leakage and Side-Scatter</b> for the walls and "
                "door and <b>Leakage and Forward/Backscatter</b> for the floor and ceiling. The NCRP 147 average "
                "workload is 80 patients per week (<i>W</i><sub>norm</sub> = 6.7 mA·min per patient).")]
    story += figure("mammo_room.png", "The example mammography room: total workload 536 mA·min/week, i.e. 80 "
                                      "patients.", crop=(0, 0, 1175, 760))
    story += [P("If a material has no NCRP 147 transmission data for the chosen distribution, the result says "
                "<i>No NCRP 147 data for</i> that material.")]
    return story


def department():
    story = H1("Departments")
    story += [P("A department holds several rooms of any type: one floor, one floor plan, one report. Start with "
                "<b>Department</b> on the start screen or <b>File › New... › Design Department</b>.")]
    story += figure("department_rooms.png", "The Rooms tab of the example department.", crop=(0, 0, 1210, 470))
    story += [steps(["Type the <b>Department Name</b>. <b>New Department</b> adds another department in its own tab.",
                     "Set the <b>Number of Rooms</b>. For each room type a <b>Room Description</b> (its name) and "
                     "choose its type: <i>X-Ray room</i>, <i>CT Room</i> or <i>Mammography Room</i>.",
                     "Press <b>Design</b>: the room opens as a tab inside the department, and its results as a tab "
                     "on the right. The two tabs stay together: choosing one shows the other.",
                     "Design each room as in sections 4 to 6.",
                     "<b>Floor Plan</b>, <b>2D / 3D View</b> and <b>Export to Excel</b> on the Rooms tab work on all "
                     "the rooms of the department."])]
    story += figure("department_room.png", "A room of the department with its results.")
    return story


def floor_plan():
    story = H1("Floor plan")
    story += [P("<b>Floor Plan</b> opens the drawing of the room or department. Trace the walls on it, place the "
                "source and say what lies beyond each wall: the program measures the distances, suggests <i>T</i> "
                "and <i>P</i> and fills in the barriers.")]
    story += figure("plan_editor.png", "The floor plan of the example department, Barrier 4 of the X-ray room "
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
                     "The first wall becomes Barrier 1, the next Barrier 2, and so on.",
                     "<b>Place source</b>: the X-ray tube (CT: the isocenter; mammography: the unit).",
                     "<b>Add door</b>: click its two edges on a wall.",
                     "<b>Select wall / door</b>: click a wall and choose what is <b>Beyond it</b> (sets <i>T</i>), "
                     "its <b>Area</b> (sets <i>P</i>) and whether the <b>Primary beam</b> is aimed at it. The yellow "
                     "note shows the distance and the suggested values; <b>Apply to this barrier</b> writes them in.",
                     "<b>Floor and ceiling</b>: what is below and above, and whether the primary beam hits the floor.",
                     "<b>Apply everything to the room</b> fills in every barrier at once."])]
    story += note("Mouse wheel: zoom. Right-drag: move the drawing. Walls of neighbouring rooms that touch are "
                  "recognised, so 'Adjacent x-ray rooms' is suggested for them.")
    return story


def viewer():
    story = H1("2D / 3D view")
    story += [P("<b>2D / 3D View</b> shows the room, or the whole department, with the materials of every barrier, "
                "the dose beyond it and, if you wish, the radiation around the source. Without a floor plan the "
                "room is drawn schematically, each wall at its entered distance from the source.")]
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
                "materials from the room side out, the <b>Required</b> and <b>Planned</b> thickness of each (mm) and "
                "the <b>Dose beyond</b>. Pick a barrier to mark it on the 2D plan; click a wall on the plan to find "
                "it in the list.")]
    story += H2("Pointing at a wall")
    story += [P("Rest the pointer on a wall or door, in 2D or 3D, to see its materials, their thicknesses and the "
                "dose beyond it (" + fig("viewer_note.png") + "). Inside a room the note gives the floor and ceiling; with the radiation "
                "map on, it also gives the air kerma at that point.")]
    story += figure("viewer_note.png", "The note of Barrier 3: one planned gypsum board is not enough.",
                    crop=(500, 300, 1500, 960), width=130 * mm)
    story += H2("Radiation map")
    story += [P("<b>Radiation map</b> colours the weekly air kerma (mGy/week, logarithmic scale, without occupancy) "
                "around the source. Inside the room it falls as 1/<i>r</i><super>2</super>, with the primary beam "
                "toward the barriers it is aimed at. At each wall it crosses, it drops by the transmission of all "
                "the materials of that wall (planned, or the required thickness), the walls of other rooms "
                "included. The dashed lines mark 0.02 and 0.1 mGy/week, the NCRP 147 goals with <i>T</i> = 1.")]
    story += figure("viewer_goal.png", "Dose beyond vs goal P, with the radiation map.", crop=(0, 140, 1130, 1000))
    story += H2("3D view and options")
    story += [bullets(["The <b>3D view</b> tab shows the same rooms in 3D. Drag to rotate; pointing at a wall gives "
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
                "three sheets. It uses the last calculation of every barrier, so press Calculate first.")]
    story += table([["Sheet", "Contents"],
                    ["Summary", "One row per barrier: room, barrier, area, location (source of T), T, P, ΣK, B, the "
                                "thickness of each material, the dose beyond, the goal P, the materials and the "
                                "status (OK, met, EXCEEDED or what is missing)."],
                    ["Details", "One row per radiation type: workload distribution, source of K¹, preshielding, N, "
                                "U, T, K¹, d (and the part of it beyond the barrier), K and whether it was used for "
                                "the transmission."],
                    ["Rooms", "Room type and workload (CT: procedures, scans per procedure, DLP and kVp)."]],
                   [25, 145])
    rep = VALUES["xray_report"]
    head = rep["header"]
    pick = ["Barrier", "T", "P (mGy/week)", "ΣK (mGy/week)", "B", "Lead (mm)", "Concrete (mm)",
            "Gypsum Wallboard (mm)", "Dose beyond (mGy/week)"]
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
                "Examples folder...</b>). Change any value and press Calculate to see its effect.")]
    return story


def worked_examples():
    x, ct, mammo = VALUES["xray"], VALUES["ct"], VALUES["mammography"]
    story = H1("Worked examples")
    story += [P("These examples follow the built-in examples step by step. Open the example, select the barrier and "
                "compare: the program gives the same numbers. Small differences in the last digit come from "
                "rounding here.")]

    # ---------- secondary barrier ----------
    b3 = x["Barrier 3"]
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
    story += H2("Secondary barrier: X-ray room, Barrier 3 (corridor)")
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
    b4 = x["Barrier 4"]
    d1, d2 = b4["distributions"]
    K1 = d1["N"] * d1["U"] * d1["T"] * d1["K1"] / d1["d"] ** 2
    K2 = d2["N"] * d2["U"] * d2["T"] * d2["K1"] / d2["d"] ** 2
    K = K1 + K2
    close(K, b4["K_total"])
    B = b4["P"] / K
    conc, lead = b4["params"]["Concrete"], b4["params"]["Lead"]
    pre = b4["preshielding"]
    start = archer_transmission(lead, pre["Lead"])
    total = math.log(start / B)
    after = start * math.exp(-0.5 * total)
    xc = archer_thickness(conc, after) - archer_thickness(conc, start)
    xl = archer_thickness(lead, B) - archer_thickness(lead, after)
    close(xc, dict(b4["thickness"])["Concrete"])
    close(xl, dict(b4["thickness"])["Lead"])
    Tp = archer_transmission(conc, archer_thickness(conc, start) + 100)
    Tp = archer_transmission(lead, archer_thickness(lead, Tp) + 1)
    close(K * Tp, b4["check"]["dose"])
    story += H2("Two radiation types and layers: X-ray room, Barrier 4 (chest bucky wall)")
    story += [P(f"The wall behind the chest bucky receives the primary beam of the chest bucky distribution and the "
                f"secondary radiation of the whole room. Beyond it are offices (<i>T</i> = {b4['T']:g}, <i>P</i> = "
                f"{b4['P']:g} mGy/week); the source is {d1['d'] - b4['beyond']:.2f} m away, so <i>d</i> = "
                f"{d1['d'] - b4['beyond']:.2f} + {b4['beyond']:g} = {d1['d']:.2f} m.")]
    story += table([["Radiation type", "N", "U", "K<super>1</super> (mGy/patient)", "K (mGy/week)"],
                    [f"#1 Primary, {d1['distribution']}, bucky", f"{d1['N']:g}", f"{d1['U']:g}", f"{d1['K1']:g}",
                     fmt(K1)],
                    [f"#2 Secondary, {d2['distribution']}", f"{d2['N']:g}", f"{d2['U']:g}", f"{d2['K1']:g}",
                     fmt(K2)],
                    ["<b>Total</b>", "", "", "", f"<b>{fmt(K)}</b>"]], [72, 16, 14, 34, 34])
    story += [P(f"<i>B</i> = {b4['P']:g} / {fmt(K)} = <b>{fmt(B)}</b>, with the transmission data of the primary "
                f"(ticked <b>Set for the calculation</b>). The wall is one barrier of concrete on the room side and "
                f"lead outside, half of the shielding each:")]
    story += [bullets([f"The bucky (0.85 mm lead) already lets through {fmt(start)}. The rest of the attenuation is "
                       f"ln({fmt(start)} / {fmt(B)}) = {total:.3f}, so each layer takes {total / 2:.3f}.",
                       f"After the concrete the transmission must be {fmt(start)} × e<super>−{total / 2:.3f}</super> "
                       f"= {fmt(after)}: concrete from {archer_thickness(conc, start):.1f} to "
                       f"{archer_thickness(conc, after):.1f} mm of equivalent thickness, i.e. <b>{xc:.2f} mm</b>.",
                       f"The lead takes it from {fmt(after)} to {fmt(B)}: <b>{xl:.2f} mm</b>."])]
    story += [P(f"Planned: 100 mm concrete + 1 mm lead. Layer after layer the transmission becomes {fmt(Tp)} and the "
                f"dose beyond {fmt(K * Tp)} mGy/week, {MET}.")]

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
    m2 = mammo["Barrier 2"]
    dist = m2["distributions"][0]
    K = dist["N"] * dist["U"] * dist["T"] * dist["K1"] / dist["d"] ** 2
    close(K, m2["K_total"])
    B = m2["P"] / K
    gyp, lead = m2["params"]["Gypsum Wallboard"], m2["params"]["Lead"]
    close(archer_thickness(gyp, B), dict(m2["thickness"])["Gypsum Wallboard"])
    story += H2("Mammography room, Barrier 2 (offices)")
    story += [P(f"Total workload 536 mA·min/week with <i>W</i><sub>norm</sub> = 6.7 mA·min/patient gives <i>N</i> = "
                f"{dist['N']:g} patients/week. The wall is secondary (leakage and side-scatter, "
                f"<i>K</i><super>1</super><sub>sec</sub> = {dist['K1']:g} mGy/patient), offices beyond (<i>T</i> = 1), "
                f"source {dist['d'] - m2['beyond']:.1f} m away, plus {m2['beyond']:g} m beyond the wall "
                f"(<i>d</i> = {dist['d']:.1f} m):")]
    story += formula(f"<i>K</i> = {dist['N']:g} × {dist['K1']:g} / {dist['d']:.1f}<super>2</super> = "
                     f"<b>{fmt(K)}</b> mGy/week<br/><i>B</i> = 0.02 / {fmt(K)} = <b>{fmt(B)}</b>")
    story += [P(f"Mammography transmission data: <b>{archer_thickness(gyp, B):.2f} mm gypsum wallboard</b> or "
                f"<b>{archer_thickness(lead, B):.3f} mm lead</b>. One standard gypsum board is more than enough.")]

    story += H2("A whole department")
    story += [P("The example department puts the three rooms on one floor plan, with a control room between the "
                "X-ray and CT rooms and a corridor below. Its 2D / 3D view shows every barrier, and the radiation "
                "of each room crossing the walls of the others.")]
    story += figure("viewer_department.png", "The example department in the 2D / 3D view.",
                    crop=(0, 140, 1130, 1000))
    return story


def reference():
    story = H1("NCRP 147 data used by the program")
    story += [P("The program reads these values from <b>Data Shielding.xlsx</b>; they are the NCRP Report No. 147 "
                "values (the report itself is in the Help menu).")]
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
                    ["Occupied point beyond the barrier (4.1.2)", "Walls and door 0.3 m; ceiling 0.5 m above the "
                                                                  "floor of the room above; floor: 1.7 m above the "
                                                                  "floor below (1.3 m under a floor with a 3 m storey)"],
                    ["CT secondary air kerma per mGy·cm of DLP at 1 m, per scan", "Body 1.2 × 3×10<super>−4</super> "
                                                                                  "cm<super>−1</super>; head "
                                                                                  "9×10<super>−5</super> cm<super>−1"
                                                                                  "</super>"],
                    ["CT scans per procedure", "1.4: every procedure once, 40 % again with contrast"],
                    ["CT typical DLP per scan", "Body 550 mGy·cm; head 1200 mGy·cm"],
                    ["Materials", "Lead, concrete (2.35 g/cm³), gypsum wallboard, steel, plate glass, wood; CT: "
                                  "lead and concrete"]], [70, 100])
    return story


def troubleshooting():
    story = H1("Messages and tips")
    story += table([["You see", "Meaning", "What to do"],
                    [f"<font color='{OK}'>none needed</font>", "B ≥ 1: the air kerma beyond is already below P.",
                     "Nothing; the barrier needs no extra shielding."],
                    [f"<font color='{BAD}'>Missing: ...</font>", "An input of the barrier is empty.",
                     "Press Calculate: the Missing data window says what to fill in, and the fields turn red."],
                    ["No NCRP 147 data for ...", "NCRP 147 has no transmission data of that material for the "
                                                 "workload distribution.", "Choose another material."],
                    [f"<font color='{BAD}'>Missing: Select Material</font>", "A material list was left empty.",
                     "Choose the material under Select Materials."],
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
                       "empirical model of photon attenuation. <i>Health Physics</i> 44:507–517, 1983."])]
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
    content()  # numbers the figures
    story = content()
    check_glyphs(story)
    doc = Guide(OUTPUT)
    doc.multiBuild(story)
    for name in os.listdir(IMAGES):  # cropped copies
        if name.startswith("_"):
            os.remove(os.path.join(IMAGES, name))
    print("written", OUTPUT)


if __name__ == "__main__":
    sys.exit(build())
