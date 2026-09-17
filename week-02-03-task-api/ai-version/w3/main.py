from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    yield


app = FastAPI(title="Task API", lifespan=lifespan)


class TaskIn(BaseModel):
    title: str
    done: bool | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be empty")
        return value


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"][1:]) or "body"
    return JSONResponse({"error": f"{field}: {first['msg']}"}, status_code=400)


def _found(task: dict | None) -> dict:
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/tasks")
def list_tasks() -> list[dict]:
    return db.list_tasks()


@app.get("/tasks/{task_id}")
def get_task(task_id: int) -> dict:
    return _found(db.get_task(task_id))


@app.post("/tasks", status_code=201)
def create_task(payload: TaskIn) -> dict:
    return db.create_task(payload.title, bool(payload.done))


@app.put("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskIn) -> dict:
    return _found(db.update_task(task_id, payload.title, payload.done))


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int) -> Response:
    if not db.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return Response(status_code=204)
