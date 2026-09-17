"""Report API with background jobs, v2. Generated from prompt-v2.md. Not edited afterwards."""

import datetime
import uuid

import inngest
import inngest.fast_api
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Report API")

inngest_client = inngest.Inngest(app_id="report-api", is_production=False)

reports: dict[str, dict] = {}


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class ReportRequest(BaseModel):
    topic: str


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc: RequestValidationError):
    err = exc.errors()[0]
    field = ".".join(str(p) for p in err["loc"][1:]) or "body"
    return JSONResponse(status_code=400, content={"error": f"{field}: {err['msg']}"})


@app.exception_handler(HTTPException)
async def http_error(request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/reports", status_code=202)
async def create_report(body: ReportRequest):
    if not body.topic.strip():
        raise HTTPException(status_code=400, detail="topic must not be blank")

    report_id = str(uuid.uuid4())
    reports[report_id] = {
        "id": report_id,
        "topic": body.topic,
        "status": "pending",
        "result": None,
    }

    await inngest_client.send(
        inngest.Event(
            name="report/requested",
            data={"id": report_id, "topic": body.topic},
        )
    )

    return {"id": report_id, "status": "pending"}


@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    if report_id not in reports:
        raise HTTPException(status_code=404, detail="report not found")
    return reports[report_id]


@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context) -> str:
    await ctx.step.sleep("sleep-five", datetime.timedelta(seconds=5))
    return "Hello from the background!"


async def on_report_failed(ctx: inngest.Context) -> None:
    report_id = ctx.event.data["event"]["data"]["id"]
    existing = reports.get(report_id, {"id": report_id})
    reports[report_id] = {**existing, "status": "failed", "failed_at": utc_now()}


@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2,
    on_failure=on_report_failed,
)
async def make_report(ctx: inngest.Context) -> dict:
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    await ctx.step.sleep("slow-work", datetime.timedelta(seconds=8))

    async def build_report():
        existing = reports.get(report_id)
        if existing and existing.get("status") == "done":
            return existing["result"]

        if topic == "fail":
            raise Exception("Report generation failed!")

        result = f"Report about {topic}, generated at {utc_now()}"
        previous = reports.get(report_id, {"id": report_id, "topic": topic})
        reports[report_id] = {
            **previous,
            "status": "done",
            "result": result,
            "finished_at": utc_now(),
        }
        return result

    result = await ctx.step.run("build-report", build_report)
    return {"id": report_id, "result": result}


@inngest_client.create_function(
    fn_id="report-stats",
    trigger=inngest.TriggerCron(cron="* * * * *"),
)
async def report_stats(ctx: inngest.Context) -> str:
    counts = {"pending": 0, "done": 0, "failed": 0}
    for r in reports.values():
        counts[r.get("status", "pending")] = counts.get(r.get("status", "pending"), 0) + 1

    line = (f"Reports: {counts['pending']} pending, "
            f"{counts['done']} done, {counts['failed']} failed")
    ctx.logger.info(line)
    print(line)
    return line


inngest.fast_api.serve(app, inngest_client, [say_hello, make_report, report_stats])
