import threading
from collections import deque

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

    def clear(self):
        """Clear all data."""
        with self._lock:
            self._timestamps.clear()
            self._y_values.clear()
            self._next_index = 0