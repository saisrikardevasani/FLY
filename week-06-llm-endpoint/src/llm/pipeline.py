"""Everything between "the model said something" and "the API returns something".

The model is an external source, so its answer is raw input. It gets parsed, checked
against the schema, given exactly one chance to correct itself, and quarantined if it
still fails. Nothing the model wrote reaches the caller unvalidated.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from .client import ask, load_prompt
from .schema import Classification

QUARANTINE = Path(__file__).resolve().parent.parent.parent / "logs" / "quarantine.jsonl"

# Models like to wrap JSON in a fence, and to say "Sure! Here is the JSON:" first.
FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

REPAIR_INSTRUCTION = (
    "Your previous answer was rejected for this reason. Return only corrected JSON "
    "matching the schema, with no code fence and no commentary."
)


# Re-running enrichment over the same scraped records is the case this pays for: the 60
# books get classified again every time the eval or a backfill runs. It would earn nothing
# against free-text support messages, where almost nothing repeats.
_CACHE: dict[str, Classification] = {}
CACHE_STATS = {"hits": 0, "misses": 0}


def cache_key(payload: dict, prompt_version: str) -> str:
    """The prompt version is part of the key. Change the prompt and yesterday's answers
    are stale, so they must not be served."""
    blob = json.dumps({"payload": payload, "prompt": prompt_version}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


class Unusable(Exception):
    """The model's answer could not be turned into a valid classification."""


def extract_json(text: str) -> str:
    """Pull the object out of whatever the model wrapped it in."""
    fenced = FENCE.search(text)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise Unusable("no JSON object found in the model's answer")
    return text[start : end + 1]


def parse_and_validate(text: str) -> Classification:
    """A structurally valid object with a genre we never allowed is still a failure."""
    candidate = extract_json(text)
    try:
        return Classification.model_validate_json(candidate)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise Unusable(problems) from exc
    except json.JSONDecodeError as exc:
        raise Unusable(f"not valid JSON: {exc}") from exc


def quarantine(payload: dict, raw: str, reason: str, prompt_version: str) -> None:
    """Keep what the model actually said, so a failure can be read rather than guessed at."""
    QUARANTINE.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "at": datetime.now(timezone.utc).isoformat(),
        "prompt_version": prompt_version,
        "input": payload,
        "raw_output": raw,
        "error": reason,
    }
    with QUARANTINE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")


def classify(payload: dict, prompt_version: str | None = None) -> tuple[Classification, int]:
    """Ask, check, and if it failed, ask once more with the reason. Returns (result, repairs)."""
    prompt_version = prompt_version or os.environ.get("PROMPT_VERSION", "book-genre-v2")

    key = cache_key(payload, prompt_version)
    if os.environ.get("LLM_CACHE", "1") == "1" and key in _CACHE:
        CACHE_STATS["hits"] += 1
        return _CACHE[key], 0
    CACHE_STATS["misses"] += 1

    system = load_prompt(prompt_version)
    raw = ask(system, payload, prompt_version)

    try:
        result = parse_and_validate(raw)
        _CACHE[key] = result
        return result, 0
    except Unusable as first_failure:
        reason = str(first_failure)

    # One repair, and only one. It fixes most real failures; a second is throwing money
    # at a model that has already shown it cannot do this one.
    repair_payload = {
        "original_input": payload,
        "your_previous_answer": raw,
        "why_it_was_rejected": reason,
        "instruction": REPAIR_INSTRUCTION,
    }
    repaired = ask(system, repair_payload, prompt_version, repairs=1)

    try:
        result = parse_and_validate(repaired)
        _CACHE[key] = result
        return result, 1
    except Unusable as second_failure:
        quarantine(payload, repaired, str(second_failure), prompt_version)
        raise Unusable(str(second_failure)) from second_failure
