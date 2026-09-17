# Task API (FlyRank A1 to A3)

A small to-do API built with FastAPI: create, read, update and delete tasks. The five endpoints
have not moved since A1. Where the tasks live has moved three times: a Python list (A1, thrown
away on every restart), a SQLite file (A2), and now a PostgreSQL server of its own (A3). One
command starts the app and that database together.

## Run it

You need Docker, and nothing else. Postgres is never installed on your machine; it arrives as
an image.

```bash
cp .env.example .env && docker compose up
```

That builds the app image, starts Postgres, waits until it is accepting connections, creates
the `tasks` table and seeds the three example tasks. The API answers on
http://localhost:3000 and Swagger UI is at http://localhost:3000/docs.

Measured on a fresh clone of this repo into an empty directory: 9.2 seconds from
`cp .env.example .env && docker compose up` to `GET /tasks` returning the three seeded tasks,
with no database step in between. Docker's layer cache and the `postgres:17` image were already
warm on that machine; the first run anywhere pays for the image pull as well.

`docker compose down` stops both containers and keeps the data. `docker compose down -v` also
deletes the volume, which is the only way to lose it.

### The variables

`.env` is git-ignored and never committed. [`.env.example`](.env.example) is committed with the
same keys, and copying it is the whole setup step:

| Variable | What it is | Value in `.env.example` |
|---|---|---|
| `POSTGRES_USER` | Database user the container creates | `postgres` |
| `POSTGRES_PASSWORD` | That user's password | `dev` |
| `POSTGRES_DB` | Database created on first start | `tasks` |
| `DATABASE_URL` | What the app connects with | `postgresql://postgres:dev@localhost:5432/tasks` |
| `REDIS_URL` | Redis, added in the extras | `redis://localhost:6379` |

Compose reads `.env` to fill in `${POSTGRES_PASSWORD}` and friends, so the password appears in
no committed file. Inside the compose network the app reaches the database at `db:5432`, not
`localhost`, so `compose.yaml` overrides `DATABASE_URL` for the `api` service. The `localhost`
value in `.env` is for the other way of running it, below.

### Running the app outside the container

Useful when you want `--reload`. The `db` service publishes 5432, so start the database only
and point the app at it:

```bash
docker compose up -d db
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload --port 3000
```

Python 3.10 or newer. On 3.9 pip fails on the FastAPI pin with a list of versions and no
explanation; point the first step at a newer interpreter and leave the rest alone.

To run the checks: `.venv/bin/python test_api.py`, which prints `all checks passed`. It calls
`POST /reset` first, so it leaves the table holding the three example tasks.

## The three services

```yaml
services:
  api:     # built from the Dockerfile, uvicorn on 3000
  db:      # the official postgres:17 image, data on a named volume
  redis:   # added in the extras, pinged once at startup, otherwise unused
```

The tag is pinned. `postgres:latest` is 18, which moved its data directory and refuses to start
against a volume mounted where the assignment mounts one:

```
Error: in 18+, these Docker images are configured to store database data in a
       format which is compatible with "pg_ctlcluster" ...
       Counter to that, there appears to be PostgreSQL data in:
         /var/lib/postgresql/data (unused mount/volume)
```

`db` has a health check and `api` waits on `condition: service_healthy` rather than the plain
`depends_on: [db]`. Postgres accepts connections a second or two after the container starts,
and this app creates its table on import, so starting the two at the same moment is a race the
app loses about as often as it wins.

## Why Postgres

- **It is a server, not a file.** Several programs can hold connections at once and Postgres
  arbitrates between them, instead of one writer locking a file for everyone else.
- **It has real types.** `boolean` is a boolean, so `done` no longer travels as 0 and 1 and
  gets converted back on the way out. `timestamptz` keeps the offset.
- **It is what the job actually uses.** The same engine behind a large share of backends.
- **It costs nothing to run.** `docker compose up`, and `down -v` when you want it gone.

The trade is that there is now a second program to start, which is exactly the problem compose
solves.

## Proof: the same responses, now from Postgres

Reads first. Same URLs, same JSON shapes, same status codes as A1 and A2; the rows come off a
Postgres server instead of a file.

```console
$ curl -i http://localhost:3000/tasks
HTTP/1.1 200 OK
content-type: application/json

[{"id":1,"title":"Read the assignment","done":true,"created_at":"2026-08-18T13:59:00.837806+00:00","updated_at":"2026-08-18T13:59:00.837806+00:00"},{"id":2,"title":"Build the CRUD API","done":false,"created_at":"2026-08-18T13:59:00.837806+00:00","updated_at":"2026-08-18T13:59:00.837806+00:00"},{"id":3,"title":"Push it to GitHub","done":false,"created_at":"2026-08-18T13:59:00.837806+00:00","updated_at":"2026-08-18T13:59:00.837806+00:00"}]

$ curl -i -X POST http://localhost:3000/tasks -H "Content-Type: application/json" -d '{"title":"Buy milk"}'
HTTP/1.1 201 Created
content-type: application/json

{"id":4,"title":"Buy milk","done":false,"created_at":"2026-08-18T13:59:36.279057+00:00","updated_at":"2026-08-18T13:59:36.279057+00:00"}

$ curl -i -X POST http://localhost:3000/tasks -H "Content-Type: application/json" -d '{}'
HTTP/1.1 400 Bad Request
content-type: application/json

{"error":"title: Field required"}

$ curl -i -X PUT http://localhost:3000/tasks/4 -H "Content-Type: application/json" -d '{"title":"Buy oat milk","done":true}'
HTTP/1.1 200 OK
content-type: application/json

{"id":4,"title":"Buy oat milk","done":true,"created_at":"2026-08-18T13:59:36.279057+00:00","updated_at":"2026-08-18T13:59:36.298393+00:00"}

$ curl -i -X DELETE http://localhost:3000/tasks/4
HTTP/1.1 204 No Content
content-type: application/json


$ curl -i -X DELETE http://localhost:3000/tasks/4
HTTP/1.1 404 Not Found
content-type: application/json

{"error":"Task 4 not found"}

$ curl -i http://localhost:3000/tasks/999
HTTP/1.1 404 Not Found
content-type: application/json

{"error":"Task 999 not found"}
```

A `PUT` moves `updated_at` and leaves `created_at` alone, which is the pair of timestamps
above: `.279057` for both on create, `.298393` after the update.

The `date`, `server` and `content-length` headers are trimmed out of every response above to
keep it readable.

One shape did change between A2 and A3. SQLite stored the timestamps as text, so they came back
as `"2026-08-18 13:17:40"`; Postgres stores `timestamptz`, so they come back as
`"2026-08-18T13:59:00.837806+00:00"`. `id`, `title` and `done` are byte-for-byte what A1
returned.

### Persistence, the point of the week

Two tasks created, then the whole stack destroyed and rebuilt:

```console
$ curl -s -X POST localhost:3000/tasks -H "Content-Type: application/json" -d '{"title":"Survive a compose down"}'
{"id":4,"title":"Survive a compose down","done":false,"created_at":"2026-08-18T14:02:05.137269+00:00",...}

$ docker compose down
 Container task-api-api-1  Removed
 Container task-api-db-1  Removed
 Network task-api_default  Removed

$ docker compose up -d
$ curl -s localhost:3000/tasks
[... 5 tasks, ids 1 to 5, "Survive a compose down" and "Prove the volume works" still there ...]
```

The containers were deleted, not stopped. The rows survived because they were never in a
container: they are on the named volume `task-api_taskdata`, which `docker compose down` leaves
alone. The timestamps came back identical, which is the giveaway that these are the original
rows rather than a fresh seed.

### The same rows, seen from the database

`docker compose exec db psql -U postgres -d tasks`, then `\dt` and a `SELECT`:

![The tasks table and its five rows in psql](docs/postgres-psql.png)

Ids 4 and 5 in that screenshot are the two tasks that lived through the `down` and `up` above.

## Endpoints

| Method | Path | Does | Success | Errors |
|---|---|---|---|---|
| GET | `/` | What this API is | 200 | |
| GET | `/health` | Liveness check | 200 | |
| GET | `/tasks` | List tasks. Optional `?done=`, `?search=`, `?sort=`, `?limit=`, `?offset=` | 200 | 400 bad query |
| GET | `/tasks/{id}` | One task | 200 | 404 unknown id |
| POST | `/tasks` | Create from `{"title": "Buy milk"}` | 201 | 400 missing or empty title |
| PUT | `/tasks/{id}` | Replace `title`, optionally `done` | 200 | 400 invalid body, 404 unknown id |
| DELETE | `/tasks/{id}` | Remove it, empty body | 204 | 404 unknown id |
| GET | `/stats` | `{"total":3,"done":1,"open":2}`, counted in SQL | 200 | |
| POST | `/reset` | Empty the table and seed it again | 200 | |

Every error comes back in the same shape, `{"error": "..."}`, whatever went wrong. The 404 text
keeps the A1 wording (`Task 999 not found` rather than `Task not found`) because the point of
these assignments is to change the storage and nothing else.

## The table

```sql
CREATE TABLE IF NOT EXISTS tasks (
  id serial PRIMARY KEY,
  title text NOT NULL,
  done boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS tasks_title ON tasks (title);
CREATE INDEX IF NOT EXISTS tasks_done ON tasks (done);
```

`serial` makes Postgres hand out the ids, so a client never sends one. It is a sequence behind
the scenes, which is why `POST /reset` runs `TRUNCATE tasks RESTART IDENTITY` rather than
`DELETE`: a sequence keeps counting after a `DELETE`, and the fresh example tasks would come
back as ids 4, 5 and 6.

Every value reaches Postgres as a `%s` parameter, never glued into the SQL text. A column name
cannot be a parameter, so `?sort=` is typed as `Literal["id", "title"]` and FastAPI rejects
anything else before a query is built:

```console
$ curl -s 'http://localhost:3000/tasks?sort=id;%20DROP%20TABLE%20tasks'
{"error":"sort: Input should be 'id' or 'title'"}
```

## Talking to the database by hand

`docker compose exec db psql -U postgres -d tasks` opens a SQL prompt inside the container.
Changes made there are visible to the API immediately, with the server left running:

```console
$ docker compose exec db psql -U postgres -d tasks -c "UPDATE tasks SET done = true;"
UPDATE 3
$ curl -s http://localhost:3000/stats
{"total":3,"done":3,"open":0}

$ docker compose exec db psql -U postgres -d tasks -c "DELETE FROM tasks WHERE done = true;"
DELETE 3
$ curl -s http://localhost:3000/tasks
[]
```

There is no syncing step and no cache to clear: `psql` and the app are two clients of the same
server. Under SQLite this same experiment was where A2 found a bug, because a second program
holding the file locked made every request fail. Postgres is built for the second program.

A2 did this through a GUI rather than a prompt, and those screenshots are still here:
[`docs/db-browser.png`](docs/db-browser.png) is `tasks.db` open in DB Browser for SQLite and
[`docs/sql-execute.png`](docs/sql-execute.png) is its Execute SQL tab running
`SELECT * FROM tasks WHERE done = 1;`. Nothing in the repo points at a SQLite file any more, so
they are kept as the record of that week rather than as instructions.

## Query parameters

- **Filter**: `GET /tasks?done=true` becomes `WHERE done = %s`.
- **Search**: `GET /tasks?search=git` becomes `WHERE title ILIKE %s` with `%git%`.
- **Sort**: `GET /tasks?sort=title` adds `ORDER BY title`.
- **Stats**: `GET /stats` is one `COUNT(*) FILTER (WHERE done)` query rather than two.
- **Pagination**: `LIMIT %s OFFSET %s`, with limit capped at 100.

`ILIKE`, not `LIKE`, and this is the one line where a storage swap nearly changed behaviour.
SQLite's `LIKE` ignores case for ASCII, so `?search=github` found `Push it to GitHub` in A2.
Postgres's `LIKE` is case-sensitive, so the same code ported literally would have returned an
empty list, silently, with no error anywhere:

```console
$ curl -s 'http://localhost:3000/tasks?search=github'
[{"id":3,"title":"Push it to GitHub","done":false,...}]
```

### The transaction

`db.init()` seeds inside one transaction, so the three example tasks arrive together or not at
all. If the process died between the second and third insert, a half-seeded table would look
"not empty" on the next start and would never be repaired, because the seed only runs when the
count is 0.

### What the repository module buys

Every SQL string in this project is in [`db.py`](db.py). [`main.py`](main.py) has routes,
validation and status codes and does not contain the word `SELECT`. That is why moving from
SQLite to Postgres changed one file plus three new infrastructure files, and no route.

A2 needed a hand-rolled `db.migrate()` that read `PRAGMA table_info(tasks)` and added missing
columns, because `CREATE TABLE IF NOT EXISTS` silently skips a table that already exists and my
own `tasks.db` predated the timestamp columns. A3 starts from an empty volume, so that function
is gone rather than ported. The lesson it taught still stands: the second time you change a
table, you need migrations, and every database gets a second time.

## Extras

None of these were required. Each one is a thing the database can now do that a file could not.

### The mortality experiment

Same Postgres image, same commands, no `-v` flag:

```console
$ docker run --name mortal -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tasks -p 5433:5432 -d postgres:17
$ docker exec mortal psql -U postgres -d tasks -c "INSERT INTO tasks (title) VALUES ('I will not survive'), ('nor will I');"
INSERT 0 2
$ docker exec mortal psql -U postgres -d tasks -c "SELECT * FROM tasks;"
 id |       title
----+--------------------
  1 | I will not survive
  2 | nor will I
(2 rows)

$ docker rm -f mortal
$ docker run --name mortal ... -d postgres:17        # same command again
$ docker exec mortal psql -U postgres -d tasks -c '\dt'
Did not find any relations.
```

A container's own filesystem is a scratch layer that is deleted with the container, so rows
written into it die with it. A volume is storage that Docker keeps outside the container and
hands to whichever container asks for it next, which is why `taskdata:/var/lib/postgresql/data`
is the difference between the run above and `docker compose down && docker compose up`.

### A health check that means something

```console
$ curl -s localhost:3000/health
{"status":"ok","db":"ok"}

$ docker compose stop db
$ curl -i localhost:3000/tasks
HTTP/1.1 503 Service Unavailable

{"error":"Database unavailable: failed to resolve host 'db': [Errno -2] Name or service not known"}

$ docker compose start db
$ curl -s -o /dev/null -w '%{http_code}\n' localhost:3000/tasks
200
```

`/health` runs `SELECT 1` rather than returning a constant. A load balancer polls it every few
seconds and takes an instance out of rotation while it fails, so an app that is running but
cannot reach its database stops receiving traffic instead of answering every request with a
500. A health check that only proves the process is alive would keep sending traffic to it.

The app also recovered on its own when the database came back, with no restart, because each
request opens its own connection.

### The index on `done`

50,000 rows, 1% of them done, `EXPLAIN ANALYZE` before and after `CREATE INDEX tasks_done`:

```console
-- before
=> EXPLAIN ANALYZE SELECT count(*) FROM tasks WHERE done = true;
 Aggregate  (actual time=1.458..1.458 rows=1 loops=1)
   ->  Seq Scan on tasks  (actual time=0.004..1.438 rows=501 loops=1)
         Filter: done
         Rows Removed by Filter: 49502
 Execution Time: 1.480 ms

-- after
=> EXPLAIN ANALYZE SELECT count(*) FROM tasks WHERE done = true;
 Aggregate  (actual time=0.311..0.311 rows=1 loops=1)
   ->  Index Only Scan using tasks_done on tasks  (actual time=0.015..0.295 rows=501 loops=1)
         Index Cond: (done = true)
 Execution Time: 0.328 ms
```

1.480 ms to 0.328 ms, and the scan stopped reading 49,502 rows it was going to throw away.

The more interesting result is the query the API actually runs, which has `ORDER BY id LIMIT
50`. There the index made it slightly slower, 0.281 ms to 0.339 ms:

```console
-- before: walks the primary key in id order and stops after 50 matches
 Limit  (actual time=0.008..0.268 rows=50 loops=1)
   ->  Index Scan using tasks_pkey on tasks  (actual time=0.008..0.265 rows=50 loops=1)
         Filter: done
 Execution Time: 0.281 ms

-- after: finds all 501 matches, then sorts them to get the first 50 by id
 Limit  (actual time=0.322..0.326 rows=50 loops=1)
   ->  Sort  (actual time=0.322..0.323 rows=50 loops=1)
         Sort Key: id
         Sort Method: top-N heapsort  Memory: 28kB
         ->  Index Scan using tasks_done on tasks  (actual time=0.006..0.295 rows=501 loops=1)
 Execution Time: 0.339 ms
```

An index that helps the count hurts the paginated list, because the primary key was already
delivering rows in the order the query wanted and a `LIMIT` lets the database stop early. An
index on `(done, id)` would serve both, which is the general lesson: index the query, not the
column.

### Redis, one PING

`compose.yaml` has a third service, `redis:7-alpine`, and the app pings it once at startup:

```console
$ docker compose logs api | grep redis
api-1  | INFO:     redis: +PONG
```

Nothing caches anything yet, so [`cache.py`](cache.py) writes `PING\r\n` to the socket and
reads the reply instead of adding a client library for one round trip. When something actually
stores a value, that is when the real client earns its place in `requirements.txt`. A failed
ping logs a warning and the app carries on, because Redis is not on the request path.

### The multi-stage image

| Dockerfile | Image size |
|---|---|
| Single stage, `pip install` into the runtime image | 317MB |
| Multi-stage, build a virtualenv and copy `/venv` | 337MB |
| Multi-stage, `pip install --prefix=/install` and copy it | 300MB |

The middle row is the one worth keeping. Multi-stage is not automatically smaller: copying a
virtualenv into an image that already ships its own `pip` and `setuptools` adds 20MB rather
than saving any, because `psycopg[binary]` installs from a wheel and there was no compiler or
header package in the build stage to leave behind. Staging the install with `--prefix` and
copying only that does save 17MB, and it is the shape that pays off properly the day a
dependency does need building.

## Storage is an implementation detail

[`test_api.py`](test_api.py) was written against the in-memory A1 version. It was run against
the SQLite version with no edit and printed `all checks passed`. At stage 3 of this assignment
it was run against Postgres, again with no edit (`git diff HEAD -- test_api.py` was empty), and
printed `all checks passed` again.

Same assertions, same status codes, same JSON, three different storage engines. The tests
describe the promise the API makes to a client, and a client cannot tell whether a task is in a
list, a file or a server on another host. That is what "storage is an implementation detail"
means, and A15 (layered architecture) is the assignment that makes the boundary formal instead
of a rule I keep by hand.

One assertion in that file did change afterwards, and for the opposite reason. The extras made
`/health` report on the database as well, so `{"status": "ok"}` became
`{"status": "ok", "db": "ok"}`. That is a change to the promise, not to where the data is kept,
and it is the only line in the file A3 touched.

## Swagger UI

Every endpoint is listed, and **Try it out** sends the real request. Both screenshots below came
from headless Chrome driving http://localhost:3000/docs against the compose stack, so they show
the Postgres build rather than a hand-taken snap of an older one:

![Swagger UI at /docs, listing all nine endpoints](docs/swagger-ui.png)

Posting `{}` through **Try it out** on `POST /tasks`, which answered `400` with
`{"error": "title: Field required"}`:

![POST /tasks with an empty body, answered with 400](docs/swagger-tryit.png)

One mismatch is visible in that screenshot: the server response is `400 Undocumented`, while the
"Responses" table below it still declares `422 Validation Error`, because that is what FastAPI
generates for a body-validated route. The app answers 400, so the generated docs and the running
code disagree on that one line.

## AI vs me, A3 (containerising the stack)

I did stages 0 to 5 by hand, then wrote [`ai-version/a3/prompt-v1.md`](ai-version/a3/prompt-v1.md)
from memory with the brief closed, and generated a whole containerised stack from that prompt
alone. Its files are in [`ai-version/a3/`](ai-version/a3/), 148 lines of Python plus a
Dockerfile, a compose file and a `.env.example`, unedited since they were generated, including
both bugs below.

### Does `docker compose up` work first try?

No, and it failed twice for two unrelated reasons.

**One.** Its compose file says `image: postgres` with no tag. That resolves to 18 now, which
moved its data directory, so the database exited before it ever started:

```console
$ docker compose up -d --build
$ docker compose ps -a
SERVICE   STATUS
api       Exited (3) 7 seconds ago
db        Exited (1) 8 seconds ago
```

This is the same wall my own stage 0 hit, which is the only reason I recognised it in one look.

**Two.** Pinning the tag to `postgres:17` from a separate override file, leaving its own files
untouched, got the database up and the app still died:

```console
SERVICE   STATUS
api       Exited (3) 9 seconds ago
db        Up 10 seconds

api-1  | psycopg.OperationalError: connection failed: connection to server at "172.20.0.2",
api-1  |   port 5432 failed: Connection refused
api-1  | ERROR:    Application startup failed. Exiting.
```

`depends_on: - db` waits for the container to start, not for Postgres to accept connections,
and the app connects during startup. It lost the race, exited, and with no restart policy it
stayed dead. Starting the API by hand a second time worked, which is exactly the "one command"
the prompt asked for, spent twice.

### With it running, the CRUD is right

Every rule my prompt actually stated came out correct:

| What I sent | Mine | AI v1 |
|---|---|---|
| `GET /tasks` | 200, three seeded tasks | 200, three seeded tasks |
| `POST /tasks -d '{"title":"Buy milk"}'` | 201 | 201 |
| `POST /tasks -d '{}'` | 400 `{"error":"title: Field required"}` | 400 `{"error":"Field required"}` |
| `POST /tasks -d '{"title":"   "}'` | 400 | 400 `{"error":"Value error, title must not be empty"}` |
| `GET /tasks/999` | 404 `{"error":"Task 999 not found"}` | 404 `{"error":"Task not found"}` |
| `DELETE /tasks/4`, then again | 204, then 404 | 204, then 404 |
| `PUT` with only a title, on a task already done | stays `done:true` | stays `done:true` |
| `GET /`, `/health`, `/stats` | 200 | 404, none exist |
| `GET /tasks?done=true` (3 tasks, 1 done) | 1 task | 3 tasks, the parameter is ignored |
| Create, `docker compose down`, `up` | rows still there | rows still there |
| Password in a committed file | no | no |

The persistence and the secret handling are both right: it put the data on a named volume and
read the password from `.env` through compose substitution, so nothing sensitive is in a file
it would have committed.

The `?done=true` row is the one that would bite in production. FastAPI accepts unknown query
parameters silently, so its `GET /tasks?done=true` answers `200` with every task rather than
`400` or a filtered list. A client would look correct and be wrong.

### What it did better

**Its app starts without a database.** It calls `db.init()` from a startup hook; mine calls it
at import. So importing its module with nothing listening is fine, and importing mine is not:

```console
$ DATABASE_URL="postgresql://postgres:dev@localhost:5999/tasks" python -c "import main"     # mine
psycopg.OperationalError: connection failed: ... port 5999 failed: Connection refused

$ DATABASE_URL="postgresql://postgres:dev@localhost:5999/tasks" python -c "import main"     # its
imported fine, no connection attempted
```

That is the difference between a test file that can import the app and one that cannot, and it
is a straight design win I did not think about.

**Its `.env.example` password is `changeme`; mine is `dev`.** Both work when copied, but one of
them tells you it is a placeholder.

**It put `EXPOSE 3000` in the Dockerfile.** Documentation rather than function, and mine has no
equivalent line.

### What it got wrong

The unpinned image and the missing readiness gate, both above, and both of them the kind of
thing that works on the machine where it was written and fails on the next one. It also left
`requirements.txt` unpinned (`fastapi`, `uvicorn[standard]`, `psycopg[binary]`, no versions),
so the image it builds next month is not the image it builds today.

### What my prompt forgot

Every one of those failures traces back to a sentence I did not write. I said "the official
image" and never said pin a major version. I said "two services so that `docker compose up`
starts both" and never said the app must wait for the database to be ready, because on my own
stack I had already solved that with a health check and had stopped thinking about it. I said
"their behaviour must not change" without quoting the 404 text or the 400 format, so it wrote
sensible strings that no existing client would match. I never mentioned the four extra
endpoints, the five query parameters, the timestamp columns, or what should happen when the
database is unreachable.

### The rematch

[`ai-version/a3-v2/prompt-v2.md`](ai-version/a3-v2/prompt-v2.md) is the same prompt with seven
paragraphs added, one per thing above. The regenerated
[`ai-version/a3-v2/`](ai-version/a3-v2/) came up on the first `docker compose up` with no
override and no second command, and all seven hold:

```console
$ docker compose ps
SERVICE   STATUS
api       Up Less than a second
db        Up 6 seconds (healthy)

$ curl -s localhost:3000/tasks/999
{"error":"Task 999 not found"}
$ curl -s -X POST localhost:3000/tasks -d '{}' -H "Content-Type: application/json"
{"error":"title: Field required"}
$ curl -s localhost:3000/health
{"status":"ok","db":"ok"}
$ curl -s 'localhost:3000/tasks?search=github'
[{"id":3,"title":"Push it to GitHub",...}]
$ curl -s 'localhost:3000/tasks?sort=id;%20DROP%20TABLE%20tasks'
{"error":"sort: Input should be 'id' or 'title'"}
$ curl -s -X POST localhost:3000/reset | python3 -c 'import sys,json;print([t["id"] for t in json.load(sys.stdin)])'
[1, 2, 3]
$ docker compose stop db && curl -s -o /dev/null -w '%{http_code}\n' localhost:3000/tasks
503
$ docker compose start db          # then a few seconds for Postgres to accept connections
$ curl -s -o /dev/null -w '%{http_code}\n' localhost:3000/tasks
200
```

One sentence on what changed: naming the version pin and the readiness condition turned a stack
that needed two manual rescues into one that started on the first command, and the six lines of
exact error text and endpoint behaviour turned a plausible API into the same API.

The lesson is the one the assignment predicts, and running it is what made it concrete. The v1
output was as good as the v1 prompt, and the v1 prompt was missing precisely the things I had
already learned by hand and therefore no longer noticed I knew. I could only grade any of this
because I had built the thing first: an unpinned `image: postgres` and a bare `depends_on` both
look completely reasonable on the page.

## AI vs me, A2 (the move to SQLite)

I did stages 0 to 5 by hand, then wrote [`ai-version/w3/prompt-v1.md`](ai-version/w3/prompt-v1.md)
from memory without opening this brief, and had an AI do the same migration from that prompt
alone. Its code is [`ai-version/w3/db.py`](ai-version/w3/db.py) and
[`ai-version/w3/main.py`](ai-version/w3/main.py), 76 and 75 lines, generated in a folder of its
own and not edited since, including the one bug below.

It started on the first try, created its own `tasks.db`, and passed my stage 2 and stage 3
checkpoints. Five restarts left three rows each time. A task created before a restart was still
there afterwards. Every rule my prompt actually stated came out right: 201 on create, 400 for a
missing, empty or whitespace-only title, 404 on unknown ids for GET, PUT and DELETE, 204 with an
empty body, the `{"error": ...}` envelope, `done` back as a JSON boolean, and `?` parameters
everywhere with no string-glued SQL.

Three differences that showed up when I ran both:

| What I probed | Mine | AI v1 |
|---|---|---|
| Open handles on `tasks.db` after 200 `GET /tasks` | 0, unchanged | grew from 4 to 12 |
| Insert after deleting the highest id | reuses the id (4 again) | jumps to 6, never reuses |
| Tables in the file | `tasks` | `tasks` and `sqlite_sequence` |
| `GET /`, `GET /health`, `GET /stats`, `?done=`, `?search=` | 200 | 404, none of them exist |
| 404 body | `{"error":"Task 999 not found"}` | `{"error":"Task not found"}` |

**What it did better.** Its update is one statement where mine is two:

```sql
UPDATE tasks SET title = ?, done = COALESCE(?, done) WHERE id = ?
```

`COALESCE` keeps the stored `done` when the parameter is NULL, so the rule "a PUT without `done`
leaves it alone" is expressed in SQL. My version reads the row first to find the current value,
then writes. Both are correct because both run inside a transaction, but the AI needed one round
trip to the database and no prior read. It also used `cur.rowcount` to tell a missing id from a
real update, where I run an extra `SELECT`. That is a better use of what the database already
tells you.

**What it got wrong.** `with sqlite3.connect(...) as conn` commits the transaction, but unlike
most Python context managers it does not close the object. The AI opens a connection per call
and never closes one, so open handles on `tasks.db` climbed from 4 to 12 over 200 requests
against a table of three rows. It looks exactly like correct code and it is the kind of leak
that only shows up in production. Its `AUTOINCREMENT` is a smaller thing but the same shape: it
sounds like the way to get automatic ids, it is not needed for that, and it quietly adds a
second table to the file.

**What my prompt forgot.** I said "keep these five endpoints" and listed five, so the four
others in my app do not exist in its version; that is my sentence, not its mistake. I said the
endpoints must behave exactly as they do now without quoting the 404 text, so it wrote a
sensible generic message that no existing client would match. I never mentioned closing
connections, timestamps, an index, or WAL. And one thing we both got wrong: my prompt said
every error must use the `{"error": ...}` envelope, and neither version does it for a URL that
matches no route at all. Both answer `GET /nope` with Starlette's own
`{"detail":"Not Found"}`, because that 404 never reaches the app's exception handler.

**The rematch.** [`ai-version/w3/prompt-v2.md`](ai-version/w3/prompt-v2.md) adds seven
paragraphs: close the connections, no `AUTOINCREMENT`, name the id in the 404, the four extra
endpoints, the five query parameters with `sort` restricted by its type annotation, the
timestamp columns and the title index, and WAL plus a 503 for a locked database. The regenerated
[`ai-version/w3-v2/`](ai-version/w3-v2/) fixed every one of them: handles on `tasks.db` stayed
at 0 across 200 requests, `sqlite_master` lists only `tasks`, `PRAGMA journal_mode` reports
`wal`, `GET /tasks/999` answers `{"error":"Task 999 not found"}`, and `?sort=nope` answers
`{"error":"sort: Input should be 'id' or 'title'"}`, the same message mine gives.

It also made two calls I did not ask about, and told me it had made them: it keeps `created_at`
and `updated_at` in the table but leaves them out of the JSON, reading "response shapes do not
change" as the stronger instruction, where I chose to expose both. The v1 prompt was 1 page and
produced a leak; the v2 prompt was 2 pages and produced code I would merge. The difference
between them is not cleverness, it is the seven things I only knew to write down because I had
already run the first version and watched a file handle counter go up.

## A1, for the record

The in-memory version is still in the history, up to commit `122991e`. Its README ended with an
experiment: add a fourth task, stop the server, start it again, ask for `GET /tasks`. The list
was back to three and the fourth was gone, because the tasks only ever existed as Python objects
inside one process. Killing the process killed the data. Everything above is the answer to that.


## AI vs me, A1 (the in-memory API)

Week 2's stages are hand-written. After finishing them I wrote a prompt from memory, asked
Claude to build the same API from that prompt alone, and kept its output in
[`ai-version/`](ai-version/) so my own code stays untouched. The full prompt is
[`ai-version/prompt-v1.md`](ai-version/prompt-v1.md); the generated code is
[`ai-version/main_v1.py`](ai-version/main_v1.py), 82 lines against the 117 of my
in-memory `main.py`.

I ran it on port 8200 and fired my Stage 4 checkpoint curls at it. Five differences that
actually showed up:

| What I sent | Mine | AI v1 |
|---|---|---|
| `POST /tasks -d '{}'` | 400 `{"error":"title: Field required"}` | 422 `{"detail":[{"type":"missing",...}]}` |
| `POST /tasks -d '{"title":"   "}'` | 400, whitespace stripped first | 201, creates a task with a blank title |
| `GET /tasks/99` | 404 `{"error":"Task 99 not found"}` | 404 `{"detail":"Task not found"}` |
| `PUT` with only a `title`, on a task already `done:true` | stays `done:true` | silently resets to `done:false` |
| `GET /` and `GET /health` | 200 | 404, neither exists |

**What the AI did better.** It declared `response_model` on every route and stored tasks as
Pydantic `Task` objects instead of dicts. That is not decoration: my `/openapi.json` describes
the 200 response of `GET /tasks` as `{}`, an empty schema, while the AI's describes it as an
array of `Task` with typed fields, so its Swagger page documents what comes back and mine only
documents what goes in. FastAPI also validates outgoing data against `response_model`, so a
route that accidentally returned the wrong shape would fail loudly there instead of quietly
reaching the client.

**What it got wrong.** My prompt said in plain words that a missing or empty title must be
rejected with 400, and the generated code returns 422 with Pydantic's raw error list, because
`Field(min_length=1)` alone leaves FastAPI's default validation handler in place. It ignored an
explicit instruction and it looks right until you read the status code. The blank-title bug
comes from the same line: `min_length=1` counts `"   "` as three characters, so a title of
pure whitespace sails through into the list.

**What my prompt forgot.** I never said what an error body should look like, so the AI chose
FastAPI's `{"detail": ...}` and stayed consistent with it, which is a defensible answer to a
question I did not ask. I never mentioned `GET /` or `GET /health`, so they do not exist. And I
wrote "replaces the title and done", which the AI implemented literally: `done` defaults to
false on `PUT`, so updating a finished task's title marks it unfinished again. That is my
sentence being ambiguous, not the model being careless.

**The rematch.** [`ai-version/prompt-v2.md`](ai-version/prompt-v2.md) adds six sentences
covering the error envelope, the 400 mapping, whitespace stripping, the two extra endpoints,
the optional `done` on `PUT`, and response models;
[`ai-version/main_v2.py`](ai-version/main_v2.py) then matched my hand-built behaviour on every
probe above, at 116 lines against that same 117. `git diff --no-index main.py ai-version/main_v2.py`
still reports 145 changed lines, but two structural choices account for most of them: it keeps
tasks as Pydantic `Task` objects where I keep plain dicts, and it has no `/stats`, `/reset`,
filtering or pagination, because prompt v2 never asked for the extras.

The thing worth keeping from this stage: the second prompt is not smarter than the first, it is
just more specific, and I could only write it because I had already built the thing by hand and
knew which six sentences were missing.

## Notes on the implementation

`db.py` holds every SQL string and the connection handling, 144 lines of it; `main.py` holds the
routes and validation in 122 lines and never mentions `psycopg` except in the handler that
catches a database it cannot reach, and `cache.py` is 32 lines for one Redis PING. Each request opens its own connection. Postgres connections
cost milliseconds rather than SQLite's microseconds, which is affordable at this size; a pool
(`psycopg_pool`) is the upgrade if the request rate ever makes it matter.

Validation lives in one Pydantic model, `TaskIn`, and error formatting lives in three exception
handlers, so every route answers in `{"error": "..."}` without any route repeating that logic.
FastAPI's own default for a bad body is 422; the handler maps it to the 400 this assignment
asks for. A database that is down answers `503` rather than a bare `Internal Server Error`,
which matters more now that the database is a separate program that can be missing while the
app is perfectly healthy.
