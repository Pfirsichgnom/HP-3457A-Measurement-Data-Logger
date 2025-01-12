import random
import tkinter as tk
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
sys.path.append('./pygubu')
from python3ui import guiUI
from gpib import *
import threading

import time

class gui(guiUI): 
    def __init__(self, master=None):
        super().__init__(master)
        self.fig = plt.Figure(figsize=(10, 5), dpi=70)
        self.ax = self.fig.add_subplot(111)
        self.line, = self.ax.plot([], [])
        self.name = "name"
        self.x_vals = [1]
        self.y_vals = [1]
        self.style="xyPlot"

        self.x=0
        self.y=0

    def change_canvas(self):
       
        fcontainer = self.builder.get_object('canvas1')
        self.canvas = FigureCanvasTkAgg(self.fig, master=fcontainer)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side='top', fill='both', expand=True)
        #self.ani = FuncAnimation(self.fig, self.display, 1, interval=1000, blit=False)  
        


    def start_animation(self):        
        self.ani = FuncAnimation(self.fig, self.display,1, interval=1000, blit=False)
    
    def display(self,i):      
        if self.style == "Historgam":
            pass
        elif self.style == "xyPlot":
            self.x_vals.append(self.x_vals[-1]+1)
            self.y_vals.append(self.y_vals[-1]+1)
            #self.x_vals.append()
            #self.y_vals.append(random.randint(0, 5))
        print("a")
        
        #self.axes.plot(self.x, self.y)

        #fig, ax = plt.subplots()
        #ax.plot(x, y)
        self.ax.set_xlim(min(self.x_vals), max(self.x_vals))
        self.ax.set_ylim(min(self.y_vals), max(self.y_vals))
        self.line.set_xdata(self.x_vals)
        self.line.set_ydata(self.y_vals)
    


# GUI
app = gui()
app.change_canvas()
app.start_animation()
app.run()
