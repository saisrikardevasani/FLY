from fastapi import FastAPI, HTTPException
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


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(status_code=400, content={"error": exc.errors()[0]["msg"]})


@app.get("/tasks")
def list_tasks():
    return db.all_tasks()


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    task = db.one_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/tasks", status_code=201)
def create_task(payload: TaskIn):
    return db.add_task(payload.title, bool(payload.done))


@app.put("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskIn):
    task = db.edit_task(task_id, payload.title, payload.done)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    if not db.remove_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
