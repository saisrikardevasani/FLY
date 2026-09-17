# Prompt v1, written from memory before generating anything

I have a working to-do API in Python 3.11 using FastAPI. Right now it keeps its tasks in a
module-level Python list, so everything is lost when the server restarts. Rewrite the storage so
the tasks live in a SQLite database instead. Use the `sqlite3` module from the standard library,
not an ORM.

The database file is called `tasks.db` and sits next to the code. Do not commit it or assume it
exists: the app must create it on startup if it is missing. Create a table called `tasks` if it
does not already exist, with three columns: `id`, an integer primary key that SQLite assigns
itself, `title`, text and required, and `done`, stored as an integer 0 or 1 because SQLite has
no boolean type. Convert `done` back to a JSON true/false in the responses.

Seed exactly three example tasks, and only when the table is empty. Count the rows first and
insert only if the count is zero. Restarting the server five times must still leave three rows,
not fifteen.

Keep these five endpoints behaving exactly as they do now. Nothing about the request or response
shapes changes; only where the data is kept changes.

- `GET /tasks` returns a JSON array of every task, status 200.
- `GET /tasks/{id}` returns one task, status 200, or 404 if there is no task with that id.
- `POST /tasks` takes `{"title": "..."}` and optionally `"done"`, lets the database assign the
  id, and returns the created task with status 201. A missing title, an empty title or a title
  that is only whitespace is a 400.
- `PUT /tasks/{id}` replaces the title and optionally `done`, returns the updated task with
  status 200. An unknown id is 404 and an invalid body is 400. If the body has no `done` field,
  keep whatever value is already stored, do not reset it to false.
- `DELETE /tasks/{id}` removes the task and returns 204 with an empty body. An unknown id
  is 404.

Every error response, whatever the status code, must be a JSON object of exactly this shape:
`{"error": "some message"}`. FastAPI's default is `{"detail": ...}` and 422 for a bad body, so
add exception handlers that convert both a raised HTTPException and a Pydantic validation error
into that envelope, mapping the validation error to 400 rather than 422.

Every value that comes from a request must reach SQLite as a `?` placeholder parameter, never
by string formatting or concatenation into the SQL text. That applies to ids, titles and the
done flag.

Keep it small and readable, and put the SQL in one place rather than spreading it through the
route functions.
