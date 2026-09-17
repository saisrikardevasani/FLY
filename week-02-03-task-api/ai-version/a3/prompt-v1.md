# Prompt v1

Written from memory after finishing stages 0 to 5 by hand, without the assignment brief open.
Nothing below is copied from it.

---

I have a small to-do API written in Python with FastAPI. It currently stores its tasks in a
SQLite file next to the code. Move it onto PostgreSQL running in Docker, and make the whole
thing start with one command.

Please produce a complete, working project:

**The database.** PostgreSQL, running as a container from the official image. I do not want to
install Postgres on my machine. There is one table, `tasks`, with an `id` that the database
hands out itself, a `title` that is text and required, and a `done` flag that is a real
boolean. Create the table on startup if it is not already there. Seed exactly three example
tasks, but only when the table is empty, so restarting the app does not keep adding rows.

**The driver and the queries.** Use psycopg. Every value that comes from a request must travel
as a query parameter, never glued into the SQL string. Keep all the SQL in one module so the
routes do not contain any.

**The endpoints.** Five of them, on port 3000, and their behaviour must not change from what I
have now:

- `GET /tasks` lists every task.
- `GET /tasks/{id}` returns one, or 404 if there is no such id.
- `POST /tasks` takes `{"title": "..."}` and optionally `"done"`, returns 201 with the created
  task including its new id. A missing, empty or whitespace-only title is a 400.
- `PUT /tasks/{id}` replaces the title and optionally `done`, returns 200 with the updated
  task, 404 for an unknown id, 400 for an invalid body. If the body has no `done`, the stored
  value must be left as it is.
- `DELETE /tasks/{id}` returns 204 with an empty body, or 404 for an unknown id.

Every error response is JSON in the shape `{"error": "some message"}`, including the 400s and
the 404s. Not FastAPI's default `detail` shape.

**The password.** The database password must not appear in any file I commit. Put the
connection string in a `.env` file, git-ignore it, and commit a `.env.example` with the same
keys so someone else knows what to set.

**Persistence.** The rows must survive the containers being destroyed and recreated, so put the
Postgres data on a named volume.

**One command.** A `Dockerfile` for the app and a `docker compose` file with the app and the
database as two services, so that `docker compose up` starts both and the API answers on
http://localhost:3000. Inside compose the app should reach the database by its service name.

Give me every file: the app, the Dockerfile, the compose file, `.env.example`, a `.gitignore`
and `requirements.txt`.
