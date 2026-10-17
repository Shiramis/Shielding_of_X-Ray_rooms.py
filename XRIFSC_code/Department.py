import os
import tkinter
from tkinter import *
from tkinter import ttk
import theme
import xlsxwriter
from tooltips import tip

ROOM_TYPES = ["X-Ray room", "CT Room", "Mammography Room"]

class ddepartment():
    # ============creating def for Deparment notebook===================================
    def creatdep(self):
        # Every call adds a new department tab; departments are independent of each other.
        # Inside the department tab: its rooms on the left and their results on the right.
        self.hide_start_buttons()
        depnote = self.ensure_workspace()
        self.dep_count += 1
        dep = self.dep_count

        # Create and configure the department frame with its rooms and results notebooks
        self.depframe = ttk.Frame(depnote)
        self.depframe.pack(fill=BOTH, expand=1)
        depnote.add(self.depframe)
        left, right = self.split_pane(self.depframe, 950, 520)
        rooms_note = ttk.Notebook(left, style="BL.TNotebook", width=theme.px(950))
        rooms_note.pack(fill=BOTH, expand=1)
        results_note = ttk.Notebook(right, style="BL.TNotebook", width=theme.px(520))
        results_note.pack(fill=BOTH, expand=1)
        setup = ttk.Frame(rooms_note)
        rooms_note.add(setup, text="Rooms")

        depcanv = Canvas(setup)
        depcanv.pack(side=LEFT, fill=BOTH, expand=1)
        scrolldep = ttk.Scrollbar(setup, orient=VERTICAL, command=depcanv.yview)
        scrolldep.pack(side=RIGHT, fill=Y)
        depcanv.configure(yscrollcommand=scrolldep.set, bg=theme.SURFACE)

        # Create and configure the rooms frame inside the department canvas
        roomsframe = ttk.Frame(depcanv)
        roomsframe.bind('<Configure>', lambda e, c=depcanv: c.configure(scrollregion=c.bbox("all")))
        depcanv.create_window((0, 0), window=roomsframe, anchor="nw")

        info = {"frame": self.depframe, "rooms_frame": roomsframe, "rooms": [],
                "rooms_note": rooms_note, "results_note": results_note,
                "name": StringVar(value=f"Department {dep}"), "numrooms": IntVar(value=1)}
        self.departments[dep] = info

        # Department name (shown on the tab, can be changed at any time)
        name_label = ttk.Label(master=roomsframe, style="BL.TLabel", text="Department Name:")
        name_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        name_entry = ttk.Entry(master=roomsframe, textvariable=info["name"], width=30)
        name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=10, sticky="w")
        tip(name_label, "department_name")
        tip(name_entry, "department_name")
        self.register_tab_name(self.depframe, info["name"], f"Department {dep}", depnote)
        new_dep = ttk.Button(master=roomsframe, text="New Department", command=self.creatdep)
        new_dep.grid(row=0, column=4, padx=10, pady=10, sticky="w")
        tip(new_dep, "new_department")

        # Add widgets to the rooms frame
        label_rooms = ttk.Label(master=roomsframe, style="BL.TLabel", text="Rooms of Department")
        label_rooms.grid(row=1, column=0, sticky="nswe", padx=10)
        numrlab = ttk.Label(master=roomsframe, style="AL.TLabel", text="Number of Rooms:")
        numrlab.grid(row=2, column=0, pady=10, padx=10, sticky="w")
        num_rooms = ttk.Spinbox(master=roomsframe, from_=0, to=10000, increment=1,
                                textvariable=info["numrooms"], width=5, command=lambda: self.createrooms(dep))
        num_rooms.grid(row=2, column=1, pady=10, padx=20, sticky="e")
        tip(numrlab, "num_rooms")
        tip(num_rooms, "num_rooms")
        exp_but = ttk.Button(master=roomsframe, text="Export to Excel", command=lambda: self.exp_dep(dep))
        exp_but.grid(row=2, column=2, pady=10, padx=10, sticky="w")
        tip(exp_but, "export")
        plan_but = ttk.Button(master=roomsframe, text="Floor Plan", command=lambda: self.open_plan(("dep", dep)))
        plan_but.grid(row=2, column=3, pady=10, padx=10, sticky="w")
        tip(plan_but, "floor_plan")
        view_but = ttk.Button(master=roomsframe, text="2D / 3D View", command=lambda: self.open_view(("dep", dep)))
        view_but.grid(row=2, column=4, pady=10, padx=10, sticky="w")
        tip(view_but, "view_3d")

        # Call to create rooms
        self.createrooms(dep)
        depnote.select(self.depframe)
    def createrooms(self, dep):
        info = self.departments[dep]
        rooms, roomsframe = info["rooms"], info["rooms_frame"]
        # Add rooms while there are fewer than the number of rooms
        while len(rooms) < info["numrooms"].get():
            self.room_count += 1
            t = self.room_count
            rooms.append(t)
            row = 2 + len(rooms)
            self.d[f"dep {t}"] = dep
            self.d[f"room_default {t}"] = f"Room {len(rooms)}"
            # Create and place the room description label
            self.d[f"labelname {t}"] = ttk.Label(master=roomsframe, style="AL.TLabel",
                text=f"Room Description {len(rooms)}:")
            self.d[f"labelname {t}"].grid(row=row, column=0, padx=10, pady=10, sticky="w")
            # Create and place the room name entry field (renames the room tabs at any time)
            self.d[f"vname_room {t}"] = StringVar()
            self.d[f"name_room {t}"] = ttk.Entry(master=roomsframe, textvariable=self.d[f"vname_room {t}"])
            self.d[f"name_room {t}"].grid(row=row, column=1, sticky="w")
            tip(self.d[f"name_room {t}"], "room_name")
            # Create and place the room selection combobox
            self.d[f"vselroom {t}"] = StringVar()
            self.d[f"selroom {t}"] = ttk.Combobox(master=roomsframe,
                textvariable=self.d[f"vselroom {t}"], values=ROOM_TYPES, state="readonly")
            self.d[f"selroom {t}"].grid(row=row, column=2, pady=10, padx=20, sticky="w")
            self.d[f"selroom {t}"].set("Shield room")
            tip(self.d[f"selroom {t}"], "room_type")
            # Create and place the design button
            self.d[f"run {t}"] = False  # Run every room only once
            self.d[f"crroomb {t}"] = ttk.Button(master=roomsframe, text="Design", style="Accent.TButton",
                command=lambda t=t: self.desroom(t))
            self.d[f"crroomb {t}"].grid(row=row, column=4, padx=10, pady=10, sticky="w")
            tip(self.d[f"crroomb {t}"], "design_room")
            # Initialize values for the room result frame
            self.d[f"resframe {t}"] = None
        # Remove rooms while there are more than the number of rooms
        while len(rooms) > info["numrooms"].get():
            t = rooms.pop()
            for key in (f"labelname {t}", f"name_room {t}", f"selroom {t}", f"crroomb {t}"):
                self.d[key].destroy()
            # If room has been run, destroy its tabs too
            if self.d[f"run {t}"]:
                self.d[f"newroomf {t}"].destroy()
                self.d[f"resframe {t}"].destroy()
                self.d[f"run {t}"] = False
    def desroom(self, t):
        room_type = self.d[f"vselroom {t}"].get()
        info = self.departments[self.d[f"dep {t}"]]
        rooms_note, results_note = info["rooms_note"], info["results_note"]
        if room_type != "Shield room":
            if not self.d[f"run {t}"]:
                # Initialize room-specific values
                self.d[f"selxroom {t}"] = None
                self.d[f"numpapwl {t}"] = None
                self.d[f"numpapwe {t}"] = None
                self.d[f"sellocation {t}"] = None
                # Create the room frame inside the department's rooms notebook
                self.d[f"newroomf {t}"] = ttk.Frame(rooms_note)
                self.d[f"newroomf {t}"].pack()
                rooms_note.add(self.d[f"newroomf {t}"])

                # Set up scrollbars for the canvas
                self.roomcanv = Canvas(self.d[f"newroomf {t}"])
                self.xscrollroom = ttk.Scrollbar(self.d[f"newroomf {t}"], orient=HORIZONTAL,
                                                 command=self.roomcanv.xview)
                self.xscrollroom.pack(side=BOTTOM, fill=X)

                self.yscrollroom = ttk.Scrollbar(self.d[f"newroomf {t}"], orient=VERTICAL, command=self.roomcanv.yview)
                self.yscrollroom.pack(side=RIGHT, fill=Y)

                self.roomcanv.configure(yscrollcommand=self.yscrollroom.set, xscrollcommand=self.xscrollroom.set,
                                        bg=theme.SURFACE)
                self.roomcanv.pack(side=LEFT, fill=BOTH, expand=1)

                # Create frame inside the canvas
                self.d[f"frame_1 {t}"] = ttk.Frame(self.roomcanv)
                self.d[f"frame_1 {t}"].bind('<Configure>',
                                            lambda e, c=self.roomcanv: c.configure(scrollregion=c.bbox("all")))
                self.roomcanv.create_window((0, 0), window=self.d[f"frame_1 {t}"], anchor="nw")
                # Mouse wheel scrolling is handled globally in App.on_mousewheel
                # Initialize some room values
                self.d[f"x {t}"] = 0
                self.d[f"y {t}"] = 0
                self.d[f"nr {t}"] = f"Room {t}:"  # unique across departments
                self.ep = 1
                # Create a notebook with Room variables
                self.d[f"noteb {t}{self.d[f'nr {t}']}"] = ttk.Notebook(self.d[f"frame_1 {t}"], style="BL.TNotebook")
                # Create label for number of barriers and spinbox for selection
                self.lanumwall = ttk.Label(self.d[f"frame_1 {t}"], style="AL.TLabel", text="Number of Barriers")
                self.lanumwall.grid(row=0, column=0, pady=5, padx=5, sticky="w")
                self.d[f"vnumwall {t}"] = IntVar(value=7)
                self.d[f"numwall {t}"] = ttk.Spinbox(self.d[f"frame_1 {t}"], from_=7, to=50, width=5,
                                                     textvariable=self.d[f"vnumwall {t}"],
                                                     command=lambda: self.barriers(t))
                self.d[f"numwall {t}"].grid(row=0, column=1, pady=5, padx=5, sticky="w")
                tip(self.lanumwall, "num_barriers")
                tip(self.d[f"numwall {t}"], "num_barriers")
                # Call the barriers method
                self.barriers(t)
                # Add close button for room frame
                self.closBut = ttk.Button(self.d[f"newroomf {t}"], text="✕", width=3, style="Close.TButton",
                                          command=lambda: self.closedeproom(t))
                self.closBut.pack()
                # If not a CT room, add "Combine Barriers" checkbox
                """if room_type != "CT Room":
                    self.d[f"varcompb {t}"] = IntVar(value=0)
                    self.d[f"compb {t}"] = ttk.Checkbutton(self.d[f"frame_1 {t}"], text="Combine Barriers as one",
                                                           variable=self.d[f"varcompb {t}"], onvalue=1, offvalue=0,
                                                           command=lambda: self.combination(t))
                    self.d[f"compb {t}"].grid(row=10, column=0, pady=5, padx=5, sticky="w")"""
                # Setup for X-Ray and Mammography Room types
                if room_type in ("X-Ray room", "Mammography Room"):
                    self.setup_xray_room(t)
                    self.add_view_buttons(t, self.d[f"frame_1 {t}"], row=2, column=0, columnspan=6)
                # Setup for CT Room type
                elif room_type == "CT Room":
                    self.setup_ct_room(t)
                    self.add_view_buttons(t, self.d[f"frame_1 {t}"], row=10, column=0, columnspan=12)
                # Setup the results tab
                self.setup_results(t, results_note)
                self.link_tabs(self.d[f"newroomf {t}"], self.d[f"resframe {t}"], rooms_note, results_note)
                self.register_tab_name(self.d[f"newroomf {t}"], self.d[f"vname_room {t}"],
                                       self.d[f"room_default {t}"], rooms_note)
                # The room type cannot change once the room is designed
                self.d[f"selroom {t}"].state(["disabled"])
            else:
                # Show the room again if its tabs were closed
                rooms_note.add(self.d[f"newroomf {t}"])
                results_note.add(self.d[f"resframe {t}"])
            # Select the current room and its results inside the department
            self.depnote.select(info["frame"])
            rooms_note.select(self.d[f"newroomf {t}"])
            results_note.select(self.d[f"resframe {t}"])
    def setup_xray_room(self, t):
        # Add workload and X-ray room options
        self.title_workload = ttk.Label(self.d[f"frame_1 {t}"], style="BL.TLabel", text="Workload:")
        self.title_workload.grid(row=1, column=0, pady=5, padx=5, sticky="w")
        tip(self.title_workload, "workload")
        # Additional workload entry options
        self.d[f"worentry {t}"] = None
        self.d[f"vrawork {t}"] = IntVar(value=0)
        self.raworkl = ttk.Radiobutton(self.d[f"frame_1 {t}"], text="Write total\nWorkload (mA∙min∙week\u207B\u00b9):",
                                       variable=self.d[f"vrawork {t}"], value=1, command=lambda: self.workload(t))
        self.raworkl.grid(row=1, column=1, pady=5, padx=5, sticky="w")
        self.ranumb = ttk.Radiobutton(self.d[f"frame_1 {t}"], text="The Number of\nPatients per week:",
                                      variable=self.d[f"vrawork {t}"], value=2, command=lambda: self.workload(t))
        self.ranumb.grid(row=1, column=3, pady=5, padx=5, sticky="w")
        tip(self.raworkl, "workload_total")
        tip(self.ranumb, "workload_patients")
    def setup_ct_room(self, t):
        # CT room setup with body/head procedures, kVp, and DLP entries
        self.bp_label = ttk.Label(self.d[f"frame_1 {t}"], text='Body Procedures (weekly):')
        self.bp_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.d[f"bp_var {t}"] = IntVar()
        self.bp_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.d[f"bp_var {t}"], width=10)
        self.bp_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        self.hp_label = ttk.Label(self.d[f"frame_1 {t}"], text='Head Procedures (weekly):')
        self.hp_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.d[f"hp_var {t}"] = IntVar()
        self.hp_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.d[f"hp_var {t}"], width=10)
        self.hp_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        self.kvp_label = ttk.Label(self.d[f"frame_1 {t}"], text='Give kVp:')
        self.kvp_label.grid(row=6, column=0, padx=10, pady=10, sticky="w")
        self.d[f"kvp_var {t}"] = IntVar()
        self.kvp_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.d[f"kvp_var {t}"], width=10)
        self.kvp_entry.grid(row=6, column=1, padx=10, pady=10, sticky="w")

        self.dlpb_label = ttk.Label(self.d[f"frame_1 {t}"], text='Give DLP/body procedure:')
        self.dlpb_label.grid(row=7, column=0, padx=10, pady=10, sticky="w")
        self.d[f"dlpb_var {t}"] = IntVar()
        self.dlpb_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.d[f"dlpb_var {t}"], width=10)
        self.dlpb_entry.grid(row=7, column=1, padx=10, pady=10, sticky="w")

        self.dlph_label = ttk.Label(self.d[f"frame_1 {t}"], text='Give DLP/head procedure:')
        self.dlph_label.grid(row=8, column=0, padx=10, pady=10, sticky="w")
        self.d[f"dlph_var {t}"] = IntVar()
        self.dlph_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.d[f"dlph_var {t}"], width=10)
        self.dlph_entry.grid(row=8, column=1, padx=10, pady=10, sticky="w")
        for name in ("bp", "hp", "dlpb", "dlph"):  # kept for highlighting empty entries
            self.d[f"{name}_entry {t}"] = getattr(self, f"{name}_entry")
        for widget, key in ((self.bp_label, "ct_body"), (self.bp_entry, "ct_body"),
                            (self.hp_label, "ct_head"), (self.hp_entry, "ct_head"),
                            (self.kvp_label, "ct_kvp"), (self.kvp_entry, "ct_kvp"),
                            (self.dlpb_label, "ct_dlp_body"), (self.dlpb_entry, "ct_dlp_body"),
                            (self.dlph_label, "ct_dlp_head"), (self.dlph_entry, "ct_dlp_head")):
            tip(widget, key)
    def setup_results(self, t, results_note):
        # Add result frame for each room, in the department's results notebook
        self.d[f"resframe {t}"] = ttk.Frame(results_note)
        self.d[f"resframe {t}"].pack()
        results_note.add(self.d[f"resframe {t}"])

        # ======Results scrollbar=========
        self.rescanv = Canvas(self.d[f"resframe {t}"])

        self.scrollres = ttk.Scrollbar(self.d[f"resframe {t}"], orient=VERTICAL, command=self.rescanv.yview)
        self.scrollres.pack(side=RIGHT, fill=Y)

        self.xscrollres = ttk.Scrollbar(self.d[f"resframe {t}"], orient=HORIZONTAL, command=self.rescanv.xview)
        self.xscrollres.pack(side=BOTTOM, fill=X)

        self.rescanv.configure(yscrollcommand=self.scrollres.set, xscrollcommand=self.xscrollres.set, bg=theme.SURFACE)
        self.rescanv.pack(side=LEFT, fill=BOTH, expand=1)

        # =========Results tab===========================
        self.d[f"resultframe {t}{self.d[f'nr {t}']}"] = ttk.Frame(self.rescanv)
        self.d[f"resultframe {t}{self.d[f'nr {t}']}"].bind('<Configure>', lambda e, c=self.rescanv: c.configure(
            scrollregion=c.bbox("all")))
        self.rescanv.create_window((0, 0), window=self.d[f"resultframe {t}{self.d[f'nr {t}']}"], anchor="nw")

        self.reshield = ttk.Label(self.d[f"resultframe {t}{self.d[f'nr {t}']}"], style="BL.TLabel",
                                  text="The Shielding of:")
        self.reshield.grid(sticky="w")
        self.d[f"run {t}"] = True

    def occupation(self, t):
        def destroy_widget(widget_key):
            if self.d.get(widget_key) is not None:
                self.d[widget_key].destroy()
        # Determine the widget key for the entry and location
        occupentry_key = f"occupentry {t}"
        sellocation_key = f"sellocation {t}"
        area_key = f"area {t}"
        frame_key = f"frame_1 {t}"
        # Handle occupancy "Write occupation Factor"
        if self.d.get(f"vraoccup {t}").get() == 1:
            destroy_widget(sellocation_key)
            destroy_widget(occupentry_key)
            self.d[f"vselocation {t}"] = StringVar()
            self.d[occupentry_key] = ttk.Entry(master=self.d[frame_key], width=10)
            area_value = self.d[area_key].get()
            default_value = {"Controlled Area": str(1), "Uncontrolled Area": str(1 / 16),
                "Supervised Area": str(1 / 4)}.get(area_value, "")
            self.d[occupentry_key].insert(0, default_value)
            self.d[occupentry_key].grid(row=2, column=1, pady=5, padx=5)
        # Handle occupancy "From NCRP 147"
        elif self.d.get(f"vraoccup {t}").get() == 2:
            destroy_widget(occupentry_key)
            destroy_widget(sellocation_key)
            self.d[f"vselocation {t}"] = StringVar()
            options = {"Controlled Area": ["Administrative or clerical offices", "Laboratories",
                "Pharmacies and other work areas fully occupied by an individual", "Receptionist areas",
                "Attended waiting rooms", "Children’s indoor play areas", "Adjacent x-ray rooms", "Film reading areas",
                "Nurse’s stations", "X-ray control rooms", "Rooms used for patient examinations and treatments"],
                "Uncontrolled Area": ["Public toilets", "Unattended vending areas", "Storage rooms",
                    "Outdoor areas with seating", "Unattended waiting rooms", "Patient holding areas",
                    "Outdoor areas with only transient pedestrian or vehicular traffic", "Unattended parking lots",
                    "Vehicular drop off areas (unattended)", "Attics", "Stairways", "Unattended elevators",
                    "Janitor’s closets"],
                "Supervised Area": ["Corridors", "Patient rooms", "Employee lounges", "Staff restrooms",
                    "Corridor doors"]}.get(self.d[area_key].get(), [])
            self.d[sellocation_key] = ttk.OptionMenu(self.d[frame_key], self.d[f"vselocation {t}"], "Select Location",
                *options)
            self.d[sellocation_key].config(width=14)
            self.d[sellocation_key].grid(row=3, column=1, columnspan=2, pady=5, padx=5, sticky="w")
        # Handle dikeent based on area type
        area_dikeent_values = {"Controlled Area": str(0.2), "Uncontrolled Area": str(0.006),
            "Supervised Area": str(0.06)}
        dikeent_value = area_dikeent_values.get(self.d[area_key].get(), "")
        if dikeent_value:
            destroy_widget(f"dikeent {t}")
            self.d[f"dikeent {t}"] = ttk.Entry(master=self.d[frame_key], width=10)
            self.d[f"dikeent {t}"].insert(0, dikeent_value)
            self.d[f"dikeent {t}"].grid(row=4, column=1, pady=5, padx=5, sticky="w")
    def workload(self, t):
        def destroy_widget(widget_key):
            if self.d.get(widget_key) is not None:
                self.d[widget_key].destroy()
        # Widget keys
        frame_key = f"frame_1 {t}"
        worentry_key = f"worentry {t}"
        numpapwe_key = f"numpapwe {t}"
        vrawork_key = f"vrawork {t}"
        # Get the value for workload type
        workload_type = self.d.get(vrawork_key).get()
        # Handle workload "Total workload"
        if workload_type == 1:
            destroy_widget(numpapwe_key)
            destroy_widget(worentry_key)
            self.d[worentry_key] = ttk.Entry(master=self.d[frame_key], width=10)
            self.d[worentry_key].grid(row=1, column=2, pady=5, padx=5)
            tip(self.d[worentry_key], "workload_total")
        # Handle workload "Number of Patients"
        elif workload_type == 2:
            destroy_widget(worentry_key)
            destroy_widget(numpapwe_key)
            self.d[numpapwe_key] = ttk.Entry(master=self.d[frame_key], width=10)
            self.d[numpapwe_key].grid(row=1, column=4, pady=5, padx=5, sticky="w")
            tip(self.d[numpapwe_key], "workload_patients")
    def combination(self, t):
        def destroy_widget(widget_key):
            if self.d.get(widget_key) is not None:
                self.d[widget_key].destroy()
        # Widget keys
        frame_key = f"frame_1 {t}"
        varcompb_key = f"varcompb {t}"
        spincom_key = f"spincom {t}"
        combutton_key = f"combutton {t}"
        commatter_key = f"commatter {t}"
        combarr_key_prefix = f"combarr {t}"
        # Check if combining is enabled
        if self.d.get(varcompb_key).get() == 1:
            # Initialize variables and widgets for combining
            self.d[f"vnumbar {t}"] = IntVar(value=2)
            self.d[spincom_key] = ttk.Spinbox(master=self.d[frame_key], from_=2, to=100, width=5,
            textvariable=self.d[f"vnumbar {t}"],command=lambda e=self.d[f"x {t}"],
            nr=self.d[f"nr {t}"]: self.numbcom(e, nr,t))
            self.d[spincom_key].grid(row=10, column=1, padx=10, pady=10, sticky="w")

            self.numbcom(self.d[f"x {t}"], self.d[f"nr {t}"], t)

            self.d[combutton_key] = ttk.Button(master=self.d[frame_key], text="Combine",
                command=lambda e=self.d[f"x {t}"], nr=self.d[f"nr {t}"],
                               b=self.d[f"vnumbar {t}"].get(): self.calcom(e,nr,b,t))
            self.d[combutton_key].grid(row=11, column=1, padx=10, pady=10, sticky="w")
            # Material selection
            materials = ("Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass", "Wood")
            self.d[f"vcommater {t}"] = StringVar()
            self.d[commatter_key] = ttk.OptionMenu(self.d[frame_key], self.d[f"vcommater {t}"], "Select Material",
                *materials)
            self.d[commatter_key].grid(row=11, column=0, padx=10, pady=10, sticky="w")

        elif self.d.get(varcompb_key).get() == 0:
            # Destroy combined material widgets
            combarr_num = self.d.get(f"comnum {t}", 2)
            for i in range(1, combarr_num + 1):
                destroy_widget(f"{combarr_key_prefix}{i}")
            destroy_widget(spincom_key)
            destroy_widget(combutton_key)
            destroy_widget(commatter_key)
            self.d[f"comnum {t}"] = 0
    def numbcom(self, e, nr, t):
        # Access frequently used keys
        num_com_key = f"comnum {t}"
        num_bar_key = f"vnumbar {t}"
        frame_key = f"frame_1 {t}"
        # Initialize values for comnum and vnumbar if not set yet
        if num_com_key not in self.d:
            self.d[num_com_key] = 0
        # Increase the number of barriers
        if self.d[num_com_key] <= self.d[num_bar_key].get():
            while self.d[num_com_key] < self.d[num_bar_key].get():
                self.d[num_com_key] += 1
                barrier_num = self.d[num_com_key]
                barrier_key = f"vcombar {nr}{barrier_num}"
                combarr_key = f"combarr {t}{barrier_num}"
                self.d[barrier_key] = StringVar()
                self.d[combarr_key] = ttk.OptionMenu(self.d[frame_key], self.d[barrier_key], "Select Barrier",
                                                     *self.barr)
                self.d[combarr_key].grid(row=12 + barrier_num)
        # Decrease the number of barriers
        elif self.d[num_com_key] > self.d[num_bar_key].get() :
            while self.d[num_com_key] > self.d[num_bar_key].get():
                barrier_num = self.d[num_com_key]
                combarr_key = f"combarr {t}{barrier_num}"
                if self.d.get(combarr_key):
                    self.d[combarr_key].destroy()
                self.d[num_com_key] -= 1
    def exp_dep(self, dep):
        # Full report of every designed room of this department
        info = self.departments[dep]
        name = info["name"].get().strip() or f"Department {dep}"
        self.export_report(name, [t for t in info["rooms"] if self.d[f"run {t}"]])
    def closedeproom(self, t):
        # Hide the room and its results; the Design button shows them again with all inputs kept
        info = self.departments[self.d[f"dep {t}"]]
        info["rooms_note"].hide(self.d[f"newroomf {t}"])
        info["results_note"].hide(self.d[f"resframe {t}"])