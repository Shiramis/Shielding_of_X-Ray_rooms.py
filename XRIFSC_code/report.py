import os
import textwrap
from datetime import date
from tkinter import filedialog, messagebox, TclError
import xlsxwriter

from theme import plain, rich_parts

MATERIALS = ["Lead", "Concrete", "Gypsum Wallboard", "Steel", "Plate Glass", "Wood"]

# The notes under the Summary, each with what it is about: a note of something the report does not have is left out
NOTES = [
    ("always", "Method: NCRP Report No. 147 (2004), Structural Shielding Design for Medical X-Ray Imaging "
               "Facilities."),
    ("literature", "Workload distributions whose name ends with a source use data of the literature instead of NCRP "
                   "147: Kirby et al. 2023 (digital radiography, made into air kerma and transmission with the "
                   "NCRP 147 method), Chen et al. 2013 (radiographic rooms in Taiwan), Biondi et al. 2024 "
                   "(interventional rooms), Judge et al. 2013 (digital mammography), Yang et al. 2017 and Li et al. "
                   "2013 (tomosynthesis; toward each barrier: Yang et al. 2016), Li et al. 2024 (orthopedic table "
                   "bucky, concrete); kVp data: 'DR 600' Li et al. 2024, W/Al and W/Rh Li et al. 2012, W/Ag Li et "
                   "al. 2013. See the User Guide."),
    ("xray", "Air kerma beyond the barrier for each radiation type: K = N · U · T · K¹ / d²  (mGy/week)."),
    ("always", "Required transmission: B = P / ΣK, with P the shielding design goal of the area beyond the barrier."),
    ("xray", "Thickness: every radiation type goes through the barrier with its own α, β, γ (of its workload "
             "distribution, primary or secondary) and its own preshielding, so that Σ K · B(x + x_pre) = P (NCRP 147 "
             "5.3.5, 5.4.2). With one radiation type: x = (1/αγ) · ln[(B^−γ + β/α) / (1 + β/α)] − x_pre."),
    ("xray", "d goes from the source to the occupied point (d_{P} primary, d_{L} leakage, d_{S} scatter, d_{sec} "
             "leakage and scatter): the distance to the barrier plus the distance beyond it (NCRP 147 4.1.2: 0.3 m "
             "beyond walls and doors, 0.5 m above the floor of the room above, 1.7 m above the floor below), or the "
             "whole distance when it is typed so; shown for each radiation type in the Details sheet."),
    ("ct", "CT rooms: K¹_{sec} per scan = κ · DLP (κ head 9×10⁻⁵ cm⁻¹, κ body 1.2 × 3×10⁻⁴ cm⁻¹); "
           "K = T · Σ N · s · K¹_{sec} / d_{sec}², with s the scans per procedure (NCRP 147: 1.4) and d_{sec} from "
           "the isocenter."),
    ("none needed", "A thickness of 0 mm means no additional shielding is required (B ≥ 1)."),
    ("check", "Dose beyond: weekly air kerma × T beyond the barrier with the planned thickness (or with the required "
              "thickness when none is planned), compared with the shielding design goal P."),
    ("alone", "'Each material alone': the thickness of each material if it were the only one."),
    ("layers", "'Layers': all materials together; from the inside out each takes its share of the attenuation, "
               "every layer starting at the equivalent thickness of the layers (and preshielding) in front of it."),
    ("existing", "Existing shielding: what the barrier already has (e.g. a floor slab, NCRP 147 2.3.5); the thicknesses "
                 "of the materials are those to add to it, outside it or on its room side, each layer starting at "
                 "the equivalent thickness of what is in front of it."),
    ("shared", "Shared with: the same wall as one of another room of the department; each material has the larger "
               "thickness of the two rooms (from the other room the layers are in the reverse order), and the dose "
               "beyond is checked on both sides."),
    ("far", "Further area: an area further away than the one just beyond the barrier, with its own T and P (NCRP 147 "
            "4.1.3); every radiation type reaches it that much further away, and each material has the larger "
            "thickness of the two areas."),
    ("height", "Shielding height: how high above the floor the shielding of a wall or door goes (NCRP 147 2.3.6, "
               "5.8); it does not change the thickness."),
    ("field", "Field: the scatter of a radiation type scaled to the primary field given, (F / d_F²) / (F₀ / d_F₀²) "
              "with F₀ at d_F₀ the field of NCRP 147 Table 4.7 (NCRP 147 4.1.7.2, Eq. C.2); the leakage is not "
              "scaled. An air kerma written is scaled whole, from the field it was written for."),
    ("angle", "Scatter at an angle: for a kVp, K¹ = K_W¹(kVp) · 2.5 mA·min · a₁(θ, kVp) · 10⁻⁶ · F / d_F² (NCRP 147 "
              "Eq. C.2, Figures B.1 and C.1), with the leakage of the tube at that kVp if ticked (Eq. C.6-C.9)."),
    ("allowed", "Workload allowed: the workload at which the dose beyond the barrier as it will be built (planned "
                "thicknesses and existing shielding) reaches P (NCRP 147 6.3.3, 6.4); every radiation type of the "
                "barrier grows with it."),
]


def existing_text(rec):
    existing = rec.get("existing")
    if not existing:
        return None
    layers = " + ".join(f"{m} {x:g} mm" for m, x in existing["layers"])
    return layers + (" (new materials outside it)" if existing["side"] == "outside" else
                     " (new materials on its room side)")


def far_text(rec):
    far = rec.get("far")
    if not far:
        return None
    text = (f"{far['delta']:g} m further" + (f", {far['location']}" if far.get("location") else "")
            + f", T {far['T']:g}, P {far['P']:g}")
    governs = {g for g in far.get("governs") or [] if g}
    return text + (" (governs)" if governs == {"other"} else " (the area just beyond governs)"
                   if governs == {"this"} else "")


def shared_text(rec):
    shared = rec.get("shared")
    if not shared:
        return None
    text = f"{shared['room']} · {shared['barrier']}"
    if shared["state"] == "ok":
        governs = {g for g in shared["governs"] if g}
        who = shared["room"] if governs == {"other"} else "this room" if governs == {"this"} else "per material"
        return text + f" (the larger of the two rooms: {who})"
    return text + (" (not calculated there yet)" if shared["state"] == "not calculated" else
                   " (missing data there)" if shared["state"] == "missing" else "")


def allowed_text(allowed):
    if not allowed or allowed.get("state") != "ok":
        return None
    rows = allowed["rows"]
    if len(rows) == 1:
        return f"{rows[0]['text']}, with {allowed['basis']}"
    return "; ".join(f"{row['room']}: {row['text']}" for row in rows) + f", with {allowed['basis']}"


def write_report(path, title, rooms):
    """Write the shielding report of the given rooms (see ReportExport.room_report) to an .xlsx file. A column or a
    note about something that none of the rooms has (a material not chosen, CT data in X-ray rooms, ...) is left
    out."""
    book = xlsxwriter.Workbook(path)
    f_title = book.add_format({"bold": True, "font_size": 14})
    f_sub = book.add_format({"italic": True, "font_color": "#555555"})
    f_head = book.add_format({"bold": True, "bg_color": "#2c3b47", "font_color": "#ffffff", "text_wrap": True,
                              "valign": "vcenter", "border": 1})
    f_text = book.add_format({"border": 1, "valign": "top", "text_wrap": True})
    f_bold = book.add_format({"border": 1, "valign": "top", "bold": True, "text_wrap": True})
    f_num = book.add_format({"border": 1, "valign": "top", "num_format": "General"})
    f_mm = book.add_format({"border": 1, "valign": "top", "num_format": "0.00"})
    f_sci = book.add_format({"border": 1, "valign": "top", "num_format": "0.00E+00"})
    f_ok = book.add_format({"border": 1, "valign": "top", "font_color": "#1e7b34", "text_wrap": True})
    f_bad = book.add_format({"border": 1, "valign": "top", "font_color": "#c00000", "text_wrap": True})
    f_note = book.add_format({"text_wrap": False})
    f_subscript = book.add_format({"font_script": 2})

    def write(ws, row, col, value, fmt=f_text):
        """A number, a text (its subscripts written d_{P}) or an empty cell."""
        if value is None or value == "":
            ws.write_blank(row, col, None, f_text)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            ws.write_number(row, col, value, fmt)
        else:
            text, fmt = str(value), fmt if fmt is not f_num else f_text
            parts = rich_parts(text)
            if any(sub for _, sub in parts) and len(parts) > 1:
                fragments = []
                for part, sub in parts:
                    fragments += [f_subscript, part] if sub else [part]
                ws.write_rich_string(row, col, *fragments, fmt)
            else:
                ws.write_string(row, col, text, fmt)

    def shown(value, fmt):
        """About how many characters the cell shows."""
        if value is None or value == "":
            return 0
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return 9 if fmt is f_sci else len(f"{value:.2f}") if fmt is f_mm else min(len(f"{value:g}"), 11)
        return len(plain(str(value)))

    def table(name, subtitle, columns, rows):
        """columns: [(heading, width, format, keep)]; rows: [[value or (value, format)]]. A column that is empty in
        every row is left out, unless keep. Every heading word and number fits its column; the rows take the height
        of their wrapped text when Excel opens the file."""
        cells = [[item if isinstance(item, tuple) else (item, columns[k][2]) for k, item in enumerate(row)]
                 for row in rows]
        used = [k for k, column in enumerate(columns)
                if column[3] or any(row[k][0] not in (None, "") for row in cells)]
        ws = book.add_worksheet(name)
        ws.write(0, 0, f"Shielding report: {title}", f_title)
        ws.write(1, 0, f"{subtitle}   ·   NCRP Report No. 147 (2004)   ·   {date.today():%d/%m/%Y}", f_sub)
        for col, k in enumerate(used):
            heading, width, fmt, _ = columns[k]
            longest = max(len(word) for word in heading.split())
            data = max([shown(value, fmt) for value, fmt in (row[k] for row in cells)] + [0])
            # wide enough for the longest heading word (bold) and the data up to 40 characters, a heading of at
            # most three lines
            width = max(width, longest * 1.2 + 1.5, min(data * 1.1 + 1.5, 40), len(heading) * 1.2 / 3 + 1.5)
            ws.set_column(col, col, width)
            ws.write(3, col, heading, f_head)
        ws.freeze_panes(4, 0)
        ws.set_landscape()
        ws.set_paper(9)  # A4
        ws.fit_to_pages(1, 0)
        ws.repeat_rows(3)
        for r, row in enumerate(cells, start=4):
            for col, k in enumerate(used):
                write(ws, r, col, *row[k])
        return ws, 4 + len(cells)

    records = [(room, barrier, barrier["record"]) for room in rooms for barrier in room["barriers"]
               if barrier["record"] is not None]

    # ===== Summary: one row per barrier =====
    chosen = {material for _, _, rec in records for material, _ in rec.get("thickness", [])}
    materials = [m for m in MATERIALS if m in chosen]  # only the materials chosen somewhere
    columns = ([("Room", 18, f_bold, True), ("Room type", 16, f_text, True), ("Barrier", 11, f_text, True),
                ("Area", 17, f_text, False), ("Location / T source", 26, f_text, False), ("T", 6, f_num, False),
                ("P (mGy/week)", 9, f_num, False), ("ΣK (mGy/week)", 10, f_sci, False), ("B", 10, f_sci, False)]
               + [(f"{m} (mm)", 9, f_mm, True) for m in materials]
               + [("Dose beyond (mGy/week)", 11, f_sci, False), ("Goal P", 26, f_text, False),
                  ("Materials", 30, f_text, False), ("Shielding height", 14, f_text, False),
                  ("Existing shielding", 26, f_text, False), ("Further area", 28, f_text, False),
                  ("Shared with", 26, f_text, False), ("Workload allowed", 34, f_text, False),
                  ("Status", 40, f_text, True)])
    rows = []
    for room in rooms:
        for barrier in room["barriers"]:
            rec = barrier["record"]
            row = [room["name"], room["type"], barrier["name"]]
            if rec is None:
                rows.append(row + [None] * (len(columns) - 4) + [("Not calculated", f_bad)])
                continue
            thickness = dict(rec.get("thickness", []))
            check = barrier.get("check")
            layers = rec.get("layers")
            row += [rec.get("area"), rec.get("location"), rec.get("T"), rec.get("P"), rec.get("K_total"), rec.get("B")]
            row += [thickness.get(material) for material in materials]
            goal = None
            if check:
                goal = ("met" if check["dose"] <= check["P"] * 1.0001 else "EXCEEDED") + f" ({check['basis']})"
                for key in ("far", "other", "other_far"):  # the other areas the barrier protects
                    area = check.get(key)
                    if area:
                        goal += (f"; {'toward ' if key != 'far' else ''}{area['room']}: {area['dose']:.3g} mGy/week, "
                                 + ("met" if area["ok"] else "EXCEEDED"))
                goal = (goal, f_ok if check["ok"] else f_bad)
            row += [check["dose"] if check else None, goal,
                    ("Layers, inside → outside: " + ", ".join(f"{m} {share:g} %" for m, share in layers))
                    if layers else "Each material alone" if thickness else None,
                    barrier.get("height"), existing_text(rec), far_text(rec), shared_text(rec),
                    allowed_text(barrier.get("allowed"))]
            if rec.get("missing"):
                row.append(("Missing: " + "; ".join(rec["missing"]), f_bad))
            elif not thickness:
                row.append(("No material selected", f_bad))
            else:
                row.append(("OK", f_ok))
            rows.append(row)
    ws, row = table("Summary", "Required barrier thickness", columns, rows)

    # the notes of what the report has
    distributions = [dist for _, _, rec in records for dist in rec.get("distributions") or []]
    has = {"always": True,
           "literature": any(mark in (dist.get("distribution") or "") for dist in distributions
                             for mark in (" – ", "Li 20", "DR 600")),
           "xray": any(rec["kind"] != "ct" for _, _, rec in records),
           "ct": any(rec["kind"] == "ct" for _, _, rec in records),
           "none needed": any(x == 0 for _, _, rec in records for _, x in rec.get("thickness", [])),
           "check": any(barrier.get("check") for _, barrier, _ in records),
           "layers": any(rec.get("layers") for _, _, rec in records),
           "alone": any(not rec.get("layers") and len(rec.get("thickness", [])) > 1 for _, _, rec in records),
           "existing": any(rec.get("existing") for _, _, rec in records),
           "far": any(rec.get("far") for _, _, rec in records),
           "height": any(barrier.get("height") for _, barrier, _ in records),
           "field": any(", field " in (dist.get("k1_source") or "") for dist in distributions),
           "shared": any(rec.get("shared") for _, _, rec in records),
           "angle": any("(NCRP 147 Appendix C" in (dist.get("k1_source") or "") for dist in distributions),
           "allowed": any(allowed_text(barrier.get("allowed")) for _, barrier, _ in records)}
    row += 1
    ws.write(row, 0, "Notes", f_title)
    for about, note in NOTES:
        if has[about]:
            row += 1
            write(ws, row, 0, "• " + note, f_note)

    # ===== Details: one row per radiation type =====
    columns = [("Room", 18, f_bold, True), ("Barrier", 11, f_text, True), ("Radiation type", 9, f_text, True),
               ("Primary / secondary", 11, f_text, False), ("Workload distribution", 26, f_text, False),
               ("K¹ source", 26, f_text, False), ("Preshielding", 11, f_text, False),
               ("N (patients/week)", 11, f_num, False), ("U", 7, f_num, False), ("T", 7, f_num, False),
               ("K¹ (mGy/patient at 1 m)", 12, f_sci, False), ("Distance", 8, f_text, False),
               ("Source to the barrier (m)", 10, f_num, False), ("+ to the person beyond it (m)", 11, f_num, False),
               ("d (m)", 8, f_num, False), ("K (mGy/week)", 11, f_sci, False)]
    rows = []
    for room, barrier, rec in records:
        ct = room.get("ct") or {}
        # from the source to the barrier and beyond it, or the whole distance typed to the person
        parts = lambda typed: ([None, "– (the whole distance is typed)"] if rec.get("whole")
                               else [typed, rec.get("beyond")])
        if rec["kind"] == "ct":
            rows.append([room["name"], barrier["name"], "#1", "Secondary (CT)",
                         f"{rec.get('kvp')} kVp" if rec.get("kvp") else "", "DLP (NCRP 147)", "",
                         f"{ct.get('body') or 0} body + {ct.get('head') or 0} head", None, rec.get("T"), None,
                         "d_{sec} (isocenter)", *parts(rec.get("D")), rec.get("d"), rec.get("K_total")])
        else:
            rows += [[room["name"], barrier["name"], f"#{dist['no']}", dist["radiation"], dist["distribution"],
                      dist["k1_source"], dist["preshielding"], dist["N"], dist["U"], dist["T"], dist["K1"],
                      dist.get("symbol"), *parts(dist.get("D")), dist["d"], dist["K"]]
                     for dist in rec["distributions"]]
    table("Details", "Inputs of each radiation type", columns, rows)

    # ===== Rooms: room-level inputs (CT: procedures, scans, DLP and kVp) =====
    columns = [("Room", 22, f_bold, True), ("Room type", 18, f_text, True), ("Workload", 28, f_text, False),
               ("Body procedures/week", 12, f_num, False), ("Head procedures/week", 12, f_num, False),
               ("Scans per body procedure", 11, f_num, False), ("Scans per head procedure", 11, f_num, False),
               ("DLP per body scan (mGy·cm)", 12, f_num, False), ("DLP per head scan (mGy·cm)", 12, f_num, False),
               ("kVp", 8, f_num, False), ("Barriers", 9, f_num, True), ("Barriers calculated", 11, f_num, True)]
    rows = []
    for room in rooms:
        ct = room.get("ct") or {}
        rows.append([room["name"], room["type"], room.get("workload"), ct.get("body"), ct.get("head"),
                     ct.get("scans_body"), ct.get("scans_head"), ct.get("dlp_body"), ct.get("dlp_head"),
                     ct.get("kvp"), len(room["barriers"]), sum(1 for b in room["barriers"] if b["record"])])
    table("Rooms", "Room data", columns, rows)

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
            option = self.d.get(f"checkpatients {e}{nr}")
            info["barriers"].append({"name": self.barn[f"lab_bar {e}{nr}"].cget("text"),
                                     "record": self.calc.get((nr, e)), "check": self.dose_check(nr, e),
                                     "allowed": self.allowed_workload(nr, e)
                                     if option is not None and option.get() == 1 else None,
                                     "height": self.height_text(e, nr)})
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
