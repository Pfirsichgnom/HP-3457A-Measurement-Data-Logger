import sys
import os
import time
import threading
import queue
import csv
from datetime import datetime
from pathlib import Path
from collections import deque

import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from tkinter import messagebox, filedialog

sys.path.append(str(Path(__file__).resolve().parent / "pygubu"))
from python3ui import guiUI
from gpib_interface import gpio_interface, DEBUG, set_measurement_debug, measurement_debug

# Settings file constant
SETTINGS_FILE = "settings.txt"


class MeasurementStats:
    """Thread-safe measurement statistics calculator."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._samples = deque()
        self._max_samples = 10000
    
    def add_sample(self, value):
        """Add a measurement sample."""
        with self._lock:
            self._samples.append(value)
            if len(self._samples) > self._max_samples:
                self._samples.popleft()
    
    def get_stats(self):
        """Get current statistics. Returns dict with count, min, max, avg, std."""
        with self._lock:
            samples = list(self._samples)
        
        if not samples:
            return {
                'count': 0,
                'min': None,
                'max': None,
                'avg': None,
                'std': None
            }
        
        count = len(samples)
        min_val = min(samples)
        max_val = max(samples)
        avg_val = sum(samples) / count
        
        # Sample standard deviation (n-1 denominator)
        if count > 1:
            variance = sum((x - avg_val) ** 2 for x in samples) / (count - 1)
            std_val = np.sqrt(variance)
        else:
            std_val = 0.0
        
        return {
            'count': count,
            'min': min_val,
            'max': max_val,
            'avg': avg_val,
            'std': std_val
        }
    
    def get_samples(self):
        """Get a copy of all samples."""
        with self._lock:
            return list(self._samples)
    
    def clear(self):
        """Clear all samples."""
        with self._lock:
            self._samples.clear()


class SettingsManager:
    """Manages persistent settings in a human-readable text file."""
    
    def __init__(self, settings_file=SETTINGS_FILE):
        self.settings_file = settings_file
        self.default_resource = "GPIB0::22::INSTR"
        
        # Default settings
        self.defaults = {
            'last_resource': self.default_resource,
            'measurement_interval': '1.0',
            'max_points': '1000',
            'histogram_bins': '50',
            'max_csv_points': '0',
            'save_path': '',
            'nrdgs': '1',
            'digits': '6',
            'nplc': '1',
            'acband': '1',
            'lock_state': '0',
            'trigger_state': '0',
            'fixedz_state': '0',
        }
    
    def load_settings(self):
        """Load all settings from file."""
        settings = self.defaults.copy()
        try:
            if not os.path.exists(self.settings_file):
                return settings
            
            with open(self.settings_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if key in settings:
                            settings[key] = value
            return settings
        except Exception as e:
            if DEBUG:
                print(f"[SETTINGS] Error loading settings: {e}")
            return settings
    
    def save_all_settings(self, settings_dict):
        """Save all settings to file."""
        try:
            with open(self.settings_file, 'w') as f:
                f.write("# GPIB Multimeter Settings\n")
                f.write("# Format: key=value\n\n")
                for key, value in settings_dict.items():
                    f.write(f"{key}={value}\n")
            return True
        except Exception as e:
            if DEBUG:
                print(f"[SETTINGS] Error saving settings: {e}")
            return False
    
    def save_settings(self, resource):
        """Save the instrument resource to settings file."""
        settings = self.load_settings()
        settings['last_resource'] = resource
        return self.save_all_settings(settings)
    
    def load_resource(self):
        """Get last connected resource."""
        settings = self.load_settings()
        return settings.get('last_resource', self.default_resource)


class MeasurementData:
    """Thread-safe container for measurement data and graph updates."""

    def __init__(self, max_points=10000):
        self._lock = threading.Lock()
        self._timestamps = deque()
        self._y_values = deque()
        self._max_points = max_points
        self._next_index = 0

    def add_measurement(self, timestamp, value):
        """Add a measurement with its real timestamp."""
        with self._lock:
            self._timestamps.append(timestamp)
            self._y_values.append(value)
            self._next_index += 1

            if len(self._y_values) > self._max_points:
                self._timestamps.popleft()
                self._y_values.popleft()

    def get_data(self):
        """Get copy of current data as (index, value) lists for the graph."""
        with self._lock:
            n = len(self._y_values)
            start = self._next_index - n
            return list(range(start, start + n)), list(self._y_values)

    def get_timestamped(self):
        """Get a copy of (timestamps, values) for export."""
        with self._lock:
            return list(self._timestamps), list(self._y_values)

    def get_count(self):
        """Get current number of points."""
        with self._lock:
            return len(self._y_values)

    def clear(self):
        """Clear all data."""
        with self._lock:
            self._timestamps.clear()
            self._y_values.clear()
            self._next_index = 0


class gui(guiUI):
    def __init__(self, master=None):
        self.settings_manager = SettingsManager()
        
        super().__init__(master)
        
        self.data_storage = MeasurementData(max_points=10000)
        self.stats = MeasurementStats()
        self.gpib_inst_instance = gpio_interface()

        self.selected_device = None
        self.last_connected_device = None
        self.measurement_unit = ""
        self.running = False
        self.measurement_thread = None
        self.measurement_interval = 1.0
        self.interval_lock = threading.Lock()
        self.save_path = ""
        self.max_csv_points = 0
        self.histogram_bins = 50
        # Events posted by worker threads (connect results, connection loss),
        # processed on the main thread by periodic_update()
        self._pending_ui = queue.Queue()
        self._connect_lock = threading.Lock()
        self._connect_in_progress = False
        self._connecting_device = None
        
        self.fig = None
        self.ax = None
        self.line = None
        self.histogram_fig = None
        self.histogram_ax = None
        
        self._init_gui_elements()
        self._init_device_list()
        self._auto_connect_with_settings()
        
        if DEBUG:
            print("[GPIB] Startup complete")
    
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
            
            save_path = settings.get('save_path', '')
            if save_path:
                self.save_path = save_path
                self.savepath_entry.delete(0, 'end')
                self.savepath_entry.insert(0, save_path)
            
            self.fig = Figure(figsize=(8, 4), dpi=100)
            self.ax = self.fig.add_subplot(111)
            self.line, = self.ax.plot([], [])
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_left_frame)
            self.canvas.get_tk_widget().pack(fill='both', expand=True)
            
            self.ax.set_xlabel('Measurement Index')
            self.ax.set_ylabel('Value')
            self.ax.set_title('Live Measurement')
            self.ax.grid(True)
            
            self.histogram_fig = Figure(figsize=(4, 3), dpi=100)
            self.histogram_ax = self.histogram_fig.add_subplot(111)
            self.hist_canvas = FigureCanvasTkAgg(self.histogram_fig, master=self.histogram_pane)
            self.hist_canvas.get_tk_widget().pack(fill='both', expand=True)
            
            self.histogram_ax.set_xlabel('Value')
            self.histogram_ax.set_ylabel('Frequency')
            self.histogram_ax.set_title('Measurement Distribution')
            self.histogram_ax.grid(True)

            # Keep the histogram pane hidden at startup; it is shown by
            # the Histogram checkbox (see histogram_checked()).
            self.histogram_pane.pack_forget()

            device_list = self.gpib_inst_instance.get_devices()
            if device_list:
                self.device_combo['values'] = device_list
                self.selected_device = device_list[0]
                self.device_combo.set(self.selected_device)
                
        except Exception as e:
            if DEBUG:
                print(f"[GUI] Error creating GUI elements: {e}")
    
    def _init_device_list(self):
        """Initialize device list."""
        devices = self.gpib_inst_instance.get_devices()
        if devices:
            self.device_combo['values'] = devices
            if not self.selected_device and devices:
                self.selected_device = devices[0]
                self.device_combo.set(self.selected_device)
    
    def _auto_connect_with_settings(self):
        """Try to auto-connect on startup using saved settings (non-blocking).

        Measurement is NOT auto-started; use the Start button or a mode
        button to begin reading.
        """
        settings = self.settings_manager.load_settings()
        saved_resource = settings.get('last_resource', self.settings_manager.default_resource)

        if DEBUG:
            print(f"[SETTINGS] Using resource: {saved_resource}")

        # First connect can take several seconds (5s GPIB timeout), so it
        # runs on a worker thread to keep the startup UI responsive.
        if not self.gpib_inst_instance.is_connected():
            self._start_connect(saved_resource)

    def _start_connect(self, device):
        """Start connecting to a device on a worker thread (non-blocking UI)."""
        with self._connect_lock:
            if self._connect_in_progress:
                if DEBUG:
                    print(f"[CONNECT] Already connecting to {self._connecting_device}")
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
                if DEBUG:
                    print(f"[CONNECT] Failed to connect to {device}: {e}")
                self._pending_ui.put(("connect_failed", device, str(e)))
                return

            # Read back the device settings (GPIB I/O, worker thread)
            values = self._query_device_settings()
            self.settings_manager.save_settings(device)

            if DEBUG:
                print(f"[CONNECT] Connected: {device}")
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
            if DEBUG:
                print(f"[INIT] NRDGS query failed: {e}")

        try:
            nplc_val = self.gpib_inst_instance.NPLCQ()
            if nplc_val:
                values['nplc'] = str(float(nplc_val))
        except Exception as e:
            if DEBUG:
                print(f"[INIT] NPLC query failed: {e}")

        try:
            acband_val = self.gpib_inst_instance.ACBANDQ()
            if acband_val:
                acband_int = int(float(acband_val))
                values['acband'] = str(acband_int)
                self.gpib_inst_instance.ACBAND(acband_int)
            else:
                self.gpib_inst_instance.ACBAND(200)
        except Exception as e:
            if DEBUG:
                print(f"[INIT] ACBAND query failed: {e}")
            self.gpib_inst_instance.ACBAND(200)

        # Make sure NPLC matches the saved setting (original behavior)
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
                    self.last_connected_device = device
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
                if DEBUG:
                    print(f"[CONNECT] Event handling error: {e}")
    
    def _apply_interval(self):
        """Apply new measurement interval."""
        try:
            interval = float(self.interval_entry.get())
            if interval <= 0:
                messagebox.showwarning("Invalid Value", "Interval must be greater than 0")
                return
            
            with self.interval_lock:
                self.measurement_interval = interval
            
            settings = self.settings_manager.load_settings()
            settings['measurement_interval'] = str(interval)
            self.settings_manager.save_all_settings(settings)
            
            if DEBUG:
                print(f"[INTERVAL] New interval: {interval}s")
                
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
            self.histogram_bins = 50
            self.bins_entry.delete(0, 'end')
            self.bins_entry.insert(0, "50")
            self._update_histogram()

            settings = self.settings_manager.load_settings()
            settings['histogram_bins'] = '50'
            self.settings_manager.save_all_settings(settings)
    
    def _save_data_csv(self):
        """Save current measurement data to CSV."""
        path = self.savepath_entry.get().strip()
        if not path:
            path = filedialog.askdirectory()
            if not path:
                messagebox.showwarning("No Path", "Please select a save directory first")
                return
        
        try:
            if not os.path.isdir(path):
                messagebox.showerror("Invalid Path", f"Directory does not exist: {path}")
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(path, f"measurements_{timestamp}.csv")
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

            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Timestamp_ns', 'Value'])

                for ts, value in zip(timestamps, samples):
                    writer.writerow([
                        datetime.fromtimestamp(ts).isoformat(),
                        int(ts * 1e9),
                        value,
                    ])

            messagebox.showinfo("Success", f"Data saved to: {filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
    
    def device_combo_selected(self, event=None):
        """Handle device selection change."""
        try:
            device = self.device_combo.get().strip()
            if device:
                self.selected_device = device
        except Exception as e:
            if DEBUG:
                print(f"[DEVICE_SELECT] Error: {e}")
    
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
                if DEBUG:
                    print(f"[MEAS] Starting measurement; connecting to {device}")
            elif DEBUG:
                print("[MEAS] Starting measurement; no device selected")

        if DEBUG:
            print("[MEAS] Starting measurement thread")

        self._reset_measurement_data()

        self.running = True
        self.measurement_thread = threading.Thread(target=self.measure_loop, daemon=True)
        self.measurement_thread.start()
        self._sync_button_states()

    def stop_measurement(self):
        """Stop measurement thread."""
        self.running = False
        if self.measurement_thread:
            # A hanging GPIB read can take up to its 5s timeout
            self.measurement_thread.join(timeout=6)
            self.measurement_thread = None
        self._sync_button_states()
    
    def measure_loop(self):
        """Measurement thread main loop."""
        set_measurement_debug(True)
        measurement_debug("Measurement thread started")
        last_unit = None
        last_time = 0
        conn_lost_reported = False

        while self.running:
            try:
                with self.interval_lock:
                    interval = self.measurement_interval

                current_time = time.time()

                if current_time - last_time < interval:
                    time.sleep(0.01)
                    continue

                if not self.gpib_inst_instance.is_connected():
                    measurement_debug("Device not connected")
                    if not conn_lost_reported:
                        # Post event; the main thread updates the UI
                        self._pending_ui.put_nowait(("conn_lost",))
                        conn_lost_reported = True
                    time.sleep(1)
                    continue
                conn_lost_reported = False
                
                if self.measurement_unit and self.measurement_unit != last_unit:
                    try:
                        self._set_measurement_mode(self.measurement_unit)
                        last_unit = self.measurement_unit
                    except Exception as e:
                        measurement_debug(f"Error setting mode: {e}")
                        time.sleep(interval)
                        continue
                
                try:
                    result = self._read_measurement()

                    if result is not None:
                        val = float(result)
                        timestamp = current_time

                        self.data_storage.add_measurement(timestamp, val)
                        self.stats.add_sample(val)

                        last_time = current_time

                except Exception as e:
                    measurement_debug(f"Read error: {e}")
                
            except Exception as e:
                measurement_debug(f"Loop error: {e}")
            
            time.sleep(0.05)
    
    def _set_measurement_mode(self, mode):
        """Set measurement mode on device."""
        if mode == "DCV":
            self.gpib_inst_instance.DCV(0)
        elif mode == "ACV":
            self.gpib_inst_instance.ACV(0)
        elif mode == "DCI":
            self.gpib_inst_instance.DCI(0)
        elif mode == "ACDCI":
            self.gpib_inst_instance.ACDCI(0)
        elif mode == "OHM":
            self.gpib_inst_instance.OHM(0)
        elif mode == "FREQ":
            self.gpib_inst_instance.FREQ(0)
        elif mode == "OHMF":
            self.gpib_inst_instance.OHMF(0)
        time.sleep(0.1)
    
    def _read_measurement(self):
        """Read measurement from device using read() not query()."""
        try:
            self.gpib_inst_instance.writeTRIG()
            time.sleep(0.05)
            result = self.gpib_inst_instance.R()
            return result
        except Exception as e:
            measurement_debug(f"Read error: {e}")
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
            if DEBUG:
                print(f"[GRAPH] Update error: {e}")
    
    def _update_histogram(self):
        """Update histogram display."""
        if self.histogram_ax is None:
            return
        
        try:
            samples = self.stats.get_samples()
            
            if len(samples) < 2:
                self.histogram_ax.cla()
                self.histogram_ax.text(0.5, 0.5, 'No data', 
                                      transform=self.histogram_ax.transAxes,
                                      ha='center', va='center')
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
            if DEBUG:
                print(f"[HISTOGRAM] Update error: {e}")
    
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
    
    def update_device_list(self):
        """Update device list in combo box."""
        devices = self.gpib_inst_instance.get_devices()
        if devices:
            self.device_combo['values'] = devices
            if not self.selected_device and devices:
                self.selected_device = devices[0]
                self.device_combo.set(self.selected_device)
    
    def volt_dc_pressed(self):
        """Handle VDC button."""
        self._set_measurement_mode_and_start("DCV")

    def volt_ac_pressed(self):
        """Handle VAC button."""
        self._set_measurement_mode_and_start("ACV")

    def curr_dc_pressed(self):
        """Handle Idc button."""
        self._set_measurement_mode_and_start("DCI")

    def curr_ac_pressed(self):
        """Handle Iac button."""
        self._set_measurement_mode_and_start("ACI")
    
    def resistance_pressed(self):
        self._set_measurement_mode_and_start("OHM")
    
    def resistancefw_pressed(self):
        self._set_measurement_mode_and_start("OHMF")
    
    def frequency_pressed(self):
        self._set_measurement_mode_and_start("FREQ")
    
    def acdci_pressed(self):
        self._set_measurement_mode_and_start("ACDCI")
    
    # Aliases for Pygubu Designer compatibility
    def ohm_pressed(self):
        """Alias for resistance_pressed (UI compatibility)."""
        self.resistance_pressed()
    
    def ohmf_pressed(self):
        """Alias for resistancefw_pressed (UI compatibility)."""
        self.resistancefw_pressed()
    
    def acdc_pressed(self):
        """Alias for acdci_pressed (UI compatibility)."""
        self.acdci_pressed()
    
    def freq_pressed(self):
        """Alias for frequency_pressed (UI compatibility)."""
        self.frequency_pressed()
    
    def _set_measurement_mode_and_start(self, mode):
        """Handle a function button (VDC/VAC/IDC/Iac/OHM/OHMF/FREQ/ACDCI).

        When the selected function changes, the previously collected
        samples are no longer comparable, so the stored values, the
        statistics and both diagrams are reset. Pressing the already
        selected function again does not clear the measurement.
        """
        if self.measurement_unit != mode:
            old_mode = self.measurement_unit or "(none)"
            self.measurement_unit = mode
            if DEBUG:
                print(f"[MODE] Function changed: {old_mode} -> {mode}, resetting data and charts")
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
            if DEBUG:
                print(f"[LOCK] Error: {e}")
    
    def trigger_checked(self):
        """Handle Trigger checkbox toggle - sends TGR to device."""
        try:
            if self.gpib_inst_instance and self.gpib_inst_instance.is_connected():
                if self.trigger_checkbox.instate(['selected']):
                    self.gpib_inst_instance.TGR(1)
                else:
                    self.gpib_inst_instance.TGR(0)
        except Exception as e:
            if DEBUG:
                print(f"[TRIGGER] Error: {e}")
    
    def fixedz_checked(self):
        """Handle FixedZ checkbox toggle - sends FIXEDZ command to device."""
        try:
            if self.gpib_inst_instance and self.gpib_inst_instance.is_connected():
                if self.fixedz_checkbox.instate(['selected']):
                    self.gpib_inst_instance.FIXEDZ(1)
                else:
                    self.gpib_inst_instance.FIXEDZ(0)
        except Exception as e:
            if DEBUG:
                print(f"[FIXEDZ] Error: {e}")
    
    def histogram_checked(self):
        """Handle Histogram checkbox toggle - show/hide histogram pane.

        The pane and the graph frame are pack-managed children of the
        panedwindow. The graph frame is packed first with side=left and
        expand=true, so if the histogram is packed after it (as the
        original code did) it is allocated zero width and displays out
        of view. Packing it 'before' the graph frame gives it its own
        space on the right.
        """
        try:
            if self.histogram_checkbox.instate(['selected']):
                self.histogram_pane.pack_forget()
                self.histogram_pane.pack(
                    side='right', fill='both', expand=False,
                    before=self.graph_left_frame
                )
                self.histogram_pane.update_idletasks()
                self._update_histogram()
            else:
                self.histogram_pane.pack_forget()
        except Exception as e:
            if DEBUG:
                print(f"[HISTOGRAM] Error: {e}")
    
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
            val = int(self.digits_entry.get())
            if self.gpib_inst_instance and self.gpib_inst_instance.is_connected():
                self.gpib_inst_instance.NDIG(val)
        except:
            pass
    
    def nplc_pressed(self):
        """Handle NPLC button."""
        try:
            val = float(self.nplc_entry.get())
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
    
    def gpib_addr_pressed(self):
        """Handle GPIB address button - stub for future implementation."""
        pass
    
    def gpib_device_pressed(self):
        """Handle GPIB device connect button on Settings tab (non-blocking)."""
        device = self.gpib_device_entry.get().strip()
        if not device:
            messagebox.showwarning("No Device", "Please enter a device resource")
            return

        self._start_connect(device)


def periodic_update(app):
    """Periodic update function called from main thread."""
    app._handle_connect_events()
    app._sync_button_states()
    if app.running:
        app._update_graph()
        app._update_stats_display()
        app._update_histogram()

    app.mainwindow.after(200, lambda: periodic_update(app))


if __name__ == "__main__":
    app = gui()
    periodic_update(app)
    app.run()
