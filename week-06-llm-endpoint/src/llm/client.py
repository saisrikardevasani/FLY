"""The model client. One place that knows a provider exists.

Everything here is about the other 9,999 calls: a timeout that is not ten minutes, a
retry policy that knows which failures are worth repeating, and a log line per call so
"what would this cost at ten thousand a day" is a question with an answer.
"""

import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import openai
from openai import OpenAI

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
CALL_LOG = Path(__file__).resolve().parent.parent.parent / "logs" / "calls.jsonl"

# Low temperature: the same book should get the same answer twice. This is a
# classification, not a creative writing exercise.
TEMPERATURE = 0.0

# The SDK default is ten minutes. Leaving it means one slow call holds an HTTP connection
# open for ten minutes and the endpoint looks dead. Configurable so the timeout path can
# actually be tested without waiting half a minute for it.
TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))

# Retries are mine, not the SDK's. max_retries=0 below turns its own two off, so that a
# log line saying "one call" means one call.
MAX_ATTEMPTS = 3
BASE_BACKOFF = 1.0

# A bad key is still a bad key in four seconds, and a 400 is still malformed. Repeating
# either burns quota and achieves nothing.
NEVER_RETRY = (
    openai.BadRequestError,
    openai.AuthenticationError,
    openai.PermissionDeniedError,
    openai.NotFoundError,
    openai.UnprocessableEntityError,
)
WORTH_RETRYING = (
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.InternalServerError,
    openai.APIConnectionError,
)


class ModelUnavailable(Exception):
    """The provider could not be reached or refused in a way no retry would fix."""

    def __init__(self, message: str, timed_out: bool = False):
        super().__init__(message)
        self.timed_out = timed_out


def load_prompt(version: str = "book-genre-v2") -> str:
    """Prompts are code. They live in a file, get a version, and can be diffed."""
    return (PROMPTS_DIR / f"{version}.md").read_text(encoding="utf-8")


def build_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        timeout=float(os.environ.get("LLM_TIMEOUT_SECONDS", TIMEOUT_SECONDS)),
        max_retries=0,
    )


def backoff_for(attempt: int, error: Exception) -> float:
    """Exponential with jitter, unless the server told us exactly how long to wait."""
    after = getattr(getattr(error, "response", None), "headers", {}) or {}
    retry_after = after.get("retry-after") if hasattr(after, "get") else None
    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            pass
    return BASE_BACKOFF * (2 ** (attempt - 1)) + random.uniform(0, 0.3)


def log_call(record: dict) -> None:
    """One structured line per call. You cannot manage what you do not measure."""
    CALL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with CALL_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def ask(system_prompt: str, payload: dict, prompt_version: str = "book-genre-v2",
        repairs: int = 0) -> str:
    """Send the book as a user message and return whatever text comes back.

    The caller's data never goes into the system prompt: it stays in the user message and
    is JSON encoded, so it cannot break out of its own quotes and be read as instructions.
    """
    client = build_client()
    model = os.environ["LLM_MODEL"]
    started = time.monotonic()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=TEMPERATURE,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            )
        except NEVER_RETRY as exc:
            log_call({
                "at": datetime.now(timezone.utc).isoformat(),
                "prompt_version": prompt_version, "model": model,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "attempts": attempt, "repairs": repairs,
                "outcome": "failed", "retryable": False,
                "error": type(exc).__name__,
            })
            raise ModelUnavailable(f"{type(exc).__name__}: {exc}") from exc
        except WORTH_RETRYING as exc:
            if attempt == MAX_ATTEMPTS:
                log_call({
                    "at": datetime.now(timezone.utc).isoformat(),
                    "prompt_version": prompt_version, "model": model,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                    "attempts": attempt, "repairs": repairs,
                    "outcome": "failed", "retryable": True,
                    "error": type(exc).__name__,
                })
                raise ModelUnavailable(
                    f"{type(exc).__name__} after {attempt} attempts: {exc}",
                    timed_out=isinstance(exc, openai.APITimeoutError),
                ) from exc
            time.sleep(backoff_for(attempt, exc))
            continue

        usage = response.usage
        log_call({
            "at": datetime.now(timezone.utc).isoformat(),
            "prompt_version": prompt_version,
            "model": model,
            "input_tokens": getattr(usage, "prompt_tokens", None),
            "output_tokens": getattr(usage, "completion_tokens", None),
            "duration_ms": round((time.monotonic() - started) * 1000),
            "attempts": attempt,
            "repairs": repairs,
            "outcome": "ok",
        })
        return response.choices[0].message.content or ""

    raise ModelUnavailable("exhausted every attempt")
