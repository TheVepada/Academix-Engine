"""
urgency_engine.py
Owner: Member 2 (Urgency Engine & Math Lead)
Calculates Task Urgency Index (TUI) and dynamic sorting.
"""

from datetime import datetime
from typing import List, Dict, Any


def calculate_hours_left(deadline_str: str, now: datetime = None) -> float:
    """Parses deadline string and returns hours remaining."""
    if not deadline_str:
        return 0.0

    if now is None:
        now = datetime.now()

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            deadline = datetime.strptime(deadline_str.strip(), fmt)
            break
        except ValueError:
            continue
    else:
        return 0.0  # Treat malformed/unknown dates safely as overdue

    delta = deadline - now
    hours_left = delta.total_seconds() / 3600.0
    return max(0.0, hours_left)


def compute_tui_score(
    hours_left: float,
    estimated_effort: float,
    priority_weight: float = 1.0,
    distraction_minutes_last_hour: float = 0.0,
    k_constant: float = 4.0
) -> float:
    """
    Calculates the Task Urgency Index (TUI) capped at 1.00 (REQ-FR-10).
    Base = (Weight * Estimated_Effort) / (Hours_Left + 1)
    """
    if hours_left <= 0:
        return 1.00  # Past deadline is always maximum critical urgency

    try:
        effort = max(0.1, float(estimated_effort))
        weight = max(0.1, float(priority_weight))
    except (ValueError, TypeError):
        effort = 1.0
        weight = 1.0

    base_urgency = (weight * effort) / (hours_left + 1.0)
    score = base_urgency / k_constant

    # Sprint 2 logic: +20% boost if user spent >= 20 mins distracted
    if distraction_minutes_last_hour >= 20.0:
        score *= 1.20

    # REQ-FR-10: Cap score at 1.00
    return min(1.00, round(score, 2))


def get_urgency_tier(tui_score: float) -> str:
    """Returns visual color-coded tier matching SRS thresholds."""
    if tui_score >= 0.60:
        return "CRITICAL (Red)"
    elif tui_score >= 0.30:
        return "MEDIUM (Yellow)"
    return "SAFE (Green)"


def sort_tasks_by_urgency(
    tasks: List[Dict[str, Any]],
    distraction_minutes: float = 0.0,
    now: datetime = None
) -> List[Dict[str, Any]]:
    """
    Calculates TUI for each task and returns them sorted descending (REQ-FR-11).
    Tie-breaker: task with fewer hours left comes first.
    """
    if not tasks:
        return []

    scored_tasks = []

    for task in tasks:
        deadline = task.get("deadline", "")
        effort = task.get("estimated_effort", 1.0)
        weight = task.get("priority_weight", 1.0)

        hours = calculate_hours_left(deadline, now=now)
        tui = compute_tui_score(
            hours_left=hours,
            estimated_effort=effort,
            priority_weight=weight,
            distraction_minutes_last_hour=distraction_minutes
        )

        updated_task = dict(task)
        updated_task["hours_left"] = round(hours, 1)
        updated_task["tui_score"] = tui
        updated_task["urgency_tier"] = get_urgency_tier(tui)
        scored_tasks.append(updated_task)

    # Primary sort: TUI score (descending), Secondary sort: hours_left (ascending)
    scored_tasks.sort(key=lambda t: (-t["tui_score"], t["hours_left"]))
    return scored_tasks

def format_db_rows_to_tasks(db_rows: list) -> list:
    """Helper to convert Member 1's SQLite tuples into dictionary format."""
    tasks = []
    for row in db_rows:
        tasks.append({
            "id": row[0],
            "title": row[1],
            "deadline": row[2],
            "estimated_effort": row[3],
            "priority_weight": row[4],
            "status": row[5] if len(row) > 5 else "pending"
        })
    return tasks