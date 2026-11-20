#!/usr/bin/python3
import tkinter as tk
import pygubu
import sys
import os
import time
import threading
import queue
import csv
from datetime import datetime
from collections import deque

from guiUI import guiUI
from GPIBInterface import print_debug
from SettingsManager import SettingsManager
from MeasurementData import MeasurementData
from MeasurementStats import MeasurementStats


import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from tkinter import messagebox, filedialog, ttk

from GPIBInterface import GPIBInterface, DEBUG, print_debug


class gui(guiUI):
    def __init__(self, master=None):
        self.settings_manager = SettingsManager()
        
        super().__init__(master)
        
        self.data_storage = MeasurementData(max_points=10000)
        self.stats = MeasurementStats()
        self.gpib_inst_instance = GPIBInterface()

        self.selected_device = None
        self.measurement_unit = ""
        self.running = False
        self.measurement_thread = None
        self.measurement_interval = 1.0
        self.save_path = ""
        self.max_csv_points = 0
        self.histogram_bins = 50
        self._pending_ui = queue.Queue()
        self._connect_lock = threading.Lock()
        self._connect_in_progress = False
        self._connecting_device = None
        
        self.fig = None
        self.ax = None
        self.line = None
        self.histogram_fig = None
        self.histogram_ax = None

        self.consave=0  
        self.filename = ""
        
        self._init_gui_elements()
        self.svd=False
        print_debug("[GPIB] Startup complete")
    
    def _init_gui_elements(self):
        """Initialize GUI elements by embedding matplotlib charts."""
        try:
            settings = self.settings_manager.load_settings()
            try:
                self.measurement_interval = float(settings.get('measurement_interval', '1.0'))
                self.interval_entry.delete(0, 'end')
                self.interval_entry.insert(0, f"{self.measurement_interval}")
            except:
                pass
            
            try:
                self.histogram_bins = int(settings.get('histogram_bins', '50'))
                self.bins_entry.delete(0, 'end')
                self.bins_entry.insert(0, str(self.histogram_bins))
            except:
                pass
            
            try:
                self.max_csv_points = int(settings.get('max_csv_points', '0'))
                self.max_csv_entry.delete(0, 'end')
                self.max_csv_entry.insert(0, str(self.max_csv_points))
                self._set_data_cap(self.max_csv_points)
            except:
                pass
            
            if settings.get('save_path', ''):
                self.save_path = settings.get('save_path', '')
                self.savepath_entry.delete(0, 'end')
                self.savepath_entry.insert(0, self.save_path)

            if int(settings.get('cont_save', '0')):
                self.consave=int(settings.get('cont_save', '0'))
                self.cont_var.set(int(settings.get('cont_save', '0')))
            
            if int(settings.get('lock_state', '0')):              
                self.lock_var.set(int(settings.get('lock_state', '0')))
            
            if int(settings.get('trigger_state', '0')):              
                self.trigger_var.set(int(settings.get('trigger_state', '0')))

            if int(settings.get('fixedz_state', '0')):              
                self.fixedz_var.set(int(settings.get('fixedz_state', '0')))
            
            if int(settings.get('acdc_state', '0')):              
                self.acdc_var.set(int(settings.get('acdc_state', '0')))            


            self.mainwindow.geometry("")

            self.fig = Figure(figsize=(8, 4), dpi=80)
            self.ax = self.fig.add_subplot(111)
            self.line, = self.ax.plot([], [])
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_left_frame)
            self.canvas.get_tk_widget().pack(fill='both', expand=True)
            
            self.ax.set_xlabel('Measurement Index')
            self.ax.set_ylabel('Value')
            self.ax.set_title('Live Measurement')
            self.ax.grid(True)
            
            self._hist_spacer = ttk.Frame(self.hist_frame)
            self._hist_spacer.pack(side='top', fill='both')

            self.histogram_fig = Figure(figsize=(4, 8), dpi=80)
            self.histogram_ax = self.histogram_fig.add_subplot(111)
            self.hist_canvas = FigureCanvasTkAgg(self.histogram_fig, master=self.hist_frame )
            self.hist_canvas.get_tk_widget().pack(fill='both', expand=True)
            

            self.histogram_ax.set_xlabel('Value')
            self.histogram_ax.set_ylabel('Frequency')
            self.histogram_ax.set_title('Measurement Distribution')
            self.histogram_ax.grid(True)
            

            if int(settings.get('show_histogram', '0')):              
                self.hm_var.set(int(settings.get('show_histogram', '0')))
            else:
                self.hist_frame.pack_forget()

            self.mainwindow.geometry("1200x800")

            device_list = self.gpib_inst_instance.get_devices()
            self._setup_device_combo(device_list)            
                
        except Exception as e:
            print_debug(f"[GUI] Error creating GUI elements: {e}")

    def _setup_device_combo(self, devices):
        if not devices:
            return
        self.device_combo['values'] = devices
        if not self.selected_device:
            self.selected_device = devices[0]
        self.device_combo.set(self.selected_device)
        try:
            longest = max(len(str(d)) for d in devices)
            self.device_combo.config(width=max(20, longest + 2))
        except Exception:
            pass
    
    def _start_connect(self, device):
        """Start connecting to a device on a worker thread (non-blocking UI)."""
        with self._connect_lock:
            if self._connect_in_progress:                
                print_debug(f"[CONNECT] Already connecting to {self._connecting_device}")
                return
            self._connect_in_progress = True
            self._connecting_device = device
        threading.Thread(target=self._do_connect, args=(device,), daemon=True).start()

    def _do_connect(self, device):
        """Worker-thread part of the connection: GPIB I/O only (no Tk calls)."""
        try:
            try:
                self.gpib_inst_instance.select_devices(device)
                self.gpib_inst_instance.PRESET()
            except Exception as e:
                print_debug(f"[CONNECT] Failed to connect to {device}: {e}")
                self._pending_ui.put(("connect_failed", device, str(e)))
                return

            # Read back the device settings (GPIB I/O, worker thread)
            values = self._query_device_settings()
            self.settings_manager.save_settings(device)

            print_debug(f"[CONNECT] Connected: {device}")
            self._pending_ui.put(("connected", device, values))
        finally:
            with self._connect_lock:
                self._connect_in_progress = False
                self._connecting_device = None

    def _query_device_settings(self):
        """Query device settings and return values for the UI (worker thread)."""
        values = {'nrdgs': "1", 'digits': "6", 'nplc': "1", 'acband': "200"}

        try:
            nrdgs_val = self.gpib_inst_instance.NRDGSQ()
            if nrdgs_val:
                values['nrdgs'] = str(int(float(nrdgs_val)))
        except Exception as e:
            print_debug(f"[INIT] NRDGS query failed: {e}")

        try:
            nplc_val = self.gpib_inst_instance.NPLCQ()
            if nplc_val:
                values['nplc'] = str(float(nplc_val))
        except Exception as e:
            print_debug(f"[INIT] NPLC query failed: {e}")

        try:
            acband_val = self.gpib_inst_instance.ACBANDQ()
            if acband_val:
                acband_int = int(float(acband_val))
                values['acband'] = str(acband_int)
                self.gpib_inst_instance.ACBAND(acband_int)
            else:
                self.gpib_inst_instance.ACBAND(200)
        except Exception as e:
            print_debug(f"[INIT] ACBAND query failed: {e}")
            self.gpib_inst_instance.ACBAND(200)

        try:
            settings = self.settings_manager.load_settings()
            self.gpib_inst_instance.NPLC(float(settings.get('nplc', '1')))
        except Exception:
            pass

        return values

    def _apply_device_settings(self, values):
        """Fill settings entries with queried values (main thread)."""
        def _fill(entry, text):
            entry.delete(0, 'end')
            entry.insert(0, text)

        _fill(self.nrdgs_entry, values.get('nrdgs', '1'))
        _fill(self.digits_entry, values.get('digits', '6'))
        _fill(self.nplc_entry, values.get('nplc', '1'))
        _fill(self.acband_entry, values.get('acband', '200'))

    def _handle_connect_events(self):
        """Process connection events posted from worker threads (main thread)."""
        while True:
            try:
                event = self._pending_ui.get_nowait()
            except queue.Empty:
                return
            try:
                kind = event[0]
                if kind == 'connected':
                    device, values = event[1], event[2]
                    self.selected_device = device
                    self._apply_device_settings(values)
                    self.device_combo.set(device)
                    self._update_connection_status(True)
                    messagebox.showinfo("Connected", f"Connected to {device}")
                elif kind == 'connect_failed':
                    device, err = event[1], event[2]
                    self._update_connection_status(False)
                    messagebox.showerror("Connection Error",
                                         f"Failed to connect to {device}: {err}")
                elif kind == 'conn_lost':
                    self._update_connection_status(False)
            except Exception as e:
                print_debug(f"[CONNECT] Event handling error: {e}")
    
    def _apply_interval(self):
        """Apply new measurement interval."""
        try:
            interval = float(self.interval_entry.get())
            if interval <= 0:
                messagebox.showwarning("Invalid Value", "Interval must be greater than 0")
                return
            
            self.measurement_interval = interval
            
            settings = self.settings_manager.load_settings()
            settings['measurement_interval'] = str(interval)
            self.settings_manager.save_all_settings(settings)
            
            print_debug(f"[INTERVAL] New interval: {interval}s")
                
        except ValueError:
            messagebox.showerror("Invalid Value", "Interval must be a positive number")
    
    def _apply_bins(self):
        """Apply new histogram bin count."""
        try:
            bins = int(self.bins_entry.get())
            if bins <= 0:
                messagebox.showwarning("Invalid Value", "Bins must be a positive integer")
                return
            
            self.histogram_bins = bins
            self._update_histogram()
            
            settings = self.settings_manager.load_settings()
            settings['histogram_bins'] = str(bins)
            self.settings_manager.save_all_settings(settings)
            
        except ValueError:
            messagebox.showerror("Invalid Value", "Bins must be a positive integer")
    
    def _apply_max_csv_points(self):
        """Apply max CSV points setting."""
        try:
            max_points = int(self.max_csv_entry.get())
            if max_points < 0:
                messagebox.showwarning("Invalid Value", "Max points must be non-negative")
                return
            
            self.max_csv_points = max_points
            self._set_data_cap(max_points)

            settings = self.settings_manager.load_settings()
            settings['max_csv_points'] = str(max_points)
            self.settings_manager.save_all_settings(settings)
            
        except ValueError:
            messagebox.showerror("Invalid Value", "Max points must be a non-negative integer")
    
    def _browse_csv_path(self):
        """Browse for CSV save directory."""
        path = filedialog.askdirectory()
        if path:
            self.save_path = path
            self.savepath_entry.delete(0, 'end')
            self.savepath_entry.insert(0, path)
            
            settings = self.settings_manager.load_settings()
            settings['save_path'] = path
            self.settings_manager.save_all_settings(settings)
    
    def _reset_measurement_data(self):
        """Clear stored samples, statistics and both charts (main thread)."""
        self.data_storage.clear()
        self.stats.clear()
        self._update_stats_display()
        self._update_graph()
        self._update_histogram()

    def _clear_data(self):
        """Clear all measurement data."""
        self._reset_measurement_data()
    
    def _reset_canvas(self):
        """Reset canvas with confirmation."""
        result = messagebox.askyesno("Reset Canvas", "Are you sure you want to reset the canvas?")
        if result:
            self._clear_data()

            settings = self.settings_manager.load_settings()
            if int(settings['histogram_bins']) >0 :

                self.histogram_bins = int(settings['histogram_bins']) 
            else:
                self.histogram_bins = 50
                settings['histogram_bins'] = '50'
                self.settings_manager.save_all_settings(settings)

            self.bins_entry.delete(0, 'end')
            self.bins_entry.insert(0, settings['histogram_bins'])
            self._update_histogram()

    def cont_save_data_csv(self,timestamp,value):
        if self.consave==1 and self.svd is True:
            if self.filename:
                if os.path.isfile(self.filename):                    
                    try:
                        with open(self.filename, "rb") as f:
                            num_lines = sum(1 for _ in f)
                        if(num_lines<self.max_csv_points) or self.max_csv_points==0:
                            with open(self.filename, 'a+', newline='') as f:
                                writer = csv.writer(f)
                                writer.writerow([
                                    datetime.fromtimestamp(timestamp).isoformat(),
                                    int(timestamp * 1e9),
                                    value,
                                ])    
                        
                    except Exception as e:
                        debug_print("CSV Save error")
                        return

    def _save_data_csv(self):
        path = self.savepath_entry.get().strip()
        if not path:
            path = filedialog.askdirectory()
            if not path:
                messagebox.showwarning("No Path", "Please select a save directory first")
                return
        
        try:
            if path.lower().endswith(".csv"):
                # A specific output file was given (e.g. 'test.csv');
                # write to it directly. Its parent directory must exist.
                directory = os.path.dirname(path) or "."
                if not os.path.isdir(directory):
                    messagebox.showerror(
                        "Invalid Path",
                        f"Directory for file does not exist: {directory}")
                    return
                self.filename = path
            else:
                # Otherwise treat the path as a directory and write a
                # timestamped file inside it.
                if not os.path.isdir(path):
                    messagebox.showerror("Invalid Path", f"Directory does not exist: {path}")
                    return
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.filename = os.path.join(path, f"measurements_{timestamp}.csv")
        except Exception as e:
            messagebox.showerror("Error", f"Invalid path: {e}")
            return
        
        # data_storage holds (timestamp, value) pairs captured when each
        # sample was actually measured
        timestamps, samples = self.data_storage.get_timestamped()
        if not samples:
            messagebox.showinfo("Info", "No measurement data to save")
            return

        try:
            if self.max_csv_points > 0:
                samples = samples[-self.max_csv_points:]
                timestamps = timestamps[-self.max_csv_points:]

            with open(self.filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Timestamp_ns', 'Value'])

                for ts, value in zip(timestamps, samples):
                    writer.writerow([
                        datetime.fromtimestamp(ts).isoformat(),
                        int(ts * 1e9),
                        value,
                    ])

            messagebox.showinfo("Success", f"Data saved to: {self.filename}")
            self.svd=True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
    
    def device_combo_selected(self, event=None):
        """Handle device selection change."""
        try:
            device = self.device_combo.get().strip()
            if device:
                self.selected_device = device
        except Exception as e:
            print_debug(f"[DEVICE_SELECT] Error: {e}")
    
    def connect_device(self):
        """Connect to selected device (non-blocking)."""
        device = self.device_combo.get().strip()
        if not device:
            messagebox.showwarning("No Device", "Please select a device")
            return

        self._start_connect(device)

    def _update_connection_status(self, connected):
        """Update connection status display (main thread)."""
        if connected:
            self.status_label.config(text="Status: Connected", foreground='green')
        else:
            self.status_label.config(text="Status: Disconnected", foreground='red')
        self._sync_button_states()

    def _sync_button_states(self):
        """
        Keep Start/Stop button states consistent everywhere:
          - not connected           -> both disabled (matching .ui initial state)
          - connected, not running  -> Start enabled, Stop disabled
          - running                 -> Start disabled, Stop enabled
        """
        running = (self.measurement_thread is not None
                   and self.measurement_thread.is_alive())
        connected = self.gpib_inst_instance.is_connected()
        if running:
            start, stop = 'disabled', 'normal'
        elif connected:
            start, stop = 'normal', 'disabled'
        else:
            start, stop = 'disabled', 'disabled'
        self.start_btn.config(state=start)
        self.stop_btn.config(state=stop)

    def _set_data_cap(self, max_csv_points):
        """Limit how long the data buffer keeps samples (min. 10000)."""
        self.data_storage._max_points = max(10000, int(max_csv_points) if max_csv_points > 0 else 0)

    def start_measurement(self):
        """Start measurement thread; initiates the connection first if needed."""
        if self.running:
            return

        if not self.gpib_inst_instance.is_connected():
            device = self.device_combo.get().strip() or self.selected_device or ""
            if device:
                self.selected_device = device
                self._start_connect(device)
                print_debug(f"[MEAS] Starting measurement; connecting to {device}")

            print_debug("[MEAS] Starting measurement; no device selected")

        print_debug("[MEAS] Starting measurement thread")

        self._reset_measurement_data()

        self.running = True
        self.measurement_thread = threading.Thread(target=self.measure_loop, daemon=True)
        self.measurement_thread.start()
        self._sync_button_states()

    def stop_measurement(self):
        """Stop measurement thread."""
        self.running = False
        if self.measurement_thread:
            self.measurement_thread.join(timeout=6)
            self.measurement_thread = None
        self._sync_button_states()
    
    def measure_loop(self):
        """Measurement thread main loop."""
        print_debug("Measurement thread started")
        last_unit = None
        last_time = 0
        conn_lost_reported = False

        while self.running:
            try:
                
                interval = self.measurement_interval

                while (time.time() - last_time) < interval:
                    time.sleep(0.001)
                    continue

                if not self.gpib_inst_instance.is_connected():
                    print_debug("Device not connected")
                    if not conn_lost_reported:
                        self._pending_ui.put_nowait(("conn_lost",))
                        conn_lost_reported = True
                    continue
                conn_lost_reported = False
                
                if self.measurement_unit and self.measurement_unit != last_unit:
                    try:
                        self._set_measurement_mode(self.measurement_unit)
                        last_unit = self.measurement_unit
                    except Exception as e:
                        print_debug(f"Error setting mode: {e}")
                        continue
                
                try:
                    result = self._read_measurement()

                    if result is not None:
                        val = float(result)
                        timestamp = time.time()
                        self.data_storage.add_measurement(timestamp, val)
                        self.stats.add_sample(val)
                        last_time = time.time()
                        self.cont_save_data_csv(timestamp, val)

                except Exception as e:
                    print_debug(f"Read error: {e}")
                
            except Exception as e:
                print_debug(f"Loop error: {e}")
            
    
    def _set_measurement_mode(self, mode):
        """Set measurement mode on device."""
        if mode == "DCV":
            self.gpib_inst_instance.DCV(0)
        elif mode == "ACV":
            self.gpib_inst_instance.ACV(0)
        elif mode == "ACDCV":
            self.gpib_inst_instance.ACDCV(0)
        elif mode == "DCI":
            self.gpib_inst_instance.DCI(0)
        elif mode == "ACI":
                self.gpib_inst_instance.ACI(0)
        elif mode == "ACDCI":
            self.gpib_inst_instance.ACDCI(0)
        elif mode == "OHM":
            self.gpib_inst_instance.OHM(0)
        elif mode == "FREQ":
            self.gpib_inst_instance.FREQ(0)
        elif mode == "OHMF":
            self.gpib_inst_instance.OHMF(0)
    
    def _read_measurement(self):
        try:
            result = self.gpib_inst_instance._query("TRIG SYN")
            return result
        except Exception as e:
            print_debug(f"Read error: {e}")
            return None
    
    def _update_graph(self):
        """Update main measurement graph from stored data."""
        if self.fig is None:
            return
        try:
            x_vals, y_vals = self.data_storage.get_data()
            
            if x_vals and y_vals:
                self.ax.set_xlim(max(0, x_vals[-1] - 100), x_vals[-1] + 10)
                
                y_range = max(y_vals) - min(y_vals)
                if y_range > 0:
                    self.ax.set_ylim(min(y_vals) - 0.1 * y_range, max(y_vals) + 0.1 * y_range)
                else:
                    self.ax.set_ylim(min(y_vals) - 1, max(y_vals) + 1)
                
                self.line.set_xdata(x_vals)
                self.line.set_ydata(y_vals)
            else:
                # No samples (e.g. after a reset): show an empty chart
                # instead of keeping the stale trace.
                self.ax.cla()
                self.ax.set_xlabel('Measurement Index')
                self.ax.set_ylabel('Value')
                self.ax.set_title('Live Measurement')
                self.ax.grid(True)
                self.line, = self.ax.plot([], [])
                
            self.canvas.draw()
        except Exception as e:
            print_debug(f"[GRAPH] Update error: {e}")
    
    def _update_histogram(self):
        """Update histogram display."""

        if self.histogram_ax is None:
            return        
        try:
            samples = self.stats.get_samples()
            if len(samples) < 2:
                self.histogram_ax.cla()
                self.histogram_ax.set_xlabel('Value')
                self.histogram_ax.set_ylabel('Frequency')
                self.histogram_ax.grid(True)
                self.hist_canvas.draw()
                return
            
            self.histogram_ax.cla()
            self.histogram_ax.hist(samples, bins=self.histogram_bins)
            self.histogram_ax.set_xlabel('Value')
            self.histogram_ax.set_ylabel('Frequency')
            self.histogram_ax.set_title(f'Measurement Distribution ({self.histogram_bins} bins)')
            self.histogram_ax.grid(True)
            
            self.hist_canvas.draw()
        except Exception as e:
            print_debug(f"[HISTOGRAM] Update error: {e}")
    
    def _update_stats_display(self):
        """Update statistics labels."""
        stats = self.stats.get_stats()
        
        self.stats_count_label.config(text=f"Samples: {stats['count']}")
        
        if stats['min'] is not None:
            self.stats_min_label.config(text=f"Min: {stats['min']:.6g}")
            self.stats_max_label.config(text=f"Max: {stats['max']:.6g}")
            self.stats_avg_label.config(text=f"Avg: {stats['avg']:.6g}")
            self.stats_std_label.config(text=f"Std Dev: {stats['std']:.6g}")
        else:
            self.stats_min_label.config(text="Min: --")
            self.stats_max_label.config(text="Max: --")
            self.stats_avg_label.config(text="Avg: --")
            self.stats_std_label.config(text="Std Dev: --")


    def volt_dc_pressed(self):
        """Handle VDC button."""
        self._set_measurement_mode_and_start("DCV")

    def volt_ac_pressed(self):
        """Handle VAC button."""
        if  self.acdc_var.get()==1:
            self._set_measurement_mode_and_start("ACDCV")
        else:
            self._set_measurement_mode_and_start("ACV")

    def curr_dc_pressed(self):
        """Handle Idc button."""
        self._set_measurement_mode_and_start("DCI")

    def curr_ac_pressed(self):
        """Handle IAC button."""
        if  self.acdc_var.get()==1:
            self._set_measurement_mode_and_start("ACDCI")
        else:
            self._set_measurement_mode_and_start("ACI")
    
    def ohm_pressed(self):
            self._set_measurement_mode_and_start("OHM")
        
    def ohmf_pressed(self):
        self._set_measurement_mode_and_start("OHMF")          
    
    def acdc_checked(self):
        settings = self.settings_manager.load_settings()
        settings['acdc_state'] = str(int(self.acdc_var.get())) 
        self.settings_manager.save_all_settings(settings)

    def freq_pressed(self):
        self._set_measurement_mode_and_start("FREQ")
    
    def _set_measurement_mode_and_start(self, mode):
        if self.measurement_unit != mode:
            old_mode = self.measurement_unit or "(none)"
            self.measurement_unit = mode
            print_debug(f"[MODE] Function changed: {old_mode} -> {mode}, resetting data and charts")
            self._reset_measurement_data()

        if not self.running:
            self.start_measurement()
    
    def lock_checked(self):
        """Handle Lock checkbox toggle - send LOCK command to device."""
        try:
            if self.gpib_inst_instance and self.gpib_inst_instance.is_connected():
                if self.lock_checkbox.instate(['selected']):
                    self.gpib_inst_instance.LOCK(1)
                else:
                    self.gpib_inst_instance.LOCK(0)
        except Exception as e:
            print_debug(f"[LOCK] Error: {e}")
    
    def cont_checked(self):
            """Handle continuous_save checkbox toggle """
            try:                
                if self.cont_saved_checkbox.instate(['selected']):
                    self.consave=1             
                else:
                    self.consave=0

                settings = self.settings_manager.load_settings()
                settings['cont_save']=str(self.consave)
                self.settings_manager.save_all_settings(settings)
            except Exception as e:
                print_debug(f"[continuous_save] Error: {e}")
    
    def trigger_checked(self):
        """Handle Trigger checkbox toggle - sends TGR to device."""
        try:
            if self.gpib_inst_instance and self.gpib_inst_instance.is_connected():
                if self.trigger_checkbox.instate(['selected']):
                    self.gpib_inst_instance.TGR(1)
                else:
                    self.gpib_inst_instance.TGR(0)
        except Exception as e:
            print_debug(f"[TRIGGER] Error: {e}")
    
    def fixedz_checked(self):
        """Handle FixedZ checkbox toggle - sends FIXEDZ command to device."""
        try:
            if self.gpib_inst_instance and self.gpib_inst_instance.is_connected():
                if self.fixedz_checkbox.instate(['selected']):
                    self.gpib_inst_instance.FIXEDZ(1)
                else:
                    self.gpib_inst_instance.FIXEDZ(0)
        except Exception as e:
            print_debug(f"[FIXEDZ] Error: {e}")
    
    def histogram_checked(self):
        try:
            if self.histogram_checkbox.instate(['selected']):
                self.hist_frame.pack_forget()
                self.hist_frame.pack(
                    side='right', fill='both', expand=False,
                    before=self.graph_left_frame
                )
                self.hist_frame.update_idletasks()
                self._update_histogram()
            else:
                self.hist_frame.pack_forget()
        except Exception as e:
            print_debug(f"[HISTOGRAM] Error: {e}")
    
    def nrdgs_pressed(self):
        """Handle NRDGS button."""
        try:
            val = int(self.nrdgs_entry.get())
            if self.gpib_inst_instance and self.gpib_inst_instance.is_connected():
                self.gpib_inst_instance.NRDGS(val)
        except:
            pass
    
    def digits_pressed(self):
        """Handle Digits button."""
        try:
            val = float(self.digits_entry.get())
            if self.gpib_inst_instance and self.gpib_inst_instance.is_connected():
                self.gpib_inst_instance.NDIG(val)
        except:
            pass
    
    def nplc_pressed(self):
        """Handle NPLC button."""
        try:
            val = float(self.nplc_entry.get())
            self.measurement_interval = val
            if self.gpib_inst_instance and self.gpib_inst_instance.is_connected():
                self.gpib_inst_instance.NPLC(val)
        except:
            pass
    
    def acband_pressed(self):
        """Handle ACBAND button."""
        try:
            val = float(self.acband_entry.get())
            if self.gpib_inst_instance and self.gpib_inst_instance.is_connected():
                self.gpib_inst_instance.ACBAND(val)
        except:
            pass

if __name__ == "__main__":
    app = gui()
    app.run()
