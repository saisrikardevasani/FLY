# Prompt v2, the rematch

Everything in prompt-v1.md, plus the four things v1 got wrong. Written after running v1 and
calling its token extraction directly, before regenerating.

---

Same service as before, with these additions. All four are about the guard.

**Never log a token.** Your last version printed the whole access token to stdout every time
verification failed:

```
Token verification failed for token eyJhbGciOiJIUzI1NiJ9.SECRET-SESSION-TOKEN.signature: ...
```

A token is a credential. Anyone who reads that log line can use it until it expires, and logs
get shipped to places the token was never meant to reach. Log the failure and the reason, never
the token itself. If you want something to correlate on, log the last few characters or a hash,
not the value.

**Parse the scheme properly rather than stripping a prefix.** `authorization.replace("Bearer ",
"")` is not parsing. Called directly, yours does this:

```
'Bearer TOKEN123'         -> extracts 'TOKEN123'      correct
'TOKEN123'                -> extracts 'TOKEN123'      a header with no scheme sails through
'Bearer Bearer TOKEN123'  -> extracts 'TOKEN123'      replaces every occurrence
```

Split the header once on the first space, require the scheme to be exactly `bearer` compared
case-insensitively, because RFC 7235 says the scheme is case-insensitive and `bearer <token>` is
a valid header that your version rejects. Require a non-empty token after it. Anything else is
`401`.

**Do not wrap the verification in a bare `except Exception`.** Catching everything means an
`AttributeError` from your own code becomes a 401 that looks like a rejected token, and you will
debug that for an hour one day. Catch the Supabase auth error specifically, and check the
response for `None` before reaching into it rather than relying on the exception handler to
catch the resulting `AttributeError`.

**Make the missing-header and bad-scheme cases your own 401**, in the same `{"error": "..."}`
shape as everything else, rather than letting FastAPI's `HTTPBearer` auto-reject produce a
different body. Declare the scheme with `auto_error=False` so your code decides.

Everything else stays the same: the five routes, the status codes, the one reusable dependency,
the second protected route, and the Swagger padlock with an Authorize button.
