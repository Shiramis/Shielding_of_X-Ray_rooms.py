from tkinter import *
from tkinter import ttk

class sec_widgets():

    def unairk(self, e, nr, i):
        # Destroy any existing widgets related to secondary barrier
        self.destroy_widgets([f"leak {e}{nr}{i}", f"side {e}{nr}{i}", f"forw {e}{nr}{i}", f"entk {e}{nr}{i}",
                              f"radside {e}{nr}{i}", f"radforward {e}{nr}{i}", f"radleak {e}{nr}{i}",
                              f"Ksec {e}{nr}{i}", f"Kleak {e}{nr}{i}", f"Kscat {e}{nr}{i}", f"entryd {e}{nr}{i}",
                              f"entk {e}{nr}{i}",f"lad {e}{nr}{i}",f"labelk {e}{nr}{i}",
                              f"lad_behind {e}{nr}{i}" ,f"d_beh {e}{nr}{i}"])

        unairkerv_key = f"unairkerv {e}{nr}{i}"

        if self.var[unairkerv_key].get() == 1:
            # NCRP-suggested mode: create radio buttons for different types of scatter/leakage
            self.var[f"airkerv {e}{nr}{i}"] = IntVar(value=0)
            self.create_radio_button(key=f"leak {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"],
                text="Leakage Radiation", variable=self.var[f"airkerv {e}{nr}{i}"], value=1, row=i * 10 + 5, column=0,
                command=lambda: self.leakage(e, nr, i))

            self.create_radio_button(key=f"side {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"], text="Side-Scatter",
                variable=self.var[f"airkerv {e}{nr}{i}"], value=2, row=i * 10 + 5, column=1,
                command=lambda: self.leakage(e, nr, i))

            self.create_radio_button(key=f"forw {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"],
                text="Forward/Backscatter", variable=self.var[f"airkerv {e}{nr}{i}"], value=3, row=i * 10 + 5, column=2,
                command=lambda: self.leakage(e, nr, i))

        elif self.var[unairkerv_key].get() == 2:
            # Custom input mode: create entry for secondary air kerma
            self.var[f"unsecair {e}{nr}{i}"] = IntVar(value=0)
            self.create_radio_button(key=f"Ksec {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"],
                                     text="Secondary",
                                     variable=self.var[f"unsecair {e}{nr}{i}"], value=1, row=i * 10 + 5, column=0,
                                     command=lambda: self.secondary_air(e, nr, i))
            self.create_radio_button(key=f"Kleak {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"], text=r"Leakage",
                                     variable=self.var[f"unsecair {e}{nr}{i}"], value=2, row=i * 10 + 5, column=1,
                                     command=lambda: self.secondary_air(e, nr, i))
            self.create_radio_button(key=f"Kscat {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"], text="Scatter",
                                     variable=self.var[f"unsecair {e}{nr}{i}"], value=3, row=i * 10 + 5, column=2,
                                     command=lambda: self.secondary_air(e, nr, i))

    def leakage(self, e, nr, i):
        airkerv_key = f"airkerv {e}{nr}{i}"
        radiob_leak_key = f"radiob_leak {e}{nr}{i}"
        # Destroy any previously created widgets
        self.destroy_widgets(
            [f"radside {e}{nr}{i}", f"radforward {e}{nr}{i}", f"radleak {e}{nr}{i}", f"entryd {e}{nr}{i}",
             f'lad {e}{nr}{i}', f"entk {e}{nr}{i}",f"lad {e}{nr}{i}",f"labelk {e}{nr}{i}", f"lad_behind {e}{nr}{i}"
             ,f"d_beh {e}{nr}{i}"])
        # Check the current selection and create the corresponding radio buttons
        self.ent[f"entryd {e}{nr}{i}"] = ttk.Entry(master=self.d[f"barrierf {e}{nr}"], width=10)

        if self.var[airkerv_key].get() == 1:  # Leakage
            self.var[radiob_leak_key] = IntVar(value=0)
            # Create radio buttons
            self.create_radio_button(key=f"radside {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"],
                                     text="Leakage and Side-Scatter", variable=self.var[radiob_leak_key], value=1,
                                     row=i * 10 + 6, column=0)
            self.create_radio_button(key=f"radforward {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"],
                                     text="Leakage and Forward/Backscatter", variable=self.var[radiob_leak_key],
                                     value=2, row=i * 10 + 6, column=1)
            self.create_radio_button(key=f"radleak {e}{nr}{i}", master=self.d[f"barrierf {e}{nr}"], text="Only Leakage",
                                     variable=self.var[radiob_leak_key], value=0, row=i * 10 + 6, column=2)
            # Initialize the label and entry
            self.d[f'lad {e}{nr}{i}'] = ttk.Label(master=self.d[f"barrierf {e}{nr}"], style="AL.TLabel")
            self.d[f'lad {e}{nr}{i}'].grid(row=i * 10 + 8, column=0, pady=6.5, padx=5, sticky="w")
            self.ent[f"entryd {e}{nr}{i}"].grid(row=i * 10 + 8, column=1, pady=6.5, padx=5, sticky="w")
            # Function to update the label based on the selected radio button
            def update_distance_label(*args):
                selected_value = self.var[radiob_leak_key].get()
                if selected_value in [1, 2]:  # Leakage and Side-Scatter or Forward/Backscatter
                    label_text = "Secondary distance (dsec)\nto the Barrier (m):"
                else:  # Only Leakage
                    label_text = "Leakage distance (dleak)\nto the Barrier (m):"
                self.d[f'lad {e}{nr}{i}']['text'] = label_text
            # Add the trace to the IntVar to call update_distance_label when it changes
            self.var[radiob_leak_key].trace_add("write", update_distance_label)
            # Call initially to set the correct label
            update_distance_label()

        elif self.var[airkerv_key].get() == 2:
            self.d[f'lad {e}{nr}{i}'] = ttk.Label(master=self.d[f"barrierf {e}{nr}"], style="AL.TLabel",
                                                  text="Scatter distance (dsca)\nto the Barrier (m):")
            self.d[f'lad {e}{nr}{i}'].grid(row=i * 10 + 8, column=0, pady=6.5, padx=5, sticky="w")
            self.ent[f"entryd {e}{nr}{i}"].grid(row=i * 10 + 8, column=1, pady=6.5, padx=5, sticky="w")

        elif self.var[airkerv_key].get() == 3:
            self.d[f'lad {e}{nr}{i}'] = ttk.Label(master=self.d[f"barrierf {e}{nr}"], style="AL.TLabel",
                                                  text="Scatter distance (dsca)\nto the Barrier (m):")
            self.d[f'lad {e}{nr}{i}'].grid(row=i * 10 + 8, column=0, pady=6.5, padx=5, sticky="w")
            self.ent[f"entryd {e}{nr}{i}"].grid(row=i * 10 + 8, column=1, pady=6.5, padx=5, sticky="w")
        # distance from barrier to the design goal
        self.d[f"lad_behind {e}{nr}{i}"] = ttk.Label(master=self.d[f"barrierf {e}{nr}"], style="AL.TLabel",
                                                     text="Distance behind the barrιer\nto the point goal (m):")
        self.d[f"lad_behind {e}{nr}{i}"].grid(row=i * 10 + 8, column=2, pady=6.5, padx=5, sticky="w")
        self.ent[f"d_beh {e}{nr}{i}"] = ttk.Entry(master=self.d[f"barrierf {e}{nr}"], width=10)
        self.ent[f"d_beh {e}{nr}{i}"].grid(row=i * 10 + 8, column=3, pady=6.5, padx=5, sticky="w")
        # sets values for behind
        self.distance_behind_sets(e, nr, i)
        # === tips ======
        self.set_distance_tips(e, nr, i)

    def secondary_air(self, e, nr, i):
        self.destroy_widgets([f"entk {e}{nr}{i}",f"lad {e}{nr}{i}",f"labelk {e}{nr}{i}", f"entryd {e}{nr}{i}",
                              f"lad_behind {e}{nr}{i}" ,f"d_beh {e}{nr}{i}"])

        self.ent[f"entk {e}{nr}{i}"] = ttk.Entry(master=self.d[f"barrierf {e}{nr}"], width=10) #air kerma
        self.ent[f"entryd {e}{nr}{i}"] = ttk.Entry(master=self.d[f"barrierf {e}{nr}"], width=10) #distance
        if self.var[f"unsecair {e}{nr}{i}"].get() == 1:
            # ===== Secondary========
            self.d[f'labelk {e}{nr}{i}'] = ttk.Label(master=self.d[f"barrierf {e}{nr}"], style="AL.TLabel",
                                                  text="Ksec(0):")
            self.d[f'lad {e}{nr}{i}'] = ttk.Label(master=self.d[f"barrierf {e}{nr}"], style="AL.TLabel",
                                                  text="Secondary distance (dsec)\nto the Barrier (m):")
        elif self.var[f"unsecair {e}{nr}{i}"].get() == 2:
            self.d[f'labelk {e}{nr}{i}'] = ttk.Label(master=self.d[f"barrierf {e}{nr}"], style="AL.TLabel",
                                                     text="Kleak(0):")
            self.d[f'lad {e}{nr}{i}'] = ttk.Label(master=self.d[f"barrierf {e}{nr}"], style="AL.TLabel",
                                                  text="Leakage distance (dleak)\nto the Barrier (m):")
        else:
            self.d[f'labelk {e}{nr}{i}'] = ttk.Label(master=self.d[f"barrierf {e}{nr}"], style="AL.TLabel",
                                                     text="Ksca(0):")
            self.d[f'lad {e}{nr}{i}'] = ttk.Label(master=self.d[f"barrierf {e}{nr}"], style="AL.TLabel",
                                                  text="Scatter distance (dscat)\nto the Barrier (m):")

        self.d[f'labelk {e}{nr}{i}'].grid(row=i * 10 + 6, column=0, pady=6.5, padx=5, sticky="w")
        self.ent[f"entk {e}{nr}{i}"].grid(row=i * 10 + 6, column=1, pady=6.5, padx=5, sticky="w")
        self.d[f'lad {e}{nr}{i}'].grid(row=i * 10 + 8, column=0, pady=6.5, padx=5, sticky="w")
        self.ent[f"entryd {e}{nr}{i}"].grid(row=i * 10 + 8, column=1, pady=6.5, padx=5, sticky="w")
        # distance from barrier to the design goal
        self.d[f"lad_behind {e}{nr}{i}"] = ttk.Label(master=self.d[f"barrierf {e}{nr}"], style="AL.TLabel",
                                                     text="Distance behind the barrιer\nto the point goal (m):")
        self.d[f"lad_behind {e}{nr}{i}"].grid(row=i * 10 + 8, column=2, pady=6.5, padx=5, sticky="w")
        self.ent[f"d_beh {e}{nr}{i}"] = ttk.Entry(master=self.d[f"barrierf {e}{nr}"], width=10)
        self.ent[f"d_beh {e}{nr}{i}"].grid(row=i * 10 + 8, column=3, pady=6.5, padx=5, sticky="w")
        # sets values for behind
        self.distance_behind_sets(e, nr, i)
        #=== tips ======
        self.set_distance_tips(e,nr,i)
