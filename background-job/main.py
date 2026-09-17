"""A7, the background job. A normal API that hands slow work to a worker."""

import datetime
import pathlib
import uuid

import inngest
import inngest.fast_api
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StringConstraints
from typing import Annotated

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

OUTBOX = pathlib.Path(__file__).resolve().parent / "outbox"

# A done report is rubbish after this long, and taking out the rubbish is what most
# real cron jobs actually do.
KEEP_DONE_FOR = datetime.timedelta(minutes=10)


def summarise(current: dict[str, dict]) -> str:
    """One line saying where every report got to."""
    counts = {"pending": 0, "done": 0, "failed": 0}
    for report in current.values():
        status = report.get("status", "pending")
        counts[status] = counts.get(status, 0) + 1
    return (
        f"heartbeat: {len(current)} reports, {counts['pending']} pending, "
        f"{counts['done']} done, {counts['failed']} failed"
    )


def expired(current: dict[str, dict], now: datetime.datetime) -> list[str]:
    """Which done reports are older than KEEP_DONE_FOR."""
    old = []
    for report_id, report in current.items():
        if report.get("status") != "done" or not report.get("finished_at"):
            continue
        if now - datetime.datetime.fromisoformat(report["finished_at"]) > KEEP_DONE_FOR:
            old.append(report_id)
    return old


class ReportIn(BaseModel):
    """A missing or blank topic is the client's mistake, and it is caught here."""

    topic: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


@app.exception_handler(RequestValidationError)
async def invalid_body(request, exc: RequestValidationError) -> JSONResponse:
    """A body that fails validation is a 400, not FastAPI's default 422."""
    problem = exc.errors()[0]
    field = ".".join(p for p in problem["loc"][1:] if isinstance(p, str)) or "body"
    return JSONResponse(status_code=400, content={"error": f"{field}: {problem['msg']}"})


@app.exception_handler(HTTPException)
async def error_shape(request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


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


@app.get("/reports")
async def list_reports() -> dict:
    """The control panel: every report and where it got to."""
    return {"count": len(reports), "reports": list(reports.values())}


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


async def report_failed(ctx: inngest.Context) -> None:
    """Runs once the retries are used up, so a dead job stops looking pending."""
    report_id = ctx.event.data["event"]["data"]["id"]
    previous = reports.get(report_id, {"id": report_id})
    reports[report_id] = {**previous, "status": "failed"}


@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2,  # three attempts in total, so the show is short
    concurrency=[inngest.Concurrency(limit=2)],
    on_failure=report_failed,
)
async def make_report(ctx: inngest.Context) -> dict:
    """The slow half of POST /reports, running where nobody is waiting on it."""
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    async def gather() -> dict:
        """A cheap first step, so a restart has something finished to skip over."""
        return {"topic": topic, "sources": 3}

    facts = await ctx.step.run("gather-facts", gather)

    # Stands in for the real slow thing: an AI call, a big export, a PDF render.
    await ctx.step.sleep("do-the-slow-work", datetime.timedelta(seconds=8))

    async def build() -> dict:
        # The same event delivered twice must not produce two reports. Inngest can
        # redeliver, and a job that is not safe to run twice is a job that will one day
        # send the same customer the same email twice.
        existing = reports.get(report_id)
        if existing and existing.get("status") == "done":
            return existing

        # A wrong moment deserves a retry. This stands in for the oven breaking.
        if topic == "fail":
            raise RuntimeError("The report oven is broken!")

        finished = {
            "id": report_id,
            "topic": topic,
            "status": "done",
            "result": f"Everything worth knowing about {topic}, from {facts['sources']} sources.",
            "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        # Replace the entry rather than editing the pending one in place.
        reports[report_id] = finished

        # Stands in for sending the report somewhere. Writing a file from a job is the
        # same shape as emailing one, without needing a mail server.
        OUTBOX.mkdir(exist_ok=True)
        (OUTBOX / f"{report_id}.txt").write_text(finished["result"], encoding="utf-8")
        return finished

    return await ctx.step.run("build-report", build)


@inngest_client.create_function(
    fn_id="heartbeat",
    trigger=inngest.TriggerCron(cron="* * * * *"),
)
async def heartbeat(ctx: inngest.Context) -> str:
    """Nobody asks for this one. The clock is the only trigger.

    Every minute is for watching it work. A real heartbeat would run daily.
    """
    summary = summarise(reports)
    ctx.logger.info(summary)
    print(summary, flush=True)
    return summary


@inngest_client.create_function(
    fn_id="cleanup",
    trigger=inngest.TriggerCron(cron="*/5 * * * *"),
)
async def cleanup(ctx: inngest.Context) -> str:
    """Every five minutes, throw away reports nobody came back for."""
    now = datetime.datetime.now(datetime.timezone.utc)
    for report_id in expired(reports, now):
        del reports[report_id]
    return summarise(reports)


inngest.fast_api.serve(
    app, inngest_client, [say_hello, make_report, heartbeat, cleanup]
)
