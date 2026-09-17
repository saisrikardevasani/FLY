"""All database access for the task API. No SQL lives outside this module."""

import os

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]

SEED = [
    ("Read the assignment", True),
    ("Build the CRUD API", False),
    ("Push it to GitHub", False),
]


def connect():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init():
    """Create the tasks table if it is missing and seed it if it is empty."""
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"]
        if count == 0:
            for title, done in SEED:
                conn.execute(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s)", (title, done)
                )


def all_tasks():
    with connect() as conn:
        return conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()


def one_task(task_id):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM tasks WHERE id = %s", (task_id,)
        ).fetchone()


def add_task(title, done):
    with connect() as conn:
        return conn.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *",
            (title, done),
        ).fetchone()


def edit_task(task_id, title, done):
    """done=None means keep whatever is stored."""
    with connect() as conn:
        if done is None:
            return conn.execute(
                "UPDATE tasks SET title = %s WHERE id = %s RETURNING *",
                (title, task_id),
            ).fetchone()
        return conn.execute(
            "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING *",
            (title, done, task_id),
        ).fetchone()


def remove_task(task_id):
    with connect() as conn:
        row = conn.execute(
            "DELETE FROM tasks WHERE id = %s RETURNING id", (task_id,)
        ).fetchone()
        return row is not None
