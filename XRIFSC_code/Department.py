import os
from tkinter import *
from tkinter import ttk
import platform
import pandas as pd

class ddepartment():
    # ============creating def for Deparment notebook===================================
    def creatdep(self):
        # Cleanup previous widgets
        self.depbutton.destroy()
        self.roombutton.destroy()
        self.CTbutton.destroy()
        #self.quickbutton.destroy()
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
        self.var["numrooms"] = IntVar(value=1)
        self.num_rooms = ttk.Spinbox(master=self.roomsframe, from_=0, to=10000, increment=1,
                                     textvariable=self.var["numrooms"], width=5, command=self.createrooms)
        self.num_rooms.grid(row=1, column=1, pady=10, padx=20, sticky="e")

        # Call to create rooms
        self.createrooms()

    def createrooms(self):
        # Add rooms if current index is less than the number of rooms
        if self.i < self.var["numrooms"].get():
            while self.i < self.var["numrooms"].get():
                self.i += 1
                # Create and place the room description label
                self.d[f"labelname {self.i}"] = ttk.Label(master=self.roomsframe, style="AL.TLabel",
                    text=f"Room Description {self.i}:")
                self.d[f"labelname {self.i}"].grid(row=2 + self.i, column=0, padx=10, pady=10, sticky="w")
                # Create and place the room name entry field
                self.d[f"name_room {self.i}"] = ttk.Entry(master=self.roomsframe)
                self.d[f"name_room {self.i}"].grid(row=2 + self.i, column=1, sticky="w")
                # Create and place the room selection combobox
                self.var[f"vselroom {self.i}"] = StringVar()
                self.d[f"selroom {self.i}"] = ttk.Combobox(master=self.roomsframe,
                    textvariable=self.var[f"vselroom {self.i}"], values=["X-Ray room", "CT Room"], state="readonly")
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
            while self.i > self.var["numrooms"].get():
                # Destroy room components for the current room
                self.destroy_widgets([f"labelname {self.i}"])
                self.destroy_widgets([f"name_room {self.i}"])
                self.destroy_widgets([f"selroom {self.i}"])
                self.destroy_widgets([f"crroomb {self.i}"])
                # Destroy method selection if uncommented
                # self.d[f"method {self.i}"].destroy()
                # If room has been run, destroy additional components
                if self.d[f"run {self.i}"]:
                    self.destroy_widgets([f"newroomf {self.i}"])
                    self.destroy_widgets([f"resframe {self.i}"])
                    # If only one room exists, destroy the result note
                    if self.i == 1:
                        self.resnote.destroy()
                # Decrease room index
                self.i -= 1

    def desroom(self, t):
        room_type = self.var[f"vselroom {t}"].get()
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
                self.d[f"roomcanv {t}"] = Canvas(self.d[f"newroomf {t}"])
                self.d[f"xscrollroom {t}"] = ttk.Scrollbar(self.d[f"newroomf {t}"], orient=HORIZONTAL,
                                                           command=self.d[f"roomcanv {t}"].xview)
                self.d[f"xscrollroom {t}"].pack(side=BOTTOM, fill=X)

                self.d[f"yscrollroom {t}"] = ttk.Scrollbar(self.d[f"newroomf {t}"], orient=VERTICAL,
                                                           command=self.d[f"roomcanv {t}"].yview)
                self.d[f"yscrollroom {t}"].pack(side=RIGHT, fill=Y)

                self.d[f"roomcanv {t}"].configure(yscrollcommand=self.d[f"yscrollroom {t}"].set,
                                                  xscrollcommand=self.d[f"xscrollroom {t}"].set, bg="#f7faf9")
                self.d[f"roomcanv {t}"].pack(side=LEFT, fill=BOTH, expand=1)

                # Create frame inside the canvas
                self.d[f"frame_1 {t}"] = ttk.Frame(self.d[f"roomcanv {t}"])
                self.d[f"frame_1 {t}"].bind('<Configure>', lambda e: self.d[f"roomcanv {t}"].configure(
                    scrollregion=self.d[f"roomcanv {t}"].bbox("all")))
                self.d[f"roomcanv {t}"].create_window((0, 0), window=self.d[f"frame_1 {t}"], anchor="nw")

                # Scroll functions (centralized logic)
                def on_vertical_scroll(event):
                    system = platform.system()
                    if system in ["Windows", "Linux"]:
                        self.d[f"roomcanv {t}"].yview_scroll(int(-1 * (event.delta / 120)), "units")
                    elif system == "Darwin":  # macOS
                        self.d[f"roomcanv {t}"].yview_scroll(int(event.delta), "units")

                def on_horizontal_scroll(event):
                    system = platform.system()
                    if system in ["Windows", "Linux"]:
                        self.d[f"roomcanv {t}"].xview_scroll(int(-1 * (event.delta / 120)), "units")
                    elif system == "Darwin":  # macOS
                        self.d[f"roomcanv {t}"].xview_scroll(int(event.delta), "units")

                # Bind mouse scroll for vertical and horizontal scrolling (platform-specific)
                system = platform.system()

                if system in ["Windows", "Linux"]:
                    self.d[f"roomcanv {t}"].bind("<MouseWheel>", on_vertical_scroll)  # Vertical scrolling
                    self.d[f"roomcanv {t}"].bind("<Shift-MouseWheel>",
                                                 on_horizontal_scroll)  # Horizontal scrolling with Shift key
                elif system == "Darwin":  # macOS
                    self.d[f"roomcanv {t}"].bind("<Button-4>", lambda event: self.d[f"roomcanv {t}"].yview_scroll(-1,
                                                                                                                  "units"))  # Scroll up
                    self.d[f"roomcanv {t}"].bind("<Button-5>", lambda event: self.d[f"roomcanv {t}"].yview_scroll(1,
                                                                                                                  "units"))  # Scroll down
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
                self.var[f"vnumwall {t}"] = IntVar(value=7)
                self.d[f"numwall {t}"] = ttk.Spinbox(self.d[f"frame_1 {t}"], from_=7, to=50, width=5,
                                                     textvariable=self.var[f"vnumwall {t}"],
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
        self.var[f"vrawork {t}"] = IntVar(value=0)
        self.raworkl = ttk.Radiobutton(self.d[f"frame_1 {t}"], text="Write total\nWorkload (mA∙min∙week\u207B\u00b9):",
                                       variable=self.var[f"vrawork {t}"], value=1, command=lambda: self.workload(t))
        self.raworkl.grid(row=1, column=1, pady=5, padx=5, sticky="w")
        self.ranumb = ttk.Radiobutton(self.d[f"frame_1 {t}"], text="The Number of\nPatients per week:",
                                      variable=self.var[f"vrawork {t}"], value=2, command=lambda: self.workload(t))
        self.ranumb.grid(row=1, column=3, pady=5, padx=5, sticky="w")

    def setup_ct_room(self, t):
        # CT room setup with body/head procedures, kVp, and DLP entries
        self.bp_label = ttk.Label(self.d[f"frame_1 {t}"], text='Body Procedures (weekly):')
        self.bp_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.var[f"bp_var {t}"] = IntVar()
        self.bp_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.var[f"bp_var {t}"], width=10)
        self.bp_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        self.hp_label = ttk.Label(self.d[f"frame_1 {t}"], text='Head Procedures (weekly):')
        self.hp_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.var[f"hp_var {t}"] = IntVar()
        self.hp_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.var[f"hp_var {t}"], width=10)
        self.hp_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        self.kvp_label = ttk.Label(self.d[f"frame_1 {t}"], text='Give kVp:')
        self.kvp_label.grid(row=6, column=0, padx=10, pady=10, sticky="w")
        self.var[f"kvp_var {t}"] = IntVar()
        self.kvp_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.var[f"kvp_var {t}"], width=10)
        self.kvp_entry.grid(row=6, column=1, padx=10, pady=10, sticky="w")

        self.dlpb_label = ttk.Label(self.d[f"frame_1 {t}"], text='Give DLP/body procedure:')
        self.dlpb_label.grid(row=7, column=0, padx=10, pady=10, sticky="w")
        self.var[f"dlpb_var {t}"] = IntVar()
        self.dlpb_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.var[f"dlpb_var {t}"], width=10)
        self.dlpb_entry.grid(row=7, column=1, padx=10, pady=10, sticky="w")

        self.dlph_label = ttk.Label(self.d[f"frame_1 {t}"], text='Give DLP/head procedure:')
        self.dlph_label.grid(row=8, column=0, padx=10, pady=10, sticky="w")
        self.var[f"dlph_var {t}"] = IntVar()
        self.dlph_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.var[f"dlph_var {t}"], width=10)
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

    def workload(self, t):
        # Widget keys
        frame_key = f"frame_1 {t}"
        worentry_key = f"worentry {t}"
        numpapwe_key = f"numpapwe {t}"
        vrawork_key = f"vrawork {t}"
        # Get the value for workload type
        workload_type = self.var.get(vrawork_key).get()
        # Handle workload "Total workload"
        if workload_type == 1:
            self.destroy_widgets([numpapwe_key])
            self.destroy_widgets([worentry_key])
            self.d[worentry_key] = ttk.Entry(master=self.d[frame_key], width=10)
            self.d[worentry_key].grid(row=1, column=2, pady=5, padx=5)
        # Handle workload "Number of Patients"
        elif workload_type == 2:
            self.destroy_widgets([worentry_key])
            self.destroy_widgets([numpapwe_key])
            self.d[numpapwe_key] = ttk.Entry(master=self.d[frame_key], width=10)
            self.d[numpapwe_key].grid(row=1, column=4, pady=5, padx=5, sticky="w")

    def combination(self, t):
        # Widget keys
        frame_key = f"frame_1 {t}"
        varcompb_key = f"varcompb {t}"
        spincom_key = f"spincom {t}"
        combutton_key = f"combutton {t}"
        commatter_key = f"commatter {t}"
        combarr_key_prefix = f"combarr {t}"
        # Check if combining is enabled
        if self.var.get(varcompb_key).get() == 1:
            # Initialize variables and widgets for combining
            self.var[f"vnumbar {t}"] = IntVar(value=2)
            self.d[spincom_key] = ttk.Spinbox(master=self.d[frame_key], from_=2, to=100, width=5,
            textvariable=self.var[f"vnumbar {t}"],command=lambda e=self.d[f"x {t}"],
            nr=self.d[f"nr {t}"]: self.numbcom(e, nr,t))
            self.d[spincom_key].grid(row=10, column=1, padx=10, pady=10, sticky="w")

            self.numbcom(self.d[f"x {t}"], self.d[f"nr {t}"], t)

            self.d[combutton_key] = ttk.Button(master=self.d[frame_key], text="Combine",
                command=lambda e=self.d[f"x {t}"], nr=self.d[f"nr {t}"],
                               b=self.d[f"vnumbar {t}"].get(): self.calcom(e,nr,b,t))
            self.d[combutton_key].grid(row=11, column=1, padx=10, pady=10, sticky="w")
            # Material selection
            materials = ("Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass", "Wood")
            self.var[f"vcommater {t}"] = StringVar()
            self.d[commatter_key] = ttk.OptionMenu(self.d[frame_key], self.var[f"vcommater {t}"], "Select Material",
                *materials)
            self.d[commatter_key].grid(row=11, column=0, padx=10, pady=10, sticky="w")

        elif self.var.get(varcompb_key).get() == 0:
            # Destroy combined material widgets
            combarr_num = self.d.get(f"comnum {t}", 2)
            for i in range(1, combarr_num + 1):
                self.destroy_widgets(f"{combarr_key_prefix}{i}")
            self.destroy_widgets(spincom_key)
            self.destroy_widgets(combutton_key)
            self.destroy_widgets(commatter_key)
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
                self.var[barrier_key] = StringVar()
                self.d[combarr_key] = ttk.OptionMenu(self.d[frame_key], self.var[barrier_key], "Select Barrier",
                                                     *self.barr)
                self.d[combarr_key].grid(row=12 + barrier_num)
        # Decrease the number of barriers
        elif self.d[num_com_key] > self.d[num_bar_key].get() :
            while self.d[num_com_key] > self.d[num_bar_key].get():
                barrier_num = self.d[num_com_key]
                combarr_key = f"combarr {t}{barrier_num}"
                self.destroy_widgets([combarr_key])
                self.d[num_com_key] -= 1

    def exp_dep(self, t):
        # Prepare data for export
        for b in range(1, t + 1):
            self.d[f"room_data {b}"] = pd.DataFrame(data=self.rdata[f'{self.d[f"nr {b}"]}'])
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
        self.destroy_widgets(keys_to_destroy)

    def destroy_widgets(self, keys):
        """Utility function to destroy a list of widgets if they exist."""
        for key in keys:
            if key in self.d and self.d[key] is not None:
                self.d[key].destroy()
                del self.d[key]
            elif key in self.var and self.var[key] is not None:
                del self.var[key]