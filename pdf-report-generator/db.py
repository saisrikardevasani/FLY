"""Everything that talks to report.db lives here. No SQL anywhere else."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "report.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY,
    title  TEXT    NOT NULL,
    price  REAL    NOT NULL,
    rating INTEGER NOT NULL,
    url    TEXT    NOT NULL UNIQUE
);

-- The bookkeeping for generated reports lives next to the data they describe.
CREATE TABLE IF NOT EXISTS reports (
    id         TEXT PRIMARY KEY,
    path       TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA)


# The four questions the report answers. Kept as named constants so the README can quote
# the exact SQL that produced the numbers in the PDF.
TOTAL_BOOKS = "SELECT COUNT(*) AS total_books FROM books"

AVERAGE_PRICE = "SELECT ROUND(AVG(price), 2) AS average_price FROM books"

TOP_5_EXPENSIVE = """
SELECT title, price, rating
FROM books
ORDER BY price DESC
LIMIT 5
"""

BY_RATING = """
SELECT rating, COUNT(*) AS books, ROUND(AVG(price), 2) AS average_price
FROM books
GROUP BY rating
ORDER BY rating
"""

ALL_BOOKS = "SELECT title, price, rating, url FROM books ORDER BY title"


def get_report_data() -> dict:
    """Everything the report needs, in one object, from one connection."""
    with connect() as connection:
        def rows(sql):
            return [dict(row) for row in connection.execute(sql).fetchall()]

        return {
            "total_books": connection.execute(TOTAL_BOOKS).fetchone()["total_books"],
            "average_price": connection.execute(AVERAGE_PRICE).fetchone()["average_price"],
            "top_5_expensive": rows(TOP_5_EXPENSIVE),
            "by_rating": rows(BY_RATING),
            "all_books": rows(ALL_BOOKS),
        }


def save_report(report_id: str, path: str, created_at: str) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO reports (id, path, created_at) VALUES (?, ?, ?)",
            (report_id, path, created_at),
        )


def get_report(report_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT id, path, created_at FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
    return dict(row) if row else None


def report_made_on(day: str) -> dict | None:
    """The first report generated on a given day, if there is one."""
    with connect() as connection:
        row = connection.execute(
            "SELECT id, path, created_at FROM reports WHERE date(created_at) = ? "
            "ORDER BY created_at LIMIT 1",
            (day,),
        ).fetchone()
    return dict(row) if row else None


def list_reports() -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, path, created_at FROM reports ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]
