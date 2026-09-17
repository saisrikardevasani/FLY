# Prompt v1

Written from memory, before looking at anything I had built.

---

Build a small to-do API in Python using FastAPI. Keep it in one file called `main.py`.

Tasks are kept in memory in a list. No database. Each task has an `id` (number), a `title`
(text) and `done` (true or false). Start with three example tasks already in the list.

Endpoints:

- `GET /tasks` returns the whole list.
- `GET /tasks/{id}` returns one task, or 404 if there is no task with that id.
- `POST /tasks` takes JSON like `{"title": "Buy milk"}`, gives the task the next free id,
  sets `done` to false, adds it to the list, and returns the new task with status 201.
- `PUT /tasks/{id}` replaces the title and done of an existing task and returns the updated
  task. 404 if the id is unknown.
- `DELETE /tasks/{id}` removes the task and returns 204 with an empty body. 404 if the id is
  unknown.

Validate the input: a missing or empty title must be rejected with 400.

Swagger UI at `/docs` should list every endpoint so I can try them from the browser.

Tell me the command to run the server.
