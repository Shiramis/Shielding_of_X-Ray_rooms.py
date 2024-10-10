import tkinter
from tkinter import *
from tkinter import ttk
import os
import xlsxwriter

class droom():
    # ============creating def for Room notebook===================================
    def creatroom(self):
        self.depbutton.destroy()
        self.roombutton.destroy()
        self.CTbutton.destroy()
        #self.quickbutton.destroy()
        self.chooseCal.destroy()
        p = "Design x-ray room"
        self.i += 1
        t = self.i
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
        self.var[f"vselroom {self.i}"] = StringVar(value = "X-Ray room")
        self.ent[f"name_room {self.i}"] = StringVar(value = "X-Ray Room")
        self.d[f"run {self.i}"] = False
        self.desroom(self.i)
        self.roomsframe.destroy()

        '''#======Room scrollbar=========
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
        

        #==========αρχικοποίηση τιμών =================
        self.d["selxroom {0}".format(str(t))] = None
        self.d["numpapwl {0}".format(str(t))] = None
        self.d["numpapwe {0}".format(str(t))] = None
        self.d["sellocation {0}".format((str(t)))] = None
        self.ep = 1
        self.d["x {0}".format(str(t))] = 0

        self.var["vselroom {0}".format(str(t))] = StringVar()
        self.d["selroom {0}".format(str(t))] = ttk.Combobox(master=self.d["frame_1 " + str(t)],
                                                            textvariable=self.var["vselroom " + str(t)],
                                                            values=["X-Ray room", "From X-Ray room"], state="readonly")
        self.d["selroom {0}".format(str(t))].set("X-Ray room")
        self.d["nr {0}".format(str(t))]= "Design x-ray room"
        self.d["noteb {0}".format(str(t) + self.d["nr " + str(t)])] = ttk.Notebook(self.d["frame_1 " + str(t)],
                                                                                   style="BL.TNotebook")

        # ==============Number of Barriers in the Room==========
        self.lanumwall = ttk.Label(master=self.d["frame_1 " + str(t)], style="AL.TLabel", text="Number of Barriers")
        self.lanumwall.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        self.var["vnumwall {0}".format(str(t))] = IntVar(value=7)
        self.d["numwall {0}".format(str(t))] = ttk.Spinbox(master=self.d["frame_1 " + str(t)],
                                                           textvariable=self.var["vnumwall " + str(t)], from_=7, to=50,
                                                           width=5, command=lambda: self.barriers(t))
        self.d["numwall " + str(t)].grid(row=0, column=1, pady=10, padx=10, sticky="w")
        self.barriers(t)
        #======Export to excel========
        self.exp_but = ttk.Button(master=self.d["frame_1 " + str(t)], text="Export to Excel", command=lambda : self.exp_dep(t))
        self.exp_but.grid(row=0, column=5, pady=10, padx=10, sticky="w")
        # ==========Results==============
        self.d["resframe {0}".format(str(t))] = ttk.Frame(self.resnote)
        self.d["resframe " + str(t)].pack()
        self.resnote.add(self.d["resframe " + str(t)], text="Results of X-Ray Room" )

        # ======Results scrollbar=========
        self.rescanv = Canvas(self.d["resframe " + str(t)])
        self.rescanv.pack(side=LEFT, fill=BOTH, expand=1)
        self.scrollres = ttk.Scrollbar(self.d["resframe " + str(t)], orient=VERTICAL, command=self.rescanv.yview)
        self.scrollres.pack(side=RIGHT, fill=Y)
        self.rescanv.configure(yscrollcommand=self.scrollres.set, bg="#f6f8f8")
        # =========Results tab===========================
        self.d["resultframe {0}".format(str(t))+p] = ttk.Frame(self.rescanv)
        self.d["resultframe " + str(t)+p].bind('<Configure>',
                                             lambda e: self.rescanv.configure(scrollregion=self.rescanv.bbox("all")))
        self.rescanv.create_window((0, 0), window=self.d["resultframe " + str(t)+p], anchor="nw")
        self.reshield = ttk.Label(self.d["resultframe " + str(t)+p], style="BL.TLabel", text="The Shielding of:")
        self.reshield.grid(sticky="w")
        #======Destroy button======
        self.closBut = ttk.Button(self.roomframe, text="X", width=4, command=lambda:self.closeroom(t) )
        self.closBut.pack()'''

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
