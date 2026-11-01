#!/usr/bin/python3
import pathlib
import tkinter as tk
import tkinter.ttk as ttk
import pygubu
from pygubu.api.v1 import register_widget
from pygubu.component.builderobject import PanedWindowBO

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
        
        # Main container widgets
        self.notebook1 = self.builder.get_object("notebook1")
        self.panedwindow1 = self.builder.get_object("panedwindow1")
        
        # Graph frames (for matplotlib embedding)
        self.graph_left_frame = self.builder.get_object("graph_left_frame")
        self.histogram_pane = self.builder.get_object("histogram_pane")
        
        # Statistics frame and labels
        self.stats_frame = self.builder.get_object("stats_frame")
        self.stats_min_label = self.builder.get_object("stats_min_label")
        self.stats_max_label = self.builder.get_object("stats_max_label")
        self.stats_avg_label = self.builder.get_object("stats_avg_label")
        self.stats_std_label = self.builder.get_object("stats_std_label")
        self.stats_count_label = self.builder.get_object("stats_count_label")
        
        # Device control widgets
        self.device_combo = self.builder.get_object("device_combo")
        self.connect_btn = self.builder.get_object("connect_btn")
        self.status_label = self.builder.get_object("status_label")
        self.start_btn = self.builder.get_object("start_btn")
        self.stop_btn = self.builder.get_object("stop_btn")
        
        # Measurement mode buttons
        self.voltage_dc_button = self.builder.get_object("volt_dc_btn")
        self.voltage_ac_button = self.builder.get_object("volt_ac_btn")
        self.current_dc_button = self.builder.get_object("curr_dc_btn")
        self.current_ac_button = self.builder.get_object("curr_ac_btn")
        self.resistancefw_button = self.builder.get_object("ohmf_btn")
        self.frequency_button = self.builder.get_object("freq_btn")
        self.acdci_button = self.builder.get_object("acdc_btn")
        
        # Checkboxes
        self.histogram_checkbox = self.builder.get_object("histogram_checkbox")
        self.lock_checkbox = self.builder.get_object("lock_checkbox")
        self.trigger_checkbox = self.builder.get_object("trigger_checkbox")
        self.fixedz_checkbox = self.builder.get_object("fixedz_checkbox")
        
        # Data Settings tab widgets
        self.interval_entry = self.builder.get_object("interval_entry")
        self.interval_btn = self.builder.get_object("interval_btn")
        self.bins_entry = self.builder.get_object("bins_entry")
        self.bins_btn = self.builder.get_object("bins_btn")
        self.max_csv_entry = self.builder.get_object("max_csv_entry")
        self.max_csv_btn = self.builder.get_object("max_csv_btn")
        self.savepath_entry = self.builder.get_object("savepath_entry")
        self.browse_btn = self.builder.get_object("browse_btn")
        self.save_csv_btn = self.builder.get_object("save_csv_btn")
        self.clear_btn = self.builder.get_object("clear_btn")
        self.reset_btn = self.builder.get_object("reset_btn")
        
        # Settings tab widgets (device parameters)
        self.nrdgs_entry = self.builder.get_object("nrdgs_entry")
        self.nrdgs_btn = self.builder.get_object("nrdgs_btn")
        self.digits_entry = self.builder.get_object("digits_entry")
        self.digits_btn = self.builder.get_object("digits_btn")
        self.nplc_entry = self.builder.get_object("nplc_entry")
        self.nplc_btn = self.builder.get_object("nplc_btn")
        self.acband_entry = self.builder.get_object("acband_entry")
        self.acband_btn = self.builder.get_object("acband_btn")
        self.gpib_device_entry = self.builder.get_object("gpib_device_entry")
        self.gpib_device_btn = self.builder.get_object("gpib_device_btn")
        self.settings_frame = self.builder.get_object("settings_frame")
        
        # Connect Pygubu callbacks and supplement with manual connections
        self.builder.connect_callbacks(self)
        
        # Supplement manual connections for callbacks not in .ui
        self.connect_btn.config(command=self.connect_device)
        self.start_btn.config(command=self.start_measurement)
        self.stop_btn.config(command=self.stop_measurement)
        self.interval_btn.config(command=self._apply_interval)
        self.bins_btn.config(command=self._apply_bins)
        self.browse_btn.config(command=self._browse_csv_path)
        self.max_csv_btn.config(command=self._apply_max_csv_points)
        self.save_csv_btn.config(command=self._save_data_csv)
        self.clear_btn.config(command=self._clear_data)
        self.reset_btn.config(command=self._reset_canvas)
        self.device_combo.bind('<<ComboboxSelected>>', self.device_combo_selected)
        self.voltage_dc_button.config(command=self.volt_dc_pressed)
        self.voltage_ac_button.config(command=self.volt_ac_pressed)
        self.current_dc_button.config(command=self.curr_dc_pressed)
        self.current_ac_button.config(command=self.curr_ac_pressed)
        self.resistance_button = self.builder.get_object("ohm_btn")
        self.resistance_button.config(command=self.resistance_pressed)
        self.resistancefw_button.config(command=self.resistancefw_pressed)
        self.frequency_button.config(command=self.frequency_pressed)
        self.acdci_button.config(command=self.acdci_pressed)
        self.histogram_checkbox.config(command=self.histogram_checked)
        self.lock_checkbox.config(command=self.lock_checked)
        self.trigger_checkbox.config(command=self.trigger_checked)
        self.fixedz_checkbox.config(command=self.fixedz_checked)
        self.nrdgs_btn.config(command=self.nrdgs_pressed)
        self.digits_btn.config(command=self.digits_pressed)
        self.nplc_btn.config(command=self.nplc_pressed)
        self.acband_btn.config(command=self.acband_pressed)
        self.gpib_device_entry.config(state='normal')
        self.gpib_device_btn.config(command=self.gpib_device_pressed)

    def run(self):
        self.mainwindow.mainloop()
        
    # Placeholder callback methods - to be overridden by main.py
    def ac_checked(self):
        pass

    def acdci_pressed(self):
        pass

    def callback(self, event=None):
        pass

    def current_pressed(self):
        pass

    def fixedge_checked(self):
        pass

    def fixedz_checked(self):
        pass

    def frequency_pressed(self):
        pass

    def histogram_checked(self):
        pass

    def lock_checked(self):
        pass

    def resistance_pressed(self):
        pass

    def resistancefw_pressed(self):
        pass

    def trigger_checked(self):
        pass

    def voltage_pressed(self):
        pass

    def nrdgs_pressed(self):
        pass

    def digits_pressed(self):
        pass

    def nplc_pressed(self):
        pass

    def acband_pressed(self):
        pass

    def gpib_addr_pressed(self):
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
