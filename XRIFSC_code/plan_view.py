import math
import os
from tkinter import *
from tkinter import ttk, filedialog, messagebox, simpledialog
import theme

from PIL import Image, ImageTk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.colors import LogNorm, to_rgba
import matplotlib.lines
import numpy as np
from matplotlib.cm import ScalarMappable
from matplotlib.patches import Patch, Polygon as PolygonPatch
from matplotlib.path import Path as MplPath
from matplotlib.transforms import offset_copy
from mpl_toolkits.mplot3d import proj3d
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from Depcalculations import wb, archer_transmission, stack_transmission
from Department_defs import OCCUPANCY_LOCATIONS, DESIGN_GOALS
from barrier_names import DOOR_HEIGHT
from tooltips import tip

DEFAULT_SCALE = 0.02          # m per plan pixel when no drawing is loaded (50 px = 1 m)
DEFAULT_HEIGHT = 2.8          # floor-to-ceiling height (m)
DEFAULT_SOURCE_HEIGHT = 1.0   # height of the source / isocenter above the floor (m)
SCHEMATIC_DISTANCE = 2.5      # wall distance used in a schematic room when none is entered (m)
DEFAULT_FLOOR_TO_FLOOR = 3.0  # floor of this room to the floor of the room above, also below (m)
AREAS = ["Controlled Area", "Uncontrolled Area", "Supervised Area"]
MATERIALS = ["Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass", "Wood"]
SHORT = {"Lead": "Pb", "Concrete": "Concrete", "Gypsum Wallboard": "Gypsum", "Steel": "Steel",
         "Plate Glass": "Glass", "Wood": "Wood"}
OCCUPANCY_T = {row[0]: row[1] for row in wb['Occupancy Factor ( T )'].iter_rows(min_row=2, max_col=2, values_only=True)
               if row[0]}
NO_SHIELDING = "#cfe8cf"
GOAL_MET, GOAL_EXCEEDED = "#43a047", "#e53935"
NOT_CALCULATED = "#d9d9d9"
WALL_COLOR, SELECTED_COLOR, DOOR_COLOR, OTHER_COLOR = "#1f3b73", "#f28c28", "#8b5a2b", "#9a9a9a"

MODE_NOTES = {
    "select": "Click a wall, a door or nothing to edit what is beyond it.\n"
              "Wheel: zoom   ·   Right-drag: move the plan",
    "outline": "Click the corners of the room in order. Click the first corner (or press Enter) to close it.\n"
               "Backspace: undo the last corner   ·   Esc: cancel   ·   'Straight walls' snaps to 90°",
    "source": "Click where the X-ray source is (CT: the isocenter; mammography: the unit).",
    "door": "Click the two edges of the door, on the same wall. Every door traced is one more door of the room.",
    "scale": "Click two points whose real distance you know (e.g. a dimension line), then type it in metres.",
}


# ===================== geometry =====================
def point_segment_distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    if length2 == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    u = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2))
    return math.hypot(p[0] - (a[0] + u * dx), p[1] - (a[1] + u * dy))


def project_on_segment(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy or 1e-12
    u = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2))
    return (a[0] + u * dx, a[1] + u * dy)


def edges(points):
    return [(points[i], points[(i + 1) % len(points)]) for i in range(len(points))]


def centroid(points):
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in edges(points):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(area) < 1e-12:
        return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))
    return (cx / (3 * area), cy / (3 * area))


def inward(a, b, inside, distance):
    """Point at the middle of wall a-b, moved towards the inside of the room (outside if distance < 0)."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    nx, ny = -(b[1] - a[1]), b[0] - a[0]
    length = math.hypot(nx, ny) or 1
    nx, ny = nx / length, ny / length
    if (inside[0] - mx) * nx + (inside[1] - my) * ny < 0:
        nx, ny = -nx, -ny
    return (mx + distance * nx, my + distance * ny)


def schematic_outline(distances):
    """Convex room around the source (0, 0) whose wall k lies at distance distances[k] (clockwise from the top)."""
    n = len(distances)
    lines = []
    for k, d in enumerate(distances):
        angle = math.pi / 2 - 2 * math.pi * k / n
        lines.append((math.cos(angle), math.sin(angle), d))
    corners = []
    for k in range(n):
        (a1, b1, c1), (a2, b2, c2) = lines[k - 1], lines[k]
        det = a1 * b2 - a2 * b1
        corners.append(((c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det))
    return corners  # wall k runs from corners[k] to corners[k + 1]


def shared_wall(a, b, other_points, tolerance):
    """True if the wall a-b lies along a wall of another room (both within tolerance and parallel)."""
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    for c, d in edges(other_points):
        if point_segment_distance(mid, c, d) <= tolerance:
            cross = (b[0] - a[0]) * (d[1] - c[1]) - (b[1] - a[1]) * (d[0] - c[0])
            norm = math.hypot(b[0] - a[0], b[1] - a[1]) * math.hypot(d[0] - c[0], d[1] - c[1]) or 1
            if abs(cross) / norm < 0.1:
                return True
    return False


def suggested_area(location):
    # Conservative: only an X-ray control room is treated as controlled
    return "Controlled Area" if location == "X-ray control rooms" else "Uncontrolled Area"


def load_drawing(path, parent):
    """Load a floor plan as a PIL image: PNG/JPG directly, PDF via PyMuPDF (asks for the page)."""
    if path.lower().endswith(".pdf"):
        import pymupdf
        document = pymupdf.open(path)
        page = 1
        if document.page_count > 1:
            page = simpledialog.askinteger("Floor plan", f"The PDF has {document.page_count} pages.\nWhich page?",
                                           initialvalue=1, minvalue=1, maxvalue=document.page_count, parent=parent)
            if page is None:
                return None
        pdf_page = document[page - 1]
        zoom = min(3.0, 4000 / max(pdf_page.rect.width, pdf_page.rect.height))
        pixmap = pdf_page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    image = Image.open(path)
    image.load()
    return image.convert("RGB")


def maximize(window):
    # Fill the screen, whatever its size, so the side panel always fits
    try:
        window.state("zoomed")
    except TclError:
        window.geometry(f"{window.winfo_screenwidth() - 40}x{window.winfo_screenheight() - 80}+10+10")


def room_doors(room):
    """The doors traced in a room of the floor plan (older plans have one 'door')."""
    if "doors" not in room:
        door = room.pop("door", None)
        room["doors"] = [door] if door else []
    return room["doors"]


def new_room_plan():
    return {"outline": [], "closed": False, "walls": [], "doors": [], "source": None,
            "height": DEFAULT_HEIGHT, "source_height": DEFAULT_SOURCE_HEIGHT, "floor_to_floor": DEFAULT_FLOOR_TO_FLOOR,
            "floor": {"location": "", "area": "", "primary": True}, "ceiling": {"location": "", "area": ""}}


# ===================== floor plan editor =====================
class PlanEditor(Toplevel):
    def __init__(self, app, key, title, rooms, room=None):
        super().__init__(app.master)
        self.app, self.key, self.rooms = app, key, rooms
        self.plan = app.plans.setdefault(key, {"image": None, "image_name": "", "scale": DEFAULT_SCALE, "rooms": {}})
        self.title(f"Floor plan: {title}")
        maximize(self)
        self.zoom, self.origin = 1.0, [0.0, 0.0]
        self.points = []          # pending clicks for scale / door
        self.selected = None      # ("wall", i) or ("door", k)
        self.photo = None
        self.pan_start = None
        self.mode = StringVar(value="select")
        self.ortho = BooleanVar(value=True)

        # ----- toolbar -----
        bar = ttk.Frame(self)
        bar.pack(side=TOP, fill=X)
        tip(ttk.Button(bar, text="Load drawing (PDF / PNG / JPG)", command=self.load_plan), "plan_load").pack(
            side=LEFT, padx=5, pady=5)
        ttk.Button(bar, text="Fit to window", command=self.fit).pack(side=LEFT, padx=5, pady=5)
        self.scale_text = StringVar()
        ttk.Label(bar, textvariable=self.scale_text, style="AL.TLabel").pack(side=LEFT, padx=15)
        self.note = Label(bar, justify=LEFT, background="#fff8d6", relief=SOLID, borderwidth=1, padx=8, pady=4,
                          font=theme.BASE, anchor="w")
        self.note.pack(side=LEFT, fill=X, expand=1, padx=10, pady=5)

        # ----- canvas and side panel -----
        body = ttk.Frame(self)
        body.pack(fill=BOTH, expand=1)
        side = ttk.Frame(body, width=360)
        side.pack(side=RIGHT, fill=Y, padx=5)
        self.canvas = Canvas(body, background="#ffffff", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(side=LEFT, fill=BOTH, expand=1)
        self.build_side_panel(side)

        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Double-Button-1>", lambda e: self.close_outline())
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        for button in ("2", "3"):
            self.canvas.bind(f"<ButtonPress-{button}>", self.pan_begin)
            self.canvas.bind(f"<B{button}-Motion>", self.pan_move)
        self.bind("<Return>", lambda e: self.close_outline())
        self.bind("<Escape>", lambda e: self.cancel())
        self.bind("<BackSpace>", lambda e: self.undo_point())
        self.bind("<Delete>", lambda e: None if e.widget.winfo_class() in ("TEntry", "Entry", "TCombobox")
                  else self.remove_door())  # not while typing in a field

        names = [app.room_name(t) for t in rooms]
        self.room_box["values"] = names
        self.room_box.current(rooms.index(room) if room in rooms else 0)
        self.on_room_change()
        self.mode.trace_add("write", lambda *a: self.on_mode_change())
        self.on_mode_change()
        self.after(60, self.fit)

    # ----- side panel -----
    def build_side_panel(self, side):
        box = ttk.LabelFrame(side, text="Room")
        box.pack(fill=X, pady=4)
        self.room_box = ttk.Combobox(box, state="readonly", width=32)
        self.room_box.grid(row=0, column=0, columnspan=2, padx=5, pady=4, sticky="w")
        self.room_box.bind("<<ComboboxSelected>>", lambda e: self.on_room_change())
        self.height_var, self.source_height_var, self.storey_var = StringVar(), StringVar(), StringVar()
        for row, (text, var, key) in enumerate((("Floor-to-ceiling height (m):", self.height_var, "plan_height"),
                                                ("Source height above floor (m):", self.source_height_var,
                                                 "plan_source_height"),
                                                ("Floor-to-floor height (m):", self.storey_var,
                                                 "plan_floor_to_floor")), start=1):
            label = ttk.Label(box, text=text)
            label.grid(row=row, column=0, padx=5, pady=2, sticky="w")
            entry = ttk.Entry(box, textvariable=var, width=8)
            entry.grid(row=row, column=1, padx=5, pady=2, sticky="w")
            tip(label, key)
            tip(entry, key)
            var.trace_add("write", lambda *a: self.store_heights())

        box = ttk.LabelFrame(side, text="Tools")
        box.pack(fill=X, pady=4)
        for row, (text, value, key) in enumerate((("Select a wall / door", "select", "plan_select"),
                                                   ("Draw walls", "outline", "plan_outline"),
                                                   ("Place source", "source", "plan_source"),
                                                   ("Add door", "door", "plan_door"),
                                                   ("Set scale", "scale", "plan_scale"))):
            tip(ttk.Radiobutton(box, text=text, variable=self.mode, value=value), key).grid(
                row=row, column=0, padx=5, pady=1, sticky="w")
        ttk.Checkbutton(box, text="Straight walls (90°)", variable=self.ortho).grid(row=0, column=1, padx=5, sticky="w")
        tip(ttk.Button(box, text="Clear walls", command=self.clear_outline), "plan_clear").grid(
            row=1, column=1, padx=5, sticky="w")
        tip(ttk.Button(box, text="Remove door", command=self.remove_door), "plan_remove_door").grid(
            row=3, column=1, padx=5, sticky="w")

        box = ttk.LabelFrame(side, text="Selected wall or door")
        box.pack(fill=X, pady=4)
        self.sel_title = StringVar(value="Nothing selected")
        ttk.Label(box, textvariable=self.sel_title, style="BL2.TLabel").grid(row=0, column=0, columnspan=2,
                                                                            padx=5, pady=2, sticky="w")
        self.location_var, self.area_var, self.primary_var = StringVar(), StringVar(), BooleanVar()
        ttk.Label(box, text="Beyond it:").grid(row=1, column=0, padx=5, sticky="w")
        self.location_box = ttk.Combobox(box, textvariable=self.location_var, values=OCCUPANCY_LOCATIONS,
                                         state="readonly", width=30)
        self.location_box.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        tip(self.location_box, "plan_beyond")
        ttk.Label(box, text="Area:").grid(row=2, column=0, padx=5, sticky="w")
        self.area_box = ttk.Combobox(box, textvariable=self.area_var, values=AREAS, state="readonly", width=30)
        self.area_box.grid(row=2, column=1, padx=5, pady=2, sticky="w")
        tip(self.area_box, "area")
        self.primary_check = ttk.Checkbutton(box, text="Primary beam on this wall (e.g. chest bucky)",
                                             variable=self.primary_var, command=self.store_selection)
        self.primary_check.grid(row=3, column=0, columnspan=2, padx=5, sticky="w")
        tip(self.primary_check, "plan_primary")
        self.location_box.bind("<<ComboboxSelected>>", lambda e: self.on_location())
        self.area_box.bind("<<ComboboxSelected>>", lambda e: self.store_selection())
        self.suggestion = Label(box, justify=LEFT, background="#fff8d6", relief=SOLID, borderwidth=1,
                                wraplength=theme.px(330), padx=6, pady=4, font=theme.SMALL, anchor="w")
        self.suggestion.grid(row=4, column=0, columnspan=2, padx=5, pady=4, sticky="we")
        tip(ttk.Button(box, text="Apply to this barrier", command=self.apply_selected), "plan_apply").grid(
            row=5, column=0, columnspan=2, padx=5, pady=4, sticky="w")

        box = ttk.LabelFrame(side, text="Floor and ceiling")
        box.pack(fill=X, pady=4)
        self.floor_location, self.floor_area = StringVar(), StringVar()
        self.ceiling_location, self.ceiling_area = StringVar(), StringVar()
        self.floor_primary = BooleanVar(value=True)
        for row, (text, loc, area) in enumerate((("Below:", self.floor_location, self.floor_area),
                                                 ("Above:", self.ceiling_location, self.ceiling_area))):
            ttk.Label(box, text=text).grid(row=2 * row, column=0, padx=5, sticky="w")
            loc_box = ttk.Combobox(box, textvariable=loc, values=OCCUPANCY_LOCATIONS, state="readonly", width=30)
            loc_box.grid(row=2 * row, column=1, padx=5, pady=2, sticky="w")
            area_box = ttk.Combobox(box, textvariable=area, values=AREAS, state="readonly", width=30)
            area_box.grid(row=2 * row + 1, column=1, padx=5, pady=2, sticky="w")
            tip(loc_box, "plan_beyond")
            tip(area_box, "area")
            loc_box.bind("<<ComboboxSelected>>", lambda e, l=loc, a=area: (
                a.set(a.get() or suggested_area(l.get())), self.store_floor_ceiling()))
            area_box.bind("<<ComboboxSelected>>", lambda e: self.store_floor_ceiling())
        self.floor_primary_check = ttk.Checkbutton(box, text="Primary beam on the floor", variable=self.floor_primary,
                                                   command=self.store_floor_ceiling)
        self.floor_primary_check.grid(row=4, column=0, columnspan=2, padx=5, sticky="w")

        tip(ttk.Button(side, text="Apply everything to the room", command=self.apply_all), "plan_apply_all").pack(
            fill=X, pady=8)
        tip(ttk.Button(side, text="2D / 3D View", command=lambda: self.app.open_view(self.key)), "view_3d").pack(
            fill=X)

    # ----- state helpers -----
    @property
    def t(self):
        return self.rooms[self.room_box.current()]

    def room_plan(self, t=None):
        room = self.plan["rooms"].setdefault(self.t if t is None else t, new_room_plan())
        room_doors(room)
        return room

    def room_type(self):
        return self.app.d[f"vselroom {self.t}"].get()

    def metres(self, pixels):
        return pixels * self.plan["scale"] if self.plan["scale"] else None

    def on_room_change(self):
        self.selected = None  # the selection belonged to the previous room
        room = self.room_plan()
        room.setdefault("floor_to_floor", max(DEFAULT_FLOOR_TO_FLOOR, room["height"]))  # older plans
        # while the fields show this room, they must not store the previous room's values into it
        self.showing_room = True
        self.height_var.set(f"{room['height']:g}")
        self.source_height_var.set(f"{room['source_height']:g}")
        self.storey_var.set(f"{room['floor_to_floor']:g}")
        self.showing_room = False
        self.floor_location.set(room["floor"]["location"])
        self.floor_area.set(room["floor"]["area"])
        self.floor_primary.set(room["floor"].get("primary", True))
        self.ceiling_location.set(room["ceiling"]["location"])
        self.ceiling_area.set(room["ceiling"]["area"])
        xray = self.room_type() in ("X-Ray room", "Fluoroscopy Room")
        for widget in (self.primary_check, self.floor_primary_check):
            widget.state(["!disabled"] if xray else ["disabled"])
        self.points = []
        self.select(None)

    def store_heights(self):
        if getattr(self, "showing_room", False):
            return
        room = self.room_plan()
        for key, var in (("height", self.height_var), ("source_height", self.source_height_var),
                         ("floor_to_floor", self.storey_var)):
            try:
                room[key] = float(var.get())
            except ValueError:
                pass
        self.update_panel()

    def store_floor_ceiling(self):
        room = self.room_plan()
        room["floor"].update(location=self.floor_location.get(), area=self.floor_area.get(),
                             primary=self.floor_primary.get())
        room["ceiling"].update(location=self.ceiling_location.get(), area=self.ceiling_area.get())

    def selected_item(self):
        room = self.room_plan()
        if self.selected is None:
            return None
        if self.selected[0] == "door":
            return room["doors"][self.selected[1]]
        return room["walls"][self.selected[1]]

    def on_location(self):
        item = self.selected_item()
        if item is not None and not self.area_var.get():
            self.area_var.set(suggested_area(self.location_var.get()))
        self.store_selection()

    def store_selection(self):
        item = self.selected_item()
        if item is not None:
            item.update(location=self.location_var.get(), area=self.area_var.get(), primary=self.primary_var.get())
        self.update_panel()

    def select(self, selection):
        self.selected = selection
        item = self.selected_item()
        self.location_var.set(item["location"] if item else "")
        self.area_var.set(item["area"] if item else "")
        self.primary_var.set(item.get("primary", False) if item else False)
        state = ["!disabled"] if item else ["disabled"]
        for widget in (self.location_box, self.area_box):
            widget.state(state + ["readonly"] if item else state)
        self.update_panel()
        self.redraw()

    # ----- suggestions -----
    def barrier_of(self, selection, create=False):
        """The barrier of the room tab of a wall (door) of the plan: the walls (doors) of the room, in order.
        None if the room has fewer; create: they are added."""
        return self.app.plan_barrier(self.t, selection[0], selection[1], create=create)

    def name_of(self, selection):
        """Name of the wall or door in the room tab ('Wall 5' if it is not there yet)."""
        e = self.barrier_of(selection)
        if e is not None:
            return self.app.barrier_name(e, self.app.d[f"nr {self.t}"])
        return f"{'Door' if selection[0] == 'door' else 'Wall'} {selection[1] + 1}"

    def segment_of(self, selection):
        room = self.room_plan()
        if selection[0] == "door":
            door = room["doors"][selection[1]]
            return door["a"], door["b"]
        return edges(room["outline"])[selection[1]]

    def distance_to(self, selection):
        room = self.room_plan()
        if room["source"] is None or not self.plan["scale"]:
            return None
        a, b = self.segment_of(selection)
        return self.metres(point_segment_distance(room["source"], a, b))

    def neighbour_of(self, selection):
        # Another traced room of this plan that shares the wall
        if selection[0] != "wall" or not self.plan["scale"]:
            return None
        a, b = self.segment_of(selection)
        tolerance = 0.4 / self.plan["scale"]
        for t, other in self.plan["rooms"].items():
            if t != self.t and other["closed"] and t in self.rooms and shared_wall(a, b, other["outline"], tolerance):
                return self.app.room_name(t)
        return None

    def update_panel(self):
        room = self.room_plan()
        if self.selected is None:
            self.sel_title.set("Nothing selected")
            lines = ["Draw the walls, place the source, then click a wall."]
            if room["closed"]:
                walls = len(room["walls"])
                lines = [f"{walls} walls traced: {self.name_of(('wall', 0))} … {self.name_of(('wall', walls - 1))}"
                         + (f"; {len(room['doors'])} door{'s' if len(room['doors']) > 1 else ''}: "
                            + ", ".join(self.name_of(('door', k)) for k in range(len(room["doors"])))
                            if room["doors"] else "") + ".",
                         "Click a wall or a door to choose what is beyond it."]
            self.suggestion.configure(text="\n".join(lines))
            return
        name = self.name_of(self.selected)
        a, b = self.segment_of(self.selected)
        length = self.metres(math.dist(a, b))
        self.sel_title.set(f"{name}" + (f"   ({length:.2f} m long)" if length else ""))
        ct = self.room_type() == "CT Room"
        lines = []
        d = self.distance_to(self.selected)
        if d is None:
            lines.append("Distance: place the source to compute it." if self.plan["scale"]
                         else "Distance: set the scale of the drawing first.")
        else:
            lines.append(f"Distance {'isocenter' if ct else 'source'} → {name}: {d:.2f} m, plus 0.3 m "
                         f"beyond it to the occupied point ({d + 0.3:.2f} m)")
        if self.barrier_of(self.selected) is None:
            lines.append(f"The room tab has no {name} yet: 'Apply' adds it.")
        neighbour = self.neighbour_of(self.selected)
        if neighbour and not self.location_var.get():
            lines.append(f"Shared with room '{neighbour}': suggested 'Adjacent x-ray rooms' (T = 1).")
        location = self.location_var.get()
        if location:
            lines.append(f"Beyond: {location} → T = {OCCUPANCY_T.get(location, '?'):g} (NCRP 147 Table 4.1)")
        area = self.area_var.get()
        if area:
            lines.append(f"{area} → P = {DESIGN_GOALS[area]} mGy/week")
        elif location:
            lines.append(f"Suggested area: {suggested_area(location)}")
        if self.room_type() in ("X-Ray room", "Fluoroscopy Room"):
            lines.append("Radiation: Primary" if self.primary_var.get()
                         else "Radiation: Secondary (tick 'Primary beam' for e.g. the chest bucky wall)")
        elif self.room_type() == "Mammography Room":
            lines.append("Radiation: Secondary (mammography, NCRP 147)")
        self.suggestion.configure(text="\n".join(lines))

    # ----- applying to the room -----
    def apply_selected(self):
        if self.selected is None:
            messagebox.showinfo("Floor plan", "Select a wall or a door first.", parent=self)
            return
        item = self.selected_item()
        location = item["location"] or (
            "Adjacent x-ray rooms" if self.neighbour_of(self.selected) else "")
        self.app.apply_barrier_inputs(self.t, self.barrier_of(self.selected, create=True),
                                      distance=self.distance_to(self.selected),
                                      location=location, area=item["area"] or (
                                          suggested_area(location) if location else ""),
                                      primary=item.get("primary", False))
        self.suggestion.configure(text=self.suggestion.cget("text") + "\n✓ Applied to the room.")

    def apply_all(self):
        room = self.room_plan()
        if not room["closed"]:
            messagebox.showinfo("Floor plan", "Draw the walls of the room first.", parent=self)
            return
        self.store_floor_ceiling()
        selections = [("wall", i) for i in range(len(room["walls"]))] + [("door", k) for k in range(len(room["doors"]))]
        for selection in selections:
            self.selected = selection
            item = self.selected_item()
            location = item["location"] or ("Adjacent x-ray rooms" if self.neighbour_of(selection) else "")
            self.app.apply_barrier_inputs(self.t, self.barrier_of(selection, create=True),
                                          distance=self.distance_to(selection),
                                          location=location,
                                          area=item["area"] or (suggested_area(location) if location else ""),
                                          primary=item.get("primary", False))
        # NCRP 147 4.1.2: the person below is 1.7 m above the lower floor, the person above 0.5 m above the floor
        # of the room above; the floor-to-floor height is taken the same for the storey below
        storey = room.get("floor_to_floor") or max(DEFAULT_FLOOR_TO_FLOOR, room["height"])
        for e, key, distance, beyond in ((1, "floor", room["source_height"], max(storey - 1.7, 0.0)),
                                         (2, "ceiling", room["height"] - room["source_height"],
                                          max(storey - room["height"], 0.0) + 0.5)):
            side = room[key]
            self.app.apply_barrier_inputs(self.t, e, distance=distance if distance > 0 else None, beyond=beyond,
                                          location=side["location"],
                                          area=side["area"] or (suggested_area(side["location"])
                                                                if side["location"] else ""),
                                          primary=side.get("primary", False) if key == "floor" else False)
        self.select(None)
        doors = len(room["doors"])
        self.suggestion.configure(text=f"✓ Applied {len(room['walls'])} walls, {doors} door{'' if doors == 1 else 's'}, "
                                       f"the floor and the ceiling to "
                                       f"'{self.app.room_name(self.t)}'.\nCheck the room tab, then press Calculate.")

    # ----- drawing -----
    def load_plan(self):
        path = filedialog.askopenfilename(parent=self, title="Load floor plan",
                                          filetypes=[("Drawings", "*.pdf *.png *.jpg *.jpeg"), ("All files", "*.*")])
        if not path:
            return
        if any(r["outline"] for r in self.plan["rooms"].values()) and not messagebox.askyesno(
                "Floor plan", "Walls are already traced on this plan.\nLoad the new drawing and clear them?",
                parent=self):
            return
        try:
            image = load_drawing(path, self)
        except Exception as error:
            messagebox.showerror("Floor plan", f"Cannot open the drawing:\n{error}", parent=self)
            return
        if image is None:
            return
        for room in self.plan["rooms"].values():
            room.update(outline=[], closed=False, walls=[], doors=[], source=None)
        self.plan.update(image=image, image_name=os.path.basename(path), scale=None)
        self.fit()
        self.mode.set("scale")

    def fit(self):
        width, height = max(self.canvas.winfo_width(), 100), max(self.canvas.winfo_height(), 100)
        if self.plan["image"] is not None:
            x0, y0, x1, y1 = 0, 0, self.plan["image"].width, self.plan["image"].height
        else:
            points = [p for r in self.plan["rooms"].values() for p in r["outline"]]
            if points:
                xs, ys = [p[0] for p in points], [p[1] for p in points]
                x0, y0, x1, y1 = min(xs) - 50, min(ys) - 50, max(xs) + 50, max(ys) + 50
            else:
                x0, y0, x1, y1 = 0, 0, 12 / DEFAULT_SCALE, 9 / DEFAULT_SCALE
        self.zoom = min(width / max(x1 - x0, 1), height / max(y1 - y0, 1))
        self.origin = [x0 - (width / self.zoom - (x1 - x0)) / 2, y0 - (height / self.zoom - (y1 - y0)) / 2]
        self.redraw()

    def to_screen(self, p):
        return ((p[0] - self.origin[0]) * self.zoom, (p[1] - self.origin[1]) * self.zoom)

    def to_world(self, x, y):
        return (x / self.zoom + self.origin[0], y / self.zoom + self.origin[1])

    def redraw(self, cursor=None):
        c = self.canvas
        c.delete("all")
        width, height = c.winfo_width(), c.winfo_height()
        image = self.plan["image"]
        if image is not None:
            (wx0, wy0), (wx1, wy1) = self.origin, self.to_world(width, height)
            x0, y0 = max(0, int(wx0)), max(0, int(wy0))
            x1, y1 = min(image.width, int(wx1) + 1), min(image.height, int(wy1) + 1)
            if x1 > x0 and y1 > y0:
                size = (max(1, round((x1 - x0) * self.zoom)), max(1, round((y1 - y0) * self.zoom)))
                self.photo = ImageTk.PhotoImage(image.crop((x0, y0, x1, y1)).resize(size, Image.Resampling.BILINEAR),
                                                master=c)
                c.create_image(*self.to_screen((x0, y0)), image=self.photo, anchor="nw")
        elif self.plan["scale"]:
            step = 1 / self.plan["scale"]  # 1 m grid
            (wx0, wy0), (wx1, wy1) = self.origin, self.to_world(width, height)
            for k in range(int(wx0 // step), int(wx1 // step) + 2):
                x = self.to_screen((k * step, 0))[0]
                c.create_line(x, 0, x, height, fill="#e6e6e6")
            for k in range(int(wy0 // step), int(wy1 // step) + 2):
                y = self.to_screen((0, k * step))[1]
                c.create_line(0, y, width, y, fill="#e6e6e6")
            c.create_text(8, height - 8, text="Grid: 1 m", anchor="sw", fill="#777777")

        # other rooms of this plan
        for t, room in self.plan["rooms"].items():
            if t != self.t and t in self.rooms and room["outline"]:
                pts = [coord for p in room["outline"] for coord in self.to_screen(p)]
                if room["closed"]:
                    c.create_polygon(*pts, outline=OTHER_COLOR, fill="", width=2, dash=(4, 3))
                    c.create_text(*self.to_screen(centroid(room["outline"])), text=self.app.room_name(t),
                                  fill=OTHER_COLOR, font=(theme.FAMILY, 10, "bold"))

        room = self.room_plan()
        outline = room["outline"]
        if room["closed"]:
            pts = [coord for p in outline for coord in self.to_screen(p)]
            c.create_polygon(*pts, fill="#dfe9f7", outline="", stipple="gray25")
            for i, (a, b) in enumerate(edges(outline)):
                chosen = self.selected == ("wall", i)
                c.create_line(*self.to_screen(a), *self.to_screen(b), width=7 if chosen else 4,
                              fill=SELECTED_COLOR if chosen else WALL_COLOR, capstyle="round")
                mx, my = self.to_screen(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
                c.create_text(mx, my, text=self.name_of(("wall", i)), fill="white", font=(theme.FAMILY, 9, "bold"),
                              tags="label")
                bbox = c.bbox(c.find_withtag("label")[-1])
                c.create_rectangle(bbox[0] - 3, bbox[1] - 1, bbox[2] + 3, bbox[3] + 1,
                                   fill=SELECTED_COLOR if chosen else WALL_COLOR, outline="")
                c.tag_raise("label")
            x, y = self.to_screen(centroid(outline))
            c.create_text(x, y + 22, text=self.app.room_name(self.t), fill=WALL_COLOR, font=(theme.FAMILY, 11, "bold"))
        elif outline:
            pts = [coord for p in outline for coord in self.to_screen(p)]
            if len(pts) >= 4:
                c.create_line(*pts, width=3, fill=WALL_COLOR)
            for p in outline:
                x, y = self.to_screen(p)
                c.create_oval(x - 4, y - 4, x + 4, y + 4, fill=WALL_COLOR, outline="")
            if cursor is not None and self.mode.get() == "outline":
                c.create_line(*self.to_screen(outline[-1]), *self.to_screen(cursor), width=2, fill=WALL_COLOR,
                              dash=(5, 3))
        for k, door in enumerate(room["doors"]):
            chosen = self.selected == ("door", k)
            a, b = self.to_screen(door["a"]), self.to_screen(door["b"])
            c.create_line(*a, *b, width=9 if chosen else 7, fill=SELECTED_COLOR if chosen else DOOR_COLOR)
            inside = self.to_screen(centroid(outline))
            c.create_text(*inward(a, b, inside, -14), text=self.name_of(("door", k)), fill=DOOR_COLOR,
                          font=(theme.FAMILY, 9, "bold"))
        if room["source"]:
            x, y = self.to_screen(room["source"])
            c.create_oval(x - 7, y - 7, x + 7, y + 7, fill="#d62728", outline="white", width=2)
            c.create_text(x + 10, y - 10, text="Isocenter" if self.room_type() == "CT Room" else "Source",
                          anchor="sw", fill="#d62728", font=(theme.FAMILY, 10, "bold"))
        for p in self.points:
            x, y = self.to_screen(p if self.mode.get() == "scale" else p[0])
            c.create_oval(x - 5, y - 5, x + 5, y + 5, outline=SELECTED_COLOR, width=2)
        if cursor is not None and len(self.points) == 1:
            start = self.points[0] if self.mode.get() == "scale" else self.points[0][0]
            c.create_line(*self.to_screen(start), *self.to_screen(cursor), fill=SELECTED_COLOR, dash=(4, 3), width=2)
        self.scale_text.set(f"Scale: {1 / self.plan['scale']:.1f} px/m" if self.plan["scale"]
                            else "Scale: not set")

    # ----- mouse -----
    def snap(self, p):
        outline = self.room_plan()["outline"]
        if not self.ortho.get() or not outline:
            return p
        last = outline[-1]
        if abs(p[0] - last[0]) > abs(p[1] - last[1]):
            return (p[0], last[1])
        return (last[0], p[1])

    def on_motion(self, event):
        mode = self.mode.get()
        if mode in ("outline", "scale", "door"):
            p = self.to_world(event.x, event.y)
            self.redraw(cursor=self.snap(p) if mode == "outline" else p)

    def on_click(self, event):
        p = self.to_world(event.x, event.y)
        room, mode = self.room_plan(), self.mode.get()
        if mode == "outline":
            if room["closed"]:
                if not messagebox.askyesno("Floor plan", "This room already has walls. Draw them again?", parent=self):
                    return
                room.update(outline=[], closed=False, walls=[], doors=[])
            outline = room["outline"]
            if len(outline) >= 3:
                fx, fy = self.to_screen(outline[0])
                if math.hypot(event.x - fx, event.y - fy) < 12:
                    self.close_outline()
                    return
            outline.append(self.snap(p))
            self.redraw()
        elif mode == "source":
            room["source"] = p
            self.redraw()
            self.update_panel()
        elif mode == "scale":
            self.points.append(p)
            if len(self.points) == 2:
                pixels = math.dist(*self.points)
                self.points = []
                length = simpledialog.askfloat("Scale", "Real distance between the two points (m):",
                                               minvalue=0.01, parent=self)
                if length and pixels > 0:
                    self.plan["scale"] = length / pixels
                    self.mode.set("outline" if not room["closed"] else "select")
            self.redraw()
            self.update_panel()
        elif mode == "door":
            if not room["closed"]:
                self.note.configure(text="Draw the walls of the room first, then add the door.")
                return
            walls = edges(room["outline"])
            i = min(range(len(walls)), key=lambda k: point_segment_distance(p, *walls[k]))
            self.points.append((project_on_segment(p, *walls[i]), i))
            if len(self.points) == 2:
                (a, wall_a), (b, wall_b) = self.points
                self.points = []
                if wall_a != wall_b:
                    self.note.configure(text="Both edges of the door must be on the same wall. Try again.")
                else:
                    room["doors"].append({"a": a, "b": b, "wall": wall_a, "location": "", "area": ""})
                    self.mode.set("select")
                    self.select(("door", len(room["doors"]) - 1))
            self.redraw()
        else:
            self.select(self.hit_test(event.x, event.y))

    def hit_test(self, x, y):
        room = self.room_plan()
        for k, door in enumerate(room["doors"]):
            a, b = self.to_screen(door["a"]), self.to_screen(door["b"])
            if point_segment_distance((x, y), a, b) < 9:
                return ("door", k)
        if room["closed"]:
            for i, (a, b) in enumerate(edges(room["outline"])):
                if point_segment_distance((x, y), self.to_screen(a), self.to_screen(b)) < 9:
                    return ("wall", i)
        return None

    def close_outline(self):
        room = self.room_plan()
        if self.mode.get() != "outline" or room["closed"] or len(room["outline"]) < 3:
            return
        if self.ortho.get():  # make the closing wall straight too
            first, last = room["outline"][0], room["outline"][-1]
            if abs(first[0] - last[0]) < abs(first[1] - last[1]):
                room["outline"][-1] = (first[0], last[1])
            else:
                room["outline"][-1] = (last[0], first[1])
        room["closed"] = True
        room["walls"] = [{"location": "", "area": "", "primary": False} for _ in room["outline"]]
        room["doors"] = []
        self.mode.set("source" if room["source"] is None else "select")
        self.select(None)

    def clear_outline(self):
        room = self.room_plan()
        if room["outline"] and messagebox.askyesno("Floor plan", "Clear the walls of this room?", parent=self):
            room.update(outline=[], closed=False, walls=[], doors=[])
            self.select(None)

    def remove_door(self):
        """The selected door leaves the plan (the door of the room tab stays)."""
        if self.selected is None or self.selected[0] != "door":
            self.note.configure(text="Select the door to remove first.")
            return
        del self.room_plan()["doors"][self.selected[1]]
        self.select(None)

    def undo_point(self):
        room = self.room_plan()
        if self.mode.get() == "outline" and not room["closed"] and room["outline"]:
            room["outline"].pop()
            self.redraw()

    def cancel(self):
        self.points = []
        room = self.room_plan()
        if self.mode.get() == "outline" and not room["closed"]:
            room["outline"] = []
        self.redraw()

    def on_mode_change(self):
        self.points = []
        self.note.configure(text=MODE_NOTES[self.mode.get()])
        self.redraw()

    def on_wheel(self, event):
        factor = 1.2 if event.delta > 0 else 1 / 1.2
        wx, wy = self.to_world(event.x, event.y)
        self.zoom *= factor
        self.origin = [wx - event.x / self.zoom, wy - event.y / self.zoom]
        self.redraw()
        return "break"  # do not let the window-wide scrolling handle it too

    def pan_begin(self, event):
        self.pan_start = (event.x, event.y, list(self.origin))

    def pan_move(self, event):
        x, y, origin = self.pan_start
        self.origin = [origin[0] - (event.x - x) / self.zoom, origin[1] - (event.y - y) / self.zoom]
        self.redraw()


# ===================== 2D / 3D viewer =====================
# Colour of each material: a categorical palette in a fixed order (no green: here it means "goal met")
MATERIAL_COLORS = {"Lead": "#2a78d6", "Concrete": "#eb6834", "Gypsum Wallboard": "#1baf7a", "Steel": "#eda100",
                   "Plate Glass": "#e87ba4", "Wood": "#6250d6"}
OUTLINE_COLOR = "#333333"
ROOM_FILL = "#e3e9ef"
WALL_WIDTH = 10    # drawn thickness of a wall in the 2D plan (points)
DASH = 6           # length of a stripe of a wall whose materials are alternatives, 2D plan (points)
SHARED = 0.3       # walls of two rooms closer than this (m) are one wall
LAYER_GAP = 0.06   # distance between the layers of a wall in the 3D view (m)
STRIPE = 0.4       # length of a stripe in the 3D view (m)
PICKED = theme.NAVY  # the barrier picked in the list (not a material colour)


def material_rows(info):
    """[(label, material, required mm, planned mm)] of a barrier, from the room side out. Required: None when it
    has no NCRP 147 data; planned: None when not given."""
    rows, count = [], len(info["rows"])
    for k, (material, required, planned) in enumerate(info["rows"]):
        if info["layered"] and count > 1:
            label = ("inside" if k == 0 else "outside" if k == count - 1 else "middle") + f" · {material}"
        else:
            label = material if k == 0 else f"or {material}"  # each one alone: alternatives
        rows.append((label, material, required, planned))
    return rows


def shown_layers(info):
    """The materials a wall is drawn with: what it is built of (planned, or else required), thicker than 0."""
    return [m for m, x in info["built"] if x and x > 0]


def short_materials(info):
    """'Concrete + Pb' for layers or a planned barrier, 'Pb or Concrete' for alternatives."""
    if info["state"] != "ok":
        return "missing data" if info["state"] == "missing" else "not calculated"
    names = [SHORT.get(m, m) for m in shown_layers(info)]
    if not names:
        return "no shielding needed"
    return (" + " if info["together"] else " or ").join(names)


def materials_text(info):
    """The materials of a barrier and their thicknesses on one line."""
    if info["state"] != "ok":
        return short_materials(info)
    if info["planned"]:
        return " + ".join(f"{m} {x:g}" for m, x in info["built"]) + " mm (planned)"
    known = [(m, x) for m, x in info["built"] if x is not None]
    if not known:
        return "no NCRP 147 data for its materials"
    if all(x == 0 for _, x in known):
        return "no shielding needed"
    return (" + " if info["together"] else " or ").join(f"{m} {x:.2f}" for m, x in known) + " mm"


def check_text(check):
    """Weekly dose beyond the barrier against the goal P."""
    if check["basis"] == "required thickness":
        return f"{check['dose']:.3g} mGy/week = P (required thickness)"
    return (f"{check['dose']:.3g} mGy/week {'≤' if check['ok'] else '>'} P {check['P']:g}  "
            + ("✓ met" if check["ok"] else "✗ exceeded"))


def barrier_lines(info, title):
    """The note shown while the pointer is on a barrier: its materials, their thicknesses and the dose beyond."""
    lines = [title]
    if info["state"] == "not calculated":
        return lines + ["Not calculated yet: press Calculate in the room tab."]
    if info["state"] == "missing":
        missing = info["missing"]
        return lines + ["Missing data: " + "; ".join(missing[:3]) + (" …" if len(missing) > 3 else "")]
    rows = material_rows(info)
    if info["layered"] and len(rows) > 1:
        lines.append("Required, layers from the room side out:")
    elif len(rows) > 1:
        lines.append("Required, each material alone:")
    else:
        lines.append("Required:")
    for label, _, required, _ in rows:
        value = "no NCRP 147 data" if required is None else "none needed" if required == 0 else f"{required:.2f} mm"
        lines.append(f"    {label}: {value}")
    if info["planned"]:
        lines.append(("Planned, all together: " if len(info["built"]) > 1 else "Planned: ")
                     + " + ".join(f"{m} {x:g} mm" for m, x in info["built"]))
    if info["check"]:
        lines.append("Beyond: " + check_text(info["check"]))
    return lines


def wall_normal(a, b, inside):
    """Unit normal of the wall a-b, pointing into the room."""
    nx, ny = -(b[1] - a[1]), b[0] - a[0]
    length = math.hypot(nx, ny) or 1
    nx, ny = nx / length, ny / length
    if (inside[0] - (a[0] + b[0]) / 2) * nx + (inside[1] - (a[1] + b[1]) / 2) * ny < 0:
        nx, ny = -nx, -ny
    return nx, ny


def draw_wall_2d(ax, figure, a, b, inside, colors, together, zorder=2.0):
    """A wall as a thick line with a dark edge: one band per material across it (layers, the inside one on the
    room side) or stripes along it (materials that are alternatives)."""
    xs, ys = [a[0], b[0]], [a[1], b[1]]
    ax.plot(xs, ys, color=OUTLINE_COLOR, linewidth=WALL_WIDTH + 1.6, solid_capstyle="butt", zorder=zorder)
    n = len(colors)
    if n == 1:
        ax.plot(xs, ys, color=colors[0], linewidth=WALL_WIDTH, solid_capstyle="butt", zorder=zorder + 0.1)
    elif together:
        nx, ny = wall_normal(a, b, inside)
        for k, color in enumerate(colors):
            offset = WALL_WIDTH / 2 - (k + 0.5) * WALL_WIDTH / n  # points towards the room
            ax.plot(xs, ys, color=color, linewidth=WALL_WIDTH / n, solid_capstyle="butt", zorder=zorder + 0.1,
                    transform=offset_copy(ax.transData, fig=figure, x=nx * offset, y=ny * offset, units="points"))
    else:
        dash = DASH / WALL_WIDTH  # matplotlib scales dashes by the line width
        for k, color in enumerate(colors):
            ax.plot(xs, ys, color=color, linewidth=WALL_WIDTH, dash_capstyle="butt", zorder=zorder + 0.1,
                    linestyle=(k * dash, (dash, (n - 1) * dash)))


def wall_quads_3d(a, b, inside, bottom, top, colors, together):
    """[(corners, colour)] of a wall in 3D: parallel sheets for layers (the inside one on the room side),
    stripes for materials that are alternatives."""
    sheet = lambda p, q: [(*p, bottom), (*q, bottom), (*q, top), (*p, top)]
    n = len(colors)
    if n == 1:
        return [(sheet(a, b), colors[0])]
    if together:
        nx, ny = wall_normal(a, b, inside)
        quads = []
        for k, color in enumerate(colors):
            offset = LAYER_GAP * ((n - 1) / 2 - k)
            quads.append((sheet((a[0] + nx * offset, a[1] + ny * offset), (b[0] + nx * offset, b[1] + ny * offset)),
                          color))
        return quads
    pieces = max(n, int(round(math.dist(a, b) / STRIPE)))
    point = lambda u: (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
    return [(sheet(point(k / pieces), point((k + 1) / pieces)), colors[k % n]) for k in range(pieces)]


def swatch(master, color, size):
    """Small square of a colour, for the list of materials."""
    image = PhotoImage(master=master, width=size, height=size)
    image.put(OUTLINE_COLOR, to=(0, 0, size, size))
    image.put(color, to=(1, 1, size - 1, size - 1))
    return image


class RoomViewer(Toplevel):
    MODES = {"Materials": "materials", "Dose beyond vs goal P": "goal"}

    def __init__(self, app, key, title):
        super().__init__(app.master)
        self.app, self.key = app, key
        self.title(f"2D / 3D view: {title}")
        maximize(self)
        bar = ttk.Frame(self)
        bar.pack(side=TOP, fill=X)
        label = ttk.Label(bar, text="Walls show:")
        label.pack(side=LEFT, padx=(8, 4))
        tip(label, "view_walls")
        self.mode = StringVar(value="Materials")
        box = ttk.Combobox(bar, textvariable=self.mode, values=list(self.MODES), state="readonly", width=22)
        box.pack(side=LEFT, padx=4, pady=6)
        box.bind("<<ComboboxSelected>>", lambda e: self.draw())
        tip(box, "view_walls")
        self.show_radiation = BooleanVar(value=False)
        tip(ttk.Checkbutton(bar, text="Radiation map", variable=self.show_radiation, command=self.draw),
            "view_radiation").pack(side=LEFT, padx=10)
        self.show_ceiling, self.show_plan = BooleanVar(value=False), BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Ceiling (3D)", variable=self.show_ceiling, command=self.draw).pack(
            side=LEFT, padx=6)
        ttk.Checkbutton(bar, text="Drawing (2D)", variable=self.show_plan, command=self.draw).pack(
            side=LEFT, padx=6)
        tip(ttk.Button(bar, text="Refresh", command=self.draw), "view_refresh").pack(side=LEFT, padx=8)
        self.info = Label(self, justify=LEFT, background="#fff8d6", relief=SOLID, borderwidth=1, padx=8, pady=3,
                          font=theme.SMALL, anchor="w")
        self.info.pack(side=TOP, fill=X, padx=8, pady=(0, 6))

        body = ttk.PanedWindow(self, orient=HORIZONTAL)
        body.pack(fill=BOTH, expand=1)
        tabs = ttk.Notebook(body)
        side = ttk.Frame(body, padding=(theme.px(8), theme.px(2), theme.px(4), theme.px(4)))
        body.add(tabs, weight=1)
        body.add(side, weight=0)
        # the list keeps its width and the drawing takes the rest, until the divider is moved by hand
        self.sash_moved = False
        body.bind("<Configure>", lambda event: body.after_idle(self.place_sash, body), add="+")
        body.bind("<ButtonRelease-1>", lambda event: setattr(self, "sash_moved", True), add="+")
        self.build_list(side)
        self.figures, self.toolbars = {}, {}
        for name in ("2D plan", "3D view"):
            frame = ttk.Frame(tabs)
            tabs.add(frame, text=name)
            figure = Figure(figsize=(12, 7), dpi=100, layout="constrained")  # room for the legend beside
            canvas = FigureCanvasTkAgg(figure, master=frame)
            toolbar = NavigationToolbar2Tk(canvas, frame)
            toolbar.update()
            canvas.get_tk_widget().pack(fill=BOTH, expand=1)
            self.figures[name], self.toolbars[name] = (figure, canvas), toolbar
            # the note with the materials follows the pointer over the walls
            canvas.mpl_connect("motion_notify_event", lambda event, view=name: self.on_hover(event, view))
            canvas.mpl_connect("figure_leave_event", lambda event: self.hide_note())
            canvas.mpl_connect("button_press_event", lambda event, view=name: self.on_press(event, view))
        self.note = self.note_label = None
        self.ax2d = self.ax3d = self.field = None
        self.geometries, self.segments, self.quads, self.highlight = [], [], [], []
        self.selected = None
        self.draw()

    def place_sash(self, body):
        width = body.winfo_width()
        if not self.sash_moved and width > 1 and body.winfo_exists():
            body.sashpos(0, max(width - theme.px(640), int(width * 0.55)))

    # ----- the list of barriers and their materials -----
    def build_list(self, side):
        heading = ttk.Label(side, text="Barriers and their materials", style="BL2.TLabel")
        heading.pack(anchor="w")
        tip(heading, "view_list")
        ttk.Label(side, text="Thickness in mm. Point at a wall on the drawing to see its materials, or pick a "
                             "barrier here to find it on the 2D plan.", style="Muted.TLabel",
                  wraplength=theme.px(520), justify=LEFT).pack(anchor="w", pady=(2, 6))
        frame = ttk.Frame(side)
        frame.pack(fill=BOTH, expand=1)
        self.tree = ttk.Treeview(frame, columns=("required", "planned", "beyond"), selectmode="browse")
        for column, text, width, anchor in (("#0", "Barrier / material", 220, "w"), ("required", "Required", 80, "e"),
                                            ("planned", "Planned", 72, "e"),
                                            ("beyond", "Dose beyond (mGy/wk)", 180, "w")):
            self.tree.heading(column, text=text, anchor=anchor)
            self.tree.column(column, width=theme.px(width), minwidth=theme.px(50), anchor=anchor,
                             stretch=column == "#0")
        scroll = ttk.Scrollbar(frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=RIGHT, fill=Y)
        self.tree.pack(side=LEFT, fill=BOTH, expand=1)
        self.tree.tag_configure("room", font=theme.BOLD, background=theme.BG)
        self.tree.tag_configure("barrier", font=theme.BOLD)
        self.tree.tag_configure("met", foreground="#2e7d32")
        self.tree.tag_configure("exceeded", foreground=theme.DANGER)
        self.tree.tag_configure("muted", foreground=theme.MUTED)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_selected())
        size = theme.px(13)
        self.swatches = {m: swatch(self, color, size) for m, color in MATERIAL_COLORS.items()}
        self.items = {}

    def fill_list(self, geometries):
        selection = self.tree.selection()
        selected = selection[0] if selection else None
        closed = {iid for iid in self.items if self.tree.exists(iid) and not self.tree.item(iid, "open")}
        self.tree.delete(*self.tree.get_children())
        self.items = {}
        for g in geometries:
            room = f"room|{g['t']}"
            self.tree.insert("", END, iid=room, text=f"{g['name']}  ({g['type']})", open=room not in closed,
                             tags=("room",))
            self.items[room] = (g, None)
            for e, name in g["barriers"].items():
                info, iid = g["info"][e], f"{g['t']}|{e}"
                check = info["check"]
                if info["state"] == "missing":
                    beyond, tags = "missing data", ("barrier", "exceeded")
                elif check is None:
                    beyond, tags = "not calculated", ("barrier", "muted")
                elif check["basis"] == "required thickness":
                    beyond, tags = f"{check['dose']:.3g} = P (required)", ("barrier", "met")
                else:
                    beyond = (f"{check['dose']:.3g} {'≤' if check['ok'] else '>'} P {check['P']:g}  "
                              + ("✓" if check["ok"] else "✗"))
                    tags = ("barrier", "met" if check["ok"] else "exceeded")
                self.tree.insert(room, END, iid=iid, text=name, values=("", "", beyond), tags=tags,
                                 open=iid not in closed)
                self.items[iid] = (g, e)
                for k, (label, material, required, planned) in enumerate(material_rows(info)):
                    value = "–" if required is None else "none" if required == 0 else f"{required:.2f}"
                    self.tree.insert(iid, END, iid=f"{iid}|{k}", text=label, image=self.swatches.get(material, ""),
                                     values=(value, "" if planned is None else f"{planned:g}", ""))
                    self.items[f"{iid}|{k}"] = (g, e)
        if selected in self.items:
            self.tree.selection_set(selected)
            self.tree.see(selected)
        self.selected = self.items.get(selected)

    def show_selected(self):
        selection = self.tree.selection()
        self.selected = self.items.get(selection[0]) if selection else None
        self.draw_highlight()
        self.figures["2D plan"][1].draw_idle()

    def draw_highlight(self):
        """Marks the barrier picked in the list on the 2D plan (floor and ceiling: the room)."""
        for artist in self.highlight:
            artist.remove()
        self.highlight = []
        if self.selected is None or self.ax2d is None:
            return
        g, e = self.selected
        walls = [(a, b) for h, k, a, b in self.segments if h is g and k == e]
        for a, b in walls:
            self.highlight += self.ax2d.plot([a[0], b[0]], [a[1], b[1]], color=PICKED, alpha=0.35,
                                             linewidth=WALL_WIDTH + 14, solid_capstyle="round", zorder=1.8)
        if not walls:
            self.highlight.append(self.ax2d.add_patch(PolygonPatch(g["outline"], closed=True, fill=False,
                                                                   edgecolor=PICKED, linewidth=3,
                                                                   linestyle="--", zorder=4.5)))

    # ----- the note that follows the pointer -----
    def on_hover(self, event, view):
        if event.inaxes is None or event.button is not None:  # outside the drawing, or rotating / moving it
            self.hide_note()
            return
        lines = self.hover_2d(event) if view == "2D plan" else self.hover_3d(event)
        if lines:
            self.show_note("\n".join(lines))
        else:
            self.hide_note()

    def on_press(self, event, view):
        self.hide_note()
        toolbar = self.toolbars[view]
        if view != "2D plan" or event.button != 1 or toolbar.mode != "":
            return
        hit = self.hit_2d(event)
        if hit:  # click on a wall: show it in the list
            g, e = hit
            iid = f"{g['t']}|{e}" if e is not None else f"room|{g['t']}"
            if self.tree.exists(iid):
                self.tree.selection_set(iid)
                self.tree.see(iid)

    def hit_2d(self, event):
        """(room, barrier) under the pointer on the 2D plan: a wall or a door, else (room, None) inside a room."""
        ax = self.ax2d
        if ax is None or event.inaxes is not ax:
            return None
        point, best = (event.x, event.y), None
        tolerance = (WALL_WIDTH / 2 + 3) * self.figures["2D plan"][0].dpi / 72
        doors = {(tuple(a), tuple(b)) for g in self.geometries for _, a, b in g["doors"]}
        for g, e, a, b in self.segments:
            start, end = ax.transData.transform([a, b])
            # a door is on a wall: it wins when both are under the pointer
            distance = point_segment_distance(point, start, end) - (2 if (tuple(a), tuple(b)) in doors else 0)
            if distance <= tolerance and (best is None or distance < best[0]):
                best = (distance, g, e)
        if best:
            return best[1], best[2]
        for g in self.geometries:
            if MplPath(ax.transData.transform(g["outline"])).contains_point(point):
                return g, None
        return None

    def hover_2d(self, event):
        hit = self.hit_2d(event)
        lines = []
        if hit and hit[1] is not None:
            g, e = hit
            lines = barrier_lines(g["info"][e], f"{g['name']} · {g['barriers'][e]}") if e in g["info"] else []
        elif hit:  # inside a room: its floor and ceiling
            g = hit[0]
            lines = [g["name"]]
            for e in (1, 2):
                if e in g["info"]:
                    info = g["info"][e]
                    lines.append(f"{g['barriers'][e]}: {materials_text(info)}")
                    if info["check"]:
                        lines.append("    beyond: " + check_text(info["check"]))
        kerma = self.kerma_at(event.xdata, event.ydata)
        if kerma is not None:
            lines.append(f"Air kerma here: {kerma:.3g} mGy/week (T = 1)")
        return lines

    def hover_3d(self, event):
        ax = self.ax3d
        if ax is None or event.inaxes is not ax or getattr(ax, "M", None) is None:
            return None
        point, best = (event.x, event.y), None
        for g, e, corners in self.quads:
            xs, ys, zs = (np.array(c, dtype=float) for c in zip(*corners))
            qx, qy, qz = proj3d.proj_transform(xs, ys, zs, ax.M)
            if MplPath(ax.transData.transform(np.column_stack([qx, qy]))).contains_point(point):
                depth = float(np.mean(qz))  # the smaller, the nearer
                if best is None or depth < best[0]:
                    best = (depth, g, e)
        if best is None:
            return None
        g, e = best[1], best[2]
        if e not in g["info"]:  # a wall of the plan that the room tab does not have
            return None
        return barrier_lines(g["info"][e], f"{g['name']} · {g['barriers'][e]}")

    def kerma_at(self, x, y):
        if self.field is None or x is None or y is None:
            return None
        X, Y, K = self.field
        step = X[0, 1] - X[0, 0]
        i, j = int(round((y - Y[0, 0]) / step)), int(round((x - X[0, 0]) / step))
        if 0 <= i < K.shape[0] and 0 <= j < K.shape[1] and np.isfinite(K[i, j]):
            return float(K[i, j])
        return None

    def show_note(self, text):
        if self.note is None:
            self.note = Toplevel(self)
            self.note.wm_overrideredirect(True)
            self.note_label = Label(self.note, justify=LEFT, background="#fff8d6", foreground=theme.TEXT,
                                    relief=SOLID, borderwidth=1, font=theme.BASE, padx=8, pady=6)
            self.note_label.pack()
        if self.note_label.cget("text") != text:
            self.note_label.configure(text=text)
        self.note.update_idletasks()
        width, height = self.note.winfo_reqwidth(), self.note.winfo_reqheight()
        x, y = self.winfo_pointerxy()
        x = min(x + 18, self.winfo_screenwidth() - width - 4)
        y = y + 18 if y + 18 + height < self.winfo_screenheight() else y - height - 12
        self.note.wm_geometry(f"+{x}+{y}")
        self.note.deiconify()
        self.note.lift()

    def hide_note(self):
        if self.note is not None:
            self.note.withdraw()

    # ----- drawing -----
    def draw(self):
        self.hide_note()
        rooms = self.app.workspace_rooms(self.key)
        geometries = layout_rooms([self.app.room_geometry(t) for t in rooms])
        for g in geometries:  # materials, thicknesses and dose beyond every barrier
            g["info"] = {e: self.app.barrier_info(g["nr"], e) for e in g["barriers"]}
            g["checks"] = {e: info["check"] for e, info in g["info"].items()}
            g["wall_T"] = {e: info["transmission"] for e, info in g["info"].items()}
        self.geometries = geometries
        mode = self.MODES[self.mode.get()]
        self.fill_list(geometries)

        def style(e, g):
            """Colours of barrier e of room g (one per material in the materials view), its label text and
            whether its materials are together (layers) or alternatives."""
            info = g["info"].get(e)
            if info is None or info["state"] != "ok":
                return [NOT_CALCULATED], short_materials(info) if info else "not calculated", False
            if mode == "goal":
                check = info["check"]
                if check is None:
                    return [NOT_CALCULATED], "not calculated", False
                text = f"{check['dose']:.3g} mGy/wk {'✓' if check['ok'] else '✗'}\nP {check['P']:g}"
                if check["basis"] == "required thickness":
                    text += " (required)"
                return [GOAL_MET if check["ok"] else GOAL_EXCEEDED], text, False
            materials = shown_layers(info)
            if not materials:
                return [NO_SHIELDING], short_materials(info), False
            return [MATERIAL_COLORS.get(m, OTHER_COLOR) for m in materials], short_materials(info), info["together"]

        # ----- summary of the goal check -----
        checks = [(g["name"], g["barriers"][e], c) for g in geometries for e, c in g["checks"].items() if c]
        exceeded = [f"{room} – {barrier}: {c['dose']:.3g} > {c['P']:g} mGy/week" for room, barrier, c in checks
                    if not c["ok"]]
        planned = sum(1 for _, _, c in checks if c["basis"] != "required thickness")
        lines = [f"Goal P met for {len(checks) - len(exceeded)} of {len(checks)} calculated barriers"
                 + (f" ({planned} with a planned thickness, the others with the required one)." if planned else
                    " (with the required thicknesses; to check the ones you plan, tick 'Check the dose beyond the "
                    "barrier with a planned thickness' under the materials).")]
        if exceeded:
            lines.append("Exceeded: " + ";  ".join(exceeded[:4]) + ("  …" if len(exceeded) > 4 else ""))
        schematic = [g["name"] for g in geometries if g["schematic"]]
        if schematic:
            lines.append("Schematic (no floor plan): walls at their entered distances from the source: "
                         + ", ".join(schematic) + ".")
        self.info.configure(text="\n".join(lines), foreground=theme.DANGER if exceeded else theme.TEXT)

        if mode == "goal":
            legend = [Patch(color=GOAL_MET, label="Goal P met"), Patch(color=GOAL_EXCEEDED, label="Goal P exceeded"),
                      Patch(color=NOT_CALCULATED, label="Not calculated")]
        else:
            used = {m for g in geometries for info in g["info"].values() if info["state"] == "ok"
                    for m in shown_layers(info)}
            legend = [Patch(color=MATERIAL_COLORS[m], label=m) for m in MATERIALS if m in used]
            legend += [Patch(color=NO_SHIELDING, label="No shielding needed"),
                       Patch(color=NOT_CALCULATED, label="Not calculated / missing data")]
            kinds = {info["together"] for g in geometries for info in g["info"].values()
                     if info["state"] == "ok" and len(shown_layers(info)) > 1}
            blank = dict(facecolor="none", edgecolor="none")
            if True in kinds:
                legend.append(Patch(**blank, label="Bands across a wall: layers, the inside one on the room side"))
            if False in kinds:
                legend.append(Patch(**blank, label="Stripes along a wall: each material alone (alternatives)"))
        legend += [Patch(color=DOOR_COLOR, label="Door (edge)"), Patch(color="#d62728", label="Source / isocenter")]
        title = "materials of the barriers" if mode == "materials" else "weekly dose beyond each barrier"
        radiation = self.show_radiation.get()
        all_x = [p[0] for g in geometries for p in g["outline"]]
        all_y = [p[1] for g in geometries for p in g["outline"]]
        bounds = (min(all_x) - 2.5, max(all_x) + 2.5, min(all_y) - 2.5, max(all_y) + 2.5)
        kerma_norm = None

        # ----- 2D -----
        figure, canvas = self.figures["2D plan"]
        figure.clear()
        ax = self.ax2d = figure.add_subplot()
        self.segments, self.highlight, self.field = [], [], None
        drawing = self.app.plans.get(self.key, {})
        if self.show_plan.get() and drawing.get("image") is not None and drawing.get("scale") and \
                any(not g["schematic"] for g in geometries):
            image, s = drawing["image"], drawing["scale"]
            ax.imshow(image, extent=(0, image.width * s, -image.height * s, 0), alpha=0.35, zorder=0)
        if radiation:
            X, Y, K = self.field = radiation_field(geometries, bounds, step=0.06)
            kerma_norm = kerma_scale(K)
            ax.imshow(np.ma.masked_invalid(K), extent=bounds, origin="lower", norm=kerma_norm, cmap=KERMA_CMAP,
                      alpha=0.75, zorder=0.5, interpolation="bilinear")
            contours = ax.contour(X, Y, np.ma.masked_invalid(K), levels=[0.02, 0.1], colors=["#1d3f8f", "#1b5e20"],
                                  linestyles="--", linewidths=1.3, zorder=1.5)
            ax.clabel(contours, fmt={0.02: "0.02", 0.1: "0.1"}, fontsize=8)
        label_box = dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.85, linewidth=0)
        for g in geometries:
            if not radiation:
                fill = ROOM_FILL if mode == "materials" else style(1, g)[0][0]
                ax.add_patch(PolygonPatch(g["outline"], closed=True, facecolor=fill, alpha=0.4 if mode == "materials"
                                          else 0.25, edgecolor="none", zorder=1))
            cx, cy = centroid(g["outline"])
            for e, a, b in g["walls"]:
                colors, text, together = style(e, g)
                draw_wall_2d(ax, figure, a, b, (cx, cy), colors, together)
                self.segments.append((g, e, a, b))
                lx, ly = inward(a, b, (cx, cy), 0.6)
                ax.text(lx, ly, f"{g['barriers'].get(e, '')}\n{text}", ha="center", va="center", fontsize=7,
                        zorder=5, bbox=label_box)
            for e, a, b in g["doors"]:
                colors, text, together = style(e, g)
                draw_wall_2d(ax, figure, a, b, (cx, cy), colors, together, zorder=4)
                ax.plot([a[0], b[0]], [a[1], b[1]], color=DOOR_COLOR, linewidth=2.5, zorder=4.3)
                self.segments.append((g, e, a, b))
                mx, my = inward(a, b, (cx, cy), -0.6)
                ax.text(mx, my, f"{g['barriers'].get(e, 'Door')}\n{text}", ha="center", va="center", fontsize=7,
                        zorder=5, bbox=label_box)
            sx, sy = g["source"]
            ax.plot(sx, sy, marker="*", markersize=16, color="#d62728", markeredgecolor="white", zorder=6)
            floor_text, ceiling_text = style(1, g)[1].replace("\n", " "), style(2, g)[1].replace("\n", " ")
            ax.text(cx, cy - 0.3, f"{g['name']}  ({g['type']})\nFloor: {floor_text}\nCeiling: {ceiling_text}",
                    ha="center", va="top", fontsize=7.5, zorder=5,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85, linewidth=0))
        ax.set_xlim(bounds[0] + 1, bounds[1] - 1)
        ax.set_ylim(bounds[2] + 1, bounds[3] - 1)
        ax.set_aspect("equal")
        ax.set_xlabel("m")
        ax.set_ylabel("m")
        ax.set_title(f"2D plan: {title}" + ("  ·  radiation map" if radiation else ""), fontsize=11)
        legend_2d = list(legend)
        if radiation:
            legend_2d.append(matplotlib.lines.Line2D([], [], color="#1d3f8f", linestyle="--",
                                                     label="0.02 mGy/week (uncontrolled P, T = 1)"))
            legend_2d.append(matplotlib.lines.Line2D([], [], color="#1b5e20", linestyle="--",
                                                     label="0.1 mGy/week (controlled P, T = 1)"))
        if bounds[1] - bounds[0] > 1.8 * (bounds[3] - bounds[2]):  # a wide department: under the plan
            figure.legend(handles=legend_2d, loc="outside lower center", ncol=3, fontsize=8)
        else:
            figure.legend(handles=legend_2d, loc="outside left upper", fontsize=8)
        if radiation:
            figure.colorbar(ScalarMappable(norm=kerma_norm, cmap=KERMA_CMAP), ax=ax, shrink=0.7,
                            label="Weekly air kerma (mGy/week)")
        self.draw_highlight()
        canvas.draw()

        # ----- 3D -----
        figure, canvas = self.figures["3D view"]
        figure.clear()
        ax = self.ax3d = figure.add_subplot(projection="3d")
        self.quads = []
        xs, ys, zs = [], [], [0]
        if radiation:  # the radiation map on the floor
            X, Y, K = radiation_field(geometries, bounds, step=0.15)
            colors = KERMA_CMAP(kerma_norm(np.nan_to_num(K, nan=kerma_norm.vmin)))
            colors[..., 3] = np.where(np.isnan(K), 0.0, 0.85)
            ax.plot_surface(X, Y, np.zeros_like(X), facecolors=colors, shade=False, linewidth=0,
                            rstride=1, cstride=1, antialiased=False)
            xs += [bounds[0] + 1.5, bounds[1] - 1.5]
            ys += [bounds[2] + 1.5, bounds[3] - 1.5]

        def add_wall(g, e, a, b, inside, bottom, top, colors, together, alpha, edge=OUTLINE_COLOR, width=1.0):
            for corners, color in wall_quads_3d(a, b, inside, bottom, top, colors, together):
                ax.add_collection3d(Poly3DCollection([corners], facecolor=to_rgba(color, alpha), edgecolor="none"))
            corners = [(*a, bottom), (*b, bottom), (*b, top), (*a, top)]
            ax.add_collection3d(Poly3DCollection([corners], facecolor=(0, 0, 0, 0), edgecolor=edge, linewidths=width))
            self.quads.append((g, e, corners))

        for g in geometries:
            h = g["height"]
            zs.append(h)
            cx, cy = centroid(g["outline"])
            floor = [(x, y, 0.01) for x, y in g["outline"]]
            floor_color = ROOM_FILL if mode == "materials" else style(1, g)[0][0]
            ax.add_collection3d(Poly3DCollection([floor], facecolor="none" if radiation else floor_color,
                                                 edgecolor="#555555", alpha=0.55))
            self.quads.append((g, 1, floor))
            for e, a, b in g["walls"]:
                colors, text, together = style(e, g)
                alpha = 0.3 if colors == [NOT_CALCULATED] else (0.45 if radiation else 0.8)
                add_wall(g, e, a, b, (cx, cy), 0, h, colors, together, alpha)
                ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, h + 0.15, f"{g['barriers'].get(e, '')}\n{text}",
                        fontsize=7, ha="center")
            for e, a, b in g["doors"]:
                colors, text, together = style(e, g)
                nx, ny = wall_normal(a, b, (cx, cy))
                a2, b2 = (a[0] + nx * 0.03, a[1] + ny * 0.03), (b[0] + nx * 0.03, b[1] + ny * 0.03)
                add_wall(g, e, a2, b2, (cx, cy), 0, min(DOOR_HEIGHT, h), colors, together, 1.0, DOOR_COLOR, 2)
            if self.show_ceiling.get():
                ceiling = [(x, y, h) for x, y in g["outline"]]
                ceiling_color = ROOM_FILL if mode == "materials" else style(2, g)[0][0]
                ax.add_collection3d(Poly3DCollection([ceiling], facecolor=ceiling_color, edgecolor="#555555",
                                                     alpha=0.3))
                self.quads.append((g, 2, ceiling))
            sx, sy = g["source"]
            ax.scatter([sx], [sy], [g["source_height"]], marker="*", s=180, color="#d62728", depthshade=False)
            ax.text(cx, cy, h + 0.8, g["name"], fontsize=9, weight="bold", ha="center")
            xs += [p[0] for p in g["outline"]]
            ys += [p[1] for p in g["outline"]]
        if xs:
            dx, dy, dz = max(xs) - min(xs), max(ys) - min(ys), max(zs) + 1
            ax.set_xlim(min(xs), max(xs))
            ax.set_ylim(min(ys), max(ys))
            ax.set_zlim(0, dz)
            ax.set_box_aspect((max(dx, 0.1), max(dy, 0.1), dz))
        ax.set_xlabel("m")
        ax.set_ylabel("m")
        ax.set_zlabel("m")
        ax.set_title(f"3D view: {title}" + ("  ·  radiation map on the floor" if radiation else "")
                     + " (drag to rotate)", fontsize=11)
        figure.legend(handles=legend, loc="outside left lower", fontsize=8)
        if radiation:
            figure.colorbar(ScalarMappable(norm=kerma_norm, cmap=KERMA_CMAP), ax=ax, shrink=0.55,
                            label="Weekly air kerma (mGy/week)")
        canvas.draw()


# ===================== the radiation field =====================
KERMA_CMAP = matplotlib.colormaps["Spectral_r"].copy()
KERMA_CMAP.set_bad(alpha=0)


def source_terms(record):
    """(primary, secondary) weekly unshielded air kerma times distance² toward a barrier (mGy·m²/week), without
    occupancy: N · U · K1 of its radiation types (CT: K/T · d², all secondary). None if not calculated."""
    if not record or record.get("missing") or not record.get("T"):
        return None
    if record["kind"] == "ct":
        if record.get("K_total") is None or not record.get("d"):
            return None
        return 0.0, record["K_total"] / record["T"] * record["d"] ** 2
    primary = secondary = 0.0
    for dist in record.get("distributions") or []:
        if dist.get("K") is None or not dist.get("d") or not dist.get("T"):
            return None
        term = dist["K"] / dist["T"] * dist["d"] ** 2
        if dist["radiation"] == "Primary":
            primary += term
        else:
            secondary += term
    return (primary, secondary) if primary + secondary > 0 else None


def source_term(record):
    """Primary plus secondary source term toward a barrier (mGy·m²/week), or None."""
    terms = source_terms(record)
    return sum(terms) if terms else None


def ray_crossings(sx, sy, dx, dy, a, b):
    """Where the rays from the source (sx, sy) towards the grid points (offsets dx, dy) cross the segment a-b:
    (mask, t), t being the fraction of the way to the point (beyond the point when t > 1)."""
    ex, ey = b[0] - a[0], b[1] - a[1]
    den = dx * ey - dy * ex
    with np.errstate(divide="ignore", invalid="ignore"):
        t = ((a[0] - sx) * ey - (a[1] - sy) * ex) / den
        u = ((a[0] - sx) * dy - (a[1] - sy) * dx) / den
        return (den != 0) & (t > 0) & (u >= 0) & (u <= 1), t


def radiation_field(geometries, bounds, step):
    """Weekly air kerma (mGy/week) on a grid, falling as 1/r² from the source. Inside the room: scatter and
    leakage in every direction, plus the primary beam toward the barriers it is aimed at. Beyond the first wall a
    ray crosses: that barrier's whole source term times its transmission through all its materials (planned, or
    the required thickness), as in the dose check. Every wall of another room on the way cuts it again, by the
    transmission of all its materials. NaN where a barrier is not calculated."""
    x0, x1, y0, y1 = bounds
    X, Y = np.meshgrid(np.arange(x0, x1 + step, step), np.arange(y0, y1 + step, step))
    total = np.full(X.shape, np.nan)
    for g in geometries:
        segments = list(g["walls"]) + list(g["doors"])  # the doors last: they lie on a wall
        sx, sy = g["source"]
        dx, dy = X - sx, Y - sy
        best_t = np.full(X.shape, np.inf)
        best = np.full(X.shape, -1)
        for k, (e, a, b) in enumerate(segments):
            hit, t = ray_crossings(sx, sy, dx, dy, a, b)
            closer = hit & ((t <= best_t + 1e-9) if k >= len(g["walls"]) else (t < best_t))
            best_t = np.where(closer, t, best_t)
            best = np.where(closer, k, best)
        terms = [source_terms(g["results"].get(e)) for e, _, _ in segments]
        known = [s for s in terms if s]
        scatter = max((s[1] for s in known), default=np.nan)  # the same in every direction inside the room
        beam = np.array([s[0] if s else np.nan for s in terms] + [np.nan])
        strength = np.array([sum(s) if s else np.nan for s in terms] + [np.nan])
        transmission = np.array([(g["checks"].get(e) or {}).get("transmission", np.nan) for e, _, _ in segments]
                                + [np.nan])
        r2 = np.maximum(dx ** 2 + dy ** 2, 0.3 ** 2)
        inside = (scatter + beam[best]) / r2
        outside = strength[best] / r2 * transmission[best]  # beyond the first wall: shielded
        kerma = np.where(best_t <= 1, outside, inside)
        # the walls of the other rooms on the way (a wall shared with this room is the same wall: counted once)
        reach = np.hypot(dx, dy)
        for h in geometries:
            if h is g:
                continue
            factor = lambda e: h.get("wall_T", {}).get(e) or 1.0  # not calculated: no attenuation known
            doors = []
            for door in h["doors"]:
                if not shared_wall(door[1], door[2], g["outline"], SHARED):
                    door_hit, door_t = ray_crossings(sx, sy, dx, dy, door[1], door[2])
                    doors.append((door[0], door_hit & (door_t < 1), door_t))
            for e, a, b in h["walls"]:
                if shared_wall(a, b, g["outline"], SHARED):
                    continue
                hit, t = ray_crossings(sx, sy, dx, dy, a, b)
                hit &= t < 1
                for _, door_hit, door_t in doors:  # through a door, not the wall around it
                    with np.errstate(invalid="ignore"):
                        hit &= ~(door_hit & (np.abs(t - door_t) * reach < 0.05))
                kerma = np.where(hit, kerma * factor(e), kerma)
            for e, door_hit, _ in doors:
                kerma = np.where(door_hit, kerma * factor(e), kerma)
        total = np.where(np.isnan(total), kerma, np.where(np.isnan(kerma), total, total + kerma))
    return X, Y, total


def kerma_scale(K):
    finite = K[np.isfinite(K)]
    top = max(float(np.nanpercentile(finite, 99.5)) if finite.size else 1.0, 1.0)
    return LogNorm(vmin=1e-3, vmax=top, clip=True)


def layout_rooms(geometries):
    """Rooms traced on a plan keep their place; schematic rooms are put in a row to the right of them."""
    placed = [p for g in geometries if not g["schematic"] for p in g["outline"]]
    x = max((p[0] for p in placed), default=0) + (2 if placed else 0)
    base = min((p[1] for p in placed), default=0)
    for g in geometries:
        if not g["schematic"]:
            continue
        min_x, min_y = min(p[0] for p in g["outline"]), min(p[1] for p in g["outline"])
        dx, dy = x - min_x, base - min_y
        move = lambda p: (p[0] + dx, p[1] + dy)
        g["outline"] = [move(p) for p in g["outline"]]
        g["walls"] = [(e, move(a), move(b)) for e, a, b in g["walls"]]
        g["doors"] = [(e, move(a), move(b)) for e, a, b in g["doors"]]
        g["source"] = move(g["source"])
        x = max(p[0] for p in g["outline"]) + 2
    return geometries


# ===================== link with the rooms of the program =====================
class PlanViews:
    def workspace_of(self, t):
        dep = self.d.get(f"dep {t}")
        return ("dep", dep) if dep else ("room", t)

    def workspace_rooms(self, key):
        if key[0] == "dep":
            return [t for t in self.departments[key[1]]["rooms"] if self.d[f"run {t}"]]
        return [key[1]]

    def workspace_title(self, key):
        if key[0] == "dep":
            return self.departments[key[1]]["name"].get().strip() or f"Department {key[1]}"
        return self.room_name(key[1])

    def open_plan(self, key, room=None):
        rooms = self.workspace_rooms(key)
        if not rooms:
            messagebox.showinfo("Floor plan", "Design at least one room first.", parent=self.master)
            return
        PlanEditor(self, key, self.workspace_title(key), rooms, room)

    def open_view(self, key):
        if not self.workspace_rooms(key):
            messagebox.showinfo("2D / 3D View", "Design at least one room first.", parent=self.master)
            return
        RoomViewer(self, key, self.workspace_title(key))

    def add_view_buttons(self, t, parent, row, column, columnspan=1):
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=column, columnspan=columnspan, padx=5, pady=5, sticky="w")
        tip(ttk.Button(frame, text="Floor Plan", command=lambda: self.open_plan(self.workspace_of(t), t)),
            "floor_plan").pack(side=LEFT, padx=3)
        tip(ttk.Button(frame, text="2D / 3D View", command=lambda: self.open_view(self.workspace_of(t))),
            "view_3d").pack(side=LEFT, padx=3)
        tip(ttk.Button(frame, text="Calculate all barriers", command=lambda: self.calculate_all(t)),
            "calculate_all").pack(side=LEFT, padx=3)

    def barrier_info(self, nr, e):
        """What the 2D / 3D view shows about barrier e of room nr: its state, the required and planned thickness of
        each material, what the barrier is built of, the dose beyond it and the transmission through it."""
        info = {"state": "not calculated", "rows": [], "built": [], "together": False, "layered": False,
                "planned": False, "check": None, "transmission": None, "missing": []}
        rec = self.calc.get((nr, e))
        if rec is None:
            return info
        if rec.get("missing"):
            info.update(state="missing", missing=list(rec["missing"]))
            return info
        planned = self.planned_layers(nr, e)
        planned_of = dict(planned)
        layered = bool(rec.get("layers"))
        info.update(state="ok", layered=layered, check=self.dose_check(nr, e),
                    rows=[(m, x, planned_of.get(m)) for m, x in rec.get("thickness") or []])
        if planned:  # everything planned is installed together
            info.update(built=planned, together=True, planned=True)
        else:  # the required thicknesses: layers together, or each material alone (alternatives)
            info.update(built=[(m, x) for m, x in rec.get("thickness") or []], together=layered)
        # transmission through the barrier, for the rays of the other rooms that cross it
        params = (rec.get("shield") or {}).get("params", {})
        usable = [(m, x) for m, x in info["built"] if x is not None and m in params]
        if usable:
            info["transmission"] = stack_transmission(params, usable) if info["together"] else                 max(archer_transmission(params[m], x) for m, x in usable)  # alternatives: the least protective
        return info

    def barrier_distance(self, t, e):
        nr = self.d[f"nr {t}"]
        widget = self.d.get(f"dist_var {e}{nr}") if self.d[f"vselroom {t}"].get() == "CT Room" \
            else self.d.get(f"entryd {e}{nr}0")
        try:
            distance = float(widget.get())
        except (AttributeError, ValueError, TclError):
            return None
        if self.whole_distance(e, nr):  # typed to the person beyond the barrier: the wall is that much closer
            distance -= self.entry_number(f"beyond {e}{nr}") or 0.0
        return distance if distance > 0 else None

    def apply_barrier_inputs(self, t, e, distance=None, location="", area="", primary=False, beyond=None):
        """Fill a barrier of room t with values from the floor plan (distance: from the source to the barrier;
        beyond: from the barrier to the occupied point)."""
        nr = self.d[f"nr {t}"]
        room_type = self.d[f"vselroom {t}"].get()
        if e > self.d[f"x {t}"]:  # more walls on the plan than barriers in the room
            self.d[f"vnumwall {t}"].set(e)
            self.barriers(t)
        if beyond is not None:
            self.d[f"beyond {e}{nr}"].set(f"{beyond:.2f}")
        if distance is not None or beyond is not None:  # the plan gives the distance to the barrier, and beyond it
            self.d[f"whole {e}{nr}"].set(0)
        if room_type == "CT Room":
            if distance is not None:
                self.d[f"dist_var {e}{nr}"].set(f"{distance:.2f}")
        else:
            if room_type in ("X-Ray room", "Fluoroscopy Room") and self.d[f"radiob_w {e}{nr}0"].get() == 0:
                self.d[f"radiob_w {e}{nr}0"].set(1 if primary else 2)
                self.barrier_sel(e, nr, t, 0)
            if distance is not None:
                for i in range(self.d[f"num_barriers_var {e}{nr}"].get()):
                    entry = self.d[f"entryd {e}{nr}{i}"]
                    entry.delete(0, "end")
                    entry.insert(0, f"{distance:.2f}")
        if area:
            self.d[f"area {e}{nr}"].set(area)
            self.set_design_goal(e, nr)
        if location:
            self.d[f"vraoccup {e}{nr}"].set(2)
            self.occupation3(e, nr, t)
            self.d[f"vselocation {e}{nr}"].set(location)

    def room_geometry(self, t):
        """Room outline (m, y up), walls, doors, source and results, from the floor plan or schematic. The walls
        (doors) of the plan are those of the room tab, in order; a wall (door) the room tab does not have is None."""
        nr = self.d[f"nr {t}"]
        barriers = {e: self.barn[f"lab_bar {e}{nr}"].cget("text") for e in range(1, self.d[f"x {t}"] + 1)}
        geometry = {"t": t, "nr": nr, "name": self.room_name(t), "type": self.d[f"vselroom {t}"].get(),
                    "barriers": barriers,
                    "results": {e: self.calc.get((nr, e)) for e in barriers}, "doors": []}
        of_kind = lambda kind: [e for e in barriers if self.barrier_kind(e, nr) == kind]
        nth = lambda found, k: found[k] if k < len(found) else None
        plan = self.plans.get(self.workspace_of(t))
        room = plan["rooms"].get(t) if plan else None
        if room and room["closed"] and plan["scale"]:
            s = plan["scale"]
            to_m = lambda p: (p[0] * s, -p[1] * s)
            outline = [to_m(p) for p in room["outline"]]
            walls, doors = of_kind("wall"), of_kind("door")
            geometry.update(outline=outline, schematic=False, height=room["height"],
                            source_height=room["source_height"],
                            walls=[(nth(walls, i), a, b) for i, (a, b) in enumerate(edges(outline))],
                            source=to_m(room["source"]) if room["source"] else centroid(outline),
                            doors=[(nth(doors, k), to_m(door["a"]), to_m(door["b"]))
                                   for k, door in enumerate(room_doors(room))])
            return geometry
        # Schematic: every wall at its entered distance from the source
        walls = of_kind("wall")
        distances = [self.barrier_distance(t, e) or SCHEMATIC_DISTANCE for e in walls]
        while len(distances) < 3:
            walls.append(None)
            distances.append(SCHEMATIC_DISTANCE)
        distances = [max(d, 0.5) for d in distances]
        corners = schematic_outline(distances)
        wall_list = [(e, corners[k], corners[(k + 1) % len(corners)]) for k, e in enumerate(walls) if e is not None]
        geometry.update(outline=corners, schematic=True, height=DEFAULT_HEIGHT, source_height=DEFAULT_SOURCE_HEIGHT,
                        walls=wall_list, source=(0.0, 0.0))
        if wall_list:
            # each door on the wall whose distance is closest to its own, side by side when they share a wall
            on_wall = {}
            for e in of_kind("door"):
                door_distance = self.barrier_distance(t, e)
                k = min(range(len(wall_list)), key=lambda j: abs(distances[j] - door_distance)) if door_distance else 0
                on_wall.setdefault(k, []).append(e)
            for k, doors in on_wall.items():
                _, a, b = wall_list[k]
                length = math.dist(a, b) or 1
                u = min(0.6, 0.4 * length / len(doors)) / length  # half the width of a door, along the wall
                point = lambda v: (a[0] + (b[0] - a[0]) * v, a[1] + (b[1] - a[1]) * v)
                for j, e in enumerate(doors):
                    middle = (j + 1) / (len(doors) + 1)
                    geometry["doors"].append((e, point(middle - u), point(middle + u)))
        return geometry
