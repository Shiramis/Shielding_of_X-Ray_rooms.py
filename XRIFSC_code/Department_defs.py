import tkinter
import subprocess
from tkinter import *
from tkinter import ttk
from XRIFSC_code.Department import ddepartment
from idlelib.tooltip import Hovertip

class dep_defs(ddepartment):

    def barriers(self, t):
        current_barriers = self.d[f"x {t}"]
        max_barriers = self.var[f"vnumwall {t}"].get()
        room_number = self.d[f"nr {t}"]

        def initialize_barrier(index):
            """Initialize values and widgets for a barrier."""
            self.thm[f"xbar {index}{room_number}"] = 0
            self.xlmat[f"thic {index}{room_number}"] = 0

            self.d[f"barrierf {index}{room_number}"] = ttk.Frame(self.d[f"noteb {t}{room_number}"], width=190)
            self.d[f"barrierf {index}{room_number}"].pack()
            self.d[f"barrierf {index}{room_number}"].bind("<MouseWheel>", lambda event: self.on_vertical_scroll(event, t))
            self.d[f"barrierf {index}{room_number}"].bind("<Shift-MouseWheel>", lambda event: self.on_horizontal_scroll(event, t))

            if index <= 3:
                labels = ["Floor", "Ceiling", "Door"]
                self.barn[f"lab_bar {index}{room_number}"] = Label(text=labels[index - 1])
            else:
                self.barn[f"lab_bar {index}{room_number}"] = Label(text=f"Barrier {index - 3}")

            self.d[f"noteb {t}{room_number}"].add(self.d[f"barrierf {index}{room_number}"],
                                                  text=self.barn[f"lab_bar {index}{room_number}"].cget("text"))

            self.barr[self.barn[f"lab_bar {index}{room_number}"].cget("text")] = 0

            # Select Materials label
            self.d[f"matlab {index}{room_number}"] = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                                    text="Select Materials:")
            rowm = 8 if self.var[f"vselroom {t}"].get() == "CT Room" else 99

            self.d[f"matlab {index}{room_number}"].grid(row=rowm, column=0, padx=5, pady=6.5, sticky="w")

            # Add spinbox for number of materials
            self.var[f"vnumbmat {index}{room_number}"] = IntVar(value=1)
            spinbox_max = 2 if self.var[f"vselroom {t}"].get() == "CT Room" else 6
            self.d[f"numbmat {index}{room_number}"] = ttk.Spinbox(master=self.d[f"barrierf {index}{room_number}"],
                from_=1, to=spinbox_max, width=5, textvariable=self.var[f"vnumbmat {index}{room_number}"], state= 'readonly',
                command=lambda e=index, nr=room_number: self.numbmater(e, nr, t))
            self.d[f"numbmat {index}{room_number}"].grid(row=rowm, column=1, padx=5, pady=6.5, sticky="w")

            # Add widgets based on room type
            if self.var[f"vselroom {t}"].get() == "CT Room":
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
            self.destroy_widgets([barrier_frame_key,label_B_key,radpw_key,radsw_key])
            current_barriers -= 1

        # Update the number of barriers
        self.d[f"x {t}"] = current_barriers

        # Adjust grid based on the number of barriers and room type
        if self.var[f"vselroom {t}"].get() == "CT Room":
            self.d[f"noteb {t}{room_number}"].grid(row=0, column=2, rowspan=10, columnspan=current_barriers, pady=6.5,
                                                   padx=5, sticky="wn")
        else:
            self.d[f"noteb {t}{room_number}"].grid(row=4, column=0, rowspan=10, columnspan=current_barriers, pady=6.5,
                                                   padx=5, sticky="wn")

    def _add_xray_room_widgets(self, index, room_number, t):
        """Add X-ray room specific widgets."""
        # Label to indicate number of radiation types on the barrier
        labb = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                         text="Select the number of types\nof radiation on the barrier:")
        labb.grid(row=0, column=0, pady=6.5, padx=5, sticky="w")

        # Initialize tracking of the previous number of barriers
        self.d[f"prev_num_barriers {index}{room_number}"] = 0

        # Spinbox for the number of barriers
        self.var[f"num_barriers_var {index}{room_number}"] = IntVar(value=1)  # Default to 1
        self.d[f"num_barriers_spinbox {index}{room_number}"] = ttk.Spinbox(
            master=self.d[f"barrierf {index}{room_number}"], width=5, from_=1, to=8, increment=1,
            textvariable=self.var[f"num_barriers_var {index}{room_number}"],
            command=lambda e=index, nr=room_number: self._create_barrier_widgets(e, nr, t))
        self.d[f"num_barriers_spinbox {index}{room_number}"].grid(row=0, column=1, pady=6.5, padx=5, sticky="w")
        self._create_barrier_widgets(index, room_number, t)
        # Area classification and occupancy factor
        self.occup_design(index, room_number, t)

        self.d[f"calbutton {index}{room_number}"] = ttk.Button(master=self.d[f"barrierf {index}{room_number}"],text="Calculate",
              command=lambda e=index, nr=room_number: self.choosetype(e, nr, t))
        self.d[f"calbutton {index}{room_number}"].grid(row=107, column=2, pady=6.5, padx=5, sticky="w")

    def _create_barrier_widgets(self, index, room_number, t):
        """Dynamically create or delete barrier-related widgets based on the selected number in the Spinbox."""
        num_barriers = self.var[f"num_barriers_var {index}{room_number}"].get()
        prev_num_barriers = self.d[f"prev_num_barriers {index}{room_number}"]

        if num_barriers > prev_num_barriers:
            # Create widgets for the new barriers
            for i in range(prev_num_barriers, num_barriers):
                # Label for barrier type
                self.d[f"label_B {index}{room_number}{i}"] = ttk.Label(master=self.d[f"barrierf {index}{room_number}"],
                    style="BL2.TLabel", text=f"Select Radiation Type #{i + 1}:")
                self.d[f"label_B {index}{room_number}{i}"].grid(row=i * 10 + 1, column=0, pady=6.5, padx=5, sticky="w")

                self.var[f"radiob_w {index}{room_number}{i}"] = IntVar(value=0)
                # Primary Barrier Radiobutton
                self.create_radio_button(key= f"radpw {index}{room_number}{i}", master=self.d[f"barrierf {index}{room_number}"],
                    variable=self.var[f"radiob_w {index}{room_number}{i}"], text=f"Primary", value=1, row=i * 10 + 1, column=1,
                    command=lambda e=index, nr=room_number: self.barrier_sel(e, nr, t, i))
                # Secondary Barrier Radiobutton
                self.create_radio_button(key=f"radsw {index}{room_number}{i}",
                    master=self.d[f"barrierf {index}{room_number}"],variable=self.var[f"radiob_w {index}{room_number}{i}"],
                    text=f"Secondary", value=2, row=i * 10 + 1, column=2,
                    command=lambda e=index, nr=room_number: self.barrier_sel(e, nr, t, i))

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
                    f"unairk {index}{room_number}{i}",f"leak {index}{room_number}{i}", f"side {index}{room_number}{i}", f"forw {index}{room_number}{i}",
                    f"radside {index}{room_number}{i}", f"radforward {index}{room_number}{i}", f"radleak {index}{room_number}{i}",
                    f"set {index}{room_number}{i}", f"Ksec {index}{room_number}{i}", f"Kleak {index}{room_number}{i}", f"Kscat {index}{room_number}{i}",
                    f"entk {index}{room_number}{i}", f"lad {index}{room_number}{i}",f"labelk {index}{room_number}{i}", f"entryd {index}{room_number}{i}"]
                vars_to_delete = [f"vselxray {index}{room_number}{i}", f"preshvar {index}{room_number}{i}",
                    f"radiob_pre {index}{room_number}{i}",f"workv {index}{room_number}{i}", 
                    f"vsexroom {index}{room_number}{i}", f"setv {index}{room_number}{i}",f"unsecair {index}{room_number}{i}"]
                # Destroy and delete widgets
                self.destroy_widgets(keys_to_destroy)
                # Delete variables
                self.destroy_widgets(vars_to_delete)

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
                    f"worentry {e}{nr}{i}",f"numpapwe {e}{nr}{i}", f"selxroom {e}{nr}{i}", f"Ksec {e}{nr}{i}",
                   f"Kleak {e}{nr}{i}", f"Kscat {e}{nr}{i}", f"entk {e}{nr}{i}", f"lad {e}{nr}{i}",
                   f"labelk {e}{nr}{i}", f"entryd {e}{nr}{i}"]
        # ===== Workload Distribution =====
        self.d[f'workltit {e}{nr}{i}'] = ttk.Label(master=self.d[barrierf_key], style="BL2.TLabel",
                                                   text=f"Workload Distribution #{i + 1}:")
        self.d[f'workltit {e}{nr}{i}'].grid(row=i * 10 + 2, column=0, padx=5, pady=6.5, sticky="w")

        self.var[f"vselxray {e}{nr}{i}"] = IntVar(value=0)

        # Radio buttons for room or kVp selection
        self.create_radio_button(key=f"selxray1 {e}{nr}{i}", master=self.d[barrierf_key],
                                 text="X-Ray Room", variable=self.var[f"vselxray {e}{nr}{i}"],
                                 value=1, row=i * 10 + 2, column=1, command=lambda: self.XrRoom(e, nr, i))

        self.create_radio_button(key=f"selxray2 {e}{nr}{i}", master=self.d[barrierf_key], text="Tube Voltage kVp",
                                 variable=self.var[f"vselxray {e}{nr}{i}"], value=2, row=i * 10 + 2, column=2,
                                 command=lambda: self.XrRoom(e, nr, i))

        # Create the checkbutton and assign the callback
        self.var[f"setv {e}{nr}{i}"] = IntVar(value=0)
        self.d[f"set {e}{nr}{i}"] = ttk.Checkbutton(master=self.d[barrierf_key], text="Set this distribution\n"
                                                                                      "to calculate the thickness x",
                                                    variable=self.var[f"setv {e}{nr}{i}"], offvalue=0, onvalue=1,
                                                    command=lambda e=e, nr=nr, i=i: self.update_checkboxes(e, nr, i))
        self.d[f"set {e}{nr}{i}"].grid(row=i * 10 + 2, column=3, padx=5, pady=6.5, sticky="w")
        self.var[f'workdistt {e}{nr}{i}'] = Hovertip(self.d[f"set {e}{nr}{i}"], text="Set this distribution\n"
                                                                                      "fitting parameters (α, β, γ)\n"
                                                                                      "for transmision to calculate\n"
                                                                                      "the thickness x in mm\n"
                                                                                     "(Table A.1 or B.1 of NCRP 147)")
        # ===== Selects Primary  =====
        if self.var[radiob_w_key].get() == 1:
            # Safely destroy previous widgets
            self.destroy_widgets(widget_keys)
            # ===== Primary Unshielded Air Kerma =====
            self.d[f"laks {e}{nr}{i}"] = ttk.Label(master=self.d[barrierf_key],
                                                   text="Unshielded Primary\nAir Kerma K (mGy∙patient\u207B\u00b9):")
            self.d[f"laks {e}{nr}{i}"].grid(row=i * 10 + 4, column=0, pady=6.5, padx=5, sticky="w")
            self.ent[f"entk {e}{nr}{i}"] = ttk.Entry(master=self.d[barrierf_key], width=10)
            self.ent[f"entk {e}{nr}{i}"].grid(row=i * 10 + 4, column=1, pady=6.5, padx=5, sticky="w")
            # ===== Preshielding Option =====
            self.var[f"preshvar {e}{nr}{i}"] = IntVar(value=0)
            self.d[f"presh {e}{nr}{i}"] = ttk.Checkbutton(master=self.d[barrierf_key], text="Preshielding",
                                                      variable=self.var[f"preshvar {e}{nr}{i}"], offvalue=0, onvalue=1,
                                                      command=lambda: self.pres(e, nr, i))
            self.d[f"presh {e}{nr}{i}"].grid(row=i * 10 + 6, column=2, pady=6.5, padx=5, sticky="w")
            # ===== Primary Distance ========
            self.d[f'lad {e}{nr}{i}'] = ttk.Label(master=self.d[barrierf_key],
                                                               style="AL.TLabel",
                                                               text="Primary distance (d\u209A)\nto the Barrier (m):")
            self.d[f'lad {e}{nr}{i}'].grid(row=i * 10 + 8, column=0, pady=6.5, padx=5, sticky="w")
            self.ent[f"entryd {e}{nr}{i}"] = ttk.Entry(master=self.d[barrierf_key], width=10)
            self.ent[f"entryd {e}{nr}{i}"].grid(row=i * 10 + 8, column=1, pady=6.5, padx=5, sticky="w")
            # ===== Use Factor =====
            self.d[f"lau {e}{nr}{i}"] = ttk.Label(master=self.d[barrierf_key], style="AL.TLabel", text="Use Factor:")
            self.d[f"lau {e}{nr}{i}"].grid(row=i * 10 + 6, column=0, pady=6.5, padx=5, sticky="w")
            self.ent[f"use_ent {e}{nr}{i}"] = ttk.Entry(master=self.d[barrierf_key], width=10)
            self.ent[f"use_ent {e}{nr}{i}"].grid(row=i * 10 + 6, column=1, pady=6.5, padx=5, sticky="w")
            #============= tips ==============
            self.set_distance_tips(e,nr,i)
            self.var[f"pretip {e}{nr}{i}"] = Hovertip(self.d[f"presh {e}{nr}{i}"], text= 'Table 4.6 of NCRP 147')
            self.var[f"usetip {e}{nr}{i}"] = Hovertip(self.d[f"lau {e}{nr}{i}"], text= "Table 4.4 of NCRP 147")
        # ===== Selects Secondary =====
        elif self.var[radiob_w_key].get() == 2:
            # Safely destroy previous widgets for secondary
            self.destroy_widgets(widget_keys)
            self.destroy_widgets([f'workdistt {e}{nr}{i}'])
            # Create radio buttons for unshielded secondary air kerma options
            self.var[f'workdistt {e}{nr}{i}'] = Hovertip(self.d[f"set {e}{nr}{i}"], text="Set this distribution\n"
                                                                                      "fitting parameters (α, β, γ)\n"
                                                                                      "for transmision to calculate\n"
                                                                                      "the thickness x in mm\n"
                                                                                    "(Table C.1 of NCRP 147)")
            self.var[f"unairkerv {e}{nr}{i}"] = IntVar(value=0)
            self.create_radio_button(key=f"unairk {e}{nr}{i}", master=self.d[barrierf_key],
                text="Write Unshielded\nAir Kerma (mGy∙patient\u207B\u00b9)", variable=self.var[f"unairkerv {e}{nr}{i}"],
                value=2, row=i * 10 + 4, column=0, command=lambda: self.unairk(e, nr, i))

    def workloadbar(self, e, nr, i):
        # Widget keys
        worebar_key = f"worentry {e}{nr}{i}"
        numpapwebar_key = f"numpapwe {e}{nr}{i}"
        vraworkbar_key = f"workv {e}{nr}{i}"
        # Get the value for workload type
        workload_type = self.var[vraworkbar_key].get()
        # Handle workload "Total workload"
        if workload_type == 1:
            self.destroy_widgets([numpapwebar_key, worebar_key])  # Destroy patient entry if it exists
            self.d[worebar_key] = ttk.Entry(master=self.d[f"barrierf {e}{nr}"], width=10)
            self.d[worebar_key].grid(row=i * 10 + 9, column=4, pady=5, padx=5, sticky="w")
            self.var[f"workloadtip2 {e}{nr}{i}"] = Hovertip(self.d[worebar_key], text="Table 4.3 of NCRP 147")
        # Handle workload "Number of Patients"
        elif workload_type == 2:
            self.destroy_widgets([worebar_key, numpapwebar_key,f"workloadtip2 {e}{nr}{i}"])  # Destroy workload entry if it exists
            self.d[numpapwebar_key] = ttk.Entry(master=self.d[f"barrierf {e}{nr}"], width=10)
            self.d[numpapwebar_key].grid(row=i * 10 + 9, column=2, pady=5, padx=5, sticky="w")

    def XrRoom(self, e, nr, i):
        # Access frequently used keys
        xray_key = f"vselxray {e}{nr}{i}"
        barrierf_key = f"barrierf {e}{nr}"
        radiob_w_key = f"radiob_w {e}{nr}{i}"
        selxroom_key = f"selxroom {e}{nr}{i}"
        vsexroom_key = f"vsexroom {e}{nr}{i}"
        # ===== Workload ======
        self.d[f"othwork {e}{nr}{i}"] = ttk.Label(master=self.d[barrierf_key], text="Workload:", style="AL.TLabel")
        self.d[f"othwork {e}{nr}{i}"].grid(row=i * 10 + 9, column=0, pady=6.5, padx=5, sticky="w")
        self.var[f"workv {e}{nr}{i}"] = IntVar(value=0)

        # Create the 'Number of Patients' Radiobutton
        self.create_radio_button(key=f"radnumb {e}{nr}{i}", master=self.d[barrierf_key],
                                 variable=self.var[f"workv {e}{nr}{i}"], text="The Number of\nPatients per week:",
                                 value=2, row=i * 10 + 9, column=1, command=lambda: self.workloadbar(e, nr, i))
        if self.var[xray_key].get() == 1: # X-Ray rooms
            # Destroy existing widget if it exists
            self.destroy_widgets([selxroom_key, f'workdistt {e}{nr}{i}',f"radworkl {e}{nr}{i}",
                                  f"workloadtip1 {e}{nr}{i}",f"worentry {e}{nr}{i}"])
            if self.var[radiob_w_key].get() == 2: #Secondary
                self.create_radio_button(key=f"airkncrp {e}{nr}{i}", master=self.d[barrierf_key],
                                     text="Select Unshielded Secondary\nAir Kerma K (mGy∙patient\u207B\u00b9)\nSuggested (NCRP 147)",
                                     variable=self.var[f"unairkerv {e}{nr}{i}"], value=1, row=i * 10 + 4, column=2,
                                     command=lambda: self.unairk(e, nr, i))
                #tips
                self.var[f"roomstbl {e}{nr}{i}"] = Hovertip(self.d[f"airkncrp {e}{nr}{i}"], 'Table 4.7 of NCRP 147')
            elif self.var[radiob_w_key].get() == 1:# Primary
                self.var[f'workdistt {e}{nr}{i}'] = Hovertip(self.d[f"set {e}{nr}{i}"], text="Set this distribution\n"
                                                                                      "fitting parameters (α, β, γ)\n"
                                                                                      "for transmision to calculate\n"
                                                                                      "the thickness x in mm\n"
                                                                                    "(Table B.1 of NCRP 147)")
            # Define options for X-ray room
            self.xrooms = ("Rad Room (chest bucky)", "Rad Room (floor or other barriers)", "Rad Room (all barriers)",
                           "Fluoroscopy Tube (R&F room)", "Rad Tube (R&F room)", "Chest Room", "Mammography Room",
                           "Cardiac Angiography", "Peripheral Angiography")
            self.var[vsexroom_key] = StringVar()
            self.d[selxroom_key] = ttk.OptionMenu(self.d[barrierf_key], self.var[vsexroom_key], "Select X-ray room",
                                                  *self.xrooms, command=lambda value: self.uns(e, nr, i))
            self.d[selxroom_key].grid(row=i * 10 + 3, column=1, pady=6.5, padx=5, sticky="w")
            # Create the 'Write total Workload' Radiobutton
            self.create_radio_button(key=f"radworkl {e}{nr}{i}", master=self.d[barrierf_key],
                                     variable=self.var[f"workv {e}{nr}{i}"],
                                     text="Write total\nWorkload (mA∙min∙week\u207B\u00b9):", value=1, row=i * 10 + 9,
                                     column=3, command=lambda: self.workloadbar(e, nr, i))
            self.var[f"workloadtip1 {e}{nr}{i}"] = Hovertip(self.d[f"radworkl {e}{nr}{i}"], text = "Table 4.3 of NCRP 147")
        elif self.var[xray_key].get() == 2: # Tube Voltage
            # Destroy existing widget if it exists
            self.destroy_widgets([selxroom_key, f"airkncrp {e}{nr}{i}",f"leak {e}{nr}{i}", f"side {e}{nr}{i}", f"forw {e}{nr}{i}",
                                  f"radside {e}{nr}{i}", f"radforward {e}{nr}{i}", f"radleak {e}{nr}{i}", f'workdistt {e}{nr}{i}',
                                  f"radworkl {e}{nr}{i}",f"workloadtip1 {e}{nr}{i}",f"worentry {e}{nr}{i}"])
            if self.var[radiob_w_key].get() == 1: #Primary
                self.var[f'workdistt {e}{nr}{i}'] = Hovertip(self.d[f"set {e}{nr}{i}"], text="Set this distribution\n"
                                                                                      "fitting parameters (α, β, γ)\n"
                                                                                      "for transmision to calculate\n"
                                                                                      "the thickness x in mm\n"
                                                                                    "(Table A.1 of NCRP 147)")
                # Define spinbox for kVp values for primary barrier
                self.var[vsexroom_key] = IntVar(value=25)
                self.d[selxroom_key] = ttk.Spinbox(master=self.d[barrierf_key], from_=25, to=150, increment=5,
                                                   textvariable=self.var[vsexroom_key], width=10, state= 'readonly')
                self.d[selxroom_key].grid(row=i * 10 + 3, column=2, pady=6.5, padx=5, sticky="w")

            elif self.var[radiob_w_key].get() == 2: #Secondary
                # Custom Spinbox for secondary barrier
                def increment_spinbox(spinbox, values):
                    current_value = int(spinbox.get())
                    current_index = values.index(current_value)
                    new_index = current_index
                    if 0 <= new_index < len(values):
                        spinbox.set(values[new_index])
                custom_values = [30, 50, 70, 100, 125, 150]
                self.var[vsexroom_key] = IntVar(value=custom_values[0])
                self.d[selxroom_key] = ttk.Spinbox(master=self.d[barrierf_key], values=custom_values,
                                                   textvariable=self.var[vsexroom_key], width=10, state= 'readonly')
                self.d[selxroom_key].bind("<<Increment>>",
                                          lambda e: increment_spinbox(self.d[selxroom_key], custom_values))
                self.d[selxroom_key].bind("<<Decrement>>",
                                          lambda e: increment_spinbox(self.d[selxroom_key], custom_values))
                self.d[selxroom_key].grid(row=i * 10 + 3, column=2, pady=6.5, padx=5, sticky="w")

    def numbmater(self, e, nr, t):
        m_key = f"m {e}{nr}"
        vnumbmat_key = f"vnumbmat {e}{nr}"
        # Initialize the material count if not already present
        if m_key not in self.d:
            self.d[m_key] = 0
        selected_room = self.var[f"vselroom {t}"].get()
        # For "CT Room"
        if selected_room == "CT Room":
            if self.d[m_key] < self.var[vnumbmat_key].get():
                while self.d[m_key] < self.var[vnumbmat_key].get():
                    self.d[m_key] += 1
                    self.mater = ("Lead", "Concrete")
                    self.var[f"vmater {e}{self.d[m_key]}{nr}"] = StringVar()
                    self.d[f"mater {e}{self.d[m_key]}"] = ttk.OptionMenu(self.d[f"barrierf {e}{nr}"],
                        self.var[f"vmater {e}{self.d[m_key]}{nr}"], "Select Material", *self.mater)
                    if self.d[m_key] < 3:
                        self.d[f"matlab {e}{self.d[m_key]}"] = ttk.Label(self.d[f"barrierf {e}{nr}"],
                            text=f"#{self.d[m_key]}:")
                        self.d[f"matlab {e}{self.d[m_key]}"].grid(row=10, column=-1 + self.d[m_key], sticky="w")
                        self.d[f"mater {e}{self.d[m_key]}"].grid(row=10, column=-1 + self.d[m_key], pady=6.5, padx=25,
                            sticky="s")

            # Destroy extra widgets if material count exceeds the required number
            else:
                while self.d[m_key] > self.var[vnumbmat_key].get():
                    self.destroy_widgets([f"mater {e}{self.d[m_key]}", f"matlab {e}{self.d[m_key]}"])
                    self.d[m_key] -= 1

        # For "X-ray Room"
        else:
            if self.d[m_key] < self.var[vnumbmat_key].get():
                while self.d[m_key] < self.var[vnumbmat_key].get():
                    self.d[m_key] += 1
                    self.mater = ("Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass", "Wood")
                    self.var[f"vmater {e}{self.d[m_key]}{nr}"] = StringVar()
                    # Create the option menu for materials
                    self.d[f"mater {e}{self.d[m_key]}"] = ttk.OptionMenu(self.d[f"barrierf {e}{nr}"],
                                                                         self.var[f"vmater {e}{self.d[m_key]}{nr}"],
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
                while self.d[m_key] > self.var[vnumbmat_key].get():
                    self.destroy_widgets([f"mater {e}{self.d[m_key]}", f"matlab {e}{self.d[m_key]}" ])
                    self.d[m_key] -= 1

    def update_checkboxes(self, e, nr, i):
        # Loop through all the checkboxes with the same 'e' and 'nr' but different 'i'
        for index in range(0, self.var[f"num_barriers_var {e}{nr}"].get()):  # Adjust 'some_max_value' to the range of 'i' you need
            if index != i:
                if f"setv {e}{nr}{index}" in self.var:
                    # Set all other checkbuttons' variables to 0 (unchecked)
                    self.var[f"setv {e}{nr}{index}"].set(0)

    def set_distance_tips(self, e, nr, i):
        """
        Sets hovertips based on the label text (Floor, Ceiling, or Wall).
        """
        label_text = self.barn[f"lab_bar {e}{nr}"].cget("text")

        if label_text == "Floor":  # from fig. 4.4 NCRP 147
            tip_text = 'Figure 4.4 of NCRP 147\n(Floor: adds +1.7 m of what you write)'
        elif label_text == "Ceiling":
            tip_text = 'Figure 4.4 of NCRP 147\n(Ceiling: adds +0.5 m of what you write)'
        else:
            tip_text = 'Figure 4.4 of NCRP 147\n(Wall: adds +0.3 m of what you write)'

        # Assign hover tips
        self.var[f'dist_ent {e}{nr}{i}'] = Hovertip(self.ent[f"entryd {e}{nr}{i}"], text=tip_text)
        self.var[f'dist_lad {e}{nr}{i}'] = Hovertip(self.d[f'lad {e}{nr}{i}'], text=tip_text)