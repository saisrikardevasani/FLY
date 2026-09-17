"""One runnable check for the whole CRUD cycle, run against the real tasks.db.

Run it with: .venv/bin/python test_api.py
It calls POST /reset first, so it leaves tasks.db holding the three example tasks.
"""

from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def ids(response):
    return [task["id"] for task in response.json()]


def test_crud_cycle():
    client.post("/reset")

    assert client.get("/").json()["name"] == "Task API"
    # The extras made /health check the database too, which is the one assertion in this file
    # that A3 changed. Everything below it is the A1 test, unedited.
    assert client.get("/health").json() == {"status": "ok", "db": "ok"}
    assert len(client.get("/tasks").json()) == 3

    created = client.post("/tasks", json={"title": "Buy milk"})
    assert created.status_code == 201
    task_id = created.json()["id"]
    assert created.json()["done"] is False

    assert client.get(f"/tasks/{task_id}").status_code == 200
    assert client.get("/tasks/99").status_code == 404
    assert client.get("/tasks/99").json() == {"error": "Task 99 not found"}

    updated = client.put(f"/tasks/{task_id}", json={"title": "Buy oat milk", "done": True})
    assert updated.status_code == 200
    assert updated.json()["title"] == "Buy oat milk"
    assert updated.json()["done"] is True
    # The extras added timestamps: an edit moves updated_at, it never moves created_at.
    assert updated.json()["updated_at"] >= created.json()["created_at"]
    assert updated.json()["created_at"] == created.json()["created_at"]
    assert client.put("/tasks/99", json={"title": "x"}).status_code == 404

    # A PUT without "done" must leave an already-finished task finished.
    assert client.put("/tasks/1", json={"title": "Read the assignment"}).json()["done"] is True

    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.delete(f"/tasks/{task_id}").status_code == 404
    assert len(client.get("/tasks").json()) == 3


def test_validation_and_extras():
    client.post("/reset")

    for bad in ({}, {"title": ""}, {"title": "   "}):
        assert client.post("/tasks", json=bad).status_code == 400
        assert client.put("/tasks/1", json=bad).status_code == 400

    assert ids(client.get("/tasks?done=true")) == [1]
    assert ids(client.get("/tasks?search=github")) == [3]
    assert ids(client.get("/tasks?search=the")) == [1, 2]
    assert len(client.get("/tasks?limit=2&offset=2").json()) == 1
    assert client.get("/stats").json() == {"total": 3, "done": 1, "open": 2}

    # Sorting happens in SQL, so it orders the whole table rather than one page of it.
    assert ids(client.get("/tasks?sort=title")) == [2, 3, 1]
    assert client.get("/tasks?sort=title;DROP TABLE tasks").status_code == 400
    assert len(client.get("/tasks").json()) == 3


if __name__ == "__main__":
    test_crud_cycle()
    test_validation_and_extras()
    print("all checks passed")
