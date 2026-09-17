"""Fill report.db from the books my A9 scraper validated.

Safe to run twice: it clears the table first, so the row count stays at 60 rather
than doubling.
"""

import json
from pathlib import Path

import db

BOOKS_JSON = Path(__file__).resolve().parent.parent / "scraper" / "output" / "books.json"

# The site writes the star count as a word. The report wants to sort and group on it.
RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def rows_from(path: Path) -> list[tuple]:
    books = json.loads(path.read_text(encoding="utf-8"))
    return [
        (book["title"], book["price_gbp"], RATINGS[book["rating_text"]], book["product_url"])
        for book in books
    ]


def seed() -> int:
    if not BOOKS_JSON.exists():
        raise SystemExit(
            f"No scraped books at {BOOKS_JSON}. Run the A9 scraper first: "
            f"cd ../scraper && .venv/bin/python src/main.py"
        )

    db.init()
    rows = rows_from(BOOKS_JSON)
    with db.connect() as connection:
        # Clearing first is what makes a second run leave 60 rows rather than 120.
        connection.execute("DELETE FROM books")
        connection.executemany(
            "INSERT INTO books (title, price, rating, url) VALUES (?, ?, ?, ?)", rows
        )
    return len(rows)


if __name__ == "__main__":
    count = seed()
    with db.connect() as connection:
        total = connection.execute("SELECT COUNT(*) AS n FROM books").fetchone()["n"]
    print(f"seeded {count} books, table now holds {total}")
