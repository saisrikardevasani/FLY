from typing import Literal

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

import db

app = FastAPI(title="Task API")


@app.on_event("startup")
def startup():
    db.init()


class TaskIn(BaseModel):
    title: str
    done: bool | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty")
        return v


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(psycopg.OperationalError)
async def db_unreachable(request, exc):
    return JSONResponse(
        status_code=503, content={"error": f"Database unavailable: {exc}"}
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    err = exc.errors()[0]
    field = ".".join(str(p) for p in err["loc"][1:] if isinstance(p, str)) or "body"
    return JSONResponse(status_code=400, content={"error": f"{field}: {err['msg']}"})


@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health")
def health():
    try:
        db.ping()
    except psycopg.Error as exc:
        return JSONResponse(
            status_code=503, content={"status": "degraded", "db": str(exc)}
        )
    return {"status": "ok", "db": "ok"}


@app.get("/tasks")
def list_tasks(
    done: bool | None = None,
    search: str | None = None,
    sort: Literal["id", "title"] = "id",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return db.all_tasks(done, search, sort, limit, offset)


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    task = db.one_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.post("/tasks", status_code=201)
def create_task(payload: TaskIn):
    return db.add_task(payload.title, bool(payload.done))


@app.put("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskIn):
    task = db.edit_task(task_id, payload.title, payload.done)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    if not db.remove_task(task_id):
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.get("/stats")
def stats():
    row = db.stats()
    return {
        "total": row["total"],
        "done": row["done"],
        "open": row["total"] - row["done"],
    }


@app.post("/reset")
def reset():
    return db.reset()
