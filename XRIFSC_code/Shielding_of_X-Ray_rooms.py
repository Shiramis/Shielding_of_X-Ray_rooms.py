import tkinter
import os
import sys
import platform
import traceback
from datetime import datetime
from tkinter import *
from tkinter import ttk
from tkinter import font
from tkinter import simpledialog, messagebox
from Department import ddepartment
from Depcalculations import departprimsec, resource_path
from QuickCalculations import dqprimsec
from Quickcal import dquick
from Department_defs import dep_defs
from Room import droom
from CTroom import CT_Room
from report import ReportExport
from plan_view import PlanViews
from project import ProjectFile
from examples import Examples, EXAMPLES, ensure_example_files
import theme
from PIL import ImageTk


theme.make_dpi_aware()  # sharp text on scaled Windows screens
root = Tk()
font.families()
pat = 0
pat2 = 0
pat3 = 0
r2 = 0
root.title("Shielding of X-ray Rooms")
theme.apply_theme(root)
# Icons next to this file (inside the bundle for the .exe), whatever folder the program is started from
HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
BIR_BOOK = "book.9780905749747.pdf"  # BIR 2012: in the Help menu only when this file is next to the program


def set_app_icon(window):
    """Icon of the title bar and the taskbar. Set once the window is complete: on Windows, attaching the menu bar
    rebuilds the window frame and drops an icon set earlier."""
    try:
        window.app_icon = PhotoImage(file=os.path.join(HERE, "app_icon.png"))  # kept, so it is not deleted
        window.iconphoto(True, window.app_icon)  # this window and every new one; PhotoImage cannot read .ico
        if platform.system() == "Windows":
            ico = os.path.join(HERE, "app_icon.ico")  # sharper on Windows
            window.iconbitmap(ico)
            window.iconbitmap(default=ico)
    except TclError:
        pass  # a missing icon must not stop the program


def report_error(kind, value, trace):
    """An unexpected error: shown to the user and kept in a log file (the installed program has no console)."""
    details = "".join(traceback.format_exception(kind, value, trace))
    if sys.stderr is not None:
        sys.stderr.write(details)
    folder = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "Shielding of X-ray Rooms")
    where = ""
    try:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "errors.log"), "a", encoding="utf-8") as log:
            log.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}\n{details}\n")
        where = f"\n\nThe details are saved in:\n{os.path.join(folder, 'errors.log')}"
    except OSError:
        pass
    messagebox.showerror("Unexpected error", f"Something went wrong: {value}{where}", parent=root)


root.report_callback_exception = report_error
root.state('zoomed')



class App(ddepartment,dep_defs,departprimsec,dqprimsec,dquick,droom,CT_Room,ReportExport,PlanViews,ProjectFile,
          Examples):

    def __init__(self, master):
        # ============Menu Bar==================
        main_menubar = Menu(root)
        root.configure(menu=main_menubar)
        #==========αρχικοποίηση παραθύρων=======
        self.depnote=None
        self.roomframe = None
        self.depframe = None
        self.quickf = None
        # ===========File=============
        self.file_menu = Menu(main_menubar, tearoff=0)
        self.newoptions = Menu(main_menubar, tearoff=0)
        main_menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_cascade(label="New...", menu=self.newoptions)
        self.newoptions.add_command(label="Design Department", command=self.creatdep)
        self.newoptions.add_command(label="Design X-Ray Room", command=self.creatroom)
        self.newoptions.add_command(label="Design CT Room", command=self.creatCTroom)
        self.newoptions.add_command(label="Design Fluoroscopy Room",
                                    command=lambda: self.creatroom("Fluoroscopy Room"))
        self.newoptions.add_command(label="Design Mammography Room",
                                    command=lambda: self.creatroom("Mammography Room"))
        #self.newoptions.add_command(label="Design Barrier", command=self.quickcal)

        self.file_menu.add_separator()
        self.file_menu.add_command(label="New project", command=self.new_project)
        self.file_menu.add_command(label="Open project...", accelerator="Ctrl+O", command=self.open_project)
        self.file_menu.add_command(label="Save project", accelerator="Ctrl+S", command=self.save_project)
        self.file_menu.add_command(label="Save project as...", command=self.save_project_as)
        self.examples_menu = self.build_examples_menu(main_menubar)
        self.file_menu.add_cascade(label="Examples", menu=self.examples_menu)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.exit_app)
        root.bind_all("<Control-o>", self.open_project)
        root.bind_all("<Control-s>", self.save_project)
        root.bind_all("<F1>", self.open_guide)
        root.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.project_path = None
        self.standalone = {}  # standalone room key t -> its tab frame
        self.standalone_count = 0  # numbers the standalone rooms, so each one has its own key
        # ==========Edit=====================
        self.edit_menu = Menu(main_menubar, tearoff=0)
        """"main_menubar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Redo",)  # command = my_text.edit_redo)
        self.edit_menu.add_command(label="Undo", )  # command = my_text.edit_undo)
        self.edit_menu.add_command(label="Cut", )  # command = my_text.edit_redo)
        self.edit_menu.add_command(label="Copy", )  # command = my_text.edit_undo)
        self.edit_menu.add_command(label="Paste", )  # command = my_text.edit_redo)
        """
        #==========help=====================
        self.help_menu = Menu(main_menubar, tearoff= 0)
        main_menubar.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="User Guide: how the program works", accelerator="F1",
                                   command=self.open_guide)
        self.help_menu.add_separator()
        self.help_menu.add_command(label= "NCRP Report No. 147", command=self.opencpr)
        if os.path.exists(resource_path(BIR_BOOK)):  # not distributed with the program
            self.help_menu.add_command(label="BIR 2012", command=self.openbir)

        self.departments = {}  # department id -> its frame, name, rooms
        self.dep_count = 0
        self.room_count = 0  # department rooms get unique keys 1, 2, 3, ... across all departments
        self.calc = {}  # (room nr, barrier) -> inputs and results of the last calculation, for the report
        self.tab_names = {}  # tab frame -> StringVar holding its name
        self.note_pairs = {}  # rooms notebook <-> results notebook of the same department
        self.plans = {}  # ('dep', id) or ('room', t) -> floor plan drawing, scale and traced rooms
        self.highlighted = {}  # (room nr, barrier) -> entries shown red because they are missing
        self.highlight_bound = set()
        self.need, self.need_fields = [], []
        self.ep = 1 #for barrier position
        self.d = {}
        self.res = {}
        self.thm = {}
        self.xlmat ={}
        self.barn={}
        self.barr={}
        self.wa={}
        self.col={}
        self.tab_links = {}  # room tab <-> results tab

        # Mouse wheel scrolls whichever canvas is under the pointer
        root.bind_all("<MouseWheel>", self.on_mousewheel)
        root.bind_all("<Shift-MouseWheel>", lambda e: self.on_mousewheel(e, horizontal=True))
        root.bind_all("<Button-4>", lambda e: self.on_mousewheel(e, units=-1))  # Linux scroll up
        root.bind_all("<Button-5>", lambda e: self.on_mousewheel(e, units=1))  # Linux scroll down

        #=====Main window scrollbar=========
        self.master = master

        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill=BOTH, expand=1)
        # ======scrollbar=========
        self.main_canvas = Canvas(self.main_frame)

        self.main_scrollbar = ttk.Scrollbar(self.main_frame, orient=HORIZONTAL, command=self.main_canvas.xview)
        self.main_scrollbar.pack(side=BOTTOM, fill=X)
        self.main_canvas.configure(xscrollcommand=self.main_scrollbar.set, bg=theme.NAVY, highlightthickness=0)
        self.main_canvas.pack(side=LEFT, fill=BOTH, expand=1)
        # =========New tab===========================
        self.new_main_Frame = ttk.Frame(self.main_canvas, style="ML.TFrame")
        self.new_main_Frame.bind('<Configure>', lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")))
        self.main_canvas.create_window((0, 0), window=self.new_main_Frame, anchor="c")
        self.main_canvas.bind("<Configure>", self.fit_start_screen)
        self.logo = ImageTk.PhotoImage(theme.draw_icon(theme.px(88)), master=root)

        # ===========Buttons========
        self.show_start_buttons()


        self.style = ttk.Style()

    def show_start_buttons(self):
        # Welcome screen: what the program does and one card for each kind of design
        self.start_frame = Frame(self.new_main_Frame, background=theme.NAVY,
                                 width=max(self.main_canvas.winfo_width(), root.winfo_screenwidth() - 20),
                                 height=max(self.main_canvas.winfo_height(), root.winfo_screenheight() - 150))
        self.start_frame.pack_propagate(False)
        self.start_frame.pack()
        content = Frame(self.start_frame, background=theme.NAVY)
        content.place(relx=0.5, rely=0.46, anchor="center")
        Label(content, image=self.logo, background=theme.NAVY).pack()
        Label(content, text="Shielding of X-ray Rooms", background=theme.NAVY, foreground=theme.ON_NAVY,
              font=(theme.LIGHT, 28)).pack(pady=(8, 0))
        Label(content, text="Structural shielding design for medical X-ray imaging facilities   ·   NCRP Report No. 147",
              background=theme.NAVY, foreground=theme.ON_NAVY_MUTED, font=(theme.FAMILY, 12)).pack(pady=(2, 34))
        Label(content, text="START A NEW DESIGN", background=theme.NAVY, foreground=theme.ON_NAVY_MUTED,
              font=(theme.SEMIBOLD, 10)).pack(anchor="w", padx=8)
        cards = Frame(content, background=theme.NAVY)
        cards.pack(pady=(8, 28))
        choices = (("Department", "Several rooms on one floor plan, each with its own results.", self.creatdep),
                   ("X-Ray Room", "Radiography and chest rooms: primary and secondary barriers.", self.creatroom),
                   ("Fluoroscopy Room", "R&F, angiography and interventional rooms.",
                    lambda: self.creatroom("Fluoroscopy Room")),
                   ("CT Room", "Secondary radiation from the DLP of body and head scans.", self.creatCTroom),
                   ("Mammography Room", "Secondary radiation only, also tomosynthesis (DBT).",
                    lambda: self.creatroom("Mammography Room")))
        per_row = len(choices) if self.master.winfo_screenwidth() >= theme.px(272) * len(choices) else 3
        for k, (title, text, command) in enumerate(choices):
            self.start_card(cards, title, text, command).grid(row=k // per_row, column=k % per_row, padx=8, pady=6)
        actions = Frame(content, background=theme.NAVY)
        actions.pack()
        ttk.Button(actions, text="Open project…", style="Ghost.TButton", command=self.open_project).pack(
            side=LEFT, padx=6)
        self.examplesbutton = ttk.Menubutton(actions, style="AL.TMenubutton", text="Examples", direction="below")
        self.examplesbutton["menu"] = self.build_examples_menu(self.examplesbutton)
        self.examplesbutton.pack(side=LEFT, padx=6)
        Label(self.start_frame, text="Tip: rest the pointer on any field to see what to enter (NCRP 147).",
              background=theme.NAVY, foreground=theme.ON_NAVY_MUTED, font=(theme.FAMILY, 10)).place(
            relx=0.5, rely=0.97, anchor="s")

    def start_card(self, parent, title, text, command):
        """A clickable card of the welcome screen."""
        card = Frame(parent, background=theme.NAVY_2, highlightthickness=1, highlightbackground=theme.NAVY_3,
                     width=theme.px(250), height=theme.px(150), cursor="hand2")
        card.pack_propagate(False)
        Frame(card, background=theme.ACCENT, height=4).pack(fill=X)
        labels = [Label(card, text=title, font=(theme.SEMIBOLD, 15), foreground=theme.ON_NAVY, anchor="w"),
                  Label(card, text=text, font=(theme.FAMILY, 11), foreground=theme.ON_NAVY_MUTED, anchor="w",
                        justify=LEFT, wraplength=theme.px(215)),
                  Label(card, text="Start  →", font=(theme.SEMIBOLD, 11), foreground="#7fb6ef", anchor="w")]
        labels[0].pack(fill=X, padx=16, pady=(14, 4))
        labels[1].pack(fill=X, padx=16)
        labels[2].pack(side=BOTTOM, fill=X, padx=16, pady=(0, 12))

        def paint(color):
            for widget in [card] + labels:
                widget.configure(background=color)

        paint(theme.NAVY_2)
        for widget in [card] + labels:
            widget.configure(cursor="hand2")
            widget.bind("<Enter>", lambda event: paint(theme.NAVY_3))
            widget.bind("<Leave>", lambda event: paint(theme.NAVY_2))
            widget.bind("<Button-1>", lambda event: self.master.after_idle(command))  # after the click is handled
        return card

    def hide_start_buttons(self):
        if getattr(self, "start_frame", None) is not None:
            self.start_frame.destroy()
            self.start_frame = None

    def fit_start_screen(self, event):
        # The welcome screen always fills the window
        if getattr(self, "start_frame", None) is not None:
            self.start_frame.configure(width=event.width, height=event.height)

    def build_examples_menu(self, parent):
        menu = Menu(parent, tearoff=0)
        for key, (title, _, _) in EXAMPLES.items():
            menu.add_command(label=f"Example: {title}", command=lambda key=key: self.open_example(key))
        menu.add_separator()
        menu.add_command(label="Open from the Examples folder...", command=self.open_examples_folder)
        return menu

    def on_mousewheel(self, event, horizontal=False, units=None):
        if units is None:
            if platform.system() == "Darwin":
                units = -event.delta
            else:
                # Touchpads send deltas smaller than 120, so always move at least one unit
                units = int(-event.delta / 120) or (-1 if event.delta > 0 else 1)
        try:
            widget = root.winfo_containing(event.x_root, event.y_root)
        except KeyError:  # pointer over a Tk-internal widget, e.g. a combobox popdown
            return
        # Scroll the innermost canvas that actually has content outside its view
        while widget is not None:
            if isinstance(widget, Canvas):
                view = widget.xview() if horizontal else widget.yview()
                if view != (0.0, 1.0):
                    if horizontal:
                        widget.xview_scroll(units, "units")
                    else:
                        widget.yview_scroll(units, "units")
                    return
            widget = widget.master

    def ensure_workspace(self):
        # Main notebook: one tab per department or standalone room, each with its own results inside
        if self.depnote is None:
            self.depnote = ttk.Notebook(self.new_main_Frame, style="AL.TNotebook")
            # the whole window, less a margin and the menu, tab and scroll bars
            self.depnote.configure(width=root.winfo_screenwidth() - theme.px(16),
                                   height=root.winfo_screenheight() - theme.px(136))
            self.depnote.grid(row=0, sticky="w")
            self.depnote.bind("<Double-Button-1>", self.rename_tab)
        return self.depnote

    def split_pane(self, parent, left_width, right_width):
        # Inputs on the left and results on the right, with a draggable divider
        panes = ttk.PanedWindow(parent, orient=HORIZONTAL)
        panes.pack(fill=BOTH, expand=1)
        left = ttk.Frame(panes, width=theme.px(left_width))
        right = ttk.Frame(panes, width=theme.px(right_width))
        panes.add(left, weight=3)
        panes.add(right, weight=2)
        return left, right

    def register_tab_name(self, frame, var, default, notebook):
        # The tab (and its linked results tab) always shows the current value of var
        self.tab_names[str(frame)] = var
        results_notebook = self.note_pairs.get(str(notebook))

        def update(*_):
            name = var.get().strip() or default
            for nb, widget, text in ((notebook, frame, name),
                                     (results_notebook, self.tab_links.get(str(frame)), f"Results of {name}")):
                if nb is not None and widget is not None:
                    try:
                        nb.tab(widget, text=text)
                    except tkinter.TclError:  # tab was closed
                        pass

        var.trace_add("write", update)
        update()
        for nb in (notebook, results_notebook):
            if nb is not None:
                nb.bind("<Double-Button-1>", self.rename_tab)

    def rename_tab(self, event):
        # Double-click on a tab to rename it
        notebook = event.widget
        try:
            if notebook.identify(event.x, event.y) in ("", "client"):
                return
            frame = notebook.tabs()[notebook.index(f"@{event.x},{event.y}")]
        except (tkinter.TclError, IndexError):
            return
        var = self.tab_names.get(str(frame)) or self.tab_names.get(str(self.tab_links.get(str(frame))))
        if var is None:
            return
        new_name = simpledialog.askstring("Rename", "New name:", initialvalue=var.get(), parent=self.master)
        if new_name and new_name.strip():
            var.set(new_name.strip())

    def room_name(self, t):
        var = self.d.get(f"vname_room {t}")
        return (var.get().strip() if var is not None else "") or self.d.get(f"room_default {t}", f"Room {t}")

    def link_tabs(self, room_frame, result_frame, room_notebook, results_notebook):
        # Selecting a room tab selects its results tab, and vice versa
        self.tab_links[str(room_frame)] = result_frame
        self.tab_links[str(result_frame)] = room_frame
        self.note_pairs[str(room_notebook)] = results_notebook
        self.note_pairs[str(results_notebook)] = room_notebook
        room_notebook.bind("<<NotebookTabChanged>>", self.sync_tabs)
        results_notebook.bind("<<NotebookTabChanged>>", self.sync_tabs)

    def sync_tabs(self, event):
        other = self.note_pairs.get(str(event.widget))
        if other is None:
            return
        try:
            target = self.tab_links.get(str(event.widget.select()))
            if target is not None and str(other.select()) != str(target):
                other.select(target)
        except tkinter.TclError:  # linked tab was closed
            pass

    def exit_app(self):
        if self.keep_current_work("Exit"):
            root.destroy()

    def open_guide(self, event=None):
        self.open_document("User Guide.pdf")

    def opencpr(self):
        self.open_document("5_NCRP_147_2004.pdf")
    def openbir(self):
        self.open_document(BIR_BOOK)

    def open_document(self, name):
        # The reports are in the project folder (next to Data Shielding.xlsx), wherever the program is started
        path = resource_path(name)
        if not os.path.exists(path):
            messagebox.showerror("Help", f"Cannot find\n{path}", parent=self.master)
        elif hasattr(os, "startfile"):
            os.startfile(path)

# =============
try:
    ensure_example_files()  # the Examples folder with the example projects as files
except OSError:
    pass
app = App(root)
set_app_icon(root)
# A project file given when starting, e.g. a double-click on a .shield file
if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
    root.after(300, lambda: app.open_project_file(os.path.abspath(sys.argv[1])))
root.mainloop()
