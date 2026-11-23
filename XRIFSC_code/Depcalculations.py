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
EXISTING_MAX = 3  # materials the existing shielding of a barrier can have
CEILING = "Up to the ceiling"  # the height of the shielding of a wall that goes up to the ceiling
HEIGHTS = ("2.1", "2.5", CEILING)  # NCRP 147 2.3.6, 5.8: 2.1 m; a darkroom 2.5 m; to the ceiling when it is shielded
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


# ===================== shielding the barrier already has (existing), in front of or beyond the new materials ======
def barrier_stack(new, existing=(), side="outside"):
    """The layers [(material, mm)] of a barrier from the room side out: the new materials outside the existing
    shielding (side 'outside'), or on the room side of it ('inside')."""
    return list(existing) + list(new) if side == "outside" else list(new) + list(existing)


def entry_transmission(c, first, layered):
    """What the preshielding of radiation type c lets reach the first layer of the barrier (material first). Layers:
    as calculated for them (c['start']). Each material alone: the preshielding in the material of the first layer,
    as NCRP 147 Table 4.6 gives it (lead, concrete, steel); none for the other materials."""
    if layered:
        return c["start"]
    pre = c["pre"].get(first)
    return archer_transmission(c["params"][first], pre) if pre else 1.0


def stacks_usable(components, stacks):
    """Whether every radiation type has transmission data for every material of the stacks of layers."""
    return all(has_data(c["params"], m) for c in components for stack in stacks for m, _ in stack)


def stack_dose(components, layers, layered):
    """Weekly air kerma beyond the layers [(material, mm)], from the room side out: the sum of K x transmission of
    every radiation type, each after its preshielding."""
    if not layers:
        return sum(c["K"] * (c["start"] if layered else 1.0) for c in components)
    return sum(c["K"] * through(c["params"], layers, entry_transmission(c, layers[0][0], layered))
               for c in components)


def thickness_alone(components, material, P, existing=(), side="outside"):
    """Thickness of one material, the only new one of the barrier: sum of K B(x + preshielding) = P. existing: the
    layers the barrier already has, the new material outside them (side 'outside') or on their room side."""
    if existing:
        dose = lambda x: stack_dose(components, barrier_stack([(material, x)], existing, side), False)
        total = sum(c["K"] for c in components)
        return thickness_for(dose, P, max(archer_thickness(c["params"][material], min(P / total, 1.0))
                                          for c in components))
    if len(components) == 1:  # the Archer equation, minus the preshielding
        c = components[0]
        return max(archer_thickness(c["params"][material], P / c["K"]) - c["pre"].get(material, 0.0), 0.0)
    total = sum(c["K"] for c in components)
    dose = lambda x: sum(c["K"] * archer_transmission(c["params"][material], x + c["pre"].get(material, 0.0))
                         for c in components)
    return thickness_for(dose, P, max(archer_thickness(c["params"][material], min(P / total, 1.0))
                                      for c in components))


def thickness_layers(components, materials, fractions, P, existing=(), side="outside"):
    """Layers of one barrier, from the inside out, each giving its fraction of the attenuation of the air kerma from
    what the preshielding lets through down to P; every radiation type goes through all of them. existing: the layers
    the barrier already has; the new layers outside them (side 'outside': they start after them) or on their room
    side ('inside')."""
    if existing and side == "outside":  # what reaches the new layers has already gone through the existing ones
        components = [dict(c, start=through(c["params"], existing, c["start"])) for c in components]
    elif existing:
        return layers_before(components, materials, fractions, P, existing)
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


def layers_before(components, materials, fractions, P, after):
    """New layers on the room side of layers already there ('after', outside them): the new ones share the
    attenuation in front of 'after' as their fractions say, so much that the air kerma beyond all of them is P."""
    final = lambda xs: stack_dose(components, list(zip(materials, xs)) + list(after), True)
    zero = [0.0] * len(materials)
    if final(zero) <= P:
        return zero
    # the air kerma the new layers let through, exp(u), found so that 'after' brings it down to P
    low, high = math.log(P) - 80.0, math.log(sum(c["K"] * c["start"] for c in components))
    for _ in range(200):
        middle = (low + high) / 2
        if final(thickness_layers(components, materials, fractions, math.exp(middle))) > P:
            high = middle
        else:
            low = middle
        if high - low < 1e-11:
            break
    return thickness_layers(components, materials, fractions, math.exp(low))


def required_thicknesses(components, P, materials, fractions=None, existing=(), side="outside"):
    """The required thickness of each material (or why there is none): layers of one barrier when fractions are
    given, else each material alone; existing: the layers the barrier already has (see barrier_stack)."""
    usable = lambda material: all(has_data(c["params"], material) for c in components)
    no_data = [m for m, _ in existing if not usable(m)]
    if no_data:
        return [f"No transmission data for {no_data[0]} (existing)"] * len(materials)
    if fractions is not None:
        no_data = [m for m in materials if not usable(m)]
        if no_data:
            return [f"No transmission data for {no_data[0]}"] * len(materials)
        return thickness_layers(components, materials, fractions, P, existing, side)
    result = []
    for material in materials:
        if material == "Select Material":
            result.append("Select Material")
        elif usable(material):  # 0: no additional shielding is needed
            result.append(thickness_alone(components, material, P, existing, side))
        else:
            result.append(f"No transmission data for {material}")
    return result


def larger_thicknesses(own, needed, label):
    """For each material the larger of two thicknesses (or why there is none), and which one it is: 'this' or
    'other'. A thickness the other area cannot give (no data) is named after it (label)."""
    combined, governs = [], []
    for mine, theirs in zip(own, needed):
        if isinstance(mine, float) and isinstance(theirs, float):
            combined.append(max(mine, theirs))
            governs.append("other" if theirs > mine + 1e-9 else "this")
        elif isinstance(mine, float):  # the radiation of the other area has no data for this material
            combined.append(f"{theirs} ({label})")
            governs.append(None)
        else:
            combined.append(mine)
            governs.append(None)
    return combined, governs


def other_side(materials, fractions, existing, side):
    """The same barrier seen from the room on its other side: the layers in the reverse order, and the new
    materials on the other side of the existing ones."""
    if fractions is not None:
        materials, fractions = list(materials)[::-1], list(fractions)[::-1]
    return materials, fractions, list(existing)[::-1], "inside" if side == "outside" else "outside"


# NCRP 147 Table 4.1: the occupancy factor T of each location
OCCUPANCY_T = {row[0]: float(row[1]) for row in wb['Occupancy Factor ( T )'].iter_rows(min_row=2, max_col=2,
                                                                                         values_only=True) if row[0]}
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


# Digital breast tomosynthesis of Li X, Zhang D, Liu B, Med. Phys. 40 (2013) 063901: the workload per patient of the
# combined DBT workload of three MGH rooms (table IV(c), 2D + 3D, screening and diagnosis) and the transmission of its
# primary radiation (table V(a), sheet 'Li 2013 DBT abc'), which they take for the secondary radiation too
DBT_LI2013 = "Digital Breast Tomosynthesis – Li 2013"
SOURCES[DBT_LI2013] = "Li et al. 2013"
WORKLOAD_NORM[DBT_LI2013] = 12.61  # mA min per patient
TRANSMISSION_SHEETS[DBT_LI2013] = ("Li 2013 DBT abc", "Li 2013 DBT abc")
# With it, the scatter of Yang K, Li X, Liu B, Med. Phys. 43 (2016) 1096, measured around a Hologic Selenia Dimensions
# with this MGH workload (their ref. 4), table V: unshielded scatter air kerma per patient at 1 m (mGy/patient) toward
# each barrier, at the average technique (30 kVp W/Ag 2D + 30 kVp W/Al 3D) and the high one (35 kVp W/Ag 2D + 40 kVp
# W/Al 3D). Yang et al. 2016 give no transmission data.
YANG2016_KERMA = {"Wall / door, average technique": 1.76e-2, "Floor, average technique": 1.64e-1,
                  "Ceiling, average technique": 3.66e-2, "Wall / door, high technique": 3.32e-2,
                  "Floor, high technique": 3.07e-1, "Ceiling, high technique": 7.33e-2}
YANG2016_TECHNIQUES = {"average": "30 kVp W/Ag (2D) + 30 kVp W/Al (3D)", "high": "35 kVp W/Ag (2D) + 40 kVp W/Al (3D)"}
KERMA_SOURCES = {DBT_LI2013: "Yang et al. 2016"}  # where the suggested secondary air kerma comes from, if not SOURCES

# Full-field digital mammography (2D) of Judge MA, Keavey E, Phelan N, Br. J. Radiol. 86 (2013) 20120130, table 1: the
# maximum scatter at 1 m of one exposure of three units x 4 exposures per patient = K1sec (mGy/patient). Their barriers
# are calculated with Simpkin's Mo/Mo transmission (NCRP 147 Table A.1) at the kVp that reproduces their table 1.
JUDGE_FFDM = "Digital Mammography (FFDM) – Judge 2013"
SOURCES[JUDGE_FFDM] = "Judge et al. 2013"
JUDGE_UNITS = {k: (row[0], float(row[3]), int(row[4]))  # 1, 2, 3: (unit, K1sec, kVp)
               for k, row in enumerate((r for r in wb["Judge 2013"].iter_rows(min_row=3, values_only=True)
                                        if isinstance(r[0], str) and isinstance(r[1], (int, float))), start=1)}

# Radiographic rooms in Taiwan (Chen TR et al., Health Phys. 104 (2013) S60): workload per patient (table 1), primary
# air kerma per patient (table 4, PCXMC) and transmission through lead and concrete (table 6; for secondary radiation
# their 'all barriers'). Leakage and scatter: made from their spectra with the NCRP 147 method by
# tools/literature_data.py, as for Kirby et al.
CHEN = []
for _row in literature_rows("Chen 2013 kerma"):
    CHEN.append(_row[0])
    WORKLOAD_NORM[_row[0]] = _row[1]
    UNSHIELDED_SECONDARY[_row[0]] = _row[:9]
    if _row[9] is not None:
        PRIMARY_KERMA[_row[0]] = f"{_row[9]:g}"
    SOURCES[_row[0]] = "Chen et al. 2013"
    TRANSMISSION_SHEETS[_row[0]] = ("Chen 2013 prim abc", "Chen 2013 sec abc")


# Transmission of mammography and DBT beams at a kVp ('Give kVp' in a mammography room): NCRP 147 (its secondary data),
# the Mo/Mo beams of NCRP 147 Table A.1 (Simpkin), and the W/Al, W/Rh (Li et al. 2012) and W/Ag beams (Li et al. 2013)
# of a Hologic Selenia Dimensions (sheet 'Mammography kVp abc'). The secondary radiation is taken as attenuated like
# the primary beam (NCRP 147, Li et al.).
MAMMO_KVP_DATA = ["NCRP 147", "Mo/Mo (NCRP 147)", "W/Al (Li 2012)", "W/Rh (Li 2012)", "W/Ag (Li 2013)"]


def _mammography_tables():
    """{data: {kVp: {material: (alpha, beta, gamma)}}} of the mammography beams at a kVp."""
    columns = {"Lead": 1, "Concrete": 4, "Gypsum Wallboard": 7, "Steel": 10, "Plate Glass": 13, "Wood": 16}
    tables = {"Mo/Mo (NCRP 147)": {}}
    for row in wb["prim abc"].iter_rows(min_row=3, values_only=True):
        if row[0] in (25, 30, 35):
            tables["Mo/Mo (NCRP 147)"][row[0]] = {m: tuple(float(row[c + k]) for k in range(3))
                                                  for m, c in columns.items()}
    current = None
    for row in wb["Mammography kVp abc"].iter_rows(min_row=2, values_only=True):
        if isinstance(row[0], str) and row[0] in MAMMO_KVP_DATA:
            current = tables.setdefault(row[0], {})
        elif isinstance(row[0], (int, float)) and current is not None:
            current[int(row[0])] = {m: tuple(float(row[c + k]) for k in range(3)) for m, c in columns.items()}
    return tables


MAMMO_KVP_TABLES = _mammography_tables()
MAMMO_KVPS = {"NCRP 147": [30, 50, 70, 100, 125, 150]}  # the kVp of the NCRP 147 secondary data
MAMMO_KVPS.update({data: sorted(table) for data, table in MAMMO_KVP_TABLES.items()})

# Li X, Marschall TA, Yang K, Liu B, Med. Phys. 51 (2024) 8768, section 4: transmission through concrete of the primary
# beam of a workload distribution, the table bucky of an orthopedic room with an AGFA DX-D 600 (their example, figure
# 5). Concrete only, primary only; the paper gives no air kerma per patient nor workload per patient.
LI_ORTHOPEDIC = "Orthopedic Room, table bucky (DR 600) – Li 2024"
SOURCES[LI_ORTHOPEDIC] = "Li et al. 2024"
TRANSMISSION_SHEETS[LI_ORTHOPEDIC] = ("Li 2024 workload abc", None)
PRIMARY_ONLY = [LI_ORTHOPEDIC]
NO_WORKLOAD_NORM = [DBT, LI_ORTHOPEDIC, JUDGE_FFDM]  # their workload must be given in patients per week
NO_WNORM_MESSAGE = {DBT: "Patients per week (DBT)", LI_ORTHOPEDIC: "Patients per week (Li 2024)",
                    JUDGE_FFDM: "Patients per week (Judge 2013)"}


# Transmission data for a primary beam at a given kVp: NCRP 147, or modern digital radiography (Li X, Marschall TA,
# Yang K, Liu B, Med. Phys. 2024, doi:10.1002/mp.17449, tables 1 and 2: Agfa DR 600, 60-120 kV every 10 kV)
KVP_DATA = ["NCRP 147", "DR 600, default filtration (Li 2024)", "DR 600, +1 mm Al +0.1 mm Cu (Li 2024)"]

# ===================== secondary air kerma of a kVp, at a scattering angle (NCRP 147 Appendices B and C) ==========
# Tungsten anode, aluminium filter: Figure C.1 gives the scatter fraction a1 as a formula for 50-150 kVp, drawn from
# 20 to 140 degrees. The workload per patient is the one the program takes for a kVp (NCRP 147 Rad Room).
ANGLES, ANGLE_KVP, KVP_WNORM = (20, 140), (50, 150), 2.5
# Leakage (C.2): 0.876 mGy/h at 1 m at 150 kVp and 3.3 mA, behind a housing of 2.32 mm lead; at a lower kVp it falls
# with kVp² and the transmission of that housing (Eq. C.6-C.9)
LEAK_RATE, LEAK_KVP, LEAK_MA, HOUSING = 0.876 / 60, 150, 3.3, 2.32
ANGLE_OUT_OF_RANGE = "Scatter at an angle: 50-150 kVp, not mammography"


def kerma_per_workload(kvp):
    """K_W1: primary air kerma at 1 m per mA min (mGy), NCRP 147 Figure B.1, tungsten anode, aluminium filter."""
    return 1.222 - 5.664e-2 * kvp + 1.227e-3 * kvp ** 2 - 3.136e-6 * kvp ** 3


def scatter_fraction(theta, kvp):
    """a1 (× 10⁻⁶, per cm² of primary field at 1 m) at the scattering angle theta (degrees), NCRP 147 Figure C.1."""
    return 1.6e-2 * (kvp - 125) + 8.43 - 1.11e-1 * theta + 9.83e-4 * theta ** 2 - 1.74e-6 * theta ** 3


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
    "Patients per week (Li 2024)": "Li et al. 2024 give no workload per patient (Wnorm) for this workload "
                                   "distribution: at the top of the room choose 'The Number of Patients per week' (or "
                                   "tick 'Different Workload' on this radiation type).",
    "Patients per week (Judge 2013)": "Judge et al. 2013 give no workload per patient (Wnorm): at the top of the room "
                                      "choose 'The Number of Patients per week' (or tick 'Different Workload' on this "
                                      "radiation type).",
    "FFDM unit (Judge 2013)": "under the suggested secondary air kerma choose the unit: GE Essential, Hologic Selenia "
                              "or Philips MDM.",
    "kVp for the mammography data": "the transmission data chosen for the kVp exist for: Mo/Mo (NCRP 147) 25, 30, 35 kVp; "
                                    "W/Al (Li 2012) 25, 30, 35, 40, 45, 49 kVp; W/Rh (Li 2012) and W/Ag (Li 2013) 25, "
                                    "30, 35, 39 kVp. Choose one of these, or the NCRP 147 data.",
    "Primary radiation only": "this workload distribution (Li et al. 2024) has transmission data for the primary beam "
                              "only (through concrete). Choose 'Primary', or another workload distribution.",
    "Barrier of Yang 2016": "at 'Per barrier (Yang 2016)' choose the barrier (wall / door, floor or ceiling) and the "
                            "technique.",
    "Occupancy Factor (T)": "under 'Shielding Area' choose 'Write occupancy factor (T)' and type it, "
                            "or 'select Location' and pick what is beyond the barrier.",
    "Distance from the Source to the Barrier (m)": "type the distance (d_{P}, d_{L}, d_{S} or d_{sec}) from the X-ray source "
                                                   "to the barrier in metres; the distance to the person beyond it "
                                                   "is added (or tick 'Enter the whole distance' and type all of it).",
    "Distance beyond the barrier (m)": "next to the distance, type how far beyond the barrier the person to "
                                       "protect is (NCRP 147 4.1.2): walls and doors 0.3 m, ceiling 0.5 m, floor "
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
    "Existing shielding (material and thickness)": "under the materials, choose each material the barrier already "
                                                   "has and type its thickness in mm, or untick 'The barrier "
                                                   "already has shielding'.",
    "Further area (distance, T and P)": "under 'Also check an area further away' type how much further than the "
                                        "person beyond the barrier it is (m, 0 or more), its occupancy factor T "
                                        "(more than 0, at most 1) and its design goal P, or untick it.",
    "Scattering angle (20-140°)": "type the angle between the primary beam and the direction to the barrier, from 20 "
                                  "to 140 degrees (NCRP 147 Figure C.1).",
    ANGLE_OUT_OF_RANGE: "the scatter fraction of NCRP 147 Figure C.1 is for tungsten-anode beams of 50 to 150 kVp: "
                        "choose such a kVp, or write the unshielded secondary air kerma.",
    "Field size (F and d_F)": "beside 'Field size', type the primary field F (cm², e.g. the image receptor) and "
                              "its distance d_{F} from the source (m, e.g. the SID), and for a written air kerma the "
                              "field it was given for, all more than 0, or untick 'Field size'.",
    "Distance": "type the distance from the CT isocenter to the barrier in metres (or the whole distance to the "
                "person beyond it, with 'Enter the whole distance' ticked).",
    "Procedures and DLP (body or head)": "at the top of the CT room type the weekly body and/or head "
                                         "procedures and their DLP.",
}

class departprimsec():

    def choosetype(self, e, nr, t, notify=True, partner=True):
        # notify: tell the user what is missing (the Calculate button); off for batch calculations.
        # partner: a wall shared with a room of the department is calculated again on that side too
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
                                           if self.d[f"radiob_w {e}{nr}{i}"].get() == 1 else {},
                                           "d": self.last_distribution["d"]})
            for problems, problem_fields in (self.layer_problems(e, nr), self.existing_problems(e, nr),
                                             self.far_problems(e, nr)):
                missing += problems
                fields += problem_fields
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
        self.share_barrier(e, nr, t, partner)
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
                theme.insert_rich(text, " — " + MISSING_HELP.get(label, "") + "\n" if label in MISSING_HELP else "\n")
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
        existing, side = self.existing_shielding(e, nr)
        shield = getattr(self, "last_shield", None)
        far = self.far_area(e, nr)
        if far and shield and result.get("T") and not self.need:
            # the further area: every radiation type with its T and the person that much further away
            far["components"] = [dict(c, K=c["K"] * far["T"] / result["T"] * (c["d"] / (c["d"] + far["delta"])) ** 2)
                                 for c in shield["components"]]
        result.update(area=area if area != "Classify the area" else None, location=location,
                      thickness=thickness, missing=list(self.need), layers=layers,
                      existing={"layers": existing, "side": side} if existing else None,
                      far=far if far and far.get("components") else None, shield=shield)
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
            field = [self.entry_number(f"{name} {e}{nr}{i}") for name in ("fieldF", "fielddF", "fieldF0", "fielddF0")]
            if value(f"fieldvar {e}{nr}{i}") == 1 and all(field):
                source += f", field {field[0]:g} cm² at {field[1]:g} m (written for {field[2]:g} cm² at {field[3]:g} m)"
        elif value(f"unairkerv {e}{nr}{i}") == 1 and value(f"vselxray {e}{nr}{i}") == 2:
            theta = self.entry_number(f"angle {e}{nr}{i}")
            F, dF = self.entry_number(f"angleF {e}{nr}{i}"), self.entry_number(f"angledF {e}{nr}{i}")
            if None not in (theta, F, dF) and dF > 0:
                leak = " + leakage" if value(f"angleleak {e}{nr}{i}") == 1 else ""
                source = (f"Scatter at {theta:g}°{leak} (NCRP 147 Appendix C, {F:g} cm² at {dF:g} m, "
                          f"{KVP_WNORM:g} mA·min per patient)")
        elif value(f"unairkerv {e}{nr}{i}") == 1 and distribution == DBT:
            mode = {1: "2D", 2: "3D", 3: "2D + 3D"}.get(value(f"dbtmode {e}{nr}{i}"), "")
            source = f"DBT {mode} ({origin})" if mode else ""
        elif value(f"unairkerv {e}{nr}{i}") == 1 and distribution == DBT_LI2013:
            choice = self.dbt_barrier_choice(e, nr, i)
            source = f"DBT toward the {choice.lower()} (Yang et al. 2016)" if choice in YANG2016_KERMA else ""
        elif value(f"unairkerv {e}{nr}{i}") == 1 and distribution == JUDGE_FFDM:
            unit = JUDGE_UNITS.get(self.ffdm_unit(e, nr, i))
            source = f"FFDM {unit[0]} ({origin})" if unit else ""
        elif value(f"unairkerv {e}{nr}{i}") == 1:
            if value(f"airkerv {e}{nr}{i}") == 1:
                source = {1: "Leakage + side-scatter", 2: "Leakage + forward/backscatter",
                          0: "Leakage only"}.get(value(f"radiob_leak {e}{nr}{i}"), "")
            else:
                source = {2: "Side-scatter", 3: "Forward/backscatter"}.get(value(f"airkerv {e}{nr}{i}"), "")
            source = f"{source} ({origin})" if source else ""
            F, dF = self.entry_number(f"fieldF {e}{nr}{i}"), self.entry_number(f"fielddF {e}{nr}{i}")
            if source and "catter" in source and value(f"fieldvar {e}{nr}{i}") == 1 and F and dF:
                source += f", field {F:g} cm² at {dF:g} m"
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

    def dbt_barrier_choice(self, e, nr, i):
        """The barrier and technique chosen for the air kerma of Yang et al. 2016 ('Floor, high technique'), or ''."""
        variable = self.d.get(f"dbtbarrier {e}{nr}{i}")
        try:
            return variable.get() if variable is not None else ""
        except TclError:
            return ""

    def ffdm_unit(self, e, nr, i):
        """The FFDM unit chosen for the air kerma of Judge et al. 2013 (1, 2, 3), or None."""
        variable = self.d.get(f"ffdmunit {e}{nr}{i}")
        try:
            return variable.get() if variable is not None else None
        except TclError:
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
        if data in MAMMO_KVP_DATA[1:]:  # mammography beams at a kVp: Mo/Mo (NCRP 147), Li et al. 2012, 2013
            try:
                return MAMMO_KVP_TABLES[data].get(int(distribution))
            except (TypeError, ValueError):
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
            # a kVp: the Wnorm of NCRP 147 for the rad room (all barriers), or for the mammography room
            mammography = self.d[f"vselroom {t}"].get() == "Mammography Room"
            w_norm = (WORKLOAD_NORM["Mammography Room"] if mammography else 2.5) if kvp else WORKLOAD_NORM.get(distribution)
            if total is None:
                need.append("Workload")
                fields.append(f"worentry {suffix}")
            elif w_norm is None and distribution in NO_WORKLOAD_NORM:
                need.append(NO_WNORM_MESSAGE[distribution])
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
            if distribution in PRIMARY_ONLY:
                need.append("Primary radiation only")
            source = self.d[f"unairkerv {e}{nr}{i}"].get() if f"unairkerv {e}{nr}{i}" in self.d else 0
            if source == 1 and kvp:  # a kVp: the scatter at the angle given, with the leakage if ticked
                K1, missing, marked = self.angle_kerma(e, nr, i, t)
                need += missing
                fields += marked
            elif source == 1 and distribution == DBT:  # Yang et al. 2017: per view, in the chosen mode
                mode = self.d[f"dbtmode {e}{nr}{i}"].get() if f"dbtmode {e}{nr}{i}" in self.d else 0
                if mode in DBT_MODES:
                    K1 = dbt_kerma(mode)
                else:
                    need.append("Unshielded Air Kerma")
            elif source == 1 and distribution == DBT_LI2013:  # Yang et al. 2016: toward the barrier, at the technique
                K1 = YANG2016_KERMA.get(self.dbt_barrier_choice(e, nr, i))
                if K1 is None:
                    need.append("Barrier of Yang 2016")
            elif source == 1 and distribution == JUDGE_FFDM:  # Judge et al. 2013: the unit chosen
                unit = JUDGE_UNITS.get(self.ffdm_unit(e, nr, i))
                if unit is None:
                    need.append("FFDM unit (Judge 2013)")
                else:
                    K1 = unit[1]
            elif source == 1:  # NCRP 147 values for the workload distribution
                kind = self.d[f"airkerv {e}{nr}{i}"].get() if f"airkerv {e}{nr}{i}" in self.d else 0
                if kind == 1:
                    column = {1: 6, 2: 8}.get(self.d[f"radiob_leak {e}{nr}{i}"].get(), 4)
                else:
                    column = {2: 5, 3: 7}.get(kind)
                row = UNSHIELDED_SECONDARY.get(distribution)
                if column is not None and row is not None:
                    K1 = float(row[column])
                    scale = self.field_scale(e, nr, i, row)
                    if scale is None:
                        need.append("Field size (F and d_F)")
                        fields += [f"fieldF_entry {e}{nr}{i}", f"fielddF_entry {e}{nr}{i}"]
                    elif scale != 1.0 and column != 4:  # the scatter grows with the field, the leakage does not
                        leakage = float(row[4]) if column in (6, 8) else 0.0
                        K1 = leakage + scale * float(row[5] if column in (5, 6) else row[7])
                else:
                    need.append("Unshielded Air Kerma")
            elif source == 2:  # written by the user, for the field written with it
                K1 = self.entry_number(f"entk {e}{nr}{i}")
                if K1 is None:
                    need.append("Unshielded Air Kerma")
                    fields.append(f"entk {e}{nr}{i}")
                scale = self.field_scale(e, nr, i)
                if scale is None:
                    need.append("Field size (F and d_F)")
                    fields += [f"{name}_entry {e}{nr}{i}" for name in ("fieldF", "fielddF", "fieldF0", "fielddF0")]
                elif K1 is not None:
                    K1 *= scale  # the whole value: the scatter, which grows with the field, is most of it
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
        """The transmission data chosen for a radiation type given by its kVp: for a primary beam NCRP 147 or DR 600
        (Li 2024), for a secondary one in a mammography room NCRP 147, Mo/Mo or the beams of Li et al. 2012, 2013."""
        var = self.d.get(f"kvpdata {e}{nr}{i}")
        if var is None or self.d[f"vselxray {e}{nr}{i}"].get() != 2:
            return "NCRP 147"
        primary = self.d[f"radiob_w {e}{nr}{i}"].get() == 1
        return var.get() if var.get() in (KVP_DATA if primary else MAMMO_KVP_DATA) else "NCRP 147"

    def angle_kerma(self, e, nr, i, t):
        """Unshielded secondary air kerma per patient at 1 m of a radiation type given by its kVp (NCRP 147 Appendix
        C): the scatter at the angle given, K_W1(kVp) · Wnorm · a1(θ, kVp) · 10⁻⁶ · F / d_F² (Eq. C.2, Figures B.1 and
        C.1), and, if ticked, the leakage of the tube at that kVp (Eq. C.6-C.9); Wnorm 2.5 mA min, as the program takes
        for a kVp. Returns (K1 or None, what is missing, the entries to mark)."""
        need, fields = [], []
        try:
            kvp = float(self.d[f"vsexroom {e}{nr}{i}"].get())
        except (KeyError, TclError, ValueError):
            kvp = None
        if kvp is None or not ANGLE_KVP[0] <= kvp <= ANGLE_KVP[1] or \
                self.d[f"vselroom {t}"].get() == "Mammography Room":
            need.append(ANGLE_OUT_OF_RANGE)
        theta = self.entry_number(f"angle {e}{nr}{i}")
        if theta is None or not ANGLES[0] <= theta <= ANGLES[1]:
            need.append("Scattering angle (20-140°)")
            fields.append(f"angle_entry {e}{nr}{i}")
        F, dF = self.entry_number(f"angleF {e}{nr}{i}"), self.entry_number(f"angledF {e}{nr}{i}")
        if F is None or dF is None or F <= 0 or dF <= 0:
            need.append("Field size (F and d_F)")
            fields += [f"angleF_entry {e}{nr}{i}", f"angledF_entry {e}{nr}{i}"]
        if need:
            return None, need, fields
        K1 = kerma_per_workload(kvp) * KVP_WNORM * scatter_fraction(theta, kvp) * 1e-6 * F / dF ** 2
        leak = self.d.get(f"angleleak {e}{nr}{i}")
        if leak is not None and leak.get() == 1:
            # the housing at the kVp of Table A.1 (every 5 kVp; between two, the higher, which is harder)
            lead = lambda v: archer_transmission(
                self.transmission_params("prim abc", min(150, 5 * math.ceil(v / 5)))["Lead"], HOUSING)
            K1 += LEAK_RATE * kvp ** 2 * lead(kvp) * KVP_WNORM / (LEAK_KVP ** 2 * lead(LEAK_KVP) * LEAK_MA)
        return K1, [], []

    def field_scale(self, e, nr, i, row=None):
        """How much the scatter of radiation type i grows with its primary field (NCRP 147 4.1.7.2, Eq. C.2):
        (F / dF²) / (F0 / dF0²), with F0 at dF0 the field the suggested air kerma assumes (row: NCRP 147 Table 4.7, or
        the data of the literature), or, for an air kerma written (row None), the field typed with it. 1 when the
        option is off; None when the field given is not valid."""
        option = self.d.get(f"fieldvar {e}{nr}{i}")
        if option is None or option.get() != 1:
            return 1.0
        if row is None:
            F0, dF0 = self.entry_number(f"fieldF0 {e}{nr}{i}"), self.entry_number(f"fielddF0 {e}{nr}{i}")
        else:
            try:
                F0, dF0 = float(row[2]), float(row[3])
            except (TypeError, ValueError):
                return 1.0
        F, dF = self.entry_number(f"fieldF {e}{nr}{i}"), self.entry_number(f"fielddF {e}{nr}{i}")
        if any(v is None or v <= 0 for v in (F, dF, F0, dF0)):
            return None
        scale = (F / dF ** 2) / (F0 / dF0 ** 2)
        return 1.0 if abs(scale - 1) < 1e-9 else scale

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
        data = self.kvp_data(e, nr, i)
        if distribution == JUDGE_FFDM:  # Simpkin's Mo/Mo data at the kVp of the unit, as Judge et al.
            unit = JUDGE_UNITS.get(self.ffdm_unit(e, nr, i))
            if unit is None:
                return None, "FFDM unit (Judge 2013)"
            return MAMMO_KVP_TABLES["Mo/Mo (NCRP 147)"][unit[2]], None
        params = self.transmission_params("prim abc" if primary else "sec abc", distribution, data)
        if params is None and data in MAMMO_KVP_DATA[1:]:
            return None, "kVp for the mammography data"
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
        for problems, fields in (self.layer_problems(e, nr), self.existing_problems(e, nr),
                                 self.far_problems(e, nr)):
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
        self.material_thicknesses(e, nr, [{"K": K, "params": ct_params, "pre": {}, "d": d}] if K else [], P)
        self.record_barrier(e, nr, kind="ct", P=P or None, T=T, K_total=K, B=B, d=d if K else None,
                            kvp=int(number(f"kvp_var {t}")) or None, beyond=beyond, scans=scans,
                            whole=self.whole_distance(e, nr), D=D if K else None)

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

    def layer_fractions(self, e, nr):
        """The share of each layer as a fraction, from the inside out; None for 'Each one alone'."""
        if not self.is_layered(e, nr):
            return None
        shares = [self.entry_number(f"share {e}{o}{nr}") for o in range(1, self.d[f"vnumbmat {e}{nr}"].get() + 1)]
        return [share / sum(shares) for share in shares]

    def material_thicknesses(self, e, nr, components, P):
        """Thickness of every material of the barrier (self.thm), or the list of what is missing.
        components: the radiation types, each with its air kerma K, its transmission data and its preshielding; each
        goes through the barrier on its own (NCRP 147 Sections 5.3.5, 5.4.2), so the thickness gives
        sum of K B(x + preshielding) = P.
        Each alone: the thickness of each material if it were the only new one.
        Layers: from the room side outwards, each material takes its share of the attenuation; a layer starts at the
        equivalent thickness of what is already in front of it (NCRP 147 treats preshielding the same way), so the
        hardening of the beam and the order of the layers count.
        Existing shielding: the barrier already has it; the new materials go outside it or on its room side, and
        give what it does not."""
        count = self.d[f"vnumbmat {e}{nr}"].get()
        materials = [self.d[f"vmater {e}{o}{nr}"].get() for o in range(1, count + 1)]
        existing, side = self.existing_shielding(e, nr)
        usable = lambda material: all(has_data(c["params"], material) for c in components)
        self.last_shield = None  # transmission data of this barrier, for the dose check and the views
        if not self.need and not components:
            self.need.append("Unshielded air kerma is zero")
        if not self.need:
            for c in components:
                c["start"] = preshielding_transmission(c["params"], c["pre"])
            main = max(components, key=lambda c: c["K"])  # the views show the other rooms' rays through it
            names = set(materials) | {m for m, _ in existing}
            self.last_shield = {"components": components, "params": {m: main["params"][m] for m in names
                                                                      if usable(m)}}
        if self.need:
            if "Select Material" in materials:
                self.need.append("Select Material")
            self.need = list(dict.fromkeys(self.need))
            thicknesses = ["\n".join(self.need)] * count
        else:
            thicknesses = required_thicknesses(components, P, materials, self.layer_fractions(e, nr), existing, side)
        for o, value in enumerate(thicknesses, start=1):
            self.thm[f"xbar {e}{o}{nr}"] = value

    # ===================== the shielding the barrier already has =====================
    def existing_count(self, e, nr):
        variable = self.d.get(f"existcount {e}{nr}")
        try:
            return min(max(int(variable.get()), 1), EXISTING_MAX) if variable is not None else 1
        except (TclError, ValueError):
            return 1

    def existing_on(self, e, nr):
        option = self.d.get(f"existing {e}{nr}")
        return option is not None and option.get() == 1

    def existing_shielding(self, e, nr):
        """The shielding the barrier already has, [(material, mm)] from the room side out, and where the new materials
        go: 'outside' it or 'inside' (on its room side). No layers when the option is off or not filled in."""
        variable = self.d.get(f"addside {e}{nr}")
        side = variable.get() if variable is not None and variable.get() in ("inside", "outside") else "outside"
        if not self.existing_on(e, nr):
            return [], side
        layers = []
        for k in range(1, self.existing_count(e, nr) + 1):
            material = self.d[f"existmat {e}{k}{nr}"].get() if f"existmat {e}{k}{nr}" in self.d else ""
            x = self.entry_number(f"existmm {e}{k}{nr}")
            if material not in MATERIAL_COLUMNS or x is None or x < 0:
                return [], side  # existing_problems says what is missing
            layers.append((material, x))
        return layers, side

    def existing_problems(self, e, nr):
        """What stops the existing shielding from being used, and the entries to highlight."""
        if not self.existing_on(e, nr):
            return [], []
        incomplete, fields = False, []
        for k in range(1, self.existing_count(e, nr) + 1):
            material = self.d[f"existmat {e}{k}{nr}"].get() if f"existmat {e}{k}{nr}" in self.d else ""
            x = self.entry_number(f"existmm {e}{k}{nr}")
            if material not in MATERIAL_COLUMNS:
                incomplete = True
            if x is None or x < 0:
                incomplete = True
                fields.append(f"existmm_entry {e}{k}{nr}")
        return (["Existing shielding (material and thickness)"], fields) if incomplete else ([], [])

    # ===================== a further area beyond the barrier (NCRP 147 4.1.3) =====================
    def far_on(self, e, nr):
        option = self.d.get(f"far {e}{nr}")
        return option is not None and option.get() == 1

    def far_area(self, e, nr):
        """The further area beyond barrier e: how much further than the person beyond the barrier it is (m), its
        occupancy factor T and its design goal P. None when the option is off or not filled in."""
        if not self.far_on(e, nr):
            return None
        delta, T, P = (self.entry_number(f"{name} {e}{nr}") for name in ("fardist", "farT", "farP"))
        if delta is None or delta < 0 or T is None or not 0 < T <= 1 or P is None or P <= 0:
            return None
        location = self.d.get(f"farloc {e}{nr}")
        location = location.get() if location is not None and location.get() in OCCUPANCY_T else None
        return {"delta": delta, "T": T, "P": P, "location": location}

    def far_problems(self, e, nr):
        """What stops the further area from being used, and the entries to highlight."""
        if not self.far_on(e, nr):
            return [], []
        checks = (("fardist", lambda v: v >= 0), ("farT", lambda v: 0 < v <= 1), ("farP", lambda v: v > 0))
        fields = [f"{name}_entry {e}{nr}" for name, ok in checks
                  if self.entry_number(f"{name} {e}{nr}") is None or not ok(self.entry_number(f"{name} {e}{nr}"))]
        return (["Further area (distance, T and P)"], fields) if fields else ([], [])

    def far_text(self, far):
        """'the area 2 m further (Administrative or clerical offices, T 1, P 0.02)'."""
        where = f"{far['location']}, " if far.get("location") else ""
        return f"the area {far['delta']:g} m further ({where}T {far['T']:g}, P {far['P']:g})"

    @staticmethod
    def layers_text(layers, existing=()):
        """'Concrete 100 mm (existing) + Lead 1 mm': layers from the room side out."""
        existing = list(existing)
        parts = []
        for material, x in layers:
            mark = (material, x) in existing
            if mark:
                existing.remove((material, x))
            parts.append(f"{material} {x:g} mm" + (" (existing)" if mark else ""))
        return " + ".join(parts)

    # ===================== a wall shared by two rooms of a department =====================
    def share_barrier(self, e, nr, t, partner=True):
        """The other areas the barrier protects: a further area beyond it, and on a wall (or door) shared with another
        room of the department the areas of that room. For each material the barrier gets the largest thickness they
        need. partner: the other room's side is calculated again first, if it has been calculated."""
        rec = self.calc[(nr, e)]
        rec.pop("shared", None)
        self.combine_far(e, nr)
        link = self.shared_partner(t, e)
        if link is None:
            return
        t2, e2 = link
        nr2 = self.d[f"nr {t2}"]
        if partner and (nr2, e2) in self.calc:
            state = (self.need, self.need_fields, getattr(self, "last_shield", None), getattr(self, "B", None))
            self.choosetype(e2, nr2, t2, notify=False, partner=False)
            self.need, self.need_fields, self.last_shield, self.B = state
        self.combine_shared(e, nr, t2, e2)

    def barrier_build(self, e, nr):
        """The materials of barrier e, their shares as fractions (None: each alone) and its existing shielding."""
        count = self.d[f"vnumbmat {e}{nr}"].get()
        materials = [self.d[f"vmater {e}{o}{nr}"].get() for o in range(1, count + 1)]
        existing, side = self.existing_shielding(e, nr)
        return materials, self.layer_fractions(e, nr), existing, side

    def set_thicknesses(self, e, nr, values):
        """The thickness of each material of barrier e, in the results and in its record."""
        materials = self.barrier_build(e, nr)[0]
        for o, value in enumerate(values, start=1):
            self.thm[f"xbar {e}{o}{nr}"] = value
        self.calc[(nr, e)]["thickness"] = [(m, x if isinstance(x, float) else None) for m, x in zip(materials, values)
                                           if m != "Select Material"]

    def combine_far(self, e, nr):
        """The further area beyond the barrier (NCRP 147 4.1.3): its thickness of each material, the same barrier for
        a farther person with another T and P, and for each material the larger of the two areas."""
        rec = self.calc[(nr, e)]
        far = rec.get("far")
        if rec["missing"] or not far:
            return
        materials, fractions, existing, side = self.barrier_build(e, nr)
        near = [self.thm.get(f"xbar {e}{o}{nr}") for o in range(1, len(materials) + 1)]
        needed = required_thicknesses(far["components"], far["P"], materials, fractions, existing, side)
        combined, governs = larger_thicknesses(near, needed, "further area")
        far.update(near=near, far=needed, governs=governs)
        self.set_thicknesses(e, nr, combined)

    def combine_shared(self, e, nr, t2, e2):
        """The materials of this barrier as the room on its other side needs them (the same wall seen from there: the
        layers in the reverse order; its further area too), and for each material the larger thickness of the two
        rooms."""
        rec, nr2 = self.calc[(nr, e)], self.d[f"nr {t2}"]
        other = self.calc.get((nr2, e2))
        info = {"room": self.room_name(t2), "barrier": self.barrier_name(e2, nr2), "key": (t2, e2)}
        rec["shared"] = info
        if rec["missing"]:
            info["state"] = "this side"
            return
        if other is None:
            info["state"] = "not calculated"
            return
        if other["missing"] or not other.get("shield") or not other.get("P"):
            info["state"] = "missing"
            return
        materials, fractions, existing, side = self.barrier_build(e, nr)
        seen_from_there = other_side(materials, fractions, existing, side)
        theirs = None
        for components, P in [(other["shield"]["components"], other["P"])] + (
                [(other["far"]["components"], other["far"]["P"])] if other.get("far") else []):
            needed = required_thicknesses(components, P, *seen_from_there)
            if fractions is not None:
                needed = needed[::-1]
            theirs = needed if theirs is None else larger_thicknesses(theirs, needed, info["room"])[0]
        own = [self.thm.get(f"xbar {e}{o}{nr}") for o in range(1, len(materials) + 1)]
        combined, governs = larger_thicknesses(own, theirs, info["room"])
        info.update(state="ok", own=own, other=theirs, governs=governs)
        self.set_thicknesses(e, nr, combined)

    def shared_other(self, rec):
        """The calculation of the room on the other side of a shared barrier, when both sides are calculated."""
        shared = rec.get("shared") or {}
        if shared.get("state") != "ok":
            return None
        t2, e2 = shared["key"]
        return self.calc.get((self.d[f"nr {t2}"], e2))

    # ===================== the dose beyond the barrier, and how many patients it allows =====================
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

    @staticmethod
    def existing_of(rec):
        existing = rec.get("existing") or {}
        return existing.get("layers") or [], existing.get("side") or "outside"

    def built_stacks(self, nr, e, rec):
        """The barrier as it will be built, from the room side out: [layers] with the planned thicknesses (one stack),
        or with the required ones (layers: one stack; each material alone: one stack per material), the existing
        shielding in its place. (stacks, planned)."""
        existing, side = self.existing_of(rec)
        planned = self.planned_layers(nr, e)
        if planned:
            return [barrier_stack(planned, existing, side)], True
        required = [(m, x) for m, x in rec.get("thickness") or [] if x is not None]
        if rec.get("layers"):
            stacks = [barrier_stack(required, existing, side)] if len(required) == len(rec["layers"]) else []
        else:
            stacks = [barrier_stack([(m, x)], existing, side) for m, x in required]
        return stacks, False

    def dose_check(self, nr, e):
        """Weekly air kerma beyond the barrier (x T, like P) with the planned thicknesses (every material given,
        one after the other, as all of them cut the radiation) and the existing shielding, or with the required
        thickness when none is planned, and whether it meets the shielding design goal P. The other areas the
        barrier protects are checked too: a further area ('far') and, on a wall shared with another room, that room's
        side ('other') and its further area ('other_far'). None if not calculated."""
        rec = self.calc.get((nr, e))
        if not rec or rec["missing"] or not rec.get("K_total") or not rec.get("P") or not rec.get("shield"):
            return None
        K, P, shield = rec["K_total"], rec["P"], rec["shield"]
        layered = bool(rec.get("layers"))
        existing, _ = self.existing_of(rec)
        other = self.shared_other(rec)
        stacks, planned = self.built_stacks(nr, e, rec)
        if not stacks_usable(shield["components"], stacks):  # e.g. existing steel in a CT room: no data
            return None
        if planned:
            dose = stack_dose(shield["components"], stacks[0], layered)
            basis = "planned " + self.layers_text(stacks[0], existing)
        elif (existing or other or rec.get("far")) and stacks:  # the least protective material, with what is there
            dose = max(stack_dose(shield["components"], stack, layered) for stack in stacks)
            basis = "required thickness"
        else:
            dose, basis = min(K, P), "required thickness"
        result = {"K": K, "P": P, "dose": dose, "ok": dose <= P * 1.0001, "basis": basis, "transmission": dose / K}
        areas = [("far", "further area", rec.get("far"), False)]
        if other is not None:  # the same wall, from the other room: the layers in the reverse order
            areas += [("other", rec["shared"]["room"], {"components": other["shield"]["components"], "P": other["P"]},
                       True),
                      ("other_far", f"{rec['shared']['room']}, further area", other.get("far"), True)]
        for key, label, area, mirrored in areas:
            if not area or not stacks or not stacks_usable(area["components"], stacks):
                continue
            dose2 = max(stack_dose(area["components"], stack[::-1] if mirrored else stack, layered)
                        for stack in stacks)
            result[key] = {"room": label, "dose": dose2, "P": area["P"], "ok": dose2 <= area["P"] * 1.0001}
            result["ok"] = result["ok"] and result[key]["ok"]
        return result

    def room_key(self, nr):
        """The room (t) whose barriers are keyed by nr."""
        for key, value in self.d.items():
            if key.startswith("nr ") and value == nr:
                return key[3:]
        return None

    def workload_allowed(self, t, factor):
        """'up to 470 patients/week (×3.9 the present workload)': the workload of room t times factor."""
        if factor >= 1000:
            return "more than 1000 × the present workload"
        times = f"×{factor:.2g} the present workload" if factor < 10 else f"×{factor:.0f} the present workload"
        if self.d[f"vselroom {t}"].get() == "CT Room":
            body, head = self.entry_number(f"bp_var {t}") or 0, self.entry_number(f"hp_var {t}") or 0
            parts = [f"{factor * n:.0f} {kind}" for n, kind in ((body, "body"), (head, "head")) if n]
            return f"up to {' + '.join(parts)} procedures/week ({times})" if parts else times
        mode = self.d.get(f"vrawork {t}")
        try:
            mode = mode.get() if mode is not None else 0
        except TclError:
            mode = 0
        if mode == 2 and self.entry_number(f"numpapwe {t}"):
            return f"up to {factor * self.entry_number(f'numpapwe {t}'):.0f} patients/week ({times})"
        if mode == 1 and self.entry_number(f"worentry {t}"):
            return f"up to {factor * self.entry_number(f'worentry {t}'):.4g} mA·min/week ({times})"
        return times

    def allowed_workload(self, nr, e):
        """How far the workload may grow before the dose beyond the barrier reaches P (NCRP 147 6.3.3), with the barrier
        as it will be built: the planned thicknesses and the existing shielding, or the existing shielding alone; in
        every area the barrier protects (a further area too). A shared wall: also the workload of the room on its
        other side. None if the barrier is not calculated."""
        rec = self.calc.get((nr, e))
        if not rec or rec["missing"] or not rec.get("shield") or not rec.get("P") or not rec.get("K_total"):
            return None
        existing, side = self.existing_of(rec)
        planned = self.planned_layers(nr, e)
        if not planned and not existing:
            return {"state": "nothing"}
        stack = barrier_stack(planned, existing, side)
        layered = bool(rec.get("layers"))
        if not stacks_usable(rec["shield"]["components"], [stack]):
            return {"state": "no data"}
        sides = [(self.room_key(nr), rec, stack, "this room")]
        other = self.shared_other(rec)
        if other is not None and stacks_usable(other["shield"]["components"], [stack]):  # the wall from there
            sides.append((rec["shared"]["key"][0], other, stack[::-1], rec["shared"]["room"]))
        rows = []
        for t, side_rec, layers, name in sides:
            # the area beyond the barrier, and the further one: the workload is that of the more demanding
            areas = [(side_rec["shield"]["components"], side_rec["P"], None)]
            if side_rec.get("far") and stacks_usable(side_rec["far"]["components"], [layers]):
                areas.append((side_rec["far"]["components"], side_rec["far"]["P"], "the further area"))
            limits = []
            for components, P, label in areas:
                dose = stack_dose(components, layers, layered)
                limits.append((P / dose if dose > 0 else float("inf"), label))
            factor, label = min(limits, key=lambda item: item[0])
            text = self.workload_allowed(t, factor) + (f", {label} limits it" if label and len(limits) > 1 else "")
            rows.append({"room": name, "factor": factor, "text": text})
        basis = (f"the planned {self.layers_text(stack, existing)}" if planned
                 else f"the existing {self.layers_text(existing)} alone")
        return {"state": "ok", "basis": basis, "rows": rows}

    def patients_lines(self, nr, e):
        """The lines of 'Check how many patients per week the barrier allows': [(text, style)]."""
        allowed = self.allowed_workload(nr, e)
        if allowed is None:
            return [("Press Calculate: the barrier is not calculated yet, or something is missing.", "Muted.TLabel")]
        if allowed["state"] == "nothing":
            return [("Give the existing shielding, or tick 'Check the dose beyond the barrier with a planned "
                     "thickness' and type it: the check uses what the barrier will have.", "Muted.TLabel")]
        if allowed["state"] == "no data":
            return [("The existing shielding has a material without transmission data for this radiation.",
                     "RL.TLabel")]
        style = "OK.TLabel" if all(row["factor"] >= 1 for row in allowed["rows"]) else "RL.TLabel"
        if len(allowed["rows"]) == 1:
            return [(f"With {allowed['basis']}: {allowed['rows'][0]['text']}", style)]
        return [(f"With {allowed['basis']}:", style)] + [(f"   {row['room']}: {row['text']}", style)
                                                          for row in allowed["rows"]]

    def show_patients(self, e, nr, t):
        """The result of 'Check how many patients per week the barrier allows', under it in the barrier tab."""
        label, option = self.d.get(f"patientsres {e}{nr}"), self.d.get(f"checkpatients {e}{nr}")
        if label is None or not label.winfo_exists():
            return
        if option is None or option.get() != 1:
            label.grid_remove()
            return
        lines = self.patients_lines(nr, e)
        label.configure(text="\n".join(text for text, _ in lines), style=lines[0][1])
        label.grid()

    # ===================== the height of the shielding of walls and doors (NCRP 147 2.3.6, 5.8) =====================
    def shielding_height(self, e, nr):
        """How high above the floor the shielding of wall or door e goes: metres, CEILING, or None (the floor and the
        ceiling, or a height that is not a number)."""
        variable = self.d.get(f"height {e}{nr}")
        if variable is None or self.barrier_kind(e, nr) not in ("wall", "door"):
            return None
        text = variable.get().strip()
        if text == CEILING:
            return CEILING
        value = self.entry_number(f"height {e}{nr}")
        return value if value is not None and value > 0 else None

    def height_text(self, e, nr):
        height = self.shielding_height(e, nr)
        if height is None:
            return None
        return "up to the ceiling" if height == CEILING else f"{height:g} m above the floor"

    def height_note(self, e, nr):
        """A wall whose shielding stops below the ceiling when the ceiling needs shielding added to its slab:
        NCRP 147 asks the wall shielding to reach the ceiling shielding (2.3.6, 5.8)."""
        height = self.shielding_height(e, nr)
        ceiling = self.calc.get((nr, 2))
        if height is None or height == CEILING or self.barrier_kind(e, nr) != "wall" or not ceiling \
                or ceiling["missing"] or not ceiling.get("existing"):
            return None
        added = [x for _, x in ceiling.get("thickness") or [] if x is not None]
        if added and min(added) > 0:
            return ("The ceiling needs shielding added to its slab: take the shielding of this wall up to it "
                    "(NCRP 147 2.3.6, 5.8).")
        return None

    def far_line(self, far):
        """The line of the further area in the results: (text, style)."""
        text = f"Also {self.far_text(far)}"
        governs = {g for g in far.get("governs") or [] if g}
        if governs:
            text += (": it governs." if governs == {"other"} else ": the area just beyond governs." if governs == {"this"}
                     else ": each material, the larger of the two.")
        return text, "Muted.TLabel"

    def shared_text(self, shared):
        """The line of a shared wall in the results: (text, style)."""
        name = f"Shared with {shared['room']} · {shared['barrier']}"
        if shared["state"] == "not calculated":
            return f"{name}: press Calculate there too, to add the radiation of that room.", "RL.TLabel"
        if shared["state"] == "missing":
            return f"{name}: it has missing data, so only the radiation of this room is counted.", "RL.TLabel"
        if shared["state"] != "ok":
            return name, "Muted.TLabel"
        governs = {g for g in shared["governs"] if g}
        who = (shared["room"] if governs == {"other"} else "this room" if governs == {"this"}
               else "each material: the larger")
        return f"{name}: the larger thickness of the two rooms ({who} governs).", "Muted.TLabel"

    def show_barrier_result(self, e, nr, t):
        """One row per barrier in the results tab, in barrier order: the thickness of each material,
        or one red line with what is still missing."""
        key = f"resultrow {e}{nr}"
        if self.res.get(key) is not None:
            self.res[key].destroy()
        row = ttk.Frame(self.d[f"resultframe {t}{nr}"])
        row.grid(row=e, column=0, sticky="we", padx=6, pady=4)
        self.res[key] = row
        # the name of the barrier, wrapped when it is long
        self.d[f"resname {e}{nr}"] = ttk.Label(row, text=self.barn[f"lab_bar {e}{nr}"].cget("text"), style="BL2.TLabel",
                                               width=10, wraplength=theme.px(100))
        self.d[f"resname {e}{nr}"].grid(row=0, column=0, sticky="nw")
        rec = self.calc.get((nr, e))
        need = rec["missing"] if rec is not None else self.need
        if need:
            ttk.Label(row, text="Missing: " + "; ".join(need), style="RL.TLabel", wraplength=theme.px(420),
                      justify=LEFT).grid(row=0, column=1, columnspan=2, sticky="w")
            self.show_patients(e, nr, t)
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
        lines = []
        existing, side = self.existing_of(rec or {})
        if existing:
            where = "outside it" if side == "outside" else "on its room side"
            lines.append((f"In addition to the existing {self.layers_text(existing)} (the new materials {where})",
                          "Muted.TLabel"))
        if (rec or {}).get("far"):
            lines.append(self.far_line(rec["far"]))
        if (rec or {}).get("shared"):
            lines.append(self.shared_text(rec["shared"]))
        height_note = self.height_note(e, nr)
        if height_note:
            lines.append((height_note, "RL.TLabel"))
        check = self.dose_check(nr, e)
        if check and check["basis"].startswith("planned"):  # with the planned thickness: is the goal met?
            text = (f"{check['basis'][0].upper() + check['basis'][1:]} → {check['dose']:.3g} mGy/wk beyond, "
                    f"P {check['P']:g}  " + ("✓ met" if check["dose"] <= check["P"] * 1.0001 else "✗ exceeded"))
            for key in ("far", "other", "other_far"):  # the other areas the barrier protects
                area = check.get(key)
                if area:
                    text += (f";  {'toward ' if key != 'far' else ''}{area['room']}: {area['dose']:.3g}, "
                             f"P {area['P']:g}  " + ("✓ met" if area["ok"] else "✗ exceeded"))
            lines.append((text, "OK.TLabel" if check["ok"] else "RL.TLabel"))
        option = self.d.get(f"checkpatients {e}{nr}")
        if option is not None and option.get() == 1:
            lines += self.patients_lines(nr, e)
        for k, (text, style) in enumerate(lines):
            ttk.Label(row, text=text, style=style, wraplength=theme.px(380),
                      justify=LEFT).grid(row=count + 1 + k, column=1, columnspan=2, sticky="w")
        self.show_patients(e, nr, t)
