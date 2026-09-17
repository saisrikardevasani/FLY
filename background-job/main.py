"""A7, the background job. A normal API that hands slow work to a worker."""

import datetime
import uuid

import inngest
import inngest.fast_api
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Report API",
    version="1.0",
    description="Accepts a report request straight away and builds it in the background.",
)

# is_production=False points the client at the local Dev Server on port 8288.
inngest_client = inngest.Inngest(app_id="report-api", is_production=False)

# Reports live in memory, so a restart forgets them. That is the same lesson as A1 and
# still not a bug: what survives a restart here is the job, not this dictionary.
reports: dict[str, dict] = {}


class ReportIn(BaseModel):
    topic: str


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/reports", status_code=202)
async def request_report(body: ReportIn) -> dict:
    """Take the order, hand back a ticket, and do no slow work at all."""
    report_id = uuid.uuid4().hex[:8]
    reports[report_id] = {"id": report_id, "topic": body.topic, "status": "pending"}

    await inngest_client.send(
        inngest.Event(name="report/requested", data={"id": report_id, "topic": body.topic})
    )

    # 202 Accepted: I have the order, the work starts soon.
    return {"id": report_id, "status": "pending"}


@app.get("/reports/{report_id}")
async def get_report(report_id: str) -> dict:
    report = reports.get(report_id)
    if report is None:
        raise HTTPException(404, f"No report with id {report_id}")
    return report


@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context) -> str:
    """Proof that work can happen somewhere other than inside a request."""
    await ctx.step.sleep("nap", datetime.timedelta(seconds=5))
    return "Hello from the background!"


@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
)
async def make_report(ctx: inngest.Context) -> dict:
    """The slow half of POST /reports, running where nobody is waiting on it."""
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    # Stands in for the real slow thing: an AI call, a big export, a PDF render.
    await ctx.step.sleep("do-the-slow-work", datetime.timedelta(seconds=8))

    async def build() -> dict:
        finished = {
            "id": report_id,
            "topic": topic,
            "status": "done",
            "result": f"Everything worth knowing about {topic}.",
            "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        # Replace the entry rather than editing the pending one in place.
        reports[report_id] = finished
        return finished

    return await ctx.step.run("build-report", build)


inngest.fast_api.serve(app, inngest_client, [say_hello, make_report])
