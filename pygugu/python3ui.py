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

    def fw_checked(self, widget_id):
        pass

    def callback(self, event=None):
        pass

    def ac_checked(self, widget_id):
        print(self.builder.objects['ac_checkbox'])

    def hist_checked(self, widget_id):
        pass


if __name__ == "__main__":
    app = guiUI()
    app.run()
