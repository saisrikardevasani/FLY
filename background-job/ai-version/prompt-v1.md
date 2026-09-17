# Prompt v1

Written from memory before generating anything, without re-reading the assignment brief. The
generated code goes in this folder and is never edited afterwards.

---

Build me a small Python API that hands slow work to a background job system. Use FastAPI and
Inngest, with the Inngest Dev Server running locally.

The API has these endpoints:

- `GET /health` returns `{"status": "ok"}`.
- `POST /reports` takes a JSON body like `{"topic": "cats"}`. It creates an id, stores the
  report in memory as pending, sends an Inngest event called `report/requested` carrying the id
  and the topic, and returns `202` immediately with `{"id": ..., "status": "pending"}`. The
  endpoint itself must do no slow work at all. It has to come back in milliseconds.
- `GET /reports/{id}` returns the stored report. It says pending at first and done with a
  result later. An id that does not exist returns `404`.

If the topic is missing or empty, return `400` and do not send any event. A bad request is the
client's mistake and must be rejected at the door, not queued.

Background functions, served at `/api/inngest`:

1. `say-hello`, triggered by the event `test/hello`. It sleeps five seconds using a step and
   returns a greeting. This one exists only to prove the wiring works.
2. `make-report`, triggered by `report/requested`. It must use at least two steps: a step that
   sleeps for eight seconds, standing in for real slow work, and then a step that builds the
   result and saves it into the reports store with status done.
3. A function on a cron schedule of every minute that logs one line saying how many reports are
   pending, how many are done and how many failed. Nothing triggers it but the clock.

Retries: configure `make-report` to retry twice, so a failing run makes three attempts in total
and then ends as failed. To demonstrate it, make the build step raise an error when the topic is
the word "fail". The waits between attempts should get longer each time.

Use an Inngest app id of `report-api`. Give me the two commands to run it: one for the API and
one for the Dev Server.
