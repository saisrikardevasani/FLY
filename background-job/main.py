"""A7, the background job. A normal API that hands slow work to a worker."""

import datetime

import inngest
import inngest.fast_api
from fastapi import FastAPI

app = FastAPI(
    title="Report API",
    version="1.0",
    description="Accepts a report request straight away and builds it in the background.",
)

# is_production=False points the client at the local Dev Server on port 8288.
inngest_client = inngest.Inngest(app_id="report-api", is_production=False)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context) -> str:
    """Proof that work can happen somewhere other than inside a request."""
    await ctx.step.sleep("nap", datetime.timedelta(seconds=5))
    return "Hello from the background!"


inngest.fast_api.serve(app, inngest_client, [say_hello])
