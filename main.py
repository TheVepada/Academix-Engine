# main.py
import threading
from database import init_db
from telemetry import start_tracking
from ui import AcademixApp
import sys
import ctypes

if sys.platform == "win32":
    try:
        my_app_id = "academix.engine.desktop.v1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)
    except (AttributeError, Exception):
        passModelId(my_app_id)

if __name__ == "__main__":
    # 1. Ensure SQLite schema and tables exist
    init_db()

    # 2. Start telemetry poller as a background daemon thread
    telemetry_thread = threading.Thread(target=start_tracking, daemon=True)
    telemetry_thread.start()

    # 3. Launch UI on the main thread
    app = AcademixApp()
    app.mainloop()
    