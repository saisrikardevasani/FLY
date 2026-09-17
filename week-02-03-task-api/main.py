from typing import Annotated, Literal

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StringConstraints

import cache
import db

db.init()
cache.ping_at_startup()

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A tiny to-do API. Tasks live in a Postgres container, so they survive a restart.",
)

# Routes hold no SQL. Everything that talks to the database is in db.py, which is why
# moving from a list to SQLite to Postgres has never changed a single route.


class TaskIn(BaseModel):
    """What a client is allowed to send. An empty or missing title is rejected."""

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    done: bool | None = None


def found(task: dict | None, task_id: int) -> dict:
    """Turn "no such row" into the 404 the API has always returned."""
    if task is None:
        raise HTTPException(404, f"Task {task_id} not found")
    return task


@app.exception_handler(HTTPException)
async def error_shape(request, exc: HTTPException):
    """Every error answers with {"error": "..."} instead of FastAPI's default."""
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(psycopg.OperationalError)
async def database_down(request, exc: psycopg.OperationalError):
    """The database is a separate program now, so it can be missing while the app is fine."""
    return JSONResponse(status_code=503, content={"error": f"Database unavailable: {exc}"})


@app.exception_handler(RequestValidationError)
async def invalid_body(request, exc: RequestValidationError):
    """A body that fails validation is the client's fault: 400, not FastAPI's 422."""
    problem = exc.errors()[0]
    # loc looks like ("body", "title") for a field, or ("body", 39) for malformed JSON,
    # where 39 is a character offset. Dropping the numbers keeps the message readable.
    field = ".".join(p for p in problem["loc"][1:] if isinstance(p, str)) or "body"
    return JSONResponse(status_code=400, content={"error": f"{field}: {problem['msg']}"})


@app.get("/", summary="What this API is")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Is the server alive, and can it reach the database?")
def health():
    """Answers ok only after Postgres answers SELECT 1.

    A load balancer polls this and takes the instance out of rotation while it fails, so an
    app that is running but cannot reach its database stops receiving traffic instead of
    serving errors. That is why it checks the dependency rather than returning a constant.
    """
    try:
        db.ping()
    except psycopg.Error as exc:
        return JSONResponse(status_code=503, content={"status": "degraded", "db": str(exc)})
    return {"status": "ok", "db": "ok"}


@app.get("/tasks", summary="List tasks, optionally filtered")
def list_tasks(
    done: bool | None = None,
    search: str | None = None,
    sort: Literal["id", "title"] = "id",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return db.list_tasks(done, search, sort, limit, offset)


@app.get("/tasks/{task_id}", summary="Get one task by id")
def get_task(task_id: int):
    return found(db.get(task_id), task_id)


@app.post("/tasks", status_code=201, summary="Create a task")
def create_task(body: TaskIn):
    """The database hands out the id; the client never sends one."""
    return db.create(body.title, bool(body.done))


@app.put("/tasks/{task_id}", summary="Replace a task")
def update_task(task_id: int, body: TaskIn):
    return found(db.update(task_id, body.title, body.done), task_id)


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    if not db.delete(task_id):
        raise HTTPException(404, f"Task {task_id} not found")


@app.get("/stats", summary="Count tasks by state")
def stats():
    row = db.counts()
    return {"total": row["total"], "done": row["done"], "open": row["total"] - row["done"]}


@app.post("/reset", summary="Restore the 3 example tasks")
def reset():
    return db.reset()
