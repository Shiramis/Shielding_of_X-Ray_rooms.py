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
            for var in ["titleresul","use_ent", "radside", "radforward", "leakvar", "existvar", "sellocation", "forw", "side",
                        "laks", "entk", "leak"]:
                self.d[f"{var} {index}{room_number}"] = None

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

            # Select Materials label
            self.matlab = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                                    text="Select Materials:")
            rowm = 8 if self.d[f"vselroom {t}"].get() == "CT Room" else 99

            self.matlab.grid(row=rowm, column=0, padx=5, pady=6.5, sticky="w")

            # Add spinbox for number of materials
            self.d[f"vnumbmat {index}{room_number}"] = IntVar(value=1)
            spinbox_max = 2 if self.d[f"vselroom {t}"].get() == "CT Room" else 6
            self.d[f"numbmat {index}{room_number}"] = ttk.Spinbox(master=self.d[f"barrierf {index}{room_number}"],
                from_=1, to=spinbox_max, width=5, textvariable=self.d[f"vnumbmat {index}{room_number}"],
                command=lambda e=index, nr=room_number: self.numbmater(e, nr, t))
            self.d[f"numbmat {index}{room_number}"].grid(row=rowm, column=1, padx=5, pady=6.5, sticky="w")

            # Add widgets based on room type
            if self.d[f"vselroom {t}"].get() == "CT Room":
                self._add_ct_room_widgets(index, room_number, t)
            else:
                self._add_xray_room_widgets(index, room_number, t)

            # Call numbmater to initialize the materials based on the spinbox value
            self.numbmater(index, room_number, t)

        # Add barriers as necessary
        while current_barriers < max_barriers:
            current_barriers += 1
            initialize_barrier(current_barriers)

        # Remove barriers as necessary
        while current_barriers > max_barriers:
            barrier_frame_key = f"barrierf {current_barriers}{room_number}"
            label_B_key = f"label_B {current_barriers}"
            radpw_key = f"radpw {current_barriers}{room_number}"
            radsw_key = f"radsw {current_barriers}{room_number}"

            # Safely destroy and remove the barrier widgets, checking existence first
            if barrier_frame_key in self.d and self.d[barrier_frame_key] is not None:
                self.d[barrier_frame_key].destroy()
                del self.d[barrier_frame_key]

            if label_B_key in self.d and self.d[label_B_key] is not None:
                self.d[label_B_key].destroy()
                del self.d[label_B_key]

            if radpw_key in self.d and self.d[radpw_key] is not None:
                self.d[radpw_key].destroy()
                del self.d[radpw_key]

            if radsw_key in self.d and self.d[radsw_key] is not None:
                self.d[radsw_key].destroy()
                del self.d[radsw_key]

            current_barriers -= 1

        # Update the number of barriers
        self.d[f"x {t}"] = current_barriers

        # Adjust grid based on the number of barriers and room type
        if self.d[f"vselroom {t}"].get() == "CT Room":
            self.d[f"noteb {t}{room_number}"].grid(row=0, column=2, rowspan=10, columnspan=current_barriers, pady=6.5,
                                                   padx=5, sticky="wn")
        else:
            self.d[f"noteb {t}{room_number}"].grid(row=4, column=0, rowspan=10, columnspan=current_barriers, pady=6.5,
                                                   padx=5, sticky="wn")

    def _add_ct_room_widgets(self, index, room_number, t):
        """Add CT room specific widgets."""
        dist_label = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                               text='Distance from the CT Unit Isocenter (m):')
        dist_label.grid(row=7, column=0, padx=5, pady=6.5, sticky="w")
        self.d[f"dist_var {index}{room_number}"] = StringVar()
        dist_entry = ttk.Entry(master=self.d[f"barrierf {index}{room_number}"],
                               textvariable=self.d[f"dist_var {index}{room_number}"], width=10)
        dist_entry.grid(row=7, column=1, padx=5, pady=6.5, sticky="w")

        sh_label = ttk.Label(master=self.d[f"barrierf {index}{room_number}"],
                             text='Shielding Design Goal(P)\n(mGy∙week\u207B\u00b9):')
        sh_label.grid(row=11, column=0, padx=5, pady=6.5, sticky="w")
        self.d[f"sh_var {index}{room_number}"] = DoubleVar()
        sh_entry = ttk.Entry(master=self.d[f"barrierf {index}{room_number}"],
                             textvariable=self.d[f"sh_var {index}{room_number}"], width=10)
        sh_entry.grid(row=11, column=1, padx=5, pady=6.5, sticky="w")
        self.d[f"calbutton {index}{room_number}"] = ttk.Button(master=self.d[f"barrierf {index}{room_number}"],
                                                               text="Calculate",
                                                               command=lambda e=index, nr=room_number: self.choosetype(
                                                                   e, nr, t))
        self.d[f"calbutton {index}{room_number}"].grid(row=12, column=2, pady=6.5, padx=5, sticky="w")

    def _add_xray_room_widgets(self, index, room_number, t):
        """Add X-ray room specific widgets."""
        # Label to indicate number of radiation types on the barrier
        labb = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                         text="Select the number of types\nof radiation on the barrier:")
        labb.grid(row=0, column=0, pady=6.5, padx=5, sticky="w")

        # Initialize tracking of the previous number of barriers
        self.d[f"prev_num_barriers {index}{room_number}"] = 0

        # Spinbox for the number of barriers
        self.d[f"num_barriers_var {index}{room_number}"] = IntVar(value=1)  # Default to 1
        self.d[f"num_barriers_spinbox {index}{room_number}"] = ttk.Spinbox(
            master=self.d[f"barrierf {index}{room_number}"], width=5, from_=1, to=8, increment=1,
            textvariable=self.d[f"num_barriers_var {index}{room_number}"],
            command=lambda e=index, nr=room_number: self._create_barrier_widgets(e, nr, t))
        self.d[f"num_barriers_spinbox {index}{room_number}"].grid(row=0, column=1, pady=6.5, padx=5, sticky="w")
        self._create_barrier_widgets(index, room_number, t)
        # Area classification and occupancy factor
        self._add_xray_room_additional_widgets(index, room_number, t)


        self.d[f"calbutton {index}{room_number}"] = ttk.Button(master=self.d[f"barrierf {index}{room_number}"],text="Calculate",
              command=lambda e=index, nr=room_number: self.choosetype(e, nr, t))
        self.d[f"calbutton {index}{room_number}"].grid(row=107, column=2, pady=6.5, padx=5, sticky="w")

    def _create_barrier_widgets(self, index, room_number, t):
        """Dynamically create or delete barrier-related widgets based on the selected number in the Spinbox."""
        num_barriers = self.d[f"num_barriers_var {index}{room_number}"].get()
        prev_num_barriers = self.d[f"prev_num_barriers {index}{room_number}"]

        if num_barriers > prev_num_barriers:
            # Create widgets for the new barriers
            for i in range(prev_num_barriers, num_barriers):
                # Label for barrier type
                self.d[f"label_B {index}{room_number}{i}"] = ttk.Label(master=self.d[f"barrierf {index}{room_number}"],
                    style="BL2.TLabel", text=f"Select Radiation Type #{i + 1}:")
                self.d[f"label_B {index}{room_number}{i}"].grid(row=i * 10 + 1, column=0, pady=6.5, padx=5, sticky="w")

                self.d[f"radiob_w {index}{room_number}{i}"] = IntVar(value=0)

                # Primary Barrier Radiobutton
                self.d[f"radpw {index}{room_number}{i}"] = ttk.Radiobutton(
                    master=self.d[f"barrierf {index}{room_number}"],
                    variable=self.d[f"radiob_w {index}{room_number}{i}"], text=f"Primary", value=1,
                    command=lambda e=index, nr=room_number: self.barrier_sel(e, nr, t, i))
                self.d[f"radpw {index}{room_number}{i}"].grid(row=i * 10 + 1, column=1, pady=6.5, padx=5, sticky="w")

                # Secondary Barrier Radiobutton
                self.d[f"radsw {index}{room_number}{i}"] = ttk.Radiobutton(
                    master=self.d[f"barrierf {index}{room_number}"],
                    variable=self.d[f"radiob_w {index}{room_number}{i}"], text=f"Secondary", value=2,
                    command=lambda e=index, nr=room_number: self.barrier_sel(e, nr, t, i))
                self.d[f"radsw {index}{room_number}{i}"].grid(row=i * 10 + 1, column=2, pady=6.5, padx=5, sticky="w")
                # Distance label and entry
                self.d[f'lad {index}{room_number}{i}'] = ttk.Label(master=self.d[f"barrierf {index}{room_number}"],
                    style="AL.TLabel", text="Distance from the Source\nto the Barrier (m):")
                self.d[f'lad {index}{room_number}{i}'].grid(row=i * 10 + 3, column=0, pady=6.5, padx=5, sticky="w")
                self.d[f"entryd {index}{room_number}{i}"] = ttk.Entry(master=self.d[f"barrierf {index}{room_number}"],
                    width=10)
                self.d[f"entryd {index}{room_number}{i}"].grid(row=i * 10 + 3, column=1, pady=6.5, padx=5, sticky="w")

        elif num_barriers < prev_num_barriers:
            for i in range(num_barriers, prev_num_barriers):
                # Define widget keys
                keys_to_destroy = [f"radpw {index}{room_number}{i}", f"radsw {index}{room_number}{i}",
                    f"label_B {index}{room_number}{i}", f"lad {index}{room_number}{i}",
                    f"entryd {index}{room_number}{i}", f"workltit {index}{room_number}{i}", f"selxray1 {index}{room_number}{i}",
                    f"selxray2 {index}{room_number}{i}", f"lau {index}{room_number}{i}", f"use_ent {index}{room_number}{i}",
                    f"presh {index}{room_number}{i}", f"selxroom {index}{room_number}{i}", f"laks {index}{room_number}{i}",
                    f"entk {index}{room_number}{i}", f"othwork {index}{room_number}{i}", f"radbucky {index}{room_number}{i}",
                    f"radcross {index}{room_number}{i}", f"radworkl {index}{room_number}{i}",f"radnumb {index}{room_number}{i}",
                    f"worentry {index}{room_number}{i}",f"numpapwe {index}{room_number}{i}", f"airkncrp {index}{room_number}{i}",
                    f"unairk {index}{room_number}{i}",f"leak {index}{room_number}{i}", f"side {index}{room_number}{i}", f"forw {index}{room_number}{i}"
                    f"radside {index}{room_number}{i}", f"radforward {index}{room_number}{i}", f"radleak {index}{room_number}{i}",
                    f"set {index}{room_number}{i}"]
                vars_to_delete = [f"vselxray {index}{room_number}{i}", f"preshvar {index}{room_number}{i}",
                    f"oworkvar {index}{room_number}{i}", f"radiob_pre {index}{room_number}{i}",
                    f"workv {index}{room_number}{i}", f"vsexroom {index}{room_number}{i}", f"setv {index}{room_number}{i}"]
                # Destroy and delete widgets
                for key in keys_to_destroy:
                    if key in self.d and self.d[key] is not None:
                        self.d[key].destroy()
                        del self.d[key]
                # Delete variables
                for var_key in vars_to_delete:
                    if var_key in self.d:
                        del self.d[var_key]

        # Update the previous number of barriers
        self.d[f"prev_num_barriers {index}{room_number}"] = num_barriers

    def barrier_sel(self, e, nr, t, i):
        radiob_w_key = f"radiob_w {e}{nr}{i}"
        barrierf_key = f"barrierf {e}{nr}"
        widget_keys = [f"leak {e}{nr}{i}", f"side {e}{nr}{i}", f"forw {e}{nr}{i}",
                    f"lau {e}{nr}{i}", f"use_ent {e}{nr}{i}", f"presh {e}{nr}{i}",f"radbucky {e}{nr}{i}", 
                    f"radcross {e}{nr}{i}", f"laks {e}{nr}{i}", f"entk {e}{nr}{i}",f"radside {e}{nr}{i}",
                    f"radforward {e}{nr}{i}",f"radleak {e}{nr}{i}",f"airkncrp {e}{nr}{i}",
                    f"unairk {e}{nr}{i}",f"othwork {e}{nr}{i}", f"radworkl {e}{nr}{i}",f"radnumb {e}{nr}{i}",
                    f"worentry {e}{nr}{i}",f"numpapwe {e}{nr}{i}", f"selxroom {e}{nr}{i}"]
        # ===== Workload Distribution =====
        self.d[f'workltit {e}{nr}{i}'] = ttk.Label(master=self.d[barrierf_key], style="BL2.TLabel",
                                                   text=f"Workload Distribution #{i + 1}:")
        self.d[f'workltit {e}{nr}{i}'].grid(row=i * 10 + 4, column=0, padx=5, pady=6.5, sticky="w")

        self.d[f"vselxray {e}{nr}{i}"] = IntVar(value=0)

        # Radio buttons for room or kVp selection
        self.create_radio_button(key=f"selxray1 {e}{nr}{i}", master=self.d[barrierf_key],
                                 text="X-Ray Room\n(Suggested NCRP 147)", variable=self.d[f"vselxray {e}{nr}{i}"],
                                 value=1, row=i * 10 + 4, column=1, command=lambda: self.XrRoom(e, nr, i))

        self.create_radio_button(key=f"selxray2 {e}{nr}{i}", master=self.d[barrierf_key], text="Give kVp",
                                 variable=self.d[f"vselxray {e}{nr}{i}"], value=2, row=i * 10 + 4, column=2,
                                 command=lambda: self.XrRoom(e, nr, i))

        # Create the checkbutton and assign the callback
        self.d[f"setv {e}{nr}{i}"] = IntVar(value=0)
        self.d[f"set {e}{nr}{i}"] = ttk.Checkbutton(master=self.d[barrierf_key], text="Set for the calculation",
                                                    variable=self.d[f"setv {e}{nr}{i}"], offvalue=0, onvalue=1,
                                                    command=lambda e=e, nr=nr, i=i: self.update_checkboxes(e, nr, i))
        self.d[f"set {e}{nr}{i}"].grid(row=i * 10 + 4, column=3, padx=5, pady=6.5, sticky="w")

        # ===== Selects Primary  =====
        if self.d[radiob_w_key].get() == 1:
            # Safely destroy previous widgets
            self.destroy_widgets(widget_keys)
            # ===== Use Factor =====
            self.d[f"lau {e}{nr}{i}"] = ttk.Label(master=self.d[barrierf_key], style="AL.TLabel", text="Use Factor:")
            self.d[f"lau {e}{nr}{i}"].grid(row=i * 10 + 3, column=2, pady=6.5, padx=5, sticky="w")
            self.d[f"use_ent {e}{nr}{i}"] = ttk.Entry(master=self.d[barrierf_key], width=10)
            self.d[f"use_ent {e}{nr}{i}"].grid(row=i * 10 + 3, column=3, pady=6.5, padx=5, sticky="w")

            # ===== Primary Unshielded Air Kerma =====
            self.d[f"laks {e}{nr}{i}"] = ttk.Label(master=self.d[barrierf_key],
                                                   text="Primary Unshielded\nAir Kerma K (mGy∙patient\u207B\u00b9):")
            self.d[f"laks {e}{nr}{i}"].grid(row=i * 10 + 6, column=0, pady=6.5, padx=5, sticky="w")
            self.d[f"entk {e}{nr}{i}"] = ttk.Entry(master=self.d[barrierf_key], width=10)
            self.d[f"entk {e}{nr}{i}"].grid(row=i * 10 + 6, column=1, pady=6.5, padx=5, sticky="w")

            # ===== Preshielding Option =====
            self.d[f"preshvar {e}{nr}{i}"] = IntVar(value=0)
            self.d[f"presh {e}{nr}{i}"] = ttk.Checkbutton(master=self.d[barrierf_key], text="Preshielding",
                                                      variable=self.d[f"preshvar {e}{nr}{i}"], offvalue=0, onvalue=1,
                                                      command=lambda: self.pres(e, nr, i))
            self.d[f"presh {e}{nr}{i}"].grid(row=i * 10 + 6, column=2, pady=6.5, padx=5, sticky="w")

        # ===== Selects Secondary =====
        elif self.d[radiob_w_key].get() == 2:
            # Safely destroy previous widgets for secondary
            self.destroy_widgets(widget_keys)
            # Create radio buttons for unshielded secondary air kerma options
            self.d[f"unairkerv {e}{nr}{i}"] = IntVar(value=0)
            self.create_radio_button(key=f"airkncrp {e}{nr}{i}", master=self.d[barrierf_key],
                text="Select Unshielded Secondary\nAir Kerma (mGy∙patient\u207B\u00b9)\nSuggested (NCRP 147)",
                variable=self.d[f"unairkerv {e}{nr}{i}"], value=1, row=i * 10 + 6, column=0,
                command=lambda: self.unairk(e, nr, i))
            self.create_radio_button(key=f"unairk {e}{nr}{i}", master=self.d[barrierf_key],
                text="Write Unshielded Secondary\nAir Kerma (mGy∙patient\u207B\u00b9)", variable=self.d[f"unairkerv {e}{nr}{i}"],
                value=2, row=i * 10 + 6, column=1, command=lambda: self.unairk(e, nr, i))
        # ===== Different Workload Option =====
        self.d[f"oworkvar {e}{nr}{i}"] = IntVar(value=0)
        self.d[f"othwork {e}{nr}{i}"] = ttk.Checkbutton(master=self.d[barrierf_key], text="Different Workload",
                                                        variable=self.d[f"oworkvar {e}{nr}{i}"], offvalue=0,
                                                        onvalue=1, command=lambda: self.owork(e, nr, i))
        self.d[f"othwork {e}{nr}{i}"].grid(row=i * 10 + 9, column=0, pady=6.5, padx=5, sticky="w")

    def update_checkboxes(self, e, nr, i):
        # Loop through all the checkboxes with the same 'e' and 'nr' but different 'i'
        for index in range(0, self.d[f"num_barriers_var {e}{nr}"].get()):  # Adjust 'some_max_value' to the range of 'i' you need
            if index != i:
                if f"setv {e}{nr}{index}" in self.d:
                    # Set all other checkbuttons' variables to 0 (unchecked)
                    self.d[f"setv {e}{nr}{index}"].set(0)

    def XrRoom(self, e, nr, i):
        # Access frequently used keys
        xray_key = f"vselxray {e}{nr}{i}"
        barrierf_key = f"barrierf {e}{nr}"
        radiob_w_key = f"radiob_w {e}{nr}{i}"
        selxroom_key = f"selxroom {e}{nr}{i}"
        vsexroom_key = f"vsexroom {e}{nr}{i}"

        if self.d[xray_key].get() == 1:
            # Destroy existing widget if it exists
            if self.d.get(selxroom_key):
                self.d[selxroom_key].destroy()
            # Define options for X-ray room
            self.xrooms = ("Rad Room (chest bucky)", "Rad Room (floor or other barriers)", "Rad Room (all barriers)",
                           "Fluoroscopy Tube (R&F room)", "Rad Tube (R&F room)", "Chest Room", "Mammography Room",
                           "Cardiac Angiography", "Peripheral Angiography")
            self.d[vsexroom_key] = StringVar()
            self.d[selxroom_key] = ttk.OptionMenu(self.d[barrierf_key], self.d[vsexroom_key], "Select X-ray room",
                                                  *self.xrooms, command=lambda value: self.uns(e, nr, i))
            self.d[selxroom_key].grid(row=i * 10 + 5, column=1, columnspan=2, pady=6.5, padx=5, sticky="w")


        elif self.d[xray_key].get() == 2:
            # Destroy existing widget if it exists
            if self.d.get(selxroom_key):
                self.d[selxroom_key].destroy()

            if self.d[radiob_w_key].get() == 1:
                # Define spinbox for kVp values for primary barrier
                self.d[vsexroom_key] = IntVar(value=25)
                self.d[selxroom_key] = ttk.Spinbox(master=self.d[barrierf_key], from_=25, to=150, increment=5,
                                                   textvariable=self.d[vsexroom_key], width=10)
                self.d[selxroom_key].grid(row=i * 10 + 5, column=2, columnspan=2, pady=6.5, padx=5, sticky="w")


            elif self.d[radiob_w_key].get() == 2:
                # Custom Spinbox for secondary barrier
                def increment_spinbox(spinbox, values):
                    current_value = int(spinbox.get())
                    current_index = values.index(current_value)
                    new_index = current_index
                    if 0 <= new_index < len(values):
                        spinbox.set(values[new_index])

                custom_values = [30, 50, 70, 100, 125, 150]
                self.d[vsexroom_key] = IntVar(value=custom_values[0])
                self.d[selxroom_key] = ttk.Spinbox(master=self.d[barrierf_key], values=custom_values,
                                                   textvariable=self.d[vsexroom_key], width=10)
                self.d[selxroom_key].bind("<<Increment>>",
                                          lambda e: increment_spinbox(self.d[selxroom_key], custom_values))
                self.d[selxroom_key].bind("<<Decrement>>",
                                          lambda e: increment_spinbox(self.d[selxroom_key], custom_values))
                self.d[selxroom_key].grid(row=i * 10 + 5, column=2, columnspan=2, pady=6.5, padx=5, sticky="w")

    def uns(self, e, nr, i):
        if self.d[f"radiob_w {e}{nr}{i}"].get() == 1:
            # =========== Unshielded Air Kerma ============
            rad_rooms = ["Rad Room (chest bucky)", 'Rad Room (floor or other barriers)', 'Rad Tube (R&F Room)',
                         'Chest Room']
            vsexroom_key = f"vsexroom {e}{nr}{i}"
            entk_key = f"entk {e}{nr}{i}"  # Key for the unshielded air kerma entry field
            if self.d[vsexroom_key].get() in rad_rooms:
                # Clear the existing entry data before inserting new values
                if entk_key in self.d:
                    self.d[entk_key].delete(0, 'end')
                    # Insert predefined values into the entry widget based on the selected room
                    if self.d[vsexroom_key].get() == "Rad Room (chest bucky)":
                        self.d[entk_key].insert(0, "2.3")
                    elif self.d[vsexroom_key].get() == "Rad Room (floor or other barriers)":
                        self.d[entk_key].insert(0, "5.2")
                    elif self.d[vsexroom_key].get() == "Rad Tube (R&F Room)":
                        self.d[entk_key].insert(0, "5.9")
                    elif self.d[vsexroom_key].get() == "Chest Room":
                        self.d[entk_key].insert(0, "1.2")
            else:
                self.d[entk_key].delete(0, 'end')
            use_ent_key = f"use_ent {e}{nr}{i}"  # Key for the use entry
            if e == 1:
                if self.d.get(f"selxroom {e}{nr}{i}"):
                    self.d[use_ent_key].delete(0, 'end')
                    if self.d[vsexroom_key].get() == "Rad Room (floor or other barriers)":
                        self.d[use_ent_key].insert(0, str(0.89))
                    else:
                        self.d[use_ent_key].insert(0, str(1))
            elif e == 2:
                self.d[use_ent_key].delete(0, 'end')
                self.d[use_ent_key].insert(0, str(1 / 16))
            else:
                if self.d.get(f"selxroom {e}{nr}{i}"):
                    self.d[use_ent_key].delete(0, 'end')
                    if self.d[vsexroom_key].get() == "Rad Room (floor or other barriers)":
                        self.d[use_ent_key].insert(0, str(0.02))
                    else:
                        self.d[use_ent_key].insert(0, str(1 / 4))

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
                        self.d[f"mater {e}{self.d[m_key]}"].grid(row=10, column=-1 + self.d[m_key], pady=6.5, padx=25,
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
                    # Create the option menu for materials
                    self.d[f"mater {e}{self.d[m_key]}"] = ttk.OptionMenu(self.d[f"barrierf {e}{nr}"],
                                                                         self.d[f"vmater {e}{self.d[m_key]}{nr}"],
                                                                         "Select Material", *self.mater)
                    # Create label for the material entry
                    self.d[f"matlab {e}{self.d[m_key]}"] = ttk.Label(self.d[f"barrierf {e}{nr}"],
                                                                     text=f"#{self.d[m_key]}:")
                    # Grid placement logic
                    if self.d[m_key] <= 3:
                        row, col = 100, -1 + self.d[m_key]
                    else:
                        row, col = 101, -4 + self.d[m_key]
                    # Grid the label and option menu
                    self.d[f"matlab {e}{self.d[m_key]}"].grid(row=row, column=col, sticky="w")
                    self.d[f"mater {e}{self.d[m_key]}"].grid(row=row, column=col, padx=20, pady=6.5, sticky="e")
            # Destroy extra widgets if material count exceeds the required number
            else:
                while self.d[m_key] > self.d[vnumbmat_key].get():
                    self.d[f"mater {e}{self.d[m_key]}"].destroy()
                    self.d[f"matlab {e}{self.d[m_key]}"].destroy()
                    self.d[m_key] -= 1

    def pres(self, e, nr, i):
        preshvar_key = f"preshvar {e}{nr}{i}"
        radbucky_key = f"radbucky {e}{nr}{i}"
        radcross_key = f"radcross {e}{nr}{i}"
        radiob_pre_key = f"radiob_pre {e}{nr}{i}"  # Unique key for radiob_pre
        self.d[radiob_pre_key] = IntVar(value=0)  # Store IntVar in dictionary
        # Check if preshielding is selected (1)
        if self.d[preshvar_key].get() == 1:
            # Create and place the 'Bucky' Radiobutton
            self.d[radbucky_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"], variable=self.d[radiob_pre_key],
                                                   text="Bucky", value=1)
            self.d[radbucky_key].grid(row=i * 10 + 6, column=3, pady=6.5, padx=5, sticky="w")
            # Create and place the 'Cross-table' Radiobutton
            self.d[radcross_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"], variable=self.d[radiob_pre_key],
                                                   text="Cross-table", value=2)
            self.d[radcross_key].grid(row=i * 10 + 6, column=4, pady=6.5, padx=5, sticky="w")
        # If preshielding is deselected (0), destroy the widgets if they exist
        elif self.d[preshvar_key].get() == 0:
            if radbucky_key in self.d and self.d[radbucky_key] is not None:
                self.d[radbucky_key].destroy()
            if radcross_key in self.d and self.d[radcross_key] is not None:
                self.d[radcross_key].destroy()

    def owork(self, e, nr, i):
        work_key = f"oworkvar {e}{nr}{i}"
        radwork_key = f"radworkl {e}{nr}{i}"
        radnumb_key = f"radnumb {e}{nr}{i}"  # Corrected key for the second radiobutton
        workv_key = f"workv {e}{nr}{i}"  # Unique key for radiob_pre
        radiob_w_key = f"radiob_w {e}{nr}{i}"
        self.d[workv_key] = IntVar(value=0)  # Store IntVar in dictionary
        # Check if the workload option is selected (1)
        if self.d[work_key].get() == 1:
            # Create the 'Write total Workload' Radiobutton
            self.d[radwork_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"], variable=self.d[workv_key],
                                                  text="Write total\nWorkload (mA∙min∙week\u207B\u00b9):", value=1,
                                                  command=lambda: self.workloadbar(e, nr, i))
            # Create the 'Number of Patients' Radiobutton
            self.d[radnumb_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"], variable=self.d[workv_key],
                                                  text="The Number of\nPatients per week:", value=2,
                                                  command=lambda: self.workloadbar(e, nr, i))
            #place them
            self.d[radwork_key].grid(row=i * 10 + 9, column=1, pady=6.5, padx=5, sticky="w")
            self.d[radnumb_key].grid(row=i * 10 + 9, column=3, pady=6.5, padx=5, sticky="w")
        # If workload is deselected (0), destroy the widgets if they exist
        elif self.d[work_key].get() == 0:
            if radwork_key in self.d and self.d[radwork_key] is not None:
                self.d[radwork_key].destroy()
            if radnumb_key in self.d and self.d[radnumb_key] is not None:
                self.d[radnumb_key].destroy()

    def workloadbar(self, e, nr, i):
        def destroy_widget(widget_key):
            if self.d.get(widget_key) is not None:
                self.d[widget_key].destroy()
        # Widget keys
        worebar_key = f"worentry {e}{nr}{i}"
        numpapwebar_key = f"numpapwe {e}{nr}{i}"
        vraworkbar_key = f"workv {e}{nr}{i}"
        radiob_w_key = f"radiob_w {e}{nr}{i}"
        # Get the value for workload type
        workload_type = self.d[vraworkbar_key].get()
        # Handle workload "Total workload"
        if workload_type == 1:
            destroy_widget(numpapwebar_key)  # Destroy patient entry if it exists
            destroy_widget(worebar_key)
            self.d[worebar_key] = ttk.Entry(master=self.d[f"barrierf {e}{nr}"], width=10)
            self.d[worebar_key].grid(row=i * 10 + 9, column=2, pady=5, padx=5, sticky="w")
        # Handle workload "Number of Patients"
        elif workload_type == 2:
            destroy_widget(worebar_key)  # Destroy workload entry if it exists
            destroy_widget(numpapwebar_key)
            self.d[numpapwebar_key] = ttk.Entry(master=self.d[f"barrierf {e}{nr}"], width=10)
            self.d[numpapwebar_key].grid(row=i * 10 + 9, column=4, pady=5, padx=5, sticky="w")

    def unairk(self, e, nr, i):
        # Destroy any existing widgets related to secondary barrier
        self.destroy_widgets([f"leak {e}{nr}{i}", f"side {e}{nr}{i}", f"forw {e}{nr}{i}", f"entk {e}{nr}{i}"])
        if f"radside {e}{nr}{i}" in self.d:
            self.destroy_widgets([f"radside {e}{nr}{i}", f"radforward {e}{nr}{i}", f"radleak {e}{nr}{i}"])
        unairkerv_key = f"unairkerv {e}{nr}{i}"

        if self.d[unairkerv_key].get() == 1:
            # NCRP-suggested mode: create radio buttons for different types of scatter/leakage
            self.d[f"airkerv {e}{nr}{i}"] = IntVar(value=0)

            self.create_radio_button(key=f"leak {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"],
                text="Leakage Radiation", variable=self.d[f"airkerv {e}{nr}{i}"], value=1, row=i * 10 + 7, column=0,
                command=lambda: self.leakage(e, nr, i))

            self.create_radio_button(key=f"side {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"], text="Side-Scatter",
                variable=self.d[f"airkerv {e}{nr}{i}"], value=2, row=i * 10 + 7, column=1,
                command=lambda: self.leakage(e, nr, i))

            self.create_radio_button(key=f"forw {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"],
                text="Forward/Backscatter", variable=self.d[f"airkerv {e}{nr}{i}"], value=3, row=i * 10 + 7, column=2,
                command=lambda: self.leakage(e, nr, i))

        elif self.d[unairkerv_key].get() == 2:
            # Custom input mode: create entry for secondary air kerma
            self.d[f"entk {e}{nr}{i}"] = ttk.Entry(master=self.d[f"barrierf {e}{nr}"], width=10)
            self.d[f"entk {e}{nr}{i}"].grid(row=i * 10 + 6, column=2, pady=6.5, padx=5, sticky="w")

    def leakage(self, e, nr, i):
        airkerv_key = f"airkerv {e}{nr}{i}"
        radiob_leak_key = f"radiob_leak {e}{nr}{i}"

        # Destroy any previously created widgets
        self.destroy_widgets([f"radside {e}{nr}{i}", f"radforward {e}{nr}{i}", f"radleak {e}{nr}{i}"])

        # Check the current selection and create the corresponding radio buttons
        if self.d[airkerv_key].get() == 1:  # Leakage and side-scatter
            self.d[radiob_leak_key] = IntVar(value=0)
            self.create_radio_button(key=f"radside {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"],
                text="Leakage and Side-Scatter", variable=self.d[radiob_leak_key], value=1, row=i * 10 + 8, column=0)
            self.create_radio_button(key=f"radforward {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"],
                text="Leakage and Forward/Backscatter", variable=self.d[radiob_leak_key], value=2, row=i * 10 + 8,
                column=1)
            self.create_radio_button(key=f"radleak {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"], text="Only Leakage",
                variable=self.d[radiob_leak_key], value=0, row=i * 10 + 8, column=2)

    def _add_xray_room_additional_widgets(self, index, room_number, t):
        """Add additional widgets for X-ray room."""
        self.title_ocupat = ttk.Label(
            master=self.d[f"barrierf {index}{room_number}"], style="BL.TLabel",
            text="Shielding Area")
        self.title_ocupat.grid(row=104, column=0, pady=6.5, padx=5, sticky="w")
        self.d[f"area {index}{room_number}"] = StringVar()
        self.d[f"area {index}{room_number}"] = ttk.Combobox(
            master=self.d[f"barrierf {index}{room_number}"],
            textvariable=self.d[f"area {index}{room_number}"],
            values=["Controlled Area", "Uncontrolled Area", "Supervised Area"], state="readonly")
        self.d[f"area {index}{room_number}"].grid(row=104, column=1, sticky="w")
        self.d[f"area {index}{room_number}"].set("Classify the area")

        self.d[f"vraoccup {index}{room_number}"] = IntVar(value=0)
        self.raoccup = ttk.Radiobutton(
            master=self.d[f"barrierf {index}{room_number}"],
            variable=self.d[f"vraoccup {index}{room_number}"], text="Write occupancy factor (T):",
            value=1, command=lambda e=index, nr=room_number: self.occupation3(e, nr, t))
        self.raoccup.grid(row=105, column=0, pady=6.5, padx=5, sticky="w")

        self.raseloccup = ttk.Radiobutton(
            master=self.d[f"barrierf {index}{room_number}"],
            text="or select Location\n(Suggested NCRP 147)",
            variable=self.d[f"vraoccup {index}{room_number}"], value=2,
            command=lambda e=index, nr=room_number: self.occupation3(e, nr, t))
        self.raseloccup.grid(row=106, column=0, pady=6.5, padx=5, sticky="w")

        self.ladike = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                                text="Shielding Design\nGoal (mGy∙week\u207B\u00b9):")
        self.ladike.grid(row=107, column=0, pady=6.5, padx=5, sticky="w")
        self.d[f"dikeent {index}{room_number}"] = ttk.Entry(master=self.d[f"barrierf {index}{room_number}"], width=10)
        self.d[f"dikeent {index}{room_number}"].grid(row=107, column=1, pady=6.5, padx=5, sticky="w")

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
        self.d[dikeent_key].grid(row=107, column=1, pady=6.5, padx=5, sticky="w")

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
            self.d[occupentry_key].grid(row=105, column=1, pady=6.5, padx=5)
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
                locations = ("Administrative or clerical offices", "Laboratories",
                                "Pharmacies and other work areas fully occupied by an individual", "Receptionist areas",
                                "Attended waiting rooms", "Children’s indoor play areas", "Adjacent x-ray rooms",
                                "Film reading areas", "Nurse’s stations", "X-ray control rooms",
                                "Rooms used for patient examinations and treatments")
                self.d[dikeent_key].insert(0, str(0.01))
            elif self.d[area_key].get() == "Uncontrolled Area":
                locations = ("Public toilets", "Unattended vending areas", "Storage  rooms", "Outdoor areas with seating",
                "Unattended waiting rooms", "Patient holding areas",
                "Outdoor areas with only transient pedestrian or vehicular traffic", "Unattended parking lots",
                "Vehicular drop off areas (unattended)", "Attics", "Stairways", "Unattended elevators",
                "Janitor’s closets")
                self.d[dikeent_key].insert(0, str(0.006))
            elif self.d[area_key].get() == "Supervised Area":
                locations = ("Corridors", "Patient rooms", "Employee lounges", "Staff restooms", "Corridor doors")
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
            self.d[sellocation_key].grid(row=106, column=1, pady=6.5, padx=5, sticky="w")
            self.d[sellocation_key].config(width=15)

    def existbarrier(self, e,nr,t):
        if self.d["existvar " + str(e)+nr].get() == 1:
            if self.d["existla " + str(e) + nr] is not None:
                self.d["existla " + str(e) + nr].destroy()
                self.d["existmat " + str(e) + nr].destroy()
                self.d["materex " + str(e) + nr].destroy()
            self.d["existla "+str(e)+nr] \
                = ttk.Label(master=self.d["barrierf " + str(e)+nr], style="AL.TLabel",
                                                             text="Existing Barrier in mm:")
            self.d["existla " + str(e)+nr].grid(row=6, column=0, pady=6.5, padx=5, sticky="w")
            self.d["existmat "+str(e)+nr] \
                = ttk.Entry(master=self.d["barrierf " + str(e)+nr], width=10)
            self.d["existmat " + str(e)+nr].grid(row=6, column=1, pady=6.5, padx=5, sticky="w")

            self.d["vmaterex "+str(e)+nr] = StringVar()
            self.d["materex "+str(e)+nr] \
                = ttk.OptionMenu(self.d["barrierf " + str(e)+nr],
                self.d["vmaterex "+str(e)+nr], "Select Material", *self.mater)
            self.d["materex " + str(e)+nr].grid(row=7, column=0, pady=6.5, padx=5, sticky="w")
        elif self.d["existvar " + str(e)+nr].get() == 0:
            if self.d["existla " + str(e)+nr] is not None:
                self.d["existla " + str(e)+nr].destroy()
                self.d["existmat " + str(e)+nr].destroy()
                self.d["materex " + str(e)+nr].destroy()

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