"""Pictures of the program and the numbers of its examples, for the user guide and the README.

Run on Windows with the program's Python environment, from the project folder:
    venv\\Scripts\\python.exe docs\\capture_screens.py
It opens the program, loads the built-in examples and saves into docs/images:
  - pictures of the program's own windows only (rendered with PrintWindow, so nothing else on the screen appears),
  - example_values.json: the inputs and results of the examples, used by the worked examples of the guide.
Then build the guide with docs/make_user_guide.py.
"""
import ctypes
import ctypes.wintypes
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "XRIFSC_code")
OUT = os.path.join(ROOT, "docs", "images")
os.makedirs(OUT, exist_ok=True)
os.chdir(CODE)
sys.path.insert(0, CODE)

# Start the program without entering its main loop
MAIN = os.path.join(CODE, "Shielding_of_X-Ray_rooms.py")
namespace = {"__name__": "capture", "__file__": MAIN}
source = open(MAIN, encoding="utf-8").read().replace("root.mainloop()", "")
exec(compile(source, MAIN, "exec"), namespace)
app, root = namespace["app"], namespace["root"]

from PIL import Image  # noqa: E402
from matplotlib.backend_bases import MouseEvent  # noqa: E402
from Depcalculations import DBT  # noqa: E402
import examples  # noqa: E402
import plan_view  # noqa: E402
import project  # noqa: E402
import report  # noqa: E402

project.messagebox.showinfo = lambda *a, **k: None  # no pop-ups while capturing
project.messagebox.askyesnocancel = lambda *a, **k: False
app.show_note = lambda *a, **k: None  # the note of an example (captured once, below)
d = app.d
user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32), ("biHeight", ctypes.c_int32),
                ("biPlanes", ctypes.c_uint16), ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32), ("biClrImportant", ctypes.c_uint32)]


def capture(window, settle=True):
    """The window as the program draws it (PrintWindow), and its top-left corner on the screen."""
    if settle:
        window.update()
        window.after(400)
        window.update()
    hwnd = int(window.wm_frame(), 16)
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    hdc = user32.GetWindowDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bitmap = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bitmap)
    user32.PrintWindow(hwnd, mem, 2)  # PW_RENDERFULLCONTENT
    header = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buffer = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, bitmap, 0, h, buffer, ctypes.byref(header), 0)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)
    image = Image.frombuffer("RGBA", (w, h), buffer, "raw", "BGRA", 0, 1).convert("RGB")
    # only what is seen of the window: without the invisible resize borders, which PrintWindow paints black
    seen = ctypes.wintypes.RECT()
    if ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(seen), ctypes.sizeof(seen)) == 0 and \
            rect.left <= seen.left < seen.right <= rect.right and rect.top <= seen.top < seen.bottom <= rect.bottom:
        image = image.crop((seen.left - rect.left, seen.top - rect.top, seen.right - rect.left,
                            seen.bottom - rect.top))
        return image, (seen.left, seen.top)
    return image, (rect.left, rect.top)


def box_of(widget, origin, pad=0):
    x, y = widget.winfo_rootx() - origin[0], widget.winfo_rooty() - origin[1]
    return (max(x - pad, 0), max(y - pad, 0), x + widget.winfo_width() + pad, y + widget.winfo_height() + pad)


def save(name, image):
    image = image.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    image.save(os.path.join(OUT, name), optimize=True)
    print(f"{name:28s} {image.size[0]} x {image.size[1]}")


def shot(name, window, widget=None, box=None, height=None, pad=0):
    """The window, or the part covered by widget / box (window pixels); height: keep only the top part."""
    image, origin = capture(window)
    if widget is not None:
        box = box_of(widget, origin, pad)
    if box is not None:
        image = image.crop(box)
    if height is not None:
        image = image.crop((0, 0, image.width, min(height, image.height)))
    save(name, image)
    return image


def without_title_bar(window):
    image, origin = capture(window)
    return (window.winfo_rootx() - origin[0], window.winfo_rooty() - origin[1],
            window.winfo_rootx() - origin[0] + window.winfo_width(), window.winfo_rooty() - origin[1] + window.winfo_height())


def room_parts(t):
    """Inputs (left pane, without its scroll bar) and results (right pane) of a standalone room."""
    inputs = d[f"frame_1 {t}"].master  # the scrolled canvas of the inputs
    return inputs, d[f"resframe {t}"]


def select_barrier(t, e, scroll=0.0):
    nr = d[f"nr {t}"]
    d[f"noteb {t}{nr}"].select(d[f"barrierf {e}{nr}"])
    root.update()
    d[f"frame_1 {t}"].master.yview_moveto(scroll)
    root.update()


values = {}


def record(key, t, barriers):
    """Inputs and results of some barriers of an example, for the worked examples of the guide."""
    nr = d[f"nr {t}"]
    rows = {}
    for e in barriers:
        rec = dict(app.calc[(nr, e)])
        shield = rec.pop("shield", None) or {}
        rec["params"] = shield.get("params", {})
        # each radiation type: its air kerma, transmission data and preshielding
        rec["components"] = [{"K": c["K"], "params": c["params"], "pre": c["pre"]}
                             for c in shield.get("components", [])]
        rec["preshielding"] = next((c["pre"] for c in shield.get("components", []) if c["pre"]), {})
        rec["check"] = app.dose_check(nr, e)
        rec["allowed"] = app.allowed_workload(nr, e)
        rows[app.barn[f"lab_bar {e}{nr}"].cget("text")] = rec
    values[key] = rows


# ---------- start screen ----------
shot("start.png", root)

# ---------- X-ray room ----------
app.open_example("xray")
t = next(iter(app.standalone))
nr = d[f"nr {t}"]
record("xray", t, range(1, 8))
inputs, results = room_parts(t)
select_barrier(t, 1)
shot("xray_overview.png", root)
shot("xray_floor.png", root, widget=inputs)
shot("xray_results.png", root, widget=results)
select_barrier(t, 5)
shot("xray_secondary.png", root, widget=inputs)
select_barrier(t, 6, scroll=1.0)  # Wall 3: one gypsum board planned, and the check of the patients under Calculate
shot("xray_area.png", root, widget=inputs)
select_barrier(t, 7, scroll=0.42)
shot("xray_layers.png", root, widget=inputs)
select_barrier(t, 1)

# the Excel report of the example
report_path = os.path.join(OUT, "_report.xlsx")
report.write_report(report_path, "Example Rad Room", [app.room_report(t)])
from openpyxl import load_workbook  # noqa: E402
sheet = load_workbook(report_path)["Summary"]
values["xray_report"] = {"header": [c for c in next(sheet.iter_rows(min_row=4, max_row=4, values_only=True))],
                         "rows": [list(r) for r in sheet.iter_rows(min_row=5, values_only=True) if r and r[2]]}
os.remove(report_path)

# missing data: clear the distance of Wall 3 and calculate it
select_barrier(t, 6)
d[f"entryd 6{nr}0"].delete(0, "end")
app.choosetype(6, nr, t)
dialog = [w for w in root.winfo_children() if w.winfo_class() == "Toplevel"][-1]
shot("missing_dialog.png", dialog)
dialog.destroy()

# adding a barrier: the arrow up of 'Number of Barriers' asks for a wall or a door, and its name
d[f"vnumwall {t}"].set(d[f"x {t}"] + 1)
d[f"arrowclicks {t}"] += 1  # a click on the arrow up
app.barrier_count(t)
window = app.barrier_window
window.kind.set("door")
shot("barrier_dialog.png", window)
window.destroy()

# ---------- CT and mammography rooms ----------
app.open_example("ct")
t = next(iter(app.standalone))
record("ct", t, range(1, 8))
inputs, results = room_parts(t)
shot("ct_room.png", root, box=without_title_bar(root), height=720)

# existing shielding: the floor of the CT room is a concrete slab of 100 mm; how much lead must be added to it
nr = d[f"nr {t}"]
e = 1
app.existing_vars(e, nr)
d[f"existing {e}{nr}"].set(1)
d[f"existmat {e}1{nr}"].set("Concrete")
d[f"existmm {e}1{nr}"].set("100")
values["existing"] = {}
for side in ("outside", "inside"):
    d[f"addside {e}{nr}"].set(side)
    app.update_material_panel(e, nr, t)
    app.choosetype(e, nr, t, notify=False)
    rec = app.calc[(nr, e)]
    values["existing"][side] = {"thickness": rec["thickness"], "K_total": rec["K_total"], "P": rec["P"],
                                "d": rec["d"], "params": rec["shield"]["params"]}
select_barrier(t, e, scroll=0.0)
shot("existing_floor.png", root, widget=inputs, height=820)

# a further area: Wall 3 of the X-ray room has a corridor beyond it (T = 1/5) and an office across it, 2 m further
app.open_example("xray")
t = next(iter(app.standalone))
nr = d[f"nr {t}"]
inputs, results = room_parts(t)
e = 6
app.choosetype(e, nr, t, notify=False)
near = app.calc[(nr, e)]
values["further"] = {"near": {"thickness": near["thickness"], "K": near["K_total"], "T": near["T"], "P": near["P"],
                              "d": near["distributions"][0]["d"], "params": near["shield"]["params"]}}
d[f"far {e}{nr}"].set(1)
app.update_far_panel(e, nr, t)
d[f"fardist {e}{nr}"].set("2")
app.choosetype(e, nr, t, notify=False)
rec = app.calc[(nr, e)]
values["further"]["far"] = {"thickness": rec["thickness"], "K": rec["far"]["components"][0]["K"],
                            "T": rec["far"]["T"], "P": rec["far"]["P"], "delta": rec["far"]["delta"],
                            "governs": rec["far"]["governs"], "check": app.dose_check(nr, e),
                            "allowed": app.allowed_workload(nr, e)}
select_barrier(t, e, scroll=1.0)
shot("further_area.png", root, widget=inputs, height=640)

# the field of the scatter: the same wall with a 35 x 43 cm field at 1 m instead of NCRP 147's 1000 cm²
d[f"far {e}{nr}"].set(0)
app.update_far_panel(e, nr, t)
d[f"fieldvar {e}{nr}0"].set(1)
app.field_widgets(e, nr, 0)
d[f"fieldF {e}{nr}0"].set("1505")
app.choosetype(e, nr, t, notify=False)
rec = app.calc[(nr, e)]
values["field"] = {"K1": rec["distributions"][0]["K1"], "K": rec["K_total"], "thickness": rec["thickness"],
                   "params": rec["shield"]["params"], "d": rec["distributions"][0]["d"], "T": rec["T"],
                   "P": rec["P"], "N": rec["distributions"][0]["N"]}
select_barrier(t, e, scroll=0.0)
shot("field_size.png", root, widget=inputs, height=820)
# an air kerma written, for the field of NCRP 147 (1000 cm² at 1 m), scaled to the same 35 x 43 cm field
d[f"unairkerv {e}{nr}0"].set(2)
app.unairk(e, nr, 0)
d[f"entk {e}{nr}0"].insert(0, "0.0345")
d[f"fieldvar {e}{nr}0"].set(1)
app.field_widgets(e, nr, 0)
d[f"fieldF {e}{nr}0"].set("1505")
app.choosetype(e, nr, t, notify=False)
values["field"]["written"] = app.calc[(nr, e)]["distributions"][0]["K1"]
select_barrier(t, e, scroll=0.0)
shot("field_written.png", root, widget=inputs, height=820)
# a secondary radiation type at 100 kVp: the scatter at 90 degrees with the leakage (NCRP 147 Appendix C)
d[f"unairkerv {e}{nr}0"].set(1)
d[f"vselxray {e}{nr}0"].set(2)
app.XrRoom(e, nr, 0)
d[f"vsexroom {e}{nr}0"].set(100)
app.choosetype(e, nr, t, notify=False)
values["angle"] = {"K1": app.calc[(nr, e)]["distributions"][0]["K1"], "kvp": 100,
                   "theta": float(d[f"angle {e}{nr}0"].get()), "F": float(d[f"angleF {e}{nr}0"].get()),
                   "dF": float(d[f"angledF {e}{nr}0"].get())}
select_barrier(t, e, scroll=0.0)
shot("angle_kvp.png", root, widget=inputs, height=820)
app.open_example("mammography")
t = next(iter(app.standalone))
record("mammography", t, range(1, 8))
inputs, results = room_parts(t)
shot("mammo_room.png", root, widget=inputs, height=760)


def fill(key, text):
    d[key].delete(0, "end")
    d[key].insert(0, text)


def beyond_office(t, e, nr):
    """An office (T = 1, uncontrolled area) beyond barrier e."""
    d[f"area {e}{nr}"].set("Uncontrolled Area")
    app.set_design_goal(e, nr)
    d[f"vraoccup {e}{nr}"].set(2)
    app.occupation3(e, nr, t)
    d[f"vselocation {e}{nr}"].set("Administrative or clerical offices")


# digital breast tomosynthesis: the example of Yang et al. 2017 (100 patients/week, 2D + 3D, an office 2 m away)
t = app.creatroom("Mammography Room")
nr = d[f"nr {t}"]
d[f"vname_room {t}"].set("DBT room")
d[f"vrawork {t}"].set(2)
app.workload(t)
fill(f"numpapwe {t}", "100")
e = 4
d[f"radiob_w {e}{nr}0"].set(2)
app.barrier_sel(e, nr, t, 0)
d[f"vsexroom {e}{nr}0"].set(DBT)
app.on_distribution(e, nr, 0)
fill(f"entryd {e}{nr}0", "1.7")
beyond_office(t, e, nr)
d[f"vmater {e}1{nr}"].set("Gypsum Wallboard")
app.choosetype(e, nr, t, notify=False)
record("dbt", t, [e])
inputs, results = room_parts(t)
app.depnote.select(app.standalone[t])  # the room's own tab
select_barrier(t, e)
shot("dbt_barrier.png", root, widget=inputs, height=840)

# transmission data for a kVp: NCRP 147 or modern digital radiography (Li et al. 2024)
t = app.creatroom("X-Ray room")
nr = d[f"nr {t}"]
d[f"vrawork {t}"].set(2)
app.workload(t)
fill(f"numpapwe {t}", "120")
e = 1
d[f"radiob_w {e}{nr}0"].set(1)
app.barrier_sel(e, nr, t, 0)
d[f"vselxray {e}{nr}0"].set(2)
app.XrRoom(e, nr, 0)
d[f"vsexroom {e}{nr}0"].set(80)
fill(f"entryd {e}{nr}0", "1")
fill(f"use_ent {e}{nr}0", "0.89")
fill(f"entk {e}{nr}0", "5.2")
beyond_office(t, e, nr)
d[f"vnumbmat {e}{nr}"].set(2)
app.numbmater(e, nr, t)
d[f"vmater {e}1{nr}"].set("Lead")
d[f"vmater {e}2{nr}"].set("Concrete")
values["kvp_data"] = {}
for data in ("NCRP 147", "DR 600, default filtration (Li 2024)", "DR 600, +1 mm Al +0.1 mm Cu (Li 2024)"):
    d[f"kvpdata {e}{nr}0"].set(data)
    app.choosetype(e, nr, t, notify=False)
    rec = app.calc[(nr, e)]
    values["kvp_data"][data] = {"K_total": rec["K_total"], "thickness": rec["thickness"],
                                "params": rec["shield"]["params"], "d": rec["distributions"][0]["d"]}
inputs, results = room_parts(t)
app.depnote.select(app.standalone[t])  # the room's own tab
select_barrier(t, e)
shot("kvp_data.png", root, widget=inputs, height=520)


def radiation(t, nr, e, kind, distribution, distance):
    d[f"radiob_w {e}{nr}0"].set(kind)
    app.barrier_sel(e, nr, t, 0)
    d[f"vselxray {e}{nr}0"].set(1)
    app.XrRoom(e, nr, 0)
    d[f"vsexroom {e}{nr}0"].set(distribution)
    app.on_distribution(e, nr, 0)
    fill(f"entryd {e}{nr}0", distance)


def lead_and_concrete(t, e, nr):
    d[f"vnumbmat {e}{nr}"].set(2)
    app.numbmater(e, nr, t)
    d[f"vmater {e}1{nr}"].set("Lead")
    d[f"vmater {e}2{nr}"].set("Concrete")


# modern digital radiography (Kirby et al. 2023): floor and chest bucky wall, NCRP 147 and Kirby, 120 patients/week
t = app.creatroom("X-Ray room")
nr = d[f"nr {t}"]
d[f"vname_room {t}"].set("DR room")
d[f"vrawork {t}"].set(2)
app.workload(t)
fill(f"numpapwe {t}", "120")
values["kirby"] = {}
for source, floor, chest in (("NCRP 147", "Rad Room (floor or other barriers)", "Rad Room (chest bucky)"),
                             ("Kirby 2023", "DR Room (floor) – Kirby 2023", "DR Room (chest bucky) – Kirby 2023")):
    radiation(t, nr, 1, 1, floor, "1")  # floor: an office below, 1 m + 1.3 m
    radiation(t, nr, 4, 1, chest, "1.8")  # chest bucky wall: an office, 1.8 m + 0.3 m
    for e in (1, 4):
        beyond_office(t, e, nr)
        lead_and_concrete(t, e, nr)
        app.choosetype(e, nr, t, notify=False)
        rec = app.calc[(nr, e)]
        values["kirby"].setdefault(source, {})[app.barn[f"lab_bar {e}{nr}"].cget("text")] = {
            "distribution": rec["distributions"][0]["distribution"], "U": rec["distributions"][0]["U"],
            "K1": rec["distributions"][0]["K1"], "d": rec["distributions"][0]["d"], "K_total": rec["K_total"],
            "B": rec["B"], "thickness": rec["thickness"], "params": rec["shield"]["params"]}
inputs, results = room_parts(t)
app.depnote.select(app.standalone[t])  # the room's own tab
select_barrier(t, 1)
shot("kirby_floor.png", root, widget=inputs, height=520)

# interventional rooms (Biondi et al. 2024): their example, angiography, 779 procedures a year, 1 mSv a year at 2 m
t = app.creatroom("Fluoroscopy Room")
nr = d[f"nr {t}"]
d[f"vname_room {t}"].set("Angiography room")
d[f"vrawork {t}"].set(1)  # patients are counted whole: the workload of a week, Wsite x 779 / 52
app.workload(t)
fill(f"worentry {t}", f"{7155.262 / 60 * 779 / 52:.6g}")
e = 4
radiation(t, nr, e, 2, "Angiography – Biondi 2024", "1.7")  # + 0.3 m beyond the wall: 2 m
d[f"unairkerv {e}{nr}0"].set(1)
app.unairk(e, nr, 0)
d[f"airkerv {e}{nr}0"].set(1)
app.leakage(e, nr, 0)
d[f"radiob_leak {e}{nr}0"].set(2)  # leakage + forward/backscatter, as their Eq. 4
beyond_office(t, e, nr)
fill(f"dikeent {e}{nr}", "0.01923")  # 1 mSv a year
lead_and_concrete(t, e, nr)
app.choosetype(e, nr, t, notify=False)
record("biondi", t, [e])
# their Eq. 3: the tube output of their Fig. 1 at 50, 70, 100, 125 kVp
d[f"tubeon {e}{nr}0"].set(1)
for v, out in zip((50, 70, 100, 125), ("21", "46", "90", "135")):
    d[f"tube{v} {e}{nr}0"].set(out)
app.field_widgets(e, nr, 0)
app.choosetype(e, nr, t, notify=False)
record("biondi_tube", t, [e])
inputs, results = room_parts(t)
app.depnote.select(app.standalone[t])
select_barrier(t, e)
shot("biondi_barrier.png", root, widget=inputs, height=640)

# a worked example of NCRP 147, opened from its file, with the note that comes with it
del app.show_note
app.open_project_file(os.path.join(ROOT, "Examples", "NCRP 147", "5.3 Radiographic room.shield"))
note = [w for w in root.winfo_children() if w.winfo_class() == "Toplevel"][-1]
shot("ncrp_note.png", note)
note.destroy()
app.show_note = lambda *a, **k: None
t = next(iter(app.standalone))
inputs, results = room_parts(t)
select_barrier(t, 7)
shot("ncrp_results.png", root, widget=results)

# secondary radiation x (1 - U) on the cross-table wall of NCRP 147 5.3.5 (Wall 4: primary U = 0.09 and secondary)
nr = d[f"nr {t}"]
lead_before = dict(app.calc[(nr, 7)]["thickness"])["Lead"]
d[f"oneminusu 7{nr}"].set(1)
app.choosetype(7, nr, t, notify=False)
rec = app.calc[(nr, 7)]
values["share"] = {"before": lead_before, "after": dict(rec["thickness"])["Lead"],
                   "K": [dist["K"] for dist in rec["distributions"]], "U": 0.09}
frame = d[f"frame_1 {t}"]
root.update()
top = d[f"label_B 7{nr}1"].winfo_rooty() - frame.winfo_rooty()  # from radiation type #2 down
frame.master.yview_moveto(max(0.0, (top - 10) / frame.winfo_height()))
root.update()
shot("share_option.png", root, widget=inputs, height=820)
d[f"oneminusu 7{nr}"].set(0)
app.choosetype(7, nr, t, notify=False)

# NCRP 147 5.3.3.2 with the side-scatter of the chest patient at 30 degrees ('At an angle', under 'Field size')
e = next(k for k in range(1, d[f"x {t}"] + 1) if app.barrier_name(k, nr) == "Wall 2, scatter at 30°")
select_barrier(t, e)
top = d[f"label_B {e}{nr}1"].winfo_rooty() - frame.winfo_rooty()  # from radiation type #2 down
frame.master.yview_moveto(max(0.0, (top - 10) / frame.winfo_height()))
root.update()
shot("angle_option.png", root, widget=inputs, height=560)

# ---------- department ----------
app.open_example("department")
info = app.departments[1]
root.update()
info["rooms_note"].select(0)
shot("department_rooms.png", root, box=without_title_bar(root), height=520)
t = info["rooms"][1]
info["rooms_note"].select(d[f"newroomf {t}"])
shot("department_room.png", root)

# the wall shared by the CT room (Wall 2) and the mammography room (Wall 4)
ct, mammo = info["rooms"][1], info["rooms"][2]
values["shared"] = {}
for room, e in ((ct, 5), (mammo, 7)):
    nr = d[f"nr {room}"]
    rec = app.calc[(nr, e)]
    component = rec["shield"]["components"][0]
    values["shared"][app.room_name(room)] = {
        "barrier": app.barrier_name(e, nr), "K": component["K"], "P": rec["P"], "T": rec["T"],
        "params": component["params"], "own": rec["shared"]["own"], "other": rec["shared"]["other"],
        "thickness": rec["thickness"], "check": app.dose_check(nr, e)}
nr = d[f"nr {ct}"]
d[f"noteb {ct}{nr}"].select(d[f"barrierf 5{nr}"])
root.update()
window = app.barrier_dialog(ct, 5, near=d[f"noteb {ct}{nr}"])
shot("shared_dialog.png", window)
window.destroy()
shot("shared_results.png", root, widget=d[f"resframe {ct}"], height=560)

# ---------- floor plan ----------
editor = plan_view.PlanEditor(app, ("dep", 1), "Example Radiology Department", app.workspace_rooms(("dep", 1)),
                              info["rooms"][0])
editor.update()
editor.fit()
editor.select(("wall", 3))
shot("plan_editor.png", editor)
editor.destroy()
viewer = plan_view.RoomViewer(app, ("dep", 1), "Example Radiology Department")
shot("viewer_department.png", viewer)
viewer.destroy()

# ---------- 2D / 3D view of the X-ray room ----------
app.open_example("xray")
t = next(iter(app.standalone))
viewer = plan_view.RoomViewer(app, ("room", t), "Example Rad Room")
shot("viewer_materials.png", viewer)
# the note of Wall 3, as when the pointer rests on it
g = viewer.geometries[0]
a, b = next((a, b) for e, a, b in g["walls"] if e == 6)
canvas = viewer.figures["2D plan"][1]
x, y = viewer.ax2d.transData.transform(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
viewer.hide_note = lambda: None
viewer.on_hover(MouseEvent("motion_notify_event", canvas, x, y), "2D plan")
viewer.note.update()
note, _ = capture(viewer.note, settle=False)
image, origin = capture(viewer)
widget = canvas.get_tk_widget()
image.paste(note, (widget.winfo_rootx() - origin[0] + int(x) + 18,
                   widget.winfo_rooty() - origin[1] + int(widget.winfo_height() - y) + 18))
save("viewer_note.png", image)
viewer.note.withdraw()
viewer.mode.set("Dose beyond vs goal P")
viewer.show_radiation.set(True)
viewer.draw()
shot("viewer_goal.png", viewer)
viewer.mode.set("Materials")
viewer.show_radiation.set(False)
viewer.show_ceiling.set(False)
viewer.draw()
widget.master.master.select(1)  # the 3D tab
shot("viewer_3d.png", viewer)
viewer.destroy()

with open(os.path.join(OUT, "example_values.json"), "w", encoding="utf-8") as file:
    json.dump(values, file, indent=1, default=str)
print("example_values.json")
root.destroy()
