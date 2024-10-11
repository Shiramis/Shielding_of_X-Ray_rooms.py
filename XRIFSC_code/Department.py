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
                self.ent[f"name_room {self.i}"] = ttk.Entry(master=self.roomsframe)
                self.ent[f"name_room {self.i}"].grid(row=2 + self.i, column=1, sticky="w")
                # Create and place the room selection combobox
                self.var[f"vselroom {self.i}"] = StringVar()
                self.d[f"selroom {self.i}"] = ttk.Combobox(master=self.roomsframe,
                    textvariable=self.var[f"vselroom {self.i}"], values=["X-Ray Room", "CT Room"], state="readonly")
                self.d[f"selroom {self.i}"].grid(row=2 + self.i, column=2, pady=10, padx=20, sticky="w")
                self.d[f"selroom {self.i}"].set("Shield room")
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
                self.destroy_widgets([f"labelname {self.i}", f"name_room {self.i}", f"selroom {self.i}", f"crroomb {self.i}"])
                if self.d[f"run {self.i}"]:
                    self.destroy_widgets([f"newroomf {self.i}", f"resframe {self.i}"])
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
                # Create the room frame inside the notebook
                self.d[f"newroomf {t}"] = ttk.Frame(self.depnote)
                self.d[f"newroomf {t}"].pack(fill=BOTH, expand=1)
                self.depnote.add(self.d[f"newroomf {t}"], text=self.ent[f"name_room {t}"].get())

                # Set up scrollbars for the canvas
                self.d[f"roomcanv {t}"] = Canvas(self.d[f"newroomf {t}"], bg="#f7faf9")
                self.d[f"xscrollroom {t}"] = ttk.Scrollbar(self.d[f"newroomf {t}"], orient=HORIZONTAL,
                                                           command=self.d[f"roomcanv {t}"].xview)
                self.d[f"xscrollroom {t}"].pack(side=BOTTOM, fill=X)
                self.d[f"yscrollroom {t}"] = ttk.Scrollbar(self.d[f"newroomf {t}"], orient=VERTICAL,
                                                           command=self.d[f"roomcanv {t}"].yview)
                self.d[f"yscrollroom {t}"].pack(side=RIGHT, fill=Y)

                self.d[f"roomcanv {t}"].configure(yscrollcommand=self.d[f"yscrollroom {t}"].set,
                                                  xscrollcommand=self.d[f"xscrollroom {t}"].set)
                self.d[f"roomcanv {t}"].pack(side=LEFT, fill=BOTH, expand=1)

                # Create frame inside the canvas
                self.d[f"frame_1 {t}"] = ttk.Frame(self.d[f"roomcanv {t}"])
                self.d[f"frame_1 {t}"].bind('<Configure>', lambda e: self.d[f"roomcanv {t}"].configure(
                    scrollregion=self.d[f"roomcanv {t}"].bbox("all")))
                self.d[f"roomcanv {t}"].create_window((0, 0), window=self.d[f"frame_1 {t}"], anchor="nw")
                # Store room name from label
                self.d[f"nr {t}"] = self.d[f"labelname {t}"].cget("text")
                # Create a notebook with room variables inside frame_1
                self.d[f"noteb {t}{self.d[f'nr {t}']}"] = ttk.Notebook(self.d[f"frame_1 {t}"], style="BL.TNotebook")
                # Bind scroll events to both the canvas and the notebook
                self.d[f"roomcanv {t}"].bind("<MouseWheel>", lambda event: self.on_vertical_scroll(event, t))
                self.d[f"roomcanv {t}"].bind("<Shift-MouseWheel>", lambda event: self.on_horizontal_scroll(event, t))
                self.d[f"frame_1 {t}"].bind("<MouseWheel>", lambda event: self.on_vertical_scroll(event, t))
                self.d[f"frame_1 {t}"].bind("<Shift-MouseWheel>", lambda event: self.on_horizontal_scroll(event, t))

                self.d[f"x {t}"] = 0
                self.d[f"y {t}"] = 0
                self.ep = 1
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
                self.closBut = ttk.Button(self.d[f"frame_1 {t}"], text="X", width=4,
                                          command=lambda: self.closedeproom(t))
                self.closBut.grid(row=0, column=100, pady=5, padx=5, sticky="e")
                # Setup the results tab
                self.setup_results(t)
                # Setup for CT Room type
                if room_type == "CT Room":
                    self.setup_ct_room(t)
            # Select the current room and results in the notebook
            self.depnote.select(self.d[f"newroomf {t}"])
            self.resnote.select(self.d[f"resframe {t}"])

    def setup_results(self, t):
        """Set up the results tab and associated widgets for the given room."""
        # ==========Results==============
        if self.d[f"resframe {t}"] is None:
            self.d[f"resframe {t}"] = ttk.Frame(self.resnote)
            self.d[f"resframe {t}"].pack()
        self.resnote.add(self.d[f"resframe {t}"], text=f"Results of {self.ent[f'name_room {t}'].get()}")
        self.d[f"resframe {t}"].bind("<MouseWheel>", lambda event: self.on_vertical_scroll(event, t))
        # Set up the results canvas and scrollbars
        self.setup_results_scrollbars(t)
        # Create the content frame inside the results tab
        result_frame_key = f"resultframe {t}{self.d[f'nr {t}']}"
        self.d[result_frame_key] = ttk.Frame(self.rescanv)
        self.d[result_frame_key].bind('<Configure>',
                                      lambda e: self.rescanv.configure(scrollregion=self.rescanv.bbox("all")))
        # Add the result frame to the canvas
        self.rescanv.create_window((0, 0), window=self.d[result_frame_key], anchor="nw")
        # Add result label
        self.reshield = ttk.Label(self.d[result_frame_key], style="BL.TLabel", text="The Shielding of:")
        self.reshield.grid(sticky="w")
        # Mark the room as initialized and select the relevant tabs
        self.d[f"run {t}"] = True
        self.depnote.select(self.d[f"newroomf {t}"])
        self.resnote.select(self.d[f"resframe {t}"])

    def setup_results_scrollbars(self, t):
        """Set up the scrollbars for the results frame."""
        self.rescanv = Canvas(self.d[f"resframe {t}"])
        self.scrollres = ttk.Scrollbar(self.d[f"resframe {t}"], orient=VERTICAL, command=self.rescanv.yview)
        self.scrollres.pack(side=RIGHT, fill=Y)
        self.xscrollres = ttk.Scrollbar(self.d[f"resframe {t}"], orient=HORIZONTAL, command=self.rescanv.xview)
        self.xscrollres.pack(side=BOTTOM, fill=X)
        # Configure the canvas to use the scrollbars
        self.rescanv.configure(yscrollcommand=self.scrollres.set, xscrollcommand=self.xscrollres.set, bg="#f7faf9")
        self.rescanv.pack(side=LEFT, fill=BOTH, expand=1)

    def sync_results_tab(self, event):
        selected_room_tab = self.depnote.index(self.depnote.select())
        result_frame_key = f"resframe {selected_room_tab}"
        if result_frame_key in self.d:
            self.resnote.select(self.d[result_frame_key])
        else:
            pass

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
                    sheet_name = self.ent[f"name_room {b}"].get()
                    self.d[f"room_data {b}"].to_excel(writer, sheet_name=sheet_name)
        except Exception as e:
            print(f"An error occurred while saving the Excel file: {e}")
        # Open the file
        os.system(f'start {excel_file_path}')  # Use 'start' for Windows, adjust for other OS if needed

    def closedeproom(self, t):
        keys_to_destroy = [f"newroomf {t}", f"labelname {t}", f"name_room {t}", f"selroom {t}", f"crroomb {t}",
            f"resframe {t}", f"resultframe {t}{self.d.get(f'nr {t}', '')}"]
        self.destroy_widgets(keys_to_destroy)

    def create_radio_button(self, key, master, text, variable, value, row, column, command=None):
        """Utility function to create and place a radio button."""
        self.d[key] = ttk.Radiobutton(master=master, text=text, variable=variable, value=value, command=command)
        self.d[key].grid(row=row, column=column, pady=6.5, padx=5, sticky="w")

    def destroy_widgets(self, keys):
        """Utility function to destroy a list of widgets if they exist."""
        for key in keys:
            if key in self.d and self.d[key] is not None:
                self.d[key].destroy()
                del self.d[key]
            elif key in self.var and self.var[key] is not None:
                del self.var[key]
            elif key in self.ent and self.ent[key] is not None:
                try:
                    self.ent[key].destroy()
                    del self.ent[key]
                except:
                    del self.ent[key]
    # Centralized scroll functions
    def on_vertical_scroll(self, event, t):
        system = platform.system()
        if system in ["Windows", "Linux"]:
            self.d[f"roomcanv {t}"].yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif system == "Darwin":  # macOS
            self.d[f"roomcanv {t}"].yview_scroll(int(event.delta), "units")

    def on_horizontal_scroll(self, event, t):
        system = platform.system()
        if system in ["Windows", "Linux"]:
            self.d[f"roomcanv {t}"].xview_scroll(int(-1 * (event.delta / 120)), "units")
        elif system == "Darwin":  # macOS
            self.d[f"roomcanv {t}"].xview_scroll(int(event.delta), "units")