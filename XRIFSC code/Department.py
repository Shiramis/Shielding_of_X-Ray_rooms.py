import os
import tkinter
from tkinter import *
from tkinter import ttk
import xlsxwriter
import platform

class ddepartment():
    # ============creating def for Deparment notebook===================================
    def creatdep(self):
        # Cleanup previous widgets
        self.depbutton.destroy()
        self.roombutton.destroy()
        self.CTbutton.destroy()
        self.quickbutton.destroy()
        self.chooseCal.destroy()
        # Initialize the department notebook if it hasn't been initialized
        if self.depnote is None:
            self.depnote = ttk.Notebook(self.new_main_Frame, style="AL.TNotebook")
            self.depnote.configure(width=980, height=728)
            self.depnote.grid(row=0, sticky="w")
            # Bind the tab change event to sync with results
            self.depnote.bind("<<NotebookTabChanged>>", self.sync_results_tab)

        # Create and configure the department frame and canvas
        self.depframe = ttk.Frame(self.depnote)
        self.depframe.pack(fill=BOTH, expand=1)
        self.depnote.add(self.depframe, text="Department")

        self.depcanv = Canvas(self.depframe)
        self.depcanv.pack(side=LEFT, fill=BOTH, expand=1)
        self.scrolldep = ttk.Scrollbar(self.depframe, orient=VERTICAL, command=self.depcanv.yview)
        self.scrolldep.pack(side=RIGHT, fill=Y)
        self.depcanv.configure(yscrollcommand=self.scrolldep.set, bg="#f7faf9")

        # Create and configure the rooms frame inside the department canvas
        self.roomsframe = ttk.Frame(self.depcanv)
        self.roomsframe.bind('<Configure>', lambda e: self.depcanv.configure(scrollregion=self.depcanv.bbox("all")))
        self.depcanv.create_window((0, 0), window=self.roomsframe, anchor="nw")

        # Add widgets to the rooms frame
        self.label_rooms = ttk.Label(master=self.roomsframe, style="BL.TLabel", text="Rooms of Department")
        self.label_rooms.grid(row=0, column=0, sticky="nswe")
        self.numrlab = ttk.Label(master=self.roomsframe, style="AL.TLabel", text="Number of Rooms:")
        self.numrlab.grid(row=1, column=0, pady=10, padx=10, sticky="w")
        self.numrooms = IntVar(value=1)
        self.num_rooms = ttk.Spinbox(master=self.roomsframe, from_=0, to=10000, increment=1,
                                     textvariable=self.numrooms, width=5, command=self.createrooms)
        self.num_rooms.grid(row=1, column=1, pady=10, padx=20, sticky="e")

        # Call to create rooms
        self.createrooms()
    def createrooms(self):
        # Add rooms if current index is less than the number of rooms
        if self.i < self.numrooms.get():
            while self.i < self.numrooms.get():
                self.i += 1
                # Create and place the room description label
                self.d[f"labelname {self.i}"] = ttk.Label(master=self.roomsframe, style="AL.TLabel",
                    text=f"Room Description {self.i}:")
                self.d[f"labelname {self.i}"].grid(row=2 + self.i, column=0, padx=10, pady=10, sticky="w")
                # Create and place the room name entry field
                self.d[f"name_room {self.i}"] = ttk.Entry(master=self.roomsframe)
                self.d[f"name_room {self.i}"].grid(row=2 + self.i, column=1, sticky="w")
                # Create and place the room selection combobox
                self.d[f"vselroom {self.i}"] = StringVar()
                self.d[f"selroom {self.i}"] = ttk.Combobox(master=self.roomsframe,
                    textvariable=self.d[f"vselroom {self.i}"], values=["X-Ray room", "CT Room"], state="readonly")
                self.d[f"selroom {self.i}"].grid(row=2 + self.i, column=2, pady=10, padx=20, sticky="w")
                self.d[f"selroom {self.i}"].set("Shield room")
                # Selections for more methods
                """
                self.method = ("BIR 2012", "NCRP 147")
                self.d[f"vmethod {self.i}"] = StringVar()
                self.d[f"method {self.i}"] = ttk.OptionMenu(
                    self.roomsframe,
                    self.d[f"vmethod {self.i}"],
                    "Select Method",
                    *self.method
                )
                self.d[f"method {self.i}"].grid(row=2 + self.i, column=3, padx=10, pady=10, sticky="w")
                """
                # Create and place the design button
                self.d[f"run {self.i}"] = False  # Run every room only once
                self.d[f"crroomb {self.i}"] = ttk.Button(master=self.roomsframe, text="Design",
                    command=lambda t=self.i: self.desroom(t))
                self.d[f"crroomb {self.i}"].grid(row=2 + self.i, column=4, padx=10, pady=10, sticky="w")
                # Create and place the export button (only once for all rooms)
                self.exp_but = ttk.Button(master=self.roomsframe, text="Export to Excel",
                    command=lambda t=self.i: self.exp_dep(t))
                self.exp_but.grid(row=1, column=2, pady=10, padx=10, sticky="w")
                # Initialize values for the room result frame
                self.d[f"resframe {self.i}"] = None
        # Remove rooms if current index is greater than the number of rooms
        else:
            while self.i > self.numrooms.get():
                # Destroy room components for the current room
                self.d[f"labelname {self.i}"].destroy()
                self.d[f"name_room {self.i}"].destroy()
                self.d[f"selroom {self.i}"].destroy()
                self.d[f"crroomb {self.i}"].destroy()
                # Destroy method selection if uncommented
                # self.d[f"method {self.i}"].destroy()
                # If room has been run, destroy additional components
                if self.d[f"run {self.i}"]:
                    self.d[f"newroomf {self.i}"].destroy()
                    self.d[f"resframe {self.i}"].destroy()
                    # If only one room exists, destroy the result note
                    if self.i == 1:
                        self.resnote.destroy()
                # Decrease room index
                self.i -= 1
    def desroom(self, t):
        room_type = self.d[f"vselroom {t}"].get()
        if room_type != "Shield room":
            if not self.d[f"run {t}"]:
                # Initialize the result notebook if needed
                if self.i == 1 or (self.i > 0 and self.resnote is None):
                    self.resnote = ttk.Notebook(self.new_main_Frame, style="AL.TNotebook")
                    self.resnote.grid(row=0, column=1, sticky="w")
                    self.resnote.configure(width=545, height=728)
                # Initialize room-specific values
                self.d[f"selxroom {t}"] = None
                self.d[f"numpapwl {t}"] = None
                self.d[f"numpapwe {t}"] = None
                self.d[f"sellocation {t}"] = None
                # Create the room frame inside the notebook
                self.d[f"newroomf {t}"] = ttk.Frame(self.depnote)
                self.d[f"newroomf {t}"].pack()
                self.depnote.add(self.d[f"newroomf {t}"], text=self.d[f"name_room {t}"].get())
                self.depnote.grid()
                self.depnote.add(self.d[f"newroomf {t}"], text=self.d[f"name_room {t}"].get())
                self.depnote.grid()

                # Set up scrollbars for the canvas
                self.roomcanv = Canvas(self.d[f"newroomf {t}"])
                self.xscrollroom = ttk.Scrollbar(self.d[f"newroomf {t}"], orient=HORIZONTAL,
                                                 command=self.roomcanv.xview)
                self.xscrollroom.pack(side=BOTTOM, fill=X)

                self.yscrollroom = ttk.Scrollbar(self.d[f"newroomf {t}"], orient=VERTICAL, command=self.roomcanv.yview)
                self.yscrollroom.pack(side=RIGHT, fill=Y)

                self.roomcanv.configure(yscrollcommand=self.yscrollroom.set, xscrollcommand=self.xscrollroom.set,
                                        bg="#f7faf9")
                self.roomcanv.pack(side=LEFT, fill=BOTH, expand=1)

                # Create frame inside the canvas
                self.d[f"frame_1 {t}"] = ttk.Frame(self.roomcanv)
                self.d[f"frame_1 {t}"].bind('<Configure>',
                                            lambda e: self.roomcanv.configure(scrollregion=self.roomcanv.bbox("all")))
                self.roomcanv.create_window((0, 0), window=self.d[f"frame_1 {t}"], anchor="nw")

                # Bind mouse wheel scrolling
                def on_vertical_scroll(event):
                    system = platform.system()
                    if system == "Windows" or system == "Linux":
                        # For Windows/Linux, use event.delta / 120 and invert the scroll direction
                        self.roomcanv.yview_scroll(int(-1 * (event.delta / 120)), "units")
                    elif system == "Darwin":  # macOS
                        # For macOS, event.delta is in reverse, so just use it directly
                        self.roomcanv.yview_scroll(int(event.delta), "units")

                def on_horizontal_scroll(event):
                    system = platform.system()
                    if system == "Windows" or system == "Linux":
                        # For Windows/Linux, use event.delta / 120 and invert the scroll direction
                        self.roomcanv.xview_scroll(int(-1 * (event.delta / 120)), "units")
                    elif system == "Darwin":  # macOS
                        # For macOS, event.delta is in reverse, so just use it directly
                        self.roomcanv.xview_scroll(int(event.delta), "units")

                # Bind mouse scroll for vertical and horizontal scrolling
                self.roomcanv.bind_all("<MouseWheel>", on_vertical_scroll)  # For vertical scrolling (Windows/Linux)
                self.roomcanv.bind_all("<Shift-MouseWheel>",
                                       on_horizontal_scroll)  # Horizontal scrolling with Shift key (Windows/Linux)

                # For macOS, different event binding
                self.roomcanv.bind_all("<Button-4>",
                                       lambda event: self.roomcanv.yview_scroll(-1, "units"))  # macOS Scroll up
                self.roomcanv.bind_all("<Button-5>",
                                       lambda event: self.roomcanv.yview_scroll(1, "units"))  # macOS Scroll down
                # Initialize some room values
                self.d[f"x {t}"] = 0
                self.d[f"y {t}"] = 0
                self.d[f"nr {t}"] = self.d[f"labelname {t}"].cget("text")
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
                # Call the barriers method
                self.barriers(t)
                # Add close button for room frame
                self.closBut = ttk.Button(self.d[f"newroomf {t}"], text="X", width=4,
                                          command=lambda: self.closedeproom(t))
                self.closBut.pack()
                # If not a CT room, add "Combine Barriers" checkbox
                """if room_type != "CT Room":
                    self.d[f"varcompb {t}"] = IntVar(value=0)
                    self.d[f"compb {t}"] = ttk.Checkbutton(self.d[f"frame_1 {t}"], text="Combine Barriers as one",
                                                           variable=self.d[f"varcompb {t}"], onvalue=1, offvalue=0,
                                                           command=lambda: self.combination(t))
                    self.d[f"compb {t}"].grid(row=10, column=0, pady=5, padx=5, sticky="w")"""
                # Setup for X-Ray Room type
                if room_type == "X-Ray room":
                    self.setup_xray_room(t)
                # Setup for CT Room type
                elif room_type == "CT Room":
                    self.setup_ct_room(t)
                # Setup the results tab
                self.setup_results(t)
            # Select the current room and results in the notebook
            self.depnote.select(self.d[f"newroomf {t}"])
            self.resnote.select(self.d[f"resframe {t}"])
    def setup_xray_room(self, t):
        # Add workload and X-ray room options
        self.title_workload = ttk.Label(self.d[f"frame_1 {t}"], style="BL.TLabel", text="Workload:")
        self.title_workload.grid(row=1, column=0, pady=5, padx=5, sticky="w")
        # Additional workload entry options
        self.d[f"worentry {t}"] = None
        self.d[f"vrawork {t}"] = IntVar(value=0)
        self.raworkl = ttk.Radiobutton(self.d[f"frame_1 {t}"], text="Write total\nWorkload (mA min/week):",
                                       variable=self.d[f"vrawork {t}"], value=1, command=lambda: self.workload(t))
        self.raworkl.grid(row=1, column=1, pady=5, padx=5, sticky="w")
        self.ranumb = ttk.Radiobutton(self.d[f"frame_1 {t}"], text="The Number of\nPatients per week:",
                                      variable=self.d[f"vrawork {t}"], value=2, command=lambda: self.workload(t))
        self.ranumb.grid(row=1, column=3, pady=5, padx=5, sticky="w")
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
    def setup_results(self, t):
        # Add result frame for each room
        self.d[f"resframe {t}"] = ttk.Frame(self.resnote)
        self.d[f"resframe {t}"].pack()
        self.resnote.add(self.d[f"resframe {t}"], text=f"Results of {self.d[f'name_room {t}'].get()}")
        # ==========Results==============
        if self.d[f"resframe {t}"] is None:
            self.d[f"resframe {t}"] = ttk.Frame(self.resnote)
            self.d[f"resframe {t}"].pack()

        self.resnote.add(self.d[f"resframe {t}"], text=f"Results of {self.d[f'name_room {t}'].get()}")

        # ======Results scrollbar=========
        self.rescanv = Canvas(self.d[f"resframe {t}"])

        self.scrollres = ttk.Scrollbar(self.d[f"resframe {t}"], orient=VERTICAL, command=self.rescanv.yview)
        self.scrollres.pack(side=RIGHT, fill=Y)

        self.xscrollres = ttk.Scrollbar(self.d[f"resframe {t}"], orient=HORIZONTAL, command=self.rescanv.xview)
        self.xscrollres.pack(side=BOTTOM, fill=X)

        self.rescanv.configure(yscrollcommand=self.scrollres.set, xscrollcommand=self.xscrollres.set, bg="#f7faf9")
        self.rescanv.pack(side=LEFT, fill=BOTH, expand=1)

        # =========Results tab===========================
        self.d[f"resultframe {t}{self.d[f'nr {t}']}"] = ttk.Frame(self.rescanv)
        self.d[f"resultframe {t}{self.d[f'nr {t}']}"].bind('<Configure>', lambda e: self.rescanv.configure(
            scrollregion=self.rescanv.bbox("all")))
        self.rescanv.create_window((0, 0), window=self.d[f"resultframe {t}{self.d[f'nr {t}']}"], anchor="nw")

        self.reshield = ttk.Label(self.d[f"resultframe {t}{self.d[f'nr {t}']}"], style="BL.TLabel",
                                  text="The Shielding of:")
        self.reshield.grid(sticky="w")
        self.d[f"run {t}"] = True
        self.depnote.select(self.d[f"newroomf {t}"])
        self.resnote.select(self.d[f"resframe {t}"])
    def sync_results_tab(self, event):
        selected_room_tab = self.depnote.index(self.depnote.select())
        result_frame_key = f"resframe {selected_room_tab}"
        if result_frame_key in self.d:
            self.resnote.select(self.d[result_frame_key])
        else:
            pass

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
        # Handle workload "Number of Patients"
        elif workload_type == 2:
            destroy_widget(worentry_key)
            destroy_widget(numpapwe_key)
            self.d[numpapwe_key] = ttk.Entry(master=self.d[frame_key], width=10)
            self.d[numpapwe_key].grid(row=1, column=4, pady=5, padx=5, sticky="w")
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
    def exp_dep(self, t):
        import pandas as pd
        import os
        # Prepare data for export
        for b in range(1, t + 1):
            room_name = self.d[f"labelname {b}"].cget("text")
            for a in range(1, self.d[f"vnumwall {b}"].get() + 1):
                key = f"lab_bar {a} {room_name}"
                self.wa[self.barn.get(key, '')] = [str(self.xlmat.get(f"thic {a} {i} {room_name}", '')) for i in
                    range(1, 7)]
            self.d[f"room_data {b}"] = pd.DataFrame(data=self.wa,
                index=["Lead (mm)", "Concrete (mm)", "Gypsum Wallboard (mm)", "Steel (mm)", "Plate Glass (mm)",
                       "Wood (mm)"])
        user_home = os.path.expanduser('~')  # Get user's home directory
        excel_file_path = os.path.join(user_home, 'Department.xlsx')
        # Export data to Excel
        try:
            with pd.ExcelWriter(excel_file_path, engine='xlsxwriter',
                                engine_kwargs={'options': {'strings_to_numbers': True}}) as writer:
                for b in range(1, t + 1):
                    sheet_name = self.d[f"name_room {b}"].get()
                    self.d[f"room_data {b}"].to_excel(writer, sheet_name=sheet_name)
        except Exception as e:
            print(f"An error occurred while saving the Excel file: {e}")
        # Open the file
        os.system(f'start {excel_file_path}')  # Use 'start' for Windows, adjust for other OS if needed
    def closedeproom(self, t):
        keys_to_destroy = [f"newroomf {t}", f"labelname {t}", f"name_room {t}", f"selroom {t}", f"crroomb {t}",
            f"resframe {t}", f"resultframe {t}{self.d.get(f'nr {t}', '')}"]
        for key in keys_to_destroy:
            if self.d.get(key):
                self.d[key].destroy()