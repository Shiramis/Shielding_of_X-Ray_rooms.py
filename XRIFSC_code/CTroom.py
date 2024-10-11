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

        self.kvp_label = ttk.Label(self.d[f"frame_1 {t}"], text='Tube Voltage kVp:')
        self.kvp_label.grid(row=9, column=0, padx=10, pady=10, sticky="w")
        self.var[f"kvp_var {t}"] = IntVar()
        self.var[f"kvp_var {t}"].set(120)  # default value
        self.kvp_dropdown = ttk.Combobox(master=self.d["frame_1 " + str(t)],
                                         textvariable=self.var[f"kvp_var " + str(t)], values=[120, 140],
                                         state="readonly", width=7)
        self.kvp_dropdown.grid(row=9, column=1, padx=10, pady=10, sticky="w")

        self.dlpb_label = ttk.Label(self.d[f"frame_1 {t}"], text='DLP for body (mGy∙cm):')
        self.dlpb_label.grid(row=7, column=0, padx=10, pady=10, sticky="w")
        self.var[f"dlpb_var {t}"] = IntVar()
        self.dlpb_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.var[f"dlpb_var {t}"], width=10)
        self.dlpb_entry.grid(row=7, column=1, padx=10, pady=10, sticky="w")

        self.dlph_label = ttk.Label(self.d[f"frame_1 {t}"], text='DLP for head (mGy∙cm):')
        self.dlph_label.grid(row=8, column=0, padx=10, pady=10, sticky="w")
        self.var[f"dlph_var {t}"] = IntVar()
        self.dlph_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.var[f"dlph_var {t}"], width=10)
        self.dlph_entry.grid(row=8, column=1, padx=10, pady=10, sticky="w")

    def _add_ct_room_widgets(self, index, room_number, t):
        """Add CT room specific widgets."""
        dist_label = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                               text='Distance from the CT Unit Isocenter (m):')
        dist_label.grid(row=7, column=0, padx=5, pady=6.5, sticky="w")
        self.var[f"dist_var {index}{room_number}"] = StringVar()
        dist_entry = ttk.Entry(master=self.d[f"barrierf {index}{room_number}"],
                               textvariable=self.var[f"dist_var {index}{room_number}"], width=10)
        dist_entry.grid(row=7, column=1, padx=5, pady=6.5, sticky="w")

        sh_label = ttk.Label(master=self.d[f"barrierf {index}{room_number}"],
                             text='Shielding Design Goal(P)\n(mGy∙week\u207B\u00b9):')
        sh_label.grid(row=11, column=0, padx=5, pady=6.5, sticky="w")
        self.var[f"sh_var {index}{room_number}"] = DoubleVar()
        sh_entry = ttk.Entry(master=self.d[f"barrierf {index}{room_number}"],
                             textvariable=self.var[f"sh_var {index}{room_number}"], width=10)
        sh_entry.grid(row=11, column=1, padx=5, pady=6.5, sticky="w")
        self.d[f"calbutton {index}{room_number}"] = ttk.Button(master=self.d[f"barrierf {index}{room_number}"],
                                                               text="Calculate",
                                                               command=lambda e=index, nr=room_number: self.choosetype(
                                                                   e, nr, t))
        self.d[f"calbutton {index}{room_number}"].grid(row=12, column=2, pady=6.5, padx=5, sticky="w")