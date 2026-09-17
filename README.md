# FlyRank internship, Backend AI Engineering track

Nine assignments, built one stage at a time between 18 August and 17 September 2026. Each folder
is self-contained: its own dependencies, its own README, its own tests, and a git log where every
commit is a stage that actually worked when it was made.

109 commits, one per stage, made at the point that stage actually worked. Everything here was
run before it was written down.

## How to read this repo

| Week | Folder | Assignment | What it is |
| --- | --- | --- | --- |
| 2, 3 | [week-02-03-task-api](week-02-03-task-api) | A1, A2, A3 | A task API that grew from a Python list to SQLite to Postgres in Docker |
| 4 | [week-04-auth](week-04-auth) | Auth, login and protect | Supabase issues the tokens, this server only verifies them |
| 5 | [week-05-scraper](week-05-scraper) | The polite scraper | 60 books off a practice site, validated before storage |
| 6 | [week-06-llm-endpoint](week-06-llm-endpoint) | Connect to an AI API | One narrow classification job behind a strict schema |
| 7 | [week-07-background-job](week-07-background-job) | Your first background job | Answer in milliseconds, work for eight seconds |
| 7 | [week-07-pdf-reports](week-07-pdf-reports) | PDF report generator | SQL to a printed A4 document |
| 7 | [week-07-decision-flow](week-07-decision-flow) | AI Decision Flow | A graph you draw, executed by a model answering yes or no |

Weeks 2 and 3 share a folder because they share a codebase. A1 built the API against an
in-memory list, A2 moved it to SQLite and A3 to Postgres behind docker compose, all in the same
files. Splitting them into three folders would have meant three copies of the same app and a git
history that lied about how it was built.

## How this was built

Solo, with Claude Code as a pair. The programme allows this and the capstone brief puts it
plainly: AI help is encouraged, but you own every line.

Eight of the nine assignments set the same bonus exercise, so eight of them carry an "AI vs me"
section: write a specification from memory, have a model build the thing from that alone, keep
the generated code quarantined in `ai-version/` where it is never edited afterwards, then run
both and compare what actually happened. The decision flow is the one without, because its brief
does not ask for it.

That exercise turned out to be the most useful part of the programme, and not for the reason I
expected. It found three real bugs in my own code, which are described below. Every failure it
found in the generated code traced back to a sentence missing from my prompt.

## Week 2 and 3: the task API

A CRUD API for tasks, rebuilt twice underneath the same routes. The point of the assignment was
that storage is an implementation detail: the routes never changed when the data moved from a
list to SQLite to Postgres, because every line of SQL lived in `db.py` and nowhere else.

Finished with docker compose bringing up the API, Postgres and Redis together, a multi-stage
image, and an index on the column the filter actually uses.

**39 commits**, three separate AI rematches, one per assignment.

## Week 4: auth

Five routes, plus a refresh flow and an admin route added as extras. Supabase holds the users.
This server never stores a password and never hashes anything, and the test suite enforces that
by grepping its own source for `bcrypt`, `hashlib`, `passlib` and `sha256`.

The Swagger padlock was verified by driving a real browser: click Authorize, paste the JWT from
`/auth/login`, Try it out, read the 200 back. Screenshots are in `week-04-auth/docs`.

**The problem that took longest** was not code. Signup returned `400 Email signups are disabled`
for an hour. The cause was two toggles in the Supabase dashboard, not the request. Rather than
guess, I asked Supabase what it thought its own configuration was:

```bash
curl -s "$SUPABASE_URL/auth/v1/settings" -H "apikey: $SUPABASE_KEY"
# external.email was false, mailer_autoconfirm was false
```

That turned a vague "it doesn't work" into two named switches and a fix in a minute.

**The mistake worth recording** is the one I nearly published as a vulnerability. The brief says
change one character of the token and watch it fail. I changed the last one and got `200`, which
looks like a guard that does not check the signature. It was not. The signature is 86 base64
characters encoding 64 bytes, so the final character carries two significant bits, and the `Q` I
replaced with `X` shares both. The decoded bytes were identical. The token had not been altered
at all. Flipping a character in the middle produces a genuinely different token and gets the 401.

**12 stage commits**, 37 assertions.

## Week 5: the polite scraper

Three catalogue pages, 60 book pages, one local cache so the site is asked once however many
times the script is restarted. Records are validated against a Pydantic model before storage, and
anything that fails lands in `errors.json` with its reason rather than quietly entering the
dataset.

**The bug that mattered** was invisible until I looked at the data. Prices arrived as `Â£51.77`.
The server sends `Content-Type: text/html` with no charset, so requests falls back to ISO-8859-1
while the page itself declares UTF-8 in a meta tag. Two lines fixed it, reading the encoding from
the page rather than trusting the header.

**The bug I would not have found without a test.** I wrote a check with `or True` on the end,
which made it pass whatever happened. Worthless, so I removed it, and the assertion underneath
then failed for a real reason: `cache_name` was taking the second-to-last path segment, so any URL
ending in a slash became `book-catalogue.html`. Every book would have shared one cache file and
served each other's pages.

**12 stage commits**, 22 assertions, 63 seconds from a clean clone to 60 validated records.

## Week 6: an LLM behind an API

`POST /classify` reads a scraped book description and returns a genre from a closed list, an
audience, a confidence and one line of summary. The model never speaks to the caller directly:
its answer is parsed, checked against a schema, given exactly one repair attempt, and quarantined
to a log file if it still fails.

**The eval is the interesting part.** Eight cases I labelled by hand. The first prompt scored
**5 of 8**. Both failures were the same mistake: a poetry collection about the nineteenth century
and a memoir assembled from letters both landed in `history-politics`, because the model was
matching subject matter when genre is about form. One paragraph added to the prompt saying
exactly that took it to **7 of 8**.

It also made one case worse, which is the part worth keeping. Telling the model to commit to a
form made it commit in general, so a prompt-injection test that v1 hedged on became a confident
wrong answer. One line moved three cases, two up and one down. Without the eval I would have
shipped v2 and called it better.

**On injection**, four attacks went in through the normal input field. None got through: no
forbidden genre, no added field, nothing leaked, including an attempt to break out of the JSON
string. Three things stop it, and only two are about the prompt. The third is the schema, which
does not ask, it enforces.

**On model choice**, I planned to race `gemma3:4b` against `qwen3.5` and publish both scores.
The latency answered first: 3.1 seconds a call against 195, with two of six attempts never
returning. I stopped the run rather than spend forty minutes on it. A model that cannot answer
inside a request timeout is not a candidate whatever it scores, and that is a more useful thing
to have learned than a second number.

**11 stage commits**, 34 assertions.

## Week 7: your first background job

`POST /reports` answers `202` in 1.9 milliseconds and hands back an id. The eight seconds of work
happen in an Inngest function where nobody is waiting.

**The experiment I am most pleased with** is the durability one. I started a job, killed the API
three seconds in while it was mid-sleep, and brought it back five seconds later:

| Step | Started | Ended | Attempts |
| --- | --- | --- | --- |
| `gather-facts` | 10:39:49 | 10:39:49 | 0 |
| `do-the-slow-work` | 10:39:49 | 10:39:57 | 0 |
| `build-report` | 10:39:57 | 10:40:15 | 1 |

The first step finished before the process died and never ran again. The sleep carried on across
the outage because the Dev Server was counting it, not the dead process. The third step came due
while the API was still down, failed to reach it, retried, and succeeded five seconds after it
came back. The report was done at 10:40:15 even though the process that accepted it no longer
existed.

**One box I could not tick.** The concurrency cap is configured and the Dev Server confirms it
registered, but queueing five jobs and sampling every two seconds showed all five running at
once. The configuration is right and the local Dev Server does not enforce it. That box is marked
configured but unverified rather than ticked, because I watched the opposite of what it claims.

**11 stage commits**, 18 assertions.

## Week 7: PDF report generator

SQL to a printed document. The four aggregations run against the 60 books the week 5 scraper
collected, and Playwright prints the resulting page to A4.

**The trap the brief warns about is real.** The first render put the table headings on page one
and nowhere else, so pages two and three were columns of numbers with nothing saying which was
the price. Two CSS rules fix it, `display: table-header-group` on the `thead` and
`break-inside: avoid` on the rows.

No row happened to land on a page boundary with only 60 books, so the second rule was not
exercised until the big-table experiment. Inflated to 5,000 rows, the same endpoint produced a
179-page document, and the check that matters came back clean:

```
pages with text: 179
pages carrying the repeated table header: 179/179
rows whose text is split across a page break: 0
```

**12 stage commits**, 23 assertions.

## Week 7: AI decision flow

A React Flow canvas where every node is a question the model answers yes or no, and the answer
picks which edge to follow. Inngest executes the graph with one step per node, so each decision
is retried and memoised on its own.

**What went wrong was the prompt, twice.** The first entry node asked "Is this message a support
request?" and sent a pricing enquiry to support. Sharpening it fixed that and broke a how-to
question instead, which contained the words "everything is working fine" and was read as
not-a-problem. I confirmed both times that the machinery was fine by asking the model each
version of the question directly, outside the app.

The node prompt is the specification. That is why the log panel shows the prompt next to the
answer for every step: when a run goes somewhere surprising, the question that sent it there is
on screen.

**4 phase commits**, 11 assertions.

## Three bugs the AI comparison found in my code

Worth separating from the rest, because this is the part I did not expect.

**A blocking endpoint, twice.** Testing whether the generated code held the event loop, I ran the
same test on mine and it was worse: a health check that normally answers in 0.4 milliseconds took
4.4 seconds while one classification was in flight. Both of us had written `async def` around a
blocking call. I had already solved this in the PDF assignment with a plain `def` so the
framework threads it, then made the same mistake three assignments later.

**A connection that was never closed.** Every function in the generated code ended with
`conn.close()`. Mine used `with connect() as connection:` throughout, which reads like it closes
and does not: sqlite3's context manager commits the transaction and leaves the connection open.
It was not leaking in practice, because refcounting tidied up, but the code looked like it was
doing something it was not.

**An id that could collide.** I had been truncating a UUID to eight hex characters because it is
nicer to paste into a curl command. That is 4.3 billion values, so two reports collide somewhere
around 77,000 of them, and a collision silently overwrites a stored report. The generated version
used a full UUID and could not. I kept the short id and added the check that makes it safe.

## Two bugs the clone test found

Every assignment was verified by cloning the pushed repo into a temporary directory, installing
from the committed requirements and running it there. Twice that caught something no amount of
local testing would have:

**A missing dependency.** `pydantic[email]` was installed by hand in my working environment and
never written into `requirements.txt`, so the auth API crashed on startup for anyone else.

**A missing template.** `create-next-app` writes `.env*` into `.gitignore`, which quietly swallowed
the `.env.example` that the decision flow README tells you to copy. A stranger following the
instructions would have failed on the first command.

Both are the same lesson. A thing that only works in the directory you built it in is not
finished.

## Running any of it

Each folder's README has the exact commands and was tested from a clean clone. The short version:
Python 3.11 with a virtualenv per folder, Node 20 or newer for the decision flow, and `ollama` for
anything that calls a model, so none of it needs an account or a card. The auth assignment needs
a free Supabase project and two settings, both documented in its README.

No `.env` file is committed anywhere in this repository or its history.
