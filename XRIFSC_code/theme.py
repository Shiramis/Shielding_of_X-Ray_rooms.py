"""Look of the program: one colour palette, fonts and ttk styles, and the application icon."""
import math
import re
from tkinter import Canvas
from tkinter import font as tkfont
from tkinter import ttk

from PIL import Image, ImageDraw, ImageOps

# ===================== palette =====================
NAVY = "#14212e"          # header bar, start screen
NAVY_2 = "#1f3347"        # tabs and cards on navy
NAVY_3 = "#2a4560"        # hover on navy
ON_NAVY = "#e8eef4"       # text on navy
ON_NAVY_MUTED = "#9fb3c8"
ACCENT = "#1a73c8"        # main actions (Design, Calculate)
ACCENT_DARK = "#145a9e"
ACCENT_LIGHT = "#e3eefa"
BG = "#e9eef3"            # behind the content
SURFACE = "#f9fbfc"       # content areas
FIELD = "#ffffff"
TEXT = "#121b25"          # dark text for good contrast
MUTED = "#4b5866"
BORDER = "#c9d3de"
TAB = "#dfe6ed"
DANGER = "#c62828"
MISSING = "#ffd2d2"
YELLOW = "#f6c026"        # radiation yellow, used by the icon

# fonts (apply_theme picks the best installed family; these are the fallbacks)
FAMILY = SEMIBOLD = LIGHT = "Helvetica"
BASE, BOLD, SMALL, HEADING = (FAMILY, 11), (FAMILY, 11, "bold"), (FAMILY, 10), (FAMILY, 14, "bold")
SCALE = 1.0  # screen pixels per 1/96 inch: 1.25 on a Windows screen at 125 %


def px(pixels):
    """A size in pixels for this screen, so the layout looks the same at any display scaling."""
    return int(round(pixels * SCALE))


def make_dpi_aware():
    """Let Windows draw the program at the real screen resolution: sharp text instead of a stretched,
    blurry window. Call before the main window is created."""
    import ctypes
    import platform
    if platform.system() != "Windows":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def pick_font(root, *names):
    families = set(tkfont.families(root))
    return next((name for name in names if name in families), "TkDefaultFont")


# ===================== subscripts: a text writes them d_{P} =====================
SUBSCRIPT = re.compile(r"_\{([^}]*)\}")


def rich_parts(text):
    """'d_{P} = 2 m' -> [('d', False), ('P', True), (' = 2 m', False)]."""
    parts, last = [], 0
    for match in SUBSCRIPT.finditer(text):
        if match.start() > last:
            parts.append((text[last:match.start()], False))
        parts.append((match.group(1), True))
        last = match.end()
    if last < len(text) or not parts:
        parts.append((text[last:], False))
    return parts


def plain(text):
    """The text without the marks of its subscripts: d_{P} -> dP."""
    return SUBSCRIPT.sub(r"\1", text)


def subscript_font(font):
    small = tkfont.Font(font=font)
    small.configure(size=max(7, round(abs(small.actual("size")) * 0.72)))
    return small


def insert_rich(text, string, tags=()):
    """Add to the end of a Text widget a string whose subscripts are written d_{P}."""
    if "subscript" not in text.tag_names():
        text.tag_configure("subscript", offset=-px(3), font=subscript_font(text.cget("font")))
    for part, sub in rich_parts(string):
        text.insert("end", part, tuple(tags) + (("subscript",) if sub else ()))


class RichLabel(Canvas):
    """A label whose text can have subscripts, written d_{P}. Like a label, its text is set with
    configure(text=...) and read with cget('text')."""

    def __init__(self, master, text="", foreground=None, background=None, font=None):
        super().__init__(master, width=1, height=1, highlightthickness=0, borderwidth=0,
                         background=background or SURFACE)
        self.font = tkfont.Font(font=font or BASE)
        self.small = subscript_font(self.font)
        self.foreground = foreground or TEXT
        self.text = None
        self.configure(text=text)

    def configure(self, cnf=None, **kw):
        if "text" in kw:
            self.draw(kw.pop("text"))
        if cnf or kw:
            return super().configure(cnf, **kw)

    config = configure

    def cget(self, key):
        return self.text if key == "text" else super().cget(key)

    def draw(self, text):
        if text == self.text:
            return
        self.text = text
        self.delete("all")
        line = self.font.metrics("linespace")
        # the subscript's baseline a little under the line's
        drop = self.font.metrics("ascent") - self.small.metrics("ascent") + px(3)
        width = 0
        for row, content in enumerate(text.split("\n")):
            x = 0
            for part, sub in rich_parts(content):
                font = self.small if sub else self.font
                self.create_text(x, row * line + (drop if sub else 0), text=part, anchor="nw", font=font,
                                 fill=self.foreground)
                x += font.measure(part)
            width = max(width, x)
        super().configure(width=max(width, 1), height=(text.count("\n") + 1) * line + px(3))


def apply_theme(root):
    """ttk styles for the whole program. Call once, right after creating the main window."""
    global FAMILY, SEMIBOLD, LIGHT, BASE, BOLD, HEADING, SMALL, SCALE
    SCALE = root.winfo_fpixels("1i") / 96
    FAMILY = pick_font(root, "Segoe UI", "Helvetica Neue", "Helvetica", "Arial")
    SEMIBOLD = pick_font(root, "Segoe UI Semibold", FAMILY)
    LIGHT = pick_font(root, "Segoe UI Light", FAMILY)
    # 11 pt: comfortable to read for long sessions
    BASE, BOLD, SMALL = (FAMILY, 11), (SEMIBOLD, 11), (FAMILY, 10)
    HEADING = (SEMIBOLD, 14)
    # Entry fields, comboboxes and spin boxes take Tk's named fonts, not the style's
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkTooltipFont"):
        tkfont.nametofont(name, root=root).configure(family=FAMILY, size=BASE[1])
    # Classic Tk widgets only: a global "*Font" would also override the fonts of every ttk style
    for widget_class in ("Menu", "Label", "Text", "Listbox", "Button", "Entry"):
        root.option_add(f"*{widget_class}.font", BASE)
    root.option_add("*TCombobox*Listbox.font", BASE)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.configure(background=NAVY)

    style = ttk.Style(root)
    style.theme_use("clam")  # unlike the native Windows theme, it lets every colour be set
    style.configure(".", background=SURFACE, foreground=TEXT, font=BASE, bordercolor=BORDER, lightcolor=SURFACE,
                    darkcolor=BORDER, troughcolor=BG, focuscolor=ACCENT, selectbackground=ACCENT,
                    selectforeground="white", fieldbackground=FIELD, insertcolor=TEXT, arrowcolor=MUTED)
    style.map(".", foreground=[("disabled", "#9aa6b2")])

    # frames and labels
    style.configure("TFrame", background=SURFACE)
    style.configure("ML.TFrame", background=NAVY)
    for name in ("TLabel", "AL.TLabel"):
        style.configure(name, background=SURFACE, foreground=TEXT, font=BASE)
    style.configure("BL.TLabel", background=SURFACE, foreground=NAVY, font=HEADING)
    style.configure("BL2.TLabel", background=SURFACE, foreground=TEXT, font=BOLD)
    style.configure("RL.TLabel", background=SURFACE, foreground=DANGER, font=BASE)
    style.configure("OK.TLabel", background=SURFACE, foreground="#2e7d32", font=BASE)
    style.configure("Muted.TLabel", background=SURFACE, foreground=MUTED, font=BASE)
    style.configure("CL.TLabel", background=NAVY, foreground=ON_NAVY, font=(LIGHT, 22))
    style.configure("TLabelframe", background=SURFACE, bordercolor=BORDER)
    style.configure("TLabelframe.Label", background=SURFACE, foreground=NAVY, font=BOLD)

    # buttons
    style.configure("TButton", background="#f1f4f8", foreground=TEXT, bordercolor=BORDER, lightcolor="#f8fafc",
                    darkcolor="#e4e9ef", padding=(px(12), px(5)), font=BASE, focusthickness=1)
    style.map("TButton", background=[("pressed", "#d5dee8"), ("active", "#e6edf5")],
              bordercolor=[("focus", ACCENT)])
    style.configure("Accent.TButton", background=ACCENT, foreground="white", bordercolor=ACCENT_DARK,
                    lightcolor=ACCENT, darkcolor=ACCENT_DARK, font=BOLD)
    style.map("Accent.TButton", background=[("pressed", ACCENT_DARK), ("active", "#1f80dc")],
              foreground=[("disabled", "#d9e6f3")])
    style.configure("Close.TButton", background=SURFACE, foreground=MUTED, bordercolor=BORDER, padding=(px(6), px(2)))
    style.map("Close.TButton", background=[("active", DANGER)], foreground=[("active", "white")])
    style.configure("Ghost.TButton", background=NAVY_2, foreground=ON_NAVY, bordercolor=NAVY_3, lightcolor=NAVY_2,
                    darkcolor=NAVY_2, padding=(px(16), px(7)), font=BASE)
    style.map("Ghost.TButton", background=[("pressed", NAVY), ("active", NAVY_3)])
    style.configure("AL.TMenubutton", background=NAVY_2, foreground=ON_NAVY, bordercolor=NAVY_3, lightcolor=NAVY_2,
                    darkcolor=NAVY_2, arrowcolor=ON_NAVY, padding=(px(16), px(7)), font=BASE)
    style.map("AL.TMenubutton", background=[("active", NAVY_3)])
    style.configure("TMenubutton", background=FIELD, foreground=TEXT, bordercolor=BORDER, lightcolor=FIELD,
                    darkcolor=FIELD, arrowcolor=MUTED, padding=(px(8), px(3)), font=BASE)
    style.map("TMenubutton", background=[("active", ACCENT_LIGHT)])

    # input fields
    field = dict(fieldbackground=FIELD, bordercolor=BORDER, lightcolor=FIELD, darkcolor=FIELD, padding=3)
    focus = dict(bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)])
    style.configure("TEntry", **field)
    style.map("TEntry", **focus)
    style.configure("Missing.TEntry", fieldbackground=MISSING, bordercolor=DANGER, lightcolor=DANGER,
                    darkcolor=DANGER, padding=3)
    style.configure("TSpinbox", background="#f1f4f8", **field)
    style.map("TSpinbox", **focus)
    style.configure("TCombobox", background=FIELD, **field)
    style.map("TCombobox", fieldbackground=[("readonly", FIELD), ("disabled", BG)], background=[("active", ACCENT_LIGHT)],
              selectbackground=[("readonly", FIELD)], selectforeground=[("readonly", TEXT)], **focus)
    make_indicators(root, style)
    for name in ("TRadiobutton", "TCheckbutton"):
        style.configure(name, background=SURFACE, foreground=TEXT, font=BASE, padding=2)
        style.map(name, background=[("active", SURFACE)])

    # notebooks: navy tab bar for departments and rooms, light tabs inside them
    style.configure("TNotebook", background=SURFACE, bordercolor=BORDER, tabmargins=(4, 4, 4, 0))
    style.configure("TNotebook.Tab", background=TAB, foreground=MUTED, bordercolor=BORDER, lightcolor=TAB,
                    padding=(px(12), px(4)), font=BASE)
    style.map("TNotebook.Tab", background=[("selected", SURFACE), ("active", "#eaf0f6")],
              foreground=[("selected", ACCENT_DARK)], lightcolor=[("selected", SURFACE)],
              expand=[("selected", (1, 1, 1, 0))])
    style.configure("BL.TNotebook", background=SURFACE)
    style.configure("AL.TNotebook", background=NAVY, bordercolor=NAVY, tabmargins=(6, 6, 6, 0))
    style.configure("AL.TNotebook.Tab", background=NAVY_2, foreground=ON_NAVY_MUTED, bordercolor=NAVY,
                    lightcolor=NAVY_2, padding=(px(18), px(6)), font=BOLD)
    style.map("AL.TNotebook.Tab", background=[("selected", SURFACE), ("active", NAVY_3)],
              foreground=[("selected", NAVY), ("active", ON_NAVY)], lightcolor=[("selected", SURFACE)],
              expand=[("selected", (1, 1, 1, 0))])

    # lists
    style.configure("Treeview", background=FIELD, fieldbackground=FIELD, foreground=TEXT, font=BASE,
                    rowheight=px(26), bordercolor=BORDER, lightcolor=FIELD, darkcolor=FIELD)
    style.map("Treeview", background=[("selected", ACCENT_LIGHT)], foreground=[("selected", TEXT)])
    style.configure("Treeview.Heading", background=TAB, foreground=MUTED, font=BASE, bordercolor=BORDER,
                    lightcolor=TAB, darkcolor=BORDER, padding=(px(6), px(3)))
    style.map("Treeview.Heading", background=[("active", "#eaf0f6")])

    # scrollbars and dividers
    style.configure("TScrollbar", background="#cfd7e0", troughcolor=BG, bordercolor=BG, lightcolor="#cfd7e0",
                    darkcolor="#cfd7e0", arrowcolor=MUTED, gripcount=0)
    style.map("TScrollbar", background=[("active", "#b3bfcc")])
    style.configure("TPanedwindow", background=BG)
    style.configure("Sash", sashthickness=px(6), gripcount=0, background=BG)
    return style


# ===================== check and radio indicators =====================
_images = []  # Tk images must stay referenced


def indicator_image(root, kind, selected, hover=False, disabled=False, size=None):
    """Rounded check box or round radio button, drawn 4x larger and scaled down for smooth edges."""
    from PIL import ImageTk
    size = size or px(18)
    k = 4
    s, margin = size * k, px(6) * k  # transparent margin between the indicator and its text
    image = Image.new("RGBA", (s + margin, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    box = (k, k, s - k, s - k)
    if selected:
        fill, outline = ("#a9c3df", "#a9c3df") if disabled else (ACCENT, ACCENT_DARK if hover else ACCENT)
    else:
        fill, outline = (BG, "#c4ccd5") if disabled else (FIELD, ACCENT if hover else "#8d9bab")
    if kind == "check":
        draw.rounded_rectangle(box, radius=4 * k, fill=fill, outline=outline, width=int(1.6 * k))
        if selected:
            draw.line([(0.27 * s, 0.52 * s), (0.44 * s, 0.68 * s), (0.74 * s, 0.34 * s)], fill="white",
                      width=int(2.2 * k), joint="curve")
    else:
        draw.ellipse(box, fill=FIELD if not disabled else BG, outline=outline if not selected else fill,
                     width=int(1.6 * k) if not selected else int(5 * k))
        if selected:
            r = 0.17 * s
            draw.ellipse((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), fill=FIELD)
    photo = ImageTk.PhotoImage(image.resize(((s + margin) // k, size), Image.Resampling.LANCZOS), master=root)
    _images.append(photo)
    return photo


def make_indicators(root, style):
    for kind, element, widget in (("check", "Modern.Checkbutton.indicator", "Checkbutton"),
                                  ("radio", "Modern.Radiobutton.indicator", "Radiobutton")):
        image = lambda **state: indicator_image(root, kind, **state)
        style.element_create(element, "image", image(selected=False),
                             ("disabled", "selected", image(selected=True, disabled=True)),
                             ("disabled", image(selected=False, disabled=True)),
                             ("active", "selected", image(selected=True, hover=True)),
                             ("selected", image(selected=True)),
                             ("active", image(selected=False, hover=True)), sticky="w")
        style.layout(f"T{widget}", [(f"{widget}.padding", {"sticky": "nswe", "children": [
            (element, {"side": "left", "sticky": ""}),
            (f"{widget}.focus", {"side": "left", "sticky": "w", "children": [
                (f"{widget}.label", {"sticky": "nswe"})]})]})])


# ===================== icon =====================
def draw_icon(size):
    """The application icon: a radiation-yellow shield with a trefoil on a blue tile."""
    big = 1024
    gradient = ImageOps.colorize(Image.linear_gradient("L").resize((big, big)), black="#1f7ad6", white="#0d3561")
    tile = Image.new("L", (big, big), 0)
    ImageDraw.Draw(tile).rounded_rectangle((24, 24, big - 24, big - 24), radius=210, fill=255)
    icon = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    icon.paste(gradient, (0, 0), tile)
    draw = ImageDraw.Draw(icon)

    # shield: straight top and sides, curved bottom meeting in a point
    left, right, top, shoulder, tip = 0.22 * big, 0.78 * big, 0.17 * big, 0.52 * big, 0.88 * big
    curve = lambda x0, x1: [(x0 + (x1 - x0) * s, shoulder + (tip - shoulder) * math.sin(s * math.pi / 2))
                            for s in (k / 30 for k in range(31))]
    outline = [(left, top), (big / 2, top - 0.035 * big), (right, top), (right, shoulder)]
    outline += curve(right, big / 2) + curve(left, big / 2)[::-1] + [(left, shoulder)]
    draw.polygon(outline, fill="white")
    mx, my = big / 2, (top + tip) / 2  # the same shape, 91 %, leaves a white rim
    draw.polygon([(mx + (x - mx) * 0.91, my + (y - my) * 0.91) for x, y in outline], fill=YELLOW)

    # trefoil: three 60° blades and a centre disc
    cx, cy = big / 2, 0.505 * big
    outer, gap, centre = 0.215 * big, 0.085 * big, 0.06 * big
    for angle in (90, 210, 330):  # blades pointing down, upper-left and upper-right (PIL angles go clockwise)
        draw.pieslice((cx - outer, cy - outer, cx + outer, cy + outer), angle - 30, angle + 30, fill=NAVY)
    draw.ellipse((cx - gap, cy - gap, cx + gap, cy + gap), fill=YELLOW)
    draw.ellipse((cx - centre, cy - centre, cx + centre, cy + centre), fill=NAVY)
    return icon.resize((size, size), Image.Resampling.LANCZOS)


def write_icon_files(png_path, ico_path):
    draw_icon(256).save(png_path)
    draw_icon(256).save(ico_path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
