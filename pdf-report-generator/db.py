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
    created_at TEXT NOT NULL,
    min_rating INTEGER NOT NULL DEFAULT 1
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
TOTAL_BOOKS = "SELECT COUNT(*) AS total_books FROM books WHERE rating >= ?"

AVERAGE_PRICE = "SELECT ROUND(AVG(price), 2) AS average_price FROM books WHERE rating >= ?"

TOP_5_EXPENSIVE = """
SELECT title, price, rating
FROM books
WHERE rating >= ?
ORDER BY price DESC
LIMIT 5
"""

BY_RATING = """
SELECT rating, COUNT(*) AS books, ROUND(AVG(price), 2) AS average_price
FROM books
WHERE rating >= ?
GROUP BY rating
ORDER BY rating
"""

ALL_BOOKS = "SELECT title, price, rating, url FROM books WHERE rating >= ? ORDER BY title"


def get_report_data(min_rating: int = 1) -> dict:
    """Everything the report needs, in one object, from one connection.

    min_rating is bound as a parameter, never formatted into the SQL string.
    """
    with connect() as connection:
        def rows(sql):
            return [dict(row) for row in connection.execute(sql, (min_rating,)).fetchall()]

        total = connection.execute(TOTAL_BOOKS, (min_rating,)).fetchone()["total_books"]
        average = connection.execute(AVERAGE_PRICE, (min_rating,)).fetchone()["average_price"]
        return {
            "total_books": total,
            "average_price": average or 0.0,
            "min_rating": min_rating,
            "top_5_expensive": rows(TOP_5_EXPENSIVE),
            "by_rating": rows(BY_RATING),
            "all_books": rows(ALL_BOOKS),
        }


def save_report(report_id: str, path: str, created_at: str, min_rating: int = 1) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO reports (id, path, created_at, min_rating) VALUES (?, ?, ?, ?)",
            (report_id, path, created_at, min_rating),
        )


def get_report(report_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT id, path, created_at FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
    return dict(row) if row else None


def report_made_on(day: str, min_rating: int = 1) -> dict | None:
    """The first report generated on a day for this filter, if there is one.

    A report of four-star books is a different report from one of every book, so the
    once-a-day rule is per filter rather than per day.
    """
    with connect() as connection:
        row = connection.execute(
            "SELECT id, path, created_at FROM reports "
            "WHERE date(created_at) = ? AND min_rating = ? ORDER BY created_at LIMIT 1",
            (day, min_rating),
        ).fetchone()
    return dict(row) if row else None


def list_reports() -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, created_at, min_rating FROM reports ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]
