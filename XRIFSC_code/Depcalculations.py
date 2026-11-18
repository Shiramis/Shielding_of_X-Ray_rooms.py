from tkinter import *
from tkinter import ttk, messagebox
import theme
import math
import os
from openpyxl import load_workbook
import os
import sys

def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temporary folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

# Update the excel file path
excel_path = resource_path('Data Shielding.xlsx')
if not os.path.exists(excel_path):  # without the NCRP 147 data nothing can be calculated
    messagebox.showerror("Shielding of X-ray Rooms", "Cannot find the NCRP 147 data file:\n" + excel_path
                         + "\n\nKeep 'Data Shielding.xlsx' next to the program, or install the program again.")
    sys.exit(1)

wb = load_workbook(excel_path)

# First column of each material's (alpha, beta, gamma) in the 'prim abc' / 'sec abc' sheets (0-based)
MATERIAL_COLUMNS = {"Lead": 1, "Concrete": 4, "Gypsum Wallboard": 7, "Steel": 10, "Plate Glass": 13, "Wood": 16}
# NCRP 147 unshielded primary air kerma per patient at 1 m (mGy/patient)
PRIMARY_KERMA = {"Rad Room (chest bucky)": "2.3", "Rad Room (floor or other barriers)": "5.2",
                 "Rad Tube (R&F room)": "5.9", "Chest Room": "1.2"}

def archer_thickness(params, B):
    """Thickness (mm) with transmission B (Archer equation, NCRP 147); params = (alpha, beta, gamma)."""
    a, b, g = params
    return (1 / (a * g)) * math.log((B ** (-g) + b / a) / (1 + b / a))


def archer_transmission(params, x):
    """Transmission of a thickness x (mm): the inverse of archer_thickness."""
    a, b, g = params
    return ((1 + b / a) * math.exp(a * g * x) - b / a) ** (-1 / g)


def stack_transmission(params, layers, start=0.0):
    """Transmission of the layers [(material, mm)] one after the other, from the inside out; params: {material:
    (alpha, beta, gamma)}. start: thickness (mm, in the first material) already in front of them (preshielding).
    Each next layer begins at the equivalent thickness of what is in front of it."""
    transmission = 1.0
    for k, (material, x) in enumerate(layers):
        before = start if k == 0 else archer_thickness(params[material], transmission)
        transmission = archer_transmission(params[material], before + x)
    return transmission


def layered_thicknesses(layers, fractions, B, start=1.0):
    """Layers from the inside out, each giving its fraction of the attenuation ln(start/B).
    start is the transmission already given in front of them (preshielding)."""
    total = math.log(start / B) if B < start else 0.0
    transmission, thicknesses = start, []
    for params, fraction in zip(layers, fractions):
        after = transmission * math.exp(-fraction * total)
        # this layer begins at the equivalent thickness of everything in front of it
        thicknesses.append(max(archer_thickness(params, after) - archer_thickness(params, transmission), 0.0))
        transmission = after
    return thicknesses


# ===================== several radiation types on one barrier (NCRP 147 Sections 5.3.5, 5.4.2) =====================
# Each radiation type goes through the barrier with its own transmission data (its workload distribution, primary or
# secondary) and its own preshielding. A component: {"K": air kerma beyond the barrier without it (mGy/week),
# "params": {material: (alpha, beta, gamma)}, "pre": {material: preshielding thickness (mm)}, "start": transmission
# of the preshielding, in front of layers}.
def has_data(params, material):
    values = params.get(material)
    return bool(values) and bool(values[0]) and bool(values[2])


def preshielding_transmission(params, preshielding):
    """Transmission of the preshielding: Table 4.6 gives it in lead, concrete and steel; the first with data."""
    for material in ("Lead", "Concrete", "Steel"):
        if preshielding.get(material) and has_data(params, material):
            return archer_transmission(params[material], preshielding[material])
    return 1.0


def through(params, layers, start=1.0):
    """Transmission of one radiation type through the layers [(material, mm)] one after the other, from the inside out,
    after what is in front of them lets 'start' through. Each layer begins at the equivalent thickness of that."""
    transmission = start
    for material, x in layers:
        transmission = archer_transmission(params[material], archer_thickness(params[material], transmission) + x)
    return transmission


def thickness_for(dose, goal, high):
    """The thickness x >= 0 at which dose(x), which falls with x, comes down to goal; 0 if dose(0) <= goal.
    high: a thickness at which it is already below the goal (doubled until it is)."""
    if dose(0.0) <= goal:
        return 0.0
    low, high = 0.0, max(high, 1e-6)
    while dose(high) > goal:
        low, high = high, 2 * high
    for _ in range(200):
        middle = (low + high) / 2
        low, high = (middle, high) if dose(middle) > goal else (low, middle)
        if high - low <= 1e-12 * high:
            break
    return (low + high) / 2


def thickness_alone(components, material, P):
    """Thickness of one material, the only one of the barrier: sum of K B(x + preshielding) = P."""
    if len(components) == 1:  # the Archer equation, minus the preshielding
        c = components[0]
        return max(archer_thickness(c["params"][material], P / c["K"]) - c["pre"].get(material, 0.0), 0.0)
    total = sum(c["K"] for c in components)
    dose = lambda x: sum(c["K"] * archer_transmission(c["params"][material], x + c["pre"].get(material, 0.0))
                         for c in components)
    return thickness_for(dose, P, max(archer_thickness(c["params"][material], min(P / total, 1.0))
                                      for c in components))


def thickness_layers(components, materials, fractions, P):
    """Layers of one barrier, from the inside out, each giving its fraction of the attenuation of the air kerma from
    what the preshielding lets through down to P; every radiation type goes through all of them."""
    if len(components) == 1:
        c = components[0]
        return layered_thicknesses([c["params"][m] for m in materials], fractions, P / c["K"], c["start"])
    total = sum(c["K"] for c in components)
    effective = lambda layers: sum(c["K"] * through(c["params"], layers, c["start"]) for c in components) / total
    begin = effective([])
    attenuation = math.log(begin * total / P) if P < begin * total else 0.0
    layers, done = [], 0.0
    for material, fraction in zip(materials, fractions):
        done += fraction
        goal = begin * math.exp(-done * attenuation)
        high = max(archer_thickness(c["params"][material], goal) for c in components)
        layers.append((material, thickness_for(lambda x: effective(layers + [(material, x)]), goal, high)))
    return [x for _, x in layers]


# NCRP 147 total workload per patient Wnorm (mA·min/patient) of each workload distribution
WORKLOAD_NORM = {row[0]: row[1] for row in wb['Workload'].iter_rows(max_col=2, values_only=True)
                 if row[0] and isinstance(row[1], (int, float))}
# NCRP 147 unshielded secondary air kerma per patient at 1 m: the whole row of each workload distribution
UNSHIELDED_SECONDARY = {row[0]: row for row in wb['Uns Air Kerma'].iter_rows(min_row=2, values_only=True) if row[0]}

# ===================== workload distributions from the literature (not NCRP 147) =====================
# Their names end with the source; SOURCES gives it in full for the labels and the report
SOURCES = {}
# Sheets with the (alpha, beta, gamma) of a distribution that is not in 'prim abc' / 'sec abc': (primary, secondary)
TRANSMISSION_SHEETS = {}


def literature_rows(sheet):
    """Rows of a literature sheet: a name, then numbers (title and header rows above them)."""
    return [row for row in wb[sheet].iter_rows(min_row=3, values_only=True)
            if isinstance(row[0], str) and isinstance(row[1], (int, float))]


# Digital radiography (Kirby KM, Schueler BA, Littrell LA, Long Z, J. Appl. Clin. Med. Phys. 24 (2023) e13962,
# table 3): the workload spectrum of each barrier of a general and a pediatric DR room, turned into air kerma and
# transmission with the NCRP 147 method (Appendices B and C) by tools/literature_data.py. The workload of a barrier
# already includes how often the beam points at it (U = 1 with all the patients of the room).
KIRBY = []
for _row in literature_rows("Kirby 2023 kerma"):
    KIRBY.append(_row[0])
    WORKLOAD_NORM[_row[0]] = _row[1]
    UNSHIELDED_SECONDARY[_row[0]] = _row[:9]  # the columns of 'Uns Air Kerma'
    if _row[9] is not None:
        PRIMARY_KERMA[_row[0]] = f"{_row[9]:g}"
    SOURCES[_row[0]] = "Kirby et al. 2023"
    TRANSMISSION_SHEETS[_row[0]] = ("Kirby 2023 prim abc", "Kirby 2023 sec abc")

# Interventional rooms (Biondi M et al., Phys. Med. 125 (2024) 104509): workload per patient (table 2) and secondary
# transmission (table 3; lead, concrete and gypsum wallboard). Secondary only: the image receptor stops the primary
# beam. Unshielded secondary air kerma: that of NCRP 147 for cardiac or peripheral angiography x Wsite / Wnorm
# (their Eq. 4, NCRP 147 4.1.4).
BIONDI = []
for _row in literature_rows("Biondi 2024"):
    _name, _w_site, _base = _row[0], _row[6] / 60, UNSHIELDED_SECONDARY[_row[8]]  # mAs -> mA min per patient
    BIONDI.append(_name)
    WORKLOAD_NORM[_name] = _w_site
    UNSHIELDED_SECONDARY[_name] = (_name, _w_site, _base[2], _base[3]) + tuple(v * _w_site / _base[1]
                                                                                for v in _base[4:9])
    SOURCES[_name] = "Biondi et al. 2024"
    TRANSMISSION_SHEETS[_name] = (None, "Biondi 2024 sec abc")

# Digital breast tomosynthesis: Yang K, Schultz TJ, Li X, Liu B, J. Radiol. Prot. 37 (2017) 230, table 9.
# Unshielded scatter air kerma per view at 1 m (mGy/view): CC views, oblique views with the beam toward (T) or
# away (A) from the barrier, in 2D and 3D mode
DBT = "Digital Breast Tomosynthesis – Yang 2017"
SOURCES[DBT] = "Yang et al. 2017"
# Names of earlier versions, for opening their projects
LEGACY_DISTRIBUTIONS = {"Digital Breast Tomosynthesis": DBT}
DBT_VIEW_KERMA = {"2D": {"CC": 6.07e-3, "T": 4.83e-2, "A": 6.49e-3},
                  "3D": {"CC": 7.85e-3, "T": 1.43e-2, "A": 7.89e-3}}
DBT_MODES = {1: ("2D",), 2: ("3D",), 3: ("2D", "3D")}  # the choice 2D, 3D, 2D + 3D


def dbt_kerma(mode):
    """Unshielded scatter air kerma per patient at 1 m (mGy/patient) in a DBT mode: both breasts, a CC and an
    oblique view each, one oblique toward and one away from the barrier (as in the example of Yang et al.)."""
    return sum(2 * DBT_VIEW_KERMA[m]["CC"] + DBT_VIEW_KERMA[m]["T"] + DBT_VIEW_KERMA[m]["A"]
               for m in DBT_MODES[mode])


# Transmission data for a primary beam at a given kVp: NCRP 147, or modern digital radiography (Li X, Marschall TA,
# Yang K, Liu B, Med. Phys. 2024, doi:10.1002/mp.17449, tables 1 and 2: Agfa DR 600, 60-120 kV every 10 kV)
KVP_DATA = ["NCRP 147", "DR 600, default filtration (Li 2024)", "DR 600, +1 mm Al +0.1 mm Cu (Li 2024)"]

# What to do for each missing input, shown in the "Missing data" window
NL = chr(10)

MISSING_HELP = {
    "Radiation type (Primary / Secondary)": "at 'Select Radiation Type' choose Primary or Secondary.",
    "Workload": "at the top of the room choose 'Write total Workload' or 'The Number of Patients per week' "
                "and type the value (or tick 'Different Workload' on this radiation type).",
    "Workload Distribution (X-ray room or kVp)": "at 'Workload Distribution' choose 'X-Ray Room' and select the "
                                                 "room in the list, or 'Give kVp'. Every radiation type needs it: "
                                                 "it goes through the barrier with these transmission data.",
    "Secondary radiation only": "this workload distribution (Biondi et al. 2024) has data for secondary radiation "
                                "only: in fluoroscopy and angiography the image receptor stops the primary beam. "
                                "Choose 'Secondary', or another workload distribution.",
    "Use Factor (U)": "type U in the 'Use Factor' box (NCRP 147: floor 0.89, cross-table wall 0.09, "
                      "chest bucky wall 1; Kirby et al. 2023: 1).",
    "Unshielded Air Kerma": "primary: type K in 'Primary Unshielded Air Kerma'. Secondary: choose 'Select "
                            "Unshielded Secondary Air Kerma' (the value suggested for the workload distribution) "
                            "and the type of scatter (needs an X-ray room, not a kVp), or choose 'Write' and type "
                            "the value. Digital Breast Tomosynthesis: choose 2D, 3D or 2D + 3D.",
    "kVp for the DR 600 data (60-120 kV, every 10 kV)": "the DR 600 transmission data (Li et al. 2024) exist for "
                                                        "60, 70, ... 120 kV: choose one of these, or the NCRP 147 "
                                                        "data.",
    "Patients per week (DBT)": "NCRP 147 gives no workload per patient (Wnorm) for Digital Breast Tomosynthesis: "
                               "at the top of the room choose 'The Number of Patients per week' (or tick "
                               "'Different Workload' on this radiation type).",
    "Occupancy Factor (T)": "under 'Shielding Area' choose 'Write occupancy factor (T)' and type it, "
                            "or 'select Location' and pick what is beyond the barrier.",
    "Distance from the Source to the Barrier (m)": "type the distance (dP, dL, dS or dsec) from the X-ray source "
                                                   "to the barrier in metres; the distance to the person beyond it "
                                                   "is added (or tick 'Enter the whole distance' and type all of it).",
    "Distance beyond the barrier (m)": "next to the distance, type how far beyond the barrier the person to "
                                       "protect is (NCRP 147 4.1.2): walls and door 0.3 m, ceiling 0.5 m, floor "
                                       "the floor-to-floor height minus 1.7 m (1.3 m for 3 m); or tick 'Enter the "
                                       "whole distance'.",
    "Scans per procedure (%)": "at the top of the CT room, under 'Scans (phases) per procedure', give for each "
                               "scan the % of the procedures that have it, from 0 to 100 (the first is "
                               "normally 100 %).",
    "Shielding Design Goal (P)": "classify the area beyond the barrier (fills in P) or type P in mGy/week.",
    "Unshielded air kerma is zero": "check the workload, U, T and the air kerma values.",
    "Select Material": "choose the material(s) under 'Select Materials'.",
    "Material shares (must total 100 %)": "under 'Layers', give each material its share of the shielding; "
                                          "the shares must add up to 100 %.",
    "Distance": "type the distance from the CT isocenter to the barrier in metres (or the whole distance to the "
                "person beyond it, with 'Enter the whole distance' ticked).",
    "Procedures and DLP (body or head)": "at the top of the CT room type the weekly body and/or head "
                                         "procedures and their DLP.",
}

class departprimsec():

    def choosetype(self, e, nr, t, notify=True):
        # notify: tell the user what is missing (the Calculate button); off for batch calculations
        if self.d["vselroom "+str(t)].get() == "CT Room":
            self.depCTcal(e, nr, t)
        else:
            Ktotal = 0
            missing, fields = [], []
            distributions, components = [], []
            num = self.d[f"num_barriers_var {e}{nr}"].get()
            for i in range(num):
                K = self.calkerma(e, nr, i, t)
                # Missing inputs of every radiation type count, not only those of the last one
                prefix = f"Radiation Type #{i + 1}: " if num > 1 else ""
                missing += [prefix + item for item in self.need]
                fields += self.need_fields
                if K is not None:
                    Ktotal += K
                distributions.append(dict(self.last_distribution))
                # it goes through the barrier with the transmission data of its own workload distribution or kVp
                if self.d[f"radiob_w {e}{nr}{i}"].get() in (1, 2):
                    params, problem = self.radiation_transmission(e, nr, i)
                    if problem:
                        missing.append(prefix + problem)
                    elif K:
                        components.append({"K": K, "params": params, "pre": self.preshielding(e, nr, i)
                                           if self.d[f"radiob_w {e}{nr}{i}"].get() == 1 else {}})
            problems, layer_fields = self.layer_problems(e, nr)
            missing += problems
            fields += layer_fields
            P = self.entry_number("dikeent " + str(e) + nr)
            if P is None:
                missing.append("Shielding Design Goal (P)")
                fields.append("dikeent " + str(e) + nr)
            if self.beyond_distance(e, nr) is None:
                missing.append("Distance beyond the barrier (m)")
                fields.append(f"beyond_entry {e}{nr}")
            if not missing and Ktotal <= 0:
                missing.append("Unshielded air kerma is zero")
            self.need, self.need_fields = list(dict.fromkeys(missing)), fields
            self.B = P / Ktotal if not missing else None
            self.material_thicknesses(e, nr, components, P)
            self.record_barrier(e, nr, kind="xray", P=P, T=self.occupancy_factor(e, nr),
                                K_total=Ktotal if not missing else None, B=self.B, distributions=distributions,
                                beyond=self.beyond_distance(e, nr), whole=self.whole_distance(e, nr))
            self.show_barrier_result(e, nr, t)
        self.highlight_missing(e, nr, self.need_fields if self.calc[(nr, e)]["missing"] else [])
        if notify and self.calc[(nr, e)]["missing"]:
            barrier = self.barn[f"lab_bar {e}{nr}"].cget("text")
            highlighted = self.highlighted.get((nr, e))
            self.show_missing(f"{barrier} of '{self.room_name(t)}' cannot be calculated yet.",
                              [(None, self.calc[(nr, e)]["missing"])], focus=highlighted[0] if highlighted else None)

    def highlight_missing(self, e, nr, keys):
        # Empty or invalid entries of the barrier turn red until the user types in them
        for widget in self.highlighted.pop((nr, e), []):
            try:
                widget.configure(style="TEntry")
            except TclError:  # destroyed meanwhile
                pass
        widgets = [self.d[key] for key in dict.fromkeys(keys) if isinstance(self.d.get(key), ttk.Entry)]
        for widget in widgets:
            widget.configure(style="Missing.TEntry")
            if str(widget) not in self.highlight_bound:
                widget.bind("<Key>", lambda event, w=widget: w.configure(style="TEntry"), add="+")
                self.highlight_bound.add(str(widget))
        self.highlighted[(nr, e)] = widgets

    def show_missing(self, title, sections, focus=None):
        """Window that lists what the user must still fill in; sections = [(heading or None, [missing items])].
        focus: entry that gets the cursor when the window closes."""
        window = Toplevel(self.master)
        window.title("Missing data")
        window.transient(self.master)
        window.configure(background="#fff8d6")
        Label(window, text=title, background="#fff8d6", font=(theme.SEMIBOLD, 13), anchor="w",
              justify=LEFT).pack(fill=X, padx=14, pady=(12, 2))
        Label(window, text="Fill in the following to get the result:", background="#fff8d6",
              font=theme.BASE, anchor="w").pack(fill=X, padx=14)
        box = Frame(window, background="#fff8d6")
        box.pack(fill=BOTH, expand=1, padx=14, pady=8)
        text = Text(box, wrap=WORD, width=86, height=5, background="#fffdf0", relief=SOLID, borderwidth=1,
                    font=theme.BASE, padx=8, pady=6)
        scroll = ttk.Scrollbar(box, orient=VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.tag_configure("heading", font=theme.BOLD, spacing1=6)
        text.tag_configure("what", foreground="#c00000", font=theme.BOLD)
        for heading, items in sections:
            if heading:
                text.insert(END, heading + "\n", "heading")
            for item in items:
                prefix, _, label = item.rpartition(": ") if item.startswith("Radiation Type #") else ("", "", item)
                text.insert(END, "  • " + (prefix + ": " if prefix else ""))
                text.insert(END, label, "what")
                text.insert(END, " — " + MISSING_HELP.get(label, "") + "\n" if label in MISSING_HELP else "\n")
        text.configure(state=DISABLED)
        text.pack(side=LEFT, fill=BOTH, expand=1)
        # As tall as its wrapped text (up to 26 lines, then it scrolls)
        lines = sum(max(1, -(-len(line) // 82)) for line in text.get("1.0", "end-1c").split(NL))
        text.configure(height=min(26, max(3, lines)))
        if lines > 26:
            scroll.pack(side=RIGHT, fill=Y, before=text)

        def close(event=None):
            window.destroy()
            if focus is not None and focus.winfo_exists():
                # open the tabs (department, room, barrier) that hold the first empty field and put the cursor in it
                child, parent = focus, focus.master
                while parent is not None:
                    if isinstance(parent, ttk.Notebook):
                        parent.select(child)
                    child, parent = parent, parent.master
                focus.update_idletasks()
                focus.focus_set()

        ttk.Button(window, text="OK", command=close).pack(pady=(0, 12))
        window.bind("<Return>", close)
        window.bind("<Escape>", close)
        window.protocol("WM_DELETE_WINDOW", close)
        window.update_idletasks()  # centre it on the program window
        x = self.master.winfo_rootx() + (self.master.winfo_width() - window.winfo_reqwidth()) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - window.winfo_reqheight()) // 3
        window.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        window.grab_set()
        window.focus_set()
        return window

    def calculate_all(self, t):
        # Calculate every barrier of the room and list, per barrier, what is still missing
        nr = self.d[f"nr {t}"]
        sections, done = [], []
        for e in range(1, self.d[f"x {t}"] + 1):
            self.choosetype(e, nr, t, notify=False)
            barrier = self.barn[f"lab_bar {e}{nr}"].cget("text")
            if self.calc[(nr, e)]["missing"]:
                sections.append((barrier, self.calc[(nr, e)]["missing"]))
            else:
                done.append(barrier)
        if sections:
            window = self.show_missing(f"'{self.room_name(t)}': calculated {len(done)} of {self.d[f'x {t}']} "
                                       "barriers.", sections)
            return window
        messagebox.showinfo("Calculate all", f"All {len(done)} barriers of '{self.room_name(t)}' are calculated.",
                            parent=self.master)

    def record_barrier(self, e, nr, **result):
        # Keep the inputs and results of this calculation for the exported report
        def value(key):
            try:
                return self.d[key].get()
            except (KeyError, AttributeError, TclError):
                return None
        thickness = []
        for o in range(1, self.d[f"vnumbmat {e}{nr}"].get() + 1):
            material = self.d[f"vmater {e}{o}{nr}"].get()
            if material != "Select Material":
                x = self.thm.get(f"xbar {e}{o}{nr}")
                thickness.append((material, x if isinstance(x, float) else None))
        area = value(f"area {e}{nr}")
        location = None
        if value(f"vraoccup {e}{nr}") == 1:
            location = "Written"
        elif value(f"vraoccup {e}{nr}") == 2:
            location = value(f"vselocation {e}{nr}")
        layers = None
        if self.is_layered(e, nr):  # [(material, share %)] from the inside out
            layers = [(self.d[f"vmater {e}{o}{nr}"].get(), self.entry_number(f"share {e}{o}{nr}"))
                      for o in range(1, self.d[f"vnumbmat {e}{nr}"].get() + 1)]
        result.update(area=area if area != "Classify the area" else None, location=location,
                      thickness=thickness, missing=list(self.need), layers=layers,
                      shield=getattr(self, "last_shield", None))
        self.calc[(nr, e)] = result

    def describe_distribution(self, e, nr, i):
        def value(key):
            try:
                return self.d[key].get()
            except (KeyError, AttributeError, TclError):
                return None
        radiation = {1: "Primary", 2: "Secondary"}.get(value(f"radiob_w {e}{nr}{i}"), "")
        distribution = value(f"vsexroom {e}{nr}{i}")
        if distribution in (None, "", "Select X-ray room"):
            distribution = ""
        elif value(f"vselxray {e}{nr}{i}") == 2:
            data = self.kvp_data(e, nr, i)
            distribution = f"{distribution} kVp" + (f" ({data})" if data != "NCRP 147" else "")
        source = ""
        origin = SOURCES.get(distribution, "NCRP 147")  # where the suggested values come from
        if radiation == "Primary":
            suggested = PRIMARY_KERMA.get(distribution) == value(f"entk {e}{nr}{i}")
            source = f"Primary ({origin})" if suggested else "Primary (entered)"
        elif value(f"unairkerv {e}{nr}{i}") == 2:
            source = "Secondary (entered)"
        elif value(f"unairkerv {e}{nr}{i}") == 1 and distribution == DBT:
            mode = {1: "2D", 2: "3D", 3: "2D + 3D"}.get(value(f"dbtmode {e}{nr}{i}"), "")
            source = f"DBT {mode} ({origin})" if mode else ""
        elif value(f"unairkerv {e}{nr}{i}") == 1:
            if value(f"airkerv {e}{nr}{i}") == 1:
                source = {1: "Leakage + side-scatter", 2: "Leakage + forward/backscatter",
                          0: "Leakage only"}.get(value(f"radiob_leak {e}{nr}{i}"), "")
            else:
                source = {2: "Side-scatter", 3: "Forward/backscatter"}.get(value(f"airkerv {e}{nr}{i}"), "")
            source = f"{source} ({origin})" if source else ""
        preshielding = ""
        if radiation == "Primary" and value(f"preshvar {e}{nr}{i}") == 1:
            preshielding = {1: "Bucky", 2: "Cross-table"}.get(value(f"radiob_pre {e}{nr}{i}"), "")
        return {"no": i + 1, "radiation": radiation, "distribution": distribution, "k1_source": source,
                "preshielding": preshielding}

    def occupancy_factor(self, e, nr):
        # T written by the user, or taken from NCRP 147 Table 4.1 for the selected location; None if missing
        if self.d[f"vraoccup {e}{nr}"].get() == 1:
            return self.entry_number(f"occupentry {e}{nr}")
        if self.d[f"vraoccup {e}{nr}"].get() == 2:
            for location, factor in wb['Occupancy Factor ( T )'].iter_rows(min_row=2, max_col=2, values_only=True):
                if location is not None and location == self.d[f"vselocation {e}{nr}"].get():
                    return float(factor)
        return None

    def transmission_params(self, sheet, distribution, data="NCRP 147"):
        # (alpha, beta, gamma) per material for a workload distribution or kVp, or None if it is not in the table
        if distribution == DBT:  # Yang et al. 2017, table 8: scatter from a Hologic DBT room (sheet 'DBT abc')
            names = {"Gypsum": "Gypsum Wallboard", "Glass": "Plate Glass"}
            return {names.get(row[0], row[0]): tuple(float(v) for v in row[1:4])
                    for row in wb["DBT abc"].iter_rows(min_row=2, values_only=True) if row[0]}
        if distribution in TRANSMISSION_SHEETS:  # Kirby 2023, Biondi 2024: their own sheets, laid out as 'prim abc'
            sheet = TRANSMISSION_SHEETS[distribution][0 if sheet == "prim abc" else 1]
            if sheet is None:  # Biondi 2024: no primary
                return None
        if data in KVP_DATA[1:]:  # Li et al. 2024 (sheet 'prim abc DR 600'): one block of rows per filtration
            blocks = []
            for row in wb["prim abc DR 600"].iter_rows(values_only=True):
                if isinstance(row[0], str) and "filtration" in row[0].lower():
                    blocks.append([])
                elif isinstance(row[0], (int, float)) and blocks:
                    blocks[-1].append(row)
            for row in blocks[KVP_DATA.index(data) - 1]:
                if row[0] == distribution:  # lead, concrete, gypsum wallboard, steel
                    return {material: tuple(float(row[col + k]) for k in range(3))
                            for material, col in MATERIAL_COLUMNS.items() if col + 2 < len(row) and row[col] is not None}
            return None
        for row in wb[sheet].iter_rows(min_row=3, values_only=True):
            if row[0] is not None and row[0] == distribution:
                return {material: tuple(float(row[col + k] or 0) for k in range(3))
                        for material, col in MATERIAL_COLUMNS.items()}
        return None

    def preshielding(self, e, nr, i):
        # NCRP 147 equivalent thickness of primary-beam preshielding (mm), subtracted from the result
        if self.d[f"preshvar {e}{nr}{i}"].get() != 1:
            return {}
        row = {1: 3, 2: 4}.get(self.d[f"radiob_pre {e}{nr}{i}"].get())
        if row is None:
            return {}
        ws = wb["Equiv. thickness of prim pres"]
        return {"Lead": float(ws[f'B{row}'].value), "Concrete": float(ws[f'C{row}'].value),
                "Steel": float(ws[f'D{row}'].value)}

    def entry_number(self, key):
        """Number typed in an entry (comma or dot), or None if it is empty, invalid or missing."""
        try:
            widget = self.d[key]
            # A variable's own text: IntVar.get() would cut 550.5 down to 550
            text = widget._tk.globalgetvar(widget._name) if isinstance(widget, Variable) else widget.get()
            return float(str(text).strip().replace(",", "."))
        except (KeyError, AttributeError, ValueError, TclError):
            return None

    def calkerma(self, e, nr, i, t):
        # Air kerma K = N·U·T·K1/d² of one radiation type; self.need lists what is missing,
        # self.need_fields the entries to highlight
        need, fields = [], []
        radiation = self.d[f"radiob_w {e}{nr}{i}"].get()
        barrier = self.barn[f"lab_bar {e}{nr}"].cget("text")
        # ======== Distance: from the source to the barrier, plus beyond it to the occupied point ===========
        D = self.entry_number(f"entryd {e}{nr}{i}")
        beyond = self.beyond_distance(e, nr)  # if missing, it is reported once for the barrier (choosetype)
        # ======== Workload: patients per week N ===========
        distribution_var = self.d.get(f"vsexroom {e}{nr}{i}")  # workload distribution or kVp
        distribution = distribution_var.get() if distribution_var is not None else None
        kvp = self.d[f"vselxray {e}{nr}{i}"].get() == 2 if f"vselxray {e}{nr}{i}" in self.d else False
        if f"oworkvar {e}{nr}{i}" in self.d and self.d[f"oworkvar {e}{nr}{i}"].get() == 1:
            mode_key, suffix = f"workv {e}{nr}{i}", f"{e}{nr}{i}"  # this radiation type has its own workload
        else:
            mode_key, suffix = f"vrawork {t}", f"{t}"  # the workload of the room
        mode = self.d[mode_key].get() if mode_key in self.d else 0
        n = None
        if mode == 2:
            n = self.entry_number(f"numpapwe {suffix}")
            if n is None:
                need.append("Workload")
                fields.append(f"numpapwe {suffix}")
        elif mode == 1:
            total = self.entry_number(f"worentry {suffix}")
            w_norm = 2.5 if kvp else WORKLOAD_NORM.get(distribution)
            if total is None:
                need.append("Workload")
                fields.append(f"worentry {suffix}")
            elif w_norm is None and distribution == DBT:
                need.append("Patients per week (DBT)")
            elif w_norm is None:
                need.append("Workload Distribution (X-ray room or kVp)")
            else:
                n = total / w_norm
        else:
            need.append("Workload")
        # ======== Occupancy Factor T ===========
        T = self.occupancy_factor(e, nr)
        if T is None:
            need.append("Occupancy Factor (T)")
            fields.append(f"occupentry {e}{nr}")
        # ======== Use factor U and K1 "air kerma" ===========
        Us = K1 = None
        if radiation == 1:  # primary
            if distribution in BIONDI:
                need.append("Secondary radiation only")
            Us = self.entry_number(f"use_ent {e}{nr}{i}")
            if Us is None:
                need.append("Use Factor (U)")
                fields.append(f"use_ent {e}{nr}{i}")
            K1 = self.entry_number(f"entk {e}{nr}{i}")
            if K1 is None:
                need.append("Unshielded Air Kerma")
                fields.append(f"entk {e}{nr}{i}")
        elif radiation == 2:  # secondary
            Us = 1
            source = self.d[f"unairkerv {e}{nr}{i}"].get() if f"unairkerv {e}{nr}{i}" in self.d else 0
            if source == 1 and distribution == DBT:  # Yang et al. 2017: per view, in the chosen mode
                mode = self.d[f"dbtmode {e}{nr}{i}"].get() if f"dbtmode {e}{nr}{i}" in self.d else 0
                if mode in DBT_MODES:
                    K1 = dbt_kerma(mode)
                else:
                    need.append("Unshielded Air Kerma")
            elif source == 1:  # NCRP 147 values for the workload distribution
                kind = self.d[f"airkerv {e}{nr}{i}"].get() if f"airkerv {e}{nr}{i}" in self.d else 0
                if kind == 1:
                    column = {1: 6, 2: 8}.get(self.d[f"radiob_leak {e}{nr}{i}"].get(), 4)
                else:
                    column = {2: 5, 3: 7}.get(kind)
                row = UNSHIELDED_SECONDARY.get(distribution)
                if column is not None and row is not None:
                    K1 = float(row[column])
                else:
                    need.append("Unshielded Air Kerma")
            elif source == 2:  # written by the user
                K1 = self.entry_number(f"entk {e}{nr}{i}")
                if K1 is None:
                    need.append("Unshielded Air Kerma")
                    fields.append(f"entk {e}{nr}{i}")
            else:
                need.append("Unshielded Air Kerma")
        else:
            need.append("Radiation type (Primary / Secondary)")
        if D is None:
            need.append("Distance from the Source to the Barrier (m)")
            fields.append(f"entryd {e}{nr}{i}")
        d = D + beyond if D is not None and beyond is not None else None  # source to the occupied point
        self.need, self.need_fields = need, fields
        # ========== Calculate Kerma (None if there are missing variables) ==========
        K = n * Us * T * K1 / (d ** 2) if None not in (n, Us, T, K1, d) and d > 0 else None
        self.last_distribution = dict(self.describe_distribution(e, nr, i), N=n, U=Us, T=T, K1=K1, d=d, K=K,
                                      D=D, symbol=self.distance_symbol(e, nr, i))
        return K

    def kvp_data(self, e, nr, i):
        """The transmission data chosen for a primary beam given by its kVp (NCRP 147 otherwise)."""
        var = self.d.get(f"kvpdata {e}{nr}{i}")
        if var is None or self.d[f"vselxray {e}{nr}{i}"].get() != 2:
            return "NCRP 147"
        return var.get() if var.get() in KVP_DATA else "NCRP 147"

    def whole_distance(self, e, nr):
        """True when the distances of barrier e are typed all the way to the person beyond it (nothing added)."""
        whole = self.d.get(f"whole {e}{nr}")
        return whole is not None and whole.get() == 1

    def beyond_distance(self, e, nr):
        """Distance (m) from the barrier to the occupied point beyond it, added to the distance from the source: 0 when
        the whole distance is typed. None if it is not a number >= 0."""
        if self.whole_distance(e, nr):
            return 0.0
        value = self.entry_number(f"beyond {e}{nr}")
        return value if value is not None and value >= 0 else None

    def ct_scans(self, t, kind):
        """Mean number of scans (phases) per body or head procedure: the sum of the % of the procedures that have
        each scan, / 100. NCRP 147: 100 % + 40 % repeated with contrast = 1.4. None if a % is not 0 to 100."""
        count = self.d.get(f"phases_{kind} {t}")
        try:
            count = int(count.get())
        except (AttributeError, TclError, ValueError):
            return None
        total = 0.0
        for k in range(1, count + 1):
            value = self.entry_number(f"phase_{kind} {t}#{k}")
            if value is None or not 0 <= value <= 100:
                return None
            total += value / 100
        return total

    def radiation_transmission(self, e, nr, i):
        """Transmission data (alpha, beta, gamma per material) of radiation type i: those of its workload distribution
        or kVp, primary or secondary. Returns (data, None), or (None, what is missing)."""
        primary = self.d[f"radiob_w {e}{nr}{i}"].get() == 1
        variable = self.d.get(f"vsexroom {e}{nr}{i}")
        try:
            distribution = variable.get() if variable is not None else None
        except TclError:  # a kVp that is not a number
            distribution = None
        if distribution in (None, "", "Select X-ray room"):
            return None, "Workload Distribution (X-ray room or kVp)"
        data = self.kvp_data(e, nr, i) if primary else "NCRP 147"
        params = self.transmission_params("prim abc" if primary else "sec abc", distribution, data)
        if params is None and data != "NCRP 147":
            return None, "kVp for the DR 600 data (60-120 kV, every 10 kV)"
        if params is None and primary and distribution in BIONDI:
            return None, "Secondary radiation only"
        if params is None:
            return None, "Workload Distribution (X-ray room or kVp)"
        return params, None

    def depCTcal(self, e, nr, t):
        def number(key):
            return self.entry_number(key) or 0.0
        # NCRP 147 CT method: K1sec per scan = kappa * DLP (x1.2 for body); each procedure has on average 'scans'
        # scans (NCRP 147: 1.4, repeats with contrast); K = T * sum(N * scans * K1sec) / d^2
        d = D = number(f"dist_var {e}{nr}")  # isocenter to the barrier
        beyond = self.beyond_distance(e, nr)  # barrier to the occupied point
        P = number(f"dikeent {e}{nr}")
        T = self.occupancy_factor(e, nr)
        scans = {kind: self.ct_scans(t, kind) for kind in ("body", "head")}
        k1sec_body = 1.2 * 3e-4 * number(f"dlpb_var {t}")
        k1sec_head = 9e-5 * number(f"dlph_var {t}")
        workload = (number(f"bp_var {t}") * (scans["body"] or 0) * k1sec_body
                    + number(f"hp_var {t}") * (scans["head"] or 0) * k1sec_head)
        self.need, self.need_fields = [], []
        if d <= 0:
            self.need.append("Distance")
            self.need_fields.append(f"dist_entry {e}{nr}")
        if beyond is None:
            self.need.append("Distance beyond the barrier (m)")
            self.need_fields.append(f"beyond_entry {e}{nr}")
        for kind, procedures in (("body", "bp_var"), ("head", "hp_var")):
            if scans[kind] is None and number(f"{procedures} {t}") > 0:
                self.need.append("Scans per procedure (%)")
                self.need_fields += [f"phase_{kind}_entry {t}#{k}" for k in range(1, 9)]
        if P <= 0:
            self.need.append("Shielding Design Goal (P)")
            self.need_fields.append(f"dikeent {e}{nr}")
        if workload <= 0:
            self.need.append("Procedures and DLP (body or head)")
            self.need_fields += [f"{name}_entry {t}" for name in ("bp", "hp", "dlpb", "dlph")
                                 if number(f"{name}_var {t}") <= 0]
        if T is None:
            self.need.append("Occupancy Factor (T)")
            self.need_fields.append(f"occupentry {e}{nr}")
        problems, fields = self.layer_problems(e, nr)
        self.need += problems
        self.need_fields += fields
        K = B = None
        self.need = list(dict.fromkeys(self.need))
        if not self.need:
            d += beyond  # isocenter to the occupied point
            K = T * workload / d ** 2
            self.d["K " + self.barn[f"lab_bar {e}{nr}"].cget("text") + nr] = K
            B = P / K
        kvp_120 = number(f"kvp_var {t}") == 120
        ct_params = {"Lead": (2.246, 5.73, 0.547) if kvp_120 else (2.009, 3.99, 0.342),
                     "Concrete": (0.0383, 0.0142, 0.658) if kvp_120 else (0.0336, 0.0122, 0.519)}
        self.material_thicknesses(e, nr, [{"K": K, "params": ct_params, "pre": {}}] if K else [], P)
        self.record_barrier(e, nr, kind="ct", P=P or None, T=T, K_total=K, B=B, d=d if K else None,
                            kvp=int(number(f"kvp_var {t}")) or None, beyond=beyond, scans=scans,
                            whole=self.whole_distance(e, nr), D=D if K else None)
        self.show_barrier_result(e, nr, t)

    # ===================== material thicknesses: each alone, or layers =====================
    def is_layered(self, e, nr):
        mode = self.d.get(f"matmode {e}{nr}")
        return mode is not None and mode.get() == "combined"

    def layer_problems(self, e, nr):
        """What stops the layers of a barrier from being calculated, and the entries to highlight."""
        if not self.is_layered(e, nr):
            return [], []
        count = self.d[f"vnumbmat {e}{nr}"].get()
        problems, fields = [], []
        if any(self.d[f"vmater {e}{o}{nr}"].get() == "Select Material" for o in range(1, count + 1)):
            problems.append("Select Material")
        shares = [self.entry_number(f"share {e}{o}{nr}") for o in range(1, count + 1)]
        if None in shares or min(shares) < 0 or abs(sum(shares) - 100) >= 0.5:
            problems.append("Material shares (must total 100 %)")
            fields += [f"share_entry {e}{o}{nr}" for o in range(1, count + 1)]
        return problems, fields

    def material_thicknesses(self, e, nr, components, P):
        """Thickness of every material of the barrier (self.thm), or the list of what is missing.
        components: the radiation types, each with its air kerma K, its transmission data and its preshielding; each
        goes through the barrier on its own (NCRP 147 Sections 5.3.5, 5.4.2), so the thickness gives
        sum of K B(x + preshielding) = P.
        Each alone: the thickness of each material if it were the only one.
        Layers: from the room side outwards, each material takes its share of the attenuation; a layer starts at the
        equivalent thickness of what is already in front of it (NCRP 147 treats preshielding the same way), so the
        hardening of the beam and the order of the layers count."""
        count = self.d[f"vnumbmat {e}{nr}"].get()
        materials = [self.d[f"vmater {e}{o}{nr}"].get() for o in range(1, count + 1)]
        usable = lambda material: all(has_data(c["params"], material) for c in components)
        self.last_shield = None  # transmission data of this barrier, for the dose check and the views
        if not self.need and not components:
            self.need.append("Unshielded air kerma is zero")
        if not self.need:
            for c in components:
                c["start"] = preshielding_transmission(c["params"], c["pre"])
            main = max(components, key=lambda c: c["K"])  # the views show the other rooms' rays through it
            self.last_shield = {"components": components, "params": {m: main["params"][m] for m in set(materials)
                                                                      if usable(m)}}
        if self.need:
            if "Select Material" in materials:
                self.need.append("Select Material")
            self.need = list(dict.fromkeys(self.need))
            thicknesses = ["\n".join(self.need)] * count
        elif self.is_layered(e, nr):
            no_data = [m for m in materials if not usable(m)]
            if no_data:
                thicknesses = [f"No transmission data for {no_data[0]}"] * count
            else:
                shares = [self.entry_number(f"share {e}{o}{nr}") for o in range(1, count + 1)]
                fractions = [share / sum(shares) for share in shares]
                thicknesses = thickness_layers(components, materials, fractions, P)
        else:
            thicknesses = []
            for material in materials:
                if material == "Select Material":
                    thicknesses.append("Select Material")
                elif usable(material):  # 0: no additional shielding is needed
                    thicknesses.append(thickness_alone(components, material, P))
                else:
                    thicknesses.append(f"No transmission data for {material}")
        for o, value in enumerate(thicknesses, start=1):
            self.thm[f"xbar {e}{o}{nr}"] = value

    def planned_thicknesses(self, e, nr):
        """[(material, planned thickness in mm or None)] in the order of the materials; all None unless
        'Check the dose beyond the barrier with a planned thickness' is ticked."""
        checking = self.d.get(f"checkplan {e}{nr}") is not None and self.d[f"checkplan {e}{nr}"].get() == 1
        return [(self.d[f"vmater {e}{o}{nr}"].get(), self.entry_number(f"planned {e}{o}{nr}") if checking else None)
                for o in range(1, self.d[f"vnumbmat {e}{nr}"].get() + 1)]

    def planned_layers(self, nr, e):
        """The planned barrier: every material with a planned thickness, all installed together, from the inside out
        [(material, mm)]. Empty unless 'Check the dose beyond the barrier with a planned thickness' is ticked."""
        rec = self.calc.get((nr, e)) or {}
        params = (rec.get("shield") or {}).get("params", {})
        return [(m, x) for m, x in self.planned_thicknesses(e, nr) if x is not None and m in params]

    def dose_check(self, nr, e):
        """Weekly air kerma beyond the barrier (x T, like P) with the planned thicknesses (every material given,
        one after the other, as all of them cut the radiation), or with the required thickness when none is
        planned, and whether it meets the shielding design goal P. None if not calculated."""
        rec = self.calc.get((nr, e))
        if not rec or rec["missing"] or not rec.get("K_total") or not rec.get("P") or not rec.get("shield"):
            return None
        K, P, shield = rec["K_total"], rec["P"], rec["shield"]
        planned = self.planned_layers(nr, e)
        if planned:
            first = planned[0][0]
            # each radiation type through its preshielding, as in the calculation of the required thickness, then
            # through every planned layer
            start = (lambda c: c["start"]) if rec.get("layers") else \
                (lambda c: archer_transmission(c["params"][first], c["pre"].get(first, 0.0)))
            transmission = sum(c["K"] * through(c["params"], planned, start(c)) for c in shield["components"]) / K
            basis = "planned " + " + ".join(f"{m} {x:g} mm" for m, x in planned)
        else:
            transmission, basis = min(1.0, P / K), "required thickness"
        dose = K * transmission
        return {"K": K, "P": P, "dose": dose, "ok": dose <= P * 1.0001, "basis": basis,
                "transmission": transmission}

    def show_barrier_result(self, e, nr, t):
        """One row per barrier in the results tab, in barrier order: the thickness of each material,
        or one red line with what is still missing."""
        key = f"resultrow {e}{nr}"
        if self.res.get(key) is not None:
            self.res[key].destroy()
        row = ttk.Frame(self.d[f"resultframe {t}{nr}"])
        row.grid(row=e, column=0, sticky="we", padx=6, pady=4)
        self.res[key] = row
        ttk.Label(row, text=self.barn[f"lab_bar {e}{nr}"].cget("text"), style="BL2.TLabel", width=10).grid(
            row=0, column=0, sticky="nw")
        if self.need:
            ttk.Label(row, text="Missing: " + "; ".join(self.need), style="RL.TLabel", wraplength=theme.px(420),
                      justify=LEFT).grid(row=0, column=1, columnspan=2, sticky="w")
            return
        count = self.d[f"vnumbmat {e}{nr}"].get()
        layered = self.is_layered(e, nr) and count > 1
        if not layered:  # two materials per line, in aligned columns that still fit the longest text
            row.columnconfigure(1, minsize=theme.px(210))
        for k, o in enumerate(range(1, count + 1)):
            material, x = self.d[f"vmater {e}{o}{nr}"].get(), self.thm.get(f"xbar {e}{o}{nr}")
            if not isinstance(x, float):  # e.g. "Select Material"
                text, style = (x if material == "Select Material" else f"{material}: {x}"), "RL.TLabel"
            elif x > 0:
                text, style = f"{material}: {x:.2f} mm", "AL.TLabel"
            else:
                text, style = f"{material}: none needed", "OK.TLabel"
            if layered:  # one layer per line, from the inside out
                place = "inside" if o == 1 else "outside" if o == count else "middle"
                ttk.Label(row, text=f"{place}:", style="Muted.TLabel", width=8).grid(row=k, column=1, sticky="w")
                ttk.Label(row, text=text, style=style).grid(row=k, column=2, sticky="w")
            else:
                ttk.Label(row, text=text, style=style).grid(row=k // 2, column=1 + k % 2, sticky="w", padx=(0, 6))
        if layered:
            ttk.Label(row, text="Layers of one barrier", style="Muted.TLabel").grid(row=count, column=1, columnspan=2,
                                                                                    sticky="w")
        check = self.dose_check(nr, e)
        if check and check["basis"].startswith("planned"):  # with the planned thickness: is the goal met?
            text = (f"{check['basis'][0].upper() + check['basis'][1:]} → {check['dose']:.3g} mGy/wk beyond, "
                    f"P {check['P']:g}  " + ("✓ met" if check["ok"] else "✗ exceeded"))
            ttk.Label(row, text=text, style="OK.TLabel" if check["ok"] else "RL.TLabel",
                      wraplength=theme.px(380), justify=LEFT).grid(row=count + 1, column=1, columnspan=2, sticky="w")
