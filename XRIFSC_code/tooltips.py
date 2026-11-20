from tkinter import Toplevel, Label, Frame, LEFT, SOLID
from tkinter import ttk
import theme

# Guidance notes shown when the pointer rests on an input. Values follow NCRP Report No. 147
# (the same data the program reads from "Data Shielding.xlsx").
TIPS = {
    # ===== Department =====
    "num_rooms": "Number of rooms in the department.\n"
                 "For each room: write a description, choose the room type and press Design.",
    "room_type": "X-Ray room: radiography and chest rooms; also modern digital radiography (Kirby et al. 2023).\n"
                 "Fluoroscopy Room: R&F (fluoroscopy and radiographic tube), cardiac and peripheral angiography; "
                 "also five interventional rooms (Biondi et al. 2024).\n"
                 "CT Room: secondary radiation from DLP (NCRP 147 CT method).\n"
                 "Mammography Room: secondary radiation only (NCRP 147 assumes the image receptor stops the "
                 "primary beam); also digital breast tomosynthesis (DBT).",
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
    "num_barriers": "Number of barriers in the room: the Floor, the Ceiling, then the walls and doors (at first Door 1 "
                    "and Wall 1 to Wall 4).\n"
                    "Each click on the arrow up opens a window to add a barrier: you choose a wall or a door and may "
                    "name it (several clicks, several windows). The arrow down removes the last barrier.\n"
                    "The mouse wheel over this field does not change the barriers.",
    "barrier_tabs": "Double-click a tab (or right-click it) to rename the wall or door, or to make a wall a door and "
                    "a door a wall. Every barrier of the room needs its own name; the Floor and the Ceiling keep "
                    "theirs.\n"
                    "A new door starts as a secondary barrier of lead (mammography: of wood).",
    "workload": "Weekly workload of the room. It applies to every barrier unless a barrier has "
                "'Different Workload' ticked.",
    "workload_total": "Total workload Wtot (mA·min/week).\n"
                      "The program finds patients/week as N = Wtot / Wnorm.\n"
                      "Wnorm per patient (NCRP 147, mA·min/patient):\n"
                      "  Rad Room (chest bucky) 0.6 · Rad Room (floor/other) 1.9\n"
                      "  Rad Room (all barriers) 2.5 · Chest Room 0.22\n"
                      "  Fluoroscopy Tube (R&F) 13 · Rad Tube (R&F) 1.5\n"
                      "  Mammography 6.7 · Cardiac Angio 160 · Peripheral Angio 64\n"
                      "The distributions of the literature have their own Wnorm (User Guide, 'Workload "
                      "distributions of the literature').\n"
                      "With 'Give kVp' the program uses Wnorm = 2.5 (mammography room: 6.7).",
    "workload_patients": "Number of patients per week N (40-h week).\n"
                         "NCRP 147 typical values (average / busy):\n"
                         "  Rad Room 120 / 160 · Chest Room 200 / 400\n"
                         "  Fluoroscopy Tube (R&F) 20 / 30 · Rad Tube (R&F) 25 / 40\n"
                         "  Mammography 80 / 160\n"
                         "  Cardiac Angio 20 / 30 · Peripheral Angio 20 / 30",

    # ===== Barrier: radiation =====
    "num_radiation": "How many workload distributions irradiate this barrier.\n"
                     "Example: a wall that is primary for the chest bucky and secondary for the table.\n"
                     "Their air kerma values are added: K = Σ N·U·T·K¹ / d². Each goes through the barrier with "
                     "the transmission data of its own workload distribution and its own preshielding (NCRP 147).",
    "radiation_type": "Primary: the useful beam is aimed at this barrier (e.g. floor, chest bucky wall).\n"
                      "Secondary: only leakage and scatter reach it.",
    "radiation_type_mammo": "Mammography: every barrier is secondary.\n"
                            "NCRP 147 assumes the image receptor intercepts the primary beam, "
                            "so only scatter and leakage are shielded.",
    "distance": "Distance (m) to the barrier, named as in NCRP 147:\n"
                "  d_{P}: primary, from the focal spot\n"
                "  d_{L}: leakage, from the focal spot\n"
                "  d_{S}: scatter, from the patient\n"
                "  d_{sec}: leakage and scatter, taken the same (d_{S} = d_{L})\n"
                "The distance from the barrier to the person beyond it is added (next to it: walls and doors 0.3 m, "
                "ceiling 0.5 m, floor 1.3 m), and the sum is shown. Or tick 'Enter the whole distance' and type the "
                "distance all the way to the person.",
    "whole_distance": "Ticked: every distance of this barrier is typed all the way to the person beyond it, as "
                      "NCRP 147 gives it; nothing is added.\n"
                      "Not ticked: the distance is typed to the barrier and the distance beyond it is added.",
    "beyond": "Distance (m) from the barrier to the person to protect beyond it (NCRP 147 4.1.2); it is added to "
              "the distance from the source. One value per barrier, shown with every distance.\n"
              "  Walls and doors: 0.3 m.\n"
              "  Ceiling: 0.5 m above the floor of the room above (add the space above a suspended ceiling).\n"
              "  Floor: the person below is 1.7 m above the lower floor, i.e. floor-to-floor height − 1.7 m below "
              "this floor: 1.3 m for 3 m, 2.6 m for 4.3 m.\n"
              "The floor plan fills it in from the floor-to-floor height.",
    "workload_distribution": "X-Ray Room: choose the workload distribution in the list (those of this kind of "
                             "room). Give kVp: a single tube voltage.\n"
                             "The first group is NCRP 147. The others are from the literature and end with their "
                             "source:\n"
                             "  Kirby 2023: modern digital radiography, general and pediatric (J. Appl. Clin. Med. "
                             "Phys. 24 (2023) e13962), made into NCRP 147 data with the NCRP 147 method\n"
                             "  Chen 2013: radiographic rooms in Taiwan (Health Phys. 104 (2013) S60): their Wnorm, "
                             "K¹P, U and lead and concrete transmission; leakage and scatter made with the NCRP 147 "
                             "method\n"
                             "  Biondi 2024: interventional rooms, secondary only (Phys. Med. 125 (2024) 104509)\n"
                             "  Judge 2013: full-field digital mammography units (Br. J. Radiol. 86 (2013) 20120130); "
                             "give the workload as patients per week\n"
                             "  Yang 2017: digital breast tomosynthesis (J. Radiol. Prot. 37 (2017) 230); give the "
                             "workload as patients per week\n"
                             "  Li 2013: digital breast tomosynthesis, its workload and transmission (Med. Phys. 40 "
                             "(2013) 063901), with the scatter of Yang 2016 toward each barrier\n"
                             "  Li 2024: the table bucky of an orthopedic room (Med. Phys. 51 (2024) 8768), primary "
                             "transmission through concrete only; write K¹ and give patients per week\n"
                             "It sets Wnorm, the unshielded air kerma and the transmission parameters "
                             "(α, β, γ) used for the thickness.",
    "kvp_data": "Transmission data for this kVp:\n"
                "  NCRP 147: radiographic systems installed before 2000, 25–150 kVp.\n"
                "  DR 600 (Li et al., Med. Phys. 2024): modern digital radiography (Agfa DR 600, Monte Carlo with "
                "measured HVLs), 60–120 kV every 10 kV, with the default filtration or with 1 mm Al + 0.1 mm Cu "
                "added. Lead, concrete, gypsum wallboard and steel only.",
    "dbt_mode": "Digital breast tomosynthesis (Yang et al., J. Radiol. Prot. 37 (2017) 230, table 9).\n"
                "Unshielded scatter air kerma per patient at 1 m: both breasts, a CC and an oblique view each, one "
                "oblique toward and one away from the barrier:\n"
                "  2D 0.0669 · 3D 0.0379 · 2D + 3D 0.1048 mGy/patient.",
    "dbt_barrier": "Digital breast tomosynthesis, toward the barrier (Yang et al., Med. Phys. 43 (2016) 1096, table V): "
                   "unshielded scatter air kerma per patient at 1 m toward a wall or door, the floor or the ceiling of "
                   "a Hologic Selenia Dimensions room, for its 2D + 3D exams (mGy/patient):\n"
                   "  average technique (30 kVp W/Ag 2D + 30 kVp W/Al 3D): wall / door 0.0176 · floor 0.164 · "
                   "ceiling 0.0366\n"
                   "  high technique (35 kVp W/Ag 2D + 40 kVp W/Al 3D): wall / door 0.0332 · floor 0.307 · "
                   "ceiling 0.0733\n"
                   "They measured it with the MGH workload of Li et al. 2013, whose transmission (their table V(a)) "
                   "the workload distribution 'Digital Breast Tomosynthesis – Li 2013' uses.",
    "ffdm_unit": "Full-field digital mammography (Judge et al., Br. J. Radiol. 86 (2013) 20120130, table 1): the "
                 "maximum scatter at 1 m of one exposure × 4 exposures per patient (mGy/patient):\n"
                 "  GE Essential 0.0248 · Hologic Selenia 0.018 · Philips MDM 0.006\n"
                 "The transmission is that of the Mo/Mo beams of NCRP 147 (Simpkin), as in the article: 30 kVp for "
                 "the GE and the Hologic, 35 kVp for the Philips.",
    "kvp_data_mammo": "Transmission data for this kVp (the secondary radiation is attenuated like the primary beam):\n"
                      "  NCRP 147: its secondary data (30 kVp in mammography)\n"
                      "  Mo/Mo (NCRP 147): the mammography beams of Simpkin, 25, 30, 35 kVp\n"
                      "  W/Al (Li 2012): 25, 30, 35, 40, 45, 49 kVp · W/Rh (Li 2012): 25, 30, 35, 39 kVp\n"
                      "  W/Ag (Li 2013): 25, 30, 35, 39 kVp\n"
                      "The W beams are those of a Hologic Selenia Dimensions (2D: W/Rh, W/Ag; 3D: W/Al). Write the "
                      "unshielded air kerma yourself.",
    "kvp": "Tube voltage (kVp) for a single-kVp transmission curve.\n"
           "Primary: 25–150 kVp. Secondary: 30, 50, 70, 100, 125 or 150 kVp (mammography: those of the data chosen).\n"
           "With kVp you must write the unshielded air kerma yourself.",
    "use_factor": "Use factor U: fraction of the primary beam aimed at this barrier.\n"
                  "NCRP 147 (Rad Room): Floor 0.89 · Cross-table wall 0.09 · Wall No. 3 0.02\n"
                  "Chest image receptor (chest bucky distribution) 1.\n"
                  "Kirby 2023: 1 on its own barrier (the workload of each barrier already includes how often the "
                  "beam points at it).\n"
                  "Filled in when you pick the room: walls get 0.09; change it to 0.02 for wall No. 3.\n"
                  "The ceiling is normally not a primary barrier. For secondary barriers U = 1.",
    "primary_kerma": "K¹P: unshielded primary air kerma per patient at 1 m (mGy/patient).\n"
                     "NCRP 147: Rad Room (chest bucky) 2.3 · Rad Room (floor/other) 5.2\n"
                     "Rad Tube (R&F) 5.9 · Chest Room 1.2\n"
                     "Kirby 2023 (NCRP 147 method): DR Room chest bucky 3.05 · floor 1.22 · cross-table 0.461\n"
                     "Filled in automatically when you pick one of these rooms.",
    "preshielding": "Preshielding: attenuation by the image receptor before the barrier (NCRP 147). "
                    "Only this primary beam passes through it; the other radiation types of the barrier do not.\n"
                    "  Bucky (table or wall bucky): 0.85 mm lead / 72 mm concrete / 7 mm steel\n"
                    "  Cross-table (grid and cassette only): 0.3 mm lead / 30 mm concrete / 2 mm steel\n"
                    "Use only for primary barriers behind the image receptor.",
    "secondary_kerma_ncrp": "Use the suggested unshielded secondary air kerma per patient at 1 m (K¹sec) "
                            "of the selected workload distribution: NCRP 147, or the source named in the list.\n"
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
    "calculate": "Calculates the thickness for each material: the x at which the air kerma beyond the barrier, "
                 "Σ K·B(x + preshielding) over the radiation types, equals P. With one radiation type: B = P / K, "
                 "x = (1/αγ)·ln[(B^−γ + β/α) / (1 + β/α)].\n"
                 "Anything missing appears in red in the results tab.",

    # ===== CT =====
    "ct_body": "Number of body CT procedures per week.",
    "ct_head": "Number of head CT procedures per week.",
    "ct_dlp_body": "DLP of one body scan (one phase), mGy·cm. NCRP 147 typical value: 550 mGy·cm.\n"
                   "K¹sec per scan = 1.2 × 3×10⁻⁴ cm⁻¹ × DLP; the scans per procedure are set above.",
    "ct_dlp_head": "DLP of one head scan (one phase), mGy·cm. NCRP 147 typical value: 1200 mGy·cm.\n"
                   "K¹sec per scan = 9×10⁻⁵ cm⁻¹ × DLP; the scans per procedure are set above.",
    "ct_phases": "Scans (phases) per procedure, e.g. without and with contrast, or 3–4 phases.\n"
                 "Set how many scans a procedure can have and, for scan 1, 2, ..., the % of the procedures "
                 "that have it. Their sum / 100 is the mean number of scans per procedure.\n"
                 "NCRP 147: every procedure scanned once and 40 % again with contrast: 100 % + 40 % = 1.4.",
    "ct_kvp": "Tube voltage. CT transmission data (NCRP 147) are available for 120 and 140 kVp.",
    "ct_distance": "Distance (m) from the CT isocenter to the barrier, d_{sec}. The distance from the barrier to the "
                   "person beyond it is added (next to it: walls and doors 0.3 m, ceiling 0.5 m, floor 1.3 m), and "
                   "the sum is shown. Or tick 'Enter the whole distance' and type the distance all the way to the "
                   "person.",
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
    "plan_floor_to_floor": "From the floor of this room to the floor of the room above (NCRP 147: 3 to 5 m), "
                           "taken the same for the storey below.\n"
                           "It sets where the people are (NCRP 147 4.1.2): below, 1.7 m above the lower floor "
                           "(floor-to-floor − 1.7 m under this floor); above, 0.5 m above the floor of the room "
                           "above.",
    "plan_source_height": "Height of the source (CT: isocenter) above the floor.\n"
                          "Floor distance = this height; ceiling distance = room height − this height.",
    "plan_select": "Click a wall or a door to choose what is beyond it and see the suggested values.",
    "plan_outline": "Click the corners of the room in order; click the first corner or press Enter to close.\n"
                    "The walls traced are the walls of the room, in order: the first is Wall 1 of the room tab, "
                    "the next Wall 2, ...",
    "plan_source": "Click the position of the X-ray source (CT: isocenter, mammography: the unit).\n"
                   "Distances to every wall are measured from here.",
    "plan_door": "Click the two edges of a door on a wall. The doors traced are the doors of the room, in order: "
                 "the first is Door 1 of the room tab, the next Door 2, ...\n"
                 "To remove a door, select it and press 'Remove door' (or Delete).",
    "plan_remove_door": "Removes the selected door from the floor plan (the door of the room tab stays).",
    "plan_scale": "Click two points whose real distance you know (e.g. a dimension line) and type it in metres.\n"
                  "Without a drawing, the grid is 1 m.",
    "plan_clear": "Removes the traced walls and doors of this room.",
    "plan_beyond": "What is on the other side (NCRP 147 Table 4.1). It sets the occupancy factor T and a "
                   "suggested area classification (P). Only X-ray control rooms are suggested as controlled.",
    "plan_primary": "Tick if the useful beam is aimed at this wall (e.g. the chest bucky wall). "
                    "Otherwise the wall is secondary.",
    "plan_apply": "Writes the distance, location (T) and area (P) into this barrier of the room tab.",
    "plan_apply_all": "Writes every wall and door, the floor and the ceiling into the room tab.\n"
                      "Walls and doors are added to the room if the plan has more of them.",
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
