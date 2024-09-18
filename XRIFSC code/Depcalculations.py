from tkinter import *
from tkinter import ttk
import pandas as pd
import math
import os
from openpyxl import load_workbook

# Get the current script directory
script_dir = os.path.dirname(__file__)

excel_path = os.path.join(script_dir, '..', 'Data Shielding.xlsx')

wb = load_workbook(excel_path)

class departprimsec():

    def choosetype(self,e,nr, t):
        if self.d["vselroom "+str(t)].get() == "CT Room":
            self.depCTcal(e, nr, nb, t)
        else:
            Ktotal = 0
            for i in range(0,self.d[f"num_barriers_var {e}{nr}"].get()):
                K = self.calkerma(e, nr, i, t)
                Ktotal += K
                print ("Kt="+str(Ktotal))
                if self.d[f"setv {e}{nr}{i}"].get() == 1:
                    ce = e
                    cnr = nr
                    ci = i
            self.B = (float(self.d["dikeent " + str(e) + nr].get()))/Ktotal
            self.depcalc(ce, cnr, ci, t)

    def calkerma(self, e, nr, i, t):
        # Fetching individual values directly without a list of keys
        D = float(self.d[f"entryd {e}{nr}{i}"].get())  # Distance (entryd)
        # ======== Workload ===========
        if self.d[f"oworkvar {e}{nr}{i}"] == 1: #If checks different workload
            if self.d[f"workv {e}{nr}{i}"].get() == 2:
                n = int(self.d[f"numpapwe {e}{nr}{i}"].get())  # Number of patients (numpapwe)
            elif self.d[f"workv {e}{nr}{i}"].get() == 1:# Workload option
                ws = wb['Workload']
                for x in range(1, 13):
                    if self.d[f"vsexroom {e}{nr}{i}"].get() == ws['A' + str(x)].value:  # X-ray room selection (vsexroom)
                        n = float(self.d[f"worentry {e}{nr}{i}"].get()) / ws['B' + str(x)].value  # Workload entry (worentry)
                if self.d[f"vselxray {e}{nr}{i}"].get() == 2:  # X-ray selection (vselxray)
                    n = float(self.d[f"worentry {e}{nr}{i}"].get()) / 2.5  # Workload entry (worentry)
        else:
            # The general workload
            if self.d[f"vrawork {t}"].get() == 2:
                n = int(self.d[f"numpapwe {t}"].get())
            elif self.d[f"vrawork {t}"].get() == 1:
                ws = wb['Workload']
                for x in range(1, 13):
                    if self.d[f"vsexroom {e}{nr}{i}"].get() == ws['A' + str(x)].value:
                        n = float(self.d[f"worentry {t}"].get()) / ws['B' + str(x)].value
                if self.d[f"vselxray {t}"].get() == 2:
                    n = float(self.d[f"worentry {t}"].get()) / 2.5
        # ======== Occupancy Factor T ===========
        if self.d[f"vraoccup {e}{nr}"].get() == 1:  # Occupancy option (vraoccup)
            T = float(self.d[f"occupentry {e}{nr}"].get())  # Occupancy entry (occupentry)
        elif self.d[f"vraoccup {e}{nr}"].get() == 2:
            ws = wb['Occupancy Factor ( T )']
            for x in range(2, 32):
                if self.d[f"vselocation {e}{nr}"].get() == ws['A' + str(x)].value:  # Location selection (vselocation)
                    T = float(ws['B' + str(x)].value)
        # ======== K1 "air kerma" ===========
        if self.d[f"radiob_w {e}{nr}{i}"].get() == 1:
        # primary unshielded air kerma
            K1 = float(self.d[f"entk {e}{nr}{i}"].get())  # Entered kerma value (entk)
        elif self.d[f"radiob_w {e}{nr}{i}"].get() == 2:
            if self.d[f"unairkerv {e}{nr}{i}"].get() == 1: #Selects fron NCRP 147
                # Secondary air kerma calculations based on the 'airkerv' value
                ws = wb["Uns Air Kerma"]
                room_type = self.d[f"vsexroom {e}{nr}{i}"].get()  # Fetching X-ray room type
                if self.d[f"airkerv {e}{nr}{i}"].get() == 1:
                    # Leakage air kerma calculation
                    if self.d[f"radiob_leak {e}{nr}{i}"].get() == 1:
                        for j in range(1, 11):
                            if room_type == ws['A' + str(j)].value:
                                K1 = float(ws['G' + str(j)].value)  # Leak & side scatter
                    elif self.d[f"radiob_leak {e}{nr}{i}"].get() == 2:
                        for j in range(1, 11):
                            if room_type == ws['A' + str(j)].value:
                                K1 = float(ws['I' + str(j)].value)  # Leakage and Forward/ Backscatter (Ksec)
                    else:
                        for j in range(1, 11):
                            if room_type == ws['A' + str(j)].value:
                                K1 = float(ws['E' + str(j)].value)  # Only Leakage

                elif self.d[f"airkerv {e}{nr}{i}"].get() == 2:
                    # Side-Scatter
                    for j in range(1, 11):
                        if room_type == ws['A' + str(j)].value:
                            K1 = float(ws['F' + str(j)].value)

                elif self.d[f"airkerv {e}{nr}{i}"].get() == 3:
                    # Forward/ Backscatter
                    for j in range(1, 11):
                        if room_type == ws['A' + str(j)].value:
                            K1 = float(ws['H' + str(j)].value)
            elif self.d[f"unairkerv {e}{nr}{i}"].get() == 2:
                # User-entered air kerma
                K1 = float(self.d[f"entk {e}{nr}{i}"].get())
        # ======== Use Factor ===========
        if self.d[f"radiob_w {e}{nr}{i}"].get() == 1:
            Us = float(self.d[f"use_ent {e}{nr}{i}"].get())  # Use factor (use_ent)
        elif self.d[f"radiob_w {e}{nr}{i}"].get() == 2:
            Us = 1
        # ========== Calculate Kerma ==========
        K = n * Us * T * K1 / (D ** 2)
        return K

    def depcalc(self, e, nr, i, t):  # Barrier calculations
        if self.d["titleresul " + str(e)+nr] is not None:
            for o in range(1, 7):
                if self.res["resmat " + str(o) + str(e)] is not None:
                    self.res["resmat " + str(o)+str(e)].destroy()
        else:
            for o in range(1, 7):
                self.res["resmat {0}".format(str(o)) + str(e)] = None

        for o in range(1,self.d["vnumbmat " +str(e)+nr].get()+1):
            if self.d[f"radiob_w {e}{nr}{i}"].get() == 1:
            # ========================primary αβγ========================
                ws = wb['prim abc']
                for x in range(2, 39):
                    if self.d[f"vsexroom {e}{nr}{i}"].get() == ws['A' + str(x)].value:
                        self.alp = ws['B' + str(x)].value
                        self.blp = ws['C' + str(x)].value
                        self.clp = float(ws['D' + str(x)].value)
                        self.acp = ws['E' + str(x)].value
                        self.bcp = ws['F' + str(x)].value
                        self.ccp = float(ws['G' + str(x)].value)
                        self.agp = ws['H' + str(x)].value
                        self.bgp = ws['I' + str(x)].value
                        self.cgp = float(ws['J' + str(x)].value)
                        self.asp = ws['K' + str(x)].value
                        self.bsp = ws['L' + str(x)].value
                        self.csp = float(ws['M' + str(x)].value)
                        self.appr = ws['N' + str(x)].value
                        self.bpp = ws['O' + str(x)].value
                        self.cpp = float(ws['P' + str(x)].value)
                        self.awp = ws['Q' + str(x)].value
                        self.bwp = ws['R' + str(x)].value
                        self.cwp = float(ws['S' + str(x)].value)
                    #===============Preshielding=====================
                    if self.d[f"preshvar {e}{nr}{i}"].get()==1:
                        ws = wb["Equiv. thickness of prim pres"]
                        if self.d["radiob_pre " + str(e)+nr].get()==1:
                            self.xlead = float(ws['B' + str(3)].value)
                            self.xconc = float(ws['C' + str(3)].value)
                            self.xsteel = float(ws['D' + str(3)].value)
                        elif self.d["radiob_pre " + str(e) + nr].get() == 2:
                            self.xlead = float(ws['B' + str(4)].value)
                            self.xconc = float(ws['C' + str(4)].value)
                            self.xsteel = float(ws['D' + str(4)].value)
                    else:
                        self.xlead = 0
                        self.xconc = 0
                        self.xsteel = 0
            elif self.d[f"radiob_w {e}{nr}{i}"].get() == 2:
                ws = wb['sec abc']
                # ====================secondary αβγ============================
                for x in range(3, 18):
                    if self.d[f"vsexroom {e}{nr}{i}"].get() == ws['A' + str(i)].value:
                        self.als = ws['B' + str(x)].value
                        self.bls = ws['C' + str(x)].value
                        self.cls = float(ws['D' + str(x)].value)
                        self.acs = ws['E' + str(x)].value
                        self.bcs = ws['F' + str(x)].value
                        self.ccs = float(ws['G' + str(x)].value)
                        self.ags = ws['H' + str(x)].value
                        self.bgs = ws['I' + str(x)].value
                        self.cgs = float(ws['J' + str(x)].value)
                        self.ass = ws['K' + str(x)].value
                        self.bss = ws['L' + str(x)].value
                        self.css = float(ws['M' + str(x)].value)
                        self.aps = ws['N' + str(x)].value
                        self.bps = ws['O' + str(x)].value
                        self.cps = float(ws['P' + str(x)].value)
                        self.aws = ws['Q' + str(x)].value
                        self.bws = ws['R' + str(x)].value
                        self.cws = float(ws['S' + str(x)].value)
            # ========================== Material selection =================================
            if self.d["vmater "+str(e)+str(o)+nr].get() == "Lead":
                self.thm["xbar " + str(e)+str(o)+nr]  = (1 / (self.alp * self.clp)) * math.log(
                    (self.B ** (-self.clp) + self.blp / self.alp) / (1 + self.blp / self.alp))-self.xlead
                self.xlmat["thic "+str(e) + str(1) + nr] = self.thm["xbar " + str(e)+str(o)+nr]
            elif self.d["vmater "+str(e)+str(o)+nr].get() == "Concrete":
                self.thm["xbar " + str(e)+str(o)+nr] = (1 / (self.acp * self.ccp)) * math.log(
                    (self.B ** (-self.ccp) + self.bcp / self.acp) / (1 + self.bcp / self.acp))-self.xconc
                self.xlmat["thic " + str(e) + str(2) + nr] = self.thm["xbar " + str(e) + str(o) + nr]
            elif self.d["vmater "+str(e)+str(o)+nr].get() == "Gypsum Wallboard":
                self.thm["xbar " + str(e)+str(o)+nr] = (1 / (self.agp * self.cgp)) * math.log(
                    (self.B ** (-self.cgp) + self.bgp / self.agp) / (1 + self.bgp / self.agp))
                self.xlmat["thic " + str(e) + str(3) + nr] = self.thm["xbar " + str(e) + str(o) + nr]
            elif self.d["vmater "+str(e)+str(o)+nr].get() == "Steel":
                self.thm["xbar " + str(e)+str(o)+nr] = (1 / (self.asp * self.csp)) * math.log(
                    (self.B ** (-self.csp) + self.bsp / self.asp) / (1 + self.bsp / self.asp))-self.xsteel
                self.xlmat["thic " + str(e) + str(4) + nr] = self.thm["xbar " + str(e) + str(o) + nr]
            elif self.d["vmater "+str(e)+str(o)+nr].get() == "Plate Glass":
                self.thm["xbar " + str(e)+str(o)+nr] = (1 / (self.appr * self.cpp)) * math.log(
                    (self.B ** (-self.cpp) + self.bpp / self.appr) / (1 + self.bpp / self.appr))
                self.xlmat["thic " + str(e) + str(5) + nr] = self.thm["xbar " + str(e) + str(o) + nr]
            elif self.d["vmater "+str(e)+str(o)+nr].get() == "Wood":
                self.thm["xbar " + str(e)+str(o)+nr] = (1 / (self.awp * self.cwp)) * math.log(
                    (self.B ** (-self.cwp) + self.bwp / self.awp) / (1 + self.bwp / self.awp))
                self.xlmat["thic " + str(e) + str(6) + nr] = self.thm["xbar " + str(e) + str(o) + nr]
            if self.d["titleresul " + str(e)+nr] is None:
                self.res["resmat " + str(o)+str(e)]= ttk.Label(self.d["resultframe " + str(t)+nr], style="AL.TLabel",
                                                                text=self.d["vmater " + str(e) + str(o)+nr].get()
                                                                     + ": " + str(
                                                                    round(self.thm["xbar " + str(e)+str(o)+nr], 2)) + " mm")
                if o < 3:
                    self.res["resmat " + str(o)+str(e)].grid(row=str(self.ep), column=o, pady=3, padx=3, sticky="w")
                    op = 0
                elif 2 < o < 5:
                    if o == 3:
                        self.ep += 1
                        op += 1
                    self.res["resmat " + str(o)+str(e)].grid(row=str(self.ep), column=o - 2, pady=3, padx=3, sticky="w")
                else:
                    if o == 5:
                        self.ep += 1
                        op += 1
                    self.res["resmat " + str(o)+str(e)].grid(row=str(self.ep), column=o - 4, pady=3, padx=3, sticky="w")
            else:

                self.res["resmat " + str(o)+str(e)] = ttk.Label(self.d["resultframe " + str(t)+nr], style="AL.TLabel",
                                                       text=self.d["vmater " + str(e) + str(o)+nr].get() + ": " + str(
                                                           round(self.thm["xbar " + str(e)+str(o)+nr], 2)) + " mm")
                if o < 3:
                    self.res["resmat " + str(o)+str(e)].grid(row=str(self.d["spot " + str(e)]), column=o, pady=3, padx=3,
                                                    sticky="w")
                elif 2 < o < 5:
                    self.res["resmat " + str(o)+str(e)].grid(row=str(self.d["spot " + str(e)] + 1), column=o - 2, pady=3,
                                                    padx=3, sticky="w")
                else:
                    self.res["resmat " + str(o)+str(e)].grid(row=str(self.d["spot " + str(e)] + 2), column=o - 4, pady=3,
                                                    padx=3, sticky="w")

        if self.d["titleresul " + str(e)+nr] is None:
            self.d["titleresul " + str(e)+nr] = ttk.Label(self.d["resultframe " + str(t)+nr], style="AL.TLabel",
                                                       text=self.barn["lab_bar " + str(e) + nr].cget("text") + ": ")
            self.d["titleresul " + str(e)+nr].grid(row=str(self.ep - op), column=0, pady=3, padx=3, sticky="s")
            self.d["spot {0}".format(str(e))] = self.ep
        else:
            self.d["titleresul " + str(e)+nr].destroy()
            self.d["titleresul " + str(e)+nr] = ttk.Label(self.d["resultframe " + str(t)+nr], style="AL.TLabel",
                                                       text=self.barn["lab_bar " + str(e) + nr].cget("text") + ": ")
            self.d["titleresul " + str(e)+nr].grid(row=str(self.d["spot " + str(e)]), column=0, pady=3, padx=3,
                                                sticky="s")

        self.rdata={self.barn["lab_bar " + str(e) + nr].cget("text"):{self.d["vmater " + str(e) + str(o)+nr].get():str(
                                                           round(self.thm["xbar " + str(e)+str(o)+nr], 3))}}

        print ("B="+str(self.B))
        print("xb="+str(self.thm["xbar " + str(e)+str(o)+nr]))
        self.ep += 1

    def depCTcal(self, e, nr, nb, t):
        if self.d["titleresul " + str(e)+nr] is not None:
            for o in range (1,7):
                if self.res["resmat " + str(o)+str(e)] is not None:
                    self.res["resmat " + str(o)+str(e)].destroy()
        else:
            for o in range(1, 7):
                self.res["resmat {0}".format(str(o)) + str(e)] = None
        for o in range(1, self.d["vnumbmat " + str(e) + nr].get() + 1):
            k1sec_body = float(1.2 * (3 * 10 ** -4) * (1.4 * float(self.d["dlpb_var "+ str(t)].get())))
            k1sec_head = float((9 * 10 ** -5) * (1.4 * float(self.d['dlph_var '+ str(t)].get())))
            self.d["K "+self.barn["lab_bar " + str(e) + nr].cget("text")+nr] = float((1 / float(self.d["dist_var "+ str(e) + nr].get())) ** 2
                                                                     * ((self.d["bp_var "+str(t)].get() * k1sec_body)
                                                                        + (self.d["hp_var " + str(t)].get() * k1sec_head)))
            B = float(self.d["sh_var " + str(e) + nr].get() / float(self.d["K "+self.barn["lab_bar " + str(e) + nr].cget("text")+nr]))
            print(B)
            if self.d["vmater "+str(e)+str(o)+nr].get() == "Lead":
                if self.d["kvp_var "+ str(t)].get() == 120:
                    a = 2.246
                    b = 5.73
                    c = 0.547
                else:
                    a = 2.009
                    b = 3.99
                    c = 0.342
            elif self.d["vmater "+str(e)+str(o)+nr].get() == "Concrete":
                if self.d["kvp_var "+ str(t)].get() == 120:
                    a = 0.0383
                    b = 0.0142
                    c = 0.658
                else:
                    a = 0.0336
                    b = 0.0122
                    c = 0.519
            self.thm["xbar "+str(e)+str(o)+nr] = float((1 / (a * c)) * math.log((B ** -c + (b / a)) / (1 + (b / a))))

            if self.d["titleresul " + str(e) + nr] is None:
                self.res["resmat " + str(o) + str(e)] = ttk.Label(self.d["resultframe " + str(t) + nr],
                                                                  style="AL.TLabel", text=self.d[
                                                                                              "vmater " + str(e) + str(
                                                                                                  o) + nr].get() + ": " + str(
                        round(self.thm["xbar " + str(e) + str(o) + nr], 2)) + " mm")
                if o < 3:
                    self.res["resmat " + str(o) + str(e)].grid(row=str(self.ep), column=o, pady=3, padx=3, sticky="w")
                    op = 0
                elif 2 < o < 5:
                    if o == 3:
                        self.ep += 1
                        op += 1
                    self.res["resmat " + str(o) + str(e)].grid(row=str(self.ep), column=o - 2, pady=3, padx=3,
                                                               sticky="w")
                else:
                    if o == 5:
                        self.ep += 1
                        op += 1
                    self.res["resmat " + str(o) + str(e)].grid(row=str(self.ep), column=o - 4, pady=3, padx=3,
                                                               sticky="w")
            else:
                self.res["resmat " + str(o) + str(e)] = ttk.Label(self.d["resultframe " + str(t) + nr],
                                                                  style="AL.TLabel", text=self.d[
                                                                                              "vmater " + str(e) + str(
                                                                                                  o) + nr].get() + ": " + str(
                        round(self.thm["xbar " + str(e) + str(o) + nr], 2)) + " mm")
                if o < 3:
                    self.res["resmat " + str(o) + str(e)].grid(row=str(self.d["spot " + str(e)]), column=o, pady=3,
                                                               padx=3, sticky="w")
                elif 2 < o < 5:
                    self.res["resmat " + str(o) + str(e)].grid(row=str(self.d["spot " + str(e)] + 1), column=o - 2,
                                                               pady=3, padx=3, sticky="w")
                else:
                    self.res["resmat " + str(o) + str(e)].grid(row=str(self.d["spot " + str(e)] + 2), column=o - 4,
                                                               pady=3, padx=3, sticky="w")

        if self.d["titleresul " + str(e) + nr] is None:
            self.d["titleresul " + str(e) + nr] = ttk.Label(self.d["resultframe " + str(t) + nr], style="AL.TLabel",
                                                            text=self.barn["lab_bar " + str(e) + nr].cget(
                                                                "text") + ": ")
            self.d["titleresul " + str(e) + nr].grid(row=str(self.ep - op), column=0, pady=3, padx=3, sticky="s")
            self.d["spot {0}".format(str(e))] = self.ep
        else:
            self.d["titleresul " + str(e) + nr].destroy()
            self.d["titleresul " + str(e) + nr] = ttk.Label(self.d["resultframe " + str(t) + nr], style="AL.TLabel",
                                                            text=self.barn["lab_bar " + str(e) + nr].cget(
                                                                "text") + ": ")
            self.d["titleresul " + str(e) + nr].grid(row=str(self.d["spot " + str(e)]), column=0, pady=3, padx=3,
                                                     sticky="s")

        print(self.d["K " + self.barn["lab_bar " + str(e) + nr].cget("text") + nr])
        self.ep += 1