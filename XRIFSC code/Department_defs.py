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
            for var in ["radside", "radforward", "leakvar", "existvar",
                        "sellocation", "forw", "side", "laks", "entk", "leak"]:
                self.d[f"{var} {index}{room_number}"] = None
            for var in ["preshvar", "preshuns", "radiob_pre","radiob_leak", "leakvar",
                        "airkerv"]:
                self.d[f"{var} {index}{room_number}"] = IntVar(value=0)
            self.d[f"barrierf {index}{room_number}"] = ttk.Frame(self.d[f"noteb {t}{room_number}"], width=190)
            self.d[f"barrierf {index}{room_number}"].pack()
            if index <= 3:
                labels = ["Floor", "Ceiling", "Door"]
                self.barn[f"lab_bar {index}{room_number}"] = Label(text=labels[index - 1])
            else:
                self.barn[f"lab_bar {index}{room_number}"] = Label(text=f"Barrier {index - 3}")
            self.d[f"noteb {t}{room_number}"].add(self.d[f"barrierf {index}{room_number}"], text=self.barn[f"lab_bar {index}{room_number}"].cget("text"))
            self.barr[self.barn[f"lab_bar {index}{room_number}"].cget("text")] = 0
            # Add widgets based on room type
            if self.d[f"vselroom {t}"].get() == "CT Room":
                self._add_ct_room_widgets(index, room_number, t)
            else:
                self._add_xray_room_widgets(index, room_number, t)
            # Calculate button
            self.d[f"calbutton {index}"] = ttk.Button(
                master=self.d[f"barrierf {index}{room_number}"],
                text="Calculate",
                command=lambda e=index, nr=room_number, ep=self.ep: self.choosetype(e, nr, ep, t)
            )
            self.d[f"calbutton {index}"].grid(row=19, column=1, pady=10, padx=10, sticky="w")
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
        self.d[f"x {t}"] = current_barriers
        self.d[f"noteb {t}{room_number}"].grid(row=0, column=4, rowspan=10, columnspan=current_barriers, pady=10, padx=10, sticky="wn")

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

    def occupation3(self,e,nr,t):
        if self.d["vraoccup " + str(e)+nr].get() == 1:
            if self.d["sellocation " + str(e)+nr] is not None:
                self.d["sellocation " + str(e)+nr].destroy()
            if self.d["occupentry " + str(e)+nr] is not None:
                self.d["occupentry " + str(e)+nr].destroy()
            self.d["vselocation {0}".format(str(e)) + nr]=StringVar()
            self.d["occupentry " + str(e)+nr] = ttk.Entry(master=self.d["barrierf " + str(e)+nr], width=10)
            if self.d["area " + str(e)+nr].get() == "Cotrolled Area":
                self.d["occupentry " + str(e)+nr].insert(0,str(1))
            elif self.d["area " + str(e)+nr].get() == "Uncontrolled Area":
                self.d["occupentry " + str(e)+nr].insert(0,str(1/16))
            elif self.d["area " + str(e)+nr].get() == "Supervised Area":
                self.d["occupentry " + str(e)+nr].insert(0,str(1/4))
            self.d["occupentry " + str(e)+nr].grid(row=14, column=1, pady=10, padx=10)
        elif self.d["vraoccup " + str(e)+nr].get() == 2:
            if self.d["occupentry " + str(e)+nr] is not None:
                self.d["occupentry " + str(e)+nr].destroy()
            if self.d["sellocation " + str(e)+nr] is not None:
                self.d["sellocation " + str(e)+nr].destroy()
            self.d["vselocation {0}".format(str(e))+nr] = StringVar()
            if self.d["area " + str(e)+nr].get() == "Cotrolled Area":
                self.control = ("Administrative or clerical offices", "Laboratories",
                                "Pharmacies and other work areas fully occupied by an individual", "Receptionist areas",
                                "Attended waiting rooms", "Children’s indoor play areas", "Adjacent x-ray rooms",
                                "Film reading areas", "Nurse’s stations", "X-ray control rooms",
                                "Rooms used for patient examinations and treatments")
                self.d["sellocation " + str(e)+nr] = ttk.OptionMenu(self.d["barrierf " + str(e)+nr],
                                                                 self.d["vselocation " + str(e)+nr], "Select Location",
                                                                 *self.control)
            elif self.d["area " + str(e)+nr].get() == "Uncontrolled Area":
                self.uncontroll = (
                "Public toilets", "Unattended vending areas", "Storage  rooms", "Outdoor areas with seating",
                "Unattended waiting rooms", "Patient holding areas",
                "Outdoor areas with only transient pedestrian or vehicular traffic", "Unattended parking lots",
                "Vehicular drop off areas (unattended)", "Attics", "Stairways", "Unattended elevators",
                "Janitor’s closets")
                self.d["sellocation " + str(e)+nr] = ttk.OptionMenu(self.d["barrierf " + str(e)+nr],
                                                                 self.d["vselocation " + str(e)+nr], "Select Location",
                                                                 *self.uncontroll)
            elif self.d["area " + str(e)+nr].get() == "Supervised Area":
                self.supervised = ("Corridors", "Patient rooms", "Employee lounges", "Staff restooms", "Corridor doors")
                self.d["sellocation " + str(e)+nr] = ttk.OptionMenu(self.d["barrierf " + str(e)+nr],
                                                                 self.d["vselocation " + str(e)+nr], "Select Location",
                                                                 *self.supervised)
            else:
                self.d["sellocation " + str(e)+nr] = ttk.Combobox(self.d["barrierf " + str(e)+nr], textvariable=self.d["vselocation " + str(e)+nr], state="readonly",
                                        values=["Administrative or clerical offices", "Laboratories",
                                                "Pharmacies and other work areas fully occupied by an individual",
                                                "Receptionist areas", "Attended waiting rooms",
                                                "Children’s indoor play areas", "Adjacent x-ray rooms",
                                                "Film reading areas", "Nurse’s stations", "X-ray control rooms",
                                                "Rooms used for patient examinations and treatments", "Corridors",
                                                "Patient rooms", "Employee lounges", "Staff restooms", "Corridor doors",
                                                "Public toilets", "Unattended vending areas", "Storage  rooms",
                                                "Outdoor areas with seating", "Unattended waiting rooms",
                                                "Patient holding areas",
                                                "Outdoor areas with only transient pedestrian or vehicular traffic",
                                                "Unattended parking lots", "Vehicular drop off areas (unattended)",
                                                "Attics", "Stairways", "Unattended elevators", "Janitor’s closets"])

            self.d["sellocation " + str(e)+nr].grid(row=15, column=1, pady=10, padx=10, sticky="w")
            self.d["sellocation " + str(e) + nr].config(width=15)
        if self.d["area " + str(e) + nr].get() == "Cotrolled Area":
            self.d["dikeent " + str(e) + nr].destroy()
            self.d["dikeent {0}".format(e) + nr] = ttk.Entry(
                master=self.d["barrierf " + str(e) + nr], width=10)
            self.d["dikeent " + str(e) + nr].grid(row=16, column=1, pady=10, padx=10, sticky="w")
            self.d["dikeent "+str(e)+nr].insert(0, str(0.01))
        elif self.d["area " + str(e) + nr].get() == "Uncontrolled Area":
            self.d["dikeent " + str(e) + nr].destroy()
            self.d["dikeent {0}".format(e) + nr] = ttk.Entry(master=self.d["barrierf " + str(e) + nr], width=10)
            self.d["dikeent " + str(e) + nr].grid(row=16, column=1, pady=10, padx=10, sticky="w")
            self.d["dikeent "+str(e)+nr].insert(0, str(0.006))
        elif self.d["area " + str(e) + nr].get() == "Supervised Area":
            self.d["dikeent " + str(e) + nr].destroy()
            self.d["dikeent {0}".format(e) + nr] = ttk.Entry(master=self.d["barrierf " + str(e) + nr], width=10)
            self.d["dikeent " + str(e) + nr].grid(row=16, column=1, pady=10, padx=10, sticky="w")
            self.d["dikeent "+str(e)+nr].insert(0, str(0.006))
    def workload2(self,e,nr, t):
        if self.d["vrawork " + str(e)+nr].get() == 1:
            if self.d["numpapwe " + str(e)+nr] is not None:
                self.d["numpapwe " + str(e)+nr].destroy()
            if self.d["worentry " + str(e)+nr] is not None:
                self.d["worentry " + str(e)+nr].destroy()
            self.d["worentry " + str(e)+nr] = ttk.Entry(master=self.d["barrierf " + str(e) + nr], width=10)
            self.d["worentry " + str(e)+nr].grid(row=17, column=1, pady=5, padx=5)
        elif self.d["vrawork " + str(e)+nr].get() == 2:
            if self.d["worentry " + str(e)+nr] is not None:
                self.d["worentry " + str(e)+nr].destroy()
            if self.d["numpapwe " + str(e)+nr] is not None:
                self.d["numpapwe " + str(e)+nr].destroy()
            self.d["numpapwe " + str(e)+nr] = ttk.Entry(master=self.d["barrierf " + str(e) + nr], width=10)
            self.d["numpapwe " + str(e)+nr].grid(row=18, column=1, pady=5, padx=5, sticky="w")

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

    def barrier_sel(self, e,nr,t):
        if self.d["radiob_w "+str(e)+nr].get() == 1:
            if self.d["lau "+str(e)] is not None:
                self.d["lau " + str(e)].destroy()
                self.d["use_ent " + str(e)].destroy()
                self.d["presh " + str(e)].destroy()
                self.d["preunsh " + str(e)].destroy()
                if self.d["laks " + str(e) + nr] is not None:
                    self.d["laks " + str(e) + nr].destroy()
                    self.d["entk " + str(e) + nr].destroy()
            if self.d["leak " + str(e) + nr] is not None:
                if  self.d["airkerv " + str(e) + nr].get()== 1:
                    self.d["radside "+str(e)+nr].destroy()
                    self.d["radforward " +str(e)+nr].destroy()
                    self.d["leak " + str(e) + nr].destroy()
                    self.d["forw " + str(e) + nr].destroy()
                    self.d["side " + str(e) + nr].destroy()
                    self.d["write " + str(e) + nr].destroy()
                elif self.d["airkerv " + str(e) + nr].get()== 4:
                    self.d["leak " + str(e) + nr].destroy()
                    self.d["forw " + str(e) + nr].destroy()
                    self.d["side " + str(e) + nr].destroy()
                    self.d["write " + str(e) + nr].destroy()
                    self.d["laks " + str(e) + nr].destroy()
                    self.d["entk " + str(e) + nr].destroy()
                else:
                    self.d["leak " + str(e) + nr].destroy()
                    self.d["forw " + str(e) + nr].destroy()
                    self.d["side " + str(e) + nr].destroy()
                    self.d["write " + str(e) + nr].destroy()
            #=========use factor====================
            self.d["lau "+str(e)] = ttk.Label(master=self.d["barrierf " + str(e)+nr], style="AL.TLabel",
                                    text="Use Factor:")
            self.d["lau "+str(e)].grid(row=3, column=0, pady=10, padx=10, sticky="w")
            self.d["use_ent "+str(e)] = ttk.Entry(
                master=self.d["barrierf " + str(e)+nr], width=10)
            if e==1:
                if self.d["selxroom {0}".format(str(t))] is not None:
                    if self.d["vsexroom " + str(t)].get()=="Rad Room (floor or other barriers)":
                        self.d["use_ent " + str(e)].insert(0, str(0.89))
                else:
                    self.d["use_ent " + str(e)].insert(0, str(1))
            elif e==2:
                self.d["use_ent " + str(e)].insert(0, str(1/16))
            else:
                if self.d["selxroom {0}".format(str(t))] is not None:
                    if self.d["vsexroom " + str(t)].get()=="Rad Room (floor or other barriers)":
                        self.d["use_ent " + str(e)].insert(0, str(0.02))
                else:
                    self.d["use_ent " + str(e)].insert(0, str(1/4))
            self.d["use_ent " + str(e)].grid(row=3, column=1, pady=10, padx=10, sticky="w")
            #==========Preshielding===========
            self.d["presh "+str(e)]=ttk.Checkbutton(master=self.d["barrierf " + str(e)+nr], text= "Preshielding",
                                                    variable=self.d["preshvar "+str(e) + nr],
                                                    offvalue=0, onvalue=1, command=lambda: self.pres(e,nr))
            self.d["presh " + str(e)].grid(row=4, column=0, pady=10, padx=10, sticky="w")
            #===========unshielding air kerma=================
            self.d["preunsh " + str(e)] = ttk.Checkbutton(master=self.d["barrierf " + str(e) + nr], text="Unshielded air kerma",
                                                        variable=self.d["preshuns " + str(e) + nr], offvalue=0,
                                                        onvalue=1, command=lambda: self.uns(e, nr))
            self.d["preunsh " + str(e)].grid(row=4, column=1, pady=10, padx=10, sticky="w")


        elif self.d["radiob_w "+str(e)+nr].get() == 2:
            if self.d["leak " + str(e) + nr] is not None:
                self.d["leak " + str(e) + nr].destroy()
                self.d["side " + str(e) + nr].destroy()
                self.d["forw " + str(e) + nr].destroy()
                self.d["write " + str(e) + nr].destroy()
            if self.d["lau "+str(e)] is not None:
                self.d["lau " + str(e)].destroy()
                self.d["use_ent " + str(e)].destroy()
                self.d["preunsh " + str(e)].destroy()
                if  self.d["preshvar " + str(e) + nr].get()== 1:
                    self.d["radbucky " + str(e)].destroy()
                    self.d["radcross " + str(e)].destroy()
                    self.d["presh " + str(e)].destroy()
                elif self.d["preshvar " + str(e) + nr].get()== 0:
                    self.d["presh " + str(e)].destroy()
                if self.d["laks " + str(e) + nr] is not None:
                    self.d["laks " + str(e) + nr].destroy()
                    self.d["entk " + str(e) + nr].destroy()
            # ====================Leakage========================
            self.d["leak " + str(e) + nr] = ttk.Radiobutton(
                master=self.d["barrierf " + str(e) + nr],text="Leakage radiation",
                variable=self.d["airkerv " + str(e) + nr], value=1,
                 command=lambda : self.leakage(e, nr))
            self.d["leak " + str(e) + nr].grid(row=2, column=0, pady=10, padx=10, sticky="w")
            self.d["side " + str(e) + nr] = ttk.Radiobutton(master=self.d["barrierf " + str(e) + nr],
                text="Side-Scatter", variable=self.d["airkerv " + str(e) + nr],value=2,
                 command=lambda : self.leakage(e, nr))
            self.d["side " + str(e) + nr].grid(row=2, column=1, pady=10, padx=10, sticky="w")
            self.d["forw " + str(e) + nr] = ttk.Radiobutton(master=self.d["barrierf " + str(e) + nr],
                text="Forward/ Backscatter", variable=self.d["airkerv " + str(e) + nr], value=3,
                 command=lambda : self.leakage(e, nr))
            self.d["forw " + str(e) + nr].grid(row=3, column=0, pady=10, padx=10, sticky="w")
            self.d["write "+ str(e) + nr] = ttk.Radiobutton(master=self.d["barrierf " + str(e) + nr],
                text="Unshielded air kerma", variable=self.d["airkerv " + str(e) + nr], value=4,
                 command=lambda : self.leakage(e, nr))
            self.d["write " + str(e) + nr].grid(row=3, column=1, pady=10, padx=10, sticky="w")

    def uns(self,e,nr):
        if self.d["preshuns " + str(e) + nr].get()== 1:
            self.d["laks " + str(e) + nr] = ttk.Label(master=self.d["barrierf " + str(e) + nr], text="K\u209b\u2091 (mGy/patient):")
            self.d["laks " + str(e) + nr].grid(row=6, column=0, pady=10, padx=10, sticky="w")
            self.d["entk " + str(e) + nr] = ttk.Entry(master=self.d["barrierf " + str(e) + nr], width=10)
            self.d["entk " + str(e) + nr].grid(row=6, column=1, pady=10, padx=10, sticky="w")

        elif self.d["preshuns " + str(e) + nr].get()==0:
            if self.d["laks " + str(e) + nr] is not None:
                self.d["laks " + str(e) + nr].destroy()
                self.d["entk " + str(e) + nr].destroy()


    def numbmater(self,e,nr,t):
        if self.d["vselroom "+ str(t)].get()=="CT Room":
            if self.d["m "+ str(e) + nr]  < self.d["vnumbmat " +str(e)+nr].get():
                while self.d["m "+ str(e) + nr]  < self.d["vnumbmat " +str(e)+nr].get():
                    self.d["m " + str(e) + nr]+=1
                    self.mater = ("Lead", "Concrete")
                    self.d["vmater {0}".format(str(e))+str(self.d["m " + str(e) + nr])+nr] = StringVar()
                    self.d["mater {0}".format(str(e))+str(self.d["m " + str(e) + nr])] = ttk.OptionMenu(
                        self.d["barrierf " + str(e) + nr],
                        self.d["vmater " +str(e)+str(self.d["m " + str(e) + nr])+nr], "Select Material", *self.mater)
                    if self.d["m " + str(e) + nr] <3:
                        self.d["matlab {0}".format(str(e)) + str(self.d["m " + str(e) + nr])]\
                            =ttk.Label(self.d["barrierf " + str(e) + nr],text="#"+str(self.d["m " + str(e) + nr])+":")
                        self.d["matlab "+str(e) + str(self.d["m " + str(e) + nr])].\
                            grid(row=10, column= -1+self.d["m " + str(e) + nr], sticky="w")
                        self.d["mater " + str(e)+str(self.d["m " + str(e) + nr])].\
                            grid(row=10, column= -1+self.d["m " + str(e) + nr],pady=10, padx=25, sticky="s")

            else:
                while self.d["m " + str(e) + nr] > self.d[
                    "vnumbmat " + str(e) + nr].get():
                    self.d["mater "+str(e)+str(self.d["m " + str(e) + nr])].destroy()
                    self.d["matlab " + str(e) + str(self.d["m " + str(e) + nr])].destroy()
                    self.d["m " + str(e) + nr] -= 1
        else:
            if self.d["m "+ str(e) + nr]  < self.d["vnumbmat " +str(e)+nr].get():
                while self.d["m "+ str(e) + nr]  < self.d["vnumbmat " +str(e)+nr].get():
                    self.d["m " + str(e) + nr]+=1
                    self.mater = ("Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass", "Wood")
                    self.d["vmater {0}".format(str(e))+str(self.d["m " + str(e) + nr])+nr] = StringVar()
                    self.d["mater {0}".format(str(e))+str(self.d["m " + str(e) + nr])] = ttk.OptionMenu(
                        self.d["barrierf " + str(e) + nr],
                        self.d["vmater " +str(e)+str(self.d["m " + str(e) + nr])+nr], "Select Material", *self.mater)
                    if self.d["m " + str(e) + nr] <3:
                        self.d["matlab {0}".format(str(e)) + str(self.d["m " + str(e) + nr])]\
                            =ttk.Label(self.d["barrierf " + str(e) + nr],text="#"+str(self.d["m " + str(e) + nr])+":")
                        self.d["matlab "+str(e) + str(self.d["m " + str(e) + nr])].\
                            grid(row=10, column= -1+self.d["m " + str(e) + nr], sticky="w")
                        self.d["mater " + str(e)+str(self.d["m " + str(e) + nr])].\
                            grid(row=10, column= -1+self.d["m " + str(e) + nr],pady=5, padx=5, sticky="s")
                    elif 2<self.d["m "+ str(e) + nr] <5:
                        self.d["matlab {0}".format(str(e)) + str(self.d["m " + str(e) + nr])] = ttk.Label(
                            self.d["barrierf " + str(e) + nr], text="#" + str(self.d["m " + str(e) + nr]) + ":")
                        self.d["matlab " + str(e) + str(self.d["m " + str(e) + nr])].grid(row=11, column= -3+self.
                            d["m " + str(e) + nr], sticky="w")
                        self.d["mater " + str(e) + str(self.d["m " + str(e) + nr])].grid(row=11, column= -3+self.
                            d["m " + str(e) + nr ],pady=5, padx=5, sticky="s")
                    else:
                        self.d["matlab {0}".format(str(e)) + str(self.d["m " + str(e) + nr])] = ttk.Label(
                            self.d["barrierf " + str(e) + nr], text="#" + str(self.d["m " + str(e) + nr]) + ":")
                        self.d["matlab " + str(e) + str(self.d["m " + str(e) + nr])]. grid(row=12, column= -5+self.
                            d["m " + str(e) + nr], sticky="w")
                        self.d["mater " + str(e) + str(self.d["m " + str(e) + nr])].grid(row=12, column=-5 + self.d[
                            "m " + str(e) + nr], pady=5, padx=5, sticky="s")
            else:
                while self.d["m " + str(e) + nr] > self.d[
                    "vnumbmat " + str(e) + nr].get():
                    self.d["mater "+str(e)+str(self.d["m " + str(e) + nr])].destroy()
                    self.d["matlab " + str(e) + str(self.d["m " + str(e) + nr])].destroy()
                    self.d["m " + str(e) + nr] -= 1

    def pres(self,e,nr):
        if self.d["preshvar " + str(e) + nr].get()== 1:
            self.d["radbucky "+str(e)] = ttk.Radiobutton(master=self.d["barrierf " + str(e) + nr],
                variable=self.d["radiob_pre " + str(e)+nr], text="Bucky", value=1)
            self.d["radbucky " + str(e)].grid(row=5, column=0, pady=10, padx=10, sticky="w")
            self.d["radcross " +str(e)] = ttk.Radiobutton(master=self.d["barrierf " + str(e) + nr],
                variable=self.d["radiob_pre " + str(e)+nr], text="Cross-table", value=2)
            self.d["radcross " + str(e)].grid(row=5, column=1, pady=10, padx=10, sticky="w")

        elif self.d["preshvar "+str(e) + nr].get()==0:

            if self.d["radbucky " + str(e)] is not None:
                self.d["radbucky " + str(e)].destroy()
                self.d["radcross " +str(e)].destroy()

    def leakage(self,e,nr):
        if self.d["airkerv " + str(e) + nr].get()== 1:
            if self.d["radside " + str(e)+nr] is not None:
                self.d["radside " + str(e)+nr].destroy()
                self.d["radforward " +str(e)+nr].destroy()
                self.d["radleak " + str(e) + nr].destroy()
            if self.d["laks "+ str(e) + nr] is not None:
                self.d["laks " + str(e) + nr].destroy()
                self.d["entk " + str(e) + nr].destroy()
            self.d["radside "+str(e)+nr] = ttk.Radiobutton(master=self.d["barrierf " + str(e) + nr],
                variable=self.d["radiob_leak " + str(e)+nr], text="Leakage and Side-Scatter", value=1)
            self.d["radside " + str(e)+nr].grid(row=4, column=0, pady=10, padx=10, sticky="w")
            self.d["radforward " +str(e)+nr] = ttk.Radiobutton(master=self.d["barrierf " + str(e) + nr],
                variable=self.d["radiob_leak " + str(e)+nr], text="Leakage and Forward/ Backscatter", value=2)
            self.d["radforward " + str(e)+nr].grid(row=4, column=1, pady=10, padx=10, sticky="w")
            self.d["radleak " + str(e) + nr] = ttk.Radiobutton(master=self.d["barrierf " + str(e) + nr],
                                                                  variable=self.d["radiob_leak " + str(e) + nr],
                                                                  text="Only Leakage", value=0)
            self.d["radleak " + str(e) + nr].grid(row=5, column=0, pady=10, padx=10, sticky="w")

        elif self.d["airkerv " + str(e) + nr].get()== 4:
            if self.d["radside " + str(e)+nr] is not None:
                self.d["radside " + str(e)+nr].destroy()
                self.d["radforward " +str(e)+nr].destroy()
                self.d["radleak " + str(e) + nr].destroy()
            if self.d["laks "+ str(e) + nr] is not None:
                self.d["laks " + str(e) + nr].destroy()
                self.d["entk " + str(e) + nr].destroy()
            self.d["laks "+ str(e) + nr]=ttk.Label(master=self.d["barrierf " + str(e) + nr], text="K\u209b (mGy/patient):")
            self.d["laks "+ str(e) + nr].grid(row=4, column=0, pady=10, padx=10, sticky="w")
            self.d["entk "+ str(e) + nr]=ttk.Entry(master=self.d["barrierf " + str(e) + nr], width=10)
            self.d["entk " + str(e) + nr].grid(row=4, column=1, pady=10, padx=10, sticky="w")

        else:
            if self.d["radside " + str(e)+nr] is not None:
                self.d["radside " + str(e)+nr].destroy()
                self.d["radforward " +str(e)+nr].destroy()
                self.d["radleak " + str(e) + nr].destroy()
            if self.d["laks "+ str(e) + nr] is not None:
                self.d["laks " + str(e) + nr].destroy()
                self.d["entk " + str(e) + nr].destroy()

        # ============selection of X-ray room or X-ray tube=============
    def XrRoom1(self,e,nr, t):
        if self.d["vselxray " +str(e)+nr].get() == 1:
            if self.d["selxroom " +str(e)+nr] is not None:
                self.d["selxroom " +str(e)+nr].destroy()
            self.xrooms = (
            "Rad Room (chest bucky)", "Rad Room (floor or other barriers)", "Rad Room (all barriers)",
            "Fluoroscopy Tube (R&F room)","Rad Tube (R&F room)", "Chest Room", "Mammography Room", "Cardiac Angiography",
            "Peripheral Angiography")
            self.d["vsexroom {0}".format(str(e))+nr] = StringVar()
            self.d["selxroom " +str(e)+nr] = ttk.OptionMenu(self.d["barrierf " + str(e) + nr], self.d["vsexroom " + str(e)+nr],
                                                          "Select X-ray room", *self.xrooms)
            self.d["selxroom " +str(e)+nr].grid(row=16, column=0, columnspan=2, pady=10, padx=10, sticky="w")
        elif self.d["vselxray " +str(e)+nr].get() == 2:
            if self.d["selxroom " +str(e)+nr] is not None:
                self.d["selxroom " +str(e)+nr].destroy()
            self.d["vsexroom {0}".format(str(e))+nr] = IntVar(value=25)
            self.d["selxroom "+str(e)+nr] = ttk.Spinbox(master=self.d["barrierf " + str(e) + nr], from_=25, to=150,
                                                       increment=5, textvariable=self.d["vsexroom " + str(e)+nr],
                                                       width=10)
            self.d["selxroom " +str(e)+nr].grid(row=16, column=1, columnspan=2, pady=10, padx=10, sticky="w")