#!/usr/bin/python3
import pathlib
import tkinter as tk
import pygubu
from python3ui import guiUI


class gui(guiUI):
    def __init__(self, master=None):
        super().__init__(master)


if __name__ == "__main__":
    app = gui()
    app.run()
