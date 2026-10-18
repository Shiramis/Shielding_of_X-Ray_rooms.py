"""Built-in example projects, one for each kind of design (department, X-ray, CT and mammography room).

They use NCRP 147 typical values (workloads, kerma, use and occupancy factors, design goals) to show how every
part of the program is filled in. They are illustrations, not the worked examples printed in NCRP Report No. 147.
"""
import json
import os
import sys
import zipfile
from datetime import datetime
from tkinter import filedialog, messagebox

from plan_view import edges, point_segment_distance
from project import FORMAT, VERSION, FILE_TYPES

SCALE = 0.02  # m per plan pixel (the 1 m grid of a floor plan without a drawing)
DESIGN_GOAL = {"Controlled Area": "0.1", "Uncontrolled Area": "0.02"}  # NCRP 147 (mGy/week)
HEIGHT, SOURCE_HEIGHT = 3.0, 1.0  # floor-to-ceiling height and height of the source above the floor (m)
SCATTER = {"leakage + side-scatter": ("1", "1"), "leakage + forward/backscatter": ("1", "2"),
           "side-scatter": ("2", "0"), "forward/backscatter": ("3", "0")}


# ===================== building blocks =====================
def primary(distribution, use, kerma, preshielding=None, use_for_transmission=True):
    """Primary radiation type: NCRP 147 workload distribution, use factor U and kerma K1 (mGy/patient at 1 m)."""
    return {"radiob_w": "1", "setv": "1" if use_for_transmission else "0", "vselxray": "1",
            "vsexroom": distribution, "use_ent": use, "entk": kerma,
            "preshvar": "1" if preshielding else "0", "radiob_pre": {"bucky": "1", "cross-table": "2"}.get(preshielding, "0"),
            "unairkerv": "0", "airkerv": "0", "radiob_leak": "0", "oworkvar": "0"}


def secondary(distribution, scatter, use_for_transmission=False):
    """Secondary radiation type with the NCRP 147 unshielded secondary air kerma."""
    kind, leak = SCATTER[scatter]
    return {"radiob_w": "2", "setv": "1" if use_for_transmission else "0", "vselxray": "1",
            "vsexroom": distribution, "use_ent": None, "entk": None, "preshvar": "0", "radiob_pre": "0",
            "unairkerv": "1", "airkerv": kind, "radiob_leak": leak, "oworkvar": "0"}


def barrier(distance, location, area, materials, radiation=(), ct=False, shares=None, planned=None):
    """One barrier: what is beyond it (NCRP 147 Table 4.1 location -> T, area -> P) and its radiation types.
    shares (%): the materials are layers of one barrier, from the room side outwards.
    planned (mm, one per material, "" for none): the thickness to install, to check the dose beyond it."""
    for item in radiation:
        item["entryd"] = distance
    return {"area": area, "vraoccup": "2", "occupentry": None, "vselocation": location,
            "dikeent": DESIGN_GOAL[area], "dist_var": distance if ct else None, "materials": list(materials),
            "matmode": "combined" if shares else "separate", "shares": list(shares or []),
            "planned": list(planned or []), "checkplan": "1" if any(planned or []) else "0",
            "calculated": True, "radiation": list(radiation)}


def room_geometry(rect, source, door):
    """Rectangle (x0, y0, x1, y1) in metres, source (x, y) and door (x_from, x_to) on the bottom wall.
    Returns the outline (plan pixels), the source (pixels), and the distances (m, as text) source -> top, right,
    bottom, left wall and door."""
    x0, y0, x1, y1 = rect
    px = lambda x, y: [x / SCALE, y / SCALE]
    outline = [px(x0, y0), px(x1, y0), px(x1, y1), px(x0, y1)]
    src = px(*source)
    door_a, door_b = px(door[0], y1), px(door[1], y1)
    distances = [point_segment_distance(src, a, b) * SCALE for a, b in edges([tuple(p) for p in outline])]
    distances.append(point_segment_distance(src, door_a, door_b) * SCALE)
    return outline, src, (door_a, door_b), [f"{d:.2f}" for d in distances]


def plan_room(outline, source, door, beyond, door_beyond, below, above, floor_primary):
    """Floor plan of a room: walls top, right, bottom, left are Barrier 1-4, the door is on the bottom wall."""
    return {"outline": outline, "closed": True,
            "walls": [{"location": location, "area": area, "primary": False} for location, area in beyond],
            "door": {"a": door[0], "b": door[1], "wall": 2, "location": door_beyond[0], "area": door_beyond[1]},
            "source": source, "height": HEIGHT, "source_height": SOURCE_HEIGHT,
            "floor_to_floor": HEIGHT, "floor": {"location": below[0], "area": below[1], "primary": floor_primary},
            "ceiling": {"location": above[0], "area": above[1]}}


UNCONTROLLED, CONTROLLED = "Uncontrolled Area", "Controlled Area"
OFFICES = ("Administrative or clerical offices", UNCONTROLLED)  # T = 1
CONTROL_ROOM = ("X-ray control rooms", CONTROLLED)                # T = 1
CORRIDOR = ("Corridors", UNCONTROLLED)                            # T = 1/5
CORRIDOR_DOOR = ("Corridor doors", UNCONTROLLED)                  # T = 1/8
PATIENT_ROOMS = ("Patient rooms", UNCONTROLLED)                   # T = 1/5
ADJACENT_XRAY = ("Adjacent x-ray rooms", UNCONTROLLED)            # T = 1 (conservative: uncontrolled)
OUTDOORS = ("Outdoor areas with only transient pedestrian or vehicular traffic", UNCONTROLLED)  # T = 1/40
PARKING = ("Unattended parking lots", UNCONTROLLED)               # T = 1/40
OUTDOOR_SEATING = ("Outdoor areas with seating", UNCONTROLLED)    # T = 1/20


# ===================== the three rooms =====================
def xray_room(x=0.0):
    """Radiographic room, 6 m x 5 m: chest bucky on the left wall, outside wall at the top (cross-table),
    control room on the right, corridor and door at the bottom."""
    outline, source, door, (top, right, bottom, left, door_d) = room_geometry((x, 0, x + 6, 5), (x + 2, 2.5),
                                                                                 (x + 4.4, x + 5.6))
    rad_all, rad_floor, chest = "Rad Room (all barriers)", "Rad Room (floor or other barriers)", "Rad Room (chest bucky)"
    walls = ((OUTDOORS, top), (CONTROL_ROOM, right), (CORRIDOR, bottom), (OFFICES, left))
    data = {"barriers": 7, "room": {"vrawork": "2", "worentry": None, "numpapwe": "120"}, "barrier_data": [
        # Floor: primary beam (U = 0.89, K = 5.2 mGy/patient) attenuated by the table bucky
        barrier(f"{SOURCE_HEIGHT:.2f}", *OFFICES, ["Concrete", "Lead"],
                [primary(rad_floor, "0.89", "5.2", "bucky")], planned=["100", ""]),
        barrier(f"{HEIGHT - SOURCE_HEIGHT:.2f}", *PATIENT_ROOMS, ["Concrete", "Lead"],
                [secondary(rad_all, "leakage + forward/backscatter", True)]),
        barrier(door_d, *CORRIDOR_DOOR, ["Lead"], [secondary(rad_all, "leakage + side-scatter", True)]),
        # Barrier 1: cross-table wall, primary (U = 0.09) plus secondary from the rest of the work
        barrier(top, *OUTDOORS, ["Lead", "Concrete"],
                [primary(rad_floor, "0.09", "5.2", "cross-table"), secondary(rad_all, "leakage + side-scatter")]),
        barrier(right, *CONTROL_ROOM, ["Lead", "Gypsum Wallboard"],
                [secondary(rad_all, "leakage + side-scatter", True)], planned=["0.5", ""]),
        # Barrier 3: one standard gypsum board (15.9 mm) is planned, but 38.6 mm are needed: goal exceeded
        barrier(bottom, *CORRIDOR, ["Lead", "Gypsum Wallboard"],
                [secondary(rad_all, "leakage + side-scatter", True)], planned=["", "15.9"]),
        # Barrier 4: chest bucky wall, primary (U = 1, K = 2.3) plus secondary; one wall of concrete (room side)
        # and lead (outside), each giving half of the shielding
        barrier(left, *OFFICES, ["Concrete", "Lead"],
                [primary(chest, "1", "2.3", "bucky"), secondary(rad_all, "leakage + side-scatter")],
                shares=["50", "50"], planned=["100", "1"]),
    ]}
    plan = plan_room(outline, source, door, [w[0] for w in walls], CORRIDOR_DOOR, OFFICES, PATIENT_ROOMS, True)
    return data, plan


def ct_room(x=0.0):
    """CT room, 7 m x 5 m: control room on the left, mammography room on the right, corridor and door at the
    bottom, parking outside the top wall."""
    outline, source, door, (top, right, bottom, left, door_d) = room_geometry((x, 0, x + 7, 5), (x + 3.5, 2.5),
                                                                                 (x + 1.0, x + 2.4))
    materials = ["Lead", "Concrete"]
    # From the isocenter to each barrier; the occupied point beyond it takes the NCRP 147 defaults
    floor_d, ceiling_d = f"{SOURCE_HEIGHT:.2f}", f"{HEIGHT - SOURCE_HEIGHT:.2f}"
    # NCRP 147: every procedure scanned once and 40 % again with contrast (1.4 scans per procedure)
    phases = {"body": ["100", "40"], "head": ["100", "40"]}
    data = {"barriers": 7, "room": {"bp_var": "100", "hp_var": "50", "dlpb_var": "550", "dlph_var": "1200",
                                    "kvp_var": "120", "phases": phases}, "barrier_data": [
        barrier(floor_d, *OFFICES, materials, ct=True),
        barrier(ceiling_d, *PATIENT_ROOMS, materials, ct=True),
        barrier(door_d, *CORRIDOR_DOOR, ["Lead"], ct=True),
        barrier(top, *PARKING, materials, ct=True),
        barrier(right, *ADJACENT_XRAY, materials, ct=True),
        barrier(bottom, *CORRIDOR, materials, ct=True),
        barrier(left, *CONTROL_ROOM, materials, ct=True),
    ]}
    walls = (PARKING, ADJACENT_XRAY, CORRIDOR, CONTROL_ROOM)
    plan = plan_room(outline, source, door, walls, CORRIDOR_DOOR, OFFICES, PATIENT_ROOMS, False)
    return data, plan


def mammography_room(x=0.0):
    """Mammography room, 4 m x 5 m: the unit near the top wall, offices on the right, CT room on the left."""
    outline, source, door, (top, right, bottom, left, door_d) = room_geometry((x, 0, x + 4, 5), (x + 2, 1.5),
                                                                                 (x + 0.4, x + 1.6))
    mammo, materials = "Mammography Room", ["Gypsum Wallboard", "Lead"]
    side = lambda: [secondary(mammo, "leakage + side-scatter", True)]
    data = {"barriers": 7, "room": {"vrawork": "1", "worentry": "536", "numpapwe": None}, "barrier_data": [
        barrier(f"{SOURCE_HEIGHT:.2f}", *OFFICES, ["Concrete", "Lead"],
                [secondary(mammo, "leakage + forward/backscatter", True)]),
        barrier(f"{HEIGHT - SOURCE_HEIGHT:.2f}", *PATIENT_ROOMS, ["Concrete", "Lead"],
                [secondary(mammo, "leakage + forward/backscatter", True)]),
        barrier(door_d, *CORRIDOR_DOOR, ["Lead", "Wood"], side()),
        barrier(top, *OUTDOOR_SEATING, materials, side()),
        barrier(right, *OFFICES, materials, side()),
        barrier(bottom, *CORRIDOR, materials, side()),
        barrier(left, *ADJACENT_XRAY, materials, side()),
    ]}
    walls = (OUTDOOR_SEATING, OFFICES, CORRIDOR, ADJACENT_XRAY)
    plan = plan_room(outline, source, door, walls, CORRIDOR_DOOR, OFFICES, PATIENT_ROOMS, False)
    return data, plan


def plan(rooms):
    return {"image": None, "image_name": "", "scale": SCALE, "rooms": {str(k): r for k, r in enumerate(rooms)}}


def project(*workspaces):
    return {"format": FORMAT, "version": VERSION, "saved": "", "workspaces": list(workspaces)}


def standalone(kind, name, builder):
    data, room_plan = builder()
    return project({"kind": "room", "type": kind, "name": name, "data": data, "plan": plan([room_plan])})


def department():
    # One floor: X-ray room (0-6 m), control room (6-8 m), CT room (8-15 m), mammography room (15-19 m), corridor below
    rooms = [("Rad Room 1", "X-Ray room", xray_room(0)), ("CT Scanner", "CT Room", ct_room(8)),
             ("Mammography", "Mammography Room", mammography_room(15))]
    return project({"kind": "department", "name": "Example Radiology Department",
                    "rooms": [{"name": name, "type": kind, "designed": True, "data": built[0]}
                              for name, kind, built in rooms],
                    "plan": plan([built[1] for _, _, built in rooms])})


NOTE = ("\n\nAll values are NCRP 147 typical values, already calculated. Hover over any field for guidance, "
        "change a value and press Calculate, open 'Floor Plan' or '2D / 3D View', or 'Export to Excel'.")

EXAMPLES = {
    "department": ("Radiology department", department,
                   "A department with three rooms on one floor plan: a radiographic room, a CT room and a "
                   "mammography room, with a shared control room and a corridor.\n"
                   "Shared walls between rooms are 'Adjacent x-ray rooms'; the control room is a controlled area "
                   "(P = 0.1 mGy/week), everything else is uncontrolled (P = 0.02 mGy/week)."),
    "xray": ("X-Ray room", lambda: standalone("X-Ray room", "Example Rad Room", xray_room),
             "Radiographic room, 120 patients/week (NCRP 147 average).\n"
             "• Floor: primary beam, U = 0.89, K = 5.2 mGy/patient, with bucky preshielding.\n"
             "• Barrier 1 (outside wall): cross-table primary, U = 0.09, plus secondary radiation; the primary "
             "is 'Set for the calculation'.\n"
             "• Barrier 4: chest bucky wall, primary U = 1, K = 2.3 mGy/patient, plus secondary. Its materials are "
             "'Layers of one barrier': concrete on the room side and lead outside, half of the shielding each.\n"
             "• Barrier 2: control room (controlled area). Door and Barrier 3: corridor.\n"
             "• Planned thicknesses (under the materials) for the floor, Barriers 2, 3 and 4: open the 2D / 3D View, "
             "choose 'Dose beyond vs goal P' and tick 'Radiation map'. Barrier 3 plans one gypsum board, which is not "
             "enough: the goal is exceeded (red)."),
    "ct": ("CT room", lambda: standalone("CT Room", "Example CT Room", ct_room),
           "CT room, 100 body and 50 head procedures/week, DLP 550 and 1200 mGy·cm per procedure "
           "(NCRP 147 typical values), 120 kVp.\n"
           "Distances are measured from the isocenter; T comes from the location beyond each barrier."),
    "mammography": ("Mammography room", lambda: standalone("Mammography Room", "Example Mammography Room",
                                                            mammography_room),
                    "Mammography room, total workload 536 mA·min/week (80 patients × 6.7 mA·min/patient, NCRP 147 "
                    "average).\nEvery barrier is secondary (the image receptor stops the primary beam); walls use "
                    "leakage + side-scatter, floor and ceiling leakage + forward/backscatter."),
}


# ===================== the examples as files =====================
def examples_folder():
    """'Examples' next to the program: beside the .exe, or in the project folder when run from the code."""
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "Examples")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Examples")


def example_file_name(title):
    return f"Example - {title}.shield"


def write_example_files(folder=None):
    """Write every example as a project file (.shield) that File > Open project can open."""
    folder = folder or examples_folder()
    os.makedirs(folder, exist_ok=True)
    paths = []
    for title, build, description in EXAMPLES.values():
        project = build()
        project.update(saved=datetime.now().isoformat(timespec="seconds"), title=f"Example: {title}",
                       description=description + NOTE)
        path = os.path.join(folder, example_file_name(title))
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("project.json", json.dumps(project, indent=1, ensure_ascii=False))
        paths.append(path)
    return paths


def ensure_example_files():
    """Create the examples folder if it is missing (e.g. a fresh copy of the program). Returns the folder."""
    folder = examples_folder()
    try:
        if not all(os.path.exists(os.path.join(folder, example_file_name(title)))
                   for title, _, _ in EXAMPLES.values()):
            write_example_files(folder)
    except OSError:  # e.g. a read-only installation folder: use the user's Documents instead
        folder = os.path.join(os.path.expanduser("~"), "Documents", "Shielding examples")
        write_example_files(folder)
    return folder


class Examples:
    def open_example(self, key):
        title, build, description = EXAMPLES[key]
        if not self.keep_current_work("Open example"):
            return
        self.build_project(build())
        self.set_project_path(None)
        messagebox.showinfo(f"Example: {title}", description + NOTE, parent=self.master)

    def open_examples_folder(self):
        """Open one of the example files, starting in the examples folder."""
        if not self.keep_current_work("Open example"):
            return
        folder = ensure_example_files()
        path = filedialog.askopenfilename(parent=self.master, title="Open an example", initialdir=folder,
                                          filetypes=FILE_TYPES)
        if path:
            self.open_project_file(path)
