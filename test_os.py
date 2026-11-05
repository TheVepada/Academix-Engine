import time
import win32gui

print("Window tracking test started... (Press Ctrl+C to stop)")

while True:
    window = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(window)
    print("Active Window:", title)
    time.sleep(3)