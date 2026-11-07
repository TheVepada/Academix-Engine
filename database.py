

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any

DB_NAME = "academix.db"


def get_connection():
    """Returns a SQLite connection with timeout and WAL journal mode for multi-threading."""
    conn = sqlite3.connect(DB_NAME, timeout=15.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes tables for tasks and telemetry logs (REQ-FR-01, REQ-FR-02, REQ-FR-05)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Tasks Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                deadline TEXT NOT NULL,
                estimated_effort REAL NOT NULL DEFAULT 1.0,
                priority_weight REAL NOT NULL DEFAULT 1.0,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Activity / Distraction Telemetry Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                window_title TEXT,
                category TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


# ==================== Task CRUD Operations ====================

def add_task(title: str, deadline: str, estimated_effort: float = 1.0, priority_weight: float = 1.0) -> int:
    """Inserts a new academic task."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (title, deadline, estimated_effort, priority_weight, status)
            VALUES (?, ?, ?, ?, 'pending')
        """, (title.strip(), deadline.strip(), float(estimated_effort), float(priority_weight)))
        conn.commit()
        return cursor.lastrowid


def fetch_tasks(status: str = "pending") -> List[Dict[str, Any]]:
    """Fetches tasks matching status as clean dictionaries ready for urgency_engine.py."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if status == "all":
            cursor.execute("SELECT id, title, deadline, estimated_effort, priority_weight, status FROM tasks")
        else:
            cursor.execute(
                "SELECT id, title, deadline, estimated_effort, priority_weight, status FROM tasks WHERE status = ?",
                (status,)
            )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def mark_task_complete(task_id: int):
    """Marks a task as completed."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))
        conn.commit()


def delete_task(task_id: int):
    """Deletes a task from the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()

        


# ==================== Telemetry Logs & Distraction Aggregation ====================

def log_activity(window_title: str, category: str):
    """Logs a single window poller snapshot from Member 3's telemetry daemon."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO activity_logs (window_title, category)
            VALUES (?, ?)
        """, (window_title, category))
        conn.commit()


def get_distraction_minutes_last_hour() -> float:
    """
    Computes total distraction time (in minutes) logged in the last 60 minutes.
    Assumes standard 3-second polling interval (REQ-FR-04).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        # Query logs from the last 60 minutes marked as 'Distracting'
        cursor.execute("""
            SELECT COUNT(*) FROM activity_logs
            WHERE category = 'Distracting'
            AND timestamp >= datetime('now', '-1 hour')
        """)
        distracting_samples = cursor.fetchone()[0]
        # Each sample is 3 seconds -> minutes = (samples * 3) / 60 = samples / 20
        distraction_minutes = distracting_samples / 60.0
        return round(distraction_minutes, 1)

def get_recent_logs(limit: int = 15) -> List[Dict[str, Any]]:
    """Fetches the latest activity logs from Member 3's telemetry daemon."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT window_title, category, timestamp 
            FROM activity_logs 
            ORDER BY id DESC 
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]