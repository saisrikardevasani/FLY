# Prompt v2, the rematch

Everything in prompt-v1.md, plus the four things v1 failed to say. Written after running v1
and seeing what it did, before regenerating.

---

Same assignment as before, with these additions.

**Decoding.** books.toscrape.com sends `Content-Type: text/html` with no charset, so requests
will guess ISO-8859-1 and every price will come out as `Â£51.77` instead of `£51.77`. The page
itself declares UTF-8 in a meta tag. Set the response encoding from the page rather than
trusting the header, and do it before caching the text, so the cache does not preserve the
mistake.

**Parsing the price.** Do not strip a specific currency symbol. Pull the number out of the
price text with a regular expression, and raise a clear error when the text contains no number
at all rather than guessing zero.

**The rating is a closed list.** rating_text is exactly one of One, Two, Three, Four or Five.
Anything else means the page changed and must be rejected as an invalid record, not stored.

**fetched_at is provenance, not a clock reading.** It must say when the copy being parsed
actually arrived from the site. On a run that reads from cache, a record's fetched_at should
still be the time that cached page was downloaded, not the time of the current run. Format it
as UTC ending in Z.

Everything else stays the same: three catalogue pages, 60 books, eight raw fields plus
price_gbp, Pydantic validation, errors.json with reasons, no duplicates, one retry on timeouts
and 5xx only, a run report every run, and a way to inject one broken URL.
