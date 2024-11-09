#!/usr/bin/python3
import pathlib
import tkinter as tk
import pygubu

PROJECT_PATH = pathlib.Path(__file__).parent
PROJECT_UI = PROJECT_PATH / "project.ui"
RESOURCE_PATHS = [PROJECT_PATH]


class guiUI:
    def __init__(self, master=None):
        self.builder = pygubu.Builder()
        self.builder.add_resource_paths(RESOURCE_PATHS)
        self.builder.add_from_file(PROJECT_UI)
        # Main widget
        self.mainwindow: tk.Tk = self.builder.get_object("tk1", master)
        self.builder.connect_callbacks(self)

    def run(self):
        self.mainwindow.mainloop()

    def ac_checked(self):
        pass

    def callback(self, event=None):
        pass

    def histogram_checked(self):
        pass

    def voltage_pressed(self):
        pass

    def current_pressed(self):
        pass

    def resistance_pressed(self):
        pass

    def frequency_pressed(self):
        pass

    def acdci_pressed(self):
        pass

    def acdcv_pressed(self):
        pass

    def resistancefw_pressed(self):
        pass

    def nrdgs_pressed(self):
        pass

    def digits_pressed(self):
        pass

    def nplc_pressed(self):
        pass

    def acband_pressed(self):
        pass

    def lock_pressed(self):
        pass

    def trigger_pressed(self):
        pass

    def safve(self):
        pass

    def max_points_pressed(self):
        pass

    def sampless_pressed(self):
        pass

    def saveas_pressed(self):
        pass


if __name__ == "__main__":
    app = guiUI()
    app.run()
