import tkinter
import PyPDF2
import os
from tkinter import *
from tkinter import ttk
from tkinter import font
from Department import ddepartment
from Depcalculations import departprimsec
from QuickCalculations import dqprimsec
from Quickcal import dquick
from Department_defs import dep_defs
from Room import droom
from CTroom import CT_Room


root = Tk()
font.families()
pat = 0
pat2 = 0
pat3 = 0
r2 = 0
root.title("Shielding of X-ray Rooms")
root.iconphoto(False, PhotoImage(file='715518-200.png'))
root.state('zoomed')
root.configure(background="#2c3b47")
style = ttk.Style()
style.configure(root, background="#f7faf9")



class App(ddepartment,dep_defs,departprimsec,dqprimsec,dquick,droom,CT_Room):

    def __init__(self, master):
        # ============Menu Bar==================
        main_menubar = Menu(root)
        root.configure(menu=main_menubar)
        #==========αρχικοποίηση παραθύρων=======
        self.depnote=None
        self.resnote=None
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
        #self.newoptions.add_command(label="Design Barrier", command=self.quickcal)

        """self.file_menu.add_command(label="Open", )
        self.file_menu.add_command(label="Save as...", )"""
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=root.quit)
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
        self.help_menu.add_command(label= "NCRP Report No. 147", command=self.opencpr)
        self.help_menu.add_command(label="BIR 2012", command=self.openbir)

        self.i=0
        self.ep = 1 #for barrier position
        self.d = {}
        self.res = {}
        self.thm = {}
        self.xlmat ={}
        self.barn={}
        self.barr={}
        self.wa={}
        self.col={}

        #=====Main window scrollbar=========
        self.master = master

        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill=BOTH, expand=1)
        # ======scrollbar=========
        self.main_canvas = Canvas(self.main_frame)

        self.main_scrollbar = ttk.Scrollbar(self.main_frame, orient=HORIZONTAL, command=self.main_canvas.xview)
        self.main_scrollbar.pack(side=BOTTOM, fill=X)
        self.main_canvas.configure(xscrollcommand=self.main_scrollbar.set, bg="#2c3b47")
        self.main_canvas.pack(side=LEFT, fill=BOTH, expand=1)
        # =========New tab===========================
        self.new_main_Frame = ttk.Frame(self.main_canvas, style="ML.TFrame")
        self.new_main_Frame.bind('<Configure>', lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")))
        self.main_canvas.create_window((0, 0), window=self.new_main_Frame, anchor="c")

        # ===========Buttons========
        self.chooseCal=ttk.Label(master=self.new_main_Frame,text="Design", style="CL.TLabel" )
        self.depbutton = ttk.Button(master=self.new_main_Frame, style="AL.TButton", text="Department", command=self.creatdep)
        self.roombutton = ttk.Button(master=self.new_main_Frame,style="AL.TButton", text="X-Ray Room", command=self.creatroom)
        self.CTbutton = ttk.Button(master=self.new_main_Frame, style="AL.TButton", text="CT Room",
                                     command=self.creatCTroom)
        #self.quickbutton = ttk.Button(master=self.new_main_Frame,style="AL.TButton", text="Barrier",
                                      #command=self.quickcal)

        self.chooseCal.pack(anchor="c", pady=10, padx=700)
        self.depbutton.pack(anchor="c", pady=10, padx=700)
        self.roombutton.pack(anchor="c", pady=10, padx=700)
        self.CTbutton.pack(anchor="c", pady=10, padx=700)
        #self.quickbutton.pack(anchor="c", pady=10, padx=700)


        # ====================Styles=============================================
        self.style = ttk.Style()
        self.style.configure("TButton", background="#f7faf9", foreground='#171a24', font="calibri 12")
        self.style.configure("AL.TButton", background="#2c3b47", foreground='#171a24', font="calibri 13")
        self.style.configure("TFrame", background="#f7faf9", foreground="#f7faf9")
        self.style.configure("ML.TFrame", background="#2c3b47", foreground="#171719")
        self.style.configure("AL.TNotebook", background="#2c3b47", foreground="#f7faf9")
        self.style.configure("BL.TNotebook", background="#f7faf9", foreground="#f7faf9")
        #======Label styles==========
        self.style.configure("BL.TLabel", background="#f7faf9", foreground='#171719', font='Helvetica 14',
                             weight='bold')
        self.style.configure("CL.TLabel", background="#2c3b47", foreground='#f6f8f8', font='Helvetica 14',
                             weight='bold')
        self.style.configure("AL.TLabel", background="#f7faf9", foreground='#171719', font='Helvetica 12')
        self.style.configure("BL2.TLabel", background="#f7faf9", foreground='#171719', font=('Helvetica', 12, 'bold'))
        self.style.configure("RL.TLabel", background="#f7faf9", foreground='#f71616', font='Helvetica 12')

        self.style.configure("TLabel", background="#f7faf9", foreground='#171719', font='Helvetica 12')

        self.style.configure("TRadiobutton", background="#f7faf9", foreground='#171719', font='Helvetica 11')
        self.style.configure("TCheckbutton", background="#f7faf9", foreground='#171719', font='Helvetica 11')
        self.style.configure("TSpinbox", background="#f7faf9", foreground='#000000', font='Helvetica 11')
        self.style.configure("TCombobox", background="#f7faf9", foreground='#000000', font='Helvetica 11')
        self.style.configure("TMenubutton", background="#ffffff", foreground='#000000', font='Helvetica 9')
        self.style.configure("TScrollbar", background="#f7faf9", foreground="#f7faf9")

    def opencpr(self):
        self.path= "5_NCRP_147_2004.pdf"
        os.system(self.path)
    def openbir(self):
        self.path= "book.9780905749747.pdf"
        os.system(self.path)

# =============
app = App(root)
root.mainloop()
