"""A8, the PDF report generator. Query, render, serve."""

from fastapi import FastAPI

app = FastAPI(
    title="Report PDF API",
    version="1.0",
    description="Turns the books table into a printable PDF report.",
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
