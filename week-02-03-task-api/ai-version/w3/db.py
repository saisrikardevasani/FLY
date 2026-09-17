"""SQLite storage for tasks. All SQL lives here."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("tasks.db")

SEED = ("Buy milk", "Write the report", "Call the plumber")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _row(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


def init() -> None:
    """Create the file and table if missing, seed only when the table is empty."""
    with connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "title TEXT NOT NULL, "
            "done INTEGER NOT NULL DEFAULT 0)"
        )
        (count,) = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()
        if count == 0:
            conn.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, 0)",
                [(title,) for title in SEED],
            )


def list_tasks() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
    return [_row(r) for r in rows]


def get_task(task_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    return _row(row) if row else None


def create_task(title: str, done: bool) -> dict:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, done) VALUES (?, ?)", (title, int(done))
        )
        task_id = cur.lastrowid
    return {"id": task_id, "title": title, "done": done}


def update_task(task_id: int, title: str, done: bool | None) -> dict | None:
    """done=None keeps the stored value."""
    with connect() as conn:
        cur = conn.execute(
            "UPDATE tasks SET title = ?, done = COALESCE(?, done) WHERE id = ?",
            (title, None if done is None else int(done), task_id),
        )
        if cur.rowcount == 0:
            return None
    return get_task(task_id)


def delete_task(task_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cur.rowcount > 0
