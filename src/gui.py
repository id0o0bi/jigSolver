from tkinter import *
from tkinter import ttk

class App(Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.pack()
        ttk.Label(self, text="Hello World!").grid(column=0, row=0)
        ttk.Button(self, text="Quit", command=self.destroy).grid(column=1, row=0)

# app = App()
# root = Tk()
# frm = ttk.Frame(root, padding=10)
# frm.grid()

root = Tk()
app = App(root)
app.master.title("jigSolver 0.1")
app.mainloop()

# root.super.__init__()
app.mainloop()