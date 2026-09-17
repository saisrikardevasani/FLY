# Prompt v2

Prompt v1 again, with everything running v1 taught me it had left unsaid. The additions are the
seven paragraphs under "Things v1 did not say", and they are all things I only knew to write
down because I watched the first version fail.

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

**The endpoints.** On port 3000, and their behaviour must not change from what I have now:

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

## Things v1 did not say

**Pin the Postgres image to a major version**, `postgres:17`, not bare `postgres`. The bare tag
now resolves to 18, which changed where it keeps its data and refuses to start against a volume
mounted at `/var/lib/postgresql/data`.

**Wait for the database to be ready, not just started.** `depends_on: [db]` waits for the
container, and Postgres begins accepting connections a second or two later, so an app that
connects during startup loses that race and exits. Give the `db` service a health check using
`pg_isready` and make the app depend on `condition: service_healthy`.

**A database that is unreachable must not kill the app.** If Postgres cannot be reached during
a request, answer `503` with the usual `{"error": "..."}` shape rather than a bare 500, and let
the app recover by itself when the database comes back.

**Exact error text.** A 404 says `Task 999 not found`, with the id in it, not `Task not found`.
A 400 from a missing field names the field: `title: Field required`. Existing clients match on
these strings.

**Four more endpoints**, which the app already has: `GET /` returning a small description,
`GET /health` which runs `SELECT 1` and answers `{"status": "ok", "db": "ok"}`, `GET /stats`
returning `{"total": n, "done": n, "open": n}` counted in SQL, and `POST /reset` which empties
the table and seeds it again with the ids starting from 1 again.

**Five query parameters on `GET /tasks`**, all applied in SQL rather than in Python: `done`,
`search`, `sort` restricted to `id` or `title`, `limit` capped at 100, and `offset`. `search`
must be case-insensitive, so `?search=github` finds `Push it to GitHub`.

**Two timestamp columns**, `created_at` and `updated_at`, both `timestamptz` defaulting to
`now()`, returned in the JSON. A `PUT` moves `updated_at` and leaves `created_at` alone.

Give me every file: the app, the Dockerfile, the compose file, `.env.example`, a `.gitignore`
and `requirements.txt`.
