# Prompt v2, the rematch

Everything in prompt-v1.md, plus the four things v1 failed to say. Written after running v1 and
watching what it did, before regenerating.

---

Same system as before, with these additions.

**A failed run has to mark the report failed.** In v1 I asked the cron to count how many reports
are pending, done and failed, but I never said how a report ever becomes failed. The result
counted a state that could not happen: after a run exhausted its retries the report still read
`"status": "pending"` forever, and the failed counter was permanently zero. Add an `on_failure`
handler to `make-report` that sets the report's status to `failed` once the retries are used up.
A status endpoint that reports pending for work that died an hour ago is lying to its caller.

**Every bad body is a 400, not only a missing one.** A topic of `42` must be rejected with 400,
the same as a missing or blank one. Convert FastAPI's validation error into a 400 rather than
letting the framework's 422 through, and make every error response the same shape,
`{"error": "..."}`, so a client has one thing to parse.

**Timestamps are UTC and timezone aware.** Use `datetime.now(timezone.utc)` and store ISO 8601.
A naive local timestamp is ambiguous the moment the code runs anywhere other than the laptop it
was written on.

**Do not edit stored reports in place, and do not build the same report twice.** Replace the
stored dictionary with a new one rather than mutating the pending one. Before building, check
whether the report is already done and return the existing one if it is. The same event can be
delivered more than once, and the second delivery must not produce a second report or a second
side effect.

Everything else stays the same: 202 with an id, the status endpoint with 404, the sleep step and
the build step, retries of 2, the "fail" topic that raises, and the every-minute cron.
