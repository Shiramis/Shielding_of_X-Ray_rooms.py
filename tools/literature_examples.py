"""The worked examples of the papers whose data the program offers, as project files of the program: one file per
example in Examples/Literature, each opening with a note that gives the data of the example and the result of the
paper next to that of the program.

    Yang et al. 2017 (DBT room, section 3.4), Yang et al. 2016 (DBT floor, Eq. 8-9, with the transmission of Li et
    al. 2012), Judge et al. 2013 (table 1: three FFDM units), Biondi et al. 2024 (table 4, Eq. 4: five interventional
    rooms), Li et al. 2024 (lead for a transmission of 0.001, section 3).
    Kirby et al. 2023, Chen et al. 2013 and Li et al. 2013 give no worked example; the sheet 'Data checks' compares
    values the papers give about their own data with those the program finds from its data (Chen: their table 6 and
    K1 from their table 1 with the NCRP 147 method; Li 2013: their table V(a) from the single-kVp tables of Li 2012
    and Li 2013 and the workload of their table IV(c)).

Run from the project folder:  python tools/literature_examples.py
It builds every example, calculates it with the program, checks the results against the papers, writes the files,
'Literature examples - comparison.xlsx' in the same folder (paper, program and their difference) and
docs/images/literature_examples.json (the comparison, for the user guide).
"""
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ncrp147_examples import barrier, number, primary, room, secondary, recalculate  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "XRIFSC_code")
FOLDER = os.path.join(ROOT, "Examples", "Literature")
RESULTS = os.path.join(ROOT, "docs", "images", "literature_examples.json")
COMPARISON = "Literature examples - comparison.xlsx"
OFFICE = "Administrative or clerical offices"  # T = 1
DBT = "Digital Breast Tomosynthesis – Yang 2017"  # the program's name of the DBT workload distribution
WEEKS = 52  # Biondi et al. give the workload and the goal per year

REFERENCES = {
    "Yang 2017": "Yang K, Schultz TJ, Li X, Liu B. Radiation shielding calculation for digital breast tomosynthesis "
                 "rooms with an updated workload survey. J Radiol Prot 2017;37(1):230-246.",
    "Yang 2016": "Yang K, Li X, Liu B. Scatter radiation intensities around a clinical digital breast tomosynthesis "
                 "unit and the impact on radiation shielding considerations. Med Phys 2016;43(3):1096-1110.",
    "Biondi 2024": "Biondi M, Bortoli E, Avitabile R, et al. Radiation shielding calculation for interventional "
                   "radiology: an updated workload survey using a dose monitoring software. Phys Med "
                   "2024;125:104509.",
    "Li 2024": "Li X, Marschall TA, Yang K, Liu B. Radiation shielding transmission data for modern digital "
               "radiography. Med Phys 2024;51(12):8768-8775.",
    "Kirby 2023": "Kirby KM, Schueler BA, Littrell LA, Long Z. Workload and use factor data for a modern digital "
                  "radiography system. J Appl Clin Med Phys 2023;24(5):e13962.",
    "Li 2012": "Li X, Zhang D, Liu B. Transmission of broad W/Rh and W/Al (target/filter) x-ray beams operated at 25-49 "
               "kVp through common shielding materials. Med Phys 2012;39(7):4132-4138.",
    "Li 2013": "Li X, Zhang D, Liu B. Workload and transmission data for the installation of a digital breast "
               "tomosynthesis system. Med Phys 2013;40(6):063901.",
    "Judge 2013": "Judge MA, Keavey E, Phelan N. Scatter radiation intensities around full-field digital mammography "
                  "units. Br J Radiol 2013;86(1021):20120130.",
    "Chen 2013": "Chen TR, Tyan YS, Chu CH, Wu MC, Tung CJ. Surveyed data for structural shielding calculations of "
                 "radiographic x-ray installations in Taiwan. Health Phys 2013;104(5 Suppl 2):S60-S67.",
}
JUDGE = "Digital Mammography (FFDM) – Judge 2013"  # the program's name of the FFDM workload distribution


def suggested(distribution, d, **choice):
    """A secondary radiation type with the air kerma the program suggests for the distribution: DBT (Yang et al.
    2017, dbtmode 3 = 2D + 3D) or FFDM (Judge et al. 2013, ffdmunit 1-3)."""
    item = {"radiob_w": "2", "d": d, "vselxray": "1", "vsexroom": distribution, "use_ent": None, "entk": None,
            "preshvar": "0", "radiob_pre": "0", "unairkerv": "1", "airkerv": "0", "radiob_leak": "0", "oworkvar": "0",
            "workv": None, "worentry": None, "numpapwe": None, "kvpdata": None, "dbtmode": None, "dbtbarrier": None,
            "ffdmunit": None}
    item.update({k: str(v) for k, v in choice.items()})
    return item


def department(name, rooms):
    """rooms: workspaces of standalone rooms, put together in one department."""
    return {"kind": "department", "name": name, "plan": None,
            "rooms": [{"name": r["name"], "type": r["type"], "designed": True, "data": r["data"]} for r in rooms]}


# ===================== the examples =====================
# Each: file, title, paper, workspace, what the example is about, and its checks: (room, barrier, quantity, unit,
# value of the paper, tolerance, how the paper finds it). A tolerance None: shown, not compared (with the reason).
EXAMPLES = []


def example(file, title, paper, workspace, about, checks):
    EXAMPLES.append({"file": file, "title": title, "paper": paper, "workspace": workspace, "about": about,
                     "checks": checks})


example("Yang 2017 - DBT room", "Yang et al. 2017: digital breast tomosynthesis room", "Yang 2017",
        room("Mammography Room", "Yang 2017: DBT room",
             {4: barrier(4, ["Gypsum Wallboard"], [suggested(DBT, 2.0, dbtmode=3)], location=OFFICE,
                         name="Office wall")},
             patients=100),
        "100 patients per week, every exam a 2D + 3D screening of both breasts (2 CC and 1 oblique view toward and 1 "
        "away from the barrier, in 2D and in 3D), a fully occupied office (T = 1, P = 0.02 mGy/week) 2 m from the "
        "gantry. The air kerma per view at 1 m is that of their table 9, the transmission that of their table 8 "
        "(both in the program as 'Digital Breast Tomosynthesis – Yang 2017').",
        [("Yang 2017: DBT room", "Office wall", "K", "mGy/week", 2.62, 0.01,
          "K = [200 (6.07 + 7.85)×10⁻³ + 100 (4.83×10⁻² + 1.43×10⁻² + 6.49×10⁻³ + 7.89×10⁻³)] / 2² = 2.62 mGy/week"),
         ("Yang 2017: DBT room", "Office wall", "B", "", 7.6e-3, 0.05e-3, "B = 0.02 / 2.62 = 7.6×10⁻³"),
         ("Yang 2017: DBT room", "Office wall", "Gypsum Wallboard", "mm", 23, 1.0,
          "a minimum of 23 mm gypsum, with the transmission data of table 8")])

yang2016 = secondary(None, 1.2, written="0.307", kvp=40)  # K1sec of their table V, the 40 kVp W/Al data of Li 2012
yang2016["kvpdata"] = "W/Al (Li 2012)"
example("Yang 2016 - DBT floor", "Yang et al. 2016: the floor of a DBT room", "Yang 2016",
        room("Mammography Room", "Yang 2016: DBT room", {1: barrier(1, ["Concrete"], [yang2016], T=1)}, patients=100),
        "100 patients per week, the scatter toward the floor at the high technique (35 kVp W/Ag for 2D and 40 kVp W/Al "
        "for 3D): K¹_{sec} = 3.07×10⁻¹ mGy per patient at 1 m (their table V), a fully occupied area below at the "
        "shortest distance, 1.2 m, P = 0.02 mGy/week. As the article, the transmission is that of the 40 kVp W/Al beam "
        "of Li et al. 2012 ('Give kVp': 40, W/Al (Li 2012)), and K¹_{sec} is written. In the program the same air "
        "kerma is the choice 'Floor, high technique' of the workload distribution 'Digital Breast Tomosynthesis – Li "
        "2013', which uses the transmission of the DBT workload of Li et al. 2013 instead.",
        [("Yang 2016: DBT room", "Floor", "K", "mGy/week", 21.3, 0.05, "K = 3.07×10⁻¹ / 1.2² × 100 = 21.3 mGy/week (Eq. 8)"),
         ("Yang 2016: DBT room", "Floor", "B", "", 9.4e-4, 0.05e-4, "B = 0.02 / 21.3 = 9.4×10⁻⁴ (Eq. 9)"),
         ("Yang 2016: DBT room", "Floor", "Concrete", "mm", 35, ("approximately", 3.5),
          "~35 mm concrete with the transmission of Li et al. 2012, 40 kVp W/Al: an approximate value (the Archer "
          "equation with their table I gives 32 mm)")])

# Judge et al. 2013, table 1: each unit's maximum scatter at 1 m x 40 000 exposures a year (40 patients a day, 4
# exposures, 5 days, 50 weeks), a member of the public (0.3 mGy a year, T = 1) at 1 m, Simpkin's Mo/Mo transmission
JUDGE_TABLE = [("GE Essential", 248, 1.21e-3, (21, 9, 180)), ("Hologic Selenia", 180, 1.67e-3, (19, 8, 169)),
               ("Philips MDM", 60, 5.00e-3, (18, 8, 157))]
judge_walls, judge_checks = {}, []
for k, (unit, ais, B, (gypsum, glass, wood)) in enumerate(JUDGE_TABLE, start=1):
    wall = barrier(3 + k, ["Gypsum Wallboard", "Plate Glass", "Wood"], [suggested(JUDGE, 1.0, ffdmunit=k)], T=1,
                   name=unit)
    wall["dikeent"] = f"{0.3 / WEEKS:.6g}"
    judge_walls[3 + k] = wall
    room_name = "Judge 2013: FFDM room"
    judge_checks += [(room_name, unit, "K per year", "mGy/year", ais, 1.0,
                      "annual incident scatter: the maximum scatter at 1 m × 40 000 exposures"),
                     (room_name, unit, "B", "", B, 0.006e-3 if B < 2e-3 else 0.02e-3, "B = 0.3 / AIS (Eq. 2, T = 1)"),
                     (room_name, unit, "Gypsum Wallboard", "mm", gypsum, 0.6, "gypsum plasterboard, table 1"),
                     (room_name, unit, "Plate Glass", "mm", glass, 0.6, "plate glass, table 1"),
                     (room_name, unit, "Wood", "mm", wood, 1.0, "wood, table 1")]
example("Judge 2013 - FFDM room", "Judge et al. 2013: three full-field digital mammography units", "Judge 2013",
        room("Mammography Room", "Judge 2013: FFDM room", judge_walls, patients=10000 / WEEKS),
        "Their table 1: the barrier at 1 m from each unit for a member of the public (0.3 mGy a year, T = 1), with the "
        "maximum scatter at 1 m of one exposure × 40 000 exposures a year (40 patients a day, 4 exposures each, 5 days "
        "a week, 50 weeks). In the program: the workload distribution 'Digital Mammography (FFDM) – Judge 2013' with "
        "the unit of each wall (K¹_{sec} = 4 exposures × the maximum scatter), 10 000 / 52 patients a week, P = 0.3 / 52 "
        "mGy/week. Judge et al. used Simpkin's Mo/Mo transmission without stating its kVp: 30 kVp reproduces their GE "
        "and Hologic values and 35 kVp their Philips values, which the program uses.",
        judge_checks)

# Biondi et al. 2024: table 1 (procedures in 2023), table 2 (workload), table 4 with their Eq. 4 (the NCRP 147
# secondary air kerma of cardiac or peripheral angiography, leakage + forward/backscatter, times Wsite / Wnorm)
BIONDI_ROOMS = [("Angiography", 779, 345, 1.5), ("Electrophysiology", 523, 1, 0.0), ("Haemodynamics", 1199, 150, 1.1),
                ("Neuroangiography", 172, 196, 1.3), ("Vascular Surgery", 393, 107, 1.0)]
BIONDI_NOTE = {"Neuroangiography": "table 4 gives 196 mGy/year, which is Eq. 4 with 523 patients a year (the number "
                                   "of electrophysiology in table 1), not the 172 of neuroangiography",
               "Vascular Surgery": "table 4 gives 107 mGy/year, which is Eq. 4 with 172 patients a year (the number "
                                   "of neuroangiography in table 1), not the 393 of vascular surgery"}


def biondi_room(name, patients):
    wall = barrier(4, ["Lead"], [secondary(f"{name} – Biondi 2024", 2.0, "leakage + forward/backscatter")], T=1,
                   P=1 / WEEKS, name="Wall at 2 m")
    wall["dikeent"] = f"{1 / WEEKS:.6g}"  # 1 mSv a year
    return room("Fluoroscopy Room", f"Biondi 2024: {name}", {4: wall}, patients=patients / WEEKS)


biondi_checks = []
for name, patients, kerma, lead in BIONDI_ROOMS:
    known = BIONDI_NOTE.get(name)
    biondi_checks += [(f"Biondi 2024: {name}", "Wall at 2 m", "K per year", "mGy/year", kerma, None if known else 1.0,
                       known or f"Eq. 4: Wsite / Wnorm × {patients} patients × K¹_{{sec}} / 2²"),
                      (f"Biondi 2024: {name}", "Wall at 2 m", "Lead", "mm", lead, None if known else 0.06,
                       (known + ", so its lead too") if known else "their table 3 transmission, B = 1 / K")]
example("Biondi 2024 - interventional rooms", "Biondi et al. 2024: five interventional rooms", "Biondi 2024",
        department("Biondi 2024: interventional rooms",
                   [biondi_room(name, patients) for name, patients, _, _ in BIONDI_ROOMS]),
        "Their table 4, Eq. 4 (the shielding without the output of the tube): the patients of 2023 (table 1), the "
        "workload per patient (table 2), the NCRP 147 secondary air kerma per patient of cardiac (electrophysiology, "
        "haemodynamics: 3.8 mGy) or peripheral angiography (the others: 0.95 mGy, leakage + forward/backscatter), "
        "times Wsite / Wnorm, a fully occupied uncontrolled area 2 m from the isocenter, 1 mSv a year (P = 1/52 mGy "
        "per week, T = 1), lead with their table 3 transmission. The program works per week: patients / 52.",
        biondi_checks)

# Li et al. 2024, section 3: the lead for a transmission of 0.001 at each kVp, for both filtrations (tables 1 and 2)
LI_KVP = [60, 70, 80, 90, 100, 110, 120]
LI_LEAD = {"DR 600, default filtration (Li 2024)": [0.61, 0.87, 1.22, 1.62, 1.82, 1.90, 1.94],
           "DR 600, +1 mm Al +0.1 mm Cu (Li 2024)": [0.71, 1.02, 1.41, 1.86, 2.05, 2.10, 2.12]}


def li_room(data):
    walls = {}
    for k, kvp in enumerate(LI_KVP):
        item = primary(None, 1.0, "1", "20", kvp=kvp)  # K = 1 × 1 × 1 × 20 / 1² = 20 mGy/week, B = 0.02 / 20
        item["kvpdata"] = data
        walls[4 + k] = barrier(4 + k, ["Lead"], [item], T=1, P=0.02, name=f"{kvp} kV")
    return room("X-Ray room", f"Li 2024: {data.split(', ', 1)[1].replace(' (Li 2024)', '')}", walls, patients=1)


li_checks = [(f"Li 2024: {data.split(', ', 1)[1].replace(' (Li 2024)', '')}", f"{kvp} kV", "Lead", "mm", lead, 0.006,
              f"lead for B = 0.001 at {kvp} kV, table {1 if 'default' in data else 2}")
             for data, leads in LI_LEAD.items() for kvp, lead in zip(LI_KVP, leads)]
example("Li 2024 - DR 600 lead", "Li et al. 2024: lead for a transmission of 0.001", "Li 2024",
        department("Li 2024: DR 600", [li_room(data) for data in LI_LEAD]),
        "The lead that lets 0.001 of the primary beam through at 60 to 120 kV, for the DR 600 with its default "
        "filtration and with 1 mm Al + 0.1 mm Cu added (their section 3, from tables 1 and 2). Each wall is one kVp "
        "('Give kVp' with the DR 600 data): K = 20 mGy/week (1 patient, U = 1, K¹ = 20 mGy at 1 m), P = 0.02, so "
        "B = 0.001.",
        li_checks)


# ===================== build, check, write =====================
def program_value(app, rec, nr, e, quantity):
    if quantity == "K":
        return rec["K_total"]
    if quantity == "K per year":
        return rec["K_total"] * WEEKS
    if quantity == "B":
        return rec["B"]
    return dict(rec["thickness"])[quantity]


def data_checks(app):
    """Values the papers give about their own data, against the data of the program."""
    from Depcalculations import WORKLOAD_NORM, dbt_kerma, LI_ORTHOPEDIC
    rows = []
    for name, published in (("DR Room (floor) – Kirby 2023", 0.52), ("DR Room (cross-table wall) – Kirby 2023", 0.13),
                            ("DR Room (chest bucky) – Kirby 2023", 0.72), ("Pediatric DR (floor) – Kirby 2023", 0.17),
                            ("Pediatric DR (cross-table wall) – Kirby 2023", 0.004),
                            ("Pediatric DR (chest bucky) – Kirby 2023", 0.11)):
        rows.append({"paper": "Kirby 2023", "what": f"W total of table 3, {name.split(' – ')[0]} (mA·min/patient)",
                     "paper_value": published, "program": WORKLOAD_NORM[name], "tolerance": 0.006,
                     "how": "the sum of the workload of every kVp bin (the paper rounds it to 2 figures)"})
    rows.append({"paper": "Yang 2017", "what": "2D + 3D exam of both breasts, air kerma per patient at 1 m (mGy)",
                 "paper_value": 0.105, "program": dbt_kerma(3), "tolerance": 0.0005,
                 "how": "section 4: the sum of table 9 for 2 CC, 1 oblique toward and 1 away, in 2D and 3D"})
    params = app.transmission_params("prim abc", LI_ORTHOPEDIC)["Concrete"]
    for label, published, value in zip(("α", "β", "γ"), (0.04633, 0.0644, 0.5964), params):
        rows.append({"paper": "Li 2024", "what": f"Orthopedic table bucky, concrete {label}", "paper_value": published,
                     "program": value, "tolerance": 0.0,
                     "how": "section 4, the fit to the Archer equation (the program's workload distribution)"})
    rows += chen_checks(app) + li2013_checks()
    for row in rows:
        row["ok"] = abs(row["program"] - row["paper_value"]) <= row["tolerance"] + 1e-12
    return rows


def thickness_at(transmission, B, high=0.01):
    """The thickness at which transmission(x), falling with x, comes down to B."""
    low = 0.0
    while transmission(high) > B:
        high *= 2
    for _ in range(200):
        middle = (low + high) / 2
        low, high = (middle, high) if transmission(middle) > B else (low, middle)
    return (low + high) / 2


def chen_checks(app):
    """Chen et al. 2013: their table 1 sums to its totals; with the NCRP 147 method (tools/literature_data.py) their
    table 1 gives their primary air kerma (table 4) and their transmission through lead and concrete (table 6)."""
    import literature_data
    from Depcalculations import wb, PRIMARY_KERMA, CHEN, archer_thickness
    tables, rows = literature_data.Tables(wb), []
    sheet = [r for r in wb["Chen 2013"].iter_rows(min_row=3, values_only=True)]
    bins = [r for r in sheet if isinstance(r[0], (int, float))]
    totals = next(r for r in sheet if r[0] == "W total (published)")
    kerma = {r[0]: r for r in literature_rows(wb, "Chen 2013 kerma")}
    prim = {r[0]: r for r in literature_rows(wb, "Chen 2013 prim abc")}
    for k, (barrier, name) in enumerate(zip(("floor", "wall", "all"), CHEN), start=1):
        rows.append({"paper": "Chen 2013", "what": f"{barrier}: total workload of table 1 (mA·min/patient)",
                     "paper_value": totals[k], "program": sum(r[k] for r in bins), "tolerance": 0.0025,
                     "how": "table 1: the total against the sum of its 24 bins, each rounded to 3 decimals"})
        rows.append({"paper": "Chen 2013", "what": f"{barrier}: K¹P (mGy/patient), table 4 and NCRP 147 method",
                     "paper_value": float(PRIMARY_KERMA.get(name) or literature_data.CHEN_KP1[barrier]),
                     "program": kerma[name][10], "tolerance": 0.015,
                     "how": "table 4 (PCXMC), against their table 1 with the NCRP 147 K_W1 (Fig. B.1)"})
        spectrum = literature_data.Spectrum(tables, dict(zip(literature_data.CHEN_KVP,
                                                             literature_data.CHEN_SPECTRA[barrier])),
                                            *literature_data.CHEN_FIELD[barrier])
        for material, column in (("Lead", 1), ("Concrete", 4)):
            fit = tuple(float(v) for v in prim[name][column:column + 3])
            paper = archer_thickness(fit, 1e-3)
            rows.append({"paper": "Chen 2013", "what": f"{barrier}: {material.lower()} for B = 10⁻³ (mm), table 6 and "
                                                       "NCRP 147 method",
                         "paper_value": paper, "program": thickness_at(
                             lambda x: spectrum.transmission(material, x, False), 1e-3),
                         "tolerance": 0.01 * paper,
                         "how": "their fit (table 6), against the transmission of their table 1 with the NCRP 147 "
                                "data of each kVp (Table A.1, weighted by the air kerma)"})
    return rows


def li2013_checks():
    """Li et al. 2013: the sums of their table IV(c); their table V(a), the transmission of the combined DBT workload,
    from the single-kVp data of Li 2012 (tables I, II) and Li 2013 (table VI) weighted by the air kerma of each bin."""
    import literature_data
    from Depcalculations import wb, MAMMO_KVP_TABLES, archer_transmission, archer_thickness
    workload, rows = literature_data.LI2013_WORKLOAD, []
    for k, (label, published) in enumerate((("mA·min per patient", 12.61), ("K¹ (mGy per patient)", 19.22)), start=2):
        rows.append({"paper": "Li 2013", "what": f"table IV(c), sum (2D + 3D) of the {label}", "paper_value": published,
                     "program": sum(r[k] for r in workload), "tolerance": 0.02,
                     "how": "table IV(c), screening and diagnosis: the sum against its rows"})
    data = {"W/Rh": "W/Rh (Li 2012)", "W/Al": "W/Al (Li 2012)", "W/Ag": "W/Ag (Li 2013)"}
    total = sum(r[3] for r in workload)
    fits = next(r for r in wb["Li 2013 DBT abc"].iter_rows(min_row=3, values_only=True) if isinstance(r[0], str))
    columns = {"Lead": 1, "Concrete": 4, "Gypsum Wallboard": 7, "Steel": 10, "Plate Glass": 13, "Wood": 16}
    for material, column in columns.items():
        fit = tuple(float(v) for v in fits[column:column + 3])
        paper = archer_thickness(fit, 1e-3)
        combined = lambda x, m=material: sum(r[3] * archer_transmission(MAMMO_KVP_TABLES[data[r[0]]][r[1]][m], x)
                                             for r in workload) / total
        rows.append({"paper": "Li 2013", "what": f"{material} for B = 10⁻³ (mm), table V(a) and the single-kVp data",
                     "paper_value": paper, "program": thickness_at(combined, 1e-3), "tolerance": 0.01 * paper,
                     "how": "their fit (table V(a)), against Eq. 1: the W/Rh, W/Al (Li 2012) and W/Ag (Li 2013) "
                            "transmission at the highest kVp of each bin, weighted by its K¹ (table IV(c))"})
    return rows


def literature_rows(wb, sheet):
    return [r for r in wb[sheet].iter_rows(min_row=3, values_only=True)
            if isinstance(r[0], str) and isinstance(r[1], (int, float))]


def main():
    os.chdir(CODE)
    sys.path.insert(0, CODE)
    main_file = os.path.join(CODE, "Shielding_of_X-Ray_rooms.py")
    namespace = {"__name__": "literature_examples", "__file__": main_file}
    exec(compile(open(main_file, encoding="utf-8").read().replace("root.mainloop()", ""), main_file, "exec"),
         namespace)
    app, root = namespace["app"], namespace["root"]
    root.withdraw()
    from project import FORMAT, VERSION
    import Depcalculations
    assert Depcalculations.DBT == DBT

    os.makedirs(FOLDER, exist_ok=True)
    rows, failed = [], []
    for item in EXAMPLES:
        app.build_project({"format": FORMAT, "version": VERSION, "saved": "", "workspaces": [item["workspace"]]})
        rooms = {app.room_name(t): t for t in app.standalone} if app.standalone else \
            {app.room_name(t): t for t in app.departments[1]["rooms"]}
        lines = []
        for room_name, barrier_name, quantity, unit, paper, tolerance, how in item["checks"]:
            t = rooms[room_name]
            nr = app.d[f"nr {t}"]
            e = next(k for k in range(1, app.d[f"x {t}"] + 1) if app.barrier_name(k, nr) == barrier_name)
            rec = app.calc[(nr, e)]
            assert not rec["missing"], (item["file"], room_name, barrier_name, rec["missing"])
            value = program_value(app, rec, nr, e, quantity)
            approximate = isinstance(tolerance, tuple)  # the paper gives an approximate value
            limit = tolerance[1] if approximate else tolerance
            ok = limit is None or abs(value - paper) <= limit
            if not ok:
                failed.append((item["file"], room_name, barrier_name, quantity, paper, value))
            shown = f"{value:.3g}" if quantity in ("B",) else f"{value:.2f}"
            lines.append(f"• {room_name.split(': ', 1)[1]}, {barrier_name}, {quantity}: paper {paper:g} {unit}, "
                         f"program {shown} {unit}. {how[0].upper() + how[1:]}.")
            rows.append({"paper": item["paper"], "example": item["title"].split(": ", 1)[1],
                         "room": room_name.split(": ", 1)[1], "barrier": barrier_name, "quantity": quantity,
                         "unit": unit, "paper_value": paper, "program": value, "compared": tolerance is not None,
                         "approximate": approximate,
                         "ok": ok, "how": how})
            print(f"{item['file']:36s} {room_name[-22:]:22s} {barrier_name:14s} {quantity:16s} paper {paper:<9g} "
                  f"program {value:.4g}" + ("" if tolerance is not None else "   (not compared)"))
        project, _ = app.collect_project()
        project.update(title=item["title"], description="\n\n".join(
            [item["about"], "\n".join(lines), REFERENCES[item["paper"]]]))
        path = os.path.join(FOLDER, item["file"] + ".shield")
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("project.json", json.dumps(project, indent=1, ensure_ascii=False))
    checks = data_checks(app)
    for row in checks:
        print(f"data  {row['paper']:11s} {row['what'][:60]:60s} paper {row['paper_value']:<8g} program "
              f"{row['program']:.5g}  {'ok' if row['ok'] else 'DIFFERENT'}")
    with open(RESULTS, "w", encoding="utf-8") as file:
        json.dump({"examples": rows, "data": checks}, file, indent=1, ensure_ascii=False)
    root.destroy()
    write_comparison(rows, checks)
    print("written:", FOLDER)
    assert not failed, failed
    assert all(row["ok"] for row in checks), [row for row in checks if not row["ok"]]


# ===================== the comparison as an Excel workbook =====================
def write_comparison(rows, checks):
    """Examples/Literature/Literature examples - comparison.xlsx: paper, program and their difference (formulas),
    recalculated with Excel when it is installed."""
    from datetime import date
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from theme import plain  # the subscripts written d_{P}, as plain text

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
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
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

    made = (f"Program: Shielding of X-ray Rooms, the project files of this folder (Examples\\Literature), calculated by "
            f"tools/literature_examples.py on {date.today():%d/%m/%Y}. Difference = Program − Paper.")
    book = Workbook()
    ws = book.active
    ws.title = "Examples"
    sheet(ws, "Worked examples of the papers whose data the program offers", made,
          [("Paper", 12), ("Example", 30), ("Room", 22), ("Barrier", 13), ("Quantity", 16), ("Unit", 10),
           ("Paper", 11), ("Program", 11), ("Difference", 11), ("Difference (%)", 11), ("Compared", 10),
           ("How the paper finds it", 70)])
    for r, row in enumerate(rows, start=5):
        for col, value in enumerate([row["paper"], row["example"], row["room"], row["barrier"], row["quantity"],
                                     row["unit"]], start=1):
            put(ws, r, col, value)
        fmt = "0.00E+00" if row["quantity"] == "B" else "0.00"
        put(ws, r, 7, row["paper_value"], fmt, value_font)
        put(ws, r, 8, round(row["program"], 6) if row["quantity"] != "B" else float(f"{row['program']:.6g}"), fmt,
            value_font)
        put(ws, r, 9, f"=H{r}-G{r}", "+0.00E+00;-0.00E+00;0" if row["quantity"] == "B" else "+0.00;-0.00;0.00",
            formula_font)
        put(ws, r, 10, f'=IF(G{r}=0,"",I{r}/G{r})', "+0.0%;-0.0%;0.0%", formula_font)
        put(ws, r, 11, ("DIFFERENT" if not row["ok"] else "approximately" if row.get("approximate") else "yes")
            if row["compared"] else "no")
        put(ws, r, 12, plain(row["how"][0].upper() + row["how"][1:] + "."))
    notes(ws, 5 + len(rows) + 1, [
        "Blue: values (Paper: what the paper gives; Program: the result of the program). Black: formulas.",
        "Compared 'yes': within the rounding of the paper; 'approximately': the paper gives an approximate value; "
        "'no': shown, not compared, for the reason given.",
        "Biondi et al. 2024, table 4, Eq. 4: for neuroangiography and vascular surgery the paper's air kerma comes "
        "from the patients of another room of its table 1 (523 and 172); the program uses those of the room (172 and "
        "393).",
        "Yang et al. 2016: '~35 mm' of concrete with the 40 kVp W/Al data of Li et al. 2012; the Archer equation with "
        "their table I gives 32 mm.",
        "Judge et al. 2013 do not state the kVp of the Simpkin Mo/Mo data: 30 kVp (GE, Hologic) and 35 kVp (Philips) "
        "reproduce their table 1.",
        "Kirby et al. 2023, Chen et al. 2013 and Li et al. 2013 have no worked example: see the sheet 'Data checks'."]
          + list(REFERENCES.values()))

    ws = book.create_sheet("Data checks")
    sheet(ws, "Values the papers give about their own data, against the data in the program", made,
          [("Paper", 12), ("Value", 60), ("Paper", 11), ("Program", 11), ("Difference", 11), ("Same", 9),
           ("Where the paper gives it", 70)])
    for r, row in enumerate(checks, start=5):
        put(ws, r, 1, row["paper"])
        put(ws, r, 2, row["what"])
        put(ws, r, 3, row["paper_value"], "0.0000##", value_font)
        put(ws, r, 4, round(row["program"], 6), "0.0000##", value_font)
        put(ws, r, 5, f"=D{r}-C{r}", "+0.0000;-0.0000;0.0000", formula_font)
        put(ws, r, 6, "yes" if row["ok"] else "DIFFERENT")
        put(ws, r, 7, row["how"][0].upper() + row["how"][1:] + ".")
    notes(ws, 5 + len(checks) + 1, [
        "Kirby table 3, Biondi tables 2 and 3, Yang 2017 tables 8 and 9, Yang 2016 table V and Li 2024 tables 1 and 2 "
        "were also compared value by value with the program's data.",
        "Chen tables 1 and 6, and Li 2012 tables I and II with Li 2013 tables IV(c), V(a) and VI, reproduce each other "
        "(rows above); Judge table 1 is reproduced in the sheet Examples."])

    path = os.path.join(FOLDER, COMPARISON)
    book.save(path)
    recalculate(path)


if __name__ == "__main__":
    main()
