"""Fill report.db from the books my A9 scraper validated.

Safe to run twice: it clears the table first, so the row count stays at 60 rather
than doubling.
"""

import json
from pathlib import Path

import db

BOOKS_JSON = Path(__file__).resolve().parent.parent / "week-05-scraper" / "output" / "books.json"

# The site writes the star count as a word. The report wants to sort and group on it.
RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def rows_from(path: Path) -> list[tuple]:
    books = json.loads(path.read_text(encoding="utf-8"))
    return [
        (book["title"], book["price_gbp"], RATINGS[book["rating_text"]], book["product_url"])
        for book in books
    ]


def inflate(rows: list[tuple], target: int) -> list[tuple]:
    """Repeat the real books until there are `target` of them, keeping urls unique.

    Only used for the big-table experiment, to see what a long report costs.
    """
    out = []
    while len(out) < target:
        for title, price, rating, url in rows:
            if len(out) >= target:
                break
            n = len(out)
            out.append((f"{title} (copy {n})", price, rating, f"{url}#{n}"))
    return out


def seed(target: int | None = None) -> int:
    if not BOOKS_JSON.exists():
        raise SystemExit(
            f"No scraped books at {BOOKS_JSON}. Run the A9 scraper first: "
            f"cd ../week-05-scraper && .venv/bin/python src/main.py"
        )

    db.init()
    rows = rows_from(BOOKS_JSON)
    if target:
        rows = inflate(rows, target)
    with db.connect() as connection:
        # Clearing first is what makes a second run leave 60 rows rather than 120.
        connection.execute("DELETE FROM books")
        connection.executemany(
            "INSERT INTO books (title, price, rating, url) VALUES (?, ?, ?, ?)", rows
        )
    return len(rows)


if __name__ == "__main__":
    import sys

    target = int(sys.argv[1]) if len(sys.argv) > 1 else None
    count = seed(target)
    with db.connect() as connection:
        total = connection.execute("SELECT COUNT(*) AS n FROM books").fetchone()["n"]
    print(f"seeded {count} books, table now holds {total}")
