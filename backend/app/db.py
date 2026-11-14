#app/db.py
#database connection and initialization (using SQLite)

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "planner.db"

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db() -> None:
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            weekly_hours INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            profile_id INTEGER REFERENCES profiles(id),
            name TEXT NOT NULL,
            duration INTEGER NOT NULL,
            benefit REAL NOT NULL,
            deadline TEXT,
            course_id TEXT,
            completed INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER REFERENCES profiles(id),
            algorithm TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()