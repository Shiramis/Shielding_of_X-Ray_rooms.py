"""The worked examples of NCRP Report No. 147 (Section 5) as project files of the program: one file per example in
Examples/NCRP 147. Each file opens with a note giving the data of the example, which barrier is which, and the result
of NCRP 147 next to that of the program.

Run from the project folder:  python tools/ncrp147_examples.py
It builds every example, calculates it with the program, checks the results against NCRP 147, writes the files,
'NCRP 147 examples - comparison.xlsx' in the same folder (NCRP 147, the program and their difference) and
docs/images/ncrp147_examples.json (the comparison, for the user guide).

NCRP 147 gives the distance d from the source to the person beyond the barrier. The files tick 'Enter the whole
distance', so the distance entered is that d and nothing is added beyond the barrier (sheet 'Distances' of the
comparison).
"""
import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "XRIFSC_code")
FOLDER = os.path.join(ROOT, "Examples", "NCRP 147")
RESULTS = os.path.join(ROOT, "docs", "images", "ncrp147_examples.json")
COMPARISON = "NCRP 147 examples - comparison.xlsx"
# The thickness NCRP 147 tries, and the air kerma it finds beyond it (mGy/week): (section, barrier) -> (mm, dose)
TRIALS = {("5.3", "Barrier 4"): (0.8, 0.014), ("5.4", "Floor"): (72, 0.017)}

UNCONTROLLED, CONTROLLED = "Uncontrolled Area", "Controlled Area"
GOAL = {UNCONTROLLED: 0.02, CONTROLLED: 0.1}
OFFICE = "Administrative or clerical offices"  # T = 1
SCATTER = {"leakage + side-scatter": ("1", "1"), "leakage + forward/backscatter": ("1", "2"), "leakage": ("1", "0"),
           "side-scatter": ("2", "0"), "forward/backscatter": ("3", "0")}
RAD_ALL, RAD_FLOOR = "Rad Room (all barriers)", "Rad Room (floor or other barriers)"
CHEST_BUCKY, FLUORO, RAD_TUBE = "Rad Room (chest bucky)", "Fluoroscopy Tube (R&F room)", "Rad Tube (R&F room)"
METHOD = ("Method: every radiation type goes through the barrier with the transmission of its own workload "
          "distribution and its own preshielding, and the thickness is the one at which the air kerma beyond adds up "
          "to P (NCRP 147 Sections 5.3.5 and 5.4.2).")
DISTANCES = ("Distances: as NCRP 147 gives them, from the source to the person beyond the barrier (dP primary, dL "
             "leakage, dS scatter, dsec leakage and scatter): 'Enter the whole distance' is ticked, so nothing is "
             "added beyond the barrier.")


def number(value):
    return f"{round(value, 4):g}"


# ===================== building blocks, in the format of the project files =====================
def radiation(kind, distribution, d, *, use=None, kerma=None, preshielding=None, scatter=None, written=None,
              patients=None, kvp=None):
    """One radiation type of a barrier. d: NCRP 147 distance from the source to the occupied point (m).
    patients: its own number of patients per week ('Different Workload')."""
    primary = kind == "primary"
    item = {"radiob_w": "1" if primary else "2", "d": d,
            "vselxray": "2" if kvp else "1", "vsexroom": str(kvp) if kvp else distribution,
            "use_ent": use, "entk": kerma if primary else written,
            "preshvar": "1" if preshielding else "0", "radiob_pre": {"bucky": "1", "cross-table": "2"}.get(preshielding, "0"),
            "unairkerv": "0", "airkerv": "0", "radiob_leak": "0", "oworkvar": "0", "workv": None, "worentry": None,
            "numpapwe": None, "kvpdata": "NCRP 147" if kvp else None, "dbtmode": None}
    if not primary:
        if written is not None:
            item["unairkerv"] = "2"
        else:
            item["unairkerv"] = "1"
            item["airkerv"], item["radiob_leak"] = SCATTER[scatter]
    if patients is not None:
        item.update(oworkvar="1", workv="2", numpapwe=number(patients))
    return item


def primary(distribution, d, use, kerma, preshielding=None, **extra):
    return radiation("primary", distribution, d, use=use, kerma=kerma, preshielding=preshielding, **extra)


def secondary(distribution, d, scatter=None, **extra):
    return radiation("secondary", distribution, d, scatter=scatter, **extra)


def default_beyond(e):
    return {1: 1.3, 2: 0.5}.get(e, 0.3)


def barrier(e, materials, items=(), *, location=None, T=None, area=UNCONTROLLED, P=None, ct=None, planned=None):
    """Barrier e (1 floor, 2 ceiling, 3 door, 4... walls). location: NCRP 147 Table 4.1 (gives T), or T written.
    ct: NCRP 147 distance from the CT isocenter to the occupied point. planned: the thickness of each material that
    NCRP 147 tries, to check the dose beyond it. The distances are the whole distances to the person, as NCRP 147
    gives them ('Enter the whole distance')."""
    items = [dict(item) for item in items]
    for item in items:
        item["entryd"] = number(item["d"])
    return {"area": area, "vraoccup": "2" if location else "1", "occupentry": None if location else number(T),
            "vselocation": location, "dikeent": number(P if P is not None else GOAL[area]),
            "dist_var": number(ct) if ct is not None else None, "beyond": number(default_beyond(e)), "whole": "1",
            "ncrp_ct": ct,
            "materials": list(materials), "matmode": "separate", "shares": [None] * len(materials),
            "planned": [number(x) for x in planned] if planned else [""] * len(materials),
            "checkplan": "1" if planned else "0", "calculated": True, "radiation": items}


def empty():
    return {"materials": ["Select Material"], "radiation": [], "calculated": False}


def room(kind, name, barriers, patients=None, ct=None):
    """barriers: {e: barrier}; the room has at least 7."""
    count = max(7, max(barriers))
    data = {"barriers": count, "barrier_data": [barriers.get(e, empty()) for e in range(1, count + 1)],
            "room": ct if ct is not None else {"vrawork": "2", "worentry": None, "numpapwe": number(patients)}}
    return {"kind": "room", "type": kind, "name": name, "data": data, "plan": None}


# ===================== the examples of NCRP 147, Section 5 =====================
# Each: file name, title, room, what the example is about, and per barrier: (barrier, material, how it is set up,
# NCRP 147 thickness (mm), what NCRP 147 finds, tolerance (mm), or None where the program is known to differ)
EXAMPLES = []


def example(file, title, workspace, about, checks):
    EXAMPLES.append({"file": file, "title": title, "workspace": workspace, "about": about, "checks": checks})


example("5.1 Cardiac angiography", "NCRP 147 §5.1: Cardiac angiography",
        room("Fluoroscopy Room", "§5.1 Cardiac angiography",
             {4: barrier(4, ["Lead"], [secondary("Cardiac Angiography", 4.0, "leakage + forward/backscatter")],
                         location=OFFICE)}, patients=25),
        "25 patients per week, Cardiac Angiography workload distribution. Only secondary radiation: the image "
        "intensifier stops the primary beam.",
        [("Barrier 1", "Lead", "a wall to a fully occupied uncontrolled area (T = 1, P = 0.02 mGy/week), d = 4 m "
          "from the isocenter; leakage + forward/backscatter, K¹sec = 3.8 mGy/patient at 1 m (Table 4.7)",
          1.3, "K = 5.9 mGy/week, B = 3.4×10⁻³: 1.3 mm lead (Equation 4.10, Figure C.2)", 0.05)])

example("5.2 Dedicated chest unit", "NCRP 147 §5.2: Dedicated chest unit",
        room("X-Ray room", "§5.2 Dedicated chest unit",
             {4: barrier(4, ["Lead"], [primary("Chest Room", 3.0, "1", "1.2", "bucky")], location=OFFICE),
              5: barrier(5, ["Lead"], [secondary("Chest Room", 2.1, "leakage + side-scatter")], location=OFFICE)},
             patients=300),
        "300 patients per week, Chest Room workload distribution; the beam always points at the wall-mounted chest "
        "bucky (1535 cm² at 1.83 m).",
        [("Barrier 1", "Lead", "the wall behind the image receptor, primary, U = 1, K¹P = 1.2 mGy/patient, an office "
          "(T = 1, P = 0.02) at d = 3 m, wall bucky preshielding 0.85 mm lead (Table 4.6)",
          1.4, "B = 5×10⁻⁴: 2.2 mm lead in all, minus 0.85 mm = 1.4 mm (the total rounded to 2.2 mm first)", 0.1),
         ("Barrier 2", "Lead", "the adjacent wall, secondary, leakage + side-scatter 2.7×10⁻³ mGy/patient, an office "
          "at d = 2.1 m", 0.42, "K = 0.18 mGy/week, B = 0.11: 0.42 mm lead", 0.02)])

example("5.3 Radiographic room", "NCRP 147 §5.3: Radiographic room (Figures 5.1 and 5.2)",
        room("X-Ray room", "§5.3 Radiographic room", {
            1: barrier(1, ["Concrete"], [primary(RAD_FLOOR, 4.1, "1", "5.2", "bucky")], location=OFFICE),
            2: barrier(2, ["Concrete"], [secondary(RAD_ALL, 2.7, "leakage + forward/backscatter")],
                       location=OFFICE),
            4: barrier(4, ["Lead"], [primary(CHEST_BUCKY, 2.5, "1", "2.3", "bucky")], location="Staff rest rooms"),
            5: barrier(5, ["Lead"], [secondary(RAD_FLOOR, 4.5, "leakage + side-scatter"),
                                     secondary(CHEST_BUCKY, 0.8, "side-scatter"),
                                     secondary(CHEST_BUCKY, 2.5, "leakage")], location="Staff rest rooms"),
            6: barrier(6, ["Lead"], [secondary(RAD_ALL, 2.0, "leakage + side-scatter")], T=1, P=0.025),
            7: barrier(7, ["Lead"], [primary(RAD_FLOOR, 2.8, "0.09", "5.2", "cross-table"),
                                     secondary(RAD_FLOOR, 2.0, "leakage + side-scatter")], location=OFFICE,
                       planned=[0.8]),
            8: barrier(8, ["Lead"], [secondary(RAD_ALL, 1.8, "leakage + side-scatter")],
                       location="X-ray control rooms", area=CONTROLLED),
            9: barrier(9, ["Concrete"], [secondary(RAD_ALL, 3.0, "leakage + side-scatter")], location=OFFICE),
            10: barrier(10, ["Lead"], [secondary(RAD_ALL, 2.0, "leakage + side-scatter", patients=25)], T=1,
                        P=5e-4),
            11: barrier(11, ["Lead"], [secondary(RAD_ALL, 1.8, "leakage + side-scatter", patients=25)], T=1,
                        P=5e-4, area=CONTROLLED),
        }, patients=125),
        "125 patients per week in the room of Figures 5.1 and 5.2. Each barrier is one calculation of Section 5.3; "
        "the Door is not part of the example.",
        [("Floor", "Concrete", "5.3.1.1, under the table: primary Rad Room (floor), U = 1 (instead of 0.89, to be "
          "safe), K¹P = 5.2, d = 4.1 m, table bucky (72 mm concrete); an office below",
          35, "K = 39 mGy/week, B = 5.1×10⁻⁴: 107 mm concrete in all, minus 72 mm = 35 mm", 1.0),
         ("Ceiling", "Concrete", "5.3.2: secondary Rad Room (all barriers), leakage + forward/backscatter, d = 2.7 m",
          44, "K = 0.84 mGy/week, B = 2.4×10⁻²: 44 mm concrete", 1.0),
         ("Barrier 1", "Lead", "5.3.3.1, chest bucky wall behind the image receptor: primary Rad Room (chest bucky), "
          "U = 1, K¹P = 2.3, d = 2.5 m, wall bucky; a staff rest room (T = 1/5)",
          0.45, "B = 2.2×10⁻³: 1.3 mm lead in all (Figure B.2), minus 0.85 mm = 0.45 mm", 0.05),
         ("Barrier 2", "Lead", "5.3.3.2, the same wall outside the beam: the over-table tube (Rad Room floor, leakage "
          "+ side-scatter, 4.5 m), side-scatter of the chest patient (0.8 m) and leakage of the chest tube (2.5 m)",
          0.35, "K = 0.14 + 0.96 + 0.008 = 1.1 mGy/week, B = 9.1×10⁻² (P/T = 0.1); with the chest bucky "
          "transmission for all of them, to be simple and safe, 0.35 mm lead (with each source's own workload "
          "distribution and place, and 30° scatter from the chest patient: 0.3 mm)", 0.02),
         ("Barrier 3", "Lead", "5.3.4, darkroom wall: secondary, d = 2 m, T = 1, P = 0.025 mGy/week for the "
          "stored film", 0.53, "K = 1.1 mGy/week, B = 2.3×10⁻²: 0.53 mm lead (Figure C.2)", 0.03),
         ("Barrier 4", "Lead", "5.3.5, cross-table wall: primary Rad Room (floor), U = 0.09, d = 2.8 m, behind grid "
          "and cassette (0.3 mm lead), and secondary at 2 m, which does not pass through them; an office. 0.8 mm "
          "planned, as NCRP 147 tries",
          0.78, "the primary alone 0.9 − 0.3 = 0.6 mm. With the secondary radiation, each through its own thickness, "
          "0.8 mm lets 0.72 B_sec(0.8) + 7.5 B_P(0.8 + 0.3) = 0.014 mGy/week through, below 0.02, so less is "
          "enough; with all the sources of the room (also the chest bucky exposures, not given in the example) "
          "0.78 mm", ("below", 0.8)),
         ("Barrier 5", "Lead", "5.3.6, control wall: secondary, d = 1.8 m, controlled area (P = 0.1)",
          0.27, "K = 1.3 mGy/week, B = 7.7×10⁻²: 0.27 mm lead", 0.02),
         ("Barrier 6", "Concrete", "5.3.1.2, the floor away from the table: secondary, d = 3 m", 33, "K = 0.47 mGy/week, B = 4.3×10⁻²: 33 mm concrete", 1.0),
         ("Barrier 7", "Lead", "5.3.4, the film passbox: 25 patients in one day (Different Workload), "
          "P = 5×10⁻⁴ mGy for loaded cassettes, d = 2 m",
          1.3, "K = 0.21 mGy in a day, B = 2.3×10⁻³: 1.3 mm lead (Figure C.2)", 0.1),
         ("Barrier 8", "Lead", "5.3.6, loaded cassettes behind the control wall: 25 patients in one day, "
          "P = 5×10⁻⁴ mGy, d = 1.8 m", 1.3, "K = 0.26 mGy in a day, B = 1.9×10⁻³: 1.3 mm lead", 0.05)])

example("5.4 Radiographic and fluoroscopic room", "NCRP 147 §5.4: Radiographic and fluoroscopic (R&F) room",
        room("Fluoroscopy Room", "§5.4 R&F room", {
            1: barrier(1, ["Concrete"], [secondary(FLUORO, 2.4, "leakage"),
                                         secondary(FLUORO, 3.0, "forward/backscatter"),
                                         primary(RAD_FLOOR, 4.1, "1", "5.2", "bucky", patients=60),
                                         primary(RAD_TUBE, 4.1, "1", "5.9", "bucky")],
                       location=OFFICE, planned=[72]),
            4: barrier(4, ["Concrete"], [secondary(FLUORO, 2.4, "leakage"),
                                         secondary(FLUORO, 3.0, "forward/backscatter"),
                                         secondary(RAD_ALL, 4.1, "leakage", patients=60),
                                         secondary(RAD_ALL, 3.0, "side-scatter", patients=60),
                                         secondary(RAD_TUBE, 4.1, "leakage"),
                                         secondary(RAD_TUBE, 3.0, "side-scatter")],
                       location=OFFICE),
        }, patients=20),
        "The room of Figures 5.1 and 5.2 as an R&F room: 20 fluoroscopy and 60 radiographic-only patients per week, "
        "the fluoroscopy tube under the table, an office below. The room workload is the 20 fluoroscopy patients; "
        "the radiation types of the 60 radiographic patients have their own (Different Workload).",
        [("Floor", "Concrete", "5.4.2, under the table: leakage (d = 2.4 m) and forward/backscatter (3 m) of the "
          "fluoroscopy tube, which do not pass through the table bucky, and the primary beam of the over-table tube, "
          "U = 1, d = 4.1 m, behind the table bucky: Rad Room (floor) for the 60 patients and Rad Tube (R&F room) for "
          "the 20. 72 mm planned, as NCRP 147 tries",
          69, "1 + 18.6 + 7 mGy/week, each through its own thickness: 72 mm lets 0.011 + 0.002 + 0.004 = "
          "0.017 mGy/week through; a minimum of 69 mm concrete", 1.0),
         ("Barrier 1", "Concrete", "5.4.1, the floor away from the table: leakage "
          "and scatter of the fluoroscopy tube (2.4 and 3 m) and of the radiographic tube, for the 60 radiographic "
          "(Rad Room all barriers) and the 20 fluoroscopy patients (Rad Tube R&F room) (4.1 and 3 m)",
          62, "K = 1 + 0.23 + 0.063 = 1.3 mGy/week, B = 1.5×10⁻²: 62 mm concrete from Figure C.3 (65 mm from "
          "Figure 4.8c)", 4.0)])

example("5.5 Mammography", "NCRP 147 §5.5: Mammography",
        room("Mammography Room", "§5.5 Mammography", {
            3: barrier(3, ["Wood"], [secondary("Mammography Room", 2.1, written="0.036")],
                       location="Corridor doors"),
            4: barrier(4, ["Gypsum Wallboard"], [secondary("Mammography Room", 2.1, written="0.036")],
                       location=OFFICE),
        }, patients=150),
        "150 patients per week. NCRP 147 takes 3.6×10⁻² mGy per patient at 1 m from the isocenter of the unit in "
        "every direction (Section 5.5); it is written as the unshielded secondary air kerma.",
        [("Barrier 1", "Gypsum Wallboard", "an adjacent wall to an office (T = 1, P = 0.02), d = 2.1 m",
          9.8, "K = 1.2 mGy/week, B = 1.7×10⁻²: 9.8 mm gypsum wallboard (Figure C.4)", 0.3),
         ("Door", "Wood", "the door to a corridor (corridor door, T = 1/8), d = 2.1 m",
          41, "B = 0.13: 41 mm wood (Figure C.7); a 43 mm solid-core door is enough", 1.0)])

# CTDI method: K¹sec = κ (L/p) mAs nCTDI100; the program works with the DLP, K¹sec = 1.2 κbody DLP or κhead DLP
CTDI_BODY = 3e-4 * 50 / 1.35 * 250 * 0.138  # mGy per body scan at 1 m
CTDI_HEAD = 9e-5 * 20 / 1 * 300 * 0.223
example("5.6 CT, CTDI method", "NCRP 147 §5.6: Computed tomography, CTDI method",
        room("CT Room", "§5.6 CT (CTDI method)",
             {4: barrier(4, ["Lead"], location=OFFICE, ct=3.0)},
             ct={"bp_var": "60", "hp_var": "40", "dlpb_var": number(CTDI_BODY / (1.2 * 3e-4)),
                 "dlph_var": number(CTDI_HEAD / 9e-5), "kvp_var": "120",
                 "phases": {"body": ["100"], "head": ["100"]}}),
        "A multi-slice scanner at 120 kVp, 100 patients per week: 60 with one body scan (L = 50 cm, pitch 1.35, "
        "250 mAs, nCTDI100 = 0.138 mGy/mAs) and 40 with one head scan (L = 20 cm, pitch 1, 300 mAs, "
        f"0.223 mGy/mAs). NCRP 147: K¹sec = κ (L/p) mAs nCTDI100 = {CTDI_BODY:.3f} mGy per body and "
        f"{CTDI_HEAD:.3f} mGy per head scan. The program works with the DLP: the DLP entered gives the same values, "
        f"body {CTDI_BODY / (1.2 * 3e-4):.0f} mGy·cm (× 1.2 × 3×10⁻⁴), head {CTDI_HEAD / 9e-5:.0f} mGy·cm "
        "(× 9×10⁻⁵), one scan per procedure (100 %).",
        [("Barrier 1", "Lead", "a wall to an office (T = 1, P = 0.02), 3 m from the isocenter",
          1.3, "K = 3.1 mGy/week, B = 6.5×10⁻³: 1.3 mm lead (Figure A.2)", 0.05)])

example("5.6.1 CT, DLP method", "NCRP 147 §5.6.1: Computed tomography, dose-length product method",
        room("CT Room", "§5.6.1 CT (DLP method)",
             {4: barrier(4, ["Lead"], location=OFFICE, ct=3.0)},
             ct={"bp_var": "150", "hp_var": "30", "dlpb_var": "550", "dlph_var": "1200", "kvp_var": "120",
                 "phases": {"body": ["100", "40"], "head": ["100", "40"]}}),
        "150 body and 30 head procedures per week, 40 % of them repeated with contrast (100 % + 40 % = 1.4 scans per "
        "procedure), the DLP of Table 5.2 (body average 550, head 1200 mGy·cm), 120 kVp.",
        [("Barrier 1", "Lead", "an adjoining wall to a fully occupied office (T = 1, P = 0.02), 3 m from the "
          "isocenter", 1.5, "K¹sec 0.28 (body) and 0.15 (head) mGy per procedure, K = 5.2 mGy/week, "
          "B = 3.9×10⁻³: 1.5 mm lead (Figure A.2)", 0.05)])

DXA = 0.04 * 30 / 3600  # 0.04 mGy/h at 1 m, a spine and a hip scan of 15 s each
example("5.7 Bone mineral density unit", "NCRP 147 §5.7: Bone mineral density (DXA) unit",
        room("X-Ray room", "§5.7 Bone densitometry",
             {4: barrier(4, ["Lead"], [secondary(None, 1.0, written=number(DXA * 0.999), kvp=150)],
                         location=OFFICE)}, patients=60),
        "A fan beam unit: scattered air kerma rate below 0.04 mGy/h at 1 m, a spine and a hip scan of 15 s per "
        "patient, 60 patients per week, i.e. 0.5 h of scanning a week. It is written as the unshielded secondary "
        f"air kerma, 0.04 mGy/h × 30 s = {DXA:.2e} mGy per patient (just below it, as NCRP 147 says 'below'). There "
        "are no transmission data for these heavily filtered beams; as NCRP 147 suggests, those of the highest kVp "
        "are used (Give kVp: 150).",
        [("Barrier 1", "Lead", "an office (T = 1, P = 0.02) 1 m away", 0.0,
          "below 0.02 mGy/week at 1 m: no structural shielding is needed, even in the smallest room", 0.0)])


# ===================== build, check, write =====================
def main():
    os.chdir(CODE)
    sys.path.insert(0, CODE)
    main_file = os.path.join(CODE, "Shielding_of_X-Ray_rooms.py")
    namespace = {"__name__": "ncrp147_examples", "__file__": main_file}
    exec(compile(open(main_file, encoding="utf-8").read().replace("root.mainloop()", ""), main_file, "exec"),
         namespace)
    app, root = namespace["app"], namespace["root"]
    root.withdraw()
    from project import FORMAT, VERSION

    os.makedirs(FOLDER, exist_ok=True)
    rows, failed, distances = [], [], []
    for item in EXAMPLES:
        app.build_project({"format": FORMAT, "version": VERSION, "saved": "", "workspaces": [item["workspace"]]})
        t = next(iter(app.standalone))
        nr = app.d[f"nr {t}"]
        names = {app.barn[f"lab_bar {e}{nr}"].cget("text"): e for e in range(1, app.d[f"x {t}"] + 1)}
        lines = []
        for barrier_name, material, setup, ncrp, said, tolerance in item["checks"]:
            rec = app.calc[(nr, names[barrier_name])]
            assert not rec["missing"], (item["file"], barrier_name, rec["missing"])
            value = dict(rec["thickness"])[material]
            # ("below", x): NCRP 147 shows that x is enough for the sources of the example
            bound = tolerance[1] if isinstance(tolerance, tuple) else None
            ok = value < bound if bound is not None else abs(value - ncrp) <= tolerance
            shown = "no shielding needed" if value == 0 else f"{value:.2f} mm {material.lower()}"
            check = app.dose_check(nr, names[barrier_name])
            planned = check if check and check["basis"].startswith("planned") else None
            section = item["file"].split()[0]
            trial = TRIALS.get((section, barrier_name))
            if planned:
                shown += f"; the {planned['basis']} lets {planned['dose']:.3f} mGy/week through"
                ok = ok and abs(planned["dose"] - trial[1]) <= 0.003
            if not ok:
                failed.append((item["file"], barrier_name, material, ncrp, value))
            lines.append(f"• {barrier_name}: {setup}.\n   NCRP 147: {said}. Program: {shown}.")
            rows.append({"section": section, "example": item["title"].split(": ", 1)[1],
                         "barrier": barrier_name, "material": material, "setup": setup, "ncrp_text": said,
                         "ncrp": ncrp, "bound": bound, "program": value,
                         "planned": planned["basis"][len("planned "):] if planned else None,
                         "planned_dose": planned["dose"] if planned else None,
                         "ncrp_planned_dose": trial[1] if planned else None,
                         "K": rec["K_total"], "B": rec["B"]})
            print(f"{item['file']:42s} {barrier_name:10s} {material:17s} NCRP {ncrp:6.2f}  program {value:7.2f}"
                  + (f"  planned: {planned['dose']:.4f} mGy/week (NCRP {trial[1]})" if planned else ""))
        distances += barrier_distances(app, item, nr, names)
        project, _ = app.collect_project()
        project.update(title=item["title"], description="\n\n".join(
            [item["about"], "\n".join(lines), METHOD, DISTANCES]))
        path = os.path.join(FOLDER, item["file"] + ".shield")
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("project.json", json.dumps(project, indent=1, ensure_ascii=False))
    with open(RESULTS, "w", encoding="utf-8") as file:
        json.dump(rows, file, indent=1, ensure_ascii=False)
    root.destroy()
    write_comparison(rows, distances)
    print("written:", FOLDER)
    assert not failed, failed
    wrong = [row for row in distances if abs(row["d"] - row["ncrp"]) > 1e-9]
    assert not wrong, wrong


KINDS = {codes: name for name, codes in SCATTER.items()}


def barrier_distances(app, item, nr, names):
    """The distance of every radiation type of the barriers checked: NCRP 147, what is entered, what the program adds
    beyond the barrier, and the distance it calculates with."""
    rows, section = [], item["file"].split()[0]
    for barrier_name in dict.fromkeys(check[0] for check in item["checks"]):
        e = names[barrier_name]
        rec, spec = app.calc[(nr, e)], item["workspace"]["data"]["barrier_data"][e - 1]
        common = {"section": section, "example": item["title"].split(": ", 1)[1], "barrier": barrier_name,
                  "whole": rec["whole"], "beyond": rec["beyond"]}
        if rec["kind"] == "ct":
            rows.append(dict(common, radiation="Secondary (CT)", symbol="dsec (isocenter)", ncrp=spec["ncrp_ct"],
                             entered=rec["D"], d=rec["d"]))
            continue
        for k, (dist, given) in enumerate(zip(rec["distributions"], spec["radiation"]), start=1):
            if given["radiob_w"] == "1":
                kind = "Primary"
            elif given["unairkerv"] == "2":
                kind = "Secondary (K¹ written)"
            else:
                kind = KINDS[(given["airkerv"], given["radiob_leak"])].capitalize()
            rows.append(dict(common, radiation=f"#{k} {kind}", symbol=dist["symbol"], ncrp=given["d"],
                             entered=dist["D"], d=dist["d"]))
    return rows


# ===================== the comparison as an Excel workbook =====================
def write_comparison(rows, distances):
    """Examples/NCRP 147/NCRP 147 examples - comparison.xlsx: NCRP 147, the program, and their difference (formulas),
    then recalculated with Excel when it is installed, so that the file shows the values in any viewer."""
    from datetime import date
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    font = lambda **kw: Font(name="Arial", size=kw.pop("size", 10), **kw)
    value_font, formula_font = font(color="0000FF"), font(color="000000")
    head_font, head_fill = font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="14212E")
    edge = Side(style="thin", color="C9D3DE")
    border = Border(left=edge, right=edge, top=edge, bottom=edge)
    top_wrap = Alignment(vertical="top", wrap_text=True)

    def sheet(ws, title, subtitle, columns):
        ws["A1"], ws["A2"] = title, subtitle
        ws["A1"].font, ws["A2"].font = font(bold=True, size=13), font(italic=True, color="4B5866")
        for col, (heading, width) in enumerate(columns, start=1):
            cell = ws.cell(row=4, column=col, value=heading)
            cell.font, cell.fill, cell.border = head_font, head_fill, border
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            ws.column_dimensions[get_column_letter(col)].width = width
        ws.row_dimensions[4].height = 30
        ws.freeze_panes = "A5"
        ws.page_setup.orientation, ws.page_setup.paperSize = "landscape", ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0  # one page wide
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_title_rows = "4:4"

    def put(ws, row, col, value, number_format=None, cell_font=None):
        cell = ws.cell(row=row, column=col, value=value)
        cell.font, cell.border, cell.alignment = cell_font or font(), border, top_wrap
        if number_format:
            cell.number_format = number_format
        return cell

    def notes(ws, row, lines):
        for k, line in enumerate(lines):
            ws.cell(row=row + k, column=1, value=line).font = font(color="4B5866")

    made = (f"Program: Shielding of X-ray Rooms, the project files of this folder (Examples\\NCRP 147), calculated by "
            f"tools/ncrp147_examples.py on {date.today():%d/%m/%Y}. Difference = Program − NCRP 147.")
    book = Workbook()
    ws = book.active
    ws.title = "Thickness"
    sheet(ws, "Worked examples of NCRP Report No. 147 (Section 5): required thickness", made,
          [("Section", 8), ("Example", 30), ("Barrier", 10), ("Material", 15), ("What is calculated", 60),
           ("NCRP 147 (mm)", 11), ("Program (mm)", 11), ("Difference (mm)", 12), ("Difference (%)", 11),
           ("How NCRP 147 finds it", 60)])
    for r, row in enumerate(rows, start=5):
        values = [row["section"], row["example"], row["barrier"], row["material"], row["setup"]]
        for col, value in enumerate(values, start=1):
            put(ws, r, col, value)
        put(ws, r, 6, row["ncrp"], "0.00", value_font)
        put(ws, r, 7, round(row["program"], 4), "0.00", value_font)
        put(ws, r, 8, f"=G{r}-F{r}", "+0.00;-0.00;0.00", formula_font)
        put(ws, r, 9, f'=IF(F{r}=0,"",H{r}/F{r})', "+0.0%;-0.0%;0.0%", formula_font)
        text = row["ncrp_text"][0].upper() + row["ncrp_text"][1:]
        put(ws, r, 10, text + (f" (Program: {row['program']:.2f} mm, below the {row['bound']:g} mm that NCRP 147 "
                               f"shows is enough for the sources of the example.)" if row["bound"] else "."))
    last = 4 + len(rows)
    notes(ws, last + 2, [
        "Blue: values (NCRP 147: the thickness the report gives; Program: the result of the program). Black: "
        "formulas.",
        "Small differences: NCRP 147 read most thicknesses from its figures (B.2, B.3, C.2–C.4, C.7, A.2), or rounded "
        "before subtracting the preshielding (§5.2: 2.2 − 0.85 = 1.4 mm; the equation gives 2.16 − 0.85 = 1.31 mm).",
        "§5.3 Barrier 4 (cross-table wall): 0.78 mm is the report's result with all the sources of the room, which "
        "the example does not give; with its two sources the report shows that 0.8 mm is enough (sheet "
        "'Trial thickness').",
        "Every radiation type goes through the barrier with its own transmission data and preshielding (NCRP 147 "
        "§5.3.5, §5.4.2).",
        "Distances: the files enter the whole distances of NCRP 147, from the source to the person beyond the "
        "barrier (sheet 'Distances')."])

    ws = book.create_sheet("Trial thickness")
    sheet(ws, "Dose beyond the barrier with the thickness that NCRP 147 tries", made,
          [("Section", 8), ("Example", 30), ("Barrier", 10), ("Thickness tried", 18),
           ("NCRP 147 (mGy/week)", 13), ("Program (mGy/week)", 13), ("Difference (mGy/week)", 14),
           ("Difference (%)", 11)])
    trials = [row for row in rows if row["planned"]]
    for r, row in enumerate(trials, start=5):
        for col, value in enumerate([row["section"], row["example"], row["barrier"], row["planned"]], start=1):
            put(ws, r, col, value)
        put(ws, r, 5, row["ncrp_planned_dose"], "0.000", value_font)
        put(ws, r, 6, round(row["planned_dose"], 6), "0.0000", value_font)
        put(ws, r, 7, f"=F{r}-E{r}", "+0.0000;-0.0000;0.0000", formula_font)
        put(ws, r, 8, f'=IF(E{r}=0,"",G{r}/E{r})', "+0.0%;-0.0%;0.0%", formula_font)
    notes(ws, 5 + len(trials) + 1, [
        "The air kerma beyond the barrier (mGy/week, with T) for the thickness NCRP 147 tries in §5.3.5 and §5.4.2: "
        "the sum of all its radiation types, each through its own thickness. The goal is P = 0.02 mGy/week.",
        "NCRP 147 reads the transmissions from its figures B.2, B.3, C.2 and C.3."])

    ws = book.create_sheet("Distances")
    sheet(ws, "Distance from the source to the person beyond the barrier, per radiation type", made,
          [("Section", 8), ("Example", 30), ("Barrier", 10), ("Radiation type", 30), ("Symbol", 14),
           ("NCRP 147 (m)", 11), ("Source to the barrier, entered (m)", 15),
           ("+ to the person beyond it (m)", 14), ("Program d (m)", 11), ("Difference (m)", 12),
           ("How the distance is entered", 34)])
    ws.row_dimensions[4].height = 44  # three-line headings
    for r, row in enumerate(distances, start=5):
        values = [row["section"], row["example"], row["barrier"], row["radiation"], row["symbol"]]
        for col, value in enumerate(values, start=1):
            put(ws, r, col, value)
        put(ws, r, 6, row["ncrp"], "0.00", value_font)
        put(ws, r, 7, round(row["entered"], 4), "0.00", value_font)
        put(ws, r, 8, 0 if row["whole"] else round(row["beyond"], 4), "0.00", value_font)
        put(ws, r, 9, f"=G{r}+H{r}", "0.00", formula_font)
        put(ws, r, 10, f"=I{r}-F{r}", "+0.00;-0.00;0.00", formula_font)
        put(ws, r, 11, "the whole distance (nothing added)" if row["whole"] else
            f"to the barrier, + {row['beyond']:g} m beyond it")
    notes(ws, 5 + len(distances) + 1, [
        "NCRP 147 gives every distance from the source to the person beyond the barrier: dP primary, dL leakage, dS "
        "scatter (from the patient), dsec leakage and scatter (dS = dL); CT from the isocenter.",
        "The program asks for the distance from the source to the barrier and adds the distance from the barrier to "
        "the person beyond it, shown next to it and editable (NCRP 147 §4.1.2: walls 0.3 m, ceiling 0.5 m, floor "
        "1.3 m).",
        "These files tick 'Enter the whole distance': the distance entered is the whole d of NCRP 147, and nothing is "
        "added. Program d = entered + added."])

    path = os.path.join(FOLDER, COMPARISON)
    book.save(path)
    recalculate(path)


def recalculate(path):
    """Let Excel (when installed) calculate the formulas and save their values in the file."""
    import subprocess
    script = (f"$excel = New-Object -ComObject Excel.Application; $excel.Visible = $false; "
              f"$excel.DisplayAlerts = $false; $book = $excel.Workbooks.Open('{path}'); $excel.CalculateFull(); "
              f"$book.Save(); $book.Close(); $excel.Quit()")
    result = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True)
    print("recalculated with Excel" if result.returncode == 0 else
          f"not recalculated (open it in Excel): {result.stderr.strip()[:200]}")


if __name__ == "__main__":
    main()
