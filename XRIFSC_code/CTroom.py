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
        #self.quickbutton.destroy()
        self.chooseCal.destroy()
        p = "Design CT room"
        t = 0
        if self.depnote is None:
            self.depnote = ttk.Notebook(self.new_main_Frame, style="AL.TNotebook")
            self.depnote.configure(width=955, height=728)
            self.depnote.grid(row=0, sticky="w")
        self.roomframe = ttk.Frame(self.depnote)
        self.roomframe.pack(fill=BOTH, expand=1)
        self.depnote.add(self.roomframe, text="CT Room")
        #======Room scrollbar=========
        self.roomcanv= Canvas(self.roomframe)

        self.xscrollroom = ttk.Scrollbar(self.roomframe, orient=HORIZONTAL, command=self.roomcanv.xview)
        self.xscrollroom.pack(side=BOTTOM, fill=X)
        self.roomcanv.pack(side=LEFT, fill=BOTH, expand=1)
        self.yscrollroom = ttk.Scrollbar (self.roomframe, orient= VERTICAL, command= self.roomcanv.yview)
        self.yscrollroom.pack(side =RIGHT, fill=Y)
        self.roomcanv.configure(yscrollcommand=self.yscrollroom.set, xscrollcommand=self.xscrollroom.set,bg="#f6f8f8")
        # =========Room tab===========================
        self.d["frame_1 {0}".format(str(t))] = ttk.Frame(self.roomcanv)
        self.d["frame_1 " + str(t)].bind('<Configure>', lambda e: self.roomcanv.configure(scrollregion=self.roomcanv.bbox("all")))
        self.roomcanv.create_window((0,0), window=self.d["frame_1 " + str(t)], anchor="nw")
        if self.resnote is None:
            self.resnote = ttk.Notebook(self.new_main_Frame, style="AL.TNotebook")
            self.resnote.grid(row=0, column=1, sticky="w")
            self.resnote.configure(width=562, height=728)

        # ==========αρχικοποίηση τιμών =================
        self.d["selxroom {0}".format(str(t))] = None
        self.d["numpapwl {0}".format(str(t))] = None
        self.d["numpapwe {0}".format(str(t))] = None
        self.ep = 1
        self.d["x {0}".format(str(t))] = 0
        self.var["vselroom {0}".format(str(t))] = StringVar()
        self.d["selroom {0}".format(str(t))] = ttk.Combobox(master=self.d["frame_1 " + str(t)],
                                                            textvariable=self.var["vselroom " + str(t)],
                                                            values=["X-Ray room", "From X-Ray room","CT Room"], state="readonly")
        self.d["selroom {0}".format(str(t))].set("CT Room")
        self.d["nr {0}".format(str(t))] = "Design CT room"
        self.d["noteb {0}".format(str(t) + self.d["nr " + str(t)])] = ttk.Notebook(self.d["frame_1 " + str(t)],
                                                                                   style="BL.TNotebook")
        # ==============Number of Barriers in the Room==========
        self.lanumwall = ttk.Label(master=self.d["frame_1 " + str(t)], style="AL.TLabel", text="Number of Barriers")
        self.lanumwall.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        self.d["vnumwall {0}".format(str(t))] = IntVar(value=7)
        self.d["numwall {0}".format(str(t))] = ttk.Spinbox(master=self.d["frame_1 " + str(t)],
                                                           textvariable=self.var["vnumwall " + str(t)], from_=7,
                                                           to=50, width=5, command=lambda: self.barriers(t))
        self.d["numwall " + str(t)].grid(row=0, column=1, pady=10, padx=10, sticky="w")
        self.barriers(t)

        self.bp_label = ttk.Label(master=self.d["frame_1 " + str(t)], text='Body Procedures (weekly):')
        self.bp_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.var[f"bp_var {str(t)}"] = IntVar()
        self.bp_entry = ttk.Entry(master=self.d["frame_1 " + str(t)], textvariable=self.var[f"bp_var "+str(t)], width=10)
        self.bp_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        self.hp_label = ttk.Label(master=self.d["frame_1 " + str(t)], text='Head Procedures (weekly):')
        self.hp_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.var[f"hp_var {str(t)}"] = IntVar()
        self.hp_entry = ttk.Entry(master=self.d["frame_1 " + str(t)], textvariable=self.var[f"hp_var "+str(t)], width=10)
        self.hp_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        self.dlpb_label = ttk.Label(master=self.d["frame_1 " + str(t)], text='DLP for body (mGy\u2022cm):')
        self.dlpb_label.grid(row=4, column=0, padx=10, pady=10, sticky="w")
        self.var[f"dlpb_var {str(t)}"] = IntVar()
        self.dlpb_entry = ttk.Entry(master=self.d["frame_1 " + str(t)], textvariable=self.var[f"dlpb_var "+str(t)], width=10)
        self.dlpb_entry.grid(row=4, column=1, padx=10, pady=10, sticky="w")

        self.dlph_label = ttk.Label(master=self.d["frame_1 " + str(t)], text='DLP for head (mGy\u2022cm):')
        self.dlph_label.grid(row=5, column=0, padx=10, pady=10, sticky="w")
        self.var[f"dlph_var {str(t)}"] = IntVar()
        self.dlph_entry = ttk.Entry(master=self.d["frame_1 " + str(t)], textvariable=self.var[f"dlph_var "+str(t)], width=10)
        self.dlph_entry.grid(row=5, column=1, padx=10, pady=10, sticky="w")

        self.kvp_label = ttk.Label(master=self.d["frame_1 " + str(t)], text='Give kVp:')
        self.kvp_label.grid(row=6, column=0, padx=10, pady=10, sticky="w")
        self.var[f"kvp_var {str(t)}"] = IntVar()
        self.var[f"kvp_var "+str(t)].set(120)  # default value
        self.kvp_dropdown = ttk.Combobox(master=self.d["frame_1 " + str(t)], textvariable=self.var[f"kvp_var "+str(t)], values=[120, 140],
                                         state="readonly", width=7)
        self.kvp_dropdown.grid(row=6, column=1, padx=10, pady=10, sticky="w")
        # ==========Results==============
        self.d["resframe {0}".format(str(t))] = ttk.Frame(self.resnote)
        self.d["resframe " + str(t)].pack()
        self.resnote.add(self.d["resframe " + str(t)], text="Results of CT Room")

        # ======Results scrollbar=========
        self.rescanv = Canvas(self.d["resframe " + str(t)])
        self.rescanv.pack(side=LEFT, fill=BOTH, expand=1)
        self.scrollres = ttk.Scrollbar(self.d["resframe " + str(t)], orient=VERTICAL, command=self.rescanv.yview)
        self.scrollres.pack(side=RIGHT, fill=Y)
        self.rescanv.configure(yscrollcommand=self.scrollres.set, bg="#f6f8f8")
        # =========Results tab===========================
        self.d["resultframe {0}".format(str(t)) + p] = ttk.Frame(self.rescanv)
        self.d["resultframe " + str(t) + p].bind('<Configure>', lambda e: self.rescanv.configure(
            scrollregion=self.rescanv.bbox("all")))
        self.rescanv.create_window((0, 0), window=self.d["resultframe " + str(t) + p], anchor="nw")
        self.reshield = ttk.Label(self.d["resultframe " + str(t) + p], style="BL.TLabel", text="The Shielding of:")
        self.reshield.grid(sticky="w")
        # ======Destroy button======
        self.closBut = ttk.Button(self.roomframe, text="X", width=4, command=lambda: self.closeroom(t))
        self.closBut.pack()

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
        self.kvp_label.grid(row=9, column=0, padx=10, pady=10, sticky="w")
        self.var[f"kvp_var {t}"] = IntVar()
        self.var[f"kvp_var {t}"].set(120)  # default value
        self.kvp_dropdown = ttk.Combobox(master=self.d["frame_1 " + str(t)],
                                         textvariable=self.var[f"kvp_var " + str(t)], values=[120, 140],
                                         state="readonly", width=7)
        self.kvp_dropdown.grid(row=9, column=1, padx=10, pady=10, sticky="w")

        self.dlpb_label = ttk.Label(self.d[f"frame_1 {t}"], text='DLP for body (mGy\u2022cm):')
        self.dlpb_label.grid(row=7, column=0, padx=10, pady=10, sticky="w")
        self.var[f"dlpb_var {t}"] = IntVar()
        self.dlpb_entry = ttk.Entry(self.d[f"frame_1 {t}"], textvariable=self.var[f"dlpb_var {t}"], width=10)
        self.dlpb_entry.grid(row=7, column=1, padx=10, pady=10, sticky="w")

        self.dlph_label = ttk.Label(self.d[f"frame_1 {t}"], text='DLP for head (mGy\u2022cm):')
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