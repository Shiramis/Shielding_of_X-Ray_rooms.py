import tkinter
import subprocess
from tkinter import *
from tkinter import ttk
import theme
from tooltips import tip
from Depcalculations import (wb, PRIMARY_KERMA, KVP_DATA, DBT, SOURCES, KIRBY, BIONDI, LI_ORTHOPEDIC, YANG2016_KERMA,
                             DBT_LI2013, JUDGE_FFDM, JUDGE_UNITS, CHEN, KERMA_SOURCES, MAMMO_KVP_DATA, MAMMO_KVPS,
                             EXISTING_MAX, UNSHIELDED_SECONDARY, OCCUPANCY_T, HEIGHTS, ANGLES, SPECTRA)
from barrier_names import BarrierDialog, KEEP, default_kind, default_name, door_material

MATERIALS = ("Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass", "Wood")
CT_MATERIALS = ("Lead", "Concrete")  # NCRP 147 has CT transmission data for these

# NCRP 147 shielding design goals P (mGy/week). Supervised areas are treated as uncontrolled.
DESIGN_GOALS = {"Controlled Area": "0.1", "Uncontrolled Area": "0.02", "Supervised Area": "0.02"}
# NCRP 147 4.1.2: the person to protect is 0.3 m beyond walls and doors, 0.5 m above the floor of the room above,
# and not more than 1.7 m above the floor below, i.e. (floor-to-floor height - 1.7 m) below this floor: 1.3 m for
# 3 m. Barrier 1 is the floor and barrier 2 the ceiling; walls and doors take 0.3 m.
BEYOND_DEFAULT = {1: "1.3", 2: "0.5"}
# The workload distributions of each kind of room, in groups split by a line in the list: NCRP 147 (Table 4.3),
# then those of the literature, whose names end with their source. A fluoroscopy room also has the radiographic
# ones of NCRP 147, for patients who have only radiographs in it (NCRP 147 5.4)
RAD_ROOM = ("Rad Room (chest bucky)", "Rad Room (floor or other barriers)", "Rad Room (all barriers)")
DISTRIBUTIONS = {
    "X-Ray room": (RAD_ROOM + ("Chest Room",),
                   tuple(name for name in KIRBY if name.startswith("DR Room")),
                   tuple(name for name in KIRBY if not name.startswith("DR Room")),
                   tuple(CHEN), (LI_ORTHOPEDIC,)),
    "Fluoroscopy Room": (("Fluoroscopy Tube (R&F room)", "Rad Tube (R&F room)", "Cardiac Angiography",
                          "Peripheral Angiography"), RAD_ROOM, tuple(BIONDI)),
    "Mammography Room": (("Mammography Room",), (JUDGE_FFDM,), (DBT, DBT_LI2013)),
}
# NCRP 147 Table 4.1 locations, exactly as in the occupancy sheet the calculation reads
OCCUPANCY_LOCATIONS = [row[0] for row in wb['Occupancy Factor ( T )'].iter_rows(min_row=2, values_only=True) if row[0]]

class dep_defs():
    def barriers(self, t, kinds=None, names=None):
        """As many barriers as 'Number of Barriers': new ones at the end (kinds and names of the new ones, in order;
        else walls with their default names), or the last ones removed."""
        current_barriers = self.d[f"x {t}"]
        max_barriers = self.d[f"vnumwall {t}"].get()
        room_number = self.d[f"nr {t}"]
        kinds, names = list(kinds or []), list(names or [])
        notebook = self.d[f"noteb {t}{room_number}"]
        # a double-click (or right click) on a tab: the name of the barrier, and wall or door
        notebook.bind("<Double-Button-1>", lambda event: self.on_barrier_tab(t, event))
        notebook.bind("<Button-3>", lambda event: self.on_barrier_tab(t, event))
        if f"tabtip {t}" not in self.d:
            self.d[f"tabtip {t}"] = tip(notebook, "barrier_tabs", where=lambda: self.pointer_on_tab(notebook))
        self.count_arrow_clicks(t)

        # Add barriers as necessary
        while current_barriers < max_barriers:
            current_barriers += 1
            self.d[f"x {t}"] = current_barriers  # the default name counts the barriers before it
            self.new_barrier(t, current_barriers, kinds.pop(0) if kinds else None, names.pop(0) if names else None)

        # Remove barriers as necessary
        unshared = []  # the other side of a shared wall that is removed: calculated again without it
        while current_barriers > max_barriers:
            partner = self.shared_partner(t, current_barriers)
            if partner:
                unshared.append(partner)
            self.unlink(t, current_barriers)
            barrier_frame_key = f"barrierf {current_barriers}{room_number}"
            label_B_key = f"label_B {current_barriers}"
            radpw_key = f"radpw {current_barriers}{room_number}"
            radsw_key = f"radsw {current_barriers}{room_number}"

            # Safely destroy and remove the barrier widgets, checking existence first
            if barrier_frame_key in self.d and self.d[barrier_frame_key] is not None:
                self.d[barrier_frame_key].destroy()
                del self.d[barrier_frame_key]

            if label_B_key in self.d and self.d[label_B_key] is not None:
                self.d[label_B_key].destroy()
                del self.d[label_B_key]

            if radpw_key in self.d and self.d[radpw_key] is not None:
                self.d[radpw_key].destroy()
                del self.d[radpw_key]

            if radsw_key in self.d and self.d[radsw_key] is not None:
                self.d[radsw_key].destroy()
                del self.d[radsw_key]

            # its name and kind
            label = self.barn.pop(f"lab_bar {current_barriers}{room_number}", None)
            if label is not None:
                self.barr.pop(label.cget("text"), None)
                label.destroy()
            self.d.pop(f"kind {current_barriers}{room_number}", None)
            self.calc.pop((room_number, current_barriers), None)
            row = self.res.pop(f"resultrow {current_barriers}{room_number}", None)
            if row is not None:
                row.destroy()
            for window in self.open_barrier_windows(t):  # the dialog of a barrier that is no more
                if window.e == current_barriers:
                    window.destroy()

            current_barriers -= 1

        # Update the number of barriers
        self.d[f"x {t}"] = current_barriers
        self.refresh_barrier_windows(t)
        self.recalculate(unshared)

        # Adjust grid based on the number of barriers and room type
        if self.d[f"vselroom {t}"].get() == "CT Room":
            self.d[f"noteb {t}{room_number}"].grid(row=0, column=2, rowspan=10, columnspan=current_barriers, pady=6.5,
                                                   padx=5, sticky="wn")
        else:
            self.d[f"noteb {t}{room_number}"].grid(row=4, column=0, rowspan=10, columnspan=current_barriers, pady=6.5,
                                                   padx=5, sticky="wn")

    def new_barrier(self, t, index, kind=None, name=None):
        """The values and widgets of barrier index: a wall or a door (barriers 1 and 2: the floor and the ceiling),
        with its name or the default one ('Wall 1', 'Door 1')."""
        room_number = self.d[f"nr {t}"]
        kind = kind if index > 2 and kind in ("wall", "door") else default_kind(index)
        self.d[f"kind {index}{room_number}"] = kind
        self.thm[f"xbar {index}{room_number}"] = 0
        self.xlmat[f"thic {index}{room_number}"] = 0

        # Default barrier settings
        for var in ["titleresul","use_ent", "radside", "radforward", "leakvar", "sellocation", "forw", "side",
                    "laks", "entk", "leak"]:
            self.d[f"{var} {index}{room_number}"] = None

        self.d[f"barrierf {index}{room_number}"] = ttk.Frame(self.d[f"noteb {t}{room_number}"], width=190)
        self.d[f"barrierf {index}{room_number}"].pack()

        name = (name or "").strip() or self.default_barrier_name(t, kind, index)
        self.barn[f"lab_bar {index}{room_number}"] = Label(text=name)
        self.d[f"noteb {t}{room_number}"].add(self.d[f"barrierf {index}{room_number}"], text=name)
        self.barr[name] = 0

        # Where the person beyond the barrier is, added to every distance from the source (NCRP 147 4.1.2),
        # unless the whole distance to the person is entered
        self.d[f"beyond {index}{room_number}"] = StringVar(value=BEYOND_DEFAULT.get(index, "0.3"))
        self.d[f"whole {index}{room_number}"] = IntVar(value=0)
        for item in ("beyond", "whole"):
            self.d[f"{item} {index}{room_number}"].trace_add(
                "write", lambda *args, e=index, nr=room_number: self.refresh_distance(e, nr))

        # Select Materials label
        self.matlab = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                                text="Select Materials:")
        rowm = 8 if self.d[f"vselroom {t}"].get() == "CT Room" else 99

        self.matlab.grid(row=rowm, column=0, padx=5, pady=6.5, sticky="w")
        materials_tip = "ct_materials" if self.d[f"vselroom {t}"].get() == "CT Room" else "materials"
        tip(self.matlab, materials_tip)

        # Add spinbox for number of materials
        self.d[f"vnumbmat {index}{room_number}"] = IntVar(value=1)
        spinbox_max = 2 if self.d[f"vselroom {t}"].get() == "CT Room" else 6
        self.d[f"numbmat {index}{room_number}"] = ttk.Spinbox(master=self.d[f"barrierf {index}{room_number}"],
            from_=1, to=spinbox_max, width=5, textvariable=self.d[f"vnumbmat {index}{room_number}"],
            command=lambda e=index, nr=room_number: self.numbmater(e, nr, t))
        self.d[f"numbmat {index}{room_number}"].grid(row=rowm, column=1, padx=5, pady=6.5, sticky="w")
        tip(self.d[f"numbmat {index}{room_number}"], materials_tip)
        if index > 2:  # walls and doors: how high above the floor their shielding goes (NCRP 147 2.3.6, 5.8)
            self.d[f"height {index}{room_number}"] = StringVar(value=HEIGHTS[0])
            label = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], text="Shielding height (m):")
            label.grid(row=rowm, column=2, padx=5, pady=6.5, sticky="e")
            box = ttk.Combobox(master=self.d[f"barrierf {index}{room_number}"], values=HEIGHTS, width=16,
                               textvariable=self.d[f"height {index}{room_number}"])
            box.grid(row=rowm, column=3, padx=5, pady=6.5, sticky="w")
            self.d[f"heightbox {index}{room_number}"] = box
            for widget in (label, box):
                tip(widget, "shielding_height")

        # Add widgets based on room type
        if self.d[f"vselroom {t}"].get() == "CT Room":
            self._add_ct_room_widgets(index, room_number, t)
        else:
            self._add_xray_room_widgets(index, room_number, t)

        # Call numbmater to initialize the materials based on the spinbox value
        self.numbmater(index, room_number, t)
        self._add_material_mode(index, room_number, t)
        if kind == "door" and not getattr(self, "restoring", False):  # a project being opened has its own values
            self.door_defaults(t, index)

    # ===================== names and kinds of the barriers =====================
    def barrier_kind(self, e, nr):
        """'floor', 'ceiling', 'wall' or 'door'."""
        return self.d.get(f"kind {e}{nr}") or default_kind(e)

    def barrier_name(self, e, nr):
        return self.barn[f"lab_bar {e}{nr}"].cget("text")

    def barrier_list(self, t, skip=None):
        """[(barrier, kind, name)] of the barriers of room t, without barrier skip."""
        nr = self.d[f"nr {t}"]
        return [(e, self.barrier_kind(e, nr), self.barrier_name(e, nr)) for e in range(1, self.d[f"x {t}"] + 1)
                if e != skip and f"lab_bar {e}{nr}" in self.barn]

    def default_barrier_name(self, t, kind, e):
        return default_name(kind, e, self.barrier_list(t, skip=e))

    def count_arrow_clicks(self, t):
        """The clicks on the arrows of 'Number of Barriers' (and its Up / Down keys): only these change the barriers,
        not the mouse wheel over it, nor the repeat of an arrow held down."""
        spinbox = self.d.get(f"numwall {t}")
        if spinbox is None or f"arrowclicks {t}" in self.d:
            return
        self.d[f"arrowclicks {t}"] = 0

        def click(event):
            try:
                on_arrow = "arrow" in str(event.widget.identify(event.x, event.y))
            except TclError:
                on_arrow = False
            if on_arrow:
                self.d[f"arrowclicks {t}"] += 1

        def key(event):
            self.d[f"arrowclicks {t}"] += 1

        spinbox.bind("<ButtonPress-1>", click, add="+")  # before the spinbox handles it (a double click: twice)
        for name in ("<KeyPress-Up>", "<KeyPress-Down>"):
            spinbox.bind(name, key, add="+")

    def barrier_count(self, t):
        """The arrows of 'Number of Barriers': every click on the arrow up opens one more window to add a wall or a
        door (two clicks, two windows), the arrow down removes the last barrier."""
        current = self.d[f"x {t}"]
        try:
            wanted = self.d[f"vnumwall {t}"].get()
        except TclError:  # not a number
            wanted = current
        clicks = self.d.get(f"arrowclicks {t}", 1)
        self.d[f"arrowclicks {t}"] = max(clicks - 1, 0)
        self.d[f"vnumwall {t}"].set(current)  # it changes when a barrier is added or removed
        if wanted == current or clicks <= 0:  # the mouse wheel, or an arrow held down
            return
        if wanted > current:
            self.barrier_dialog(t, near=self.d.get(f"numwall {t}"))
        else:
            self.d[f"vnumwall {t}"].set(max(wanted, 7))
            self.barriers(t)

    def open_barrier_windows(self, t=None):
        """The dialogs of barriers still open (of room t)."""
        self.barrier_windows = [w for w in getattr(self, "barrier_windows", []) if w.winfo_exists()]
        return [w for w in self.barrier_windows if t is None or w.room == t]

    def barrier_dialog(self, t, e=None, near=None):
        """The dialog for the kind and name of barrier e, or of a new barrier (e None). Several can be open: each
        click on the arrow up opens one more, and each adds its barrier when its Add is pressed. Barrier e has one
        dialog: a second double-click brings it to the front."""
        nr = self.d[f"nr {t}"]
        open_windows = self.open_barrier_windows(t)
        if e is not None:
            for window in open_windows:
                if window.e == e:
                    window.lift()
                    window.entry.focus_set()
                    return window
        new = e is None
        kind = "wall" if new else self.barrier_kind(e, nr)
        name = "" if new else self.barrier_name(e, nr)
        if new:  # as the room is when its Add is pressed: its barrier comes at the end
            state = lambda: (self.d[f"x {t}"] + 1, self.barrier_list(t))
        else:
            state = lambda: (e, self.barrier_list(t, skip=e))

        def done(kind, name, shared=KEEP):
            barrier = None
            if new:
                barrier = self.add_barrier(t, kind, name)
            elif e <= self.d[f"x {t}"]:
                self.set_barrier(t, e, kind, name)
                barrier = e
            if barrier is not None and shared is not KEEP:  # a wall shared with another room of the department
                self.set_shared(t, barrier, shared)
            self.refresh_barrier_windows(t)

        window = BarrierDialog(self.master, e, kind, name, state, self.d[f"vselroom {t}"].get(), done, new=new,
                               near=near, offset=theme.px(28) * len(open_windows),
                               sharing=self.sharing_options(t, e))
        window.room = t
        self.barrier_windows.append(window)
        self.barrier_window = window  # the last one opened
        return window

    def refresh_barrier_windows(self, t):
        """The open dialogs of room t follow its barriers: default names and names already taken."""
        for window in self.open_barrier_windows(t):
            window.update_view()

    def add_barrier(self, t, kind="wall", name=None):
        """One more barrier at the end of room t; returns its number."""
        nr = self.d[f"nr {t}"]
        self.d[f"vnumwall {t}"].set(self.d[f"x {t}"] + 1)
        self.barriers(t, kinds=[kind], names=[name])
        e = self.d[f"x {t}"]
        self.d[f"noteb {t}{nr}"].select(self.d[f"barrierf {e}{nr}"])
        return e

    def set_barrier(self, t, e, kind=None, name=None, defaults=True):
        """Barrier e becomes a wall or a door (the floor and the ceiling stay what they are) with the name given, or
        its default name. defaults: a wall that becomes a door gets what a new door has, where nothing is entered."""
        nr = self.d[f"nr {t}"]
        old_kind, old_name = self.barrier_kind(e, nr), self.barrier_name(e, nr)
        kind = kind if old_kind not in ("floor", "ceiling") and kind in ("wall", "door") else old_kind
        self.d[f"kind {e}{nr}"] = kind
        name = (name or "").strip() or self.default_barrier_name(t, kind, e)
        self.barn[f"lab_bar {e}{nr}"].configure(text=name)
        self.d[f"noteb {t}{nr}"].tab(self.d[f"barrierf {e}{nr}"], text=name)
        self.barr.pop(old_name, None)
        self.barr[name] = 0
        label = self.d.get(f"resname {e}{nr}")  # the name in the results
        if label is not None and label.winfo_exists():
            label.configure(text=name)
        if defaults and kind == "door" and old_kind != "door":
            self.door_defaults(t, e)
        partner = self.shared_partner(t, e)
        if partner and name != old_name:  # the other room names this wall in its results
            self.recalculate([partner])

    def door_defaults(self, t, e):
        """What a new door starts with, where nothing is entered yet: a secondary barrier in an X-ray or fluoroscopy
        room (a door is not aimed at by the primary beam), of lead, a lead-lined door (NCRP 147 2.3.3.1), or of wood
        in a mammography room, a solid-core door (NCRP 147 5.5)."""
        nr = self.d[f"nr {t}"]
        room_type = self.d[f"vselroom {t}"].get()
        radiation = self.d.get(f"radiob_w {e}{nr}0")
        if room_type in ("X-Ray room", "Fluoroscopy Room") and radiation is not None and radiation.get() == 0:
            radiation.set(2)
            self.barrier_sel(e, nr, t, 0)
        material = self.d.get(f"vmater {e}1{nr}")
        if material is not None and material.get() in ("", "Select Material"):
            material.set(door_material(room_type))

    def on_barrier_tab(self, t, event):
        """A double-click (or right click) on the tab of a wall or a door: its name, and wall or door."""
        notebook = event.widget
        try:
            if notebook.identify(event.x, event.y) in ("", "client"):
                return
            frame = notebook.tabs()[notebook.index(f"@{event.x},{event.y}")]
        except (TclError, IndexError):
            return
        nr = self.d[f"nr {t}"]
        e = next((k for k in range(1, self.d[f"x {t}"] + 1) if str(self.d.get(f"barrierf {k}{nr}")) == str(frame)),
                 None)
        if e is None:
            return
        notebook.select(frame)
        if self.barrier_kind(e, nr) in ("floor", "ceiling"):
            return  # they keep their names
        self.barrier_dialog(t, e, near=notebook)

    @staticmethod
    def pointer_on_tab(notebook):
        """Whether the pointer is on a tab of the notebook (not on what the tab shows)."""
        try:
            x = notebook.winfo_pointerx() - notebook.winfo_rootx()
            y = notebook.winfo_pointery() - notebook.winfo_rooty()
            return notebook.identify(x, y) not in ("", "client")
        except TclError:
            return False

    # ===================== walls shared by two rooms of a department =====================
    def sharing_options(self, t, e=None):
        """For a room of a department: the walls and doors of its other designed rooms that barrier e can share,
        {"choices": [(label, (room, barrier))], "current": (room, barrier) or None}; None for a standalone room."""
        dep = self.d.get(f"dep {t}")
        if dep is None or dep not in self.departments:
            return None
        choices, seen = [], set()
        for t2 in self.departments[dep]["rooms"]:
            if t2 == t or not self.d.get(f"run {t2}") or f"nr {t2}" not in self.d:
                continue
            for e2, kind, name in self.barrier_list(t2):
                if kind in ("wall", "door"):
                    label, n = f"{self.room_name(t2)} · {name}", 2
                    while label in seen:  # two rooms of the same name
                        label, n = f"{self.room_name(t2)} ({n}) · {name}", n + 1
                    seen.add(label)
                    choices.append((label, (t2, e2)))
        return {"choices": choices, "current": self.shared_partner(t, e) if e is not None else None}

    def shared_partner(self, t, e):
        """(room, barrier) on the other side of a wall or door shared with another room of the department, or None."""
        nr = self.d.get(f"nr {t}")
        link = self.d.get(f"shared {e}{nr}") if nr is not None else None
        if not link:
            return None
        t2, e2 = link
        nr2 = self.d.get(f"nr {t2}")
        if nr2 is None or not self.d.get(f"run {t2}") or e2 > self.d.get(f"x {t2}", 0) \
                or self.d.get(f"shared {e2}{nr2}") != (t, e):
            return None
        return t2, e2

    def unlink(self, t, e):
        """Barrier e of room t no longer shares its wall (nor does the barrier on the other side)."""
        nr = self.d.get(f"nr {t}")
        link = self.d.pop(f"shared {e}{nr}", None)
        if link:
            t2, e2 = link
            nr2 = self.d.get(f"nr {t2}")
            if nr2 is not None and self.d.get(f"shared {e2}{nr2}") == (t, e):
                self.d.pop(f"shared {e2}{nr2}", None)

    def set_shared(self, t, e, other):
        """Barrier e of room t is the same wall (or door) as barrier other = (room, barrier) of another room of the
        department; None: it shares it with no room. The barriers concerned that were calculated are calculated
        again."""
        old = self.shared_partner(t, e)
        if other == old:
            return
        touched = [(t, e)]
        if old:
            touched.append(old)
        self.unlink(t, e)
        if other:
            t2, e2 = other
            previous = self.shared_partner(t2, e2)
            if previous:
                touched.append(previous)
            self.unlink(t2, e2)
            self.d[f"shared {e}{self.d[f'nr {t}']}"] = (t2, e2)
            self.d[f"shared {e2}{self.d[f'nr {t2}']}"] = (t, e)
            touched.append((t2, e2))
        self.recalculate(touched)

    def recalculate(self, barriers):
        """Calculate again the barriers [(room, barrier)] that have been calculated (their results follow a change)."""
        for t, e in dict.fromkeys(barriers):
            nr = self.d.get(f"nr {t}")
            if nr is not None and e <= self.d.get(f"x {t}", 0) and (nr, e) in self.calc:
                self.choosetype(e, nr, t, notify=False, partner=False)

    def plan_barrier(self, t, kind, k, create=False):
        """The barrier of room t of the k-th wall (or door) of its floor plan: its k-th wall (door), in the order of
        the tabs. create: walls (doors) are added at the end until there is one."""
        nr = self.d[f"nr {t}"]
        while True:
            found = [e for e in range(1, self.d[f"x {t}"] + 1) if self.barrier_kind(e, nr) == kind]
            if k < len(found):
                return found[k]
            if not create:
                return None
            self.add_barrier(t, kind)

    def _add_ct_room_widgets(self, index, room_number, t):
        """Add CT room specific widgets."""
        self.distance_widgets(index, room_number, 0, row=5, ct=True)  # rows 5 to 7

        # Area classification, occupancy factor T and design goal P, as for X-ray rooms (NCRP 147)
        self._add_area_widgets(index, room_number, t)
        self.d[f"calbutton {index}{room_number}"] = ttk.Button(master=self.d[f"barrierf {index}{room_number}"],
                                                               text="Calculate", style="Accent.TButton",
                                                               command=lambda e=index, nr=room_number: self.choosetype(
                                                                   e, nr, t))
        self.d[f"calbutton {index}{room_number}"].grid(row=109, column=2, pady=6.5, padx=5, sticky="w")
        tip(self.d[f"calbutton {index}{room_number}"], "calculate")
        self.far_widgets(index, room_number, t)
        self.patients_widgets(index, room_number, t)

    def _add_xray_room_widgets(self, index, room_number, t):
        """Add X-ray room specific widgets."""
        # Label to indicate number of radiation types on the barrier
        labb = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                         text="Select the number of types\nof radiation on the barrier:")
        labb.grid(row=0, column=0, pady=6.5, padx=5, sticky="w")
        tip(labb, "num_radiation")

        # Initialize tracking of the previous number of barriers
        self.d[f"prev_num_barriers {index}{room_number}"] = 0

        # Spinbox for the number of barriers
        self.d[f"num_barriers_var {index}{room_number}"] = IntVar(value=1)  # Default to 1
        self.d[f"num_barriers_spinbox {index}{room_number}"] = ttk.Spinbox(
            master=self.d[f"barrierf {index}{room_number}"], width=5, from_=1, to=8, increment=1,
            textvariable=self.d[f"num_barriers_var {index}{room_number}"],
            command=lambda e=index, nr=room_number: self._create_barrier_widgets(e, nr, t))
        self.d[f"num_barriers_spinbox {index}{room_number}"].grid(row=0, column=1, pady=6.5, padx=5, sticky="w")
        tip(self.d[f"num_barriers_spinbox {index}{room_number}"], "num_radiation")
        self._create_barrier_widgets(index, room_number, t)
        # Area classification and occupancy factor
        self._add_area_widgets(index, room_number, t)


        self.d[f"calbutton {index}{room_number}"] = ttk.Button(master=self.d[f"barrierf {index}{room_number}"],text="Calculate",
              style="Accent.TButton", command=lambda e=index, nr=room_number: self.choosetype(e, nr, t))
        self.d[f"calbutton {index}{room_number}"].grid(row=109, column=2, pady=6.5, padx=5, sticky="w")
        tip(self.d[f"calbutton {index}{room_number}"], "calculate")
        self.far_widgets(index, room_number, t)
        self.patients_widgets(index, room_number, t)

    def far_widgets(self, e, nr, t):
        """Under the design goal: a further area beyond the barrier, which may need more shielding than the one just
        beyond it, e.g. an office across a corridor (NCRP 147 4.1.3 and Table 4.1, note a)."""
        frame = ttk.Frame(self.d[f"barrierf {e}{nr}"])
        frame.grid(row=108, column=0, columnspan=6, padx=5, pady=(4, 0), sticky="w")
        self.d[f"farframe {e}{nr}"] = frame
        self.far_vars(e, nr)
        self.update_far_panel(e, nr, t)

    def far_vars(self, e, nr):
        """The values of the further area of barrier e: kept while its panel is rebuilt, and saved."""
        defaults = {"far": lambda: IntVar(value=0), "fardist": lambda: StringVar(value=""),
                    "farloc": lambda: StringVar(value="Administrative or clerical offices"),
                    "farT": lambda: StringVar(value="1"), "fararea": lambda: StringVar(value="Uncontrolled Area"),
                    "farP": lambda: StringVar(value="0.02")}
        for name, make in defaults.items():
            if self.d.get(f"{name} {e}{nr}") is None:
                self.d[f"{name} {e}{nr}"] = make()

    def update_far_panel(self, e, nr, t):
        frame = self.d.get(f"farframe {e}{nr}")
        if frame is None or not frame.winfo_exists():
            return
        for child in frame.winfo_children():
            child.destroy()
        check = ttk.Checkbutton(frame, text="Also check an area further away (NCRP 147 4.1.3)",
                                variable=self.d[f"far {e}{nr}"], command=lambda: self.update_far_panel(e, nr, t))
        check.grid(row=0, column=0, columnspan=6, sticky="w")
        tip(check, "far_area")
        if self.d[f"far {e}{nr}"].get() != 1:
            return

        def entry(name, row, column, key):
            widget = ttk.Entry(frame, textvariable=self.d[f"{name} {e}{nr}"], width=7)
            widget.grid(row=row, column=column, padx=(6, 2), pady=3, sticky="w")
            self.d[f"{name}_entry {e}{nr}"] = widget
            tip(widget, key)

        label = ttk.Label(frame, text="Further than the person beyond the barrier by (m):")
        label.grid(row=1, column=0, columnspan=2, padx=(24, 0), pady=3, sticky="w")
        tip(label, "far_distance")
        entry("fardist", 1, 2, "far_distance")
        label = ttk.Label(frame, text="Location:")
        label.grid(row=2, column=0, padx=(24, 0), pady=3, sticky="w")
        tip(label, "far_location")

        def location_chosen(choice):
            if choice in OCCUPANCY_T:
                self.d[f"farT {e}{nr}"].set(f"{OCCUPANCY_T[choice]:g}")
        menu = ttk.OptionMenu(frame, self.d[f"farloc {e}{nr}"], self.d[f"farloc {e}{nr}"].get(), *OCCUPANCY_LOCATIONS,
                              command=location_chosen)
        menu.config(width=24)
        menu.grid(row=2, column=1, padx=(6, 2), pady=3, sticky="w")
        tip(menu, "far_location")
        ttk.Label(frame, text="T:").grid(row=2, column=2, padx=(12, 0), sticky="e")
        entry("farT", 2, 3, "far_location")
        label = ttk.Label(frame, text="Area:")
        label.grid(row=3, column=0, padx=(24, 0), pady=3, sticky="w")
        tip(label, "far_goal")
        area = ttk.Combobox(frame, textvariable=self.d[f"fararea {e}{nr}"], state="readonly", width=24,
                            values=["Controlled Area", "Uncontrolled Area", "Supervised Area"])
        area.grid(row=3, column=1, padx=(6, 2), pady=3, sticky="w")
        area.bind("<<ComboboxSelected>>", lambda event: self.d[f"farP {e}{nr}"].set(
            DESIGN_GOALS.get(self.d[f"fararea {e}{nr}"].get(), self.d[f"farP {e}{nr}"].get())))
        tip(area, "far_goal")
        ttk.Label(frame, text="P (mGy·week⁻¹):").grid(row=3, column=2, padx=(12, 0), sticky="e")
        entry("farP", 3, 3, "far_goal")

    def patients_widgets(self, e, nr, t):
        """Under Calculate, a check of its own: how many patients (CT: procedures) per week the barrier allows as it
        will be built, with its planned thicknesses and its existing shielding (NCRP 147 6.3.3)."""
        frame = self.d[f"barrierf {e}{nr}"]
        self.d[f"checkpatients {e}{nr}"] = IntVar(value=0)
        what = "procedures" if self.d[f"vselroom {t}"].get() == "CT Room" else "patients"
        button = ttk.Checkbutton(frame, text=f"Check how many {what} per week the barrier allows",
                                 variable=self.d[f"checkpatients {e}{nr}"],
                                 command=lambda: self.on_patients_check(e, nr, t))
        button.grid(row=110, column=0, columnspan=4, padx=5, pady=(10, 2), sticky="w")
        tip(button, "check_patients")
        label = ttk.Label(frame, style="Muted.TLabel", wraplength=theme.px(640), justify=LEFT)
        label.grid(row=111, column=0, columnspan=5, padx=(28, 5), pady=(0, 10), sticky="w")
        label.grid_remove()
        self.d[f"patientsres {e}{nr}"] = label

    def on_patients_check(self, e, nr, t):
        # the answer under the check, and in the results of a calculated barrier
        if (nr, e) in self.calc:
            self.show_barrier_result(e, nr, t)
        else:
            self.show_patients(e, nr, t)

    def _create_barrier_widgets(self, index, room_number, t):
        """Dynamically create or delete barrier-related widgets based on the selected number in the Spinbox."""
        num_barriers = self.d[f"num_barriers_var {index}{room_number}"].get()
        prev_num_barriers = self.d[f"prev_num_barriers {index}{room_number}"]
        mammo = self.d[f"vselroom {t}"].get() == "Mammography Room"
        radiation_tip = "radiation_type_mammo" if mammo else "radiation_type"

        if num_barriers > prev_num_barriers:
            # Create widgets for the new barriers
            for i in range(prev_num_barriers, num_barriers):
                # Label for barrier type
                self.d[f"label_B {index}{room_number}{i}"] = ttk.Label(master=self.d[f"barrierf {index}{room_number}"],
                    style="BL2.TLabel", text=f"Select Radiation Type #{i + 1}:")
                self.d[f"label_B {index}{room_number}{i}"].grid(row=i * 12 + 1, column=0, pady=6.5, padx=5, sticky="w")
                tip(self.d[f"label_B {index}{room_number}{i}"], radiation_tip)

                self.d[f"radiob_w {index}{room_number}{i}"] = IntVar(value=0)

                # Primary Barrier Radiobutton
                self.d[f"radpw {index}{room_number}{i}"] = ttk.Radiobutton(
                    master=self.d[f"barrierf {index}{room_number}"],
                    variable=self.d[f"radiob_w {index}{room_number}{i}"], text=f"Primary", value=1,
                    command=lambda e=index, nr=room_number, i=i: self.barrier_sel(e, nr, t, i))
                self.d[f"radpw {index}{room_number}{i}"].grid(row=i * 12 + 1, column=1, pady=6.5, padx=5, sticky="w")
                tip(self.d[f"radpw {index}{room_number}{i}"], radiation_tip)

                # Secondary Barrier Radiobutton
                self.d[f"radsw {index}{room_number}{i}"] = ttk.Radiobutton(
                    master=self.d[f"barrierf {index}{room_number}"],
                    variable=self.d[f"radiob_w {index}{room_number}{i}"], text=f"Secondary", value=2,
                    command=lambda e=index, nr=room_number, i=i: self.barrier_sel(e, nr, t, i))
                self.d[f"radsw {index}{room_number}{i}"].grid(row=i * 12 + 1, column=2, pady=6.5, padx=5, sticky="w")
                tip(self.d[f"radsw {index}{room_number}{i}"], radiation_tip)
                # The distance, below what the radiation type is: from the source to the barrier, plus beyond it
                self.distance_widgets(index, room_number, i, row=i * 12 + 9)

                # Mammography (NCRP 147): only secondary radiation, so preselect it
                if mammo:
                    self.d[f"radiob_w {index}{room_number}{i}"].set(2)
                    self.d[f"radpw {index}{room_number}{i}"].state(["disabled"])
                    self.barrier_sel(index, room_number, t, i)

        elif num_barriers < prev_num_barriers:
            for i in range(num_barriers, prev_num_barriers):
                # Define widget keys
                keys_to_destroy = [f"radpw {index}{room_number}{i}", f"radsw {index}{room_number}{i}",
                    f"label_B {index}{room_number}{i}", f"lad {index}{room_number}{i}",
                    f"entryd {index}{room_number}{i}", f"workltit {index}{room_number}{i}", f"selxray1 {index}{room_number}{i}",
                    f"selxray2 {index}{room_number}{i}", f"lau {index}{room_number}{i}", f"use_ent {index}{room_number}{i}",
                    f"presh {index}{room_number}{i}", f"selxroom {index}{room_number}{i}", f"laks {index}{room_number}{i}",
                    f"entk {index}{room_number}{i}", f"othwork {index}{room_number}{i}", f"radbucky {index}{room_number}{i}",
                    f"radcross {index}{room_number}{i}", f"radworkl {index}{room_number}{i}",f"radnumb {index}{room_number}{i}",
                    f"worentry {index}{room_number}{i}",f"numpapwe {index}{room_number}{i}", f"airkncrp {index}{room_number}{i}",
                    f"unairk {index}{room_number}{i}",f"leak {index}{room_number}{i}", f"side {index}{room_number}{i}", f"forw {index}{room_number}{i}",
                    f"radside {index}{room_number}{i}", f"radforward {index}{room_number}{i}", f"radleak {index}{room_number}{i}",
                    f"kvpbox {index}{room_number}{i}", f"labbeyond {index}{room_number}{i}",
                    f"beyondentry {index}{room_number}{i}", f"dtotal {index}{room_number}{i}",
                    f"dbt1 {index}{room_number}{i}", f"dbt2 {index}{room_number}{i}", f"dbt3 {index}{room_number}{i}",
                    f"dbt4 {index}{room_number}{i}", f"dbtbox {index}{room_number}{i}", f"fieldframe {index}{room_number}{i}",
                    f"angleframe {index}{room_number}{i}", f"angleopt {index}{room_number}{i}"]
                vars_to_delete = [f"vselxray {index}{room_number}{i}", f"preshvar {index}{room_number}{i}",
                    f"oworkvar {index}{room_number}{i}", f"radiob_pre {index}{room_number}{i}",
                    f"workv {index}{room_number}{i}", f"vsexroom {index}{room_number}{i}",
                    f"radiob_w {index}{room_number}{i}", f"kvpdata {index}{room_number}{i}",
                    f"entryd_var {index}{room_number}{i}"]
                # Destroy and delete widgets
                for key in keys_to_destroy:
                    if key in self.d and self.d[key] is not None:
                        self.d[key].destroy()
                        del self.d[key]
                # Delete variables
                for var_key in vars_to_delete:
                    if var_key in self.d:
                        del self.d[var_key]

        # Update the previous number of barriers
        self.d[f"prev_num_barriers {index}{room_number}"] = num_barriers
        self.primary_share_widget(index, room_number)

    def barrier_sel(self, e, nr, t, i):
        radiob_w_key = f"radiob_w {e}{nr}{i}"
        barrierf_key = f"barrierf {e}{nr}"
        widget_keys = [f"leak {e}{nr}{i}", f"side {e}{nr}{i}", f"forw {e}{nr}{i}",
                    f"lau {e}{nr}{i}", f"use_ent {e}{nr}{i}", f"presh {e}{nr}{i}",f"radbucky {e}{nr}{i}", 
                    f"radcross {e}{nr}{i}", f"laks {e}{nr}{i}", f"entk {e}{nr}{i}",f"radside {e}{nr}{i}",
                    f"radforward {e}{nr}{i}",f"radleak {e}{nr}{i}",f"airkncrp {e}{nr}{i}", f"fieldframe {e}{nr}{i}",
                    f"angleframe {e}{nr}{i}", f"angleopt {e}{nr}{i}",
                    f"unairk {e}{nr}{i}",f"othwork {e}{nr}{i}", f"radworkl {e}{nr}{i}",f"radnumb {e}{nr}{i}",
                    f"worentry {e}{nr}{i}",f"numpapwe {e}{nr}{i}", f"selxroom {e}{nr}{i}"]
        # ===== Workload Distribution =====
        self.d[f'workltit {e}{nr}{i}'] = ttk.Label(master=self.d[barrierf_key], style="BL2.TLabel",
                                                   text=f"Workload Distribution #{i + 1}:")
        self.d[f'workltit {e}{nr}{i}'].grid(row=i * 12 + 4, column=0, padx=5, pady=6.5, sticky="w")
        tip(self.d[f'workltit {e}{nr}{i}'], "workload_distribution")

        self.d[f"vselxray {e}{nr}{i}"] = IntVar(value=0)

        # Radio buttons for room or kVp selection
        self.create_radio_button(key=f"selxray1 {e}{nr}{i}", master=self.d[barrierf_key],
                                 text="X-Ray Room", variable=self.d[f"vselxray {e}{nr}{i}"],
                                 value=1, row=i * 12 + 4, column=1, command=lambda: self.XrRoom(e, nr, i),
                                 tip_key="workload_distribution")

        self.create_radio_button(key=f"selxray2 {e}{nr}{i}", master=self.d[barrierf_key], text="Give kVp",
                                 variable=self.d[f"vselxray {e}{nr}{i}"], value=2, row=i * 12 + 4, column=2,
                                 command=lambda: self.XrRoom(e, nr, i), tip_key="kvp")

        # ===== Selects Primary  =====
        if self.d[radiob_w_key].get() == 1:
            # Safely destroy previous widgets
            self.destroy_widgets(widget_keys)
            # ===== Use Factor =====
            self.d[f"lau {e}{nr}{i}"] = ttk.Label(master=self.d[barrierf_key], style="AL.TLabel", text="Use Factor:")
            self.d[f"lau {e}{nr}{i}"].grid(row=i * 12 + 7, column=0, pady=6.5, padx=5, sticky="w")
            self.d[f"use_ent {e}{nr}{i}"] = ttk.Entry(master=self.d[barrierf_key], width=10)
            self.d[f"use_ent {e}{nr}{i}"].grid(row=i * 12 + 7, column=1, pady=6.5, padx=5, sticky="w")
            tip(self.d[f"lau {e}{nr}{i}"], "use_factor")
            tip(self.d[f"use_ent {e}{nr}{i}"], "use_factor")

            # ===== Primary Unshielded Air Kerma =====
            self.d[f"laks {e}{nr}{i}"] = ttk.Label(master=self.d[barrierf_key],
                                                   text="Primary Unshielded\nAir Kerma K (mGy∙patient\u207B\u00b9):")
            self.d[f"laks {e}{nr}{i}"].grid(row=i * 12 + 6, column=0, pady=6.5, padx=5, sticky="w")
            self.d[f"entk {e}{nr}{i}"] = ttk.Entry(master=self.d[barrierf_key], width=10)
            self.d[f"entk {e}{nr}{i}"].grid(row=i * 12 + 6, column=1, pady=6.5, padx=5, sticky="w")
            tip(self.d[f"laks {e}{nr}{i}"], "primary_kerma")
            tip(self.d[f"entk {e}{nr}{i}"], "primary_kerma")

            # ===== Preshielding Option =====
            self.d[f"preshvar {e}{nr}{i}"] = IntVar(value=0)
            self.d[f"presh {e}{nr}{i}"] = ttk.Checkbutton(master=self.d[barrierf_key], text="Preshielding",
                                                      variable=self.d[f"preshvar {e}{nr}{i}"], offvalue=0, onvalue=1,
                                                      command=lambda: self.pres(e, nr, i))
            self.d[f"presh {e}{nr}{i}"].grid(row=i * 12 + 6, column=2, pady=6.5, padx=5, sticky="w")
            tip(self.d[f"presh {e}{nr}{i}"], "preshielding")

        # ===== Selects Secondary =====
        elif self.d[radiob_w_key].get() == 2:
            # Safely destroy previous widgets for secondary
            self.destroy_widgets(widget_keys)
            # Create radio buttons for unshielded secondary air kerma options
            self.d[f"unairkerv {e}{nr}{i}"] = IntVar(value=0)
            self.create_radio_button(key=f"airkncrp {e}{nr}{i}", master=self.d[barrierf_key],
                text="Select Unshielded Secondary\nAir Kerma (mGy∙patient\u207B\u00b9)\nSuggested (NCRP 147)",
                variable=self.d[f"unairkerv {e}{nr}{i}"], value=1, row=i * 12 + 6, column=0,
                command=lambda: self.unairk(e, nr, i), tip_key="secondary_kerma_ncrp")
            self.create_radio_button(key=f"unairk {e}{nr}{i}", master=self.d[barrierf_key],
                text="Write Unshielded Secondary\nAir Kerma (mGy∙patient\u207B\u00b9)", variable=self.d[f"unairkerv {e}{nr}{i}"],
                value=2, row=i * 12 + 6, column=1, command=lambda: self.unairk(e, nr, i),
                tip_key="secondary_kerma_write")
        # ===== Different Workload Option =====
        self.d[f"oworkvar {e}{nr}{i}"] = IntVar(value=0)
        self.d[f"othwork {e}{nr}{i}"] = ttk.Checkbutton(master=self.d[barrierf_key], text="Different Workload",
                                                        variable=self.d[f"oworkvar {e}{nr}{i}"], offvalue=0,
                                                        onvalue=1, command=lambda: self.owork(e, nr, i))
        self.d[f"othwork {e}{nr}{i}"].grid(row=i * 12 + 11, column=0, pady=6.5, padx=5, sticky="w")
        tip(self.d[f"othwork {e}{nr}{i}"], "different_workload")

        # Mammography (NCRP 147): preselect the mammography workload distribution and the NCRP air kerma
        if self.d[f"vselroom {t}"].get() == "Mammography Room" and self.d[radiob_w_key].get() == 2:
            self.d[f"vselxray {e}{nr}{i}"].set(1)
            self.XrRoom(e, nr, i)
            self.d[f"vsexroom {e}{nr}{i}"].set("Mammography Room")
            self.d[f"unairkerv {e}{nr}{i}"].set(1)
            self.unairk(e, nr, i)
        self.refresh_distance(e, nr)  # dP or a secondary distance
        self.primary_share_widget(e, nr)

    def primary_share_widget(self, e, nr):
        """Under the radiation types, when the barrier has both a primary and a secondary radiation type: the option to
        count the secondary radiation of a workload only for the part (1 - U) not aimed at this barrier (NCRP 147
        Eq. C.4, C.8). Off at first, as in NCRP 147 Table 4.7 and its examples."""
        count = self.d[f"num_barriers_var {e}{nr}"].get()
        kinds = set()
        for i in range(count):
            variable = self.d.get(f"radiob_w {e}{nr}{i}")
            kinds.add(variable.get() if variable is not None else 0)
        key = f"oneminusu_check {e}{nr}"
        if {1, 2} <= kinds:
            if self.d.get(f"oneminusu {e}{nr}") is None:
                self.d[f"oneminusu {e}{nr}"] = IntVar(value=0)
            if self.d.get(key) is None or not self.d[key].winfo_exists():
                check = ttk.Checkbutton(self.d[f"barrierf {e}{nr}"], variable=self.d[f"oneminusu {e}{nr}"],
                                        text="Secondary radiation × (1 − U): only the part of a workload not aimed "
                                             "at this barrier")
                check.grid(row=98, column=0, columnspan=6, padx=5, pady=6.5, sticky="w")
                tip(check, "one_minus_u")
                self.d[key] = check
        else:  # no longer both: the option goes, and is off when it comes back
            if self.d.get(key) is not None:
                self.d[key].destroy()
                self.d[key] = None
            self.d.pop(f"oneminusu {e}{nr}", None)

    def room_type_of(self, nr):
        """The kind of room ('X-Ray room', 'CT Room', ...) whose barriers are keyed by nr."""
        for key, value in self.d.items():
            if key.startswith("nr ") and value == nr:
                return self.d[f"vselroom {key[3:]}"].get()
        return None

    def on_distribution(self, e, nr, i):
        """A workload distribution was chosen: its suggested values. The suggested secondary air kerma of DBT has
        its own choices (2D, 3D, 2D + 3D), so the panel is rebuilt."""
        self.uns(e, nr, i)
        unairkerv = self.d.get(f"unairkerv {e}{nr}{i}")
        if self.d[f"radiob_w {e}{nr}{i}"].get() == 2 and unairkerv is not None and unairkerv.get() == 1:
            self.unairk(e, nr, i)
        else:
            self.update_kerma_label(e, nr, i)
            if self.d[f"radiob_w {e}{nr}{i}"].get() == 2 and unairkerv is not None and unairkerv.get() == 2:
                self.field_widgets(e, nr, i)  # the field the written value is for follows the distribution

    def update_kerma_label(self, e, nr, i):
        """The suggested secondary air kerma comes from NCRP 147, or from the source of a distribution of the
        literature (Yang et al. 2017, Kirby et al. 2023, Biondi et al. 2024)."""
        button, distribution = self.d.get(f"airkncrp {e}{nr}{i}"), self.d.get(f"vsexroom {e}{nr}{i}")
        if button is not None:
            name = distribution.get() if distribution is not None else None
            source = KERMA_SOURCES.get(name) or SOURCES.get(name, "NCRP 147")
            kvp = self.d.get(f"vselxray {e}{nr}{i}")
            way = "At an angle (NCRP 147)" if kvp is not None and kvp.get() == 2 else f"Suggested ({source})"
            button.configure(text=f"Select Unshielded Secondary\nAir Kerma (mGy∙patient⁻¹)\n{way}")

    def XrRoom(self, e, nr, i):
        # Access frequently used keys
        xray_key = f"vselxray {e}{nr}{i}"
        barrierf_key = f"barrierf {e}{nr}"
        radiob_w_key = f"radiob_w {e}{nr}{i}"
        selxroom_key = f"selxroom {e}{nr}{i}"
        vsexroom_key = f"vsexroom {e}{nr}{i}"

        if self.d[xray_key].get() == 1:
            # Destroy existing widget if it exists
            if self.d.get(selxroom_key):
                self.d[selxroom_key].destroy()
            if self.d.get(f"kvpbox {e}{nr}{i}") is not None:  # the data choice of 'Give kVp'
                self.d[f"kvpbox {e}{nr}{i}"].destroy()
                self.d[f"kvpbox {e}{nr}{i}"] = None
            # The workload distributions of this kind of room, a line between NCRP 147 and each source of the literature
            groups = DISTRIBUTIONS.get(self.room_type_of(nr), DISTRIBUTIONS["X-Ray room"])
            self.xrooms = [name for group in groups for name in group]
            self.d[vsexroom_key] = StringVar()
            self.d[selxroom_key] = ttk.OptionMenu(self.d[barrierf_key], self.d[vsexroom_key], "Select X-ray room",
                                                  *self.xrooms, command=lambda value: self.on_distribution(e, nr, i))
            menu, index = self.d[selxroom_key].nametowidget(self.d[selxroom_key]["menu"]), len(self.xrooms)
            for group in reversed(groups[1:]):
                index -= len(group)
                if group and index:
                    menu.insert_separator(index)
            self.d[selxroom_key].grid(row=i * 12 + 5, column=1, columnspan=2, pady=6.5, padx=5, sticky="w")
            tip(self.d[selxroom_key], "workload_distribution")

        elif self.d[xray_key].get() == 2:
            # Destroy existing widget if it exists
            if self.d.get(selxroom_key):
                self.d[selxroom_key].destroy()

            if self.d[radiob_w_key].get() == 1:
                # Define spinbox for kVp values for primary barrier, and the transmission data to use
                self.d[vsexroom_key] = IntVar(value=80)
                self.d[selxroom_key] = ttk.Spinbox(master=self.d[barrierf_key], from_=25, to=150, increment=5,
                                                   textvariable=self.d[vsexroom_key], width=10)
                self.d[selxroom_key].grid(row=i * 12 + 5, column=2, pady=6.5, padx=5, sticky="w")
                tip(self.d[selxroom_key], "kvp")
                if self.d.get(f"kvpdata {e}{nr}{i}") is None:
                    self.d[f"kvpdata {e}{nr}{i}"] = StringVar(value=KVP_DATA[0])
                if self.d.get(f"kvpbox {e}{nr}{i}") is not None:
                    self.d[f"kvpbox {e}{nr}{i}"].destroy()
                self.d[f"kvpbox {e}{nr}{i}"] = ttk.Combobox(master=self.d[barrierf_key], values=KVP_DATA,
                                                            textvariable=self.d[f"kvpdata {e}{nr}{i}"],
                                                            state="readonly", width=34)
                self.d[f"kvpbox {e}{nr}{i}"].grid(row=i * 12 + 5, column=3, columnspan=2, pady=6.5, padx=5,
                                                  sticky="w")
                tip(self.d[f"kvpbox {e}{nr}{i}"], "kvp_data")

            elif self.d[radiob_w_key].get() == 2:
                if self.d.get(f"kvpbox {e}{nr}{i}") is not None:
                    self.d[f"kvpbox {e}{nr}{i}"].destroy()
                    self.d[f"kvpbox {e}{nr}{i}"] = None
                # The kVp of the secondary transmission data: those of NCRP 147; in a mammography room also the Mo/Mo
                # beams of NCRP 147 and the W/Al, W/Rh (Li et al. 2012) and W/Ag beams (Li et al. 2013)
                mammography = self.room_type_of(nr) == "Mammography Room"
                old = self.d.get(f"kvpdata {e}{nr}{i}")
                data = StringVar(value=old.get() if old is not None and old.get() in MAMMO_KVP_DATA else "NCRP 147")
                self.d[f"kvpdata {e}{nr}{i}"] = data
                values = MAMMO_KVPS[data.get() if mammography else "NCRP 147"]
                self.d[vsexroom_key] = IntVar(value=values[0])
                spinbox = ttk.Spinbox(master=self.d[barrierf_key], values=values, textvariable=self.d[vsexroom_key],
                                      width=10)
                spinbox.grid(row=i * 12 + 5, column=2, pady=6.5, padx=5, sticky="w")
                self.d[selxroom_key] = spinbox
                tip(spinbox, "kvp")
                if mammography:
                    box = ttk.Combobox(master=self.d[barrierf_key], values=MAMMO_KVP_DATA, textvariable=data,
                                       state="readonly", width=20)
                    box.grid(row=i * 12 + 5, column=3, columnspan=2, pady=6.5, padx=5, sticky="w")
                    self.d[f"kvpbox {e}{nr}{i}"] = box
                    tip(box, "kvp_data_mammo")

                    def follow(*args):  # the kVp of the data chosen; a kVp they also have is kept
                        if not spinbox.winfo_exists():
                            return
                        kvps = MAMMO_KVPS.get(data.get(), MAMMO_KVPS["NCRP 147"])
                        spinbox.configure(values=kvps)
                        try:
                            current = self.d[vsexroom_key].get()
                        except TclError:
                            current = None
                        if current not in kvps:
                            self.d[vsexroom_key].set(kvps[0])

                    data.trace_add("write", follow)
        # a secondary air kerma 'Suggested' becomes 'At an angle' for a kVp, and back for a workload distribution
        unairkerv = self.d.get(f"unairkerv {e}{nr}{i}")
        if self.d[radiob_w_key].get() == 2 and unairkerv is not None and unairkerv.get() == 1:
            self.unairk(e, nr, i)
        else:
            self.update_kerma_label(e, nr, i)

    def uns(self, e, nr, i):
        if self.d[f"radiob_w {e}{nr}{i}"].get() != 1:
            return
        room = self.d[f"vsexroom {e}{nr}{i}"].get()
        barrier = {"floor": "Floor", "ceiling": "Ceiling"}.get(self.barrier_kind(e, nr), "")
        # Unshielded primary air kerma per patient at 1 m (mGy/patient): NCRP 147, Kirby et al. 2023, Chen et al. 2013
        kerma = PRIMARY_KERMA.get(room, "")
        # NCRP 147 primary use factors
        if room in ("Rad Room (chest bucky)", "Chest Room"):
            use = "1"  # chest image receptor
        elif room == "Rad Room (floor or other barriers)":
            use = {"Floor": "0.89", "Ceiling": ""}.get(barrier, "0.09")  # walls: cross-table 0.09 (wall No. 3: 0.02)
        elif room in KIRBY:  # the workload of each barrier already includes how often the beam points at it
            if "(all barriers)" in room or barrier == "Ceiling":
                use = ""
            else:
                use = "1" if ("(floor)" in room) == (barrier == "Floor") else ""
        elif room in CHEN:  # their table 5: floor 0.98 and cross-table wall 0.02; wall bucky 1
            if "(floor)" in room:
                use = {"Floor": "0.98", "Ceiling": ""}.get(barrier, "0.02")
            else:
                use = "1" if "(chest bucky)" in room and barrier == "" else ""
        elif barrier == "Floor":
            use = "1"
        else:
            use = ""
        for key, value in ((f"entk {e}{nr}{i}", kerma), (f"use_ent {e}{nr}{i}", use)):
            if self.d.get(key) is not None:
                self.d[key].delete(0, 'end')
                self.d[key].insert(0, value)

    def numbmater(self, e, nr, t):
        m_key = f"m {e}{nr}"
        vnumbmat_key = f"vnumbmat {e}{nr}"
        # Initialize the material count if not already present
        if m_key not in self.d:
            self.d[m_key] = 0
        selected_room = self.d[f"vselroom {t}"].get()
        # For "CT Room"
        if selected_room == "CT Room":
            if self.d[m_key] < self.d[vnumbmat_key].get():
                while self.d[m_key] < self.d[vnumbmat_key].get():
                    self.d[m_key] += 1
                    self.mater = ("Lead", "Concrete")
                    self.d[f"vmater {e}{self.d[m_key]}{nr}"] = StringVar()
                    self.d[f"mater {e}{self.d[m_key]}{nr}"] = ttk.OptionMenu(self.d[f"barrierf {e}{nr}"],
                        self.d[f"vmater {e}{self.d[m_key]}{nr}"], "Select Material", *self.mater)
                    if self.d[m_key] < 3:
                        self.d[f"matlab {e}{self.d[m_key]}{nr}"] = ttk.Label(self.d[f"barrierf {e}{nr}"],
                            text=f"#{self.d[m_key]}:")
                        self.d[f"matlab {e}{self.d[m_key]}{nr}"].grid(row=10, column=-1 + self.d[m_key], sticky="w")
                        self.d[f"mater {e}{self.d[m_key]}{nr}"].grid(row=10, column=-1 + self.d[m_key], pady=6.5, padx=25,
                            sticky="s")

            # Destroy extra widgets if material count exceeds the required number
            else:
                while self.d[m_key] > self.d[vnumbmat_key].get():
                    self.d[f"mater {e}{self.d[m_key]}{nr}"].destroy()
                    self.d[f"matlab {e}{self.d[m_key]}{nr}"].destroy()
                    self.d[m_key] -= 1

        # For "X-ray Room"
        else:
            if self.d[m_key] < self.d[vnumbmat_key].get():
                while self.d[m_key] < self.d[vnumbmat_key].get():
                    self.d[m_key] += 1
                    self.mater = ("Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass", "Wood")
                    self.d[f"vmater {e}{self.d[m_key]}{nr}"] = StringVar()
                    # Create the option menu for materials
                    self.d[f"mater {e}{self.d[m_key]}{nr}"] = ttk.OptionMenu(self.d[f"barrierf {e}{nr}"],
                                                                         self.d[f"vmater {e}{self.d[m_key]}{nr}"],
                                                                         "Select Material", *self.mater)
                    # Create label for the material entry
                    self.d[f"matlab {e}{self.d[m_key]}{nr}"] = ttk.Label(self.d[f"barrierf {e}{nr}"],
                                                                     text=f"#{self.d[m_key]}:")
                    # Grid placement logic
                    if self.d[m_key] <= 3:
                        row, col = 100, -1 + self.d[m_key]
                    else:
                        row, col = 101, -4 + self.d[m_key]
                    # Grid the label and option menu
                    self.d[f"matlab {e}{self.d[m_key]}{nr}"].grid(row=row, column=col, sticky="w")
                    self.d[f"mater {e}{self.d[m_key]}{nr}"].grid(row=row, column=col, padx=20, pady=6.5, sticky="e")
            # Destroy extra widgets if material count exceeds the required number
            else:
                while self.d[m_key] > self.d[vnumbmat_key].get():
                    self.d[f"mater {e}{self.d[m_key]}{nr}"].destroy()
                    self.d[f"matlab {e}{self.d[m_key]}{nr}"].destroy()
                    self.d[m_key] -= 1
        self.update_material_panel(e, nr, t, reset=True)

    # ===================== materials: each alone, or layers of one barrier =====================
    def _add_material_mode(self, e, nr, t):
        """Choice under the materials: each material on its own, or all of them as layers of one barrier."""
        row = 11 if self.d[f"vselroom {t}"].get() == "CT Room" else 102
        frame = self.d[f"barrierf {e}{nr}"]
        self.d[f"matmode {e}{nr}"] = StringVar(value="separate")
        label = ttk.Label(frame, text="The materials are:")
        label.grid(row=row, column=0, padx=5, pady=6.5, sticky="w")
        tip(label, "matmode")
        for column, (text, value) in enumerate((("Each one alone", "separate"),
                                                ("Layers of one barrier", "combined")), start=1):
            button = ttk.Radiobutton(frame, text=text, value=value, variable=self.d[f"matmode {e}{nr}"],
                                     command=lambda: self.update_material_panel(e, nr, t))
            button.grid(row=row, column=column, padx=5, pady=6.5, sticky="w")
            tip(button, f"matmode_{value}")
        self.update_material_panel(e, nr, t)

    @staticmethod
    def equal_shares(count):
        """Default shares (%): equal for every material, adding up to exactly 100."""
        share = round(100 / count, 1)
        return [f"{share:g}"] * (count - 1) + [f"{100 - share * (count - 1):g}"]

    def update_material_panel(self, e, nr, t, reset=False):
        """Under the materials: the planned thickness of each one (optional), and in 'layers' mode also the
        share (%) of each material and its place, from the room side to the outside."""
        key = f"matpanel {e}{nr}"
        if self.d.get(key) is not None:
            self.d[key].destroy()
            self.d[key] = None
        if f"matmode {e}{nr}" not in self.d:
            return
        layered = self.d[f"matmode {e}{nr}"].get() == "combined"
        count = self.d[f"vnumbmat {e}{nr}"].get()
        panel = ttk.Frame(self.d[f"barrierf {e}{nr}"])
        panel.grid(row=12 if self.d[f"vselroom {t}"].get() == "CT Room" else 103, column=0, columnspan=5,
                   padx=5, pady=(0, 8), sticky="w")
        self.d[key] = panel
        for o in range(1, count + 1):  # planned thicknesses survive a rebuild of the panel
            old = self.d.get(f"planned {e}{o}{nr}")
            self.d[f"planned {e}{o}{nr}"] = StringVar(value=old.get() if old is not None else "")
        if f"checkplan {e}{nr}" not in self.d:
            self.d[f"checkplan {e}{nr}"] = IntVar(value=0)
        checking = self.d[f"checkplan {e}{nr}"].get() == 1

        def check_option(row):
            button = ttk.Checkbutton(panel, text="Check the dose beyond the barrier with a planned thickness",
                                     variable=self.d[f"checkplan {e}{nr}"],
                                     command=lambda: self.update_material_panel(e, nr, t))
            button.grid(row=row, column=0, columnspan=9, sticky="w", pady=(4, 2))
            tip(button, "checkplan")

        def planned_entry(o, row, column):
            entry = ttk.Entry(panel, textvariable=self.d[f"planned {e}{o}{nr}"], width=7)
            entry.grid(row=row, column=column, padx=(6, 2), pady=2, sticky="w")
            self.d[f"planned_entry {e}{o}{nr}"] = entry
            tip(entry, "planned")
            ttk.Label(panel, text="mm", style="Muted.TLabel").grid(row=row, column=column + 1, padx=(0, 14), sticky="w")

        def existing_option(row):
            """The shielding the barrier already has: its materials, their thicknesses and where the new materials
            go. Returns the next free row of the panel."""
            self.existing_vars(e, nr)
            button = ttk.Checkbutton(panel, text="The barrier already has shielding (existing)",
                                     variable=self.d[f"existing {e}{nr}"],
                                     command=lambda: self.update_material_panel(e, nr, t))
            button.grid(row=row, column=0, columnspan=9, sticky="w", pady=(4, 2))
            tip(button, "existing")
            if self.d[f"existing {e}{nr}"].get() != 1:
                return row + 1
            box = ttk.Frame(panel)
            box.grid(row=row + 1, column=0, columnspan=9, sticky="w", padx=(24, 0), pady=(0, 4))
            head = ttk.Frame(box)
            head.grid(row=0, column=0, columnspan=6, sticky="w")
            label = ttk.Label(head, text="Existing materials, from the room side out:")
            label.pack(side=LEFT)
            tip(label, "existing_materials")
            spin = ttk.Spinbox(head, from_=1, to=EXISTING_MAX, width=4, state="readonly",
                               textvariable=self.d[f"existcount {e}{nr}"],
                               command=lambda: self.update_material_panel(e, nr, t))
            spin.pack(side=LEFT, padx=6)
            tip(spin, "existing_materials")
            materials = CT_MATERIALS if self.d[f"vselroom {t}"].get() == "CT Room" else MATERIALS
            for k in range(1, self.existing_count(e, nr) + 1):
                variable = self.d[f"existmat {e}{k}{nr}"]
                if variable.get() not in materials:
                    variable.set("Select Material")
                ttk.Label(box, text=f"#{k}").grid(row=k, column=0, sticky="w")
                menu = ttk.OptionMenu(box, variable, variable.get(), *materials)
                menu.grid(row=k, column=1, padx=(6, 2), pady=2, sticky="w")
                entry = ttk.Entry(box, textvariable=self.d[f"existmm {e}{k}{nr}"], width=7)
                entry.grid(row=k, column=2, padx=(6, 2), pady=2, sticky="w")
                self.d[f"existmm_entry {e}{k}{nr}"] = entry
                ttk.Label(box, text="mm", style="Muted.TLabel").grid(row=k, column=3, sticky="w")
                for widget in (menu, entry):
                    tip(widget, "existing_materials")
            side = ttk.Label(box, text="Put the new materials:")
            side.grid(row=EXISTING_MAX + 1, column=0, columnspan=2, sticky="w", pady=(4, 0))
            tip(side, "existing_side")
            for column, (text, value) in enumerate((("outside it", "outside"), ("on its room side", "inside")),
                                                   start=2):
                radio = ttk.Radiobutton(box, text=text, value=value, variable=self.d[f"addside {e}{nr}"])
                radio.grid(row=EXISTING_MAX + 1, column=column, columnspan=1 if column == 2 else 3, sticky="w",
                           padx=(6, 0), pady=(4, 0))
                tip(radio, "existing_side")
            return row + 2

        if not layered:
            top = existing_option(0)
            check_option(top)
            if not checking:
                return
            for k, o in enumerate(range(1, count + 1)):
                row, column = top + 1 + k // 3, (k % 3) * 3
                ttk.Label(panel, textvariable=self.d[f"vmater {e}{o}{nr}"], width=16).grid(row=row, column=column,
                                                                                         sticky="w")
                planned_entry(o, row, column + 1)
            return

        old = [self.d.get(f"share {e}{o}{nr}") for o in range(1, count + 1)]
        shares = self.equal_shares(count) if reset or None in old else [var.get() for var in old]
        heading = ttk.Label(panel, text="Layers, from the room side (inside) to the outside:", style="BL2.TLabel")
        heading.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))
        tip(heading, "layers")
        if checking:
            ttk.Label(panel, text="planned", style="Muted.TLabel").grid(row=0, column=4, columnspan=2, padx=(6, 0),
                                                                       sticky="w")
        total = ttk.Label(panel)

        def update_total(*_):
            values = [self.entry_number(f"share {e}{o}{nr}") for o in range(1, count + 1)]
            ok = None not in values and abs(sum(values) - 100) < 0.5
            total_text = f"{sum(v for v in values if v is not None):g}"
            total.configure(text=f"Total: {total_text} %" + ("" if ok else "  (must be 100 %)"),
                            style="OK.TLabel" if ok else "RL.TLabel")

        for o in range(1, count + 1):
            self.d[f"share {e}{o}{nr}"] = StringVar(value=shares[o - 1])
            place = "inside" if o == 1 else "outside" if o == count else "middle"
            ttk.Label(panel, text=f"#{o}  {place}", width=12).grid(row=o, column=0, sticky="w")
            ttk.Label(panel, textvariable=self.d[f"vmater {e}{o}{nr}"], width=18).grid(row=o, column=1, sticky="w")
            entry = ttk.Entry(panel, textvariable=self.d[f"share {e}{o}{nr}"], width=6)
            entry.grid(row=o, column=2, padx=(6, 2), pady=2, sticky="w")
            self.d[f"share_entry {e}{o}{nr}"] = entry
            tip(entry, "share")
            ttk.Label(panel, text="% of the shielding").grid(row=o, column=3, sticky="w")
            if checking:
                planned_entry(o, o, 4)
            self.d[f"share {e}{o}{nr}"].trace_add("write", update_total)
        total.grid(row=count + 1, column=1, columnspan=2, sticky="w", pady=(4, 0))
        update_total()
        if count > 1:
            reverse = ttk.Button(panel, text="⇅ Reverse order", command=lambda: self.reverse_layers(e, nr, t))
            reverse.grid(row=count + 1, column=3, sticky="w", pady=(4, 0))
            tip(reverse, "layers_reverse")
        check_option(existing_option(count + 2))

    def existing_vars(self, e, nr):
        """The values of the existing shielding of barrier e: kept while the panel is rebuilt, and saved."""
        defaults = {f"existing {e}{nr}": lambda: IntVar(value=0), f"existcount {e}{nr}": lambda: IntVar(value=1),
                    f"addside {e}{nr}": lambda: StringVar(value="outside")}
        for k in range(1, EXISTING_MAX + 1):
            defaults[f"existmat {e}{k}{nr}"] = lambda: StringVar(value="Select Material")
            defaults[f"existmm {e}{k}{nr}"] = lambda: StringVar(value="")
        for key, make in defaults.items():
            if self.d.get(key) is None:
                self.d[key] = make()

    def reverse_layers(self, e, nr, t):
        # The outside material comes inside and the other way round, each keeping its share and planned thickness
        count = self.d[f"vnumbmat {e}{nr}"].get()
        for name in ("vmater", "share", "planned"):
            values = [self.d[f"{name} {e}{o}{nr}"].get() for o in range(1, count + 1)]
            for o, value in enumerate(values[::-1], start=1):
                self.d[f"{name} {e}{o}{nr}"].set(value)

    def pres(self, e, nr, i):
        preshvar_key = f"preshvar {e}{nr}{i}"
        radbucky_key = f"radbucky {e}{nr}{i}"
        radcross_key = f"radcross {e}{nr}{i}"
        radiob_pre_key = f"radiob_pre {e}{nr}{i}"  # Unique key for radiob_pre
        self.d[radiob_pre_key] = IntVar(value=0)  # Store IntVar in dictionary
        # Check if preshielding is selected (1)
        if self.d[preshvar_key].get() == 1:
            # Create and place the 'Bucky' Radiobutton
            self.d[radbucky_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"], variable=self.d[radiob_pre_key],
                                                   text="Bucky", value=1)
            self.d[radbucky_key].grid(row=i * 12 + 6, column=3, pady=6.5, padx=5, sticky="w")
            # Create and place the 'Cross-table' Radiobutton
            self.d[radcross_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"], variable=self.d[radiob_pre_key],
                                                   text="Cross-table", value=2)
            self.d[radcross_key].grid(row=i * 12 + 6, column=4, pady=6.5, padx=5, sticky="w")
        # If preshielding is deselected (0), destroy the widgets if they exist
        elif self.d[preshvar_key].get() == 0:
            if radbucky_key in self.d and self.d[radbucky_key] is not None:
                self.d[radbucky_key].destroy()
            if radcross_key in self.d and self.d[radcross_key] is not None:
                self.d[radcross_key].destroy()

    def owork(self, e, nr, i):
        work_key = f"oworkvar {e}{nr}{i}"
        radwork_key = f"radworkl {e}{nr}{i}"
        radnumb_key = f"radnumb {e}{nr}{i}"  # Corrected key for the second radiobutton
        workv_key = f"workv {e}{nr}{i}"  # Unique key for radiob_pre
        radiob_w_key = f"radiob_w {e}{nr}{i}"
        self.d[workv_key] = IntVar(value=0)  # Store IntVar in dictionary
        # Check if the workload option is selected (1)
        if self.d[work_key].get() == 1:
            # Create the 'Write total Workload' Radiobutton
            self.d[radwork_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"], variable=self.d[workv_key],
                                                  text="Write total\nWorkload (mA∙min∙week\u207B\u00b9):", value=1,
                                                  command=lambda: self.workloadbar(e, nr, i))
            # Create the 'Number of Patients' Radiobutton
            self.d[radnumb_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"], variable=self.d[workv_key],
                                                  text="The Number of\nPatients per week:", value=2,
                                                  command=lambda: self.workloadbar(e, nr, i))
            #place them
            self.d[radwork_key].grid(row=i * 12 + 11, column=1, pady=6.5, padx=5, sticky="w")
            self.d[radnumb_key].grid(row=i * 12 + 11, column=3, pady=6.5, padx=5, sticky="w")
            tip(self.d[radwork_key], "workload_total")
            tip(self.d[radnumb_key], "workload_patients")
        # If workload is deselected (0), destroy the widgets if they exist
        elif self.d[work_key].get() == 0:
            if radwork_key in self.d and self.d[radwork_key] is not None:
                self.d[radwork_key].destroy()
            if radnumb_key in self.d and self.d[radnumb_key] is not None:
                self.d[radnumb_key].destroy()

    def workloadbar(self, e, nr, i):
        def destroy_widget(widget_key):
            if self.d.get(widget_key) is not None:
                self.d[widget_key].destroy()
        # Widget keys
        worebar_key = f"worentry {e}{nr}{i}"
        numpapwebar_key = f"numpapwe {e}{nr}{i}"
        vraworkbar_key = f"workv {e}{nr}{i}"
        radiob_w_key = f"radiob_w {e}{nr}{i}"
        # Get the value for workload type
        workload_type = self.d[vraworkbar_key].get()
        # Handle workload "Total workload"
        if workload_type == 1:
            destroy_widget(numpapwebar_key)  # Destroy patient entry if it exists
            destroy_widget(worebar_key)
            self.d[worebar_key] = ttk.Entry(master=self.d[f"barrierf {e}{nr}"], width=10)
            self.d[worebar_key].grid(row=i * 12 + 11, column=2, pady=5, padx=5, sticky="w")
            tip(self.d[worebar_key], "workload_total")
        # Handle workload "Number of Patients"
        elif workload_type == 2:
            destroy_widget(worebar_key)  # Destroy workload entry if it exists
            destroy_widget(numpapwebar_key)
            self.d[numpapwebar_key] = ttk.Entry(master=self.d[f"barrierf {e}{nr}"], width=10)
            self.d[numpapwebar_key].grid(row=i * 12 + 11, column=4, pady=5, padx=5, sticky="w")
            tip(self.d[numpapwebar_key], "workload_patients")

    def unairk(self, e, nr, i):
        # Destroy any existing widgets related to secondary barrier
        self.destroy_widgets([f"leak {e}{nr}{i}", f"side {e}{nr}{i}", f"forw {e}{nr}{i}", f"entk {e}{nr}{i}",
                              f"dbt1 {e}{nr}{i}", f"dbt2 {e}{nr}{i}", f"dbt3 {e}{nr}{i}", f"dbtlabel {e}{nr}{i}",
                              f"dbtbox {e}{nr}{i}", f"ffdm1 {e}{nr}{i}", f"ffdm2 {e}{nr}{i}", f"ffdm3 {e}{nr}{i}",
                              f"fieldframe {e}{nr}{i}", f"angleframe {e}{nr}{i}", f"angleopt {e}{nr}{i}"])
        if f"radside {e}{nr}{i}" in self.d:
            self.destroy_widgets([f"radside {e}{nr}{i}", f"radforward {e}{nr}{i}", f"radleak {e}{nr}{i}"])
        unairkerv_key = f"unairkerv {e}{nr}{i}"
        # the field of the other choice (suggested / written: only the written one has fieldF0): start afresh
        if (self.d.get(f"fieldF0 {e}{nr}{i}") is not None) != (self.d[unairkerv_key].get() == 2):
            for name in ("fieldvar", "fieldF", "fielddF", "fieldF0", "fielddF0"):
                self.d.pop(f"{name} {e}{nr}{i}", None)
        # 'At an angle' under the field belongs to a suggested air kerma of a workload distribution; the angle of a kVp
        # to a suggested air kerma: what the other choices left goes
        kvp_given = self.d.get(f"vselxray {e}{nr}{i}") is not None and self.d[f"vselxray {e}{nr}{i}"].get() == 2
        if self.d[unairkerv_key].get() != 1 or kvp_given:
            self.d.pop(f"angleon {e}{nr}{i}", None)
        if self.d[unairkerv_key].get() != 1:
            self.d.pop(f"angle {e}{nr}{i}", None)

        distribution = self.d.get(f"vsexroom {e}{nr}{i}")
        name = distribution.get() if distribution is not None else None
        self.update_kerma_label(e, nr, i)
        frame = self.d[f"barrierf {e}{nr}"]
        given_kvp = self.d.get(f"vselxray {e}{nr}{i}") is not None and self.d[f"vselxray {e}{nr}{i}"].get() == 2
        if self.d[unairkerv_key].get() == 1 and given_kvp:
            self.angle_widgets(e, nr, i)  # a kVp: the scatter at an angle (NCRP 147 Appendix C)
        elif self.d[unairkerv_key].get() == 1 and name == DBT:
            # Digital breast tomosynthesis (Yang et al. 2017): the scatter per patient of the mode
            self.d[f"dbtmode {e}{nr}{i}"] = IntVar(value=3)
            for k, text in ((1, "2D"), (2, "3D (tomosynthesis)"), (3, "2D + 3D")):
                self.create_radio_button(key=f"dbt{k} {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"], text=text,
                                         variable=self.d[f"dbtmode {e}{nr}{i}"], value=k, row=i * 12 + 7,
                                         column=k - 1, tip_key="dbt_mode")
        elif self.d[unairkerv_key].get() == 1 and name == DBT_LI2013:
            # The workload of Li et al. 2013, with the scatter of Yang et al. 2016 toward this barrier (wall / door,
            # floor, ceiling), at the average or high technique
            label = ttk.Label(frame, text="Toward the barrier\n(Yang 2016):")
            label.grid(row=i * 12 + 7, column=0, pady=6.5, padx=5, sticky="w")
            self.d[f"dbtlabel {e}{nr}{i}"] = label
            if self.d.get(f"dbtbarrier {e}{nr}{i}") is None:
                kind = self.barrier_kind(e, nr)
                self.d[f"dbtbarrier {e}{nr}{i}"] = StringVar(
                    value={"floor": "Floor", "ceiling": "Ceiling"}.get(kind, "Wall / door") + ", average technique")
            box = ttk.Combobox(frame, textvariable=self.d[f"dbtbarrier {e}{nr}{i}"], values=list(YANG2016_KERMA),
                               state="readonly", width=30)
            box.grid(row=i * 12 + 7, column=1, columnspan=2, pady=6.5, padx=5, sticky="w")
            self.d[f"dbtbox {e}{nr}{i}"] = box
            for widget in (label, box):
                tip(widget, "dbt_barrier")
        elif self.d[unairkerv_key].get() == 1 and name == JUDGE_FFDM:
            # Full-field digital mammography (Judge et al. 2013): the scatter of the unit
            if self.d.get(f"ffdmunit {e}{nr}{i}") is None:
                self.d[f"ffdmunit {e}{nr}{i}"] = IntVar(value=1)
            for k, (unit, _, _) in JUDGE_UNITS.items():
                self.create_radio_button(key=f"ffdm{k} {e}{nr}{i}", master=frame, text=unit,
                                         variable=self.d[f"ffdmunit {e}{nr}{i}"], value=k, row=i * 12 + 7,
                                         column=k - 1, tip_key="ffdm_unit")
        elif self.d[unairkerv_key].get() == 1:
            # NCRP-suggested mode: create radio buttons for different types of scatter/leakage
            self.d[f"airkerv {e}{nr}{i}"] = IntVar(value=0)

            self.create_radio_button(key=f"leak {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"],
                text="Leakage Radiation", variable=self.d[f"airkerv {e}{nr}{i}"], value=1, row=i * 12 + 7, column=0,
                command=lambda: self.leakage(e, nr, i), tip_key="leakage")

            self.create_radio_button(key=f"side {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"], text="Side-Scatter",
                variable=self.d[f"airkerv {e}{nr}{i}"], value=2, row=i * 12 + 7, column=1,
                command=lambda: self.leakage(e, nr, i), tip_key="side_scatter")

            self.create_radio_button(key=f"forw {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"],
                text="Forward/Backscatter", variable=self.d[f"airkerv {e}{nr}{i}"], value=3, row=i * 12 + 7, column=2,
                command=lambda: self.leakage(e, nr, i), tip_key="forward_scatter")

        elif self.d[unairkerv_key].get() == 2:
            # Custom input mode: create entry for secondary air kerma
            self.d[f"entk {e}{nr}{i}"] = ttk.Entry(master=self.d[f"barrierf {e}{nr}"], width=10)
            self.d[f"entk {e}{nr}{i}"].grid(row=i * 12 + 6, column=2, pady=6.5, padx=5, sticky="w")
            tip(self.d[f"entk {e}{nr}{i}"], "secondary_kerma_write")
            self.field_widgets(e, nr, i)
        self.refresh_distance(e, nr)

    def leakage(self, e, nr, i):
        airkerv_key = f"airkerv {e}{nr}{i}"
        radiob_leak_key = f"radiob_leak {e}{nr}{i}"

        # Destroy any previously created widgets
        self.destroy_widgets([f"radside {e}{nr}{i}", f"radforward {e}{nr}{i}", f"radleak {e}{nr}{i}"])

        # Check the current selection and create the corresponding radio buttons
        if self.d[airkerv_key].get() == 1:  # Leakage and side-scatter
            self.d[radiob_leak_key] = IntVar(value=0)
            self.create_radio_button(key=f"radside {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"],
                text="Leakage and Side-Scatter", variable=self.d[radiob_leak_key], value=1, row=i * 12 + 8, column=0,
                tip_key="leak_side")
            self.create_radio_button(key=f"radforward {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"],
                text="Leakage and Forward/Backscatter", variable=self.d[radiob_leak_key], value=2, row=i * 12 + 8,
                column=1, tip_key="leak_forward")
            self.create_radio_button(key=f"radleak {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"], text="Only Leakage",
                variable=self.d[radiob_leak_key], value=0, row=i * 12 + 8, column=2, tip_key="leak_only")
            # leakage only: dL; leakage and scatter: dsec
            self.d[radiob_leak_key].trace_add("write", lambda *args: self.refresh_distance(e, nr))
            self.d[radiob_leak_key].trace_add("write", lambda *args: self.field_widgets(e, nr, i))
        self.field_widgets(e, nr, i)
        self.refresh_distance(e, nr)

    def angle_widgets(self, e, nr, i):
        """A radiation type given by its kVp: the scattering angle, the leakage and the primary field that make its
        unshielded secondary air kerma (NCRP 147 Appendix C, Eq. C.2 and C.6-C.9)."""
        for name, default in (("angle", "90"), ("angleleak", 1), ("angleF", "1000"), ("angledF", "1")):
            if self.d.get(f"{name} {e}{nr}{i}") is None:
                self.d[f"{name} {e}{nr}{i}"] = IntVar(value=default) if name == "angleleak" else StringVar(value=default)
        frame = ttk.Frame(self.d[f"barrierf {e}{nr}"])
        frame.grid(row=i * 12 + 7, column=0, columnspan=6, padx=5, pady=6.5, sticky="w")
        self.d[f"angleframe {e}{nr}{i}"] = frame
        label = ttk.Label(frame, text="Scattering angle θ:")
        label.pack(side=LEFT)
        angle = ttk.Spinbox(frame, from_=ANGLES[0], to=ANGLES[1], increment=5, width=5,
                            textvariable=self.d[f"angle {e}{nr}{i}"])
        angle.pack(side=LEFT, padx=(6, 2))
        self.d[f"angle_entry {e}{nr}{i}"] = angle
        ttk.Label(frame, text="°", style="Muted.TLabel").pack(side=LEFT)
        leak = ttk.Checkbutton(frame, text="with leakage", variable=self.d[f"angleleak {e}{nr}{i}"],
                               command=lambda: self.refresh_distance(e, nr))
        leak.pack(side=LEFT, padx=(14, 0))
        field = ttk.Label(frame, text="Field size")
        field.pack(side=LEFT, padx=(14, 0))
        for name, unit in (("angleF", "cm² at"), ("angledF", "m")):
            entry = ttk.Entry(frame, textvariable=self.d[f"{name} {e}{nr}{i}"], width=6)
            entry.pack(side=LEFT, padx=(6, 2))
            self.d[f"{name}_entry {e}{nr}{i}"] = entry
            ttk.Label(frame, text=unit, style="Muted.TLabel").pack(side=LEFT)
            tip(entry, "angle_field")
        for widget in (label, angle):
            tip(widget, "scatter_angle")
        tip(leak, "angle_leakage")
        tip(field, "angle_field")

    def field_widgets(self, e, nr, i):
        """The primary field that makes the scatter (NCRP 147 4.1.7.2, Eq. C.2). Suggested secondary air kerma with
        scatter in it: next to the scatter type; it assumes the field of NCRP 147 Table 4.7 (or of the data of the
        literature), and another field scales the scatter, not the leakage. Air kerma written: under it, with the
        field the value was given for; another field scales the whole value."""
        key = f"fieldframe {e}{nr}{i}"
        for frame_key in (key, f"angleopt {e}{nr}{i}"):
            if self.d.get(frame_key) is not None:
                self.d[frame_key].destroy()
                self.d[frame_key] = None

        def value(name):
            variable = self.d.get(f"{name} {e}{nr}{i}")
            try:
                return variable.get() if variable is not None else None
            except TclError:
                return None
        kind, leak = value("airkerv"), value("radiob_leak")
        row = UNSHIELDED_SECONDARY.get(value("vsexroom"))
        written = value("unairkerv") == 2
        if written:  # the field of the distribution chosen, or else of NCRP 147 (mammography, else 1000 cm² at 1 m)
            row = row or UNSHIELDED_SECONDARY.get("Mammography Room" if self.room_type_of(nr) == "Mammography Room"
                                                  else "Rad Room (all barriers)")
        elif value("unairkerv") != 1 or row is None or not (kind in (2, 3) or (kind == 1 and leak in (1, 2))):
            return
        reference = (f"{row[2]:g}", f"{row[3]:g}")
        names = ("fieldF", "fielddF") + (("fieldF0", "fielddF0") if written else ())
        for name, default in [("fieldvar", None)] + list(zip(names, reference * 2)):
            if self.d.get(f"{name} {e}{nr}{i}") is None:
                self.d[f"{name} {e}{nr}{i}"] = IntVar(value=0) if default is None else StringVar(value=default)
        option = self.d[f"fieldvar {e}{nr}{i}"]
        if option.get() != 1:  # off: the field of the data, which follows the workload distribution
            for name, default in zip(names, reference * 2):
                self.d[f"{name} {e}{nr}{i}"].set(default)
        frame = ttk.Frame(self.d[f"barrierf {e}{nr}"])
        frame.grid(row=i * 12 + 7, column=0 if written else 3, columnspan=4 if written else 3, padx=5, pady=6.5,
                   sticky="w")
        self.d[key] = frame
        check = ttk.Checkbutton(frame, text="Field size", variable=option,
                                command=lambda: self.field_widgets(e, nr, i))
        check.pack(side=LEFT)
        state = ["!disabled"] if option.get() == 1 else ["disabled"]
        units = ("cm² at", "m", "cm² at", "m")
        tip_key = "field_size_written" if written else "field_size"
        for k, name in enumerate(names):
            if k == 2:
                ttk.Label(frame, text=",  the value is for", style="Muted.TLabel").pack(side=LEFT, padx=(4, 0))
            entry = ttk.Entry(frame, textvariable=self.d[f"{name} {e}{nr}{i}"], width=6)
            entry.pack(side=LEFT, padx=(6, 2))
            entry.state(state)
            self.d[f"{name}_entry {e}{nr}{i}"] = entry
            ttk.Label(frame, text=units[k], style="Muted.TLabel").pack(side=LEFT)
            tip(entry, tip_key)
        tip(check, tip_key)
        if not written and value("vsexroom") in SPECTRA and self.room_type_of(nr) != "Mammography Room":
            self.angle_option(e, nr, i)

    def angle_option(self, e, nr, i):
        """Under 'Field size': the scatter of the suggested air kerma at the angle given, made from the kVp spectrum of
        the workload distribution (NCRP 147 Eq. C.2, C.5), instead of 90 degrees (side-scatter) or 135 degrees
        (forward/backscatter) of Table 4.7."""
        for name, default in (("angleon", 0), ("angle", "90")):
            if self.d.get(f"{name} {e}{nr}{i}") is None:
                self.d[f"{name} {e}{nr}{i}"] = IntVar(value=default) if name == "angleon" else StringVar(value=default)
        frame = ttk.Frame(self.d[f"barrierf {e}{nr}"])
        frame.grid(row=i * 12 + 8, column=3, columnspan=3, padx=5, pady=6.5, sticky="w")
        self.d[f"angleopt {e}{nr}{i}"] = frame
        check = ttk.Checkbutton(frame, text="At an angle θ", variable=self.d[f"angleon {e}{nr}{i}"],
                                command=lambda: self.field_widgets(e, nr, i))
        check.pack(side=LEFT)
        angle = ttk.Spinbox(frame, from_=ANGLES[0], to=ANGLES[1], increment=5, width=5,
                            textvariable=self.d[f"angle {e}{nr}{i}"])
        angle.pack(side=LEFT, padx=(6, 2))
        angle.state(["!disabled"] if self.d[f"angleon {e}{nr}{i}"].get() == 1 else ["disabled"])
        self.d[f"angle_entry {e}{nr}{i}"] = angle
        ttk.Label(frame, text="°", style="Muted.TLabel").pack(side=LEFT)
        for widget in (check, angle):
            tip(widget, "angle_option")

    def _add_area_widgets(self, index, room_number, t):
        """Area classification, occupancy factor and design goal of a barrier."""
        self.title_ocupat = ttk.Label(
            master=self.d[f"barrierf {index}{room_number}"], style="BL.TLabel",
            text="Shielding Area")
        self.title_ocupat.grid(row=104, column=0, pady=6.5, padx=5, sticky="w")
        self.d[f"area {index}{room_number}"] = StringVar()
        self.d[f"area {index}{room_number}"] = ttk.Combobox(
            master=self.d[f"barrierf {index}{room_number}"],
            textvariable=self.d[f"area {index}{room_number}"],
            values=["Controlled Area", "Uncontrolled Area", "Supervised Area"], state="readonly")
        self.d[f"area {index}{room_number}"].grid(row=104, column=1, sticky="w")
        self.d[f"area {index}{room_number}"].set("Classify the area")
        tip(self.title_ocupat, "area")
        tip(self.d[f"area {index}{room_number}"], "area")
        self.d[f"area {index}{room_number}"].bind(
            "<<ComboboxSelected>>", lambda event, e=index, nr=room_number: self.set_design_goal(e, nr))

        self.d[f"vraoccup {index}{room_number}"] = IntVar(value=0)
        self.raoccup = ttk.Radiobutton(
            master=self.d[f"barrierf {index}{room_number}"],
            variable=self.d[f"vraoccup {index}{room_number}"], text="Write occupancy factor (T):",
            value=1, command=lambda e=index, nr=room_number: self.occupation3(e, nr, t))
        self.raoccup.grid(row=105, column=0, pady=6.5, padx=5, sticky="w")
        tip(self.raoccup, "occupancy_write")

        self.raseloccup = ttk.Radiobutton(
            master=self.d[f"barrierf {index}{room_number}"],
            text="or select Location\n(Suggested NCRP 147)",
            variable=self.d[f"vraoccup {index}{room_number}"], value=2,
            command=lambda e=index, nr=room_number: self.occupation3(e, nr, t))
        self.raseloccup.grid(row=106, column=0, pady=6.5, padx=5, sticky="w")
        tip(self.raseloccup, "occupancy_select")

        self.ladike = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                                text="Shielding Design\nGoal (mGy∙week\u207B\u00b9):")
        self.ladike.grid(row=107, column=0, pady=6.5, padx=5, sticky="w")
        self.d[f"dikeent {index}{room_number}"] = ttk.Entry(master=self.d[f"barrierf {index}{room_number}"], width=10)
        self.d[f"dikeent {index}{room_number}"].grid(row=107, column=1, pady=6.5, padx=5, sticky="w")
        tip(self.ladike, "design_goal")
        tip(self.d[f"dikeent {index}{room_number}"], "design_goal")

    # ===================== distances =====================
    def distance_symbol(self, e, nr, i):
        """The NCRP 147 name of the distance of radiation type i: dP (primary), dL (leakage), dS (scatter), dsec
        (leakage and scatter, dS = dL), with its subscript written d_{P}."""
        def value(name):
            variable = self.d.get(f"{name} {e}{nr}{i}")
            try:
                return variable.get() if variable is not None else None
            except TclError:
                return None
        if value("radiob_w") == 1:
            return "d_{P}"
        if value("radiob_w") != 2:
            return "d"
        if value("unairkerv") == 1 and value("vselxray") == 2:  # a kVp at an angle: scatter, with leakage if ticked
            return "d_{sec}" if value("angleleak") == 1 else "d_{S}"
        if value("unairkerv") == 1 and value("vsexroom") != DBT:
            if value("airkerv") == 1:
                return "d_{L}" if value("radiob_leak") == 0 else "d_{sec}"
            if value("airkerv") in (2, 3):
                return "d_{S}"
        return "d_{sec}"

    def distance_widgets(self, e, nr, i, row, ct=False):
        """The distance of one radiation type (or of a CT barrier) from the source to the barrier, the distance from
        the barrier to the person beyond it (one value per barrier, shown with every distance) and their sum."""
        frame = self.d[f"barrierf {e}{nr}"]
        key = lambda name: f"ct{name} {e}{nr}" if ct else f"{name} {e}{nr}{i}"
        label = theme.RichLabel(frame)  # its text, with the subscript of d: refresh_distance
        label.grid(row=row, column=0, pady=6.5, padx=5, sticky="w")
        if ct:  # the CT entry keeps its variable 'dist_var' (and the key 'dist_entry')
            variable = self.d[f"dist_var {e}{nr}"] = StringVar()
            entry = self.d[f"dist_entry {e}{nr}"] = ttk.Entry(frame, textvariable=variable, width=10)
        else:
            variable = self.d[f"entryd_var {e}{nr}{i}"] = StringVar()
            entry = self.d[f"entryd {e}{nr}{i}"] = ttk.Entry(frame, textvariable=variable, width=10)
        entry.grid(row=row, column=1, pady=6.5, padx=5, sticky="w")
        variable.trace_add("write", lambda *args: self.refresh_distance(e, nr))
        # next to the distance; in the narrower CT panel on the row below it
        place = (row + 1, 0) if ct else (row, 2)
        plus = ttk.Label(frame, style="AL.TLabel", text="+ to the person\nbeyond it (m):")
        plus.grid(row=place[0], column=place[1], pady=6.5, padx=5, sticky="w")
        beyond = ttk.Entry(frame, textvariable=self.d[f"beyond {e}{nr}"], width=6)
        beyond.grid(row=place[0], column=place[1] + 1, pady=6.5, padx=5, sticky="w")
        total = theme.RichLabel(frame, foreground=theme.MUTED)
        total.grid(row=place[0], column=place[1] + 2, pady=6.5, padx=5, sticky="w")
        self.d[key("lad")], self.d[key("labbeyond")], self.d[key("beyondentry")], self.d[key("dtotal")] = \
            label, plus, beyond, total
        for widget in (label, entry):
            tip(widget, "ct_distance" if ct else "distance")
        for widget in (plus, beyond):
            tip(widget, "beyond")
        if ct or i == 0:  # once per barrier
            self.d[f"beyond_entry {e}{nr}"] = beyond
            whole = ttk.Checkbutton(frame, variable=self.d[f"whole {e}{nr}"],
                                    text="Enter the whole distance, to the person beyond the barrier (nothing added)")
            whole.grid(row=place[0] + 1, column=0, columnspan=4, pady=(0, 6.5), padx=5, sticky="w")
            self.d[f"wholecb {e}{nr}"] = whole
            tip(whole, "whole_distance")
        self.refresh_distance(e, nr)

    def refresh_distance(self, e, nr):
        """Labels of the distances of barrier e: which distance (dP, dL, dS, dsec), what is added beyond the barrier
        and the sum, or the whole distance to the person."""
        whole = self.d.get(f"whole {e}{nr}") is not None and self.d[f"whole {e}{nr}"].get() == 1
        beyond = self.beyond_distance(e, nr)
        if self.d.get(f"ctlad {e}{nr}") is not None:  # a CT barrier
            rows = [(lambda name: f"ct{name} {e}{nr}", f"dist_var {e}{nr}", "d_{sec}", "CT Isocenter")]
        else:
            count = self.d[f"num_barriers_var {e}{nr}"].get() if f"num_barriers_var {e}{nr}" in self.d else 0
            rows = [(lambda name, i=i: f"{name} {e}{nr}{i}", f"entryd {e}{nr}{i}", self.distance_symbol(e, nr, i),
                     "Source") for i in range(count)]
        for key, entry, symbol, source in rows:
            label, total = self.d.get(key("lad")), self.d.get(key("dtotal"))
            if label is None or total is None:
                continue
            label.configure(text=f"Distance from the {source}\nto the {'Person' if whole else 'Barrier'}, {symbol} (m):")
            for name in ("labbeyond", "beyondentry"):
                widget = self.d.get(key(name))
                if widget is not None:
                    widget.grid_remove() if whole else widget.grid()
            distance = self.entry_number(entry)
            total.configure(text="" if whole or distance is None or beyond is None else
                            f"{symbol} = {distance + beyond:.2f} m")

    def set_design_goal(self, e, nr):
        # NCRP 147 shielding design goal P for the area classification
        goal = DESIGN_GOALS.get(self.d[f"area {e}{nr}"].get())
        if goal is not None:
            self.d[f"dikeent {e}{nr}"].delete(0, 'end')
            self.d[f"dikeent {e}{nr}"].insert(0, goal)

    def occupation3(self, e, nr, t):
        vra_key = f"vraoccup {e}{nr}"
        area_key = f"area {e}{nr}"
        occupentry_key = f"occupentry {e}{nr}"
        sellocation_key = f"sellocation {e}{nr}"
        barrierf_key = f"barrierf {e}{nr}"
        if self.d[f"dikeent {e}{nr}"].get() == "":
            self.set_design_goal(e, nr)
        # Destroy previous widgets if they exist
        for key in (occupentry_key, sellocation_key):
            if self.d.get(key):
                self.d[key].destroy()
        self.d[f"vselocation {e}{nr}"] = StringVar()

        if self.d[vra_key].get() == 1:
            # Entry for the occupancy factor; a controlled area (e.g. control room) has T = 1 in NCRP 147
            self.d[occupentry_key] = ttk.Entry(master=self.d[barrierf_key], width=10)
            if self.d[area_key].get() == "Controlled Area":
                self.d[occupentry_key].insert(0, "1")
            self.d[occupentry_key].grid(row=105, column=1, pady=6.5, padx=5)
            tip(self.d[occupentry_key], "occupancy_write")
        elif self.d[vra_key].get() == 2:
            # All NCRP 147 Table 4.1 locations: T depends on the location, not on the area classification
            self.d[sellocation_key] = ttk.OptionMenu(self.d[barrierf_key], self.d[f"vselocation {e}{nr}"],
                                                     "Select Location", *OCCUPANCY_LOCATIONS)
            self.d[sellocation_key].grid(row=106, column=1, pady=6.5, padx=5, sticky="w")
            self.d[sellocation_key].config(width=15)
            tip(self.d[sellocation_key], "occupancy_select")

    def create_radio_button(self, key, master, text, variable, value, row, column, command=None, tip_key=None):
        """Utility function to create and place a radio button."""
        self.d[key] = ttk.Radiobutton(master=master, text=text, variable=variable, value=value, command=command)
        self.d[key].grid(row=row, column=column, pady=6.5, padx=5, sticky="w")
        if tip_key:
            tip(self.d[key], tip_key)

    def destroy_widgets(self, keys):
        """Utility function to destroy a list of widgets if they exist."""
        for key in keys:
            if key in self.d and self.d[key] is not None:
                self.d[key].destroy()
                del self.d[key]