"""SQLite storage for the task API. Every statement lives in this module."""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterator, Literal

DB_PATH = Path(__file__).with_name("tasks.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY,
    title      TEXT NOT NULL,
    done       INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_tasks_title ON tasks (title);
"""

SEED = (
    ("Buy milk", 0),
    ("Write the status report", 0),
    ("Book the flights", 1),
)

Sort = Literal["id", "title"]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_conn() -> Iterator[sqlite3.Connection]:
    """One connection per request, closed even when the route raises."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def init() -> None:
    with closing(connect()) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        seed_if_empty(conn)


def seed_if_empty(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
        conn.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)", SEED)
        conn.commit()


def as_task(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


def list_tasks(
    conn: sqlite3.Connection,
    done: bool | None,
    search: str | None,
    sort: Sort,
    limit: int,
    offset: int,
) -> list[dict]:
    assert sort in ("id", "title"), sort  # a column cannot be a ? parameter
    sql = "SELECT id, title, done FROM tasks"
    where: list[str] = []
    params: list[object] = []
    if done is not None:
        where.append("done = ?")
        params.append(int(done))
    if search:
        where.append("title LIKE ?")
        params.append(f"%{search}%")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {sort} LIMIT ? OFFSET ?"
    params += [limit, offset]
    return [as_task(r) for r in conn.execute(sql, params)]


def get_task(conn: sqlite3.Connection, task_id: int) -> dict | None:
    row = conn.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    return as_task(row) if row else None


def create_task(conn: sqlite3.Connection, title: str, done: bool) -> dict:
    cur = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)", (title, int(done))
    )
    conn.commit()
    return {"id": cur.lastrowid, "title": title, "done": done}


def update_task(
    conn: sqlite3.Connection, task_id: int, title: str, done: bool | None
) -> dict | None:
    """COALESCE keeps the stored done flag when the body omits it."""
    cur = conn.execute(
        "UPDATE tasks SET title = ?, done = COALESCE(?, done),"
        " updated_at = datetime('now') WHERE id = ?",
        (title, None if done is None else int(done), task_id),
    )
    conn.commit()
    return get_task(conn, task_id) if cur.rowcount else None


def delete_task(conn: sqlite3.Connection, task_id: int) -> bool:
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    return cur.rowcount > 0


def stats(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        "SELECT (SELECT COUNT(*) FROM tasks) AS total,"
        " (SELECT COUNT(*) FROM tasks WHERE done = 1) AS done,"
        " (SELECT COUNT(*) FROM tasks WHERE done = 0) AS open"
    ).fetchone()
    return {"total": row["total"], "done": row["done"], "open": row["open"]}


def reset(conn: sqlite3.Connection) -> list[dict]:
    conn.execute("DELETE FROM tasks")
    conn.commit()
    seed_if_empty(conn)
    return list_tasks(conn, None, None, "id", len(SEED), 0)
