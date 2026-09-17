"""The model client. One place that knows a provider exists."""

import json
import os
from pathlib import Path

from openai import OpenAI

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

# Low temperature: the same book should get the same answer twice. This is a
# classification, not a creative writing exercise.
TEMPERATURE = 0.0


def load_prompt(version: str = "book-genre-v1") -> str:
    """Prompts are code. They live in a file, get a version, and can be diffed."""
    return (PROMPTS_DIR / f"{version}.md").read_text(encoding="utf-8")


def build_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
    )


def ask(system_prompt: str, payload: dict) -> str:
    """Send the book as a user message and return whatever text comes back.

    The caller's data never goes into the system prompt: it stays in the user message and
    is JSON encoded, so it cannot break out of its own quotes and be read as instructions.
    """
    client = build_client()
    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )
    return response.choices[0].message.content or ""
