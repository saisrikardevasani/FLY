"""A7, the background job. A normal API that hands slow work to a worker."""

from fastapi import FastAPI

app = FastAPI(
    title="Report API",
    version="1.0",
    description="Accepts a report request straight away and builds it in the background.",
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
