"""Book classifier endpoint, v2. Generated from prompt-v2.md. Not edited afterwards."""

import json
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from openai import APITimeoutError, OpenAI
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"
LOGS_DIR = BASE_DIR / "logs"

PROMPT_VERSION = "book-genre-v1"

app = FastAPI(title="Book Classifier")

# max_retries=0 turns the SDK's own two retries off, so the only retries are the ones in
# call_model below and one logical call means one HTTP request per attempt.
client = OpenAI(
    base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.getenv("LLM_API_KEY", "ollama"),
    timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
    max_retries=0,
)

Genre = Literal[
    "fiction", "mystery-thriller", "romance", "science-fiction-fantasy",
    "historical", "biography-memoir", "history-politics", "science-nature",
    "food-drink", "art-design", "self-help", "childrens", "poetry", "other",
]
Audience = Literal["adult", "young-adult", "children"]


class ProviderFailed(Exception):
    """The provider could not be reached. Never allowed to escape as a 500."""

    def __init__(self, message: str, timed_out: bool = False):
        super().__init__(message)
        self.timed_out = timed_out


class ClassifyRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)


class ClassifyResponse(BaseModel):
    genre: Genre
    audience: Audience
    confidence: float = Field(ge=0.0, le=1.0)
    one_line: str = Field(min_length=1, max_length=160)


STUB_RESPONSE = ClassifyResponse(
    genre="other", audience="adult", confidence=0.5,
    one_line="Stub response for testing.",
)

FALLBACK_RESPONSE = ClassifyResponse(
    genre="other", audience="adult", confidence=0.0,
    one_line="Classification is currently disabled.",
)


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc: RequestValidationError):
    error = exc.errors()[0]
    field = ".".join(str(p) for p in error["loc"][1:]) or "body"
    return JSONResponse(status_code=400, content={"error": f"{field}: {error['msg']}"})


def load_prompt() -> str:
    return (PROMPTS_DIR / f"{PROMPT_VERSION}.md").read_text()


def log_call(**kwargs):
    LOGS_DIR.mkdir(exist_ok=True)
    entry = {"timestamp": datetime.now().isoformat(), "prompt_version": PROMPT_VERSION, **kwargs}
    with open(LOGS_DIR / "calls.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def quarantine(input_data: dict, raw_output: str, error: str):
    LOGS_DIR.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt_version": PROMPT_VERSION,
        "input": input_data,
        "raw_output": raw_output,
        "error": error,
    }
    with open(LOGS_DIR / "quarantine.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def extract_json(text: str) -> str:
    """Strip code fences and any chatter around the JSON object."""
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output")
    return text[start:end + 1]


def call_model(messages: list, max_retries: int = 3) -> tuple:
    """Call the model with retries on transient errors."""
    start = time.time()
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "gemma3:4b"),
                messages=messages,
                temperature=0.0,
            )
            duration_ms = int((time.time() - start) * 1000)
            usage = response.usage
            return response.choices[0].message.content, {
                "model": os.getenv("LLM_MODEL", "gemma3:4b"),
                "input_tokens": usage.prompt_tokens if usage else None,
                "output_tokens": usage.completion_tokens if usage else None,
                "duration_ms": duration_ms,
                "attempts": attempt + 1,
            }
        except Exception as e:
            last_error = e
            status = getattr(e, "status_code", None)
            if status in (400, 401, 403):
                raise ProviderFailed(f"{type(e).__name__}: {e}")
            if attempt < max_retries - 1:
                time.sleep((2 ** attempt) + random.uniform(0, 0.5))

    raise ProviderFailed(
        f"{type(last_error).__name__} after {max_retries} attempts: {last_error}",
        timed_out=isinstance(last_error, APITimeoutError),
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_error_handler(request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


# A plain def, not async def: the model call below is blocking, and inside an async def it
# would hold the event loop and make every other request wait behind it.
@app.post("/classify", response_model=ClassifyResponse)
def classify(request: ClassifyRequest):
    if os.getenv("LLM_STUB") == "1":
        return STUB_RESPONSE

    if os.getenv("LLM_ENABLED", "true").lower() == "false":
        return FALLBACK_RESPONSE

    payload = {"title": request.title, "description": request.description}
    messages = [
        {"role": "system", "content": load_prompt()},
        {"role": "user", "content": json.dumps(payload)},
    ]

    try:
        raw, meta = call_model(messages)
    except ProviderFailed as e:
        raise HTTPException(
            status_code=504 if e.timed_out else 503,
            detail=f"The classifier is unavailable: {e}",
        )

    try:
        parsed = ClassifyResponse.model_validate_json(extract_json(raw))
        log_call(**meta, repairs=0, outcome="ok")
        return parsed
    except (ValidationError, ValueError) as first_error:
        error_text = str(first_error)

    repair_messages = messages + [
        {"role": "assistant", "content": raw},
        {"role": "user", "content":
            f"Your previous answer was rejected: {error_text}. "
            f"Return only corrected JSON matching the schema."},
    ]
    try:
        repaired, repair_meta = call_model(repair_messages)
    except ProviderFailed as e:
        raise HTTPException(
            status_code=504 if e.timed_out else 503,
            detail=f"The classifier is unavailable during repair: {e}",
        )

    try:
        parsed = ClassifyResponse.model_validate_json(extract_json(repaired))
        log_call(**repair_meta, repairs=1, outcome="ok")
        return parsed
    except (ValidationError, ValueError) as second_error:
        quarantine(payload, repaired, str(second_error))
        log_call(**repair_meta, repairs=1, outcome="failed")
        raise HTTPException(
            status_code=422,
            detail=f"Model output failed validation: {second_error}",
        )
