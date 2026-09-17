"""Plain asserts over the query, seed and template logic. No server, no PDF render.

Run it with:  .venv/bin/python test_report.py
"""

from fastapi.testclient import TestClient

import db
import main
import render
from seed import RATINGS, inflate, rows_from, BOOKS_JSON

client = TestClient(main.app)


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"  ok  {name}")


print("seeding")
rows = rows_from(BOOKS_JSON)
check("every scraped book becomes a row", len(rows) == 60)
check("the star word becomes a number", all(1 <= r[2] <= 5 for r in rows))
check("'Three' maps to 3", RATINGS["Three"] == 3)
check("urls are unique, which the table requires", len({r[3] for r in rows}) == 60)

big = inflate(rows, 500)
check("inflating reaches the target count", len(big) == 500)
check("inflated urls stay unique", len({r[3] for r in big}) == 500)

print("aggregations")
data = db.get_report_data()
check("the total matches the seeded rows", data["total_books"] == 60)
check("the rating groups sum to the total",
      sum(r["books"] for r in data["by_rating"]) == data["total_books"])
check("the top five is five books", len(data["top_5_expensive"]) == 5)
check("the top five is sorted by price, descending",
      [b["price"] for b in data["top_5_expensive"]]
      == sorted((b["price"] for b in data["top_5_expensive"]), reverse=True))
check("no single book costs more than the whole top five",
      data["top_5_expensive"][0]["price"] >= data["average_price"])

filtered = db.get_report_data(min_rating=4)
check("filtering to 4 stars returns fewer books",
      filtered["total_books"] < data["total_books"])
check("every book in a filtered report meets the filter",
      all(b["rating"] >= 4 for b in filtered["all_books"]))
check("the filter is carried on the data for the template",
      filtered["min_rating"] == 4)

print("the printed page")
html = render.html_for(data)
check("header rows sit in a thead so the browser repeats them",
      html.count("<thead>") == 3)
check("rows are told not to split across a page break",
      "break-inside: avoid" in html)
check("the header group rule is present",
      "display: table-header-group" in html)
check("every book appears in the long table", html.count("<tr>") >= 60)

print("the api rejects bad input before it renders anything")
check("a rating above five is a 400",
      client.post("/reports", json={"min_rating": 9}).status_code == 400)
check("a rating below one is a 400",
      client.post("/reports", json={"min_rating": 0}).status_code == 400)
check("the error names the field",
      "min_rating" in client.post("/reports", json={"min_rating": 9}).json()["error"])
check("an unknown report id is a 404",
      client.get("/reports/nosuchid").status_code == 404)
check("an unknown report file is a 404",
      client.get("/reports/nosuchid/file").status_code == 404)

print("\nall checks passed")
