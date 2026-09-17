"""Plain asserts over the schema, the parser and the retry policy. No model, no network.

Run it with:  .venv/bin/python test_llm.py
"""

import json
import os
import sys
from pathlib import Path

os.environ["LLM_STUB"] = "1"
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "test-model")

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import openai  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

import main  # noqa: E402
from llm.client import NEVER_RETRY, WORTH_RETRYING, backoff_for  # noqa: E402
from llm.pipeline import (  # noqa: E402
    Unusable, cache_key, extract_json, parse_and_validate)
from llm.schema import FALLBACK, STUB, Classification  # noqa: E402

client = TestClient(main.app)
GOOD = {"genre": "poetry", "audience": "adult", "confidence": 0.8, "one_line": "A collection."}


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"  ok  {name}")


def rejects(payload) -> bool:
    try:
        Classification.model_validate(payload)
        return False
    except ValidationError:
        return True


print("the output schema is a closed contract")
check("a valid classification passes", Classification.model_validate(GOOD).genre == "poetry")
check("a genre outside the list is rejected", rejects({**GOOD, "genre": "cookbook"}))
check("an audience outside the list is rejected", rejects({**GOOD, "audience": "teens"}))
check("confidence above 1 is rejected", rejects({**GOOD, "confidence": 1.5}))
check("confidence below 0 is rejected", rejects({**GOOD, "confidence": -0.1}))
check("an invented extra field is rejected", rejects({**GOOD, "vibe": "great"}))
check("a missing field is rejected", rejects({k: v for k, v in GOOD.items() if k != "genre"}))
check("an over-long one_line is rejected", rejects({**GOOD, "one_line": "x" * 161}))
check("the stub satisfies the schema", STUB.genre == "other")
check("the fallback satisfies the schema", FALLBACK.confidence == 0.0)

print("the parser survives what models actually send")
check("a bare object", extract_json(json.dumps(GOOD)).startswith("{"))
check("a fenced object", json.loads(extract_json(f"```json\n{json.dumps(GOOD)}\n```"))
      == GOOD)
check("a chatty preamble", json.loads(
    extract_json(f"Sure! Here is the JSON:\n```json\n{json.dumps(GOOD)}\n```")) == GOOD)
check("trailing prose", json.loads(
    extract_json(f"{json.dumps(GOOD)}\nHope that helps!")) == GOOD)

for bad, label in [("I cannot help with that.", "a refusal"), ("", "an empty answer")]:
    try:
        extract_json(bad)
        raise AssertionError(f"FAILED: {label} should be Unusable")
    except Unusable:
        print(f"  ok  {label} raises Unusable rather than crashing")

print("validation catches what parsing cannot")
try:
    parse_and_validate(json.dumps({**GOOD, "genre": "pirate-treasure"}))
    raise AssertionError("FAILED: an invented genre should be Unusable")
except Unusable as exc:
    check("a well-formed object with a forbidden genre is still a failure",
          "genre" in str(exc))

print("the retry policy knows what not to repeat")
check("a 401 is never retried", openai.AuthenticationError in NEVER_RETRY)
check("a 403 is never retried", openai.PermissionDeniedError in NEVER_RETRY)
check("a 400 is never retried", openai.BadRequestError in NEVER_RETRY)
check("a timeout is retried", openai.APITimeoutError in WORTH_RETRYING)
check("a 429 is retried", openai.RateLimitError in WORTH_RETRYING)
check("a 5xx is retried", openai.InternalServerError in WORTH_RETRYING)
check("backoff grows between attempts", backoff_for(1, Exception()) < backoff_for(3, Exception()))


class FakeResponse:
    headers = {"retry-after": "7"}


class Throttled(Exception):
    response = FakeResponse()


check("Retry-After is obeyed instead of guessed", backoff_for(1, Throttled()) == 7.0)

print("the cache key")
book = {"title": "Olio", "description": "A poetry collection."}
check("the same book and prompt give the same key",
      cache_key(book, "book-genre-v1") == cache_key(book, "book-genre-v1"))
check("a different book gives a different key",
      cache_key(book, "book-genre-v1")
      != cache_key({**book, "title": "Other"}, "book-genre-v1"))
check("changing the prompt version invalidates the entry",
      cache_key(book, "book-genre-v1") != cache_key(book, "book-genre-v2"))
check("key order in the payload does not change the key",
      cache_key({"title": "A", "description": "B"}, "v1")
      == cache_key({"description": "B", "title": "A"}, "v1"))

print("the endpoint validates before it ever calls a model")
check("a missing description is a 400",
      client.post("/classify", json={"title": "x"}).status_code == 400)
check("the error names the field",
      client.post("/classify", json={"title": "x"}).json()["error"].startswith("description"))
check("a blank title is a 400",
      client.post("/classify", json={"title": " ", "description": "x"}).status_code == 400)
check("an over-long description is a 400",
      client.post("/classify",
                  json={"title": "x", "description": "y" * 4001}).status_code == 400)
check("stub mode returns a schema-valid answer with no model",
      Classification.model_validate(
          client.post("/classify", json={"title": "x", "description": "y"}).json()).genre
      == "other")

print("\nall checks passed")
