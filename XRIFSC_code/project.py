import io
import json
import os
import zipfile
from datetime import datetime
from tkinter import Variable, TclError, filedialog, messagebox
from tkinter import ttk

from PIL import Image


FORMAT = "xray-shielding-project"
VERSION = 1
FILE_TYPES = [("Shielding project", "*.shield"), ("All files", "*.*")]
# Inputs of one radiation type of an X-ray / mammography barrier (keys "<name> <e><nr><i>")
RADIATION_KEYS = ["radiob_w", "setv", "entryd", "vselxray", "vsexroom", "use_ent", "entk", "preshvar", "radiob_pre",
                  "unairkerv", "airkerv", "radiob_leak", "oworkvar", "workv", "worentry", "numpapwe"]
CT_KEYS = ["bp_var", "hp_var", "dlpb_var", "dlph_var", "kvp_var"]


class ProjectFile:
    # ===================== reading and writing single inputs =====================
    def read_input(self, key):
        """Text of an entry, combobox or variable (None if it does not exist)."""
        widget = self.d.get(key)
        if widget is None:
            return None
        try:
            if isinstance(widget, Variable):
                return str(widget._tk.globalgetvar(widget._name))
            return widget.get()
        except (TclError, AttributeError):
            return None

    def write_input(self, key, value):
        widget = self.d.get(key)
        if widget is None or value is None:
            return
        if isinstance(widget, (Variable, ttk.Combobox)):
            widget.set(value)
        else:
            widget.delete(0, "end")
            widget.insert(0, value)

    # ===================== collecting the project =====================
    def room_data(self, t):
        nr = self.d[f"nr {t}"]
        ct = self.d[f"vselroom {t}"].get() == "CT Room"
        names = CT_KEYS if ct else ["vrawork", "worentry", "numpapwe"]
        data = {"barriers": self.d[f"x {t}"], "room": {name: self.read_input(f"{name} {t}") for name in names},
                "barrier_data": []}
        for e in range(1, self.d[f"x {t}"] + 1):
            count = int(self.read_input(f"vnumbmat {e}{nr}") or 1)
            barrier = {name: self.read_input(f"{name} {e}{nr}")
                       for name in ("area", "vraoccup", "occupentry", "vselocation", "dikeent", "dist_var")}
            barrier.update(materials=[self.read_input(f"vmater {e}{o}{nr}") for o in range(1, count + 1)],
                           matmode=self.read_input(f"matmode {e}{nr}"),
                           shares=[self.read_input(f"share {e}{o}{nr}") for o in range(1, count + 1)],
                           planned=[self.read_input(f"planned {e}{o}{nr}") for o in range(1, count + 1)],
                           checkplan=self.read_input(f"checkplan {e}{nr}"),
                           calculated=(nr, e) in self.calc, radiation=[])
            if not ct:
                for i in range(self.d[f"num_barriers_var {e}{nr}"].get()):
                    barrier["radiation"].append({name: self.read_input(f"{name} {e}{nr}{i}")
                                                 for name in RADIATION_KEYS})
            data["barrier_data"].append(barrier)
        return data

    def plan_data(self, key, positions, images, index):
        plan = self.plans.get(key)
        if not plan:
            return None
        image_file = None
        if plan["image"] is not None:
            image_file = f"plans/plan{index}.png"
            images[image_file] = plan["image"]
        return {"image": image_file, "image_name": plan["image_name"], "scale": plan["scale"],
                "rooms": {str(positions[t]): room for t, room in plan["rooms"].items() if t in positions}}

    def collect_project(self):
        """Everything needed to rebuild the work: departments, standalone rooms, inputs and floor plans."""
        workspaces, images = [], {}
        departments = {str(info["frame"]): dep for dep, info in self.departments.items()}
        standalone = {str(frame): t for t, frame in self.standalone.items() if frame.winfo_exists()}
        for tab in (map(str, self.depnote.tabs()) if self.depnote is not None else []):
            if tab in departments:
                dep = departments[tab]
                info = self.departments[dep]
                workspace = {"kind": "department", "name": info["name"].get(), "rooms": [
                    {"name": self.d[f"vname_room {t}"].get(), "type": self.d[f"vselroom {t}"].get(),
                     "designed": bool(self.d[f"run {t}"]),
                     "data": self.room_data(t) if self.d[f"run {t}"] else None} for t in info["rooms"]]}
                key, positions = ("dep", dep), {t: k for k, t in enumerate(info["rooms"])}
            elif tab in standalone:
                t = standalone[tab]
                workspace = {"kind": "room", "type": self.d[f"vselroom {t}"].get(),
                             "name": self.d[f"vname_room {t}"].get(), "data": self.room_data(t)}
                key, positions = ("room", t), {t: 0}
            else:
                continue
            workspace["plan"] = self.plan_data(key, positions, images, len(workspaces))
            workspaces.append(workspace)
        project = {"format": FORMAT, "version": VERSION, "saved": datetime.now().isoformat(timespec="seconds"),
                   "workspaces": workspaces}
        return project, images

    def write_project(self, path):
        project, images = self.collect_project()
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("project.json", json.dumps(project, indent=1, ensure_ascii=False))
            for name, image in images.items():
                buffer = io.BytesIO()
                image.save(buffer, "PNG")
                archive.writestr(name, buffer.getvalue())

    # ===================== rebuilding the project =====================
    def restore_room(self, t, data):
        nr = self.d[f"nr {t}"]
        room_type = self.d[f"vselroom {t}"].get()
        if data["barriers"] != self.d[f"x {t}"]:
            self.d[f"vnumwall {t}"].set(data["barriers"])
            self.barriers(t)
        room = data["room"]
        if room_type == "CT Room":
            for name in CT_KEYS:
                self.write_input(f"{name} {t}", room.get(name))
        elif room.get("vrawork") in ("1", "2"):
            self.write_input(f"vrawork {t}", room["vrawork"])
            self.workload(t)
            self.write_input(f"worentry {t}", room.get("worentry"))
            self.write_input(f"numpapwe {t}", room.get("numpapwe"))
        for e, barrier in enumerate(data["barrier_data"], start=1):
            if room_type == "CT Room":
                self.write_input(f"dist_var {e}{nr}", barrier.get("dist_var"))
            else:
                self.restore_radiation(t, e, nr, barrier["radiation"])
            self.write_input(f"area {e}{nr}", barrier.get("area"))
            if barrier.get("vraoccup") in ("1", "2"):
                self.write_input(f"vraoccup {e}{nr}", barrier["vraoccup"])
                self.occupation3(e, nr, t)
                self.write_input(f"occupentry {e}{nr}", barrier.get("occupentry"))
                self.write_input(f"vselocation {e}{nr}", barrier.get("vselocation"))
            self.write_input(f"dikeent {e}{nr}", barrier.get("dikeent"))
            self.write_input(f"vnumbmat {e}{nr}", str(len(barrier["materials"])))
            self.numbmater(e, nr, t)
            for o, material in enumerate(barrier["materials"], start=1):
                self.write_input(f"vmater {e}{o}{nr}", material)
            if barrier.get("matmode") == "combined":
                self.write_input(f"matmode {e}{nr}", "combined")
                self.update_material_panel(e, nr, t)
                for o, share in enumerate(barrier.get("shares") or [], start=1):
                    self.write_input(f"share {e}{o}{nr}", share)
            for o, planned in enumerate(barrier.get("planned") or [], start=1):
                self.write_input(f"planned {e}{o}{nr}", planned)
            # older files have planned thicknesses without the option: check them when any is given
            check = barrier.get("checkplan") or ("1" if any(barrier.get("planned") or []) else "0")
            if check != self.read_input(f"checkplan {e}{nr}"):
                self.write_input(f"checkplan {e}{nr}", check)
                self.update_material_panel(e, nr, t)
        for e, barrier in enumerate(data["barrier_data"], start=1):
            if barrier.get("calculated"):
                self.choosetype(e, nr, t, notify=False)

    def restore_radiation(self, t, e, nr, items):
        # The widgets of a radiation type appear step by step, as when the user clicks them
        if items and len(items) != self.d[f"num_barriers_var {e}{nr}"].get():
            self.d[f"num_barriers_var {e}{nr}"].set(len(items))
            self._create_barrier_widgets(e, nr, t)
        for i, saved in enumerate(items):
            key = lambda name: f"{name} {e}{nr}{i}"
            radiation = saved.get("radiob_w")
            if radiation in ("1", "2") and (self.read_input(key("radiob_w")) != radiation
                                            or key("workltit") not in self.d):
                self.write_input(key("radiob_w"), radiation)
                self.barrier_sel(e, nr, t, i)
            self.write_input(key("setv"), saved.get("setv"))
            self.write_input(key("entryd"), saved.get("entryd"))
            if saved.get("vselxray") in ("1", "2"):
                self.write_input(key("vselxray"), saved["vselxray"])
                self.XrRoom(e, nr, i)
                self.write_input(key("vsexroom"), saved.get("vsexroom"))
            if radiation == "1":
                self.write_input(key("use_ent"), saved.get("use_ent"))
                self.write_input(key("entk"), saved.get("entk"))
                if saved.get("preshvar") == "1":
                    self.write_input(key("preshvar"), "1")
                    self.pres(e, nr, i)
                    self.write_input(key("radiob_pre"), saved.get("radiob_pre"))
            elif radiation == "2" and saved.get("unairkerv") in ("1", "2"):
                self.write_input(key("unairkerv"), saved["unairkerv"])
                self.unairk(e, nr, i)
                if saved["unairkerv"] == "2":
                    self.write_input(key("entk"), saved.get("entk"))
                elif saved.get("airkerv") in ("1", "2", "3"):
                    self.write_input(key("airkerv"), saved["airkerv"])
                    self.leakage(e, nr, i)
                    self.write_input(key("radiob_leak"), saved.get("radiob_leak"))
            if saved.get("oworkvar") == "1":
                self.write_input(key("oworkvar"), "1")
                self.owork(e, nr, i)
                if saved.get("workv") in ("1", "2"):
                    self.write_input(key("workv"), saved["workv"])
                    self.workloadbar(e, nr, i)
                    self.write_input(key("worentry"), saved.get("worentry"))
                    self.write_input(key("numpapwe"), saved.get("numpapwe"))

    def restore_plan(self, key, data, rooms_by_position, archive):
        if not data:
            return
        image = None
        if data.get("image"):
            image = Image.open(io.BytesIO(archive.read(data["image"])))
            image.load()
        as_point = lambda p: tuple(p) if p is not None else None
        rooms = {}
        for position, room in data["rooms"].items():
            t = rooms_by_position.get(int(position))
            if t is None:
                continue
            room["outline"] = [as_point(p) for p in room["outline"]]
            room["source"] = as_point(room.get("source"))
            if room.get("door"):
                room["door"]["a"], room["door"]["b"] = as_point(room["door"]["a"]), as_point(room["door"]["b"])
            rooms[t] = room
        self.plans[key] = {"image": image, "image_name": data.get("image_name", ""), "scale": data.get("scale"),
                           "rooms": rooms}

    def reset_workspace(self):
        """Close every department, room and window: an empty program, as at start-up."""
        for window in self.master.winfo_children():
            if window.winfo_class() == "Toplevel":
                window.destroy()
        if self.depnote is not None:
            self.depnote.destroy()
            self.depnote = None
        for label in self.barn.values():
            label.destroy()
        for store in (self.d, self.res, self.thm, self.barn, self.barr, self.calc, self.plans, self.departments,
                      self.tab_links, self.tab_names, self.note_pairs, self.standalone, self.highlighted):
            store.clear()
        self.highlight_bound.clear()
        self.dep_count = self.room_count = self.standalone_count = 0
        self.ep = 1

    def load_project(self, path):
        with zipfile.ZipFile(path) as archive:
            project = json.loads(archive.read("project.json").decode("utf-8"))
            if project.get("format") != FORMAT:
                raise ValueError("This file is not a shielding project.")
            self.build_project(project, archive)
        return project

    def build_project(self, project, archive=None):
        """Replace the current work with the project (archive holds its floor plan drawings, if any)."""
        self.reset_workspace()
        self.hide_start_buttons()
        for workspace in project["workspaces"]:
            if workspace["kind"] == "department":
                self.creatdep()
                dep = self.dep_count
                info = self.departments[dep]
                info["name"].set(workspace["name"])
                info["numrooms"].set(len(workspace["rooms"]))
                self.createrooms(dep)
                for t, room in zip(info["rooms"], workspace["rooms"]):
                    self.d[f"vname_room {t}"].set(room["name"])
                    self.d[f"vselroom {t}"].set(room["type"])
                    if room["designed"]:
                        self.desroom(t)
                        self.restore_room(t, room["data"])
                info["rooms_note"].select(0)
                self.restore_plan(("dep", dep), workspace.get("plan"), dict(enumerate(info["rooms"])), archive)
            else:
                if workspace["type"] == "CT Room":
                    t = self.creatCTroom()
                else:
                    t = self.creatroom(workspace["type"])
                self.d[f"vname_room {t}"].set(workspace["name"])
                self.restore_room(t, workspace["data"])
                self.restore_plan(("room", t), workspace.get("plan"), {0: t}, archive)
        if self.depnote is not None and self.depnote.tabs():
            self.depnote.select(0)
        else:
            self.show_start_buttons()

    # ===================== menu commands =====================
    def set_project_path(self, path):
        self.project_path = path

    def save_project(self, event=None):
        if not self.project_path:
            return self.save_project_as()
        try:
            self.write_project(self.project_path)
        except OSError as error:
            messagebox.showerror("Save project", f"Cannot save the project:\n{error}", parent=self.master)
            return False
        return True

    def save_project_as(self, event=None):
        if self.depnote is None:
            messagebox.showinfo("Save project", "There is nothing to save yet.", parent=self.master)
            return False
        path = filedialog.asksaveasfilename(parent=self.master, title="Save project", defaultextension=".shield",
                                            filetypes=FILE_TYPES, initialdir=os.path.expanduser("~"),
                                            initialfile=os.path.basename(self.project_path or "Shielding project"))
        if not path:
            return False
        self.set_project_path(path)
        return self.save_project()

    def keep_current_work(self, action):
        """Ask to save the current work before it is closed; False if the user cancels."""
        if self.depnote is None:
            return True
        answer = messagebox.askyesnocancel(action, "Save the current project first?", parent=self.master)
        if answer is None:
            return False
        return self.save_project() if answer else True

    def open_project(self, event=None):
        if not self.keep_current_work("Open project"):
            return
        path = filedialog.askopenfilename(parent=self.master, title="Open project", filetypes=FILE_TYPES,
                                          initialdir=os.path.dirname(self.project_path or os.path.expanduser("~")))
        if path:
            self.open_project_file(path)

    def open_project_file(self, path):
        try:
            project = self.load_project(path)
        except (OSError, KeyError, ValueError, zipfile.BadZipFile) as error:
            messagebox.showerror("Open project", f"Cannot open the project:\n{error}", parent=self.master)
            return
        if project.get("description"):
            # An example file: Save asks for a new name, so the example itself stays unchanged
            self.set_project_path(None)
            messagebox.showinfo(project.get("title", "Example"), project["description"], parent=self.master)
        else:
            self.set_project_path(path)

    def new_project(self, event=None):
        if not self.keep_current_work("New project"):
            return
        self.reset_workspace()
        self.hide_start_buttons()
        self.show_start_buttons()
        self.set_project_path(None)
