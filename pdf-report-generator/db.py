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
"""


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA)
