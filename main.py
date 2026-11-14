import threading
import sys
import ctypes
from database import init_db
from telemetry import start_tracking
from ui import AcademixApp

if sys.platform == "win32":
    try:
        my_app_id = "mars.academix.engine.v2"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)
    except Exception:
        pass

if __name__ == "__main__":
    init_db()

    telemetry_thread = threading.Thread(target=start_tracking, daemon=True)
    telemetry_thread.start()

    app = AcademixApp()
    app.mainloop()