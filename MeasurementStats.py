import threading
from collections import deque
import numpy as np

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
            arr = np.asarray(list(self._samples), float)
        
        if arr.size<=0:
            return {
                'count': 0,
                'min': None,
                'max': None,
                'avg': None,
                'std': None
            }
        
        count = len(arr)
        min_val = arr.min()
        max_val = arr.max()
        avg_val = arr.mean()
        if arr.size > 1:
            std_val = arr.std(ddof=1)        
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