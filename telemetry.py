import csv
import os
import time
from datetime import datetime
import win32gui
from notifier import show_alert
import database
from database import log_activity

LOG_FILE = "distraction_logs.csv"

TELEMETRY_STATE = {
    "user_id": None,
    "grace_limit_sec": 0,        # Chosen timer duration in seconds (max 3600)
    "remaining_sec": 0,          # Current countdown remaining in seconds
    "timer_configured": False,   # True once user sets a timer > 0:00
    "paused": False,             # True when user clicks Pause
    "keywords": list(database.DEFAULT_KEYWORDS),
}


def set_active_user(user_id):
    """Updates the currently logged-in user and loads their custom keyword blacklist."""
    TELEMETRY_STATE["user_id"] = user_id
    if user_id is not None:
        reload_user_keywords(user_id)


def reload_user_keywords(user_id=None):
    """Refreshes the in-memory keyword list from SQLite for the active user."""
    uid = user_id if user_id is not None else TELEMETRY_STATE.get("user_id")
    if uid is not None:
        try:
            TELEMETRY_STATE["keywords"] = database.get_user_keywords(uid)
        except Exception:
            TELEMETRY_STATE["keywords"] = list(database.DEFAULT_KEYWORDS)


def configure_personal_timer(minutes: int, seconds: int = 0) -> bool:
    """
    Sets the personal allowance timer (0:00 to 60:00 max).
    Blocked if a timer is already running (> 0 seconds remaining).
    """
    if TELEMETRY_STATE["remaining_sec"] > 0:
        return False
    total_sec = max(0, min(3600, int(minutes) * 60 + int(seconds)))
    TELEMETRY_STATE["grace_limit_sec"] = total_sec
    TELEMETRY_STATE["remaining_sec"] = total_sec
    TELEMETRY_STATE["timer_configured"] = total_sec > 0
    TELEMETRY_STATE["paused"] = False
    return True


def toggle_pause_timer() -> bool:
    """Toggles pause state while timer is running and returns the new paused status."""
    if TELEMETRY_STATE["remaining_sec"] > 0:
        TELEMETRY_STATE["paused"] = not TELEMETRY_STATE["paused"]
    return TELEMETRY_STATE["paused"]


def can_reset_timer() -> bool:
    """Reset is unlocked ONLY after a configured timer finishes and reaches 00:00."""
    return TELEMETRY_STATE["timer_configured"] and TELEMETRY_STATE["remaining_sec"] == 0


def reset_personal_timer() -> bool:
    """Resets the timer back to the chosen duration once it has reached 00:00."""
    if can_reset_timer():
        TELEMETRY_STATE["remaining_sec"] = TELEMETRY_STATE["grace_limit_sec"]
        TELEMETRY_STATE["paused"] = False
        return True
    return False


def initialize_csv():
    """Create CSV file with headers if it does not exist."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "User_ID", "Window_Title", "Duration_Seconds", "Action_Taken"])


def log_distraction(window_title, duration=0, action="Alert Triggered", user_id=1):
    """Append a distraction record with duration to CSV."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, user_id, window_title, f"{duration:.1f}", action])
    print(f"[LOG SAVED]: User {user_id} | {timestamp} -> {window_title} | Duration: {duration:.1f}s | Action: {action}")


def check_for_distraction(window_title):
    """Check if the active window matches any of the user's configured distraction keywords."""
    if not window_title:
        return False

    active_keywords = TELEMETRY_STATE.get("keywords") or database.DEFAULT_KEYWORDS
    for word in active_keywords:
        if word.lower() in window_title.lower():
            return True
    return False


def start_tracking():
    initialize_csv()
    print("Telemetry tracking started... (Press Ctrl+C to stop)")

    last_alert_time = 0
    in_distraction = False
    distraction_start_time = 0
    current_distracted_title = ""

    try:
        while True:
            user_id = TELEMETRY_STATE.get("user_id")

            if user_id is None:
                time.sleep(1)
                continue

            if TELEMETRY_STATE["paused"]:
                time.sleep(1)
                continue

            window = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(window)

            is_distracted = check_for_distraction(title)
            current_time = time.time()

            if is_distracted and TELEMETRY_STATE["remaining_sec"] > 0:
                TELEMETRY_STATE["remaining_sec"] = max(0, TELEMETRY_STATE["remaining_sec"] - 1)
                category = "Productive"
            else:
                category = "Distracting" if is_distracted else "Productive"

            try:
                log_activity(window_title=title, category=category, user_id=user_id)
            except Exception as e:
                print(f"[DB LOG ERROR]: {e}")

            if is_distracted and TELEMETRY_STATE["remaining_sec"] == 0:
                if not in_distraction:
                    in_distraction = True
                    distraction_start_time = current_time
                    current_distracted_title = title
                    last_alert_time = current_time

                    print(f"\n[DISTRACTION DETECTED]: {title}")
                    show_alert(title="Study Timer Up / Task Approaching!", message="Personal study timer is 00:00. Focus back on work!")
                    log_distraction(title, duration=0, action="Alert Triggered", user_id=user_id)

                elif current_time - last_alert_time > 30:
                    print(f"[DISTRACTION ONGOING]: {title}")
                    show_alert(title="Reminder", message="Still off-task. Please refocus!")
                    last_alert_time = current_time

            else:
                if in_distraction:
                    total_duration = current_time - distraction_start_time
                    print(f"[FOCUS RESTORED]: Returned to work. Time spent: {total_duration:.1f} seconds.\n")
                    log_distraction(current_distracted_title, duration=total_duration, action="Focus Restored", user_id=user_id)
                    in_distraction = False
                    distraction_start_time = 0

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nTelemetry tracking stopped safely by user.")


if __name__ == "__main__":
    start_tracking()