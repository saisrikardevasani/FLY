# Prompt v1

Written from memory before generating anything, without re-reading the assignment brief. The
generated code goes in this folder and is never edited afterwards.

---

Build me a small Python service that turns rows in a database into a PDF report. Use FastAPI,
SQLite through the standard library's `sqlite3`, and Playwright to produce the PDF.

**The data.** A SQLite file `report.db` with one table `books`: an integer id, a title, a price
as a real number, a rating as an integer from 1 to 5, and a url. Write a seed script that reads
a JSON file of books and fills the table. Each book in the JSON has a `title`, a `price_gbp`
number, a `rating_text` which is the word One, Two, Three, Four or Five, and a `product_url`.
Running the seed script twice must leave the same number of rows, not double them.

**The aggregations.** One function that returns a single object holding four things: the total
number of books, the average price, the five most expensive books, and a count of books grouped
by star rating. Write them as SQL, not as Python loops over every row.

**The document.** Build an HTML page from that object with a title, today's date, the two
totals, a small table of the top five, and a long table listing every book. Render it with
Playwright: launch headless Chromium, set the page content, and print to A4 with backgrounds
turned on. Save it under `reports/`.

**The endpoints.**

- `GET /health` returns `{"status": "ok"}`.
- `POST /reports` runs the whole pipeline: query, render the PDF to `reports/<id>.pdf`, insert
  a row into a `reports` table holding the id, the file path and a created-at timestamp, and
  return `201` with the id and a link to the file.
- `GET /reports/{id}` returns that row with its link, or `404` if there is no such report.
- `GET /reports/{id}/file` serves the actual PDF from disk with the right content type.

**The once-a-day rule.** If a report has already been generated today, `POST /reports` must not
generate a second one. Return the existing id and link with `200` instead of `201`. Accept
`{"force": true}` in the body to override that and generate a fresh one anyway.

Note that Playwright's synchronous API cannot run inside a running asyncio event loop, so the
endpoint that renders needs to be a normal `def` rather than `async def`.

Give me the commands to seed the database and run the API.
