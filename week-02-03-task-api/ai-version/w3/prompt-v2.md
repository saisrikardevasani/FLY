# Prompt v2, after running v1 and probing it

Everything in [prompt-v1.md](prompt-v1.md) still applies. These paragraphs are what running v1
showed I had left unsaid.

Close every connection you open. `with sqlite3.connect(...) as conn` commits the transaction but
does not close the connection, so a connection opened per request leaks file handles until the
process runs out. Open one connection per request and close it in a `finally`, or use
`contextlib.closing`.

Do not use `AUTOINCREMENT`. Plain `id INTEGER PRIMARY KEY` is enough; SQLite hands out ids from
it, and it avoids the extra `sqlite_sequence` table that `AUTOINCREMENT` creates. Reusing the id
of a deleted row is fine here.

The 404 message must name the id that was not found: `{"error": "Task 42 not found"}`, not a
generic "Task not found". Existing clients match on that string.

There are four more endpoints beyond the five CRUD ones, and they must survive the move to
SQLite as well. `GET /` returns `{"name": ..., "version": ..., "endpoints": [...]}`.
`GET /health` returns `{"status": "ok"}`. `GET /stats` returns `{"total": n, "done": n,
"open": n}` and must compute those with `SELECT COUNT(*)` in SQL rather than counting rows in
Python. `POST /reset` empties the table and seeds it again, returning the seeded tasks.

`GET /tasks` takes four optional query parameters, and all four must be handled by the database
rather than by filtering a list in Python: `?done=true` adds `WHERE done = ?`, `?search=milk`
adds `WHERE title LIKE ?` matching anywhere in the title, `?sort=` accepts only `id` or `title`
and adds `ORDER BY`, and `?limit=` and `?offset=` add `LIMIT ? OFFSET ?` with limit defaulting
to 50 and capped at 100. A column name cannot be a `?` parameter, so `sort` must be restricted
to those two names by the type annotation, not by string checks inside the function.

Add `created_at` and `updated_at` columns, both text, both defaulting to `datetime('now')`, and
set `updated_at` on every update. Add an index on `title`. Both of those go in the same
create-if-missing step as the table.

Switch the database into WAL mode at startup (`PRAGMA journal_mode = WAL`) so that a reader is
never blocked by a writer, and add an exception handler for `sqlite3.OperationalError` that
returns 503 with the same `{"error": ...}` envelope, so a locked database is not a 500 with an
HTML-free "Internal Server Error" body.
