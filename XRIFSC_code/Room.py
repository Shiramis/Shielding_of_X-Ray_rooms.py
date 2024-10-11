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
