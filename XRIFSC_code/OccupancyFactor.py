from tkinter import *
from tkinter import ttk
from idlelib.tooltip import Hovertip

class occupation_widgets():

    def occup_design(self, index, room_number, t):
        """Add additional widgets for X-ray room."""
        self.title_ocupat = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="BL.TLabel",
            text="Shielding Area")
        self.title_ocupat.grid(row=104, column=0, pady=6.5, padx=5, sticky="w")
        self.var[f"area {index}{room_number}"] = StringVar()
        self.d[f"area {index}{room_number}"] = ttk.Combobox(master=self.d[f"barrierf {index}{room_number}"],
            textvariable=self.var[f"area {index}{room_number}"],
            values=["Controlled Area", "Uncontrolled Area", "Supervised Area"], state="readonly")
        self.d[f"area {index}{room_number}"].grid(row=104, column=1, sticky="w")
        self.d[f"area {index}{room_number}"].set("Classify the area")

        self.var[f"vraoccup {index}{room_number}"] = IntVar(value=0)
        self.raoccup = ttk.Radiobutton(master=self.d[f"barrierf {index}{room_number}"],
            variable=self.var[f"vraoccup {index}{room_number}"], text="Write occupancy factor (T):", value=1,
            command=lambda e=index, nr=room_number: self.occupation3(e, nr, t))
        self.raoccup.grid(row=105, column=0, pady=6.5, padx=5, sticky="w")

        self.raseloccup = ttk.Radiobutton(master=self.d[f"barrierf {index}{room_number}"],
            text="or select Location", variable=self.var[f"vraoccup {index}{room_number}"], value=2,
            command=lambda e=index, nr=room_number: self.occupation3(e, nr, t))
        self.raseloccup.grid(row=106, column=0, pady=6.5, padx=5, sticky="w")
        # tip for Location
        self.location_tip = Hovertip(self.raseloccup, text= "Table 4.1 of NCRP 147\n(suggested occupancy factors)")
        self.ladike = ttk.Label(master=self.d[f"barrierf {index}{room_number}"], style="AL.TLabel",
                                text="Shielding Design Goal(P)\n(mGy∙week\u207B\u00b9):")
        self.ladike.grid(row=107, column=0, pady=6.5, padx=5, sticky="w")
        self.d[f"dikeent {index}{room_number}"] = ttk.Entry(master=self.d[f"barrierf {index}{room_number}"], width=10)
        self.d[f"dikeent {index}{room_number}"].grid(row=107, column=1, pady=6.5, padx=5, sticky="w")

    def occupation3(self, e, nr, t):
        vra_key = f"vraoccup {e}{nr}"
        area_key = f"area {e}{nr}"
        occupentry_key = f"occupentry {e}{nr}"
        sellocation_key = f"sellocation {e}{nr}"
        barrierf_key = f"barrierf {e}{nr}"
        dikeent_key = f"dikeent {e}{nr}"
        # Destroy any existing entry before creating a new one
        self.destroy_widgets([dikeent_key])

        self.d[dikeent_key] = ttk.Entry(master=self.d[barrierf_key], width=10)
        self.d[dikeent_key].grid(row=107, column=1, pady=6.5, padx=5, sticky="w")

        if self.var[vra_key].get() == 1:
            # Destroy previous widgets if they exist
            self.destroy_widgets([sellocation_key])
            self.destroy_widgets([occupentry_key])
            # Create Location Entry widget for occupation
            self.var[f"vselocation {e}{nr}"] = StringVar()
            self.d[occupentry_key] = ttk.Entry(master=self.d[barrierf_key], width=10)
            # Insert specific values depending on the area
            if self.d[area_key].get() == "Controlled Area":
                self.d[occupentry_key].insert(0, str(1))
                self.d[dikeent_key].insert(0, str(0.01))
            elif self.d[area_key].get() == "Uncontrolled Area":
                self.d[occupentry_key].insert(0, str(1 / 16))
                self.d[dikeent_key].insert(0, str(0.006))
            elif self.d[area_key].get() == "Supervised Area":
                self.d[occupentry_key].insert(0, str(1 / 4))
                self.d[dikeent_key].insert(0, str(0.006))
            self.d[occupentry_key].grid(row=105, column=1, pady=6.5, padx=5)
        elif self.var[vra_key].get() == 2:
            # Destroy previous widgets if they exist
            self.destroy_widgets([sellocation_key])
            self.destroy_widgets([occupentry_key])
            # Initialize the location options
            self.var[f"vselocation {e}{nr}"] = StringVar()
            # Create location options based on the area
            if self.d[area_key].get() == "Controlled Area":
                locations = ("Administrative or clerical offices", "Laboratories",
                             "Pharmacies and other work areas fully occupied by an individual", "Receptionist areas",
                             "Attended waiting rooms", "Children’s indoor play areas", "Adjacent x-ray rooms",
                             "Film reading areas", "Nurse’s stations", "X-ray control rooms",
                             "Rooms used for patient examinations and treatments")
                self.d[dikeent_key].insert(0, str(0.01))
            elif self.d[area_key].get() == "Uncontrolled Area":
                locations = ("Public toilets", "Unattended vending areas", "Storage  rooms", "Outdoor areas with seating",
                             "Unattended waiting rooms", "Patient holding areas",
                             "Outdoor areas with only transient pedestrian or vehicular traffic", "Unattended parking lots",
                             "Vehicular drop off areas (unattended)", "Attics", "Stairways", "Unattended elevators",
                             "Janitor’s closets")
                self.d[dikeent_key].insert(0, str(0.006))
            elif self.d[area_key].get() == "Supervised Area":
                locations = ("Corridors", "Patient rooms", "Employee lounges", "Staff restooms", "Corridor doors")
                self.d[dikeent_key].insert(0, str(0.006))
            else:
                locations = ("Administrative or clerical offices", "Laboratories",
                             "Pharmacies and other work areas fully occupied by an individual", "Receptionist areas",
                             "Attended waiting rooms", "Children’s indoor play areas", "Adjacent x-ray rooms",
                             "Film reading areas", "Nurse’s stations", "X-ray control rooms",
                             "Rooms used for patient examinations and treatments", "Corridors", "Patient rooms",
                             "Employee lounges", "Staff restooms", "Corridor doors", "Public toilets",
                             "Unattended vending areas", "Storage  rooms", "Outdoor areas with seating",
                             "Unattended waiting rooms", "Patient holding areas",
                             "Outdoor areas with only transient pedestrian or vehicular traffic", "Unattended parking lots",
                             "Vehicular drop off areas (unattended)", "Attics", "Stairways", "Unattended elevators",
                             "Janitor’s closets")
            # Create OptionMenu with location choices
            self.d[sellocation_key] = ttk.OptionMenu(self.d[barrierf_key], self.var[f"vselocation {e}{nr}"],
                                                     "Select Location", *locations)
            self.d[sellocation_key].grid(row=106, column=1, pady=6.5, padx=5, sticky="w")
            self.d[sellocation_key].config(width=15)
