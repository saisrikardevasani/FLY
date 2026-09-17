# Prompt v2, the rematch

Everything in prompt-v1.md, plus the four things v1 got wrong. Written after running v1 against
a provider that always fails, before regenerating.

---

Same service as before, with these additions. All four are about what happens when the provider
misbehaves, which is the half my last prompt left to chance.

**Turn the SDK's own retries off.** The OpenAI client retries twice by default, underneath
whatever retry loop you write. Your last version wrapped a three-attempt loop around a client
that was already retrying, so one classification sent **five** HTTP requests to the provider for
one logical call. Pass `max_retries=0` when constructing the client, so that the only retries are
the ones in your code and a log line saying "one attempt" means one request left the machine.

**Set the timeout on the client, not only on the call.** Construct the client with
`timeout=30.0`. Reading it from an environment variable is better still, because otherwise the
timeout path cannot be tested without waiting half a minute for it.

**A provider failure must not escape as a 500.** Your last version let `APIConnectionError` and
`InternalServerError` propagate out of the route, so a failing provider produced
`Internal Server Error` as plain text with a stack trace in the log, after 39 seconds. Catch
every provider error, and turn it into a clean JSON response in the same `{"error": "..."}` shape
as everything else: `504` when the call timed out, `503` for anything else the caller can do
nothing about. Never crash, and never let the caller receive an unshaped error.

**The endpoint must not block the event loop.** The model call is synchronous and takes seconds.
Declared as `async def`, it holds the event loop for that whole time, so every other request
queues behind it: measured, a `/health` call that normally answers in 0.4 milliseconds took over
three seconds while one classification was in flight. Declare the route as a plain `def` so
FastAPI runs it in a worker thread, or make the whole path genuinely async. Either is fine, but
"async def wrapped around blocking code" is the one option that is always wrong.

Everything else stays the same: the closed genre list, the 400 on bad input before any model
call, the prompt in a file, stub mode, parse and validate and one repair then 422 with a
quarantine line, the retry rules, the per-call cost log and the kill switch.
