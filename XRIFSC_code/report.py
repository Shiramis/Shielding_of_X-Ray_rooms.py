import os
from datetime import date
from tkinter import filedialog, messagebox, TclError
import xlsxwriter

MATERIALS = ["Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass", "Wood"]

NOTES = [
    "Method: NCRP Report No. 147 (2004), Structural Shielding Design for Medical X-Ray Imaging Facilities.",
    "Workload distributions whose name ends with a source use data of the literature instead of NCRP 147: Yang "
    "et al. 2017 (tomosynthesis), Kirby et al. 2023 (digital radiography, made into air kerma and transmission with "
    "the NCRP 147 method), Biondi et al. 2024 (interventional rooms); 'DR 600' kVp data: Li et al. 2024. See the "
    "User Guide.",
    "Air kerma beyond the barrier for each radiation type: K = N · U · T · K¹ / d²  (mGy/week).",
    "Required transmission: B = P / ΣK, with P the shielding design goal of the area beyond the barrier.",
    "Thickness: every radiation type goes through the barrier with its own α, β, γ (of its workload distribution, "
    "primary or secondary) and its own preshielding, so that Σ K · B(x + x_pre) = P (NCRP 147 5.3.5, 5.4.2). With "
    "one radiation type: x = (1/αγ) · ln[(B^−γ + β/α) / (1 + β/α)] − x_pre.",
    "d goes from the source to the occupied point (dP primary, dL leakage, dS scatter, dsec leakage and scatter): "
    "the distance to the barrier plus the distance beyond it (NCRP 147 4.1.2: 0.3 m beyond walls and door, 0.5 m "
    "above the floor of the room above, 1.7 m above the floor below), or the whole distance when it is typed so; "
    "shown for each radiation type in the Details sheet.",
    "CT rooms: K¹sec per scan = κ · DLP (κ head 9×10⁻⁵ cm⁻¹, κ body 1.2 × 3×10⁻⁴ cm⁻¹); "
    "K = T · Σ N · s · K¹sec / d², with s the scans per procedure (NCRP 147: 1.4) and d from the isocenter.",
    "A thickness of 0 mm means no additional shielding is required (B ≥ 1).",
    "Dose beyond: weekly air kerma × T beyond the barrier with the planned thickness (or with the required "
    "thickness when none is planned), compared with the shielding design goal P.",
    "'Each material alone': the thickness of each material if it were the only one. 'Layers': all materials "
    "together; from the inside out each takes its share of the attenuation, every layer starting at the equivalent "
    "thickness of the layers (and preshielding) in front of it.",
]


def write_report(path, title, rooms):
    """Write the shielding report of the given rooms (see ReportExport.room_report) to an .xlsx file."""
    book = xlsxwriter.Workbook(path)
    f_title = book.add_format({"bold": True, "font_size": 14})
    f_sub = book.add_format({"italic": True, "font_color": "#555555"})
    f_head = book.add_format({"bold": True, "bg_color": "#2c3b47", "font_color": "#ffffff", "text_wrap": True,
                              "valign": "vcenter", "border": 1})
    f_text = book.add_format({"border": 1, "valign": "top", "text_wrap": True})
    f_bold = book.add_format({"border": 1, "valign": "top", "bold": True})
    f_num = book.add_format({"border": 1, "valign": "top", "num_format": "General"})
    f_mm = book.add_format({"border": 1, "valign": "top", "num_format": "0.00"})
    f_sci = book.add_format({"border": 1, "valign": "top", "num_format": "0.00E+00"})
    f_ok = book.add_format({"border": 1, "valign": "top", "font_color": "#1e7b34"})
    f_bad = book.add_format({"border": 1, "valign": "top", "font_color": "#c00000", "text_wrap": True})
    f_note = book.add_format({"text_wrap": False})

    def cell(ws, row, col, value, fmt=f_text):
        if value is None or value == "":
            ws.write_blank(row, col, None, f_text)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            ws.write_number(row, col, value, fmt)
        else:
            ws.write_string(row, col, str(value), fmt if fmt is not f_num else f_text)

    def sheet(name, subtitle, columns):
        ws = book.add_worksheet(name)
        ws.write(0, 0, f"Shielding report: {title}", f_title)
        ws.write(1, 0, f"{subtitle}   ·   NCRP Report No. 147 (2004)   ·   {date.today():%d/%m/%Y}", f_sub)
        for col, (heading, width) in enumerate(columns):
            ws.write(3, col, heading, f_head)
            ws.set_column(col, col, width)
        ws.set_row(3, 32)
        ws.freeze_panes(4, 0)
        ws.set_landscape()
        ws.set_paper(9)  # A4
        ws.fit_to_pages(1, 0)
        ws.repeat_rows(3)
        return ws

    # ===== Summary: one row per barrier =====
    ws = sheet("Summary", "Required barrier thickness",
               [("Room", 18), ("Room type", 16), ("Barrier", 11), ("Area", 17), ("Location / T source", 26),
                ("T", 6), ("P (mGy/week)", 9), ("ΣK (mGy/week)", 10), ("B", 10)]
               + [(f"{m} (mm)", 9) for m in MATERIALS]
               + [("Dose beyond (mGy/week)", 11), ("Goal P", 26), ("Materials", 30), ("Status", 40)])
    row = 4
    for room in rooms:
        for barrier in room["barriers"]:
            rec = barrier["record"]
            cell(ws, row, 0, room["name"], f_bold)
            cell(ws, row, 1, room["type"])
            cell(ws, row, 2, barrier["name"])
            if rec is None:
                for col in range(3, 12 + len(MATERIALS)):
                    cell(ws, row, col, None)
                cell(ws, row, 12 + len(MATERIALS), "Not calculated", f_bad)
            else:
                cell(ws, row, 3, rec.get("area"))
                cell(ws, row, 4, rec.get("location"))
                cell(ws, row, 5, rec.get("T"), f_num)
                cell(ws, row, 6, rec.get("P"), f_num)
                cell(ws, row, 7, rec.get("K_total"), f_sci)
                cell(ws, row, 8, rec.get("B"), f_sci)
                thickness = dict(rec.get("thickness", []))
                for k, material in enumerate(MATERIALS):
                    cell(ws, row, 9 + k, thickness.get(material), f_mm)
                check = barrier.get("check")
                cell(ws, row, 9 + len(MATERIALS), check["dose"] if check else None, f_sci)
                cell(ws, row, 10 + len(MATERIALS), None if not check else (
                    ("met" if check["ok"] else "EXCEEDED") + f" ({check['basis']})"), f_ok if check and check["ok"]
                     else f_bad)
                layers = rec.get("layers")
                cell(ws, row, 11 + len(MATERIALS), "Layers, inside → outside: " + ", ".join(
                    f"{m} {share:g} %" for m, share in layers) if layers else "Each material alone")
                if rec.get("missing"):
                    cell(ws, row, 12 + len(MATERIALS), "Missing: " + "; ".join(rec["missing"]), f_bad)
                elif not thickness:
                    cell(ws, row, 12 + len(MATERIALS), "No material selected", f_bad)
                else:
                    cell(ws, row, 12 + len(MATERIALS), "OK", f_ok)
            row += 1
    row += 1
    ws.write(row, 0, "Notes", f_title)
    for note in NOTES:
        row += 1
        ws.write(row, 0, "• " + note, f_note)

    # ===== Details: one row per radiation type =====
    ws = sheet("Details", "Inputs of each radiation type",
               [("Room", 18), ("Barrier", 11), ("Radiation type", 9), ("Primary / secondary", 11),
                ("Workload distribution", 26), ("K¹ source", 26), ("Preshielding", 11), ("N (patients/week)", 11),
                ("U", 7), ("T", 7), ("K¹ (mGy/patient at 1 m)", 12), ("Distance", 8),
                ("Source to the barrier (m)", 10), ("+ to the person beyond it (m)", 11), ("d (m)", 8),
                ("K (mGy/week)", 11)])
    row = 4
    for room in rooms:
        ct = room.get("ct") or {}
        for barrier in room["barriers"]:
            rec = barrier["record"]
            if rec is None:
                continue
            # from the source to the barrier and beyond it, or the whole distance typed to the person
            parts = lambda typed: ([None, "– (the whole distance is typed)"] if rec.get("whole")
                                   else [typed, rec.get("beyond")])
            if rec["kind"] == "ct":
                values = [room["name"], barrier["name"], "#1", "Secondary (CT)",
                          f"{rec.get('kvp')} kVp" if rec.get("kvp") else "", "DLP (NCRP 147)", "",
                          f"{ct.get('body') or 0} body + {ct.get('head') or 0} head", None, rec.get("T"), None,
                          "dsec (isocenter)", *parts(rec.get("D")), rec.get("d"), rec.get("K_total")]
                rows = [values]
            else:
                rows = [[room["name"], barrier["name"], f"#{dist['no']}", dist["radiation"], dist["distribution"],
                         dist["k1_source"], dist["preshielding"], dist["N"], dist["U"], dist["T"], dist["K1"],
                         dist.get("symbol"), *parts(dist.get("D")), dist["d"], dist["K"]]
                        for dist in rec["distributions"]]
            for values in rows:
                for col, value in enumerate(values):
                    fmt = f_bold if col == 0 else f_sci if col in (10, 15) else f_num
                    cell(ws, row, col, value, fmt)
                row += 1

    # ===== Rooms: room-level inputs =====
    ws = sheet("Rooms", "Room data",
               [("Room", 22), ("Room type", 18), ("Workload", 28), ("Body procedures/week", 12),
                ("Head procedures/week", 12), ("Scans per body procedure", 11), ("Scans per head procedure", 11),
                ("DLP per body scan (mGy·cm)", 12), ("DLP per head scan (mGy·cm)", 12), ("kVp", 8),
                ("Barriers", 9), ("Calculated", 10)])
    row = 4
    for room in rooms:
        ct = room.get("ct") or {}
        calculated = sum(1 for b in room["barriers"] if b["record"] is not None)
        values = [room["name"], room["type"], room.get("workload"), ct.get("body"), ct.get("head"),
                  ct.get("scans_body"), ct.get("scans_head"), ct.get("dlp_body"), ct.get("dlp_head"), ct.get("kvp"),
                  len(room["barriers"]), calculated]
        for col, value in enumerate(values):
            cell(ws, row, col, value, f_bold if col == 0 else f_num)
        row += 1

    book.close()


class ReportExport:
    def room_report(self, t):
        """Collect everything the report needs about one room."""
        def value(key):
            try:
                return self.d[key].get()
            except (KeyError, AttributeError, TclError):
                return None
        nr = self.d[f"nr {t}"]
        room_type = self.d[f"vselroom {t}"].get()
        info = {"name": self.room_name(t), "type": room_type, "workload": "", "ct": None, "barriers": []}
        if room_type == "CT Room":
            info["ct"] = {"body": value(f"bp_var {t}"), "head": value(f"hp_var {t}"),
                          "dlp_body": value(f"dlpb_var {t}"), "dlp_head": value(f"dlph_var {t}"),
                          "kvp": value(f"kvp_var {t}"), "scans_body": self.ct_scans(t, "body"),
                          "scans_head": self.ct_scans(t, "head")}
        elif value(f"vrawork {t}") == 1 and value(f"worentry {t}"):
            info["workload"] = f"{value(f'worentry {t}')} mA·min/week (total workload)"
        elif value(f"vrawork {t}") == 2 and value(f"numpapwe {t}"):
            info["workload"] = f"{value(f'numpapwe {t}')} patients/week"
        for e in range(1, self.d[f"x {t}"] + 1):
            info["barriers"].append({"name": self.barn[f"lab_bar {e}{nr}"].cget("text"),
                                     "record": self.calc.get((nr, e)), "check": self.dose_check(nr, e)})
        return info

    def export_report(self, title, rooms):
        if not rooms:
            messagebox.showinfo("Export to Excel", "Design at least one room first.", parent=self.master)
            return
        file_name = "".join(ch for ch in title if ch not in '\\/:*?"<>|').strip() or "Shielding report"
        path = filedialog.asksaveasfilename(parent=self.master, title="Export report",
                                            defaultextension=".xlsx", filetypes=[("Excel workbook", "*.xlsx")],
                                            initialdir=os.path.expanduser("~"), initialfile=f"{file_name}.xlsx")
        if not path:
            return
        try:
            write_report(path, title, [self.room_report(t) for t in rooms])
        except PermissionError:
            messagebox.showerror("Export to Excel", f"Cannot write\n{path}\n\nClose it in Excel and try again.",
                                 parent=self.master)
            return
        if hasattr(os, "startfile"):
            os.startfile(path)
