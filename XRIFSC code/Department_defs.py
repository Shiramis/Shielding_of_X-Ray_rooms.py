import tkinter
import subprocess
from tkinter import *
from tkinter import ttk

class dep_defs():
    def barriers(self, t):
        current_barriers = self.d[f"x {t}"]
        max_barriers = self.d[f"vnumwall {t}"].get()
        room_number = self.d[f"nr {t}"]

        def initialize_barrier(index):
            """Initialize values and widgets for a barrier."""
            self.thm[f"xbar {index}{room_number}"] = 0
            self.xlmat[f"thic {index}{room_number}"] = 0
            # Default barrier settings
            for var in ["titleresul", "lau", "use_ent", "presh", "radbucky", "radcross"]:
                self.d[f"{var} {index}"] = None
            for var in ["radside", "radforward", "leakvar", "existvar", "sellocation", "forw", "side", "laks", "entk",
                        "leak"]:
                self.d[f"{var} {index}{room_number}"] = None
            for var in ["preshvar", "preshuns", "radiob_pre", "radiob_leak", "leakvar", "airkerv"]:
                self.d[f"{var} {index}{room_number}"] = IntVar(value=0)
            self.d[f"barrierf {index}{room_number}"] = ttk.Frame(self.d[f"noteb {t}{room_number}"], width=190)
            self.d[f"barrierf {index}{room_number}"].pack()
            if index <= 3:
                labels = ["Floor", "Ceiling", "Door"]
                self.barn[f"lab_bar {index}{room_number}"] = Label(text=labels[index - 1])
            else:
                self.barn[f"lab_bar {index}{room_number}"] = Label(text=f"Barrier {index - 3}")
            self.d[f"noteb {t}{room_number}"].add(self.d[f"barrierf {index}{room_number}"],
                text=self.barn[f"lab_bar {index}{room_number}"].cget("text"))
            self.barr[self.barn[f"lab_bar {index}{room_number}"].cget("text")] = 0
            # Select Materials
            self.matlab = ttk.Label(master= self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                                    text="Select Materials:")
            self.matlab.grid(row=8, column=0, padx=10, pady=10, sticky="w")
            # Add spinbox for number of materials
            self.d[f"vnumbmat {index}{room_number}"] = IntVar(value=1)
            if self.d[f"vselroom {t}"].get() == "CT Room":
                self.d[f"numbmat {index}{room_number}"] = ttk.Spinbox(master=self.d[f"barrierf {index}{room_number}"],
                    from_=1, to=2, width=5, textvariable=self.d[f"vnumbmat {index}{room_number}"],
                    command=lambda e=index, nr=room_number: self.numbmater(e, nr, t))
            else:
                self.d[f"numbmat {index}{room_number}"] = ttk.Spinbox(master=self.d[f"barrierf {index}{room_number}"],
                    from_=1, to=6, width=5, textvariable=self.d[f"vnumbmat {index}{room_number}"],
                    command=lambda e=index, nr=room_number: self.numbmater(e, nr, t))

            self.d[f"numbmat {index}{room_number}"].grid(row=8, column=1, padx=10, pady=10, sticky="w")
            # Add widgets based on room type
            if self.d[f"vselroom {t}"].get() == "CT Room":
                self._add_ct_room_widgets(index, room_number, t)
            else:
                self._add_xray_room_widgets(index, room_number, t)
            # Calculate button
            self.d[f"calbutton {index}"] = ttk.Button(master=self.d[f"barrierf {index}{room_number}"], text="Calculate",
                command=lambda e=index, nr=room_number: self.choosetype(e, nr, t))
            self.d[f"calbutton {index}"].grid(row=19, column=1, pady=10, padx=10, sticky="w")
            # Call numbmater to initialize the materials based on the spinbox value
            self.numbmater(index, room_number, t)
        # Add or remove barriers as necessary
        if current_barriers < max_barriers:
            while current_barriers < max_barriers:
                current_barriers += 1
                initialize_barrier(current_barriers)
        elif current_barriers > max_barriers:
            while current_barriers > max_barriers:
                self.d[f"barrierf {current_barriers}{room_number}"].destroy()
                self.d[f"label_B {current_barriers}"].destroy()
                self.d[f"radpw {current_barriers}{room_number}"].destroy()
                self.d[f"radsw {current_barriers}{room_number}"].destroy()
                current_barriers -= 1
        # Update the number of barriers
        self.d[f"x {t}"] = current_barriers
        if self.d[f"vselroom {t}"].get() == "CT Room":
            self.d[f"noteb {t}{room_number}"].grid(row=0, column=2, rowspan=10, columnspan=current_barriers, pady=10,
                                                   padx=10, sticky="wn")
        else:
            self.d[f"noteb {t}{room_number}"].grid(row=4, column=0, rowspan=10, columnspan=current_barriers, pady=10,
                                               padx=10, sticky="wn")
    def _add_ct_room_widgets(self, index, room_number, t):
        """Add CT room specific widgets."""
        dist_label = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                               text='Distance from the CT Unit Isocenter (m):')
        dist_label.grid(row=7, column=0, padx=10, pady=10, sticky="w")
        self.d[f"dist_var {index}{room_number}"] = StringVar()
        dist_entry = ttk.Entry(master=self.d[f"barrierf {index}{room_number}"],
                               textvariable=self.d[f"dist_var {index}{room_number}"], width=10)
        dist_entry.grid(row=7, column=1, padx=10, pady=10, sticky="w")

        sh_label = ttk.Label(master=self.d[f"barrierf {index}{room_number}"],
                             text='Shielding design Goal(P)\n in air kerma(mGy∙week\u207B\u00b9):')
        sh_label.grid(row=11, column=0, padx=10, pady=10, sticky="w")
        self.d[f"sh_var {index}{room_number}"] = DoubleVar()
        sh_entry = ttk.Entry(master=self.d[f"barrierf {index}{room_number}"],
                             textvariable=self.d[f"sh_var {index}{room_number}"], width=10)
        sh_entry.grid(row=11, column=1, padx=10, pady=10, sticky="w")

    def _add_xray_room_widgets(self, index, room_number, t):
        """Add X-ray room specific widgets."""
        self.d[f"label_B {index}"] = ttk.Label(
            master=self.d[f"barrierf {index}{room_number}"],
            style="BL.TLabel", text="Select Barrier Type")
        self.d[f"label_B {index}"].grid(row=0, column=0, pady=10, padx=10, sticky="w")

        self.d[f"radiob_w {index}{room_number}"] = IntVar(value=0)
        self.d[f"radpw {index}{room_number}"] = ttk.Radiobutton(
            master=self.d[f"barrierf {index}{room_number}"],
            variable=self.d[f"radiob_w {index}{room_number}"],
            text="Primary Barrier", value=1,
            command=lambda e=index, nr=room_number: self.barrier_sel(e, nr, t))
        self.d[f"radpw {index}{room_number}"].grid(row=1, column=0, pady=10, padx=10, sticky="w")

        self.d[f"radsw {index}{room_number}"] = ttk.Radiobutton(
            master=self.d[f"barrierf {index}{room_number}"],
            variable=self.d[f"radiob_w {index}{room_number}"],
            text="Secondary Barrier", value=2,
            command=lambda e=index, nr=room_number: self.barrier_sel(e, nr, t))
        self.d[f"radsw {index}{room_number}"].grid(row=1, column=1, pady=10, padx=10, sticky="w")

        self.lad = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                             text="Distance from the Source (m):")
        self.lad.grid(row=7, column=0, pady=10, padx=10, sticky="w")
        self.d[f"entryd {index}{room_number}"] = ttk.Entry(
            master=self.d[f"barrierf {index}{room_number}"], width=10)
        self.d[f"entryd {index}{room_number}"].grid(row=7, column=1, pady=10, padx=10, sticky="w")
        # Area classification and occupancy factor
        self._add_xray_room_additional_widgets(index, room_number, t)

    def _add_xray_room_additional_widgets(self, index, room_number, t):
        """Add additional widgets for X-ray room."""
        self.title_ocupat = ttk.Label(
            master=self.d[f"barrierf {index}{room_number}"], style="BL.TLabel",
            text="Shielding Area")
        self.title_ocupat.grid(row=13, column=0, pady=10, padx=10, sticky="w")
        self.d[f"area {index}{room_number}"] = StringVar()
        self.d[f"area {index}{room_number}"] = ttk.Combobox(
            master=self.d[f"barrierf {index}{room_number}"],
            textvariable=self.d[f"area {index}{room_number}"],
            values=["Controlled Area", "Uncontrolled Area", "Supervised Area"], state="readonly")
        self.d[f"area {index}{room_number}"].grid(row=13, column=1, sticky="w")
        self.d[f"area {index}{room_number}"].set("Classify the area")

        self.d[f"vraoccup {index}{room_number}"] = IntVar(value=0)
        self.raoccup = ttk.Radiobutton(
            master=self.d[f"barrierf {index}{room_number}"],
            variable=self.d[f"vraoccup {index}{room_number}"], text="Write occupancy factor (T):",
            value=1, command=lambda e=index, nr=room_number: self.occupation3(e, nr, t))
        self.raoccup.grid(row=14, column=0, pady=10, padx=10, sticky="w")

        self.raseloccup = ttk.Radiobutton(
            master=self.d[f"barrierf {index}{room_number}"],
            text="or select Location [suggested NCRP 147]",
            variable=self.d[f"vraoccup {index}{room_number}"], value=2,
            command=lambda e=index, nr=room_number: self.occupation3(e, nr, t))
        self.raseloccup.grid(row=15, column=0, pady=10, padx=10, sticky="w")

        self.ladike = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                                text="Design Kerma Goal (mGy/week):")
        self.ladike.grid(row=16, column=0, pady=10, padx=10, sticky="w")
        self.d[f"dikeent {index}{room_number}"] = ttk.Entry(master=self.d[f"barrierf {index}{room_number}"], width=10)
        self.d[f"dikeent {index}{room_number}"].grid(row=16, column=1, pady=10, padx=10, sticky="w")

    def occupation3(self, e, nr, t):
        vra_key = f"vraoccup {e}{nr}"
        area_key = f"area {e}{nr}"
        occupentry_key = f"occupentry {e}{nr}"
        sellocation_key = f"sellocation {e}{nr}"
        barrierf_key = f"barrierf {e}{nr}"
        dikeent_key = f"dikeent {e}{nr}"
        # Destroy any existing entry before creating a new one
        if self.d.get(dikeent_key):
            self.d[dikeent_key].destroy()

        self.d[dikeent_key] = ttk.Entry(master=self.d[barrierf_key], width=10)
        self.d[dikeent_key].grid(row=16, column=1, pady=10, padx=10, sticky="w")

        if self.d[vra_key].get() == 1:
            # Destroy previous widgets if they exist
            if self.d.get(sellocation_key):
                self.d[sellocation_key].destroy()
            if self.d.get(occupentry_key):
                self.d[occupentry_key].destroy()
            # Create Location Entry widget for occupation
            self.d[f"vselocation {e}{nr}"] = StringVar()
            self.d[occupentry_key] = ttk.Entry(master=self.d[barrierf_key], width=10)
            # Insert specific values depending on the area
            if self.d[area_key].get() == "Controlled Area":
                self.d[occupentry_key].insert(0, str(1))
                self.d[dikeent_key].insert(0, str(0.01))
            elif self.d[area_key].get() == "Uncontrolled Area":
                self.d[occupentry_key].insert(0, str(1 / 16))
                self.d[dikeent_key].insert(0, str(0.006))
            elif self.d[area_key].get() == "Supervised Area":
                self.d[occupentry_key].insert(0, str(1 / 4))
                self.d[dikeent_key].insert(0, str(0.006))
            self.d[occupentry_key].grid(row=14, column=1, pady=10, padx=10)
        elif self.d[vra_key].get() == 2:
            # Destroy previous widgets if they exist
            if self.d.get(occupentry_key):
                self.d[occupentry_key].destroy()
            if self.d.get(sellocation_key):
                self.d[sellocation_key].destroy()
            # Initialize the location options
            self.d[f"vselocation {e}{nr}"] = StringVar()
            # Create location options based on the area
            if self.d[area_key].get() == "Controlled Area":
                locations = ("Administrative or clerical offices", "Laboratories", "Pharmacies", "Receptionist areas",
                             "X-ray control rooms")
                self.d[dikeent_key].insert(0, str(0.01))
            elif self.d[area_key].get() == "Uncontrolled Area":
                locations = ("Public toilets", "Storage rooms", "Outdoor areas", "Unattended waiting rooms")
                self.d[dikeent_key].insert(0, str(0.006))
            elif self.d[area_key].get() == "Supervised Area":
                locations = ("Corridors", "Patient rooms", "Employee lounges", "Staff restrooms")
                self.d[dikeent_key].insert(0, str(0.006))
            else:
                locations = ("Administrative or clerical offices","Laboratories", "Pharmacies and other work areas fully occupied by an individual",
                "Receptionist areas","Attended waiting rooms","Children’s indoor play areas","Adjacent x-ray rooms",
                "Film reading areas", "Nurse’s stations","X-ray control rooms","Rooms used for patient examinations and treatments",
                "Corridors", "Patient rooms","Employee lounges", "Staff restooms","Corridor doors", "Public toilets",
                "Unattended vending areas","Storage  rooms","Outdoor areas with seating","Unattended waiting rooms",
                "Patient holding areas","Outdoor areas with only transient pedestrian or vehicular traffic",
                "Unattended parking lots","Vehicular drop off areas (unattended)","Attics", "Stairways",
                "Unattended elevators","Janitor’s closets")
            # Create OptionMenu with location choices
            self.d[sellocation_key] = ttk.OptionMenu(self.d[barrierf_key], self.d[f"vselocation {e}{nr}"],
                                                     "Select Location", *locations)
            self.d[sellocation_key].grid(row=15, column=1, pady=10, padx=10, sticky="w")
            self.d[sellocation_key].config(width=15)

    def barrier_sel(self, e, nr, t):
        radiob_w_key = f"radiob_w {e}{nr}"
        barrierf_key = f"barrierf {e}{nr}"
        # =====Selects Primary Barrier=======
        if self.d[radiob_w_key].get() == 1:
            # Safely destroy previous widgets if they exist
            for key in [f"lau {e}", f"use_ent {e}", f"presh {e}", f"preunsh {e}",f"radbucky {e}",f"radcross {e}", f"laks {e}{nr}", f"entk {e}{nr}",
                        f"radside {e}{nr}", f"radforward {e}{nr}", f"leak {e}{nr}",f"radleak {e}{nr}", f"forw {e}{nr}", f"side {e}{nr}",
                        f"write {e}{nr}"]:
                if self.d.get(key):
                    self.d[key].destroy()
            # ================== Use Factor ====================
            self.d[f"lau {e}"] = ttk.Label(master=self.d[barrierf_key], style="AL.TLabel", text="Use Factor:")
            self.d[f"lau {e}"].grid(row=3, column=0, pady=10, padx=10, sticky="w")
            self.d[f"use_ent {e}"] = ttk.Entry(master=self.d[barrierf_key], width=10)
            # Insert the appropriate values based on Room
            if e == 1:
                if self.d.get(f"selxroom {t}"):
                    if self.d[f"vsexroom {t}"].get() == "Rad Room (floor or other barriers)":
                        self.d[f"use_ent {e}"].insert(0, str(0.89))
                else:
                    self.d[f"use_ent {e}"].insert(0, str(1))
            elif e == 2:
                self.d[f"use_ent {e}"].insert(0, str(1 / 16))
            else:
                if self.d.get(f"selxroom {t}"):
                    if self.d[f"vsexroom {t}"].get() == "Rad Room (floor or other barriers)":
                        self.d[f"use_ent {e}"].insert(0, str(0.02))
                else:
                    self.d[f"use_ent {e}"].insert(0, str(1 / 4))
            self.d[f"use_ent {e}"].grid(row=3, column=1, pady=10, padx=10, sticky="w")
            # =========== Preshielding ==============
            self.d[f"presh {e}"] = ttk.Checkbutton(master=self.d[barrierf_key], text="Preshielding",
                                                   variable=self.d[f"preshvar {e}{nr}"], offvalue=0, onvalue=1,
                                                   command=lambda: self.pres(e, nr))
            self.d[f"presh {e}"].grid(row=4, column=0, pady=10, padx=10, sticky="w")
            # =========== Unshielded Air Kerma ============
            self.d[f"preunsh {e}"] = ttk.Checkbutton(master=self.d[barrierf_key], text="Unshielded air kerma",
                                                     variable=self.d[f"preshuns {e}{nr}"], offvalue=0, onvalue=1,
                                                     command=lambda: self.uns(e, nr))
            self.d[f"preunsh {e}"].grid(row=4, column=1, pady=10, padx=10, sticky="w")
        # =====Selects Secondary Barrier=======
        elif self.d[radiob_w_key].get() == 2:
            # Safely destroy widgets for the previous state if they exist
            for key in [f"leak {e}{nr}", f"side {e}{nr}", f"forw {e}{nr}", f"write {e}{nr}", f"lau {e}", f"use_ent {e}",
                        f"preunsh {e}", f"presh {e}", f"radbucky {e}",f"radcross {e}", f"laks {e}{nr}", f"entk {e}{nr}"]:
                if self.d.get(key):
                    self.d[key].destroy()
            # ============ Leakage Radiation Selection ============
            self.d[f"leak {e}{nr}"] = ttk.Radiobutton(master=self.d[barrierf_key], text="Leakage radiation",
                                                      variable=self.d[f"airkerv {e}{nr}"], value=1,
                                                      command=lambda: self.leakage(e, nr))
            self.d[f"leak {e}{nr}"].grid(row=2, column=0, pady=10, padx=10, sticky="w")
            self.d[f"side {e}{nr}"] = ttk.Radiobutton(master=self.d[barrierf_key], text="Side-Scatter",
                                                      variable=self.d[f"airkerv {e}{nr}"], value=2,
                                                      command=lambda: self.leakage(e, nr))
            self.d[f"side {e}{nr}"].grid(row=2, column=1, pady=10, padx=10, sticky="w")
            self.d[f"forw {e}{nr}"] = ttk.Radiobutton(master=self.d[barrierf_key], text="Forward/Backscatter",
                                                      variable=self.d[f"airkerv {e}{nr}"], value=3,
                                                      command=lambda: self.leakage(e, nr))
            self.d[f"forw {e}{nr}"].grid(row=3, column=0, pady=10, padx=10, sticky="w")
            self.d[f"write {e}{nr}"] = ttk.Radiobutton(master=self.d[barrierf_key], text="Unshielded air kerma",
                                                       variable=self.d[f"airkerv {e}{nr}"], value=4,
                                                       command=lambda: self.leakage(e, nr))
            self.d[f"write {e}{nr}"].grid(row=3, column=1, pady=10, padx=10, sticky="w")

    def uns(self, e, nr):
        preshuns_key = f"preshuns {e}{nr}"
        barrierf_key = f"barrierf {e}{nr}"
        laks_key = f"laks {e}{nr}"
        entk_key = f"entk {e}{nr}"
        if self.d[preshuns_key].get() == 1:
            # Create and display if select unshielded air kerma
            self.d[laks_key] = ttk.Label(master=self.d[barrierf_key], text="K (mGy/patient):")
            self.d[laks_key].grid(row=6, column=0, pady=10, padx=10, sticky="w")
            self.d[entk_key] = ttk.Entry(master=self.d[barrierf_key], width=10)
            self.d[entk_key].grid(row=6, column=1, pady=10, padx=10, sticky="w")
        elif self.d[preshuns_key].get() == 0:
            if self.d.get(laks_key):
                self.d[laks_key].destroy()
            if self.d.get(entk_key):
                self.d[entk_key].destroy()

    def numbmater(self, e, nr, t):
        m_key = f"m {e}{nr}"
        vnumbmat_key = f"vnumbmat {e}{nr}"
        # Initialize the material count if not already present
        if m_key not in self.d:
            self.d[m_key] = 0
        selected_room = self.d[f"vselroom {t}"].get()
        # For "CT Room"
        if selected_room == "CT Room":
            if self.d[m_key] < self.d[vnumbmat_key].get():
                while self.d[m_key] < self.d[vnumbmat_key].get():
                    self.d[m_key] += 1
                    self.mater = ("Lead", "Concrete")
                    self.d[f"vmater {e}{self.d[m_key]}{nr}"] = StringVar()
                    self.d[f"mater {e}{self.d[m_key]}"] = ttk.OptionMenu(self.d[f"barrierf {e}{nr}"],
                        self.d[f"vmater {e}{self.d[m_key]}{nr}"], "Select Material", *self.mater)
                    if self.d[m_key] < 3:
                        self.d[f"matlab {e}{self.d[m_key]}"] = ttk.Label(self.d[f"barrierf {e}{nr}"],
                            text=f"#{self.d[m_key]}:")
                        self.d[f"matlab {e}{self.d[m_key]}"].grid(row=10, column=-1 + self.d[m_key], sticky="w")
                        self.d[f"mater {e}{self.d[m_key]}"].grid(row=10, column=-1 + self.d[m_key], pady=10, padx=25,
                            sticky="s")

            # Destroy extra widgets if material count exceeds the required number
            else:
                while self.d[m_key] > self.d[vnumbmat_key].get():
                    self.d[f"mater {e}{self.d[m_key]}"].destroy()
                    self.d[f"matlab {e}{self.d[m_key]}"].destroy()
                    self.d[m_key] -= 1

        # For "X-ray Room"
        else:
            if self.d[m_key] < self.d[vnumbmat_key].get():
                while self.d[m_key] < self.d[vnumbmat_key].get():
                    self.d[m_key] += 1
                    self.mater = ("Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass", "Wood")
                    self.d[f"vmater {e}{self.d[m_key]}{nr}"] = StringVar()
                    self.d[f"mater {e}{self.d[m_key]}"] = ttk.OptionMenu(self.d[f"barrierf {e}{nr}"],
                        self.d[f"vmater {e}{self.d[m_key]}{nr}"], "Select Material", *self.mater)
                    if self.d[m_key] < 3:
                        self.d[f"matlab {e}{self.d[m_key]}"] = ttk.Label(self.d[f"barrierf {e}{nr}"],
                            text=f"#{self.d[m_key]}:")
                        self.d[f"matlab {e}{self.d[m_key]}"].grid(row=10, column=-1 + self.d[m_key], sticky="w")
                        self.d[f"mater {e}{self.d[m_key]}"].grid(row=10, column=-1 + self.d[m_key], pady=5, padx=5,
                            sticky="s")
                    elif 2 < self.d[m_key] < 5:
                        self.d[f"matlab {e}{self.d[m_key]}"] = ttk.Label(self.d[f"barrierf {e}{nr}"],
                            text=f"#{self.d[m_key]}:")
                        self.d[f"matlab {e}{self.d[m_key]}"].grid(row=11, column=-3 + self.d[m_key], sticky="w")
                        self.d[f"mater {e}{self.d[m_key]}"].grid(row=11, column=-3 + self.d[m_key], pady=5, padx=5,
                            sticky="s")
                    else:
                        self.d[f"matlab {e}{self.d[m_key]}"] = ttk.Label(self.d[f"barrierf {e}{nr}"],
                            text=f"#{self.d[m_key]}:")
                        self.d[f"matlab {e}{self.d[m_key]}"].grid(row=12, column=-5 + self.d[m_key], sticky="w")
                        self.d[f"mater {e}{self.d[m_key]}"].grid(row=12, column=-5 + self.d[m_key], pady=5, padx=5,
                            sticky="s")

            # Destroy extra widgets if material count exceeds the required number
            else:
                while self.d[m_key] > self.d[vnumbmat_key].get():
                    self.d[f"mater {e}{self.d[m_key]}"].destroy()
                    self.d[f"matlab {e}{self.d[m_key]}"].destroy()
                    self.d[m_key] -= 1

    def pres(self, e, nr):
        preshvar_key = f"preshvar {e}{nr}"
        radbucky_key = f"radbucky {e}"
        radcross_key = f"radcross {e}"
        radiob_pre_key = f"radiob_pre {e}{nr}"
        # Check if selects preshielding
        if self.d[preshvar_key].get() == 1:
            self.d[radbucky_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"], variable=self.d[radiob_pre_key],
                text="Bucky", value=1)
            self.d[radbucky_key].grid(row=5, column=0, pady=10, padx=10, sticky="w")

            self.d[radcross_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"], variable=self.d[radiob_pre_key],
                text="Cross-table", value=2)
            self.d[radcross_key].grid(row=5, column=1, pady=10, padx=10, sticky="w")

        # If "preshielding" is set to 0, destroy the widgets if they exist
        elif self.d[preshvar_key].get() == 0:
            if radbucky_key in self.d and self.d[radbucky_key] is not None:
                self.d[radbucky_key].destroy()
            if radcross_key in self.d and self.d[radcross_key] is not None:
                self.d[radcross_key].destroy()

    def leakage(self, e, nr):
        airkerv_key = f"airkerv {e}{nr}"
        radside_key = f"radside {e}{nr}"
        radforward_key = f"radforward {e}{nr}"
        radleak_key = f"radleak {e}{nr}"
        laks_key = f"laks {e}{nr}"
        entk_key = f"entk {e}{nr}"
        radiob_leak_key = f"radiob_leak {e}{nr}"
        # Function to destroy existing widgets if they exist
        def destroy_widgets(keys):
            for key in keys:
                if key in self.d and self.d[key] is not None:
                    self.d[key].destroy()
        # If selects Leakage
        if self.d[airkerv_key].get() == 1:
            # Destroy any existing widgets before creating new ones
            destroy_widgets([radside_key, radforward_key, radleak_key, laks_key, entk_key])
            # Create options of leakage barrier
            self.d[radside_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"], variable=self.d[radiob_leak_key],
                text="Leakage and Side-Scatter", value=1)
            self.d[radside_key].grid(row=4, column=0, pady=10, padx=10, sticky="w")
            self.d[radforward_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"],
                variable=self.d[radiob_leak_key], text="Leakage and Forward/ Backscatter", value=2)
            self.d[radforward_key].grid(row=4, column=1, pady=10, padx=10, sticky="w")
            self.d[radleak_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"], variable=self.d[radiob_leak_key],
                text="Only Leakage", value=0)
            self.d[radleak_key].grid(row=5, column=0, pady=10, padx=10, sticky="w")
        # If selects Secondary Air Kerma
        elif self.d[airkerv_key].get() == 4:
            # Destroy any existing widgets before creating new ones
            destroy_widgets([radside_key, radforward_key, radleak_key, laks_key, entk_key])
            self.d[laks_key] = ttk.Label(master=self.d[f"barrierf {e}{nr}"], text="K\u209b (mGy/patient):")
            self.d[laks_key].grid(row=4, column=0, pady=10, padx=10, sticky="w")
            self.d[entk_key] = ttk.Entry(master=self.d[f"barrierf {e}{nr}"], width=10)
            self.d[entk_key].grid(row=4, column=1, pady=10, padx=10, sticky="w")
        # For Scatter, destroy existing widgets
        else:
            destroy_widgets([radside_key, radforward_key, radleak_key, laks_key, entk_key])
        # ============selection of X-ray room or X-ray tube=============

    def existbarrier(self, e,nr,t):
        if self.d["existvar " + str(e)+nr].get() == 1:
            if self.d["existla " + str(e) + nr] is not None:
                self.d["existla " + str(e) + nr].destroy()
                self.d["existmat " + str(e) + nr].destroy()
                self.d["materex " + str(e) + nr].destroy()
            self.d["existla "+str(e)+nr] \
                = ttk.Label(master=self.d["barrierf " + str(e)+nr], style="AL.TLabel",
                                                             text="Existing Barrier in mm:")
            self.d["existla " + str(e)+nr].grid(row=6, column=0, pady=10, padx=10, sticky="w")
            self.d["existmat "+str(e)+nr] \
                = ttk.Entry(master=self.d["barrierf " + str(e)+nr], width=10)
            self.d["existmat " + str(e)+nr].grid(row=6, column=1, pady=10, padx=10, sticky="w")

            self.d["vmaterex "+str(e)+nr] = StringVar()
            self.d["materex "+str(e)+nr] \
                = ttk.OptionMenu(self.d["barrierf " + str(e)+nr],
                self.d["vmaterex "+str(e)+nr], "Select Material", *self.mater)
            self.d["materex " + str(e)+nr].grid(row=7, column=0, pady=10, padx=10, sticky="w")
        elif self.d["existvar " + str(e)+nr].get() == 0:
            if self.d["existla " + str(e)+nr] is not None:
                self.d["existla " + str(e)+nr].destroy()
                self.d["existmat " + str(e)+nr].destroy()
                self.d["materex " + str(e)+nr].destroy()