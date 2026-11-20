#!/usr/bin/python3
import pathlib
import tkinter as tk
import tkinter.ttk as ttk
import pygubu
from pygubu.api.v1 import register_widget
from pygubu.component.builderobject import PanedWindowBO

from tkinter import messagebox, filedialog, ttk

PROJECT_PATH = pathlib.Path(__file__).parent
PROJECT_UI = PROJECT_PATH / "project.ui"
RESOURCE_PATHS = [PROJECT_PATH]


# Register ttk.PanedWindow (pygubu registers it as lowercase 'w')
class PanedWindowBO_tk(PanedWindowBO):
    class_ = ttk.PanedWindow
    container = True
    container_layout = True

register_widget("ttk.PanedWindow", PanedWindowBO_tk, "ttk.PanedWindow", ("Containers", "ttk"), group=1)


class guiUI:
    def __init__(self, master=None):
        self.builder = pygubu.Builder()
        self.builder.add_resource_paths(RESOURCE_PATHS)
        self.builder.add_from_file(PROJECT_UI)
        if master and isinstance(master, tk.Tk):
            self.mainwindow: tk.Tk = master
        else:
            self.mainwindow: tk.Tk = self.builder.get_object("tk1", master)
        
        # get variables 
        self.cont_var = self.builder.get_variable("cont_var")
        self.hm_var = self.builder.get_variable("hm_var")
        self.lock_var = self.builder.get_variable("lock_var")
        self.trig_var = self.builder.get_variable("trig_var")
        self.fixedz_var = self.builder.get_variable("fixedz_var")
        self.acdc_var = self.builder.get_variable("acdc_var")
                
        # Graph frames (for matplotlib embedding)
        self.graph_left_frame = self.builder.get_object("graph_left_frame")
        self.hist_frame = self.builder.get_object("hist_frame")
        
        # Statistics frame and labels
        self.stats_frame = self.builder.get_object("stats_frame")
        self.stats_min_label = self.builder.get_object("stats_min_label")
        self.stats_max_label = self.builder.get_object("stats_max_label")
        self.stats_avg_label = self.builder.get_object("stats_avg_label")
        self.stats_std_label = self.builder.get_object("stats_std_label")
        self.stats_count_label = self.builder.get_object("stats_count_label")
        
        # Device control widgets
        self.device_combo = self.builder.get_object("device_combo")
        self.status_label = self.builder.get_object("status_label")
        self.start_btn = self.builder.get_object("start_btn")
        self.stop_btn = self.builder.get_object("stop_btn")
        
        # Checkboxes
        self.histogram_checkbox = self.builder.get_object("histogram_checkbox")
        self.lock_checkbox = self.builder.get_object("lock_checkbox")
        self.trigger_checkbox = self.builder.get_object("trigger_checkbox")
        self.fixedz_checkbox = self.builder.get_object("fixedz_checkbox")
        self.cont_saved_checkbox = self.builder.get_object("contsave_checkbox")
        
        # Data Settings tab widgets
        self.interval_entry = self.builder.get_object("interval_entry")
        self.bins_entry = self.builder.get_object("bins_entry")
        self.max_csv_entry = self.builder.get_object("max_csv_entry")
        self.savepath_entry = self.builder.get_object("savepath_entry")
        
        # Settings tab widgets (device parameters)
        self.nrdgs_entry = self.builder.get_object("nrdgs_entry")
        self.digits_entry = self.builder.get_object("digits_entry")
        self.nplc_entry = self.builder.get_object("nplc_entry")
        self.acband_entry = self.builder.get_object("acband_entry")
        
        # Connect Pygubu callbacks 
        self.builder.connect_callbacks(self)


    def run(self):
        self.mainwindow.mainloop()
        
    def callback(self, event=None):
        pass

    def current_pressed(self):
        pass

    def fixedz_checked(self):
        pass

    def frequency_pressed(self):
        pass

    def histogram_checked(self):
        pass

    def acdc_checked(self):
        pass

    def lock_checked(self):
        pass

    def ohm_pressed(self):
        pass

    def ohmf_pressed(self):
        pass

    def trigger_checked(self):
        pass

    def cont_checked(self):
        pass

    def voltage_pressed(self):
        pass

    def nrdgs_pressed(self):
        pass

    def digits_pressed(self):
        pass

    def acal_pressed(self):
        pass

    def nplc_pressed(self):
        pass

    def acband_pressed(self):
        pass

    def connect_device(self):
        pass
    
    def start_measurement(self):
        pass
    
    def stop_measurement(self):
        pass
        
    def _apply_interval(self):
        pass
    
    def _apply_bins(self):
        pass
    
    def _apply_max_csv_points(self):
        pass
    
    def _browse_csv_path(self):
        pass
    
    def _clear_data(self):
        pass
    
    def _reset_canvas(self):
        pass
    
    def _save_data_csv(self):
        pass


if __name__ == "__main__":
    app = guiUI()
    app.run()
