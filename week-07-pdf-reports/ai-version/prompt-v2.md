# Prompt v2, the rematch

Everything in prompt-v1.md, plus the four things v1 got wrong or ignored. Written after running
v1 and reading its PDF, before regenerating.

---

Same service as before, with these additions.

**Print CSS, or the long table breaks.** A table that runs over several pages needs two rules or
the document is wrong in ways you only see after printing it. Put the header row of every table
inside a real `<thead>` and add `thead { display: table-header-group; }`, so the browser repeats
the column headings at the top of every page. Without it the headings appear once and every page
after the first is a column of numbers with nothing saying what they are, which is exactly what
your last version produced. Add `tr { break-inside: avoid; }` so a tall row is moved to the next
page whole rather than sliced through the middle by the page edge.

**The second request really must answer 200.** I asked for this last time and the code returned
201 both times, because the status code is declared once on the route decorator and returning a
plain dictionary cannot override it. Return an explicit `JSONResponse(status_code=200, ...)` for
the existing report, and let the newly generated one keep the 201.

**Do not put the file's path in the response.** Store the file name rather than an absolute path,
and resolve it against the reports directory when serving. An absolute path pins the database to
one machine and one home directory, and telling a caller that their report lives at
`/Users/somebody/...` tells them about your filesystem and nothing they need. The response should
carry the id, the created-at time and the link, and nothing else.

**Timestamps are UTC and timezone aware.** Use `datetime.now(timezone.utc)`, not
`datetime.now()`. Also set a `content-disposition` filename on the download so the file arrives
as something like `bookstore-report-2026-09-17.pdf` rather than a hex id.

Everything else stays the same: the seed that is safe to run twice, the four aggregations in SQL,
A4 with backgrounds, the four endpoints, the once-a-day rule and its `force` override.
