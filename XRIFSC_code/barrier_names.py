"""The names and kinds of the barriers of a room. Barriers 1 and 2 are the floor and the ceiling and keep their names;
the others are walls ('Wall 1', 'Wall 2', ...) or doors ('Door 1', ...), which the user can name. Every barrier of a
room has its own name."""
from tkinter import Toplevel, StringVar, TclError
from tkinter import ttk

import theme

KIND_NAMES = {"floor": "Floor", "ceiling": "Ceiling", "wall": "Wall", "door": "Door"}
NAME_LENGTH = 40
DOOR_HEIGHT = 2.1  # m, as the floor plan and the 2D / 3D view draw a door


def default_kind(e):
    """Barrier 1 is the floor, 2 the ceiling, 3 a door and the others walls, until the user changes them."""
    return {1: "floor", 2: "ceiling", 3: "door"}.get(e, "wall")


def default_name(kind, e, others):
    """'Wall 3': the walls are counted up to barrier e (the doors likewise), and the next number is taken when a
    barrier of the room already has the name. others: [(barrier, kind, name)] of the other barriers of the room."""
    if kind in ("floor", "ceiling"):
        return KIND_NAMES[kind]
    n = 1 + sum(1 for k, other, _ in others if other == kind and k < e)
    used = {name.casefold() for _, _, name in others}
    while f"{KIND_NAMES[kind]} {n}".casefold() in used:
        n += 1
    return f"{KIND_NAMES[kind]} {n}"


def name_problem(name, others):
    """Why the name cannot be given (None if it can; an empty name takes the default name)."""
    name = name.strip()
    if len(name) > NAME_LENGTH:
        return f"At most {NAME_LENGTH} characters."
    if name and name.casefold() in {other.casefold() for _, _, other in others}:
        return f"'{name}' is already a barrier of this room: every barrier needs its own name."
    return None


def door_material(room_type):
    """What a new door is made of: a solid-core wooden door in mammography (NCRP 147 5.5), else a lead-lined door
    (NCRP 147 2.3.3.1)."""
    return "Wood" if room_type == "Mammography Room" else "Lead"


def kind_note(kind, room_type):
    """What choosing a wall or a door does."""
    if kind == "wall":
        return "A wall of the room. The walls traced on the floor plan are the walls of the room, in their order."
    radiation = "a secondary barrier of " if room_type in ("X-Ray room", "Fluoroscopy Room") else ""
    material = ("wood (a solid-core door, NCRP 147 5.5)" if room_type == "Mammography Room"
                else "lead (a lead-lined door, NCRP 147 2.3.3.1)")
    return (f"A door starts as {radiation}{material}; you can change them. On the floor plan and in the 2D / 3D "
            f"view it lies on a wall, {DOOR_HEIGHT:g} m high, and the radiation through it is that of the door.")


class BarrierDialog(Toplevel):
    """The kind (wall or door) and the name of a barrier: of a new one (e is the number it will have), or of barrier
    e. others: [(barrier, kind, name)] of the other barriers of the room. on_done(kind, name) gets the name typed,
    or the default name when it is left empty."""

    def __init__(self, master, e, kind, name, others, room_type, on_done, new=False, near=None):
        super().__init__(master)
        self.e, self.others, self.on_done, self.room_type = e, others, on_done, room_type
        self.title("Add a barrier" if new else "Barrier")
        self.transient(master.winfo_toplevel())
        self.resizable(False, False)
        self.configure(background=theme.SURFACE)
        box = ttk.Frame(self, padding=theme.px(14))
        box.pack(fill="both", expand=1)
        ttk.Label(box, text="Add a barrier to the room" if new else "Name and kind of the barrier",
                  style="BL2.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        ttk.Label(box, text="It is a:").grid(row=1, column=0, sticky="w", padx=(0, 8))
        self.kind = StringVar(value=kind)
        self.buttons = {}
        for column, value in enumerate(("wall", "door"), start=1):
            self.buttons[value] = ttk.Radiobutton(box, text=KIND_NAMES[value], value=value, variable=self.kind)
            self.buttons[value].grid(row=1, column=column, sticky="w", padx=(0, 14))
        self.note = ttk.Label(box, style="Muted.TLabel", wraplength=theme.px(380), justify="left")
        self.note.grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 10))
        ttk.Label(box, text="Name:").grid(row=3, column=0, sticky="w", padx=(0, 8))
        self.name = StringVar(value="" if new else name)
        self.entry = ttk.Entry(box, textvariable=self.name, width=34)
        self.entry.grid(row=3, column=1, columnspan=2, sticky="w")
        self.hint = ttk.Label(box, style="Muted.TLabel")
        self.hint.grid(row=4, column=1, columnspan=2, sticky="w", pady=(2, 0))
        self.error = ttk.Label(box, style="RL.TLabel", wraplength=theme.px(380), justify="left")
        self.error.grid(row=5, column=0, columnspan=3, sticky="w", pady=(4, 0))
        buttons = ttk.Frame(box)
        buttons.grid(row=6, column=0, columnspan=3, sticky="e", pady=(10, 0))
        self.ok_button = ttk.Button(buttons, text="Add" if new else "OK", style="Accent.TButton", command=self.ok)
        self.ok_button.pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left")
        self.shown_kind = kind
        self.kind.trace_add("write", lambda *args: self.kind_changed())
        self.name.trace_add("write", lambda *args: self.update_view())
        self.bind("<Return>", lambda event: self.ok())
        self.bind("<Escape>", lambda event: self.destroy())
        self.update_view()
        self.place_near(near)
        self.entry.focus_set()
        self.entry.select_range(0, "end")
        self.after_idle(self.hold_focus)

    def default(self):
        return default_name(self.kind.get(), self.e, self.others)

    def kind_changed(self):
        # a default name follows the kind: 'Wall 4' becomes 'Door 2'
        previous = default_name(self.shown_kind, self.e, self.others)
        if self.name.get().strip().casefold() == previous.casefold():
            self.name.set(self.default())
        self.shown_kind = self.kind.get()
        self.update_view()

    def update_view(self):
        self.note.configure(text=kind_note(self.kind.get(), self.room_type))
        self.hint.configure(text=f"Leave it empty for '{self.default()}'.")
        problem = name_problem(self.name.get(), self.others)
        self.error.configure(text=problem or "")
        self.ok_button.state(["disabled"] if problem else ["!disabled"])

    def ok(self):
        if name_problem(self.name.get(), self.others):
            self.bell()
            return
        kind, name = self.kind.get(), self.name.get().strip() or self.default()
        self.destroy()
        self.on_done(kind, name)

    def place_near(self, widget):
        """Under the widget that opened it, inside the screen."""
        self.update_idletasks()
        if widget is not None and widget.winfo_exists():
            x, y = widget.winfo_rootx(), widget.winfo_rooty() + widget.winfo_height() + 4
        else:
            x, y = self.master.winfo_pointerx(), self.master.winfo_pointery()
        x = min(max(x, 0), self.winfo_screenwidth() - self.winfo_reqwidth() - 8)
        y = min(max(y, 0), self.winfo_screenheight() - self.winfo_reqheight() - 48)
        self.geometry(f"+{x}+{y}")

    def hold_focus(self):
        # the room cannot change while the dialog is open
        try:
            self.grab_set()
        except TclError:  # not shown yet
            pass
