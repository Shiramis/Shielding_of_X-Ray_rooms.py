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


# NCRP 147 total workload per patient Wnorm (mA·min/patient) of each workload distribution
WORKLOAD_NORM = {row[0]: row[1] for row in wb['Workload'].iter_rows(max_col=2, values_only=True)
                 if row[0] and isinstance(row[1], (int, float))}
# NCRP 147 unshielded secondary air kerma per patient at 1 m: the whole row of each workload distribution
UNSHIELDED_SECONDARY = {row[0]: row for row in wb['Uns Air Kerma'].iter_rows(min_row=2, values_only=True) if row[0]}

# What to do for each missing input, shown in the "Missing data" window
NL = chr(10)

MISSING_HELP = {
    "Radiation type (Primary / Secondary)": "at 'Select Radiation Type' choose Primary or Secondary.",
    "Workload": "at the top of the room choose 'Write total Workload' or 'The Number of Patients per week' "
                "and type the value (or tick 'Different Workload' on this radiation type).",
    "Workload Distribution (X-ray room or kVp)": "at 'Workload Distribution' choose 'X-Ray Room (Suggested "
                                                 "NCRP 147)' and select the room, or 'Give kVp'.",
    "Use Factor (U)": "type U in the 'Use Factor' box (NCRP 147: floor 0.89, cross-table wall 0.09, "
                      "chest bucky wall 1).",
    "Unshielded Air Kerma": "primary: type K in 'Primary Unshielded Air Kerma'. Secondary: choose 'Select "
                            "Unshielded Secondary Air Kerma (NCRP 147)' and the type of scatter (needs an X-ray "
                            "room, not a kVp), or choose 'Write' and type the value.",
    "Occupancy Factor (T)": "under 'Shielding Area' choose 'Write occupancy factor (T)' and type it, "
                            "or 'select Location' and pick what is beyond the barrier.",
    "Distance from the Source to the Barrier (m)": "type the distance from the X-ray source to the barrier "
                                                   "in metres.",
    "Shielding Design Goal (P)": "classify the area beyond the barrier (fills in P) or type P in mGy/week.",
    "Set for the calculation": "tick 'Set for the calculation' on the radiation type whose transmission "
                               "should be used.",
    "Unshielded air kerma is zero": "check the workload, U, T and the air kerma values.",
    "Select Material": "choose the material(s) under 'Select Materials'.",
    "Material shares (must total 100 %)": "under 'Layers', give each material its share of the shielding; "
                                          "the shares must add up to 100 %.",
    "Distance": "type the distance from the CT isocenter to the barrier in metres.",
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
            ci = None
            missing, fields = [], []
            distributions = []
            num = self.d[f"num_barriers_var {e}{nr}"].get()
            for i in range(num):
                K = self.calkerma(e, nr, i, t)
                # Missing inputs of every radiation type count, not only those of the last one
                prefix = f"Radiation Type #{i + 1}: " if num > 1 else ""
                missing += [prefix + item for item in self.need]
                fields += self.need_fields
                if K is not None:
                    Ktotal += K
                is_set = self.d[f"setv {e}{nr}{i}"].get() == 1
                if is_set:
                    ci = i
                distributions.append(dict(self.last_distribution, set=is_set))
            problems, layer_fields = self.layer_problems(e, nr)
            missing += problems
            fields += layer_fields
            P = self.entry_number("dikeent " + str(e) + nr)
            if P is None:
                missing.append("Shielding Design Goal (P)")
                fields.append("dikeent " + str(e) + nr)
            if ci is None:
                missing.append("Set for the calculation")
            else:
                # its transmission curve needs the workload distribution (X-ray room) or the kVp
                distribution = self.d.get(f"vsexroom {e}{nr}{ci}")
                if distribution is None or distribution.get() in ("", "Select X-ray room"):
                    prefix = f"Radiation Type #{ci + 1}: " if num > 1 else ""
                    missing.append(prefix + "Workload Distribution (X-ray room or kVp)")
            if not missing and Ktotal <= 0:
                missing.append("Unshielded air kerma is zero")
            self.need, self.need_fields = list(dict.fromkeys(missing)), fields
            self.B = P / Ktotal if not missing else None
            self.depcalc(e, nr, ci if ci is not None else 0, t)
            self.record_barrier(e, nr, kind="xray", P=P, T=self.occupancy_factor(e, nr),
                                K_total=Ktotal if not missing else None, B=self.B, distributions=distributions)
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
            distribution = f"{distribution} kVp"
        source = ""
        if radiation == "Primary":
            ncrp = PRIMARY_KERMA.get(distribution) == value(f"entk {e}{nr}{i}")
            source = "Primary (NCRP 147)" if ncrp else "Primary (entered)"
        elif value(f"unairkerv {e}{nr}{i}") == 2:
            source = "Secondary (entered)"
        elif value(f"unairkerv {e}{nr}{i}") == 1:
            if value(f"airkerv {e}{nr}{i}") == 1:
                source = {1: "Leakage + side-scatter", 2: "Leakage + forward/backscatter",
                          0: "Leakage only"}.get(value(f"radiob_leak {e}{nr}{i}"), "")
            else:
                source = {2: "Side-scatter", 3: "Forward/backscatter"}.get(value(f"airkerv {e}{nr}{i}"), "")
            source = f"{source} (NCRP 147)" if source else ""
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

    def transmission_params(self, sheet, distribution):
        # (alpha, beta, gamma) per material for a workload distribution or kVp, or None if it is not in the table
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
        # ======== Distance, plus the NCRP 147 distance to the occupied point ===========
        D = self.entry_number(f"entryd {e}{nr}{i}")
        if D is not None:
            D += {"Floor": 1.7, "Ceiling": 0.5}.get(barrier, 0.3)  # from fig. 4.4 NCRP 147
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
            if source == 1:  # NCRP 147 values for the workload distribution
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
        self.need, self.need_fields = need, fields
        # ========== Calculate Kerma (None if there are missing variables) ==========
        K = n * Us * T * K1 / (D ** 2) if None not in (n, Us, T, K1, D) else None
        self.last_distribution = dict(self.describe_distribution(e, nr, i), N=n, U=Us, T=T, K1=K1, d=D, K=K)
        return K

    def depcalc(self, e, nr, i, t):  # Barrier calculations
        params, preshielding = None, {}
        if not self.need:
            # NCRP 147 transmission parameters (alpha, beta, gamma) of the distribution set for the calculation
            primary = self.d[f"radiob_w {e}{nr}{i}"].get() == 1
            distribution = self.d.get(f"vsexroom {e}{nr}{i}")
            params = self.transmission_params('prim abc' if primary else 'sec abc',
                                              distribution.get() if distribution is not None else None)
            if params is None:
                self.need.append("Workload Distribution (X-ray room or kVp)")
            elif primary:
                preshielding = self.preshielding(e, nr, i)

        self.material_thicknesses(e, nr, params, self.B, preshielding)

    def depCTcal(self, e, nr, t):
        def number(key):
            return self.entry_number(key) or 0.0
        # NCRP 147 CT method: K1sec = kappa * DLP (x1.2 for body, x1.4 for contrast), K = T * sum(N * K1sec) / d^2
        d = number(f"dist_var {e}{nr}")
        P = number(f"dikeent {e}{nr}")
        T = self.occupancy_factor(e, nr)
        k1sec_body = 1.2 * 3e-4 * 1.4 * number(f"dlpb_var {t}")
        k1sec_head = 9e-5 * 1.4 * number(f"dlph_var {t}")
        workload = number(f"bp_var {t}") * k1sec_body + number(f"hp_var {t}") * k1sec_head
        self.need, self.need_fields = [], []
        if d <= 0:
            self.need.append("Distance")
            self.need_fields.append(f"dist_entry {e}{nr}")
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
        if not self.need:
            K = T * workload / d ** 2
            self.d["K " + self.barn[f"lab_bar {e}{nr}"].cget("text") + nr] = K
            B = P / K
        kvp_120 = number(f"kvp_var {t}") == 120
        ct_params = {"Lead": (2.246, 5.73, 0.547) if kvp_120 else (2.009, 3.99, 0.342),
                     "Concrete": (0.0383, 0.0142, 0.658) if kvp_120 else (0.0336, 0.0122, 0.519)}
        self.material_thicknesses(e, nr, ct_params, B)
        self.record_barrier(e, nr, kind="ct", P=P or None, T=T, K_total=K, B=B, d=d or None,
                            kvp=int(number(f"kvp_var {t}")) or None)
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

    def material_thicknesses(self, e, nr, params, B, preshielding=None):
        """Thickness of every material of the barrier (self.thm), or the list of what is missing.
        Each alone: the thickness that by itself gives the transmission B.
        Layers: from the room side outwards, each material takes its share of the attenuation ln(1/B); a layer
        starts at the equivalent thickness of what is already in front of it (NCRP 147 treats preshielding the
        same way), so the hardening of the beam and the order of the layers count."""
        preshielding = preshielding or {}
        count = self.d[f"vnumbmat {e}{nr}"].get()
        materials = [self.d[f"vmater {e}{o}{nr}"].get() for o in range(1, count + 1)]
        has_data = lambda material: material in params and params[material][0] and params[material][2]
        self.last_shield = None  # transmission data of this barrier, for the dose check
        if not self.need:
            start = 1.0  # transmission of the preshielding, the innermost layer
            for material in ("Lead", "Concrete", "Steel"):
                if preshielding.get(material) and has_data(material):
                    start = archer_transmission(params[material], preshielding[material])
                    break
            self.last_shield = {"params": {m: params[m] for m in set(materials) if has_data(m)},
                                "pre": dict(preshielding), "start": start}
        if self.need:
            if "Select Material" in materials:
                self.need.append("Select Material")
            self.need = list(dict.fromkeys(self.need))
            thicknesses = ["\n".join(self.need)] * count
        elif self.is_layered(e, nr):
            no_data = [m for m in materials if not has_data(m)]
            if no_data:
                thicknesses = [f"No NCRP 147 data for {no_data[0]}"] * count
            else:
                start = self.last_shield["start"]
                shares = [self.entry_number(f"share {e}{o}{nr}") for o in range(1, count + 1)]
                fractions = [share / sum(shares) for share in shares]
                thicknesses = layered_thicknesses([params[m] for m in materials], fractions, B, start)
        else:
            thicknesses = []
            for material in materials:
                if material == "Select Material":
                    thicknesses.append("Select Material")
                elif has_data(material):
                    # 0: no additional shielding is needed
                    thicknesses.append(max(archer_thickness(params[material], B) - preshielding.get(material, 0), 0.0))
                else:
                    thicknesses.append(f"No NCRP 147 data for {material}")
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
        params = shield["params"]
        planned = self.planned_layers(nr, e)
        if planned:
            first = planned[0][0]
            # in front of the first layer: the preshielding, as in the calculation of the required thickness
            start = archer_thickness(params[first], shield["start"]) if rec.get("layers") else \
                shield["pre"].get(first, 0)
            transmission = stack_transmission(params, planned, start)
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
