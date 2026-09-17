"""A17, an LLM behind an API. The model is a component, not the contract."""

import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from llm.pipeline import Unusable, classify as run_pipeline  # noqa: E402
from llm.schema import STUB, ClassifyIn, Classification  # noqa: E402

load_dotenv()

app = FastAPI(
    title="Book classifier",
    version="1.0",
    description="Reads a scraped book description and returns a checked classification.",
)


def flag(name: str, default: str) -> str:
    return os.environ.get(name, default).strip().lower()


@app.exception_handler(RequestValidationError)
async def invalid_body(request, exc: RequestValidationError) -> JSONResponse:
    """Bad input is a 400 naming the field, and it never reaches a model.

    Every request rejected here is a model call nobody paid for.
    """
    problem = exc.errors()[0]
    field = ".".join(p for p in problem["loc"][1:] if isinstance(p, str)) or "body"
    return JSONResponse(status_code=400, content={"error": f"{field}: {problem['msg']}"})


@app.exception_handler(HTTPException)
async def error_shape(request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/classify", response_model=Classification)
async def classify(body: ClassifyIn) -> Classification:
    # Stub mode is not a toy. It is how every later stage gets built without spending a
    # call on a typo, and how the tests run with no model on the machine at all.
    if flag("LLM_STUB", "0") == "1":
        return STUB

    payload = {"title": body.title, "description": body.description}
    try:
        result, _repairs = run_pipeline(payload)
    except Unusable as exc:
        # Never crash, never guess a default and pretend it worked, and never hand the
        # caller the model's raw text. The contract is the schema or an honest 422.
        raise HTTPException(
            status_code=422,
            detail=f"The model did not return a usable classification: {exc}",
        ) from exc
    return result
