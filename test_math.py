"""
test_math.py
Validation script for Member 2's Urgency Engine.
"""

from datetime import datetime, timedelta
from urgency_engine import sort_tasks_by_urgency

def run_test():
    print("=== Member 2: Testing Urgency Math Engine ===\n")
    base_time = datetime(2026, 10, 31, 10, 0)

    # 5 Sample tasks with varying effort, weight, and deadlines
    tasks = [
        {
            "id": 1,
            "title": "Lab Report",
            "estimated_effort": 6.0,
            "priority_weight": 2.0,
            "deadline": (base_time + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
        },
        {
            "id": 2,
            "title": "Problem Set",
            "estimated_effort": 2.0,
            "priority_weight": 1.0,
            "deadline": (base_time + timedelta(days=5)).strftime("%Y-%m-%d %H:%M")
        },
        {
            "id": 3,
            "title": "Project Defense Prep",
            "estimated_effort": 5.0,
            "priority_weight": 2.0,
            "deadline": (base_time + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        },
        {
            "id": 4,
            "title": "Reading Assignment",
            "estimated_effort": 1.0,
            "priority_weight": 1.0,
            "deadline": (base_time + timedelta(hours=36)).strftime("%Y-%m-%d %H:%M")
        },
        {
            "id": 5,
            "title": "Quiz Review",
            "estimated_effort": 3.0,
            "priority_weight": 1.5,
            "deadline": (base_time + timedelta(hours=14)).strftime("%Y-%m-%d %H:%M")
        }
    ]

    print("--- 1. Sorted Tasks (Normal Mode) ---")
    results = sort_tasks_by_urgency(tasks, distraction_minutes=0.0, now=base_time)
    for rank, task in enumerate(results, 1):
        print(f"#{rank} [TUI: {task['tui_score']:.2f}] [{task['urgency_tier']}] -> {task['title']} ({task['hours_left']}h left)")

    print("\n--- 2. Sorted Tasks (Distraction Penalty: 30 mins) ---")
    boosted_results = sort_tasks_by_urgency(tasks, distraction_minutes=30.0, now=base_time)
    for rank, task in enumerate(boosted_results, 1):
        print(f"#{rank} [TUI: {task['tui_score']:.2f}] [{task['urgency_tier']}] -> {task['title']}")

    # Verification checks
    assert results[0]["id"] == 3, "Task 3 (due in 2 hours) should rank #1!"
    assert results[-1]["id"] == 2, "Task 2 (due in 5 days) should rank last!"
    print("\n All assertions passed successfully!")

if __name__ == "__main__":
    run_test();