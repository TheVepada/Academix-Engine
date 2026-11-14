import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

DB_NAME = "academix.db"

DEFAULT_KEYWORDS = [
    "YouTube", "Discord", "Facebook", "Instagram", "Reddit",
    "Netflix", "Twitter", "Spotify", "WhatsApp", "Twitch",
    "Steam", "Epic Games", "Riot Client", "Roblox", "Minecraft", "Valorant"
]


def get_connection():
    """Returns a SQLite connection with timeout and WAL journal mode for multi-threading."""
    conn = sqlite3.connect(DB_NAME, timeout=15.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    """Initializes tables for users, tasks, telemetry logs, and custom keywords."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Tasks Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                title TEXT NOT NULL,
                deadline TEXT NOT NULL,
                estimated_effort REAL NOT NULL DEFAULT 1.0,
                priority_weight REAL NOT NULL DEFAULT 1.0,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 3. Activity / Distraction Telemetry Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                window_title TEXT,
                category TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 4. Custom Distraction Keywords Table (Sprint 3)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                keyword TEXT NOT NULL,
                UNIQUE(user_id, keyword)
            )
        """)

        # Safe migration if existing database lacks user_id columns
        cursor.execute("PRAGMA table_info(tasks)")
        if "user_id" not in [col["name"] for col in cursor.fetchall()]:
            cursor.execute("ALTER TABLE tasks ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")

        cursor.execute("PRAGMA table_info(activity_logs)")
        if "user_id" not in [col["name"] for col in cursor.fetchall()]:
            cursor.execute("ALTER TABLE activity_logs ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")

        conn.commit()


# ==================== User Authentication ====================

def seed_default_keywords(user_id: int):
    """Seeds default distraction keywords for a user if they have none."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_keywords WHERE user_id = ?", (user_id,))
        if cursor.fetchone()[0] == 0:
            for kw in DEFAULT_KEYWORDS:
                cursor.execute(
                    "INSERT OR IGNORE INTO user_keywords (user_id, keyword) VALUES (?, ?)",
                    (user_id, kw)
                )
            conn.commit()


def register_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Registers a new user and seeds default keywords."""
    username = username.strip()
    if not username or not password:
        return None
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(password))
            )
            conn.commit()
            uid = cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
    seed_default_keywords(uid)
    return {"id": uid, "username": username}


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verifies login credentials and ensures default keywords exist."""
    username = username.strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username FROM users WHERE username = ? AND password_hash = ?",
            (username, hash_password(password))
        )
        row = cursor.fetchone()
    if row:
        user = dict(row)
        seed_default_keywords(user["id"])
        return user
    return None


# ==================== Custom Distraction Keywords (Sprint 3) ====================

def get_user_keywords(user_id: int = 1) -> List[str]:
    """Returns the active distraction keywords for the user."""
    seed_default_keywords(user_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT keyword FROM user_keywords WHERE user_id = ? ORDER BY keyword ASC",
            (user_id,)
        )
        return [row["keyword"] for row in cursor.fetchall()]


def add_user_keyword(keyword: str, user_id: int = 1) -> bool:
    """Adds a new distraction keyword for the user."""
    kw = keyword.strip()
    if not kw:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO user_keywords (user_id, keyword) VALUES (?, ?)",
                (user_id, kw)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def remove_user_keyword(keyword: str, user_id: int = 1):
    """Deletes a distraction keyword for the user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM user_keywords WHERE user_id = ? AND LOWER(keyword) = LOWER(?)",
            (user_id, keyword.strip())
        )
        conn.commit()


# ==================== Task CRUD Operations ====================

def add_task(title: str, deadline: str, estimated_effort: float = 1.0, priority_weight: float = 1.0, user_id: int = 1) -> int:
    """Inserts a new academic task for a specific user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (user_id, title, deadline, estimated_effort, priority_weight, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (user_id, title.strip(), deadline.strip(), float(estimated_effort), float(priority_weight)))
        conn.commit()
        return cursor.lastrowid


def fetch_tasks(status: str = "pending", user_id: int = 1) -> List[Dict[str, Any]]:
    """Fetches tasks matching status and user_id as clean dictionaries."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if status == "all":
            cursor.execute(
                "SELECT id, title, deadline, estimated_effort, priority_weight, status FROM tasks WHERE user_id = ?",
                (user_id,)
            )
        else:
            cursor.execute(
                "SELECT id, title, deadline, estimated_effort, priority_weight, status FROM tasks WHERE status = ? AND user_id = ?",
                (status, user_id)
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


# ==================== Telemetry Logs & Analytics Aggregation ====================

def log_activity(window_title: str, category: str, user_id: int = 1):
    """Logs a single window poller snapshot for the currently logged-in user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO activity_logs (user_id, window_title, category)
            VALUES (?, ?, ?)
        """, (user_id, window_title, category))
        conn.commit()


def get_distraction_minutes_last_hour(user_id: int = 1) -> float:
    """Computes total distraction time (in minutes) logged in the last 60 minutes for user_id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM activity_logs
            WHERE user_id = ?
            AND category = 'Distracting'
            AND timestamp >= datetime('now', '-1 hour')
        """, (user_id,))
        distracting_samples = cursor.fetchone()[0]
        return round(distracting_samples / 60.0, 1)


def get_recent_logs(limit: int = 15, user_id: int = 1) -> List[Dict[str, Any]]:
    """Fetches the latest activity logs for the active user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT window_title, category, timestamp 
            FROM activity_logs 
            WHERE user_id = ?
            ORDER BY id DESC 
            LIMIT ?
        """, (user_id, limit))
        return [dict(row) for row in cursor.fetchall()]


def get_analytics_summary(user_id: int = 1) -> Dict[str, Any]:
    """Computes comprehensive Sprint 3 focus metrics and top distracting windows for the user."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Productive vs Distracting counts in the last 24 hours
        cursor.execute("""
            SELECT category, COUNT(*) as cnt
            FROM activity_logs
            WHERE user_id = ? AND timestamp >= datetime('now', '-24 hours')
            GROUP BY category
        """, (user_id,))
        counts = {row["category"]: row["cnt"] for row in cursor.fetchall()}

        prod_samples = counts.get("Productive", 0)
        dist_samples = counts.get("Distracting", 0)
        total_samples = prod_samples + dist_samples

        prod_mins = round(prod_samples / 60.0, 1)
        dist_mins = round(dist_samples / 60.0, 1)
        focus_ratio = round((prod_samples / total_samples) * 100, 1) if total_samples > 0 else 100.0

        # Task completion stats
        cursor.execute("SELECT status, COUNT(*) as cnt FROM tasks WHERE user_id = ? GROUP BY status", (user_id,))
        task_counts = {row["status"]: row["cnt"] for row in cursor.fetchall()}
        completed_tasks = task_counts.get("completed", 0)
        pending_tasks = task_counts.get("pending", 0)

        # Top 5 distracting window titles
        cursor.execute("""
            SELECT window_title, COUNT(*) as samples
            FROM activity_logs
            WHERE user_id = ? AND category = 'Distracting' AND window_title != ''
            GROUP BY window_title
            ORDER BY samples DESC
            LIMIT 5
        """, (user_id,))
        top_distractions = [
            {"title": row["window_title"], "minutes": round(row["samples"] / 60.0, 1), "samples": row["samples"]}
            for row in cursor.fetchall()
        ]

        return {
            "productive_mins": prod_mins,
            "distracting_mins": dist_mins,
            "focus_ratio": focus_ratio,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "top_distractions": top_distractions,
        }