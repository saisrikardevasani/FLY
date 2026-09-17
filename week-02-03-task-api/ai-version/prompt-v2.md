# Prompt v2 — the rematch

Same request, with the six things v1 got wrong or invented for me spelled out.
Changes from v1 are the last six bullets.

---

Build a small to-do API in Python using FastAPI. Keep it in one file called `main.py`.

Tasks are kept in memory in a list. No database. Each task has an `id` (number), a `title`
(text) and `done` (true or false). Start with three example tasks already in the list.

Endpoints:

- `GET /tasks` returns the whole list.
- `GET /tasks/{id}` returns one task, or 404 if there is no task with that id.
- `POST /tasks` takes JSON like `{"title": "Buy milk"}`, gives the task the next free id,
  sets `done` to false, adds it to the list, and returns the new task with status 201.
- `PUT /tasks/{id}` updates an existing task and returns it. 404 if the id is unknown.
- `DELETE /tasks/{id}` removes the task and returns 204 with an empty body. 404 if the id is
  unknown.

Swagger UI at `/docs` should list every endpoint so I can try them from the browser.
Tell me the command to run the server.

New this time:

- Also add `GET /` returning `{"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}`
  and `GET /health` returning `{"status": "ok"}`.
- Every error response, without exception, must have the body `{"error": "<message>"}`.
  Do not use FastAPI's default `{"detail": ...}` shape anywhere.
- A body that fails validation must return **400**, not FastAPI's default 422. Install an
  exception handler for `RequestValidationError` rather than validating by hand in each route.
- The 404 message must name the id that was not found, e.g. `Task 99 not found`.
- Strip whitespace from `title` before validating it, so a title of `"   "` is rejected as
  empty with 400.
- On `PUT`, `title` is required, `done` is optional, and when `done` is absent leave the
  task's existing `done` value alone. Do not silently reset it to false.
- Declare a response model on every route so `/docs` shows the shape of what comes back.
