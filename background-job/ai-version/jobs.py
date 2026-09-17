"""Report API with background jobs. Generated from prompt-v1.md. Not edited afterwards."""

import datetime
import uuid

import inngest
import inngest.fast_api
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Report API")

inngest_client = inngest.Inngest(app_id="report-api", is_production=False)

reports: dict[str, dict] = {}


class ReportRequest(BaseModel):
    topic: str | None = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/reports", status_code=202)
async def create_report(body: ReportRequest):
    if not body.topic or not body.topic.strip():
        raise HTTPException(status_code=400, detail="topic is required")

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


@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2,
)
async def make_report(ctx: inngest.Context) -> dict:
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    await ctx.step.sleep("slow-work", datetime.timedelta(seconds=8))

    async def build_report():
        if topic == "fail":
            raise Exception("Report generation failed!")

        result = f"Report about {topic}: generated at {datetime.datetime.now()}"
        reports[report_id]["status"] = "done"
        reports[report_id]["result"] = result
        return result

    result = await ctx.step.run("build-report", build_report)
    return {"id": report_id, "result": result}


@inngest_client.create_function(
    fn_id="report-stats",
    trigger=inngest.TriggerCron(cron="* * * * *"),
)
async def report_stats(ctx: inngest.Context) -> str:
    pending = sum(1 for r in reports.values() if r["status"] == "pending")
    done = sum(1 for r in reports.values() if r["status"] == "done")
    failed = sum(1 for r in reports.values() if r["status"] == "failed")

    line = f"Reports: {pending} pending, {done} done, {failed} failed"
    ctx.logger.info(line)
    print(line)
    return line


inngest.fast_api.serve(app, inngest_client, [say_hello, make_report, report_stats])
