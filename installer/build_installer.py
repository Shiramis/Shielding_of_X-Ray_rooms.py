"""Builds the Windows installer: installer/Output/Shielding_of_X-ray_Rooms_Setup_<version>.exe

    venv\\Scripts\\python.exe installer\\build_installer.py

Needs, in the program's Python environment: the packages of requirements.txt and PyInstaller
(pip install -r installer/requirements.txt), and Inno Setup 6 on the computer (https://jrsoftware.org/isinfo.php).
Steps: PyInstaller packs the program and its data into installer/build/dist, then Inno Setup turns that folder into
one setup file, which installs the program with a Start menu entry, the examples and the user guide.
"""
import os
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

VERSION = "2.0.0"  # also shown in Apps & features; raise it for every new release
NAME = "Shielding of X-ray Rooms"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CODE = os.path.join(ROOT, "XRIFSC_code")
BUILD = os.path.join(HERE, "build")
DIST = os.path.join(BUILD, "dist")
# Files the program reads next to itself (Help menu, NCRP 147 data, icons)
DATA = [os.path.join(ROOT, "Data Shielding.xlsx"), os.path.join(ROOT, "User Guide.pdf"),
        os.path.join(ROOT, "5_NCRP_147_2004.pdf"), os.path.join(CODE, "app_icon.png"),
        os.path.join(CODE, "app_icon.ico")]
NAVY, ACCENT = (20, 33, 46), (26, 115, 200)


def run(command):
    print(">", " ".join(f'"{c}"' if " " in c else c for c in command), flush=True)
    subprocess.run(command, check=True)


def pack_program():
    """The program as a folder: the .exe with Python, the libraries and the data files beside it."""
    for path in DATA:
        if not os.path.exists(path):
            sys.exit(f"Missing file: {path}")
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", NAME,
               "--icon", os.path.join(CODE, "app_icon.ico"),
               "--contents-directory", ".",  # data files next to the .exe, where the program looks for them
               "--distpath", DIST, "--workpath", os.path.join(BUILD, "work"), "--specpath", BUILD,
               "--paths", CODE,
               "--exclude-module", "pandas"]  # only an optional extra of openpyxl and matplotlib: not used
    for path in DATA:
        command += ["--add-data", f"{path}{os.pathsep}."]
    run(command + [os.path.join(CODE, "Shielding_of_X-Ray_rooms.py")])


def wizard_images():
    """Pictures of the setup wizard, in the colours of the program."""
    icon = Image.open(os.path.join(CODE, "app_icon.png")).convert("RGBA")
    # side picture of the first and last pages (164 x 314 at 100 %, drawn at 200 % for sharp screens)
    large = Image.new("RGB", (328, 628), NAVY)
    draw = ImageDraw.Draw(large)
    draw.rectangle((0, 600, 328, 628), fill=ACCENT)
    large.paste(icon.resize((180, 180), Image.Resampling.LANCZOS), (74, 150), icon.resize((180, 180)))
    try:
        font = ImageFont.truetype("segoeuil.ttf", 34)
        small = ImageFont.truetype("segoeui.ttf", 21)
    except OSError:
        font = small = ImageFont.load_default()
    for k, line in enumerate(("Shielding of", "X-ray Rooms")):
        width = draw.textlength(line, font=font)
        draw.text(((328 - width) / 2, 370 + 44 * k), line, font=font, fill=(240, 244, 248))
    note = "NCRP Report No. 147"
    draw.text(((328 - draw.textlength(note, font=small)) / 2, 480), note, font=small, fill=(159, 179, 200))
    large.save(os.path.join(BUILD, "wizard_large.bmp"))
    # small picture at the top right of the other pages (55 x 55 at 100 %)
    tile = Image.new("RGB", (110, 110), (255, 255, 255))
    tile.paste(icon.resize((100, 100), Image.Resampling.LANCZOS), (5, 5), icon.resize((100, 100)))
    tile.save(os.path.join(BUILD, "wizard_small.bmp"))


def find_iscc():
    candidates = [shutil.which("iscc"),
                  os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),
                  os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Inno Setup 6", "ISCC.exe"),
                  os.path.join(os.environ.get("ProgramFiles", ""), "Inno Setup 6", "ISCC.exe")]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    sys.exit("Inno Setup 6 was not found: install it from https://jrsoftware.org/isinfo.php")


def main():
    os.makedirs(BUILD, exist_ok=True)
    pack_program()
    wizard_images()
    run([find_iscc(), f"/DAppVersion={VERSION}", f"/DSourceDir={os.path.join(DIST, NAME)}",
         os.path.join(HERE, f"{NAME}.iss")])
    setup = os.path.join(HERE, "Output", f"Shielding_of_X-ray_Rooms_Setup_{VERSION}.exe")
    print(f"\nInstaller: {setup}  ({os.path.getsize(setup) / 2 ** 20:.0f} MB)")


if __name__ == "__main__":
    main()
