"""To-do API. Same nine endpoints as before, tasks now stored in SQLite."""

import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

import store


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init()
    yield


app = FastAPI(title="Task API", version="2.0.0", lifespan=lifespan)


# Errors: one envelope, {"error": "..."}, whatever the status code.


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse({"error": str(exc.detail)}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"][1:]) or "body"
    return JSONResponse({"error": f"{field}: {first['msg']}"}, status_code=400)


@app.exception_handler(sqlite3.OperationalError)
async def sqlite_error(request: Request, exc: sqlite3.OperationalError) -> JSONResponse:
    return JSONResponse({"error": f"Database unavailable: {exc}"}, status_code=503)


class TaskIn(BaseModel):
    title: str
    done: bool = False

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class TaskUpdate(TaskIn):
    done: bool | None = None  # absent keeps the stored flag


def found(task: dict | None, task_id: int) -> dict:
    if task is None:
        raise HTTPException(404, f"Task {task_id} not found")
    return task


@app.get("/")
def root() -> dict:
    return {
        "name": "Task API",
        "version": app.version,
        "endpoints": [
            "GET /tasks",
            "GET /tasks/{id}",
            "POST /tasks",
            "PUT /tasks/{id}",
            "DELETE /tasks/{id}",
            "GET /health",
            "GET /stats",
            "POST /reset",
        ],
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/stats")
def stats(conn: sqlite3.Connection = Depends(store.get_conn)) -> dict:
    return store.stats(conn)


@app.post("/reset")
def reset(conn: sqlite3.Connection = Depends(store.get_conn)) -> list[dict]:
    return store.reset(conn)


@app.get("/tasks")
def list_tasks(
    done: bool | None = None,
    search: str | None = None,
    sort: store.Sort = "id",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(store.get_conn),
) -> list[dict]:
    return store.list_tasks(conn, done, search, sort, limit, offset)


@app.get("/tasks/{task_id}")
def get_task(
    task_id: int, conn: sqlite3.Connection = Depends(store.get_conn)
) -> dict:
    return found(store.get_task(conn, task_id), task_id)


@app.post("/tasks", status_code=201)
def create_task(
    body: TaskIn, conn: sqlite3.Connection = Depends(store.get_conn)
) -> dict:
    return store.create_task(conn, body.title, body.done)


@app.put("/tasks/{task_id}")
def update_task(
    task_id: int,
    body: TaskUpdate,
    conn: sqlite3.Connection = Depends(store.get_conn),
) -> dict:
    return found(store.update_task(conn, task_id, body.title, body.done), task_id)


@app.delete("/tasks/{task_id}", status_code=204, response_class=Response)
def delete_task(
    task_id: int, conn: sqlite3.Connection = Depends(store.get_conn)
) -> Response:
    found({} if store.delete_task(conn, task_id) else None, task_id)
    return Response(status_code=204)
