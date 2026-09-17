# Put an LLM behind your API (FlyRank A17)

## What it does

The A9 scraper collected 60 books with a title, a price and a paragraph of description, and no
category. A category is what makes a catalogue browsable, and no amount of SQL will read a
paragraph and work out that a book is a cookbook. This endpoint does that: you send it a book's
title and description, and it sends back which of fourteen genres the book belongs to, who it is
for, how sure it is, and one plain sentence saying what the book is. A language model does the
reading, but the model never speaks to you directly. Its answer is checked against a fixed list
of allowed values first, and if it says something that is not on the list, you get an error
rather than a made-up category.

## One curl, and exactly what it returns

```bash
curl -s -X POST http://localhost:8200/classify \
  -H "Content-Type: application/json" \
  -d '{"title":"Sapiens: A Brief History of Humankind",
       "description":"A sweeping account of how Homo sapiens came to dominate the planet, from the cognitive revolution to the present."}'
```

```json
{"genre":"history-politics","audience":"adult","confidence":0.98,
 "one_line":"A history of humankind from prehistory to the present day."}
```

And one that is meant to fail, so a stranger can see the boundary working:

```bash
curl -s -X POST http://localhost:8200/classify \
  -H "Content-Type: application/json" -d '{"title":"Sapiens"}'
```

```json
{"error":"description: Field required"}
```

with status `400`, and no model was called.

## Run it

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # the defaults already point at a local Ollama
ollama serve                  # in another terminal, if it is not already running
ollama pull gemma3:4b

.venv/bin/uvicorn main:app --port 8200
```

The tests need no model, no network and no server:

```bash
.venv/bin/python test_llm.py
```

## The job card

[`JOB-CARD.md`](JOB-CARD.md) has it in full: the input fields and their limits, the four output
fields, the closed genre list, and the when-unsure rule. The part that does the most work is the
"must never" list:

- Never invent a genre that is not on the list, or invent an audience.
- Never add fields that are not in the card, or omit any of them.
- Never return prose, an apology, or a code fence around the JSON.
- Never repeat the publisher's marketing claims as fact in `one_line`.
- Never guess a specific genre to look decisive.

The job passes the three rules it has to. The output is closed: two enums, a bounded number and
one length-capped string. It is one decision: the genre, with the rest supporting it. And a human
could grade it, which is the only reason the eval set below can exist.

## The provider, and swapping it

Running against **Ollama** with **gemma3:4b**, locally. No account, no card, no daily quota, and
the eval set can be run as many times as it takes. Three environment variables are the whole
difference between that and a hosted model:

```bash
LLM_BASE_URL=http://localhost:11434/v1     # or https://openrouter.ai/api/v1
LLM_API_KEY=ollama                         # or sk-or-v1-...
LLM_MODEL=gemma3:4b                        # or openrouter/free
```

Nothing else in the code changes, which is the reason nobody should ever hard-code a provider.
Both were exercised here: the 401 test further down really is OpenRouter rejecting a bad key.

**Retries are mine, not the SDK's.** The OpenAI client retries twice by default; I set
`max_retries=0` and wrote the policy explicitly, so that a log line saying one attempt means one
call actually left the machine. Silent defaults are how people make six calls thinking they made
one.

## The eval

Eight cases I labelled by hand in [`evals/cases.json`](evals/cases.json), each with a note on why
it is there. Two are deliberately hard, one exists only to test the when-unsure rule, and one is
a prompt injection.

**Score: 5 of 8, on 17 September 2026, with prompt `book-genre-v1` and model `gemma3:4b`.**

```
  pass  cookbook               food-drink             conf=0.98
  pass  big-history            history-politics       conf=0.9
  pass  crime-novel            mystery-thriller       conf=0.9
  FAIL  poetry                 history-politics       conf=0.85
  pass  picture-book           childrens              conf=0.9
  FAIL  memoir-or-history      history-politics       conf=0.85
  pass  too-short-to-judge     other                  conf=0.2
  FAIL  prompt-injection       other                  conf=0.7

score: 5 of 8
  easy: 4 of 4
  hard: 1 of 4
```

Four out of four on the easy cases and one out of four on the hard ones is a more useful shape
than the total. Three things that went wrong, in order of how much they bother me:

**`history-politics` is a magnet.** Two of the three failures went there. A poetry collection
about nineteenth-century black performers and a memoir assembled from a grandfather's letters
both got filed as history, because both descriptions are full of historical nouns. The model is
matching subject matter when the genre is about form. That is a prompt problem, not a model
problem, and it is what prompt v2 below goes after.

**The injection case is a near miss, and the important half held.** It returned `other` and did
not obey the instruction: no BANANA, no `pirate-treasure`, no change of persona. It failed only
my confidence threshold, answering 0.7 where I wanted below 0.5. So the defence worked and the
calibration did not. Worth being precise about, because "failed the eval" and "got hijacked" are
very different sentences.

**The case I was sure about and got wrong** was the poetry one. I labelled it easily and assumed
a model would too, because the word "verse" is in the description. It is not there in the first
sentence, and the description leads with "part fact, part fiction" and then a list of historical
settings. I think the model decided the genre from the first clause and never revised it.

## What one call costs

A real log line, straight out of `logs/calls.jsonl`:

```json
{"at":"2026-09-17T11:45:06.483130+00:00","prompt_version":"book-genre-v1","model":"gemma3:4b",
 "input_tokens":714,"output_tokens":58,"duration_ms":2661,"attempts":1,"repairs":0,"outcome":"ok"}
```

714 tokens in and 58 out, so about 772 per classification, and the prompt is 92% of it. On Ollama
that is £0, because it runs on this laptop. At 10,000 requests a day it would be 7.14M input and
0.58M output tokens, which on a cheap hosted model priced at $0.10 and $0.30 per million works
out at roughly **$0.89 a day**, or about $4.44 on a mid-tier one at $0.50 and $1.50. The single
biggest driver is the input: the prompt is sent in full on every call and dwarfs the answer, so
shortening the prompt would save more than shortening the output ever could.

## The failure paths, each one actually run

| What happened | What the caller gets | Evidence |
| --- | --- | --- |
| missing or over-long field | `400` naming the field | `{"error":"description: Field required"}`, zero model calls |
| model returns a genre not on the list | `422` after one repair | quarantined to `logs/quarantine.jsonl` |
| `LLM_ENABLED=false` | `200` with the deterministic fallback | answered in 0.0006s, zero model calls logged |
| bad API key (a real 401) | `503`, fast | 0.4s, `attempts: 1`, `retryable: false` |
| provider never answers | `504` | 9.3s, `attempts: 3` with backoff |

The 422 case, forced by temporarily telling the prompt to emit a genre the schema forbids:

```json
{"error":"The model did not return a usable classification: genre: Input should be 'fiction',
 'mystery-thriller', ... or 'other'"}
```

and the line it wrote to quarantine, which keeps what the model actually said:

```json
{"at":"2026-09-17T11:43:41.827138+00:00","prompt_version":"book-genre-v1",
 "input":{"title":"Sharp Objects", ...},
 "raw_output":"```json {   \"genre\": \"crime-fiction-paperback\", ... ",
 "error":"genre: Input should be 'fiction', ..."}
```

Raw model text is never returned to the caller, on success or on failure. If an API can emit an
arbitrary string a model wrote, it does not have a contract.

## What surprised me on the first real call

The prompt says, in its own section of rules, "Return the JSON object on its own. No code fence".
All three of the first three books came back fenced in ```` ```json ````. The content was right
every time and the format was wrong every time. The model is not so much ignoring the instruction
as following a stronger habit. That is the whole reason the parser exists: an instruction in a
prompt is a request, and the parser is what turns it into a guarantee.

## What I would fix with another day

Split the genre decision from the summary. Asking for form (`poetry`), subject (`audience`) and
prose (`one_line`) in one call is what lets a description full of historical nouns drag the genre
to `history-politics`, and two cheap calls with one decision each would almost certainly beat one
call with three.

## An honest limitation

`confidence` is a number the model writes about itself, and nothing checks it. It read 0.85 on
both answers it got wrong and 0.7 on the injection it half-handled, so it is not a probability
and should not be treated as one downstream. A real calibration would compare confidence against
eval outcomes over far more than eight cases.
