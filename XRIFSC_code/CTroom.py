import tkinter
from tkinter import *
from tkinter import ttk
import theme
import os
from numpy import log as ln
from tooltips import tip


class  CT_Room():
    # ============creating def for CT notebook===================================
    def creatCTroom(self):
        self.hide_start_buttons()
        t, p, title = self.new_standalone("CT", "Design CT room", "CT Room")  # own key: never shares inputs
        depnote = self.ensure_workspace()
        self.roomframe = ttk.Frame(depnote)
        self.roomframe.pack(fill=BOTH, expand=1)
        depnote.add(self.roomframe, text=title)
        room_area, results_area = self.split_pane(self.roomframe, 950, 520)
        self.standalone[t] = self.roomframe
        #======Room scrollbar=========
        self.roomcanv= Canvas(room_area, width=theme.px(900))

        self.xscrollroom = ttk.Scrollbar(room_area, orient=HORIZONTAL, command=self.roomcanv.xview)
        self.xscrollroom.pack(side=BOTTOM, fill=X)
        self.roomcanv.pack(side=LEFT, fill=BOTH, expand=1)
        self.yscrollroom = ttk.Scrollbar (room_area, orient= VERTICAL, command= self.roomcanv.yview)
        self.yscrollroom.pack(side =RIGHT, fill=Y)
        self.roomcanv.configure(yscrollcommand=self.yscrollroom.set, xscrollcommand=self.xscrollroom.set,bg=theme.SURFACE)
        # =========Room tab===========================
        self.d["frame_1 {0}".format(str(t))] = ttk.Frame(self.roomcanv)
        self.d["frame_1 " + str(t)].bind('<Configure>', lambda e, c=self.roomcanv: c.configure(scrollregion=c.bbox("all")))
        self.roomcanv.create_window((0,0), window=self.d["frame_1 " + str(t)], anchor="nw")

        # ==========αρχικοποίηση τιμών =================
        self.d["selxroom {0}".format(str(t))] = None
        self.d["numpapwl {0}".format(str(t))] = None
        self.d["numpapwe {0}".format(str(t))] = None
        self.ep = 1
        self.d["x {0}".format(str(t))] = 0
        self.d["vselroom {0}".format(str(t))] = StringVar()
        self.d["selroom {0}".format(str(t))] = ttk.Combobox(master=self.d["frame_1 " + str(t)],
                                                            textvariable=self.d["vselroom " + str(t)],
                                                            values=["X-Ray room", "From X-Ray room","CT Room"], state="readonly")
        self.d["selroom {0}".format(str(t))].set("CT Room")
        self.d["nr {0}".format(str(t))] = p  # unique name: barrier inputs are keyed by it
        self.d["noteb {0}".format(str(t) + self.d["nr " + str(t)])] = ttk.Notebook(self.d["frame_1 " + str(t)],
                                                                                   style="BL.TNotebook")
        # ==============Number of Barriers in the Room==========
        self.lanumwall = ttk.Label(master=self.d["frame_1 " + str(t)], style="AL.TLabel", text="Number of Barriers")
        self.lanumwall.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        self.d["vnumwall {0}".format(str(t))] = IntVar(value=7)
        self.d["numwall {0}".format(str(t))] = ttk.Spinbox(master=self.d["frame_1 " + str(t)],
                                                           textvariable=self.d["vnumwall " + str(t)], from_=7,
                                                           to=50, width=5, command=lambda: self.barriers(t))
        self.d["numwall " + str(t)].grid(row=0, column=1, pady=10, padx=10, sticky="w")
        tip(self.lanumwall, "num_barriers")
        tip(self.d["numwall " + str(t)], "num_barriers")
        self.barriers(t)

        self.bp_label = ttk.Label(master=self.d["frame_1 " + str(t)], text='Body Procedures (weekly):')
        self.bp_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.d[f"bp_var {str(t)}"] = IntVar()
        self.bp_entry = ttk.Entry(master=self.d["frame_1 " + str(t)], textvariable=self.d[f"bp_var "+str(t)], width=10)
        self.bp_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        self.hp_label = ttk.Label(master=self.d["frame_1 " + str(t)], text='Head Procedures (weekly):')
        self.hp_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.d[f"hp_var {str(t)}"] = IntVar()
        self.hp_entry = ttk.Entry(master=self.d["frame_1 " + str(t)], textvariable=self.d[f"hp_var "+str(t)], width=10)
        self.hp_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        self.dlpb_label = ttk.Label(master=self.d["frame_1 " + str(t)], text='DLP for body (mGy\u2022cm):')
        self.dlpb_label.grid(row=4, column=0, padx=10, pady=10, sticky="w")
        self.d[f"dlpb_var {str(t)}"] = IntVar()
        self.dlpb_entry = ttk.Entry(master=self.d["frame_1 " + str(t)], textvariable=self.d[f"dlpb_var "+str(t)], width=10)
        self.dlpb_entry.grid(row=4, column=1, padx=10, pady=10, sticky="w")

        self.dlph_label = ttk.Label(master=self.d["frame_1 " + str(t)], text='DLP for head (mGy\u2022cm):')
        self.dlph_label.grid(row=5, column=0, padx=10, pady=10, sticky="w")
        self.d[f"dlph_var {str(t)}"] = IntVar()
        self.dlph_entry = ttk.Entry(master=self.d["frame_1 " + str(t)], textvariable=self.d[f"dlph_var "+str(t)], width=10)
        self.dlph_entry.grid(row=5, column=1, padx=10, pady=10, sticky="w")

        self.kvp_label = ttk.Label(master=self.d["frame_1 " + str(t)], text='Give kVp:')
        self.kvp_label.grid(row=6, column=0, padx=10, pady=10, sticky="w")
        self.d[f"kvp_var {str(t)}"] = IntVar()
        self.d[f"kvp_var "+str(t)].set(120)  # default value
        self.kvp_dropdown = ttk.Combobox(master=self.d["frame_1 " + str(t)], textvariable=self.d[f"kvp_var "+str(t)], values=[120, 140],
                                         state="readonly", width=7)
        self.kvp_dropdown.grid(row=6, column=1, padx=10, pady=10, sticky="w")
        for name in ("bp", "hp", "dlpb", "dlph"):  # kept for highlighting empty entries
            self.d[f"{name}_entry {t}"] = getattr(self, f"{name}_entry")
        for widget, key in ((self.bp_label, "ct_body"), (self.bp_entry, "ct_body"),
                            (self.hp_label, "ct_head"), (self.hp_entry, "ct_head"),
                            (self.dlpb_label, "ct_dlp_body"), (self.dlpb_entry, "ct_dlp_body"),
                            (self.dlph_label, "ct_dlp_head"), (self.dlph_entry, "ct_dlp_head"),
                            (self.kvp_label, "ct_kvp"), (self.kvp_dropdown, "ct_kvp")):
            tip(widget, key)
        # ==========Results==============
        self.d["resframe {0}".format(str(t))] = results_area
        ttk.Label(results_area, style="BL.TLabel", text="Results").pack(anchor="w", padx=5, pady=5)
        # ======Results scrollbar=========
        self.rescanv = Canvas(self.d["resframe " + str(t)], width=theme.px(480))
        self.rescanv.pack(side=LEFT, fill=BOTH, expand=1)
        self.scrollres = ttk.Scrollbar(self.d["resframe " + str(t)], orient=VERTICAL, command=self.rescanv.yview)
        self.scrollres.pack(side=RIGHT, fill=Y)
        self.rescanv.configure(yscrollcommand=self.scrollres.set, bg=theme.SURFACE)
        # =========Results tab===========================
        self.d["resultframe {0}".format(str(t)) + p] = ttk.Frame(self.rescanv)
        self.d["resultframe " + str(t) + p].bind('<Configure>', lambda e, c=self.rescanv: c.configure(
            scrollregion=c.bbox("all")))
        self.rescanv.create_window((0, 0), window=self.d["resultframe " + str(t) + p], anchor="nw")
        self.reshield = ttk.Label(self.d["resultframe " + str(t) + p], style="BL.TLabel", text="The Shielding of:")
        self.reshield.grid(sticky="w")
        self.d[f"room_default {t}"] = title
        self.d[f"vname_room {t}"] = StringVar(value=title)
        self.register_tab_name(self.roomframe, self.d[f"vname_room {t}"], title, depnote)
        # ======Export to excel========
        self.exp_but = ttk.Button(master=self.d["frame_1 " + str(t)], text="Export to Excel",
                                  command=lambda: self.exp_room(t))
        self.exp_but.grid(row=7, column=0, pady=10, padx=10, sticky="w")
        tip(self.exp_but, "export")
        self.add_view_buttons(t, self.d["frame_1 " + str(t)], row=10, column=0, columnspan=12)
        # ======Destroy button======
        self.closBut = ttk.Button(room_area, text="✕", width=3, style="Close.TButton",
                                  command=lambda f=self.roomframe, r=self.d["resframe " + str(t)]: self.closeroom(f, r))
        self.closBut.pack()
        return t
