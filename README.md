<img src="XRIFSC_code/app_icon.png" width="72" align="right" alt="">

# Shielding of X-ray Rooms

A desktop program for the **structural shielding design of medical X-ray imaging facilities**, following
**NCRP Report No. 147** (2004). It works out how thick the walls, floor, ceiling and door of a room must be, and checks
the thickness you plan to install.

![An X-ray room with its results](docs/images/xray_overview.png)

## What it does

- **Room types**: X-ray rooms (radiography, chest), fluoroscopy rooms (R&F, cardiac and peripheral
  angiography), CT rooms (from the DLP, with the scans or phases per procedure) and mammography rooms, including
  digital breast tomosynthesis (Yang et al., J. Radiol. Prot. 2017).
  You can also design **departments**, with several rooms on one floor plan.
- **Required thickness** of lead, concrete, gypsum wallboard, steel, plate glass or wood for every barrier. The program
  uses the NCRP 147 workloads, unshielded air kerma, use and occupancy factors, preshielding and Archer transmission
  parameters.
- **Several materials in one barrier**: each material on its own (alternatives), or layers of one barrier. For layers
  you set each material's share of the shielding and the order from the room side outwards.
- **Planned thickness check**: the weekly dose beyond the barrier with the thicknesses you plan to install, compared
  with the design goal *P*.
- **Floor plan**: load the architect's drawing (PDF, PNG, JPG), trace the walls, place the source and say what lies
  beyond each wall. The program measures the distances and suggests *T* and *P*.
- **2D / 3D view**: every wall in the colours of its materials, the dose beyond each barrier and a radiation map.
  Point at a wall to see its materials and thicknesses.
- **Excel report** (summary, details, rooms), **project files** (`.shield`) and **built-in examples**.
- A **note on every field** says what to enter, with the NCRP 147 typical values.

![2D view with the radiation map](docs/images/viewer_goal.png)

## The method in brief

For each workload distribution that reaches a barrier, the unshielded weekly air kerma at the occupied point beyond it
is *K* = *N*·*U*·*T*·*K*¹ / *d*². The barrier must transmit *B* = *P* / Σ*K*, and the thickness of each material comes
from the Archer equation *x* = (1/αγ)·ln[(*B*^−γ + β/α) / (1 + β/α)].

- *d* runs from the source to the barrier, plus the distance beyond the barrier to the person (NCRP 147 §4.1.2), which
  can be edited for each barrier. The defaults are 0.3 m for walls and doors, 0.5 m for the ceiling, and 1.3 m for the
  floor (the person is 1.7 m above the floor below, with a 3 m storey).
- CT rooms use the NCRP 147 DLP method, with the scans (phases) per procedure. The NCRP default of 1.4 means 40 % of
  the procedures are scanned again with contrast.

- For primary beams given by their kVp, you can also use the transmission data of modern digital radiography
  (Li et al., Med. Phys. 2024).

The [User Guide](User%20Guide.pdf) explains every step and works through the examples by hand.

## Installing

Download `Shielding_of_X-ray_Rooms_Setup_<version>.exe` from the
[Releases](https://github.com/Shiramis/Shielding_of_X-Ray_rooms.py/releases) page and run it (Windows 10 or 11,
64-bit).

- **No administrator rights are needed**: the setup installs the program for the current user, or for all users if you
  choose so and have the rights.
- You get a Start menu entry with the program, the **User Guide** and the **Examples**. You can also choose a desktop
  icon, and whether `.shield` project files open with the program on a double-click.
- To remove it, use **Settings › Apps** or **Uninstall** in its Start menu folder. Your projects are not touched.

The setup is not digitally signed, so Windows SmartScreen may warn the first time: choose **More info › Run anyway**.

## Running from the source code

With Python 3.12 or newer (keep `Data Shielding.xlsx`, the NCRP 147 data, in the project folder):

```bash
python -m venv venv
venv\Scripts\activate            # Linux / macOS: source venv/bin/activate
pip install -r requirements.txt
python XRIFSC_code/Shielding_of_X-Ray_rooms.py
```

Then:

1. Choose **Department**, **X-Ray Room**, **CT Room** or **Mammography Room** on the start screen, or open one of the
   **Examples**.
2. Fill in the room data and the barriers. Rest the pointer on any field to see what to enter.
3. Press **Calculate** (or **Calculate all barriers**). If anything is missing, the program says what.
4. Use **Floor Plan**, **2D / 3D View** and **Export to Excel**, and save the work with **File › Save project**.

The full manual is in **Help › User Guide** (F1), the file [`User Guide.pdf`](User%20Guide.pdf).

## Project layout

| Path | Contents |
| --- | --- |
| `XRIFSC_code/Shielding_of_X-Ray_rooms.py` | Main window, menus, start screen, workspace |
| `XRIFSC_code/Department.py`, `Room.py`, `CTroom.py` | Departments and rooms |
| `XRIFSC_code/Department_defs.py` | Barrier inputs, materials, area and occupancy |
| `XRIFSC_code/Depcalculations.py` | NCRP 147 calculations, results, missing-data checks, dose check |
| `XRIFSC_code/plan_view.py` | Floor plan editor and 2D / 3D view |
| `XRIFSC_code/report.py`, `project.py`, `examples.py` | Excel report, project files, built-in examples |
| `XRIFSC_code/theme.py`, `tooltips.py` | Look of the program and the guidance notes |
| `Data Shielding.xlsx` | NCRP 147 data read by the program |
| `Examples/` | The examples as project files (`.shield`) |
| `User Guide.pdf`, `docs/` | User guide, its pictures and the scripts that build it |
| `installer/` | The Windows installer: Inno Setup script and build script |

## Building the installer

You need [Inno Setup 6](https://jrsoftware.org/isinfo.php) and, in the program's environment, PyInstaller:

```bash
venv\Scripts\python.exe -m pip install -r installer\requirements.txt
venv\Scripts\python.exe installer\build_installer.py
```

The script packs the program and its data with PyInstaller (`installer/build/dist`), then Inno Setup makes one setup
file in `installer/Output`. Set the version number in `installer/build_installer.py`. Publish the setup file as a GitHub
release asset rather than committing it.

## Updating the user guide

```bash
venv\Scripts\python.exe docs\capture_screens.py   # pictures of the program and the example values (Windows)
pip install -r docs/requirements.txt              # reportlab, pillow, openpyxl
python docs/make_user_guide.py                    # writes "User Guide.pdf"
```

The guide recalculates every worked example by hand and stops if a result differs from the program's.

## References

- NCRP Report No. 147, *Structural Shielding Design for Medical X-Ray Imaging Facilities*, NCRP, 2004.
- Sutton D.G., Martin C.J., Williams J.R., Peet D.J., *Radiation Shielding for Diagnostic Radiology*, 2nd ed.,
  BIR, 2012.
- Archer B.R., Thornby J.I., Bushong S.C., Diagnostic X-ray shielding design based on an empirical model of photon
  attenuation, *Health Physics* 44:507–517, 1983.
- Yang K., Schultz T.J., Li X., Liu B., Radiation shielding calculation for digital breast tomosynthesis rooms with
  an updated workload survey, *J. Radiol. Prot.* 37:230–246, 2017.
- Li X., Marschall T.A., Yang K., Liu B., Radiation shielding transmission data for modern digital radiography,
  *Med. Phys.*, 2024, doi:10.1002/mp.17449.

The program supports a qualified expert. The final shielding design and its verification remain the responsibility of
the radiation protection expert or medical physicist.
