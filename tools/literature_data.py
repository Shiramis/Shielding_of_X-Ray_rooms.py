"""Workload distributions from the literature, written into 'Data Shielding.xlsx'.

Kirby KM, Schueler BA, Littrell LA, Long Z. Workload and use factor data for a modern digital radiography system.
J Appl Clin Med Phys 2023;24:e13962 (table 3).
    They give the workload spectrum (mA min per patient in 5 kVp bins) of each barrier of a general hospital and of a
    pediatric digital radiography (DR) room, but no air kerma and no transmission. These are made here the way NCRP 147
    made its own (Appendices B and C), from the spectrum:
      primary:   K_P1 = sum K_W1(kVp) W(kVp), with K_W1 of Fig. B.1 (Archer et al. 1994)            (Eq. B.1, B.4)
      scatter:   K_W1 W a1(theta, kVp) 1e-6 F / dF^2, a1 of Fig. C.1, 90 deg side-, 135 deg forward/backscatter,
                 F at dF as NCRP 147 Table 4.7 for the rad room                                     (Eq. C.2, C.5)
      leakage:   150 kVp, 3.3 mA, 0.876 mGy/h at 1 m, 2.32 mm lead housing, rate ~ kVp^2          (Eq. C.6-C.9)
      transmission: the curves of each kVp (Table A.1), weighted by the air kerma of each kVp, fitted to
                 Equation A.2; secondary with 90 degree scatter, as Table C.1
    The kVp of a bin is its highest value (Kirby et al.). The workload of each barrier already includes how often the
    beam points at it, so U = 1 with all the patients of the room. 'All barriers' is the sum of the three spectra.
    Run with --check to see the same code reproduce NCRP 147 Tables 4.5, 4.7, B.1 and C.1 from the NCRP 147 spectra.

Biondi M, Bortoli E, Avitabile R, et al. Radiation shielding calculation for interventional radiology: an updated
workload survey using a dose monitoring software. Phys Med 2024;125:104509 (tables 2 and 3, Eq. 4).
    Workload per patient of five interventional rooms and their fitted secondary transmission (lead, concrete, gypsum
    wallboard), as published. The unshielded secondary air kerma is that of NCRP 147 Table 4.7 for cardiac
    (haemodynamics, electrophysiology) or peripheral angiography (angiography, neuroangiography, vascular surgery)
    times Wsite / Wnorm (their Eq. 4; NCRP 147 4.1.4); the program does this from the sheet 'Biondi 2024'.

Li X, Marschall TA, Yang K, Liu B. Radiation shielding transmission data for modern digital radiography.
Med Phys 2024;51(12):8768-8775 (section 4, figure 5).
    Their example of a workload distribution: the primary beam of the table bucky of an orthopedic room (AGFA DX-D
    600), its transmission through concrete fitted to the Archer equation. Concrete only; no air kerma per patient.
    (Their tables 1 and 2, the transmission at each kVp, are in the sheet 'prim abc DR 600'.)

Chen TR, Tyan YS, Chu CH, Wu MC, Tung CJ. Surveyed data for structural shielding calculations of radiographic x-ray
installations in Taiwan. Health Phys 2013;104(5 Suppl 2):S60-S67 (tables 1, 4, 5, 6).
    Workload toward the floor, the wall bucky and all barriers; their primary air kerma per patient (PCXMC), use factors
    and transmission through lead and concrete, as published. They give no leakage or scatter: it is made from their
    spectra with the NCRP 147 method (Appendix C), as for Kirby et al.

Li X, Zhang D, Liu B. Transmission of broad W/Rh and W/Al (target/filter) x-ray beams operated at 25-49 kVp through
common shielding materials. Med Phys 2012;39(7):4132-4138 (tables I, II).
Li X, Zhang D, Liu B. Workload and transmission data for the installation of a digital breast tomosynthesis system.
Med Phys 2013;40(6):063901 (tables IV(c), V(a), VI).
    Single-kVp transmission of W/Al, W/Rh and W/Ag beams of a Hologic Selenia Dimensions; the transmission and the
    workload per patient of its combined DBT workload. As published.

Judge MA, Keavey E, Phelan N. Scatter radiation intensities around full-field digital mammography units. Br J Radiol
2013;86(1021):20120130 (table 1).
    Maximum scatter at 1 m of one exposure of three units, 4 exposures per patient, as published.

Run from the project folder:  python tools/literature_data.py [--check]     (needs numpy and openpyxl)
"""
import math
import os
import sys

import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import Font

XLSX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Data Shielding.xlsx")
MATERIALS = ["Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass", "Wood"]
COLUMNS = {m: 1 + 3 * k for k, m in enumerate(MATERIALS)}  # first column of (alpha, beta, gamma) in the abc sheets

# ===================== Kirby et al. 2023, table 3 (mA min per patient; the kVp is the top of the bin) =============
KIRBY_KVP = list(range(25, 165, 5))
KIRBY_SPECTRA = {  # (floor, cross-table wall, wall with chest board)
    "general": (
        [0, 0, 0, 0, 4.59e-6, 2.18e-2, 1.47e-2, 1.18e-2, 9.05e-2, 2.38e-1, 1.50e-2, 7.03e-2, 3.24e-2, 1.11e-2, 3.64e-3,
         2.88e-3, 1.37e-3, 8.41e-4, 1.98e-4, 3.28e-3, 1.04e-3, 4.51e-5, 1.29e-5, 2.17e-5, 8.74e-6, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1.43e-6, 2.99e-5, 7.78e-5, 1.17e-2, 1.11e-3, 1.73e-3, 7.90e-2, 1.26e-2, 9.86e-3, 6.24e-3,
         2.54e-3, 1.33e-3, 1.48e-3, 6.91e-4, 7.01e-4, 2.35e-4, 1.66e-4, 1.43e-4, 0, 8.60e-5, 0, 0],
        [0, 0, 0, 0, 0, 0, 4.72e-5, 1.71e-4, 1.47e-3, 9.69e-2, 2.50e-2, 8.75e-2, 2.19e-1, 3.65e-2, 1.95e-2, 8.36e-3,
         2.90e-3, 1.65e-3, 1.49e-3, 1.68e-1, 4.72e-2, 2.07e-3, 8.08e-4, 5.14e-4, 1.07e-4, 3.39e-4, 0, 0]),
    "pediatric": (
        [0, 0, 0, 0, 1.65e-6, 6.41e-3, 6.96e-3, 2.22e-2, 4.14e-2, 7.69e-2, 7.04e-3, 1.80e-3, 5.85e-3, 9.98e-4, 1.32e-5,
         1.98e-4, 5.77e-4, 9.91e-5, 3.30e-6, 7.44e-5, 0, 0, 0, 0, 7.90e-4, 1.16e-5, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1.19e-4, 9.73e-4, 2.94e-4, 1.88e-3, 9.58e-4, 0, 1.65e-5, 0, 7.27e-5, 0, 0, 0, 0,
         0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 9.91e-6, 3.13e-3, 1.10e-2, 3.12e-2, 8.49e-3, 3.33e-3, 9.72e-3, 2.13e-2, 2.28e-4, 8.17e-3,
         7.37e-4, 2.73e-3, 2.36e-4, 2.61e-4, 8.23e-3, 4.96e-6, 3.04e-4, 0, 1.39e-4, 1.65e-6, 0, 0]),
}
KIRBY_PUBLISHED_TOTAL = {"general": (0.52, 0.13, 0.72), "pediatric": (0.17, 0.004, 0.11)}
KIRBY_ROOM = {"general": "DR Room", "pediatric": "Pediatric DR"}
# barrier: (columns of table 3 summed, NCRP 147 field F (cm2) at dF (m) of the matching rad room distribution)
KIRBY_BARRIERS = {"chest bucky": ((2,), 1535, 1.83), "floor": ((0,), 1000, 1.0), "cross-table wall": ((1,), 1000, 1.0),
                  "all barriers": ((0, 1, 2), 1000, 1.0)}
KIRBY_START = {"chest bucky": "Rad Room (chest bucky)", "floor": "Rad Room (floor or other barriers)",
               "cross-table wall": "Rad Room (floor or other barriers)", "all barriers": "Rad Room (all barriers)"}


def kirby_name(practice, barrier):
    return f"{KIRBY_ROOM[practice]} ({barrier}) – Kirby 2023"


# ===================== Biondi et al. 2024, tables 2 and 3 =====================
BIONDI_BINS = ["< 50 kVp", "50-70 kVp", "70-100 kVp", "100-125 kVp", ">= 125 kVp"]
BIONDI = [  # room, workload (mAs per patient) per bin and total, NCRP 147 distribution of Eq. 4, table 3
    ("Angiography", (0.096, 318.608, 5945.228, 891.330, 0.000), 7155.262, "Peripheral Angiography",
     ((2.503, 14.618, 0.904), (0.038, 0.087, 0.558), (0.014, 0.040, 0.995))),
    ("Electrophysiology", (0.004, 3.144, 19.337, 3.654, 0.000), 26.139, "Cardiac Angiography",
     ((2.495, 15.320, 0.891), (0.0387, 0.094, 0.584), (0.014, 0.043, 0.995))),
    ("Haemodynamics", (0.043, 176.373, 1008.623, 79.498, 0.000), 1264.537, "Cardiac Angiography",
     ((2.489, 16.307, 0.884), (0.040, 0.096, 0.571), (0.015, 0.044, 0.978))),
    ("Neuroangiography", (0.033, 162.472, 4065.931, 1841.752, 0.000), 6070.188, "Peripheral Angiography",
     ((2.492, 12.812, 0.897), (0.036, 0.084, 0.594), (0.013, 0.037, 1.023))),
    ("Vascular Surgery", (0.289, 1269.307, 8091.702, 743.746, 0.000), 10105.044, "Peripheral Angiography",
     ((2.492, 16.037, 0.888), (0.040, 0.094, 0.570), (0.014, 0.044, 0.981))),
]


def biondi_name(room):
    return f"{room} – Biondi 2024"


# ===================== Li et al. 2024, section 4: transmission of a workload distribution =====================
LI_ORTHOPEDIC = ("Orthopedic Room, table bucky (DR 600) – Li 2024", {"Concrete": (0.04633, 0.0644, 0.5964)})

# ===================== Chen et al. 2013 (Taiwan radiographic rooms) =====================
# Table 1: mean workload (mA min per patient) per 5 kVp bin, 40 to 140 kVp, toward the floor, the wall (bucky) and all
CHEN_KVP = list(range(25, 145, 5))
CHEN_SPECTRA = {
    "floor": [0, 0, 0, 0.001, 0.005, 0.005, 0.007, 0.011, 0.026, 0.021, 0.054, 0.045, 0.064, 0.037, 0.027, 0.001, 0.000,
              0.001, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    "wall": [0, 0, 0, 0.000, 0.000, 0.002, 0.004, 0.011, 0.011, 0.017, 0.018, 0.004, 0.010, 0.008, 0.003, 0.004, 0.002,
             0.007, 0.005, 0.003, 0.002, 0.000, 0.000, 0.000],
    "all": [0, 0, 0, 0.001, 0.005, 0.008, 0.011, 0.022, 0.037, 0.038, 0.073, 0.049, 0.074, 0.045, 0.030, 0.004, 0.002,
            0.008, 0.006, 0.004, 0.002, 0.000, 0.000, 0.000],
}
CHEN_TOTAL = {"floor": 0.306, "wall": 0.111, "all": 0.417}  # Table 1, total workload (mA min per patient)
# Table 4 (mean of the 13 rooms): unshielded primary air kerma per patient at 1 m (mGy, PCXMC); Table 5: use factors
CHEN_KP1 = {"floor": 0.89, "wall": 0.35, "all": 1.24}
CHEN_USE = {"floor": 0.98, "cross-table wall": 0.02, "wall": 1.00}
# Table 6: transmission fitted to Equation A.2 (lead, concrete); 'all barriers' is the one for secondary barriers
CHEN_FITS = {"floor": {"Lead": (2.9416, 19.5961, 0.6138), "Concrete": (0.0418, 0.1375, 0.4478)},
             "wall": {"Lead": (2.3731, 16.9321, 0.6222), "Concrete": (0.0367, 0.1245, 0.5089)},
             "all": {"Lead": (2.6146, 18.3195, 0.5890), "Concrete": (0.0385, 0.1334, 0.4494)}}
CHEN_NAMES = {"floor": "Rad Room (floor) – Chen 2013", "wall": "Rad Room (chest bucky) – Chen 2013",
              "all": "Rad Room (all barriers) – Chen 2013"}
# the field of NCRP 147 Table 4.7 for the scatter of each (as for Kirby et al.): F (cm2) at dF (m)
CHEN_FIELD = {"floor": (1000, 1.0), "wall": (1535, 1.83), "all": (1000, 1.0)}

# ===================== Li et al. 2012 and 2013: mammography / DBT beams of a Hologic Selenia Dimensions ============
# (alpha, beta, gamma) per kVp of lead, concrete, gypsum wallboard, steel, plate glass, wood (the order of MATERIALS)
LI2012_WAL = {  # Li et al. 2012, Table I: W target, Al filter
    25: [(63.06, 27.09, 0.1490), (0.4283, 0.6450, 0.4340), (0.2180, 0.3308, 0.3798), (11.44, 8.967, 0.2344),
         (0.4733, 0.7575, 0.4454), (0.02190, 0.01372, 0.3181)],
    30: [(25.72, 49.12, 0.1217), (0.2545, 0.4988, 0.3782), (0.1391, 0.2945, 0.4519), (5.831, 9.782, 0.2166),
         (0.2919, 0.6105, 0.4443), (0.01723, 0.01196, 0.4733)],
    35: [(22.20, 42.34, 0.2152), (0.1826, 0.4967, 0.4828), (0.09200, 0.2694, 0.4893), (4.344, 9.436, 0.3310),
         (0.1975, 0.5284, 0.4656), (0.01417, 0.009502, 0.4630)],
    40: [(17.92, 41.58, 0.3201), (0.1379, 0.4620, 0.5482), (0.06727, 0.2510, 0.5468), (2.957, 8.541, 0.3569),
         (0.1492, 0.4492, 0.5028), (0.01244, 0.008440, 0.5356)],
    45: [(12.97, 39.85, 0.3514), (0.1093, 0.4065, 0.5917), (0.05115, 0.2210, 0.5830), (2.297, 8.032, 0.4421),
         (0.1173, 0.4391, 0.5791), (0.01142, 0.008285, 0.7651)],
    49: [(11.50, 37.07, 0.4101), (0.09267, 0.4031, 0.6295), (0.04267, 0.2252, 0.6361), (1.752, 8.332, 0.4704),
         (0.1007, 0.4478, 0.6430), (0.01073, 0.008158, 0.8549)],
}
LI2012_WRH = {  # Li et al. 2012, Table II: W target, Rh filter
    25: [(67.94, 20.96, 0.08503), (0.4906, 0.4668, 0.3878), (0.2432, 0.2539, 0.3153), (13.71, 4.772, 0.1771),
         (0.5308, 0.5201, 0.3626), (0.02429, 0.009839, 0.3314)],
    30: [(49.72, 45.85, 0.2231), (0.2721, 0.6599, 0.2827), (0.1538, 0.3565, 0.3216), (7.870, 12.80, 0.2533),
         (0.3101, 0.7473, 0.3029), (0.01855, 0.01307, 0.2267)],
    35: [(25.61, 82.42, 0.3307), (0.1580, 0.8254, 0.3908), (0.07447, 0.4409, 0.3739), (3.199, 17.11, 0.2814),
         (0.1702, 0.9212, 0.3908), (0.01378, 0.02024, 0.3624)],
    39: [(17.96, 81.68, 0.3821), (0.1376, 0.9611, 0.5957), (0.06656, 0.5080, 0.5791), (3.134, 18.14, 0.4678),
         (0.1485, 1.079, 0.5887), (0.01154, 0.01996, 0.4113)],
}
LI2013_WAG = {  # Li et al. 2013, Table VI: W target, Ag filter
    25: [(67.00, 21.26, 0.2288), (0.4288, 0.5526, 0.4359), (0.2174, 0.2774, 0.3707), (11.15, 7.133, 0.1884),
         (0.4812, 0.6010, 0.4720), (0.02201, 0.01011, 0.3083)],
    30: [(46.95, 33.73, 0.1923), (0.2891, 0.4375, 0.2742), (0.1384, 0.2394, 0.2387), (8.295, 8.655, 0.2527),
         (0.3197, 0.5001, 0.2888), (0.01756, 0.008786, 0.1797)],
    35: [(28.41, 62.94, 0.3201), (0.1541, 0.5974, 0.3090), (0.06557, 0.3031, 0.2593), (5.402, 16.81, 0.5086),
         (0.1514, 0.6343, 0.2725), (0.01186, 0.01312, 0.1603)],
    39: [(15.44, 67.38, 0.2861), (0.1292, 0.6718, 0.4475), (0.06427, 0.3709, 0.4628), (2.956, 14.31, 0.3706),
         (0.1443, 0.7505, 0.4603), (0.01071, 0.01373, 0.2387)],
}
MAMMO_KVP_DATA = {"W/Al (Li 2012)": LI2012_WAL, "W/Rh (Li 2012)": LI2012_WRH, "W/Ag (Li 2013)": LI2013_WAG}
# Li et al. 2013, Table V(a): the primary radiation of the combined DBT workload (W/Rh, W/Ag and W/Al, Table IV(c))
LI2013_DBT = ("Digital Breast Tomosynthesis – Li 2013",
              [(13.33, 65.26, 0.2119), (0.1338, 0.6346, 0.3777), (0.06343, 0.3415, 0.3708), (2.560, 13.66, 0.2724),
               (0.1444, 0.6858, 0.3714), (0.01285, 0.01410, 0.3422)])
LI2013_WNORM = 12.61  # Table IV(c), Sum(2D+3D): mA min per patient, screening and diagnosis
# Table IV(c), screening and diagnosis: (filter, highest kVp of the interval, mA min per patient, K1 mGy per patient)
LI2013_WORKLOAD = [("W/Rh", 25, 0.0660, 0.0405), ("W/Rh", 30, 4.16, 3.70), ("W/Rh", 35, 2.12, 2.38),
                   ("W/Ag", 30, 1.06, 1.24), ("W/Ag", 35, 1.32, 1.78), ("W/Ag", 39, 0.0433, 0.0779),
                   ("W/Al", 30, 0.953, 1.77), ("W/Al", 35, 2.29, 6.07), ("W/Al", 40, 0.542, 1.88),
                   ("W/Al", 45, 0.0550, 0.264)]

# ===================== Judge et al. 2013: scatter around full-field digital mammography units =====================
# Table 1: maximum scatter dose at 1 m of one exposure (uGy; 100 mAs, 13.5 mAs for the Philips); 4 exposures per patient
# (text). The kVp of the Simpkin Mo/Mo data that reproduces their Table 1 (they do not state it): 30, 30 and 35.
JUDGE = [("GE Essential", 6.2, 30), ("Hologic Selenia", 4.5, 30), ("Philips MDM", 1.5, 35)]
JUDGE_EXPOSURES = 4


# ===================== NCRP 147 Appendices B and C =====================
def kerma_per_workload(kvp):
    """K_W1: primary air kerma at 1 m per unit workload (mGy / mA min), NCRP 147 Fig. B.1, W anode / Al filter."""
    return 1.222 - 5.664e-2 * kvp + 1.227e-3 * kvp ** 2 - 3.136e-6 * kvp ** 3


def scatter_fraction(theta, kvp):
    """a1 (x 1e-6, per cm2 of field at 1 m), NCRP 147 Fig. C.1."""
    return 1.6e-2 * (kvp - 125) + 8.43 - 1.11e-1 * theta + 9.83e-4 * theta ** 2 - 1.74e-6 * theta ** 3


def archer(params, x):
    a, b, g = params
    return ((1 + b / a) * np.exp(a * g * x) - b / a) ** (-1 / g)


def archer_thickness(params, transmission):
    a, b, g = params
    return (1 / (a * g)) * math.log((transmission ** (-g) + b / a) / (1 + b / a))


class Tables:
    """The NCRP 147 tables already in the workbook."""

    def __init__(self, wb):
        self.per_kvp, self.prim, self.sec = {}, {}, {}
        for sheet, named in (("prim abc", self.prim), ("sec abc", self.sec)):
            for row in wb[sheet].iter_rows(min_row=3, values_only=True):
                params = {m: tuple(row[c + k] for k in range(3)) for m, c in COLUMNS.items()}
                if isinstance(row[0], str):
                    named[row[0]] = params
                elif sheet == "prim abc" and isinstance(row[0], (int, float)):
                    self.per_kvp[int(row[0])] = params
        self.secondary = {row[0]: row for row in wb["Uns Air Kerma"].iter_rows(min_row=2, values_only=True) if row[0]}

    def at_kvp(self, kvp, material):
        """Table A.1 at kvp; where a material has no data (40 and 45 kVp) the next higher kVp, which is harder."""
        for k in sorted(v for v in self.per_kvp if v >= kvp):
            params = self.per_kvp[k][material]
            if all(isinstance(v, (int, float)) for v in params) and params[0] and params[2]:
                return tuple(float(v) for v in params)
        raise KeyError((kvp, material))


class Spectrum:
    """Air kerma per patient at 1 m and transmission of a workload spectrum {kVp: mA min per patient}."""
    LEAK_RATE, LEAK_KVP, LEAK_MA, HOUSING = 0.876 / 60, 150, 3.3, 2.32  # mGy/min at 1 m, kVp, mA, mm lead

    def __init__(self, tables, spectrum, field=1000.0, field_distance=1.0):
        self.t = tables
        self.w = {v: w for v, w in spectrum.items() if w > 0}
        self.primary = {v: kerma_per_workload(v) * w for v, w in self.w.items()}
        self.field = field / field_distance ** 2
        housing = lambda v: archer(tables.at_kvp(v, "Lead"), self.HOUSING)
        self.leak = {v: self.LEAK_RATE * v ** 2 * housing(v) * w
                        / (self.LEAK_KVP ** 2 * housing(self.LEAK_KVP) * self.LEAK_MA) for v, w in self.w.items()}

    def scatter(self, theta):
        return {v: k * scatter_fraction(theta, v) * 1e-6 * self.field for v, k in self.primary.items()}

    def kerma(self):
        """W, K_P1, leakage, side-scatter, leakage + side, forward/backscatter, leakage + forward (mGy per patient)."""
        leak, side, forward = sum(self.leak.values()), sum(self.scatter(90).values()), sum(self.scatter(135).values())
        return {"W": sum(self.w.values()), "KP1": sum(self.primary.values()), "leak": leak, "side": side,
                "leak+side": leak + side, "forward": forward, "leak+forward": leak + forward}

    def transmission(self, material, x, secondary):
        if not secondary:
            return sum(k * archer(self.t.at_kvp(v, material), x) for v, k in self.primary.items()) \
                / sum(self.primary.values())
        scatter = self.scatter(90)
        # leakage is already hardened by the housing: it falls by its high-attenuation HVL, ln 2 / alpha
        total = sum(scatter[v] * archer(self.t.at_kvp(v, material), x)
                    + self.leak[v] * np.exp(-self.t.at_kvp(v, material)[0] * x) for v in self.w)
        return total / (sum(scatter.values()) + sum(self.leak.values()))

    def fit(self, material, secondary, start, lowest=1e-6):
        """(alpha, beta, gamma) of Equation A.2 fitted to the transmission from 1 down to 'lowest'."""
        step = {"Lead": 0.01, "Steel": 0.05, "Concrete": 1.0, "Gypsum Wallboard": 2.0, "Plate Glass": 1.0,
                "Wood": 10.0}[material]
        x = 0.0
        while self.transmission(material, x, secondary) > lowest and x < 5000 * step:
            x += step
        xs = np.linspace(0, x, 200)
        return fit_archer(xs, np.array([self.transmission(material, v, secondary) for v in xs]), start)


def fit_archer(xs, ys, start):
    """Least squares of ln B (Nelder-Mead, restarted until it settles)."""
    ln_y = np.log(ys)

    def cost(q):
        a, b, g = math.exp(q[0]), q[1], q[2]
        if g <= 0.01:
            return 1e9
        with np.errstate(all="ignore"):
            inner = (1 + b / a) * np.exp(a * g * xs) - b / a
            if np.any(inner <= 0):
                return 1e9
            residual = (-1 / g) * np.log(inner) - ln_y
        return float(np.sum(residual * residual))

    best = np.array([math.log(start[0]), start[1], start[2]], float)
    for size in (0.2, 0.05, 0.05, 0.02, 0.02, 0.01):
        simplex = [best] + [best + np.eye(3)[k] * size * max(abs(best[k]), 0.05) for k in range(3)]
        values = [cost(s) for s in simplex]
        for _ in range(4000):
            order = np.argsort(values)
            simplex, values = [simplex[i] for i in order], [values[i] for i in order]
            centre = np.mean(simplex[:-1], axis=0)
            reflected = centre + (centre - simplex[-1])
            f_reflected = cost(reflected)
            if f_reflected < values[0]:
                expanded = centre + 2 * (centre - simplex[-1])
                f_expanded = cost(expanded)
                simplex[-1], values[-1] = (expanded, f_expanded) if f_expanded < f_reflected else (reflected, f_reflected)
            elif f_reflected < values[-2]:
                simplex[-1], values[-1] = reflected, f_reflected
            else:
                contracted = centre + 0.5 * (simplex[-1] - centre)
                f_contracted = cost(contracted)
                if f_contracted < values[-1]:
                    simplex[-1], values[-1] = contracted, f_contracted
                else:
                    simplex = [simplex[0]] + [simplex[0] + 0.5 * (s - simplex[0]) for s in simplex[1:]]
                    values = [values[0]] + [cost(s) for s in simplex[1:]]
            if abs(values[-1] - values[0]) < 1e-14:
                break
        best = simplex[int(np.argmin(values))]
    return math.exp(best[0]), float(best[1]), float(best[2])


def thickness_difference(reference, fitted, levels=(1e-1, 1e-2, 1e-3, 1e-4, 1e-5)):
    """% difference of the thickness that gives each transmission."""
    return [100 * (archer_thickness(fitted, b) / archer_thickness(reference, b) - 1) for b in levels]


# ===================== check against NCRP 147 =====================
NCRP_SPECTRA = {"Rad Room (all barriers)": 1, "Rad Room (chest bucky)": 2, "Rad Room (floor or other barriers)": 3,
                "Fluoroscopy Tube (R&F room)": 4, "Rad Tube (R&F room)": 5, "Chest Room": 6, "Cardiac Angiography": 8,
                "Peripheral Angiography": 9}  # column of the 'W kVp' sheet (NCRP 147 Table 4.2)
NCRP_PRIMARY = {"Rad Room (chest bucky)": 2.3, "Rad Room (floor or other barriers)": 5.2, "Rad Tube (R&F room)": 5.9,
                "Chest Room": 1.2}  # Table 4.5


def check(wb, tables):
    sheet = wb["W kVp"]
    worst = {}
    for name, column in NCRP_SPECTRA.items():
        spectrum = {int(row[0]): float(row[column] or 0) for row in sheet.iter_rows(min_row=2, values_only=True)
                    if isinstance(row[0], (int, float))}
        ref = tables.secondary[name]
        s = Spectrum(tables, spectrum, ref[2], ref[3])
        k = s.kerma()
        print(f"\n{name}: W {k['W']:.3g} (NCRP {ref[1]}), K_P1 {k['KP1']:.3g} (NCRP {NCRP_PRIMARY.get(name, '-')})")
        print(f"   leakage {k['leak']:.2g} ({ref[4]}), side {k['side']:.2g} ({ref[5]}), "
              f"leakage + side {k['leak+side']:.2g} ({ref[6]}), forward {k['forward']:.2g} ({ref[7]}), "
              f"leakage + forward {k['leak+forward']:.2g} ({ref[8]})")
        for secondary, table in ((False, tables.prim), (True, tables.sec)):
            if not secondary and name not in NCRP_PRIMARY:
                continue
            for material in MATERIALS:
                reference = table[name][material]
                fitted = s.fit(material, secondary, reference)
                diff = thickness_difference(reference, fitted)
                key = ("secondary" if secondary else "primary", material)
                worst[key] = max(worst.get(key, 0), max(abs(d) for d in diff))
                print(f"   {key[0]:9s} {material:16s} fit ({fitted[0]:.4g}, {fitted[1]:.4g}, {fitted[2]:.4g}) "
                      f"NCRP ({reference[0]:.4g}, {reference[1]:.4g}, {reference[2]:.4g})  thickness at B = 1e-1 .. "
                      f"1e-5: " + " ".join(f"{d:+.1f}%" for d in diff))
    print("\nLargest thickness difference from NCRP 147 (B = 0.1 to 1e-5):")
    for (kind, material), value in sorted(worst.items()):
        print(f"   {kind:9s} {material:16s} {value:.1f} %")


# ===================== write the sheets =====================
def replace_sheet(wb, title):
    if title in wb.sheetnames:
        del wb[title]
    return wb.create_sheet(title)


def abc_header(ws, note):
    ws.append([note])
    ws.append(["Workload Distribution"] + sum(([f"{m} α (mm-1)", "β (mm-1)", "γ"] for m in MATERIALS), []))
    for cell in ws[2]:
        cell.font = Font(bold=True)


def write(wb, tables):
    # --- Kirby: the spectra as published, then the kerma and transmission made from them
    ws = replace_sheet(wb, "Kirby 2023")
    ws.append(["Kirby et al., J Appl Clin Med Phys 2023;24:e13962, table 3: workload (mA min per patient) in 5 kVp "
               "bins; the kVp is the highest of the bin"])
    columns = [(p, b) for p in KIRBY_SPECTRA for b in ("floor", "cross-table wall", "chest bucky")]
    ws.append(["kVp"] + [f"{KIRBY_ROOM[p]} ({b})" for p, b in columns])
    for k, kvp in enumerate(KIRBY_KVP):
        ws.append([kvp] + [KIRBY_SPECTRA[p][("floor", "cross-table wall", "chest bucky").index(b)][k]
                           for p, b in columns])
    ws.append(["W total (published)"] + [KIRBY_PUBLISHED_TOTAL[p][("floor", "cross-table wall", "chest bucky").index(b)]
                                         for p, b in columns])
    kerma = replace_sheet(wb, "Kirby 2023 kerma")
    kerma.append(["Made from the sheet 'Kirby 2023' with the NCRP 147 method (Appendices B, C) by "
                  "tools/literature_data.py: air kerma per patient at 1 m (mGy/patient)"])
    kerma.append(["Workload Distribution", "Wnorm (mA min patient-1)", "F (cm2)", "df (m)", "Leakage", "Side-Scatter",
                  "Leakage and Side-Scatter (Ksec)", "Forward/ Backscatter", "Leakage and Forward/ Backscatter (Ksec)",
                  "Primary Kp1"])
    prim, sec = replace_sheet(wb, "Kirby 2023 prim abc"), replace_sheet(wb, "Kirby 2023 sec abc")
    note = ("Transmission of the Kirby 2023 spectra (NCRP 147 method, tools/literature_data.py), fitted to NCRP 147 "
            "Equation A.2")
    abc_header(prim, note + ": primary")
    abc_header(sec, note + ": secondary (90 degree scatter and leakage)")
    for practice in KIRBY_SPECTRA:
        for barrier, (cols, field, distance) in KIRBY_BARRIERS.items():
            spectrum = {v: sum(KIRBY_SPECTRA[practice][c][k] for c in cols) for k, v in enumerate(KIRBY_KVP)}
            s = Spectrum(tables, spectrum, field, distance)
            k = s.kerma()
            name = kirby_name(practice, barrier)
            kerma.append([name, round(k["W"], 4), field, distance] +
                         [float(f"{k[q]:.3g}") for q in ("leak", "side", "leak+side", "forward", "leak+forward")] +
                         [None if barrier == "all barriers" else float(f"{k['KP1']:.3g}")])
            start = KIRBY_START[barrier]
            for secondary, sheet, table in ((False, prim, tables.prim), (True, sec, tables.sec)):
                row = [name]
                for material in MATERIALS:
                    row += [float(f"{v:.4g}") for v in s.fit(material, secondary, table[start][material])]
                sheet.append(row)
                print(f"{name:45s} {'sec ' if secondary else 'prim'} " + " ".join(f"{v:.4g}" for v in row[1:7]))
            print(f"{name:45s} W {k['W']:.3g}  K_P1 {k['KP1']:.3g}  leak+side {k['leak+side']:.3g}  "
                  f"leak+forward {k['leak+forward']:.3g}")
    # --- Biondi: as published
    ws = replace_sheet(wb, "Biondi 2024")
    ws.append(["Biondi et al., Phys Med 2024;125:104509, table 2 (workload, mAs per patient) and Eq. 4 (the NCRP 147 "
               "distribution whose secondary air kerma is scaled by Wsite / Wnorm)"])
    ws.append(["Workload Distribution"] + BIONDI_BINS + ["Total (mAs patient-1)", "Wnorm (mA min patient-1)",
                                                         "NCRP 147 distribution (Eq. 4)"])
    sec = replace_sheet(wb, "Biondi 2024 sec abc")
    abc_header(sec, "Biondi et al. 2024, table 3: secondary transmission (lead, concrete, gypsum wallboard)")
    for room, bins, total, base, params in BIONDI:
        ws.append([biondi_name(room)] + list(bins) + [total, total / 60, base])
        sec.append([biondi_name(room)] + [v for p in params for v in p])
    # --- Chen: table 1 as published; the air kerma per patient: Wnorm table 1, primary table 4 (theirs, PCXMC),
    #     secondary made from their spectra with the NCRP 147 method (Appendix C), as for Kirby; transmission: table 6
    ws = replace_sheet(wb, "Chen 2013")
    ws.append(["Chen et al., Health Phys 2013;104(5 Suppl 2):S60-S67, table 1: mean workload (mA min per patient) per "
               "5 kVp bin, toward the floor, the wall (bucky) and all barriers"])
    ws.append(["kVp", "Floor", "Wall (bucky)", "All barriers"])
    for k, kvp in enumerate(CHEN_KVP):
        ws.append([kvp] + [CHEN_SPECTRA[b][k] for b in ("floor", "wall", "all")])
    ws.append(["W total (published)"] + [CHEN_TOTAL[b] for b in ("floor", "wall", "all")])
    kerma = replace_sheet(wb, "Chen 2013 kerma")
    kerma.append(["Chen et al. 2013: Wnorm table 1, primary Kp1 table 4 (PCXMC); leakage and scatter made from table 1 "
                  "with the NCRP 147 method (Appendix C) by tools/literature_data.py (mGy per patient at 1 m)"])
    kerma.append(["Workload Distribution", "Wnorm (mA min patient-1)", "F (cm2)", "df (m)", "Leakage", "Side-Scatter",
                  "Leakage and Side-Scatter (Ksec)", "Forward/ Backscatter", "Leakage and Forward/ Backscatter (Ksec)",
                  "Primary Kp1", "Kp1 by the NCRP 147 method (not used)"])
    prim, sec = replace_sheet(wb, "Chen 2013 prim abc"), replace_sheet(wb, "Chen 2013 sec abc")
    abc_header(prim, "Chen et al. 2013, table 6: transmission of the primary beam of each workload (lead, concrete)")
    abc_header(sec, "Chen et al. 2013, table 6: 'all barriers', which they use for secondary barriers (lead, concrete)")
    for barrier in ("floor", "wall", "all"):
        field, distance = CHEN_FIELD[barrier]
        k = Spectrum(tables, dict(zip(CHEN_KVP, CHEN_SPECTRA[barrier])), field, distance).kerma()
        kerma.append([CHEN_NAMES[barrier], CHEN_TOTAL[barrier], field, distance] +
                     [float(f"{k[q]:.3g}") for q in ("leak", "side", "leak+side", "forward", "leak+forward")] +
                     [None if barrier == "all" else CHEN_KP1[barrier], float(f"{k['KP1']:.3g}")])
        for sheet, fits in ((prim, CHEN_FITS[barrier]), (sec, CHEN_FITS["all"])):
            sheet.append([CHEN_NAMES[barrier]] + [v for m in MATERIALS for v in fits.get(m, (None, None, None))])
        print(f"{CHEN_NAMES[barrier]:40s} Kp1 NCRP method {k['KP1']:.3g} (Chen {CHEN_KP1[barrier]}), "
              f"leak+side {k['leak+side']:.3g}, leak+forward {k['leak+forward']:.3g}")
    # --- Li 2012 and Li 2013: mammography beams at a kVp, and the DBT workload of Li 2013
    ws = replace_sheet(wb, "Mammography kVp abc")
    ws.append(["Li et al., Med Phys 2012;39:4132 (tables I, II) and Med Phys 2013;40:063901 (table VI): transmission "
               "of broad W/Al, W/Rh and W/Ag beams of a Hologic Selenia Dimensions, per kVp"])
    for data, table in MAMMO_KVP_DATA.items():
        ws.append([data])
        ws.append(["kVp"] + sum(([f"{m} α (mm-1)", "β (mm-1)", "γ"] for m in MATERIALS), []))
        for kvp, params in table.items():
            ws.append([kvp] + [v for p in params for v in p])
    ws = replace_sheet(wb, "Li 2013 DBT abc")
    abc_header(ws, "Li et al., Med Phys 2013;40:063901, table V(a): transmission of the primary radiation of the "
                   f"combined DBT workload (W/Rh, W/Ag, W/Al), table IV(c); Wnorm {LI2013_WNORM} mA min per patient")
    ws.append([LI2013_DBT[0]] + [v for p in LI2013_DBT[1] for v in p])
    # --- Judge 2013: the scatter of three FFDM units
    ws = replace_sheet(wb, "Judge 2013")
    ws.append(["Judge et al., Br J Radiol 2013;86:20120130, table 1: maximum scatter dose at 1 m of one exposure; "
               f"{JUDGE_EXPOSURES} exposures per patient (text)"])
    ws.append(["Unit", "Maximum scatter at 1 m (uGy per exposure)", "Exposures per patient",
               "K1sec (mGy per patient at 1 m)", "kVp of the Mo/Mo transmission (NCRP 147, Simpkin)"])
    for unit, dose, kvp in JUDGE:
        ws.append([unit, dose, JUDGE_EXPOSURES, round(dose * JUDGE_EXPOSURES / 1000, 6), kvp])
    # --- Li 2024: their workload example, as published
    ws = replace_sheet(wb, "Li 2024 workload abc")
    abc_header(ws, "Li et al., Med Phys 2024;51:8768, section 4: transmission of the primary beam of the workload of "
                   "the table bucky of an orthopedic room (AGFA DX-D 600), concrete only")
    name, params = LI_ORTHOPEDIC
    ws.append([name] + [v for material in MATERIALS for v in params.get(material, (None, None, None))])
    for sheet in ("Kirby 2023", "Kirby 2023 kerma", "Biondi 2024", "Chen 2013", "Chen 2013 kerma", "Judge 2013"):
        for cell in wb[sheet][2]:
            cell.font = Font(bold=True)


if __name__ == "__main__":
    workbook = load_workbook(XLSX)
    ncrp = Tables(workbook)
    if "--check" in sys.argv:
        check(workbook, ncrp)
    else:
        write(workbook, ncrp)
        workbook.save(XLSX)
        print("written:", XLSX)
