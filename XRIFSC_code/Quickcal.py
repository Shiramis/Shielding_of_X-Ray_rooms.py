from tkinter import *
from tkinter import ttk

class dquick():

    def quickcal(self):
        self.depbutton.destroy()
        self.roombutton.destroy()
        self.CTbutton.destroy()
        self.quickbutton.destroy()
        self.chooseCal.destroy()
        self.f1 = None
        self.entry1 = None
        self.f2 = None
        self.f6 = None
        self.entry2 = None
        self.frame_right = None
        self.om1 = None
        self.om2=None
        self.op = None
        self.label_ex = None
        self.entryex = None
        self.om4 = None
        self.label_ex1 = None
        self.entryex1 = None
        self.om41 = None
        self.label_ex2 = None
        self.entryex2 = None
        self.om42 = None
        self.entry3= None
        self.lau =None
        self.leak = None
        self.radside= None
        self.radforward=None
        self.radiob_leak = IntVar(value=0)
        self.leakvar = IntVar(value=0)
        self.preshvar=IntVar(value=0)
        self.radiob_pre=IntVar(value=0)
        # ===========Parameters tab==============
        if self.depnote is None:
            self.depnote = ttk.Notebook(self.new_main_Frame, style="AL.TNotebook")
            self.depnote.configure(width=955, height=728)
            self.depnote.grid(row=0, sticky="w")
        self.quickf = ttk.Frame(self.depnote)
        self.quickf.pack(fill=BOTH, expand=1)
        self.depnote.add(self.quickf, text="Barrier")
        #=======Scroll Bar quick=========
        self.quickcanv = Canvas(self.quickf)

        self.xscrollroom = ttk.Scrollbar(self.quickf, orient=HORIZONTAL, command=self.quickcanv.xview)
        self.xscrollroom.pack(side=BOTTOM, fill=X)
        self.yscrollroom = ttk.Scrollbar(self.quickf, orient=VERTICAL, command=self.quickcanv.yview)
        self.yscrollroom.pack(side=RIGHT, fill=Y)
        self.quickcanv.configure(yscrollcommand=self.yscrollroom.set, xscrollcommand=self.xscrollroom.set, bg="#f6f8f8")
        self.quickcanv.pack(side=LEFT, fill=BOTH, expand=1)
        self.parframe = ttk.Frame(self.quickcanv)
        self.parframe.bind('<Configure>',
                                         lambda e: self.quickcanv.configure(scrollregion=self.quickcanv.bbox("all")))
        self.quickcanv.create_window((0, 0), window=self.parframe, anchor="nw")
        # ========Frames top and left========================================
        self.frame_top = ttk.LabelFrame(master=self.parframe, style='BO.TFrame', width=400, height=150)
        self.frame_top.grid(row=0, column=1, sticky="nswe")
        self.frame_left = ttk.LabelFrame(master=self.parframe, style='BO.TFrame', width=400, height=150)
        self.frame_left.grid(row=0, column=0, sticky="nswe")


        self.label_B = ttk.Label(master=self.frame_top, style="BL.TLabel", text="Select Barrier Type")
        self.label_B.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        #======Close button====================
        self.closBut = ttk.Button(master=self.parframe, text="X",width=4,command=lambda :self.closq() )
        self.closBut.grid(row=0, column=1,columnspan=3, sticky="ne")

        # ==============Material================
        self.var_om3 = StringVar()
        self.om3 = ttk.Combobox(master=self.frame_left, textvariable=self.var_om3,state="readonly",
                                values=["Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass", "Wood"])
        self.om3.grid(row=4, column=0, pady=10, padx=20, sticky="w")
        self.om3.set("Select Material")

        # =============Secondary air kerma gray in area==============
        self.f4 = ttk.Label(master=self.frame_left, style="AL.TLabel", text="Design Kerma goal:")
        self.f4.grid(row=8, column=0, pady=0, padx=20, sticky="we")
        self.entry4 = ttk.Entry(master=self.frame_left, width=10)
        self.entry4.grid(row=8, column=1, columnspan=2, pady=20, padx=20, sticky="w")
        # ================Workload===========================================
        self.label_GP = ttk.Label(master=self.frame_left, style="BL.TLabel", text="Workload:")
        self.label_GP.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        # =================Room or kV=====================
        self.radio_var = IntVar(value=0)
        self.radbut1 = ttk.Radiobutton(master=self.frame_left, variable=self.radio_var, text="Select Room", value=1,
                                       command=self.Room)
        self.radbut1.grid(row=1, column=0, pady=10, padx=10, sticky="w")

        self.radbut2 = ttk.Radiobutton(master=self.frame_left, variable=self.radio_var, text="Give kV", value=2,
                                       command=self.kV)
        self.radbut2.grid(row=1, column=1, pady=10, padx=10, sticky="w")
        #==========Write workload=============
        self.worentry  = None
        self.vrawork = IntVar(value=0)
        self.raworkl = ttk.Radiobutton(master=self.frame_left, variable=self.vrawork,
                                       text="Write total Workload (mA min/week):", value=1,
                                       command=lambda: self.workloadq())
        self.raworkl.grid(row=3, column=0, pady=5, padx=5, sticky="w")
        # ===========Number of patiets per week==================================
        self.ranumb = ttk.Radiobutton(master=self.frame_left, text="or the number of patients per week:",
                                      variable=self.vrawork, value=2, command=lambda: self.workloadq())
        self.ranumb.grid(row=4, column=0, pady=5, padx=5, sticky="w")

        """# =============Checkbox existing barrier==========
        self.vare = IntVar(value=0)
        self.check_ex = ttk.Checkbutton(master=self.frame_top, text="Existing Barrier", variable=self.vare, onvalue=1,
                                        offvalue=0, command=self.radb)
        self.check_ex.grid(row=2, column=0, pady=10, padx=10, sticky="w")"""
        #============Occupancy Factor=========
        self.title_ocupat = ttk.Label(master=self.frame_left, style="BL.TLabel",
                                      text="Occupancy Factor (T)")
        self.title_ocupat.grid(row=5, column=0, pady=5, padx=5, sticky="w")
        # =========Classify area=============
        self.varea  = StringVar()
        self.area = ttk.Combobox(master=self.frame_left,
            textvariable=self.varea, values=["Cotrolled Area", "Uncontrolled Area", "Supervised Area"],
            state="readonly")
        self.area.grid(row=5, column=1, pady=5, padx=5, sticky="w")
        self.area.set("Classify the area")
        # ====radiobutton_occupancy factor==================
        self.vraoccup  = IntVar(value=0)
        self.raoccup = ttk.Radiobutton(master=self.frame_left, variable=self.vraoccup ,
                                       text="Write occupancy factor (T):", value=1, command=lambda: self.occupationq())
        self.raoccup.grid(row=6, column=0, pady=10, padx=10, sticky="w")
        self.occupentry = None
        self.raseloccup = ttk.Radiobutton(master=self.frame_left, text="or select Location "
                                                                                   "[suggested NCRP 147]",
                                          variable=self.vraoccup , value=2,
                                          command=lambda: self.occupationq())
        self.raseloccup.grid(row=7, column=0, pady=10, padx=10, sticky="w")

        # ================Barries==============================
        self.radio_var2 = IntVar(value=0)
        self.rad3 = ttk.Radiobutton(master=self.frame_top, variable=self.radio_var2, text="Primary Barrier", value=1,
                                    command=self.radb)
        self.rad3.grid(row=1, column=0, pady=10, padx=10, sticky="w")
        self.rad4 = ttk.Radiobutton(master=self.frame_top, variable=self.radio_var2, text="Secondary Barrier", value=2,
                                    command=self.radb)
        self.rad4.grid(row=1, column=1, pady=10, padx=10, sticky="w")
        # ==============Material================
        self.var_om3 = StringVar()
        self.om3 = ttk.Combobox(master=self.frame_top, textvariable=self.var_om3, state="readonly",
                                values=["Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass", "Wood"])
        self.om3.grid(row=2, column=0, pady=10, padx=20, sticky="w")
        self.om3.set("Select Material")

        # ===========Button============
        self.b = ttk.Button(master=self.frame_top, text="Calculate", style="TButton", command=self.calbutton)
        self.b.grid(row=10, column=1, pady=5, padx=5)

        # =========defs for parameter notebook===========
    def kV(self):
        if self.om1 is not None:
            self.om1.destroy()
        self.om1 = IntVar(value=25)
        self.op = ttk.Spinbox(master=self.frame_left, from_=25, to=150, increment=5, textvariable=self.om1,
                              width=10)
        self.op.grid(row=2, column= 1, pady=10, padx=20, sticky="w")

    def Room(self):
        if self.op is not None:
            self.op.destroy()
        self.var_om1 = StringVar()
        self.om1 = ttk.Combobox(master=self.frame_left, textvariable=self.var_om1, state="readonly",
                                values=["Rad Room (all barriers)","Rad Room (chest bucky)","Rad Room (floor or other barriers)",
                                        "Fluoroscopy Tube (R&F room)","Rad Tube (R&F room)","Chest Room",
                                        "Mammography Room", "Cardiac Angiography", "Peripheral Angiography"])
        self.om1.grid(row=2, column=0, pady=10, padx=20, sticky="w")
        self.om1.set("Select X-ray Room")

    def radb(self):  # Selecting the barrier type and type the distance
        if self.radio_var2.get() == 1:
            if self.lau is not None:  # destroy if any label on the grid existing
                self.f1.destroy()
                self.entry1.destroy()
                self.lau.destroy()
                self.use_ent.destroy()
                self.presh.destroy()
            if self.leak is not None:
                self.f2.destroy()
                self.entry2.destroy()
                if self.leakvar.get() == 1:
                    self.radside.destroy()
                    self.radforward.destroy()
                    self.leak.destroy()
                elif self.leakvar.get() == 0:
                    self.leak.destroy()
            # =========use factor====================
            self.lau= ttk.Label(master=self.frame_top, style="AL.TLabel",
                                                text="Use Factor:")
            self.lau.grid(row=3, column=0, pady=10, padx=10, sticky="w")
            self.use_ent= ttk.Entry(master=self.frame_top, width=10)
            if self.om1 is not None:
                if self.var_om1.get() == "Rad Room (floor or other barriers)":
                        self.use_ent.insert(0, str(0.89))
                else:
                    self.use_ent.insert(0, str(1))
            else:
                self.use_ent.insert(0, str(1))
            self.use_ent.grid(row=3, column=1, pady=10, padx=10, sticky="w")
            # ==========Preshielding===========
            self.presh = ttk.Checkbutton(master=self.frame_top,
                                                        text="Preshielding",
                                                        variable=self.preshvar, offvalue=0,
                                                        onvalue=1, command=lambda: self.presq())
            self.presh.grid(row=4, column=0, pady=10, padx=10, sticky="w")
            self.f1 = ttk.Label(master=self.frame_top, style="AL.TLabel",
                                text="Distance (m):")
            self.f1.grid(row=6, column=0, pady=0, padx=20, sticky="we")
            self.entry1 = ttk.Entry(master=self.frame_top, width=10)
            self.entry1.grid(row=6, column=1, pady=10, padx=10, sticky="w")

        elif self.radio_var2.get() == 2:
            if self.f1 is not None:  # destroy if any label on the grid existing
                self.f1.destroy()
                self.entry1.destroy()
                self.lau.destroy()
                self.use_ent.destroy()
                if self.preshvar.get() == 1:
                    self.radbucky.destroy()
                    self.radcross.destroy()
                    self.presh.destroy()
                elif self.preshvar.get() == 0:
                    self.presh.destroy()
            if self.f2 is not None:
                self.f2.destroy()
                self.entry2.destroy()
                self.leak.destroy()
            # ====================Leakage========================
            self.leak = ttk.Checkbutton(master=self.frame_top,
                text="Leakage radiation", variable=self.leakvar, onvalue=1, offvalue=0,
                command=lambda: self.leakageq())
            self.leak.grid(row=3, column=0, pady=10, padx=10, sticky="w")

            self.f2 = ttk.Label(master=self.frame_top, style="AL.TLabel",
                                text="Distance (m):")
            self.f2.grid(row=6, column=0, pady=0, padx=20, sticky="we")
            self.entry2 = ttk.Entry(master=self.frame_top, width=10)
            self.entry2.grid(row=6, column=1, pady=10, padx=10, sticky="w")

        # ===============if select another Barrier============
        """if self.vare.get() == 1:
            if (self.radio_var2.get() == 1) or (self.radio_var2.get() == 2):
                if self.label_ex1 is not None:
                    self.label_ex1.destroy()
                    self.entryex1.destroy()
                    self.om41.destroy()
                    self.label_ex2.destroy()
                    self.entryex2.destroy()
                    self.om42.destroy()
                if self.label_ex is not None:
                    self.label_ex.destroy()
                    self.entryex.destroy()
                    self.om4.destroy()
                self.label_ex = ttk.Label(master=self.frame_top, style="AL.TLabel", text="Existing Barrier in mm:")
                self.label_ex.grid(row=3, column=0, sticky="w")
                self.entryex = ttk.Entry(master=self.frame_top, width=10)
                self.entryex.grid(row=3, column=1, pady=10, padx=10, sticky="w")
                self.varom4 = StringVar()
                self.om4 = ttk.Combobox(master=self.frame_top, textvariable=self.varom4,
                                        values=["Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass",
                                                "Wood"])
                self.om4.grid(row=4, column=0, pady=10, padx=10, sticky="w")
                self.om4.set("Select Material")

            elif self.radio_var2.get() == 3:
                if self.label_ex is not None:
                    self.label_ex.destroy()
                    self.entryex.destroy()
                    self.om4.destroy()
                self.label_ex1 = ttk.Label(master=self.frame_top, style="AL.TLabel",
                                           text="Existing Primary Barrier in mm:")
                self.label_ex1.grid(row=3, column=0, sticky="w")
                self.entryex1 = ttk.Entry(master=self.frame_top, width=10)
                self.entryex1.grid(row=3, column=1, sticky="w")
                self.varom41 = StringVar()
                self.om41 = ttk.Combobox(master=self.frame_top, textvariable=self.varom41,
                                         values=["Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass",
                                                 "Wood"], width=30)
                self.om41.grid(row=4, pady=10, padx=10, sticky="nswe")
                self.om41.set("Select Material for Primary Barrier")
                self.label_ex2 = ttk.Label(master=self.frame_top, style="AL.TLabel",
                                           text="Existing Secondary Barrier in mm:")
                self.label_ex2.grid(row=5, column=0, sticky="w")
                self.entryex2 = ttk.Entry(master=self.frame_top, width=10)
                self.entryex2.grid(row=5, column=1, sticky="w")
                self.varom42 = StringVar()
                self.om42 = ttk.Combobox(master=self.frame_top, textvariable=self.varom42,
                                         values=["Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass",
                                                 "Wood"], width=30)
                self.om42.grid(row=6, pady=10, padx=10, sticky="nswe")
                self.om42.set("Select Material for Secondary Barrier")

        else:
            if self.label_ex is not None:
                self.label_ex.destroy()
                self.entryex.destroy()
                self.om4.destroy()
            if self.label_ex1 is not None:
                self.label_ex1.destroy()
                self.entryex1.destroy()
                self.om41.destroy()
                self.label_ex2.destroy()
                self.entryex2.destroy()
                self.om42.destroy()"""

        ###=============Calculations===============
    def calbutton(self):
        if self.frame_right is not None:
            self.frame_right.destroy()
        self.frame_right = ttk.LabelFrame(master=self.parframe, style='BO.TFrame')
        self.frame_right.grid(row=1, column=1, sticky="s")
        # ================= Outputs ============================
        # First must fill every entry elsewhere warnings!!
        if self.om1 is None:
            self.fom1 = ttk.Label(master=self.frame_right, style="BL.TLabel", text="Select Room or Give kV")
            self.fom1.grid(row=0, column=0, pady=0, padx=20, sticky="w")
        elif self.om1.get() == "Select X-Ray Room":
            self.fom1 = ttk.Label(master=self.frame_right, style="BL.TLabel", text="Select Room")
            self.fom1.grid(row=0, column=0, pady=0, padx=20, sticky="w")
        if self.vraoccup.get() == 2:
            if self.var_om2.get() == "Select Location":
                self.fom2 = ttk.Label(master=self.frame_right, style="BL.TLabel", text="Select Location")
                self.fom2.grid(row=1, column=0, pady=0, padx=20, sticky="w")
        if self.om3.get() == "Select Material":
            self.fom3 = ttk.Label(master=self.frame_right, style="BL.TLabel", text="Select type of Material")
            self.fom3.grid(row=2, column=0, pady=0, padx=20, sticky="w")
        if self.vrawork.get() == 2:
            if self.entry3.get() == "":
                self.fe3 = ttk.Label(master=self.frame_right, style="BL.TLabel",
                                     text="Type Number of Patients per Week")
                self.fe3.grid(row=3, column=0, pady=0, padx=20, sticky="w")
        if self.entry4.get() == "":
            self.fe4 = ttk.Label(master=self.frame_right, style="BL.TLabel", text="Type Design Kerma goal")
            self.fe4.grid(row=4, column=0, pady=0, padx=20, sticky="w")
        if self.radio_var2.get() == 0:
            self.f6 = ttk.Label(master=self.frame_right, style="BL.TLabel", text="Select Barrier type")
            self.f6.grid(row=5, column=0, pady=0, padx=20, sticky="w")
        else:
            if self.radio_var2.get() == 1:
                if self.entry1.get() == "":
                    self.f6 = ttk.Label(master=self.frame_right, style="BL.TLabel", text="Type the distance from "
                                                                                         "source to Primary Barrier")
                    self.f6.grid(row=5, column=0, pady=0, padx=20, sticky="w")
                else:
                    self.labelP = ttk.Label(master=self.frame_right, style="BL.TLabel", text="Primary Barrier:")
                    self.labelP.grid(row=0, column=0, pady=10, padx=10)
                    self.primary()
            elif self.radio_var2.get() == 2:
                if self.entry2.get() == "":
                    self.f6 = ttk.Label(master=self.frame_right, style="BL.TLabel", text="Type the distance from "
                                                                                         "source to Secondary Barrier")
                    self.f6.grid(row=5, column=0, pady=0, padx=20, sticky="w")
                else:
                    self.labelS = ttk.Label(master=self.frame_right, style="BL.TLabel", text="Secondary Barrier:")
                    self.labelS.grid(row=2, column=0, pady=10, padx=10)
                    self.secondary()
            elif self.radio_var2.get() == 3:
                if self.entry1.get() == "":
                    self.f6 = ttk.Label(master=self.frame_right, style="BL.TLabel", text="Type the distance from "
                                                                                         "source to Primary Barrier")
                    self.f6.grid(row=5, column=0, pady=0, padx=20, sticky="w")
                if self.entry2.get() == "":
                    self.fe2 = ttk.Label(master=self.frame_right, style="BL.TLabel", text="Type the distance from "
                                                                                          "source to Secondary Barrier")
                    self.fe2.grid(row=6, column=0, pady=0, padx=20, sticky="w")
                else:
                    self.labelP = ttk.Label(master=self.frame_right, style="BL.TLabel", text="Primary Barrier:")
                    self.labelP.grid(row=0, column=0, pady=10, padx=10)
                    self.labelS = ttk.Label(master=self.frame_right, style="BL.TLabel", text="Secondary Barrier:")
                    self.labelS.grid(row=2, column=0, pady=10, padx=10)
                    self.primary()
                    self.secondary()

    def workloadq(self):
        if self.vrawork.get() == 1:
            if self.entry3 is not None:
                self.entry3.destroy()
            if self.worentry is not None:
                self.worentry.destroy()
            self.worentry  = ttk.Entry(master=self.frame_left, width=10)
            self.worentry.grid(row=3, column=1, pady=5, padx=5)
        elif self.vrawork.get() == 2:
            if self.worentry is not None:
                self.worentry.destroy()
            if self.entry3 is not None:
                self.entry3.destroy()
            self.entry3 = ttk.Entry(master=self.frame_left, width=10)
            self.entry3.grid(row=4, column=1, pady=5, padx=5, sticky="w")

    def occupationq(self):
        if self.vraoccup.get() == 1:
            if self.om2  is not None:
                self.om2.destroy()
            if self.occupentry is not None:
                self.occupentry.destroy()
            self.var_om2 = StringVar()
            self.occupentry = ttk.Entry(master=self.frame_left, width=10)
            if self.varea.get() == "Cotrolled Area":
                self.occupentry.insert(0,str(1))
            elif self.varea.get() == "Uncontrolled Area":
                self.occupentry.insert(0,str(1/16))
            elif self.varea.get() == "Supervised Area":
                self.occupentry.insert(0,str(1/4))
            self.occupentry.grid(row=6, column=1, pady=5, padx=5)
        elif self.vraoccup.get() == 2:
            if self.occupentry is not None:
                self.occupentry.destroy()
            if self.om2 is not None:
                self.om2.destroy()
            self.var_om2 = StringVar()
            if self.varea.get() == "Cotrolled Area":
                self.control = ("Administrative or clerical offices", "Laboratories",
                                "Pharmacies and other work areas fully occupied by an individual", "Receptionist areas",
                                "Attended waiting rooms", "Children’s indoor play areas", "Adjacent x-ray rooms",
                                "Film reading areas", "Nurse’s stations", "X-ray control rooms",
                                "Rooms used for patient examinations and treatments")
                self.om2 = ttk.OptionMenu(self.frame_left,
                                                                 self.var_om2, "Select Location",
                                                                 *self.control)
            elif self.varea.get() == "Uncontrolled Area":
                self.uncontroll = (
                "Public toilets", "Unattended vending areas", "Storage  rooms", "Outdoor areas with seating",
                "Unattended waiting rooms", "Patient holding areas",
                "Outdoor areas with only transient pedestrian or vehicular traffic", "Unattended parking lots",
                "Vehicular drop off areas (unattended)", "Attics", "Stairways", "Unattended elevators",
                "Janitor’s closets")
                self.om2 = ttk.OptionMenu(self.frame_left,
                                                                 self.var_om2, "Select Location",
                                                                 *self.uncontroll)
            elif self.varea.get() == "Supervised Area":
                self.supervised = ("Corridors", "Patient rooms", "Employee lounges", "Staff restooms", "Corridor doors")
                self.om2 = ttk.OptionMenu(self.frame_left,
                                                                 self.var_om2, "Select Location",
                                                                 *self.supervised)
            else:
                self.om2 = ttk.Combobox(self.frame_left, textvariable=self.var_om2, state="readonly",
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
                self.om2.set("Select Location")
            self.om2.config(width=15)
            self.om2.grid(row=7, column=1, columnspan=2, pady=5, padx=5, sticky="w")
        if self.varea.get() == "Cotrolled Area":
            self.entry4.destroy()
            self.entry4 = ttk.Entry(master=self.frame_left, width=10)
            self.entry4.grid(row=8, column=1, pady=5, padx=5, sticky="w")
            self.entry4.insert(0, str(0.01))
        elif self.varea.get() == "Uncontrolled Area":
            self.entry4.destroy()
            self.entry4 = ttk.Entry(master=self.frame_left, width=10)
            self.entry4.grid(row=8, column=1, pady=5, padx=5, sticky="w")
            self.entry4.insert(0, str(0.006))
        elif self.varea.get() == "Supervised Area":
            self.entry4.destroy()
            self.entry4 = ttk.Entry(master=self.frame_left, width=10)
            self.entry4.grid(row=8, column=1, pady=5, padx=5, sticky="w")
            self.entry4.insert(0, str(0.006))
    def presq(self):
        if self.preshvar.get()== 1:
            self.radbucky= ttk.Radiobutton(master=self.frame_top,
                variable=self.radiob_pre, text="Bucky", value=1)
            self.radbucky.grid(row=5, column=0, pady=10, padx=10, sticky="w")
            self.radcross = ttk.Radiobutton(master=self.frame_top,
                variable=self.radiob_pre , text="Cross-table", value=2)
            self.radcross .grid(row=5, column=1, pady=10, padx=10, sticky="w")
        elif self.preshvar.get()==0:
            if self.radbucky  is not None:
                self.radbucky .destroy()
                self.radcross .destroy()
    def leakageq(self):
        if self.leakvar.get()== 1:
            self.radside = ttk.Radiobutton(master=self.frame_top,
                variable=self.radiob_leak, text="Side-Scatter", value=1)
            self.radside.grid(row=4, column=0, pady=10, padx=10, sticky="w")
            self.radforward = ttk.Radiobutton(master=self.frame_top,
                variable=self.radiob_leak, text="Forward/ Backscatter", value=2)
            self.radforward.grid(row=4, column=1, pady=10, padx=10, sticky="w")

        elif self.leakvar.get()==0:
            if self.radside is not None:
                self.radside.destroy()
                self.radforward.destroy()
    def closq(self):
        self.quickf.destroy()
        if self.depframe is None and self.roomframe is None:
            self.depnote.destroy()
            self.depnote = None
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