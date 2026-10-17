from tkinter import Toplevel, Label, LEFT, SOLID
from tkinter import ttk
import theme

# Guidance notes shown when the pointer rests on an input. Values follow NCRP Report No. 147
# (the same data the program reads from "Data Shielding.xlsx").
TIPS = {
    # ===== Department =====
    "num_rooms": "Number of rooms in the department.\n"
                 "For each room: write a description, choose the room type and press Design.",
    "room_type": "X-Ray room: radiography, R&F, chest, angiography.\n"
                 "CT Room: secondary radiation from DLP (NCRP 147 CT method).\n"
                 "Mammography Room: secondary radiation only. NCRP 147 assumes the image receptor "
                 "stops the primary beam.",
    "design_room": "Opens the room's barriers on the left and its results tab on the right.\n"
                   "If you closed the room with X, this shows it again with all inputs kept.",
    "department_name": "Name of the department, shown on its tab and in the exported report.\n"
                       "You can change it at any time. Tip: double-click any tab to rename it.",
    "new_department": "Adds another department, in its own tab, with its own rooms.",
    "room_name": "Name of the room, shown on its tab, its results tab and in the report.\n"
                 "You can change it at any time, also after Design.",
    "export": "Saves a complete Excel report:\n"
              "  Summary: one row per barrier with P, ΣK, B and the thickness of each material\n"
              "  Details: every radiation type with N, U, T, K¹, d and K\n"
              "  Rooms: room type, workload and CT data\n"
              "The report uses the last calculation of each barrier (press Calculate first).",

    # ===== Room =====
    "num_barriers": "Number of barriers in the room.\n"
                    "The first three are always Floor, Ceiling and Door; the rest are walls (Barrier 1, 2, ...).",
    "workload": "Weekly workload of the room. It applies to every barrier unless a barrier has "
                "'Different Workload' ticked.",
    "workload_total": "Total workload Wtot (mA·min/week).\n"
                      "The program finds patients/week as N = Wtot / Wnorm.\n"
                      "Wnorm per patient (NCRP 147, mA·min/patient):\n"
                      "  Rad Room (chest bucky) 0.6 · Rad Room (floor/other) 1.9\n"
                      "  Rad Room (all barriers) 2.5 · Chest Room 0.22\n"
                      "  Fluoroscopy Tube (R&F) 13 · Rad Tube (R&F) 1.5\n"
                      "  Mammography 6.7 · Cardiac Angio 160 · Peripheral Angio 64\n"
                      "With 'Give kVp' the program uses Wnorm = 2.5.",
    "workload_patients": "Number of patients per week N (40-h week).\n"
                         "NCRP 147 typical values (average / busy):\n"
                         "  Rad Room 120 / 160 · Chest Room 200 / 400\n"
                         "  Fluoroscopy Tube (R&F) 20 / 30 · Rad Tube (R&F) 25 / 40\n"
                         "  Mammography 80 / 160\n"
                         "  Cardiac Angio 20 / 30 · Peripheral Angio 20 / 30",

    # ===== Barrier: radiation =====
    "num_radiation": "How many workload distributions irradiate this barrier.\n"
                     "Example: a wall that is primary for the chest bucky and secondary for the table.\n"
                     "Their air kerma values are added: K = Σ N·U·T·K¹ / d².",
    "radiation_type": "Primary: the useful beam is aimed at this barrier (e.g. floor, chest bucky wall).\n"
                      "Secondary: only leakage and scatter reach it.",
    "radiation_type_mammo": "Mammography: every barrier is secondary.\n"
                            "NCRP 147 assumes the image receptor intercepts the primary beam, "
                            "so only scatter and leakage are shielded.",
    "distance": "Distance d (m) from the X-ray source (focal spot) to the barrier.\n"
                "The program adds the NCRP 147 distance to the occupied point beyond the barrier:\n"
                "  walls and door +0.3 m · floor +1.7 m · ceiling +0.5 m",
    "workload_distribution": "Choose the NCRP 147 workload distribution (room type), or give the kVp.\n"
                             "It sets Wnorm, the unshielded air kerma and the transmission parameters "
                             "(α, β, γ) used for the thickness.",
    "kvp": "Tube voltage (kVp) for a single-kVp transmission curve.\n"
           "Primary: 25–150 kVp. Secondary: 30, 50, 70, 100, 125 or 150 kVp.\n"
           "With kVp you must write the unshielded air kerma yourself.",
    "set_calc": "The transmission parameters (α, β, γ) of the distribution ticked here are used to find the "
                "thickness from B = P / ΣK.\n"
                "Tick the distribution that gives the most air kerma, or the most penetrating one "
                "for a conservative result. Only one can be ticked per barrier.",
    "use_factor": "Use factor U: fraction of the primary beam aimed at this barrier.\n"
                  "NCRP 147 (Rad Room): Floor 0.89 · Cross-table wall 0.09 · Wall No. 3 0.02\n"
                  "Chest image receptor (chest bucky distribution) 1.\n"
                  "Filled in when you pick the room: walls get 0.09; change it to 0.02 for wall No. 3.\n"
                  "The ceiling is normally not a primary barrier. For secondary barriers U = 1.",
    "primary_kerma": "K¹P: unshielded primary air kerma per patient at 1 m (mGy/patient).\n"
                     "NCRP 147: Rad Room (chest bucky) 2.3 · Rad Room (floor/other) 5.2\n"
                     "Rad Tube (R&F) 5.9 · Chest Room 1.2\n"
                     "Filled in automatically when you pick one of these rooms.",
    "preshielding": "Preshielding: attenuation by the image receptor before the barrier (NCRP 147). "
                    "It is subtracted from the calculated thickness.\n"
                    "  Bucky (table or wall bucky): 0.85 mm lead / 72 mm concrete / 7 mm steel\n"
                    "  Cross-table (grid and cassette only): 0.3 mm lead / 30 mm concrete / 2 mm steel\n"
                    "Use only for primary barriers behind the image receptor.",
    "secondary_kerma_ncrp": "Use the NCRP 147 unshielded secondary air kerma per patient at 1 m (K¹sec) "
                            "for the selected workload distribution.\n"
                            "Example, Mammography Room: side-scatter 0.011, leakage + forward/backscatter "
                            "0.049 mGy/patient.",
    "secondary_kerma_write": "Write your own unshielded secondary air kerma K¹sec "
                             "(mGy per patient at 1 m).",
    "leakage": "Leakage from the tube housing.\n"
               "Then choose whether to add side-scatter or forward/backscatter to it.\n"
               "Walls beside the patient: 'Leakage and Side-Scatter'.\n"
               "Floor/ceiling in line with the beam: 'Leakage and Forward/Backscatter'.",
    "side_scatter": "Side-scatter (about 90°) from the patient only. Use for walls beside the patient.",
    "forward_scatter": "Forward scatter and backscatter only (in line with the beam), e.g. floor and ceiling.",
    "leak_side": "Leakage + side-scatter (K¹sec). Usual choice for walls and doors.",
    "leak_forward": "Leakage + forward/backscatter (K¹sec). Usual choice for floor and ceiling.",
    "leak_only": "Leakage only, without scatter.",
    "different_workload": "Tick if this workload distribution has its own workload, different from the "
                          "room workload at the top.",

    # ===== Barrier: area and result =====
    "matmode": "How the materials are calculated.\n"
               "Each one alone: the thickness of each material if it were the only one.\n"
               "Layers of one barrier: all the materials together, each giving its share of the shielding.",
    "matmode_separate": "The thickness of each material if it were the only material of the barrier "
                        "(e.g. lead OR concrete).",
    "matmode_combined": "One barrier made of all the selected materials (e.g. concrete AND lead).\n"
                        "Give each material's share of the shielding and put them in order: #1 is on the room "
                        "side (inside), the last one outside. The order counts, because the first layers "
                        "harden the beam.",
    "layers": "#1 faces the room and the source, the last material is outside.\n"
              "Change the order by choosing the materials in the menus above, or press 'Reverse order'.",
    "share": "Share of the shielding (of the attenuation) that this material gives, in %.\n"
             "All shares must add up to 100 %. Default: equal shares.",
    "checkplan": "Tick to enter the thicknesses you plan to install and check them: the results, the 2D / 3D view "
                 "and the report then show the weekly dose beyond the barrier and whether it meets the goal P.\n"
                 "Not ticked: only the required thickness is calculated.",
    "planned": "The thickness you plan to install, in mm.\n"
               "Every material you give a planned thickness is taken as installed: together they cut the "
               "radiation, one after the other from the room side out. Leave a material empty if it will not be "
               "there. The results, the 2D / 3D view and the report show the weekly dose beyond the barrier and "
               "whether it meets the goal P.",
    "view_walls": "Materials: each wall in the colours of its materials (planned ones, or else the required ones). "
                  "Bands across a wall are layers, stripes along it are materials that are each enough alone.\n"
                  "Dose beyond vs goal P: green when the barrier meets the goal P, red when it exceeds it.",
    "view_radiation": "Shows the radiation: the weekly air kerma (mGy/week, log scale) around the source. It "
                      "falls with the distance and drops at each wall it crosses by all the materials of that wall "
                      "(planned thicknesses, or the required ones), the walls of the other rooms included. The "
                      "lines mark 0.02 and 0.1 mGy/week (NCRP 147 goals, with T = 1).",
    "view_list": "Every barrier of the rooms shown: its materials (from the room side out), the required and the "
                 "planned thickness of each one and the weekly dose beyond it.\n"
                 "Pick a barrier to mark it on the 2D plan; click a wall on the plan to find it here.",
    "layers_reverse": "Puts the outside material inside and the other way round, each keeping its share.",
    "materials": "Number of materials to calculate. You get one thickness per material.\n"
                 "Transmission data: NCRP 147 (concrete at standard density 2.35 g/cm³).",
    "area": "Classification of the area beyond this barrier. It sets the design goal P.\n"
            "Controlled: occupied only by radiation workers (P = 0.1 mGy/week).\n"
            "Uncontrolled: everyone else, i.e. public, other staff, patients (P = 0.02 mGy/week).\n"
            "Supervised is not an NCRP 147 class; it is treated as uncontrolled.",
    "occupancy_write": "Occupancy factor T: fraction of time the most-exposed person stays beyond the barrier.\n"
                       "NCRP 147 Table 4.1:\n"
                       "  1: offices, labs, reception, attended waiting rooms, nurse stations, control rooms\n"
                       "  1/2: patient examination and treatment rooms\n"
                       "  1/5: corridors, patient rooms, staff lounges and rest rooms\n"
                       "  1/8: corridor doors\n"
                       "  1/20: public toilets, storage, unattended waiting rooms, patient holding\n"
                       "  1/40: outdoors (transient), stairways, attics, janitor's closets, parking\n"
                       "For a controlled area T = 1 is filled in (control room).",
    "occupancy_select": "Select the location beyond the barrier; T is taken from NCRP 147 Table 4.1.\n"
                        "All locations are listed, whatever the area classification.",
    "design_goal": "Shielding design goal P (air kerma, mGy/week). NCRP 147:\n"
                   "  Controlled area 0.1 mGy/week (5 mSv/year)\n"
                   "  Uncontrolled area 0.02 mGy/week (1 mSv/year)\n"
                   "Filled in when you classify the area. If your national dose constraint is lower, "
                   "enter that value instead.",
    "calculate_all": "Calculates every barrier of this room and shows, per barrier, what is still missing.",
    "calculate": "Calculates the thickness for each material:\n"
                 "B = P / ΣK, then x = (1/αγ)·ln[(B^−γ + β/α) / (1 + β/α)].\n"
                 "Anything missing appears in red in the results tab.",

    # ===== CT =====
    "ct_body": "Number of body CT procedures per week.",
    "ct_head": "Number of head CT procedures per week.",
    "ct_dlp_body": "DLP per body procedure (mGy·cm). NCRP 147 typical value: 550 mGy·cm.\n"
                   "K¹sec = 1.2 × 3×10⁻⁴ cm⁻¹ × 1.4 × DLP\n"
                   "(1.4 accounts for repeat scans with contrast).",
    "ct_dlp_head": "DLP per head procedure (mGy·cm). NCRP 147 typical value: 1200 mGy·cm.\n"
                   "K¹sec = 9×10⁻⁵ cm⁻¹ × 1.4 × DLP",
    "ct_kvp": "Tube voltage. CT transmission data (NCRP 147) are available for 120 and 140 kVp.",
    "ct_distance": "Distance (m) from the CT isocenter to the occupied point beyond the barrier.",
    "ct_materials": "CT transmission data (NCRP 147) are available for lead and concrete.",

    # ===== Floor plan and 2D / 3D view =====
    "floor_plan": "Opens the floor plan: load the architect's drawing (PDF, PNG, JPG), trace the walls, place the "
                  "source and choose what is beyond each wall.\n"
                  "The program computes the distances, suggests T and P (NCRP 147) and fills in the barriers.",
    "view_3d": "Shows the room (or the whole department) in 2D and 3D, with the materials of every barrier and "
               "the dose beyond it. Point at a wall to see its materials and thicknesses.\n"
               "Without a floor plan, the walls are placed at their entered distances from the source.",
    "view_refresh": "Redraws with the latest inputs and results (press Calculate in the room tabs first).",
    "plan_load": "Load the drawing of the room or department: PDF (choose the page), PNG or JPG.\n"
                 "Then set its scale with two points of known distance.",
    "plan_height": "Floor-to-ceiling height of the room, used for the 3D view and the ceiling distance.",
    "plan_source_height": "Height of the source (CT: isocenter) above the floor.\n"
                          "Floor distance = this height; ceiling distance = room height − this height.",
    "plan_select": "Click a wall or the door to choose what is beyond it and see the suggested values.",
    "plan_outline": "Click the corners of the room in order; click the first corner or press Enter to close.\n"
                    "Each wall becomes a barrier: the first wall is Barrier 1, the next Barrier 2, ...",
    "plan_source": "Click the position of the X-ray source (CT: isocenter, mammography: the unit).\n"
                   "Distances to every wall are measured from here.",
    "plan_door": "Click the two edges of the door on a wall. The door is the 'Door' barrier of the room.",
    "plan_scale": "Click two points whose real distance you know (e.g. a dimension line) and type it in metres.\n"
                  "Without a drawing, the grid is 1 m.",
    "plan_clear": "Removes the traced walls and door of this room.",
    "plan_beyond": "What is on the other side (NCRP 147 Table 4.1). It sets the occupancy factor T and a "
                   "suggested area classification (P). Only X-ray control rooms are suggested as controlled.",
    "plan_primary": "Tick if the useful beam is aimed at this wall (e.g. the chest bucky wall). "
                    "Otherwise the wall is secondary.",
    "plan_apply": "Writes the distance, location (T) and area (P) into this barrier of the room tab.",
    "plan_apply_all": "Writes every wall, the door, the floor and the ceiling into the room tab.\n"
                      "Barriers are added to the room if the plan has more walls.",
}


class ToolTip:
    """Small note window that appears while the pointer rests on a widget."""

    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
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
        if self.tip is not None or not self.widget.winfo_exists():
            return
        self.tip = Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
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

    def hide(self, event=None):
        self.cancel()
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


def tip(widget, key):
    """Attach the guidance note TIPS[key] to a widget. Labels get a '?' pointer as a hint."""
    ToolTip(widget, TIPS[key])
    if isinstance(widget, (ttk.Label, Label)):
        widget.configure(cursor="question_arrow")
    return widget
