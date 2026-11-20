"""
 GPIB interface module for multimeter control.
 Handles device discovery, connection, and SCPI commands.
"""

import pyvisa
import os
import threading
import datetime

# Global debug switches (override with GPIB_DEBUG=1/0)
DEBUG = os.environ.get("GPIB_DEBUG", "1") == "1"

# GPIB mutex - protects all GPIB operations
_gpib_lock = threading.RLock()

# Connection state tracking
_connection_lock = threading.Lock()
_is_connected = False

def print_debug(msg):
    """Print debug message if debugging is enabled."""
    if DEBUG:
        print(msg)

class GPIBConnectionError(Exception):
    """Exception raised for GPIB connection errors."""
    pass


class GPIBReadError(Exception):
    """Exception raised for GPIB read errors."""
    pass


class GPIBWriteError(Exception):
    """Exception raised for GPIB write errors."""
    pass


class GPIBInterface:
    """GPIB interface class for multimeter control."""
    
    def __init__(self):
        self.instr_list = []
        self.instr = None
        self._connected = False
        self._resource_manager = None
        
        try:
            self._resource_manager = pyvisa.ResourceManager("@py")
        except Exception as e:
            print_debug(f"[GPIB] Failed to create resource manager: {e}")
    
    def _write(self, cmd):
        """Write command to device with error handling."""
        with _gpib_lock:
            print_debug(f"[GPIB] WRITE: {cmd}")
            if self.instr:
                try:
                    self.instr.write(cmd)
                except pyvisa.VisaIOError as e:
                    raise GPIBWriteError(f"Write error: {e}")
               

    def _query(self, cmd):
        """Write command and read response with error handling."""
        with _gpib_lock:
            print_debug(f"[GPIB] WRITE: {cmd}")
            if self.instr:
                try:
                    result = self.instr.query(cmd)
                    print_debug(f"[GPIB] RESPONSE: {result}")
                    return result
                except pyvisa.VisaIOError as e:
                    raise GPIBReadError(f"Query error: {e}")
            return None

    def is_connected(self):
        """Thread-safe check if device is connected."""
        with _connection_lock:
            return self._connected
    
    def _set_connected_state(self, state):
        """Thread-safe set connection state (internal)."""
        with _connection_lock:
            self._connected = state
    
    def get_devices(self):
        """Discover available GPIB devices."""
        print_debug("[GPIB] Searching for devices...")
        self.instr_list = []
        if self._resource_manager is None:
            print_debug("[GPIB] Resource manager not available")
            return self.instr_list
        
        try:
            devices = self._resource_manager.list_resources()
            self.instr_list = list(devices)
            for device in self.instr_list:
                print_debug(f"[GPIB] Found device: {device}")

            gpib_devs = self._get_gpib_devices_from_fs()
            for device in gpib_devs:
                if device not in self.instr_list:
                    self.instr_list.append(device)
                    print_debug(f"[GPIB] Found device: {device}")
        except Exception as e:
            print_debug(f"[GPIB] Error during GPIB device discovery: {e}")
        
        if not self.instr_list:
            print_debug("[GPIB] No devices found.")
        
        return self.instr_list
    
    def _get_gpib_devices_from_fs(self):
        """Get GPIB devices from filesystem."""
        gpib_devices = []
        
        if os.path.exists("/dev/gpib"):
            try:
                for item in os.listdir("/dev/gpib"):
                    resource = f"GPIB0::{item}::INSTR"
                    gpib_devices.append(resource)
            except Exception:
                pass
        
        if os.path.exists("/dev/gpib0"):
            gpib_devices.append("GPIB0::22::INSTR")
        
        if os.path.exists("/dev"):
            try:
                for item in os.listdir("/dev"):
                    if item.startswith("gpib"):
                        try:
                            addr = int(item.replace("gpib", ""))
                            gpib_devices.append(f"GPIB0::{addr}::INSTR")
                        except ValueError:
                            continue
            except Exception:
                pass

        return gpib_devices
    
    def select_devices(self, device):
        """
        Connect to specified device.
        
        Raises:
            GPIBConnectionError: If connection fails
        """
        with _gpib_lock:
            try:
                print_debug(f"[GPIB] Connecting to: {device}")
                
                if self._resource_manager is None:
                    raise GPIBConnectionError("Resource manager not available")
                
                # Close existing connection if any
                if self.instr:
                    try:
                        self.instr.close()
                    except Exception:
                        pass
                
                self.instr = self._resource_manager.open_resource(device)
                
                # Set communication parameters
                self.instr.timeout = 6000  # 1 second timeout
                self.instr.write_termination = "\n"
                self.instr.read_termination = "\n"
                
                print_debug("[GPIB] Writing PRESET to device...")
                self.instr.write("PRESET")

                print_debug("[GPIB] Writing END ALWAYS to device...")
                self.instr.write("END ALWAYS")
                
                # Query device ID to verify connection
                device_id = self.instr.query("*IDN?")
                print_debug(f"[GPIB] Device ID: {device_id}")
                
                self._set_connected_state(True)
                print_debug("[GPIB] Connection established")
                
            except Exception as e:
                self._set_connected_state(False)
                raise GPIBConnectionError(f"Failed to connect to {device}: {e}")
    
    def disconnect_device(self):
        """Thread-safe disconnect from device."""
        with _gpib_lock:
            try:
                if self.instr:
                    self.instr.close()
            except Exception:
                pass
            finally:
                self.instr = None
                self._set_connected_state(False)
    
    def auto_connect(self):
        """
        Auto-connect to available device.
        
        Returns:
            str: Connected resource name, or None if failed
        """
        print_debug("[GPIB] Attempting auto-connect...")
        default_resource = "GPIB0::22::INSTR"
        
        # Try saved/default resource first
        try:
            self.select_devices(default_resource)
            print_debug(f"[GPIB] Connected to default device: {default_resource}")
            return default_resource
        except Exception as e:
            print_debug(f"[GPIB] Failed to connect to default device: {e}")
        
        # Try USB devices
        instr_list = self.get_devices()
        for resource in instr_list:
            if "USB" in resource:
                try:
                    self.select_devices(resource)
                    print_debug(f"[GPIB] Connected to USB device: {resource}")
                    return resource
                except Exception:
                    continue
        
        # Try first available device
        if instr_list:
            try:
                self.select_devices(instr_list[0])
                print_debug(f"[GPIB] Connected to first available device: {instr_list[0]}")
                return instr_list[0]
            except Exception:
                pass
        
        print_debug("[GPIB] No devices available for auto-connect")
        return None
    
    # Measurement mode commands
    def DCV(self, range_val):
        """DC Voltage mode."""
        if range_val == 0:
            self._write("DCV AUTO")
        else:
            self._write(f"DCV {range_val:.2f}")
    
    def ACV(self, range_val):
        """AC Voltage mode."""
        if range_val == 0:
            self._write("ACV AUTO")
        else:
            self._write(f"ACV {range_val:.2f}")
    
    def ACDCV(self, range_val):
        """AC Voltage mode."""
        if range_val == 0:
            self._write("ACDCV AUTO")
        else:
            self._write(f"ACDCV {range_val:.2f}")
    
    def DCI(self, range_val):
        """DC Current mode."""
        if range_val == 0:
            self._write("DCI AUTO")
        else:
            self._write(f"DCI {range_val:.2f}")
    
    def ACI(self, range_val):
        """AC Current mode."""
        if range_val == 0:
            self._write("ACI AUTO")
        else:
            self._write(f"ACI {range_val:.2f}")
    
    def ACDCI(self, range_or_freq):
        """AC/DC Current mode - use ACI for auto range."""
        if range_or_freq == 0:
            self._write("ACI AUTO")
        elif isinstance(range_or_freq, (int, float)):
            self._write(f"ACI {range_or_freq:.2f}")
    
    def OHM(self, range_val):
        """Resistance mode."""
        if range_val == 0:
            self._write("OHM AUTO")
        else:
            self._write(f"OHM {range_val:.2e}")
    
    def OHMF(self, range_val):
        """Four Wire resistance mode."""
        if range_val == 0:
            self._write("OHMF AUTO")
        else:
            self._write(f"OHMF {range_val:.2e}")
    
    def FREQ(self, range_val):
        """Frequency mode."""
        if range_val == 0:
            self._write("FREQ AUTO")
        else:
            self._write(f"FREQ {range_val}")
    
    # Trigger and read commands
    def writeTRIG(self):
        """Write trigger command."""
        with _gpib_lock:
            if self.instr:
                try:
                    self.TRIG_SYN()
                except pyvisa.VisaIOError as e:
                    raise GPIBWriteError(f"Trigger error: {e}")
    
    def read(self):
        """
        Read measurement value from device.
        
        Returns:
            str: Measurement response, or None on error
        """
        with _gpib_lock:
            if self.instr:
                try:
                    result = self.instr.read()
                    print_debug(f"[GPIB] READ: {result}")
                    return result
                except pyvisa.VisaIOError as e:
                    print_debug(f"[GPIB] Read error: {e}")
                    return None
            return None
    

    
    # Configuration commands
    def PRESET(self):
        """Preset device to default state."""
        self._write("PRESET")
    
    def RESET(self):
        """Reset device."""
        self._write("RESET")
    
    def CRESET(self):
        """Communication reset."""
        self._write("CRESET")
    
    def NRDGS(self, val):
        """Set number of readings."""
        self._write(f"NRDGS {int(val)}")
    
    def NRDGSQ(self):
        """Query number of readings."""
        return self._query("NRDGS?")
    
    def NDIG(self, val):
        """Set number of digits."""
        self._write(f"NDIG {float(val)}")
    
    def NPLC(self, val):
        """Set number of power line cycles."""
        num = float(val)
        if str(val)[0]=='0':
            num = str(val)[1::]
            
        self._write(f"NPLC {num}")
    
    def NPLCQ(self):
        """Query number of power line cycles."""
        return self._query("NPLC?")
    
    def ACBAND(self, freq):
        """Set AC bandwidth."""
        self._write(f"ACBAND {int(freq)}")
    
    def ACBANDQ(self):
        """Query AC bandwidth."""
        return self._query("ACBAND?")
    
    def ADCOUPLE(self, coupling):
        """Set ADC coupling (AC or DC)."""
        self._write(f"ADCOUPLE {coupling}")
    
    def LOCK(self, val):
        """Lock setting."""
        self._write(f"LOCK {int(val)}")
    
    def TRIG(self, val):
        """TRIG setting."""
        self._write(f"TRIG {int(val)}")
    
    def TRIG_SYN(self):
        """TRIG SYN"""
        self._write(f"TRIG SYN")
    
    def TGR(self, val):
        """TGR setting (trigger gate)."""
        self._write(f"TGR {int(val)}")
    
    def TRIGQ(self):
        """Query TRIG setting."""
        return self._query("TRIG?")
    
    # Standard HP 3457A negative error codes (as returned by ERR?)
    _ERR_DESCRIPTIONS = {
        -1: "Syntax error",
        -2: "Unknown command received",
        -100: "Parameter (value) out of range",
        -101: "Parameter ignored",
        -102: "Required parameter missing",
        -110: "Unknown command received",
        -111: "Unknown parameter received",
        -208: "Out of memory",
        -853: "Out of calibration",
        -859: "Autocal required",
    }

    # Query commands
    def ERR(self):
        """Query error status. Handles negative HP error numbers and
        legacy positive bitmask values."""
        try:
            error = int(self._query("ERR?"))
        except (ValueError, TypeError):
            error = 0
        errors = []
        if error < 0:
            errors.append(self._ERR_DESCRIPTIONS.get(error, f"Unknown error (code {error})"))
            return error, errors
        if error > 0:
            if error & 0x001:
                errors.append("Hardware error, check the auxiliary error register")
            if error & 0x002:
                errors.append("Error in the CAl or ACAL process")
            if error & 0x004:
                errors.append("Trigger too fast")
            if error & 0x008:
                errors.append("Syntax error")
            if error & 0x010:
                errors.append("Unknown command received")
            if error & 0x020:
                errors.append("Unknown parameter received")
            if error & 0x040:
                errors.append("Parameter out of range")
            if error & 0x080:
                errors.append("Required parameter missing")
            if error & 0x100:
                errors.append("Parameter ignored")
            if error & 0x200:
                errors.append("Out of calibration")
            if error & 0x400:
                errors.append("Autocal required")
        return error, errors
    
    def STBQ(self):
        """Query status byte."""
        try:
            error = int(self._query("STB?"))
        except (ValueError, TypeError):
            error = 0
        errors = []
        if error > 0:
            if error & 0x001:
                errors.append("Program Memory Execution Completed")
            if error & 0x002:
                errors.append("Hi or Lo Limit Exceeded")
            if error & 0x004:
                errors.append("Front Panel SRQ")
            if error & 0x008:
                errors.append("Power On SRQ")
            if error & 0x010:
                errors.append("Ready")
            if error & 0x020:
                errors.append("Error (Consult Error Register)")
            if error & 0x040:
                errors.append("Service Requested (you cannot disable this bit)")
            if error & 0x080:
                errors.append("not used")
        return error, errors
    
    def IDQ(self):
        """Query device ID."""
        return self._query("ID?")
    
    def RANGEQ(self):
        """Query current range."""
        return self._query("RANGE?")
    
    def CHANQ(self):
        """Query current channel."""
        return self._query("CHAN?")
    
    def DELAYQ(self):
        """Query delay setting."""
        return self._query("DELAY?")
    
    def TERMQ(self):
        """Query terminal setting."""
        return self._query("TERM?")
    
    def TIMERQ(self):
        """Query timer setting."""
        return self._query("TIMER?")
    
    def LFREQQ(self):
        """Query low frequency setting."""
        return self._query("LFREQ?")
    
    def LINE(self):
        """Query LINE setting."""
        return self._query("LINE?")
    
    def CALNUM(self):
        """Query calibration number."""
        return self._query("CALNUM?")
    
    def OPTQ(self):
        """Query options."""
        return self._query("OPT?")
    
    def FIXEDZQ(self):
        """Query fixed Z setting."""
        return self._query("FIXEDZ?")
    
    def OCOMPQ(self):
        """Query OCOMP setting."""
        return self._query("OCOMP?")
    
    def AZEROQ(self):
        """Query Azero setting."""
        return self._query("AZERO?")
    
    def AUXERR(self):
        """Query auxiliary error."""
        return self._query("AUXERR?")
    
    # Additional commands
    def ACAL(self):
        """ACAL 1."""
        if self.instr is None:
            raise GPIBWriteError("Not connected")
        with _gpib_lock:
            try:
                self.instr.timeout = 60000
            except Exception:
                pass
            self._write("ACAL 1")
            try:
                self.instr.timeout = 3000
            except Exception:
                pass
    
    def AZERO(self, val):
        """AZERO setting."""
        self._write(f"AZERO{val}")
    
    def BEEP(self):
        """Beep command."""
        self._write("BEEP")
    
    def CHAN(self, chan):
        """Set channel."""
        self._write(f"CHAN{chan}")
    
    def CLOSE(self, chan):
        """Close channel."""
        self._write(f"CLOSE{chan}")
    
    def CSB(self):
        """CSB command."""
        self._write("CSB")
    
    def DELAY(self, time_val):
        """Set delay."""
        self._write(f"DELAY {time_val:.2e}")
    
    def DISPLAY(self, mesg):
        """Display message."""
        self._write(f"DISPLAY {mesg}")
    
    def FIXEDZ(self, val=None):
        """Fixed Z command."""
        if val is not None:
            self._write(f"FIXEDZ {int(val)}")
        else:
            self._write("FIXEDZ")
    
    def FSOURCE(self, src):
        """Set frequency source."""
        self._write(f"FSOURCE {int(src)}")
    
    def INBUF(self, state):
        """Set input buffer."""
        self._write(f"INBUF {int(state)}")
    
    def LFREQ(self, freq):
        """Set low frequency."""
        self._write(f"LFREQ {int(freq)}")
    
    def LINEQ(self):
        """Line query."""
        return self._query("LINEQ?")
    
    def OCOMP(self, val):
        """Set OCOMP."""
        self._write(f"OCOMP {int(val)}")
    
    def PAUSE(self):
        """Pause command."""
        self._write("PAUSE")
    
    def PER(self, range_val):
        """Set period range."""
        self._write(f"PER {range_val}")
    
    def RANGE(self, range_val):
        """Set range."""
        self._write(f"RANGE{range_val:.2e}")
    
    def TARM(self, value):
        """Set TARM."""
        self._write(f"TARM {int(value)}")
    
    def TERM(self, value):
        """Set TERM."""
        self._write(f"TERM {int(value)}")
    
    def TIMER(self, value):
        """Set timer."""
        self._write(f"TIMER {int(value)}")
    
    def TONE(self, value):
        """Set tone."""
        self._write(f"TONE {int(value)}")
