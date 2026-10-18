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
import examples  # noqa: E402
import plan_view  # noqa: E402
import project  # noqa: E402
import report  # noqa: E402

examples.messagebox.showinfo = lambda *a, **k: None  # no pop-ups while capturing
project.messagebox.askyesnocancel = lambda *a, **k: False
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
        rec["preshielding"] = shield.get("pre", {})
        rec["check"] = app.dose_check(nr, e)
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
select_barrier(t, 5, scroll=1.0)
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

# missing data: clear the distance of Barrier 3 and calculate it
select_barrier(t, 6)
d[f"entryd 6{nr}0"].delete(0, "end")
app.choosetype(6, nr, t)
dialog = [w for w in root.winfo_children() if w.winfo_class() == "Toplevel"][-1]
shot("missing_dialog.png", dialog)
dialog.destroy()

# ---------- CT and mammography rooms ----------
app.open_example("ct")
t = next(iter(app.standalone))
record("ct", t, range(1, 8))
inputs, results = room_parts(t)
shot("ct_room.png", root, box=without_title_bar(root), height=720)
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
d[f"vsexroom {e}{nr}0"].set("Digital Breast Tomosynthesis")
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

# ---------- department ----------
app.open_example("department")
info = app.departments[1]
root.update()
info["rooms_note"].select(0)
shot("department_rooms.png", root, box=without_title_bar(root), height=520)
t = info["rooms"][1]
info["rooms_note"].select(d[f"newroomf {t}"])
shot("department_room.png", root)

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
# the note of Barrier 3, as when the pointer rests on it
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
