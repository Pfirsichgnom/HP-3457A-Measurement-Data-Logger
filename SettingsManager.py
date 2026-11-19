import os

# Settings file constant
SETTINGS_FILE = "settings.txt"

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
            'cont_save':'1',
            'show_histogram':'1',
            'acdc_state':'1'
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
            print_debug(f"[SETTINGS] Error loading settings: {e}")
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
            print_debug(f"[SETTINGS] Error saving settings: {e}")
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