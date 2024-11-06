import random
import tkinter as Tk
import sys
import os

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

sys.path.append(os.path.abspath("./pygugu"))
from python3 import *
from python3ui import *
class grath: 
    def __init__(self,name,style):
        self.name = name
        self.x_vals = []
        self.y_vals = []
        self.style=style



    def display(i):        
        if self.style == "Historgam":
            pass
        elif self.style == "xyPlot":
            self.x_vals.append(next(index))
            self.y_vals.append(random.randint(0, 5))

        ax1 = plt.gcf().get_axes()
        ax1.cla()
        ax1.plot(self.x_vals, y_vals)


# GUI
root = Tk.Tk()
root.geometry('800x400')
label = Tk.Label(root, text="Measurment setup").grid(column=0, row=0)
plt.style.use('fivethirtyeight')
canvas = FigureCanvasTkAgg(plt.gcf(), master=root)
canvas.get_tk_widget().grid(column=0, row=1)

mg = grath("xy","xyPlot")
ani = FuncAnimation(plt.gcf(), mg.display, interval=1000, blit=False)

Tk.mainloop()