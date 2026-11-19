import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent / "pygubu"))
from guiUI import guiUI
from gui import gui

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
