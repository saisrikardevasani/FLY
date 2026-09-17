"""All database access. No SQL outside this module."""

import os

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]

SEED = [
    ("Read the assignment", True),
    ("Build the CRUD API", False),
    ("Push it to GitHub", False),
]

SORTABLE = {"id", "title"}


def connect():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init():
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        if conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"] == 0:
            for title, done in SEED:
                conn.execute(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s)", (title, done)
                )


def ping():
    with connect() as conn:
        return conn.execute("SELECT 1 AS ok").fetchone()["ok"] == 1


def all_tasks(done=None, search=None, sort="id", limit=50, offset=0):
    clauses, params = [], []
    if done is not None:
        clauses.append("done = %s")
        params.append(done)
    if search:
        clauses.append("title ILIKE %s")
        params.append(f"%{search}%")
    sql = "SELECT * FROM tasks"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    if sort not in SORTABLE:
        sort = "id"
    sql += f" ORDER BY {sort} LIMIT %s OFFSET %s"
    with connect() as conn:
        return conn.execute(sql, (*params, limit, offset)).fetchall()


def one_task(task_id):
    with connect() as conn:
        return conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()


def add_task(title, done):
    with connect() as conn:
        return conn.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *", (title, done)
        ).fetchone()


def edit_task(task_id, title, done):
    with connect() as conn:
        return conn.execute(
            "UPDATE tasks SET title = %s, done = COALESCE(%s::boolean, done),"
            " updated_at = now() WHERE id = %s RETURNING *",
            (title, done, task_id),
        ).fetchone()


def remove_task(task_id):
    with connect() as conn:
        return (
            conn.execute(
                "DELETE FROM tasks WHERE id = %s RETURNING id", (task_id,)
            ).fetchone()
            is not None
        )


def stats():
    with connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE done) AS done FROM tasks"
        ).fetchone()


def reset():
    with connect() as conn:
        conn.execute("TRUNCATE tasks RESTART IDENTITY")
    init()
    return all_tasks()
