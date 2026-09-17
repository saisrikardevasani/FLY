"""Storage layer. Every SQL string in this project lives in this file.

Third storage engine, same five endpoints: a Python list (A1), a SQLite file (A2), now a
Postgres server in a container. Routes call the functions below and never see SQL, so the
next swap touches this file only.
"""

import os
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and try again.")

SEED = [
    ("Read the assignment", True),
    ("Build the CRUD API", False),
    ("Push it to GitHub", False),
]

# A column name cannot travel as a query parameter, so the two sortable columns are named
# here. Anything else never reaches the SQL text.
SORT_COLUMNS = {"id": "id", "title": "title"}


@contextmanager
def transaction():
    """Yield a connection inside a transaction: commit on success, roll back on any error.

    One connection per call. Postgres connections cost milliseconds rather than SQLite's
    microseconds, which is fine at this size; a pool (psycopg_pool) is the upgrade if the
    request rate ever makes it matter.
    """
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        yield conn


def init() -> None:
    """Create the table, its indexes and the three example rows, each only if missing."""
    with transaction() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            " id serial PRIMARY KEY,"
            " title text NOT NULL,"
            " done boolean NOT NULL DEFAULT false,"
            " created_at timestamptz NOT NULL DEFAULT now(),"
            " updated_at timestamptz NOT NULL DEFAULT now())"
        )
        # Sorting by title reads straight off this index instead of sorting every row.
        conn.execute("CREATE INDEX IF NOT EXISTS tasks_title ON tasks (title)")
        conn.execute("CREATE INDEX IF NOT EXISTS tasks_done ON tasks (done)")
        # Seeding is all-or-nothing: three rows or none, never one and a crash.
        if conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"] == 0:
            conn.cursor().executemany(
                "INSERT INTO tasks (title, done) VALUES (%s, %s)", SEED
            )


def ping() -> bool:
    """Ask the database to answer one trivial query. This is what GET /health reports on."""
    with transaction() as conn:
        return conn.execute("SELECT 1 AS one").fetchone()["one"] == 1


def list_tasks(done=None, search=None, sort="id", limit=50, offset=0) -> list[dict]:
    """Filter, search and sort in SQL. Python never loops over rows to throw them away.

    ILIKE, not LIKE: SQLite's LIKE ignores case for ASCII and Postgres's does not, so plain
    LIKE here would quietly stop `?search=github` finding "Push it to GitHub".
    """
    where, params = [], []
    if done is not None:
        where.append("done = %s")
        params.append(done)
    if search:
        where.append("title ILIKE %s")
        params.append(f"%{search}%")
    sql = "SELECT * FROM tasks"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {SORT_COLUMNS[sort]} LIMIT %s OFFSET %s"
    with transaction() as conn:
        return conn.execute(sql, (*params, limit, offset)).fetchall()


def get(task_id: int) -> dict | None:
    with transaction() as conn:
        return conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()


def create(title: str, done: bool) -> dict:
    """RETURNING hands back the finished row, so the id never needs a second query."""
    with transaction() as conn:
        return conn.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *", (title, done)
        ).fetchone()


def update(task_id: int, title: str, done: bool | None) -> dict | None:
    """A body without `done` keeps the stored value, so renaming a finished task keeps it done.

    COALESCE does that in the one statement; reading the row first would leave a gap between
    the read and the write. The cast is needed because a bare NULL parameter has no type.
    """
    with transaction() as conn:
        return conn.execute(
            "UPDATE tasks SET title = %s, done = COALESCE(%s::boolean, done),"
            " updated_at = now() WHERE id = %s RETURNING *",
            (title, done, task_id),
        ).fetchone()


def delete(task_id: int) -> bool:
    """True if a row went, False if there was nothing with that id."""
    with transaction() as conn:
        row = conn.execute(
            "DELETE FROM tasks WHERE id = %s RETURNING id", (task_id,)
        ).fetchone()
    return row is not None


def counts() -> dict:
    with transaction() as conn:
        return conn.execute(
            "SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE done) AS done FROM tasks"
        ).fetchone()


def reset() -> list[dict]:
    """Empty the table and seed it again.

    TRUNCATE ... RESTART IDENTITY, not DELETE: a Postgres sequence keeps counting after a
    DELETE, so without it the fresh example tasks would come back as ids 4, 5, 6.
    """
    with transaction() as conn:
        conn.execute("TRUNCATE tasks RESTART IDENTITY")
    init()
    return list_tasks()
