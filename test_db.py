"""
test_db.py
Verifies Member 1 deliverables: schema creation, CRUD, and urgency engine compatibility.
"""

from database import init_db, add_task, fetch_tasks, log_activity, get_distraction_minutes_last_hour
from urgency_engine import sort_tasks_by_urgency

def run_db_test():
    print("=== Testing Database & Urgency Integration ===")
    init_db()
    print("✓ Tables initialized.")

    # 1. Add sample tasks
    add_task("Algorithms Final Submission", "2026-11-06 18:00", estimated_effort=5.0, priority_weight=2.0)
    add_task("OS Lab Report", "2026-11-08 23:59", estimated_effort=2.0, priority_weight=1.0)
    print("✓ Added 2 test tasks.")

    # 2. Fetch tasks directly into Urgency Engine
    tasks = fetch_tasks()
    print(f"✓ Fetched {len(tasks)} tasks as dicts directly from SQLite.")

    # 3. Simulate Member 3 logging 20 distraction events
    for _ in range(20):
        log_activity("YouTube - Watch Video", "Distracting")
    
    distraction_time = get_distraction_minutes_last_hour()
    print(f"✓ Calculated distraction time: {distraction_time} mins.")

    # 4. Feed directly into your Urgency Engine
    prioritized = sort_tasks_by_urgency(tasks, distraction_minutes=distraction_time)
    print("\n--- Live Dynamic Priority Output ---")
    for task in prioritized:
        print(f"[{task['urgency_tier']}] {task['title']} (TUI: {task['tui_score']}, {task['hours_left']}h left)")

    print("\n✓ Full persistence and scoring loop verified!")

if __name__ == "__main__":
    run_db_test()