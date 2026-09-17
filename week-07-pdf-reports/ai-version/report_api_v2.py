"""PDF report generator, v2. Generated from prompt-v2.md. Not edited afterwards."""

import datetime
import json
import os
import sqlite3
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from playwright.sync_api import sync_playwright
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "report.db"
REPORTS_DIR = BASE_DIR / "reports"
BOOKS_JSON = BASE_DIR.parent.parent / "scraper" / "output" / "books.json"

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

app = FastAPI(title="PDF Report Generator")


class ReportRequest(BaseModel):
    force: bool = False


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            rating INTEGER NOT NULL,
            url TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def seed_database():
    """Read books.json and fill the books table. Safe to run twice."""
    init_db()
    with open(BOOKS_JSON) as f:
        books = json.load(f)

    conn = get_db()
    conn.execute("DELETE FROM books")
    for book in books:
        conn.execute(
            "INSERT INTO books (title, price, rating, url) VALUES (?, ?, ?, ?)",
            (book["title"], book["price_gbp"],
             RATING_WORDS[book["rating_text"]], book["product_url"]),
        )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    conn.close()
    return count


def get_report_data():
    conn = get_db()
    total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    average_price = conn.execute("SELECT AVG(price) FROM books").fetchone()[0]
    top_5 = [dict(r) for r in conn.execute(
        "SELECT title, price, rating FROM books ORDER BY price DESC LIMIT 5"
    ).fetchall()]
    by_rating = [dict(r) for r in conn.execute(
        "SELECT rating, COUNT(*) as count FROM books GROUP BY rating ORDER BY rating"
    ).fetchall()]
    all_books = [dict(r) for r in conn.execute(
        "SELECT title, price, rating FROM books ORDER BY title"
    ).fetchall()]
    conn.close()

    return {
        "total_books": total_books,
        "average_price": round(average_price, 2) if average_price else 0,
        "top_5": top_5,
        "by_rating": by_rating,
        "all_books": all_books,
    }


def build_html(data):
    today = datetime.date.today().strftime("%B %d, %Y")

    top_rows = "".join(
        f"<tr><td>{b['title']}</td><td>{b['rating']}</td>"
        f"<td>£{b['price']:.2f}</td></tr>"
        for b in data["top_5"]
    )
    rating_rows = "".join(
        f"<tr><td>{r['rating']} stars</td><td>{r['count']}</td></tr>"
        for r in data["by_rating"]
    )
    book_rows = "".join(
        f"<tr><td>{b['title']}</td><td>{b['rating']}</td>"
        f"<td>£{b['price']:.2f}</td></tr>"
        for b in data["all_books"]
    )

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            h1 {{ color: #333; }}
            .summary {{ background: #f5f5f5; padding: 15px; margin: 20px 0; }}
            .stat {{ display: inline-block; margin-right: 40px; }}
            .stat-value {{ font-size: 24px; font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th {{ background: #333; color: white; padding: 8px; text-align: left; }}
            td {{ padding: 8px; border-bottom: 1px solid #ddd; }}

            /* Print rules: repeat the column headings on every page, and never let a
               row be sliced in half by the page edge. */
            thead {{ display: table-header-group; }}
            tr {{ break-inside: avoid; }}
        </style>
    </head>
    <body>
        <h1>Book Report</h1>
        <p>Generated on {today}</p>

        <div class="summary">
            <div class="stat">
                <div>Total Books</div>
                <div class="stat-value">{data['total_books']}</div>
            </div>
            <div class="stat">
                <div>Average Price</div>
                <div class="stat-value">£{data['average_price']:.2f}</div>
            </div>
        </div>

        <h2>Top 5 Most Expensive</h2>
        <table>
            <thead><tr><th>Title</th><th>Rating</th><th>Price</th></tr></thead>
            <tbody>{top_rows}</tbody>
        </table>

        <h2>Books by Rating</h2>
        <table>
            <thead><tr><th>Rating</th><th>Count</th></tr></thead>
            <tbody>{rating_rows}</tbody>
        </table>

        <h2>All Books</h2>
        <table>
            <thead><tr><th>Title</th><th>Rating</th><th>Price</th></tr></thead>
            <tbody>{book_rows}</tbody>
        </table>
    </body>
    </html>
    """


def generate_pdf(html, output_path):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.pdf(path=str(output_path), format="A4", print_background=True)
        browser.close()
    return output_path


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/reports", status_code=201)
def create_report(request: ReportRequest = ReportRequest()):
    conn = get_db()
    today = datetime.date.today().isoformat()

    if not request.force:
        existing = conn.execute(
            "SELECT id FROM reports WHERE date(created_at) = ?", (today,)
        ).fetchone()
        if existing:
            conn.close()
            # The decorator declares 201, so the only way to answer 200 is an explicit
            # response object.
            return JSONResponse(
                status_code=200,
                content={"id": existing["id"],
                         "file": f"/reports/{existing['id']}/file"},
            )

    report_id = str(uuid.uuid4())[:8]
    filename = f"{report_id}.pdf"
    generate_pdf(build_html(get_report_data()), REPORTS_DIR / filename)

    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO reports (id, path, created_at) VALUES (?, ?, ?)",
        (report_id, filename, created_at),
    )
    conn.commit()
    conn.close()

    return {"id": report_id, "file": f"/reports/{report_id}/file"}


@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "file": f"/reports/{report_id}/file",
    }


@app.get("/reports/{report_id}/file")
async def get_report_file(report_id: str):
    conn = get_db()
    row = conn.execute("SELECT path FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    created = conn2 = None  # no extra query needed, the name is derived from the id
    return FileResponse(
        REPORTS_DIR / row["path"],
        media_type="application/pdf",
        filename=f"bookstore-report-{datetime.date.today().isoformat()}.pdf",
    )


if __name__ == "__main__":
    print(f"Seeded {seed_database()} books")
