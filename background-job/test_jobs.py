"""Plain asserts over the parts that do not need a running job server.

Run it with:  .venv/bin/python test_jobs.py
"""

import datetime

from fastapi.testclient import TestClient

import main
from main import expired, new_id, summarise

client = TestClient(main.app)
NOW = datetime.datetime(2026, 9, 17, 12, 0, tzinfo=datetime.timezone.utc)


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"  ok  {name}")


def ago(minutes):
    return (NOW - datetime.timedelta(minutes=minutes)).isoformat()


print("input validation happens before any job is created")
r = client.post("/reports", json={})
check("a body with no topic is a 400", r.status_code == 400)
check("the error names the field", r.json() == {"error": "topic: Field required"})

r = client.post("/reports", json={"topic": "   "})
check("a blank topic is a 400", r.status_code == 400)

r = client.post("/reports", json={"topic": 42})
check("a topic of the wrong type is a 400", r.status_code == 400)

print("reading reports")
check("an unknown id is a 404", client.get("/reports/nosuchid").status_code == 404)
check("the list endpoint starts empty", client.get("/reports").json()["count"] == 0)
check("health is ok", client.get("/health").json() == {"status": "ok"})

print("the heartbeat summary")
check("no reports reads as all zeros",
      summarise({}) == "heartbeat: 0 reports, 0 pending, 0 done, 0 failed")
check("each status is counted separately",
      summarise({
          "a": {"status": "pending"},
          "b": {"status": "done"},
          "c": {"status": "done"},
          "d": {"status": "failed"},
      }) == "heartbeat: 4 reports, 1 pending, 2 done, 1 failed")
check("a report with no status counts as pending",
      summarise({"a": {}}) == "heartbeat: 1 reports, 1 pending, 0 done, 0 failed")

print("the cleanup cron only removes old finished work")
sample = {
    "old": {"status": "done", "finished_at": ago(20)},
    "fresh": {"status": "done", "finished_at": ago(2)},
    "pending": {"status": "pending"},
    "failed_old": {"status": "failed", "finished_at": ago(20)},
}
old = expired(sample, NOW)
check("a report finished 20 minutes ago is expired", "old" in old)
check("a report finished 2 minutes ago is kept", "fresh" not in old)
check("a pending report is never expired", "pending" not in old)
check("a failed report is kept for inspection", "failed_old" not in old)
check("exactly one report expired", len(old) == 1)

print("report ids never overwrite an existing report")
taken = {"aaaaaaaa": {}, "bbbbbbbb": {}}
sequence = iter(["aaaaaaaa", "bbbbbbbb", "cccccccc"])
check("a taken id is skipped rather than reused",
      new_id(taken, generate=lambda: next(sequence)) == "cccccccc")
check("an id is free straight away when nothing is taken",
      new_id({}, generate=lambda: "dddddddd") == "dddddddd")
check("real ids are eight hex characters",
      len(new_id({})) == 8 and all(c in "0123456789abcdef" for c in new_id({})))

print("\nall checks passed")
