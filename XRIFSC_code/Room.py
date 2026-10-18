import tkinter
from tkinter import *
from tkinter import ttk
import theme
import os
import xlsxwriter
from tooltips import tip

# Standalone room types: room type -> (key prefix, room name, tab title). Each room adds its own number, so two
# rooms of the same type never share inputs.
STANDALONE_ROOMS = {
    "X-Ray room": ("X", "Design x-ray room", "X-Ray Room"),
    "Mammography Room": ("M", "Design mammography room", "Mammography Room"),
    "Fluoroscopy Room": ("F", "Design fluoroscopy room", "Fluoroscopy Room"),
}

class droom():
    # ============creating def for Room notebook===================================
    def creatroom(self, room_type="X-Ray room"):
        self.hide_start_buttons()
        t, p, title = self.new_standalone(*STANDALONE_ROOMS[room_type])
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

        #==========αρχικοποίηση τιμών =================
        self.d["selxroom {0}".format(str(t))] = None
        self.d["numpapwl {0}".format(str(t))] = None
        self.d["numpapwe {0}".format(str(t))] = None
        self.d["sellocation {0}".format((str(t)))] = None
        self.ep = 1
        self.d["x {0}".format(str(t))] = 0

        self.d["vselroom {0}".format(str(t))] = StringVar()
        self.d["selroom {0}".format(str(t))] = ttk.Combobox(master=self.d["frame_1 " + str(t)],
                                                            textvariable=self.d["vselroom " + str(t)],
                                                            values=list(STANDALONE_ROOMS), state="readonly")
        self.d["selroom {0}".format(str(t))].set(room_type)
        self.d["nr {0}".format(str(t))]= p
        self.d["noteb {0}".format(str(t) + self.d["nr " + str(t)])] = ttk.Notebook(self.d["frame_1 " + str(t)],
                                                                                   style="BL.TNotebook")

        # ==============Number of Barriers in the Room==========
        self.lanumwall = ttk.Label(master=self.d["frame_1 " + str(t)], style="AL.TLabel", text="Number of Barriers")
        self.lanumwall.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        self.d["vnumwall {0}".format(str(t))] = IntVar(value=7)
        self.d["numwall {0}".format(str(t))] = ttk.Spinbox(master=self.d["frame_1 " + str(t)],
                                                           textvariable=self.d["vnumwall " + str(t)], from_=7, to=50,
                                                           width=5, command=lambda: self.barriers(t))
        self.d["numwall " + str(t)].grid(row=0, column=1, pady=10, padx=10, sticky="w")
        tip(self.lanumwall, "num_barriers")
        tip(self.d["numwall " + str(t)], "num_barriers")
        self.barriers(t)
        # Add workload
        self.setup_xray_room(t)

        #======Export to excel========
        self.exp_but = ttk.Button(master=self.d["frame_1 " + str(t)], text="Export to Excel", command=lambda : self.exp_room(t))
        self.exp_but.grid(row=1, column=5, pady=10, padx=10, sticky="w")
        tip(self.exp_but, "export")
        self.add_view_buttons(t, self.d["frame_1 " + str(t)], row=2, column=0, columnspan=6)

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
        self.d["resultframe {0}".format(str(t))+p] = ttk.Frame(self.rescanv)
        self.d["resultframe " + str(t)+p].bind('<Configure>',
                                             lambda e, c=self.rescanv: c.configure(scrollregion=c.bbox("all")))
        self.rescanv.create_window((0, 0), window=self.d["resultframe " + str(t)+p], anchor="nw")
        self.reshield = ttk.Label(self.d["resultframe " + str(t)+p], style="BL.TLabel", text="The Shielding of:")
        self.reshield.grid(sticky="w")
        self.d[f"room_default {t}"] = title
        self.d[f"vname_room {t}"] = StringVar(value=title)
        self.register_tab_name(self.roomframe, self.d[f"vname_room {t}"], title, depnote)
        #======Destroy button======
        self.closBut = ttk.Button(room_area, text="✕", width=3, style="Close.TButton",
                                  command=lambda f=self.roomframe, r=self.d["resframe " + str(t)]: self.closeroom(f, r))
        self.closBut.pack()
        return t

    def exp_room(self, t):
        self.export_report(self.room_name(t), [t])

    def new_standalone(self, prefix, name, title):
        """Unique key t, room name nr and tab title for one more standalone room: the second X-Ray room is
        'X-Ray Room 2' and keeps its own materials, barriers and results."""
        self.standalone_count += 1
        n = self.standalone_count
        same = sum(1 for key, frame in self.standalone.items()
                   if str(key).rstrip("0123456789") == prefix and frame.winfo_exists())
        return f"{prefix}{n}", f"{name} {n}:", title if same == 0 else f"{title} {same + 1}"

    def closeroom(self, room_frame, result_frame):
        # Close a standalone room (X-Ray, Mammography or CT) together with its results
        room_frame.destroy()
        result_frame.destroy()
        if not self.depnote.tabs():
            self.depnote.destroy()
            self.depnote = None
            self.show_start_buttons()
