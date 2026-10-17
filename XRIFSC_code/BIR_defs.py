import tkinter
import subprocess
from tkinter import *
from tkinter import ttk

class BIR():

    def desroom(self,t):

        self.ep = 1
        # ==============Number of Barriers in the Room==========
        self.lanumwall = ttk.Label(master=self.d["frame_1 " + str(t)], style="AL.TLabel", text="Number of Barriers")
        self.lanumwall.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        self.d["vnumwall {0}".format(str(t))] = IntVar(value=7)
        self.d["numwall {0}".format(str(t))] = ttk.Spinbox(master=self.d["frame_1 " + str(t)],
                                                           textvariable=self.d["vnumwall " + str(t)], from_=7, to=50,
                                                           width=5)
        self.d["numwall " + str(t)].grid(row=0, column=1, pady=10, padx=10, sticky="w")
        self.d["butwall {0}".format(str(t))] = ttk.Button(master=self.d["frame_1 " + str(t)], text="Ok", width=5,
                                                          command=lambda: self.barriers(t))
        self.d["butwall " + str(t)].grid(row=0, column=2, pady=10, padx=10, sticky="w")
        self.d["noteb {0}".format(str(t)) + self.d["name_room " + str(t)].cget("text")] = ttk.Notebook(
            self.d["frame_1 " + str(t)], style="BL.TNotebook")
        # ==============Number of sources============
        self.lanumsources = ttk.Label(master=self.d["frame_1 " + str(t)], style="AL.TLabel",
                                      text="Number of Sources in the room")
        self.lanumsources.grid(row=1, column=0, pady=10, padx=10, sticky="w")
        self.d["vnumsources {0}".format(str(t))] = IntVar(value=0)
        self.numsources = ttk.Spinbox(master=self.d["frame_1 " + str(t)], textvariable=self.d["vnumsources " + str(t)],
                                      from_=0, to=10, width=5)
        self.numsources.grid(row=1, column=1, pady=10, padx=10, sticky="w")
        self.d["butsources {0}".format(str(t))] = ttk.Button(master=self.d["frame_1 " + str(t)], text="Ok", width=5,
                                                             command=lambda: self.sources(t))
        self.d["butsources " + str(t)].grid(row=1, column=2, pady=10, padx=10, sticky="w")
        self.d["noteso {0}".format(str(t))] = ttk.Notebook(self.d["frame_1 " + str(t)], style="BL.TNotebook")
        # =========Occupation Factor=================
        self.title_ocupat = ttk.Label(master=self.d["frame_1 " + str(t)], style="BL.TLabel",
                                      text="Occupancy Factor (T)")
        self.title_ocupat.grid(row=2, column=0, pady=10, padx=10, sticky="w")
        self.d["vraoccup {0}".format(str(t))] = IntVar(value=0)
        self.raoccup = ttk.Radiobutton(master=self.d["frame_1 " + str(t)], variable=self.d["vraoccup " + str(t)],
                                       text="Write occupancy factor (T):", value=1, command=lambda: self.occupation(t))
        self.raoccup.grid(row=3, column=0, pady=10, padx=10, sticky="w")
        self.d["occupentry {0}".format(str(t))] = None
        self.raseloccup = ttk.Radiobutton(master=self.d["frame_1 " + str(t)], text="or select Location",
                                          variable=self.d["vraoccup " + str(t)], value=2,
                                          command=lambda: self.occupation(t))
        self.raseloccup.grid(row=4, column=0, pady=10, padx=10, sticky="w")


    def sources(self, t):
        if self.d["y " + str(t)] < self.d["vnumsources " + str(t)].get():
            while self.d["y " + str(t)] < self.d["vnumsources " + str(t)].get():
                self.d["y " + str(t)] += 1
                self.d["sourcef {0}".format(str(self.d["y " + str(t)]))] = ttk.Frame(self.d["noteso " + str(t)], width=180)
                self.d["sourcef " + str(self.d["y " + str(t)])].pack()

                self.d["lab_sour {0}".format(str(t))] = Label(text="Source " + str(self.d["y " + str(t)]))
                self.d["noteso " + str(t)].add(self.d["sourcef " + str(self.d["y " + str(t)])],
                                                  text="Source " + str(self.d["y " + str(t)]))
                #==========Tube voltage=============================
                self.d["label_Volt {0}".format(str(self.d["y " + str(t)]))] = ttk.Label(
                    master=self.d["sourcef " + str(self.d["y " + str(t)])], style="AL.TLabel", text="Tube Voltage(kV):")
                self.d["label_Volt " + str(self.d["y " + str(t)])].grid(row=0, column=0, pady=10, padx=10, sticky="w")
                self.d["envolt {0}".format(str(self.d["y " + str(t)]))] = ttk.Entry(master=self.d["sourcef " + str(self.d["y " + str(t)])], width=10)
                self.d["envolt "+str(self.d["y " + str(t)])].grid(row=0, column=1, pady=10, padx=10, sticky="w")
                #========Tube Current=======================
                self.lacur = ttk.Label(master=self.d["sourcef " + str(self.d["y " + str(t)])], style="AL.TLabel",
                                     text="Tube Current(mA):")
                self.lacur.grid(row=1, column=0, pady=10, padx=10, sticky="w")
                self.d["current_ent {0}".format(str(self.d["y " + str(t)]))] = ttk.Entry(
                    master=self.d["sourcef " + str(self.d["y " + str(t)])], width=10)
                self.d["current_ent " + str(self.d["y " + str(t)])].grid(row=1, column=1, pady=10, padx=10, sticky="w")


            self.d["noteso " + str(t)].grid(row=10, column=0, columnspan=self.d["y " + str(t)], pady=10, padx=10,
                                           sticky="wn")

        else:
            while self.d["y " + str(t)] > self.d["vnumsources " + str(t)].get():
                self.d["sourcef " + str(self.d["y " + str(t)])].destroy()

                self.d["y " + str(t)] -= 1
    def occupation(self, t):
        if self.d["vmethod " + str(t)].get() == "BIR 2012":
            if self.d["vraoccup " + str(t)].get() == 1:
                if self.d["sellocation " + str(t)] is not None:
                    self.d["sellocation " + str(t)].destroy()
                self.d["occupentry " + str(t)] = ttk.Entry(master=self.d["frame_1 " + str(t)], width=10)
                self.d["occupentry " + str(t)].grid(row=3, column=1, pady=10, padx=10)
            elif self.d["vraoccup " + str(t)].get() == 2:
                if self.d["occupentry " + str(t)] is not None:
                    self.d["occupentry " + str(t)].destroy()
                self.d["vselocation {0}".format(str(t))] = StringVar()
                if self.d["area " + str(t)].get() == "Cotrolled Area":
                    self.control = (
                        "Control rooms", "Reception areas", "Nurses stations", "Offices", "shops", "living quarters",
                        "children’s indoor play areas", "occupied space in nearby buildings")
                    self.d["sellocation " + str(t)] = ttk.OptionMenu(self.d["frame_1 " + str(t)],
                                                                     self.d["vselocation " + str(t)], "Select Location",
                                                                     *self.control)
                elif self.d["area " + str(t)].get() == "Uncontrolled Area":
                    self.uncontroll = ("Corridors", "Storerooms", "Stairways", "Changing rooms", "Unattended car parks",
                                       "Unattended waiting rooms", "Toilets", "bathrooms")
                    self.d["sellocation " + str(t)] = ttk.OptionMenu(self.d["frame_1 " + str(t)],
                                                                     self.d["vselocation " + str(t)], "Select Location",
                                                                     *self.uncontroll)
                elif self.d["area " + str(t)].get() == "Supervised Area":
                    self.supervised = ("Staff rooms", "Adjacent Wards", "Clinic rooms", "Reporting areas")
                    self.d["sellocation " + str(t)] = ttk.OptionMenu(self.d["frame_1 " + str(t)],
                                                                     self.d["vselocation " + str(t)], "Select Location",
                                                                     *self.supervised)
                self.d["sellocation " + str(t)].config(width=14)
                self.d["sellocation " + str(t)].grid(row=4, column=1, columnspan=2, pady=10, padx=10, sticky="w")
