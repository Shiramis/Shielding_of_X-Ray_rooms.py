from tkinter import Toplevel, Label, Frame, LEFT, SOLID
from tkinter import ttk
import theme

# Short notes shown when the pointer rests on an input (NCRP Report No. 147; the User Guide has the details).
TIPS = {
    # ===== Department =====
    "num_rooms": "Number of rooms. For each: a name, its type, then Design.",
    "room_type": "X-Ray: radiography and chest rooms. Fluoroscopy: R&F, angiography, interventional.\n"
                 "CT: from the DLP. Mammography: secondary radiation only, also DBT.",
    "design_room": "Opens the room and its results. After closing it, shows it again as it was.",
    "department_name": "Shown on its tab and in the report. Double-click a tab to rename it.",
    "new_department": "Adds another department, in its own tab.",
    "room_name": "Shown on its tabs and in the report; change it at any time.",
    "export": "Saves the Excel report of the last calculation: Summary, Details and Rooms.",

    # ===== Room =====
    "num_barriers": "Arrow up: adds a wall or a door (one window per click).\nArrow down: removes the last barrier.",
    "barrier_tabs": "Double-click a tab to rename it, make it a door or a wall, or share it with another room.",
    "workload": "Weekly workload of the room, for every barrier without 'Different Workload'.",
    "workload_total": "Total workload, mA·min/week; N = Wtot / Wnorm.\n"
                      "Wnorm (NCRP 147): Rad Room 2.5 · Chest Room 0.22 · Mammography 6.7 · Cardiac 160.",
    "workload_patients": "Patients per week. NCRP 147 average / busy:\n"
                         "Rad Room 120 / 160 · Chest Room 200 / 400 · Mammography 80 / 160 · Angio 20 / 30.",

    # ===== Barrier: radiation =====
    "num_radiation": "How many workload distributions reach this barrier. Their air kerma values are added.",
    "radiation_type": "Primary: the beam is aimed at the barrier. Secondary: leakage and scatter only.",
    "radiation_type_mammo": "In mammography every barrier is secondary (NCRP 147).",
    "distance": "From the source to the barrier (m): d_{P} primary, d_{L} leakage, d_{S} scatter, d_{sec} both.\n"
                "The distance beyond the barrier is added.",
    "whole_distance": "Ticked: type the distances all the way to the person beyond; nothing is added.",
    "beyond": "From the barrier to the person beyond it (NCRP 147 4.1.2):\n"
              "walls and doors 0.3 m · ceiling 0.5 m · floor 1.3 m (3 m storey).",
    "workload_distribution": "The workload distribution, or a single kVp.\n"
                             "NCRP 147 first; those of the literature end with their source (User Guide).",
    "kvp_data": "Transmission data: NCRP 147 (25–150 kVp) or modern DR (Li 2024, 60–120 kV).",
    "dbt_mode": "DBT scatter per patient at 1 m (Yang 2017): 2D 0.067 · 3D 0.038 · 2D + 3D 0.105 mGy.",
    "dbt_barrier": "DBT scatter toward this barrier (Yang 2016), average or high technique.",
    "ffdm_unit": "Scatter of the unit (Judge 2013), mGy/patient: GE 0.0248 · Hologic 0.018 · Philips 0.006.",
    "kvp_data_mammo": "Transmission data: NCRP 147, Mo/Mo, W/Al and W/Rh (Li 2012), W/Ag (Li 2013).\n"
                      "Write the air kerma yourself.",
    "kvp": "A single tube voltage. Write the unshielded air kerma yourself.",
    "use_factor": "Fraction of the beam aimed at this barrier.\n"
                  "NCRP 147: floor 0.89 · cross-table wall 0.09 · wall No. 3 0.02 · chest bucky 1.",
    "primary_kerma": "Unshielded primary air kerma per patient at 1 m (mGy).\n"
                     "NCRP 147: chest bucky 2.3 · floor 5.2 · R&F 5.9 · Chest Room 1.2.",
    "preshielding": "Image receptor in the beam: Bucky 0.85 mm lead · Cross-table 0.3 mm lead.\n"
                    "Primary barriers only.",
    "secondary_kerma_ncrp": "The secondary air kerma suggested for the workload distribution (NCRP 147 Table 4.7 "
                            "or the source named).",
    "secondary_kerma_write": "Your own secondary air kerma, mGy per patient at 1 m.",
    "leakage": "Leakage from the tube housing; then choose the scatter added to it.",
    "side_scatter": "Side-scatter only (90°): walls beside the patient.",
    "forward_scatter": "Forward/backscatter only: floor and ceiling.",
    "leak_side": "Leakage + side-scatter: the usual choice for walls and doors.",
    "leak_forward": "Leakage + forward/backscatter: the usual choice for floor and ceiling.",
    "leak_only": "Leakage only.",
    "different_workload": "This radiation type has its own workload, not the room's.",
    "field_size": "Your field F (cm²) at d_{F} (m), e.g. the receptor at the SID.\n"
                  "The scatter is scaled from the field shown (NCRP 147 Table 4.7); the leakage is not.",
    "field_size_written": "Your field F (cm²) at d_{F} (m), and the field your value was given for.\n"
                          "The value is scaled by the ratio of the two (NCRP 147 Eq. C.2).",

    # ===== Barrier: materials, area and result =====
    "matmode": "Each one alone: alternatives. Layers of one barrier: all together.",
    "matmode_separate": "The thickness of each material if it were the only one (lead OR concrete).",
    "matmode_combined": "One barrier of all the materials (concrete AND lead); #1 on the room side.",
    "layers": "#1 faces the room, the last is outside. The order counts.",
    "share": "The share (%) of the shielding this layer gives; the shares add up to 100 %.",
    "checkplan": "Type the thicknesses you will install: the dose beyond is checked against P.",
    "planned": "The thickness you will install (mm). Leave empty a material that will not be there.",
    "existing": "The barrier already has shielding (a slab, a wall, lead): you get what to add.",
    "existing_materials": "The existing materials, from the room side out, and their thicknesses (mm).",
    "existing_side": "Where the new materials go. The order counts: if not decided, calculate both and take the "
                     "larger.",
    "far_area": "Also protect an area further away, e.g. an office across a corridor (NCRP 147 4.1.3).",
    "far_distance": "How much further from the source its person is (m), e.g. the corridor width.",
    "far_location": "What the further area is; it gives T (NCRP 147 Table 4.1).",
    "far_goal": "Its classification, which gives P.",
    "shielding_height": "How high the shielding goes (NCRP 147 2.3.6): 2.1 m · darkroom 2.5 m · to the ceiling "
                        "when the ceiling is shielded.",
    "check_patients": "How many patients (CT: procedures) per week the barrier allows as built (NCRP 147 6.3.3).",
    "view_walls": "Materials: walls in the colours of their materials.\nDose beyond vs goal P: green met, red exceeded.",
    "view_radiation": "Weekly air kerma around the source (log scale); lines at 0.02 and 0.1 mGy/week.",
    "view_list": "Every barrier with its materials, thicknesses and dose beyond. Pick one to mark it on the plan.",
    "layers_reverse": "Swaps inside and outside, each layer keeping its share.",
    "materials": "Number of materials; you get one thickness for each.",
    "area": "The area beyond the barrier: controlled P = 0.1, uncontrolled P = 0.02 mGy/week.",
    "occupancy_write": "Occupancy factor T (NCRP 147 Table 4.1):\n"
                       "offices 1 · exam rooms 1/2 · corridors 1/5 · corridor doors 1/8 · toilets, storage 1/20 · "
                       "outdoors 1/40.",
    "occupancy_select": "The location beyond the barrier; it gives T (NCRP 147 Table 4.1).",
    "design_goal": "P, mGy/week: controlled 0.1 · uncontrolled 0.02 (NCRP 147). Type a lower national value if "
                   "needed.",
    "calculate_all": "Calculates every barrier of the room and lists what is missing.",
    "calculate": "Calculates the thickness of each material. Anything missing is shown in red.",

    # ===== CT =====
    "ct_body": "Body CT procedures per week.",
    "ct_head": "Head CT procedures per week.",
    "ct_dlp_body": "DLP of one body scan, mGy·cm (NCRP 147: 550).",
    "ct_dlp_head": "DLP of one head scan, mGy·cm (NCRP 147: 1200).",
    "ct_phases": "Scans per procedure: the % of procedures with each scan.\nNCRP 147: 100 % + 40 % = 1.4.",
    "ct_kvp": "120 or 140 kVp (NCRP 147 CT data).",
    "ct_distance": "From the isocenter to the barrier, d_{sec} (m); the distance beyond it is added.",
    "ct_materials": "NCRP 147 has CT data for lead and concrete.",

    # ===== Floor plan and 2D / 3D view =====
    "floor_plan": "Load the drawing, trace the walls, place the source: distances, T and P are filled in.",
    "view_3d": "The rooms in 2D and 3D, with their materials and the dose beyond each barrier.",
    "view_refresh": "Redraws with the latest results.",
    "plan_load": "A PDF, PNG or JPG drawing; then set its scale.",
    "plan_height": "Floor-to-ceiling height (m).",
    "plan_floor_to_floor": "From this floor to the floor above (m), 3 to 5 m; it places the people above and below.",
    "plan_source_height": "Height of the source (CT: isocenter) above the floor (m).",
    "plan_select": "Click a wall or a door to set what is beyond it.",
    "plan_outline": "Click the corners in order; Enter or the first corner closes the room.",
    "plan_source": "Click where the source is (CT: isocenter).",
    "plan_door": "Click the two edges of a door on a wall.",
    "plan_remove_door": "Removes the selected door from the plan.",
    "plan_scale": "Click two points of known distance and type it (m).",
    "plan_clear": "Removes the traced walls and doors of this room.",
    "plan_beyond": "What is beyond the wall: it gives T and a suggested P.",
    "plan_primary": "Tick if the beam is aimed at this wall.",
    "plan_apply": "Writes the distance, T and P into this barrier.",
    "plan_apply_all": "Writes every wall, door, floor and ceiling into the room.",
}


class ToolTip:
    """Small note window that appears while the pointer rests on a widget."""

    def __init__(self, widget, text, delay=400, where=None):
        self.widget = widget
        self.text = text
        self.where = where  # shown only where this says (e.g. on the tabs of a notebook, not on what they show)
        self.delay = delay
        self.tip = None
        self.after_id = None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")
        widget.bind("<Destroy>", self.hide, add="+")

    def schedule(self, event=None):
        self.cancel()
        self.after_id = self.widget.after(self.delay, self.show)

    def cancel(self):
        if self.after_id is not None:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def show(self):
        self.after_id = None
        if self.tip is not None or not self.widget.winfo_exists() or (self.where is not None and not self.where()):
            return
        self.tip = Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        if theme.SUBSCRIPT.search(self.text):
            self.rich_note()
        else:
            Label(self.tip, text=self.text, justify=LEFT, background="#fff8d6", foreground="#171719",
                  relief=SOLID, borderwidth=1, wraplength=theme.px(420), font=theme.BASE, padx=8, pady=6).pack()
        # Place next to the pointer, kept inside the screen
        self.tip.update_idletasks()
        width, height = self.tip.winfo_reqwidth(), self.tip.winfo_reqheight()
        x = min(self.widget.winfo_pointerx() + 16, self.widget.winfo_screenwidth() - width - 4)
        y = self.widget.winfo_pointery() + 14
        if y + height > self.widget.winfo_screenheight():
            y -= height + 28
        self.tip.wm_geometry(f"+{x}+{y}")

    def rich_note(self):
        """The note with subscripts (d_{P}), wrapped like the label of the other notes. Its size comes from the font,
        not from the window (a Text would measure its lines before the window has its width)."""
        box = Frame(self.tip, background="#fff8d6", highlightthickness=1, highlightbackground="#171719")
        theme.RichLabel(box, text=self.text, foreground="#171719", background="#fff8d6",
                        wraplength=theme.px(420)).pack(padx=8, pady=6)
        box.pack()

    def hide(self, event=None):
        self.cancel()
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


def tip(widget, key, where=None):
    """Attach the guidance note TIPS[key] to a widget (where: shown only where this says). Labels get a '?' pointer
    as a hint."""
    ToolTip(widget, TIPS[key], where=where)
    if isinstance(widget, (ttk.Label, Label, theme.RichLabel)):
        widget.configure(cursor="question_arrow")
    return widget
