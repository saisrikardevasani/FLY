"""A8, the PDF report generator. Query, render, serve."""

import datetime
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

import db
import render

app = FastAPI(
    title="Report PDF API",
    version="1.0",
    description="Turns the books table into a printable PDF report.",
)

db.init()


class ReportIn(BaseModel):
    """Nothing is required. force asks for a fresh report on a day that already has one."""

    force: bool = False
    min_rating: int = Field(default=1, ge=1, le=5)


@app.exception_handler(RequestValidationError)
async def invalid_body(request, exc: RequestValidationError) -> JSONResponse:
    """A body that fails validation is a 400, and every error has the same shape."""
    problem = exc.errors()[0]
    field = ".".join(p for p in problem["loc"][1:] if isinstance(p, str)) or "body"
    return JSONResponse(status_code=400, content={"error": f"{field}: {problem['msg']}"})


@app.exception_handler(HTTPException)
async def error_shape(request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


def link_for(report_id: str) -> str:
    return f"/reports/{report_id}/file"


@app.post("/reports", status_code=201)
def create_report(body: ReportIn | None = None) -> JSONResponse:
    """Run the whole pipeline here in the request: query, render, record.

    This is a plain def rather than async def on purpose. Playwright's sync API cannot
    run inside a running event loop, and FastAPI runs a sync endpoint in a worker thread.
    """
    body = body or ReportIn()
    created = datetime.datetime.now(datetime.timezone.utc)

    # A user double-clicks the button. Every user, every time, forever. One request per
    # day produces one report, and the second caller gets the first one back with a 200
    # rather than a second identical file.
    if not body.force:
        existing = db.report_made_on(created.date().isoformat(), body.min_rating)
        if existing is not None:
            return JSONResponse(
                status_code=200,
                content={"id": existing["id"], "file": link_for(existing["id"])},
            )

    report_id = uuid.uuid4().hex[:12]

    filename = f"{report_id}.pdf"
    data = db.get_report_data(body.min_rating)
    render.render_pdf(render.html_for(data), render.REPORTS_DIR / filename)
    # Store the file name, not an absolute path. An absolute path pins the database to
    # one machine and one home directory, and it has no business in an API response.
    db.save_report(report_id, filename, created.isoformat(), body.min_rating)

    return JSONResponse(
        status_code=201, content={"id": report_id, "file": link_for(report_id)}
    )


@app.get("/reports")
async def list_reports() -> dict:
    """The control panel: every report generated, newest first, with its link."""
    reports = db.list_reports()
    return {
        "count": len(reports),
        "reports": [{**r, "file": link_for(r["id"])} for r in reports],
    }


@app.get("/reports/{report_id}")
async def read_report(report_id: str) -> dict:
    report = db.get_report(report_id)
    if report is None:
        raise HTTPException(404, f"No report with id {report_id}")
    return {
        "id": report["id"],
        "created_at": report["created_at"],
        "file": link_for(report_id),
    }


@app.get("/reports/{report_id}/file")
async def download_report(report_id: str) -> FileResponse:
    """The only endpoint that moves megabytes. The others answer in a few bytes."""
    report = db.get_report(report_id)
    if report is None:
        raise HTTPException(404, f"No report with id {report_id}")
    return FileResponse(
        render.REPORTS_DIR / report["path"], media_type="application/pdf",
        filename=f"bookstore-report-{report['created_at'][:10]}.pdf",
    )
