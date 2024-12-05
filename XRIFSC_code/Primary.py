import subprocess
from tkinter import *
from tkinter import ttk

class prim_widgets():

    def pres(self, e, nr, i):
        preshvar_key = f"preshvar {e}{nr}{i}"
        radbucky_key = f"radbucky {e}{nr}{i}"
        radcross_key = f"radcross {e}{nr}{i}"
        radiob_pre_key = f"radiob_pre {e}{nr}{i}"  # Unique key for radiob_pre
        self.var[radiob_pre_key] = IntVar(value=0)  # Store IntVar in dictionary
        # Check if preshielding is selected (1)
        if self.var[preshvar_key].get() == 1:
            # Create and place the 'Bucky' Radiobutton
            self.d[radbucky_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"],
                                                   variable=self.var[radiob_pre_key], text="Bucky or Image receptor\nin radiographic table", value=1)
            self.d[radbucky_key].grid(row=i * 10 + 6, column=3, pady=6.5, padx=5, sticky="w")
            # Create and place the 'Cross-table' Radiobutton
            self.d[radcross_key] = ttk.Radiobutton(master=self.d[f"barrierf {e}{nr}"],
                                                   variable=self.var[radiob_pre_key], text="Cross-table lateral", value=2)
            self.d[radcross_key].grid(row=i * 10 + 6, column=4, pady=6.5, padx=5, sticky="w")
        # If preshielding is deselected (0), destroy the widgets if they exist
        elif self.var[preshvar_key].get() == 0:
            self.destroy_widgets([radbucky_key, radcross_key])

    def uns(self, e, nr, i):

        if self.var[f"radiob_w {e}{nr}{i}"].get() == 1:
            # =========== Unshielded Air Kerma ============
            rad_rooms = ["Rad Room (chest bucky)", 'Rad Room (floor or other barriers)', 'Rad Tube (R&F Room)',
                         'Chest Room']
            vsexroom_key = f"vsexroom {e}{nr}{i}"
            entk_key = f"entk {e}{nr}{i}"  # Key for the unshielded air kerma entry field
            if self.var[vsexroom_key].get() in rad_rooms:
                # Clear the existing entry data before inserting new values
                if entk_key in self.ent:
                    self.ent[entk_key].delete(0, 'end')
                    # Insert predefined values into the unshielded air kerma based on NCRP 147
                    if self.var[vsexroom_key].get() == "Rad Room (chest bucky)":
                        self.ent[entk_key].insert(0, "2.3")
                    elif self.var[vsexroom_key].get() == "Rad Room (floor or other barriers)":
                        self.ent[entk_key].insert(0, "5.2")
                    elif self.var[vsexroom_key].get() == "Rad Tube (R&F Room)":
                        self.ent[entk_key].insert(0, "5.9")
                    elif self.var[vsexroom_key].get() == "Chest Room":
                        self.ent[entk_key].insert(0, "1.2")
            else:
                self.ent[entk_key].delete(0, 'end')
            # ===== Use Factor suggestes ========
            use_ent_key = f"use_ent {e}{nr}{i}"  # Key for the use entry
            if e == 1:
                if self.d.get(f"selxroom {e}{nr}{i}"):
                    self.ent[use_ent_key].delete(0, 'end')
                    if self.var[vsexroom_key].get() == "Rad Room (floor or other barriers)":
                        self.ent[use_ent_key].insert(0, str(0.89))
                    else:
                        self.ent[use_ent_key].insert(0, str(1))
                else:
                    self.ent[use_ent_key].insert(0, str(1))
            elif e == 2:
                self.ent[use_ent_key].delete(0, 'end')
                self.ent[use_ent_key].insert(0, str(1 / 16))
            else:
                if self.d.get(f"selxroom {e}{nr}{i}"):
                    self.ent[use_ent_key].delete(0, 'end')
                    if self.var[vsexroom_key].get() == "Rad Room (floor or other barriers)":
                        self.ent[use_ent_key].insert(0, str(0.09))
                    else:
                        self.ent[use_ent_key].insert(0, str(1))
                else:
                    self.ent[use_ent_key].insert(0, str(1))