from tkinter import *
from tkinter import ttk
import os
import xlsxwriter
from idlelib.tooltip import Hovertip

class droom():
    # ============creating def for Room notebook===================================
    def creatroom(self):
        self.depbutton.destroy()
        self.roombutton.destroy()
        self.CTbutton.destroy()
        self.chooseCal.destroy()
        p = "Design x-ray room"
        self.i += 1
        if self.depnote is None:
            self.depnote = ttk.Notebook(self.new_main_Frame, style="AL.TNotebook")
            self.depnote.configure(width=980, height=728)
            self.depnote.grid(row=0, sticky="w")
            # Bind the tab change event to sync with results
            self.depnote.bind("<<NotebookTabChanged>>", self.sync_results_tab)
        self.roomsframe = ttk.Frame(self.depnote)
        self.roomsframe.pack(fill=BOTH, expand=1)
        self.depnote.add(self.roomsframe, text=p)

        self.d[f"labelname {self.i}"] = ttk.Label(master=self.roomsframe, style="AL.TLabel",
                                                  text=f"X-Ray Room{self.i}:")
        self.d[f"resframe {self.i}"] = None
        self.var["numrooms"] = IntVar(value=2)
        self.var[f"vselroom {self.i}"] = StringVar(value = "X-Ray Room")
        self.ent[f"name_room {self.i}"] = StringVar(value = "X-Ray Room")
        self.d[f"run {self.i}"] = False
        self.desroom(self.i)
        self.roomsframe.destroy()

    def _add_xray_room_widgets(self, index, room_number, t):
        """Add X-ray room specific widgets."""
        # Label to indicate number of radiation types on the barrier
        labb = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                         text="Select the number of types\nof radiation on the barrier:")
        labb.grid(row=0, column=0, pady=6.5, padx=5, sticky="w")

        # Initialize tracking of the previous number of barriers
        self.var[f"prev_num_barriers {index}{room_number}"] = 0

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
        prev_num_barriers = self.var[f"prev_num_barriers {index}{room_number}"]

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
        self.var[f"prev_num_barriers {index}{room_number}"] = num_barriers

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

    def exp_room(self, t):
        import pandas as pd
        p = "Design x-ray room"
        for a in range(1, self.var["vnumwall " + str(t)].get() + 1):
            self.wa[self.barn["lab_bar " + str(a) + p].cget("text")] = [
                str(self.xlmat["thic " + str(a) + str(1) + p]), str(self.xlmat["thic " + str(a) + str(2) + p]),
                str(self.xlmat["thic " + str(a) + str(3) + p]), str(self.xlmat["thic " + str(a) + str(4) + p]),
                str(self.xlmat["thic " + str(a) + str(5) + p]), str(self.xlmat["thic " + str(a) + str(6) + p])]
        self.d["room_data {0}".format(str(t))] = pd.DataFrame(data=self.wa,
                                                              index=["Lead", "Concrete", "Gypsum Wallboard",
                                                                     "Steel", "Plate Glass", "Wood"])
        user_home = os.path.expanduser('~')  # Get user's home directory
        excel_file_path = os.path.join(user_home, 'Department.xlsx')

        with pd.ExcelWriter(excel_file_path, engine='xlsxwriter',
                            engine_kwargs={'options': {'strings_to_numbers': True}}) as writer:
            self.d["room_data " + str(t)].to_excel(writer, sheet_name="X-Ray Room")
        os.system(excel_file_path)

    def closeroom(self,t):
        self.roomframe.destroy()
        p = "Design x-ray room"
        self.d["resframe " + str(t)].destroy()
        self.d["resultframe " + str(t)+p].destroy()
        if self.depframe is None and self.quickf is None:
            self.depnote.destroy()
            self.resnote.destroy()
            self.depnote =None
            self.resnote=None
            # ===========Buttons========
            self.chooseCal = ttk.Label(master=self.new_main_Frame, text="Design", style="CL.TLabel")
            self.depbutton = ttk.Button(master=self.new_main_Frame, style="AL.TButton", text="Department",
                                        command=self.creatdep)
            self.roombutton = ttk.Button(master=self.new_main_Frame, style="AL.TButton", text="X-Ray Room",
                                         command=self.creatroom)
            self.quickbutton = ttk.Button(master=self.new_main_Frame, style="AL.TButton", text="Barrier",
                                          command=self.quickcal)
            self.chooseCal.pack(anchor="c", pady=10, padx=700)
            self.depbutton.pack(anchor="c", pady=10, padx=700)
            self.roombutton.pack(anchor="c", pady=10, padx=700)
            self.quickbutton.pack(anchor="c", pady=10, padx=700)

