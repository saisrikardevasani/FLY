# Prompt v1

Written from memory before generating anything, without re-reading the assignment brief. The
generated code goes in this folder and is never edited afterwards.

---

Build me a FastAPI endpoint that puts a language model behind a strict contract.

**The job.** `POST /classify` takes a book's `title` and `description` and returns a
classification: a `genre` from a fixed list, an `audience`, a `confidence` between 0 and 1, and a
`one_line` summary of at most 160 characters.

The genre list is closed: `fiction`, `mystery-thriller`, `romance`, `science-fiction-fantasy`,
`historical`, `biography-memoir`, `history-politics`, `science-nature`, `food-drink`,
`art-design`, `self-help`, `childrens`, `poetry`, `other`. Audience is one of `adult`,
`young-adult`, `children`.

**Validate the input first.** `title` is 1 to 200 characters, `description` is 1 to 4000, both
required. A bad request returns 400 with a JSON error naming the offending field, and no model
call is made. Use Pydantic, with enums for the closed lists.

**The prompt lives in a file**, `prompts/book-genre-v1.md`, not in a string inside the route.
Load it at call time. Send the user's book as a separate user message, never concatenated into
the system prompt.

**Stub mode.** When `LLM_STUB=1`, skip the model entirely and return a hard-coded object that
satisfies the schema, so the endpoint can be developed and tested without calling anything.

**The model's answer is untrusted input.** Parse it: models like to wrap JSON in a code fence or
put "Sure, here's the JSON" in front, so strip that and find the object. Then validate it against
the schema. If parsing or validation fails, make exactly one repair call, sending the broken
output and the validation error back and asking for corrected JSON. If that also fails, return
422 and append a line to `logs/quarantine.jsonl` with the input, the raw output and the error.
Never crash.

**Production fitness.** Set an explicit timeout of 30 seconds on the client. Retry on timeouts,
429 and 5xx with exponential backoff and jitter, and never retry on 400, 401 or 403. Log one
structured line per call with the prompt version, the model, the input and output token counts,
the duration in milliseconds and whether a repair was needed.

**A kill switch.** `LLM_ENABLED=false` skips the model and returns a deterministic fallback that
still satisfies the schema.

Configuration comes from three environment variables, `LLM_BASE_URL`, `LLM_API_KEY` and
`LLM_MODEL`, so the provider can be swapped without touching the code. I am running Ollama
locally with `gemma3:4b` through its OpenAI-compatible endpoint.
