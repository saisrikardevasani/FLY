# PDF report generator (FlyRank A8)

Turns rows in a SQLite table into a printable A4 document: query, render a web page, and ask a
headless browser to print it. The API generates the report, records it, and serves the file by
link.

![Page 1 of a generated report](docs/report-page-1.png)

## The dataset: option B, the bookstore

This uses the 60 validated books my A9 scraper collected from books.toscrape.com, rather than
inventing 200 random orders. `seed.py` reads [`../scraper/output/books.json`](../scraper/output/books.json)
and loads it into `report.db`, converting the star rating from the word the site publishes
("Three") into a number the report can group and sort on (3).

## Run it

Python 3.11. From this `pdf-report-generator/` folder:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium

.venv/bin/python seed.py                          # fills report.db with the 60 books
.venv/bin/uvicorn main:app --port 8100            # the API
```

Then `curl -X POST http://localhost:8100/reports`. The tests need no server and no browser:

```bash
.venv/bin/python test_report.py
```

Running `seed.py` twice leaves 60 rows rather than 120, because it clears the table before
inserting. `report.db` and `reports/` are both git-ignored: generated artefacts do not belong in
git, and the seed script is their recipe.

## Endpoints

| Endpoint | Does | Answers |
| --- | --- | --- |
| `GET /health` | liveness | `200 {"status": "ok"}` |
| `POST /reports` | runs the whole pipeline and records the file | `201` + `{"id", "file"}`, or `200` with the existing id if today already has one |
| `GET /reports` | every report generated, newest first | `200` + a count and a list |
| `GET /reports/{id}` | one report's record and its link | the row, or `404` |
| `GET /reports/{id}/file` | the PDF itself | `application/pdf`, or `404` |

`POST /reports` accepts an optional body: `{"force": true}` to generate a fresh one on a day
that already has a report, and `{"min_rating": 4}` to report only on books rated four stars and
above. A `min_rating` outside 1 to 5 is a `400`.

## The queries

Four questions, answered in SQL rather than in Python. These are the exact strings in
[`db.py`](db.py), and the numbers in the screenshot above came out of them:

```sql
-- how many books
SELECT COUNT(*) AS total_books FROM books WHERE rating >= ?;

-- what they cost on average
SELECT ROUND(AVG(price), 2) AS average_price FROM books WHERE rating >= ?;

-- the five priciest
SELECT title, price, rating
FROM books
WHERE rating >= ?
ORDER BY price DESC
LIMIT 5;

-- the shape of the catalogue, by star rating
SELECT rating, COUNT(*) AS books, ROUND(AVG(price), 2) AS average_price
FROM books
WHERE rating >= ?
GROUP BY rating
ORDER BY rating;
```

`min_rating` is bound as a parameter every time, never formatted into the string.

The numbers agree with each other, which is the check worth doing: the rating groups hold
15 + 8 + 13 + 10 + 14 = 60 books, and the total says 60.

## Proof: generate, then download

```
$ curl -s -o out.json -w 'status=%{http_code}  total=%{time_total}s\n' \
    -X POST http://localhost:8100/reports
status=201  total=0.274484s
{"id":"54aa635b0184","file":"/reports/54aa635b0184/file"}

$ curl -X POST http://localhost:8100/reports          # the same request again
{"id":"54aa635b0184","file":"/reports/54aa635b0184/file"}   [200]

$ curl -s http://localhost:8100/reports/54aa635b0184
{"id":"54aa635b0184","created_at":"2026-09-17T11:21:49.581341+00:00",
 "file":"/reports/54aa635b0184/file"}

$ curl -o my-report.pdf .../reports/54aa635b0184/file
content-type: application/pdf
content-disposition: attachment; filename="bookstore-report-2026-09-17.pdf"
content-length: 62149

$ file my-report.pdf
my-report.pdf: PDF document, version 1.4, 3 pages
```

Only the last of those moves megabytes. The other three answer in a few dozen bytes and hand
over a link, which is what "store and link" means in practice.

## The page-break trap

A long table breaks badly by default, and the first render proved it. Reading the text back out
of the PDF page by page:

```
page 1: RATING header present = True
page 2: RATING header present = False
page 3: RATING header present = False
```

The header row appeared once and never again, so pages 2 and 3 were columns of numbers with
nothing saying what they were. Two rules fix it:

```css
thead { display: table-header-group; }   /* repeat the header on every page */
tr    { break-inside: avoid; }           /* never slice a row down the middle */
```

with the header rows moved into a real `<thead>`. After that, all three pages carry the header.

No row happened to land on a page boundary in the 60-book report, so the second rule was not
exercised there. The 5,000-row version below is where it earns its place.

## When would you move this work out of the request?

The endpoint does everything inline: query, launch a browser, render, write the file, insert a
row. For 60 books that costs 0.27 seconds and one user clicking one button, which is fine. I
would move it into a background job at the point where the work either outlasts a sensible HTTP
timeout or arrives in parallel: a report large enough to take tens of seconds, or more than a
handful of users generating at once, because every in-flight request is holding a browser
process and a connection open, and a client that disconnects halfway leaves that work orphaned
with nobody to hand the result to. A7's job queue is exactly the shape that fixes it: return
`202` with an id straight away and let a worker render.

## Ask twice, get one

Two rapid POSTs return the same id and `reports/` gains exactly one file. The first answers
`201`, the second `200`, and `{"force": true}` opts out:

```
POST /reports                     -> {"id":"52a2fd6f8c23", ...}  [201]
POST /reports                     -> {"id":"52a2fd6f8c23", ...}  [200]
files in reports/: 1
POST /reports {"force":true}      -> {"id":"52c8c99cac88", ...}  [201]
files in reports/: 2
```

What the check protects against is the double-click: a user pressing "Generate report" twice, or
a browser retrying a request that already succeeded, producing two identical files and two
identical records for the same day. The version of this that costs money is anything with a side
effect attached, where a missing check means charging a customer's card twice for one order, or
emailing every subscriber a second copy of the same newsletter because the send job ran twice.

The rule is per filter rather than per day: a four-star report and an everything report are
different documents, so `min_rating` is stored on the row and the daily check matches on it.

## Extras

**A parameterised report.** `{"min_rating": 4}` filters every query. A rating outside 1 to 5 is
rejected with a `400` before anything renders, and every error from this API has the same shape,
`{"error": "..."}`.

**The control panel.** `GET /reports` lists everything generated, newest first, with links and
the filter each one used.

**Nice filenames.** The download arrives as `bookstore-report-2026-09-17.pdf` rather than a hex
id, set through `content-disposition` while the file on disk keeps its id.

**Brand colours and a repeating footer.** Every page carries "Page N of M", filled in by Chromium
through `display_header_footer` rather than counted by hand.

**The big-table experiment.** `python seed.py 5000` inflates the real books to 5,000 rows with
unique URLs, and the same endpoint generates over them:

| Rows | Pages | POST took |
| --- | --- | --- |
| 60 | 3 | 0.24s |
| 5,000 | 179 | 0.56s |

Those are warm timings, with Chromium already launched once. The very first request after a
fresh clone took 1.12 seconds, which is the browser starting from cold.

Two things that says. First, the work is not linear in rows: 83 times the data cost about twice
the time, because most of the 0.24 seconds is launching Chromium rather than laying out rows, so
the fixed cost dominates until the document gets genuinely large. Second, 0.56 seconds inside a
request is survivable and a 179-page report is not the limit: the same endpoint on a dataset ten
times larger, or twenty users pressing the button together, is twenty browsers launching at once
on one machine. That is the point where this belongs in a queue, not in a request.

The 179-page run also did what the 60-book one could not, which is exercise the print CSS
properly:

```
pages with text: 179
pages carrying the repeated table header: 179/179
pages carrying the page-number footer:    179/179
rows whose text is split across a page break: 0
```

## The tests

`test_report.py` is 23 plain asserts and needs no server, no browser and no network. It covers
the rating conversion, unique URLs, the inflate helper, every aggregation including whether the
rating groups still sum to the total, the filter, the presence of both print rules in the
generated HTML, and the API's 400s and 404s. It deliberately never posts a valid report, because
that would launch a browser, and a test suite that takes a second is one you actually run.

## An honest limitation

The once-a-day check reads the database and then writes, with no lock between the two. Two
requests arriving in the same millisecond can both find nothing and both generate. SQLite would
let a `UNIQUE (date(created_at), min_rating)` constraint settle it properly, and this does not
have one.

## AI vs me

I built stages 0 to 6 by hand first, which is the only reason this section is a code review
rather than a demonstration. The prompt was written from memory before anything was generated,
the generated code lives in [`ai-version/`](ai-version/) and has not been edited since, and
every line below comes from running it on the same 60 books.

### The prompt

[`ai-version/prompt-v1.md`](ai-version/prompt-v1.md) has it in full. It names the schema, the
seed that must be safe to run twice, the four aggregations as SQL, the HTML page, A4 with
backgrounds, all four endpoints, the once-a-day rule with its `force` override, and the fact that
Playwright's sync API cannot run inside an async endpoint.

### Checkpoint results

| Checkpoint | Mine | AI v1 | AI v2 |
| --- | --- | --- | --- |
| `POST /reports` returns 201 and a link | 0.27s | 0.25s | yes |
| `GET /reports/{id}` returns the row, unknown id is 404 | yes | yes | yes |
| the file downloads and opens as a real PDF | 3 pages | 3 pages | 3 pages |
| the second POST today returns the same id | yes | yes | yes |
| ...and answers **200**, not 201 | yes | **no, 201** | yes |
| exactly one file in `reports/` after two POSTs | yes | yes | yes |
| the table header repeats on every page | 3/3 | **1/3** | 3/3 |
| the response keeps the server's paths to itself | yes | **no** | yes |

### What the AI got wrong

**Its PDF walked straight into the page-break trap.** The document is three pages and the column
headings appear on page one only:

```
AI version PDF: 3 pages
  page 1: table header present = True
  page 2: table header present = False
  page 3: table header present = False
```

Pages two and three are a list of titles and numbers with nothing saying which column is the
price and which is the rating. Neither `display: table-header-group` nor `break-inside: avoid`
appears anywhere in its code, because neither appeared anywhere in my prompt.

**It ignored an instruction I did give it.** My prompt said, in those words, to return the
existing report with 200 instead of 201. Both POSTs answered 201:

```
POST /reports -> {"id":"303c5381", ...}  [201]
POST /reports -> {"id":"303c5381", ...}  [201]
```

The rule itself worked: same id, one file. But `status_code=201` is declared once on the route
decorator, and returning a plain dictionary cannot override it. To answer 200 you have to return
an explicit response object, and it did not. A caller cannot tell "I made this for you" from
"you already had one", which is the entire point of the two codes.

**It handed the caller its own filesystem.** `GET /reports/{id}` returned the whole row,
including the stored path:

```json
{"id":"303c5381",
 "path":"/Users/saisrikardevasani/Downloads/FLY/task-api/pdf-report-generator/ai-version/reports/303c5381.pdf",
 ...}
```

That tells a caller the operating system, the user's name and the deployment layout, and none of
it is anything they can use. It also pins the database to one machine: move the folder and every
stored path is wrong. I had written the same bug and caught it at stage 4, which is the only
reason I spotted it here so quickly.

**Naive timestamps again.** `datetime.datetime.now()` with no timezone, so `created_at` came back
as `2026-09-17T12:23:55` for a report generated at 11:23 UTC, and no download filename.

### What the AI did better

**It closed its database connections and I did not.** Every one of its functions ends with
`conn.close()`. I had written `with connect() as connection:` throughout, which reads like it
closes and does not: sqlite3's context manager commits or rolls back the transaction and leaves
the connection open. Checked directly:

```
after the 'with' block the connection is STILL OPEN: sqlite3's context manager
manages the transaction, not the connection. It never closes anything.
```

In practice mine was collected anyway, because the local variable's refcount hits zero when the
function returns, and a check after a query found zero live connections. So it was not leaking.
But it was relying on CPython's refcounting to do something my code looked like it was doing
itself, which is the kind of thing that stops being true on a different runtime or the day
someone holds a reference. I have made it explicit with a `session()` context manager that
commits and then closes, and the AI's plain `conn.close()` is what pointed at it.

**It kept the whole thing in one file.** For a service this size that is a defensible call and
makes it easier to read end to end. Mine is split across `db.py`, `render.py`, `seed.py` and
`main.py`, which I would still choose, because the SQL and the HTML template are the two parts
most likely to change and they have no business in the same file. It is a real trade rather than
a mistake on either side.

### What my prompt forgot to say

1. **The print CSS.** The whole difficulty of turning a long table into a document, and my prompt
   said "render it to A4" as though that were the hard part. It is not. The hard part is what
   happens at the page boundary, and I did not mention it because I had already solved it hours
   earlier and it no longer felt like a decision.
2. **How to actually return a 200.** I said what the status code should be and not that the
   decorator's `status_code` wins unless you return a response object. A spec that says what
   without saying how, on a point the framework makes awkward, gets ignored.
3. **That paths are internal.** I asked it to store the file path and return "the row", and it
   did exactly that. I never said which fields the caller should see.
4. **Timezones and download filenames.** Not mentioned at all, so not done.

### The rematch

[`ai-version/prompt-v2.md`](ai-version/prompt-v2.md) adds those four points. Regenerated once as
[`report_api_v2.py`](ai-version/report_api_v2.py), and every failing box passes:

```
POST /reports -> {"id":"c16d393d", ...}  [201]
POST /reports -> {"id":"c16d393d", ...}  [200]

GET  /reports/c16d393d
{"id":"c16d393d","created_at":"2026-09-17T11:25:24.888228+00:00",
 "file":"/reports/c16d393d/file"}

content-disposition: attachment; filename="bookstore-report-2026-09-17.pdf"

3 pages
  page 1: table header present = True
  page 2: table header present = True
  page 3: table header present = True
```

One sentence on what changed: naming the two CSS rules and the response object fixed every
defect in one pass, which says the failures were never the model's reasoning, they were four
sentences missing from my specification.
