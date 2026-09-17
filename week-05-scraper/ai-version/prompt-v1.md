# Prompt v1

Written from memory before generating anything, without re-reading the assignment brief.
The generated code goes in this folder and is never edited afterwards.

---

Write me a Python web scraper as a single script. Use requests, Beautiful Soup and Pydantic.

The target is https://books.toscrape.com/, a practice sandbox. Start at
https://books.toscrape.com/catalogue/page-1.html and follow the site's own "next" link to
page 2 and page 3, then stop. Do not hardcode the page URLs beyond the first one, and do not
hardcode the book links. Those three catalogue pages link to 60 books between them. Visit each
of those 60 book pages.

Be polite about it:

- Send a user-agent that identifies me: `FlyRankInternship-A9/1.0` with a link to my repo.
- Put a timeout on every request.
- Wait half a second between requests to the site.
- Save every page you download into a `cache/` folder and read from there on later runs, so
  that restarting the script does not hit the site again. Print whether each page was a fetch
  or a cache hit, along with its size. Do not print the HTML itself.

From each book page collect these eight fields exactly:

- title
- product_url (absolute, https)
- price_text (as shown, for example "£51.77")
- availability_text (for example "In stock (22 available)")
- rating_text (the star rating as a word: One, Two, Three, Four or Five)
- description (some books have none: use null, never make one up)
- source_page (which catalogue page the book was found on)
- fetched_at (UTC timestamp)

Relative links must be turned into absolute URLs properly with urljoin, not by joining strings.

Then clean and check the records:

- Turn price_text into a number called price_gbp, keeping price_text as well.
- Define the record as a Pydantic model. Everything is required except description.
- Validate every record before storing it. A record that fails goes into `output/errors.json`
  with the reason it failed, and must never end up in books.json.
- The product_url is the record's identity. If the same book turns up twice it is stored once.
- Write the good records to `output/books.json`. Running the script twice must give 60 records,
  not 120.

One broken page must not kill the run. Handle each page on its own, log it and skip it if it
fails. Retry once on a timeout or a 5xx, but never retry a 404 or a 403. At the end of every
run write `output/run-report.json` with the start time, how long the run took, how many pages
were fetched, how many were cache hits, how many records were valid, how many were invalid,
and how many pages failed.

Give me a way to prove the failure handling works by adding one made-up book URL to the list.
