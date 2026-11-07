import csv
import os
import time
from datetime import datetime
import win32gui
from notifier import show_alert
from database import log_activity

LOG_FILE = "distraction_logs.csv"

def initialize_csv():
    """Create CSV file with headers if it does not exist."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Window_Title", "Duration_Seconds", "Action_Taken"])

def log_distraction(window_title, duration=0, action="Alert Triggered"):
    """Append a distraction record with duration to CSV."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, window_title, f"{duration:.1f}", action])
    print(f"[LOG SAVED]: {timestamp} -> {window_title} | Duration: {duration:.1f}s | Action: {action}")

def check_for_distraction(window_title):
    """Check if the active window matches any distraction keyword."""
    if not window_title:
        return False

    distraction_keywords = [
        "YouTube", 
        "Discord", 
        "Facebook", 
        "Instagram", 
        "Reddit", 
        "Netflix", 
        "Twitter", 
        "Spotify", 
        "WhatsApp",
        "Twitch",
        "Steam",
        "Epic Games",
        "Riot Client",
        "Roblox",
        "Minecraft",
        "Valorant"
    ]
    for word in distraction_keywords:
        if word.lower() in window_title.lower():
            return True
    return False

def start_tracking():
    initialize_csv()
    print("Telemetry tracking  started... (Press Ctrl+C to stop)")
    
    last_alert_time = 0
    in_distraction = False
    distraction_start_time = 0
    current_distracted_title = ""

    try:
        while True:
            window = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(window)
            
            is_distracted = check_for_distraction(title)
            current_time = time.time()

            category = "Distracting" if is_distracted else "Productive"
            try:
                log_activity(window_title=title, category=category)
            except Exception as e:
                print(f"[DB LOG ERROR] : {e}")


            if is_distracted:
                if not in_distraction:
                    in_distraction = True
                    distraction_start_time = current_time
                    current_distracted_title = title
                    last_alert_time = current_time
                    
                    print(f"\n[DISTRACTION DETECTED]: {title}")
                    show_alert(title="Task approaching!", message="Focus back on work.")
                    log_distraction(title, duration=0, action="Session Started")
                
                elif current_time - last_alert_time > 30:
                    print(f"[DISTRACTION ONGOING]: {title}")
                    show_alert(title="Reminder", message="Still off-task. Please refocus!")
                    last_alert_time = current_time

            else:
                if in_distraction:                  
                    total_duration = current_time - distraction_start_time
                    print(f"[FOCUS RESTORED]: Returned to work. Time spent: {total_duration:.1f} seconds.\n")
                    log_distraction(current_distracted_title, duration=total_duration, action="Focus Restored")
                    in_distraction = False
                    distraction_start_time = 0

            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nTelemetry tracking stopped safely by user.")

if __name__ == "__main__":
    start_tracking()