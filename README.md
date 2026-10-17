<img src="XRIFSC_code/app_icon.png" width="72" align="right" alt="">

# Shielding of X-ray Rooms

A desktop program for the **structural shielding design of medical X-ray imaging facilities**, following
**NCRP Report No. 147** (2004). It works out how thick the walls, floor, ceiling and door of a room must be, and checks
the thickness you plan to install.

![An X-ray room with its results](docs/images/xray_overview.png)

## What it does

- **Room types**: X-ray rooms (radiography, R&F, chest, angiography), CT rooms (from the DLP) and mammography rooms.
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
from the Archer equation *x* = (1/αγ)·ln[(*B*^−γ + β/α) / (1 + β/α)]. CT rooms use the NCRP 147 DLP method. The
[User Guide](User%20Guide.pdf) explains every step and works through the examples by hand.

## Running the program

**Windows, ready to run:** start `Shielding_of_X-Ray_rooms.exe`. Keep `Data Shielding.xlsx` (the NCRP 147 data) and
the PDF files of the Help menu in the same folder.

**From the source code** (Python 3.12 or newer):

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
|---|---|
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

## Building the Windows executable

With [PyInstaller](https://pyinstaller.org) installed in the same environment:

```bash
pyinstaller --onefile --windowed --name Shielding_of_X-Ray_rooms --icon XRIFSC_code/app_icon.ico ^
  --add-data "XRIFSC_code/app_icon.png;." --add-data "XRIFSC_code/app_icon.ico;." ^
  --add-data "Data Shielding.xlsx;." --add-data "User Guide.pdf;." ^
  --add-data "5_NCRP_147_2004.pdf;." --add-data "book.9780905749747.pdf;." ^
  XRIFSC_code/Shielding_of_X-Ray_rooms.py
```

The program writes its `Examples` folder next to the executable the first time it runs.

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

The program supports a qualified expert. The final shielding design and its verification remain the responsibility of
the radiation protection expert or medical physicist.
