import tkinter
from tkinter import *
from tkinter import ttk
import os
from numpy import log as ln


class  CT_Room():
    # ============creating def for CT notebook===================================
    def creatCTroom(self):
        self.depbutton.destroy()
        self.roombutton.destroy()
        self.CTbutton.destroy()
        self.chooseCal.destroy()
        p = "Design CT Room"
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
                                                  text=f"CT Room{self.i}:")
        self.d[f"resframe {self.i}"] = None
        self.var["numrooms"] = IntVar(value=2)
        self.var[f"vselroom {self.i}"] = StringVar(value="CT Room")
        self.ent[f"name_room {self.i}"] = StringVar(value="CT Room")
        self.d[f"run {self.i}"] = False
        self.desroom(self.i)
        self.roomsframe.destroy()

    def setup_ct_room(self, t):
        # kVp
        self.kvp_label = ttk.Label(self.d[f"frame_1 {t}"], text='Tube Voltage kVp:')
        self.kvp_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.var[f"kvp_var {t}"] = IntVar()
        self.var[f"kvp_var {t}"].set(120)  # default value
        self.kvp_dropdown = ttk.Combobox(master=self.d["frame_1 " + str(t)],
                                         textvariable=self.var[f"kvp_var " + str(t)], values=[120, 140],
                                         state="readonly", width=7)
        self.kvp_dropdown.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        # =====DLP=======
        # DLP body
        self.dlpb_label = ttk.Label(self.d[f"frame_1 {t}"], text='DLP for body (mGy∙cm):')
        self.dlpb_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.var[f"dlpb_var {t}"] = StringVar()
        self.dlpb_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.var[f"dlpb_var {t}"], width=10)
        self.dlpb_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        # DLP head
        self.dlph_label = ttk.Label(self.d[f"frame_1 {t}"], text='DLP for head (mGy∙cm):')
        self.dlph_label.grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.var[f"dlph_var {t}"] = StringVar()
        self.dlph_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.var[f"dlph_var {t}"], width=10)
        self.dlph_entry.grid(row=3, column=1, padx=10, pady=10, sticky="w")

        #== procedures & phases ==
        # body procedures
        self.bp_label = ttk.Label(self.d[f"frame_1 {t}"], text='Body Procedures (weekly):')
        self.bp_label.grid(row=4, column=0, padx=10, pady=10, sticky="w")
        self.var[f"bp_var {t}"] = StringVar()
        self.bp_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.var[f"bp_var {t}"], width=10)
        self.bp_entry.grid(row=4, column=1, padx=10, pady=10, sticky="w")
        # Number of phases for body
        self.numbodyscan = ttk.Label(self.d[f"frame_1 {t}"], text='Number of phases in body procedures:')
        self.numbodyscan.grid(row=5, column=0, padx=10, pady=10, sticky="w")
        self.var[f"prev_num_body_barriers {t}"] = 0 # Initialize tracking of the previous number of barriers
        self.var[f"numbodyscans {t}"] = IntVar(value=1)
        self.num_body_scans = ttk.Spinbox(master=self.d[f"frame_1 {t}"], from_=0, to=20, increment=1,
                                     textvariable=self.var[f"numbodyscans {t}"], width=5,
                                     command=lambda: self.createbodyscan(t))
        self.num_body_scans.grid(row=5, column=1, pady=10, padx=10, sticky="w")
        #head procedures
        self.hp_label = ttk.Label(self.d[f"frame_1 {t}"], text='Head Procedures (weekly):')
        self.hp_label.grid(row=26, column=0, padx=10, pady=10, sticky="w")
        self.var[f"hp_var {t}"] = StringVar()
        self.hp_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.var[f"hp_var {t}"], width=10)
        self.hp_entry.grid(row=26, column=1, padx=10, pady=10, sticky="w")
        # Number of phases for head
        self.numheadscan = ttk.Label(self.d[f"frame_1 {t}"], text='Number of phases in head procedures:')
        self.numheadscan.grid(row=27, column=0, padx=10, pady=10, sticky="w")
        self.var[f"prev_num_head_barriers {t}"] = 0 # Initialize tracking of the previous number of barriers
        self.var[f"numheadscans {t}"] = IntVar(value=1)
        self.num_head_scans = ttk.Spinbox(master=self.d[f"frame_1 {t}"], from_=0, to=20, increment=1,
                                     textvariable=self.var[f"numheadscans {t}"], width=5,
                                     command=lambda: self.createheadscan(t))
        self.num_head_scans.grid(row=27, column=1, pady=10, padx=10, sticky="w")

        # Initial call to create scans
        self.createbodyscan(t)
        self.createheadscan(t)

    def createbodyscan(self, t):
        num_scans = self.var[f"numbodyscans {t}"].get()
        pre_nscans = self.var[f"prev_num_body_barriers {t}"]

        if num_scans > pre_nscans:
            # Create widgets for new barriers
            for i in range(pre_nscans, num_scans):
                # Label for barrier type
                if i == 0:
                    self.d[f"label_nums {t}{i}"] = ttk.Label(master=self.d[f"frame_1 {t}"],style = 'AL2.TLabel',
                        text=f"Percentage (%) of body procedures with {i + 1} phase:")
                elif i>=1:
                    self.d[f"label_nums {t}{i}"] = ttk.Label(master=self.d[f"frame_1 {t}"], style = 'AL2.TLabel',
                                                             text=f"Percentage (%) of body procedures with {i + 1} phases:")
                self.d[f"label_nums {t}{i}"].grid(row=i  + 6, column=0, pady=10, padx=10, sticky="w")
                # Calculate initial value as half of the previous
                if i == 0:
                    initial_bodyvalue = 100  # First phase always starts with 100
                else:
                    prev_value = self.var[f"perbodyscans {t}{i - 1}"].get()
                    initial_bodyvalue = max(prev_value / 2, 0.5)

                self.var[f"perbodyscans {t}{i}"] = IntVar(value = int(initial_bodyvalue))
                # Spinbox widget for scans
                self.d[f"numbodyscans {t}{i}"] = ttk.Spinbox(master=self.d[f"frame_1 {t}"], from_=0,to = 100, increment = 0.5,
                                                               textvariable=self.var[f"perbodyscans {t}{i}"],
                                                                width=5)
                self.d[f"numbodyscans {t}{i}"].grid(row=i + 6, column=1, pady=10, padx=10, sticky="w")
                self.var[f"perbodyscans {t}{i}"].trace_add("write",
                    lambda *args, idx=i: self.validate_spinbox(self.var[f"perbodyscans {t}{idx}"]))
        elif num_scans < pre_nscans:
            # Destroy excess widgets
            for i in range(num_scans, pre_nscans):
                self.destroy_widgets([f"label_nums {t}{i}", f"numbodyscans {t}{i}",f"perbodyscans {t}{i}"])
        # Update the previous number of barriers to the current value
        self.var[f"prev_num_body_barriers {t}"] = num_scans

    def createheadscan(self, t):
        num_head_scans = self.var[f"numheadscans {t}"].get()
        pre_nheadscans = self.var[f"prev_num_head_barriers {t}"]

        if num_head_scans > pre_nheadscans:
            # Create widgets for new barriers
            for i in range(pre_nheadscans, num_head_scans):
                # Label for barrier type
                if i == 0:
                    self.d[f"label_numhead {t}{i}"] = ttk.Label(master=self.d[f"frame_1 {t}"], style = 'AL2.TLabel',
                                                             text=f"Percentage (%) of head procedures with {i + 1} phase:")
                elif i >= 1:
                    self.d[f"label_numhead {t}{i}"] = ttk.Label(master=self.d[f"frame_1 {t}"], style = 'AL2.TLabel',
                                                             text=f"Percentage (%) of head procedures with {i + 1} phases:")
                self.d[f"label_numhead {t}{i}"].grid(row=i + 28, column=0, pady=10, padx=10, sticky="w")

                # Calculate initial value as half of the previous
                if i == 0:
                    initial_value = 100  # First phase always starts with 100
                else:
                    prev_value = self.var[f"perheadscans {t}{i - 1}"].get()
                    initial_value = max(prev_value / 2, 0.5)
                # Spinbox widget for scans
                self.var[f"perheadscans {t}{i}"] = IntVar(value=int(initial_value))
                self.d[f"numheadscans {t}{i}"] = ttk.Spinbox(master=self.d[f"frame_1 {t}"], from_=0,to = 100, increment = 10,
                                                               textvariable=self.var[f"perheadscans {t}{i}"],
                                                                width=5)
                self.d[f"numheadscans {t}{i}"].grid(row=i + 28, column=1, pady=10, padx=10, sticky="w")
                # Bind the spinbox to validate its value
                self.var[f"perheadscans {t}{i}"].trace_add("write",
                    lambda *args, idx=i: self.validate_spinbox(self.var[f"perheadscans {t}{idx}"]))
        elif num_head_scans < pre_nheadscans:
            # Destroy excess widgets
            for i in range(num_head_scans, pre_nheadscans):
                self.destroy_widgets([f"label_numhead {t}{i}", f"numheadscans {t}{i}", f"perheadscans {t}{i}"])
        # Update the previous number of barriers to the current value
        self.var[f"prev_num_head_barriers {t}"] = num_head_scans

    def _add_ct_room_widgets(self, index, room_number, t):
        """Add CT room specific widgets."""
        # Distance
        dist_label = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                               text='Distance from the CT Unit Isocenter (m):')
        dist_label.grid(row=0, column=0, padx=5, pady=6.5, sticky="w")
        self.var[f"dist_var {index}{room_number}"] = StringVar()
        dist_entry = ttk.Entry(master=self.d[f"barrierf {index}{room_number}"],
                               textvariable=self.var[f"dist_var {index}{room_number}"], width=10)
        dist_entry.grid(row=0, column=1, padx=5, pady=6.5, sticky="w")
        # Occupancy Factor T
        Tocclabel = ttk.Label(master=self.d[f"barrierf {index}{room_number}"],
                             text='Occupancy Factor (T):')
        Tocclabel.grid(row=3, column=0, padx=5, pady=6.5, sticky="w")
        self.var[f"occup {index}{room_number}"] =DoubleVar(value=1)
        T_entry = ttk.Entry(master=self.d[f"barrierf {index}{room_number}"],
                             textvariable=self.var[f"occup {index}{room_number}"], width=10)
        T_entry.grid(row=3, column=1, padx=5, pady=6.5, sticky="w")
        # Shielding Design Goal (P)
        sh_label = ttk.Label(master=self.d[f"barrierf {index}{room_number}"],
                             text='Shielding Design Goal(P)\n(mGy∙week\u207B\u00b9):')
        sh_label.grid(row=4, column=0, padx=5, pady=6.5, sticky="w")
        self.var[f"sh_var {index}{room_number}"] = DoubleVar()
        sh_entry = ttk.Entry(master=self.d[f"barrierf {index}{room_number}"],
                             textvariable=self.var[f"sh_var {index}{room_number}"], width=10)
        sh_entry.grid(row=4, column=1, padx=5, pady=6.5, sticky="w")
        # Calculation button
        self.d[f"calbutton {index}{room_number}"] = ttk.Button(master=self.d[f"barrierf {index}{room_number}"],
                                                               text="Calculate",
                                                               command=lambda e=index, nr=room_number: self.choosetype(
                                                                   e, nr, t))
        self.d[f"calbutton {index}{room_number}"].grid(row=5, column=1, pady=6.5, padx=5, sticky="w")

    def validate_spinbox(self, var):
        """Ensure spinbox value stays within range and handle empty values."""
        try:
            value = var.get()
        except (ValueError, TclError):
            return
        # Clamp the value within the allowed range
        if value < 0:
            var.set(0)
        elif value > 100:
            var.set(100)