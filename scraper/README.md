# The polite scraper (FlyRank A9)

Downloads the first three catalogue pages of Books to Scrape, visits the 60 book pages they
link to, and turns the HTML into checked JSON records. It caches every page it fetches, waits
between real requests, and finishes each run with a report of what happened.

## Run it

Python 3.11. From this `scraper/` folder:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python src/main.py
```

That one command does the whole pipeline and writes three files into `output/`. A cold run
takes about a minute, almost all of it the 0.5 second pause between requests.

Timed from a fresh clone of this repo on 31 August 2026: 63 seconds from `git clone` to
`output/books.json` holding 60 records, including creating the virtualenv and installing the
three dependencies.

The tests need no network and no server:

```bash
.venv/bin/python test_scraper.py
```

## Target classification

**Which site.** Books to Scrape, `https://books.toscrape.com/`.

**Why this one.** It is a sandbox. Its own front page at toscrape.com calls it "a fictional
bookstore that desperately wants to be scraped" and "a safe place for beginners learning web
scraping and for developers validating their scraping technologies as well". The site exists to
be practised on, so practising on it is what it is for. There are no real customers, no real
prices and no personal data anywhere in it.

**How much.** The first 3 catalogue pages only, `page-1.html` through `page-3.html`, and the 60
book detail pages those three pages link to. 63 pages in total, fetched once each and then read
from a local cache. Nothing else on the site is touched.

**What data.** Per book: title, product URL, price text, availability text, rating text,
description, plus the catalogue page it was found on and the time it was fetched. All of it is
already public on the page, and none of it is personal.

**Why that is appropriate here.** The scope is a fixed 63 pages on a site published for this
exact purpose, requested at human speed with a user-agent that says who I am, so the site can
see what I am doing and stop me if it wants to.

## The robots check

Requested `https://books.toscrape.com/robots.txt` once, on 31 August 2026:

```
$ curl -i https://books.toscrape.com/robots.txt
HTTP/2 404
date: Mon, 31 Aug 2026 13:52:01 GMT
content-type: text/html
content-length: 153
```

No robots file found. A missing file is not permission, it is just a missing file. The
permission here comes from the sandbox statement on the site itself, not from the 404, and the
scope stays at three catalogue pages either way.

I will not reuse this code on another site without checking its rules and terms first.

## The record

Defined once in [`src/schema.py`](src/schema.py) as a Pydantic model, and every record is
checked against it before it is allowed into `books.json`.

| Field | Type | Notes |
| --- | --- | --- |
| `title` | string | rejected if blank |
| `product_url` | string | must start with `https://`, and is the record's identity |
| `price_text` | string | as printed on the page, `£51.77` |
| `price_gbp` | number | the same price as a number, `51.77` |
| `availability_text` | string | `In stock (22 available)` |
| `rating_text` | one of `One` `Two` `Three` `Four` `Five` | a closed list, so a sixth value is an error rather than a surprise |
| `description` | string or null | null when the page has none, never invented |
| `source_page` | string | which catalogue page this book was found on |
| `fetched_at` | string | when the copy we parsed actually arrived, in UTC |

The raw text and the clean number live side by side, so `£51.77` and `51.77` are both on the
record and neither has to be recovered from the other.

A record that fails validation goes to `output/errors.json` with the reason, and never reaches
`books.json`:

```
rating_text: Input should be 'One', 'Two', 'Three', 'Four' or 'Five'
product_url: Value error, not an absolute https URL: '../relative/path'
no number in price text: 'sold out'
```

## How it stays polite

| Rule | What it does |
| --- | --- |
| User-agent | `FlyRankInternship-A9/1.0 (+link to this repo)` on every request, so the site can see who this is |
| Delay | 0.5 seconds after each real request. A cached page waits for nothing, because it never left this computer |
| Timeout | 10 seconds, then the request gives up instead of hanging the run |
| Cache | every page is saved under `cache/` and read from there afterwards. Restarting the script fifty times costs the site nothing |
| Retry | once, and only for a timeout or a 5xx. A 404 will still be missing in two seconds, and a 403 means the site said no |
| Scope | three catalogue pages, hard-limited in code by `MAX_CATALOGUE_PAGES` |

## Proof: one real run

A cold run with an empty cache, on 31 August 2026. This is `output/run-report.json` exactly as
the script wrote it:

```json
{
  "started_at": "2026-08-31T14:05:44Z",
  "duration_seconds": 58.76,
  "catalogue_pages": 3,
  "pages_fetched": 63,
  "cache_hits": 0,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "failures": []
}
```

63 pages fetched: 3 catalogue pages plus 60 book pages. Almost all of the 59 seconds is the
0.5 second pause after each one.

Run it again and the same 60 records come back, from cache, in 0.22 seconds (0.42 on a slower pass). Running twice
gives 60 records rather than 120, because the product URL is each record's identity and both
output files are written fresh rather than appended to.

## One bad page does not take the run down

`--inject-failure` adds one made-up book URL to the list, so the failure path can be proved
without going near the real site's limits:

```
$ .venv/bin/python src/main.py --inject-failure
INJECTED   https://books.toscrape.com/catalogue/a-book-that-does-not-exist_0/index.html
SKIPPED    https://books.toscrape.com/catalogue/a-book-that-does-not-exist_0/index.html: HTTP 404
detail_pages=60 failed_pages=1
```

The run finished, `books.json` still held its 60 records, and the report showed
`"failed_pages": 1`. There is no retry line in that output, which is the point: a 404 is not
retried, only timeouts and 5xx responses are.

## Why this needed no browser

The data is already in the HTML the server sends, so a browser would only add cost. The
toscrape.com front page says as much in its own table, Requires JavaScript: no. Checked
directly against the bytes:

```
$ curl -s https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html \
    | grep -o 'price_color">[^<]*'
price_color">£51.77
```

The price is in the response. Starting Chromium to read it would cost seconds and hundreds of
megabytes to learn something `grep` already knows.

## Ethics

Use an official API when the site has one, because a documented endpoint is cheaper for both
sides than parsing a page that was never meant to be parsed. Never work around a login, a
paywall or a block: those are the site saying no, and going around them is not a technical
question. Collect only the fields you actually need, and keep the receipt of where each one
came from. Say who you are in the user-agent so the site can find you, and go slowly enough
that nobody has to notice you.

## An honest limitation

The cache never expires. Once a page is in `cache/`, it is used forever, so a run in a month
would happily report August's prices with August's `fetched_at` stamps and no warning that the
data is stale. That is the right trade while developing, where the whole point is to stop
asking the site, and the wrong one for anything scheduled. The fix is an age check on the
cached file, which this assignment does not need and so does not have.

Two smaller things worth knowing. The descriptions are stored exactly as the site serves them,
which on this site means a truncated preview followed by the full text and a trailing `...more`,
because the brief's rule is to never invent or alter text that was on the page. And
`fetched_at` is read from the cache file's timestamp, so it says when that copy arrived rather
than when the current run happened.

## The tests

`test_scraper.py` is 22 plain asserts over the parsing and validation, with no network and no
test framework. It covers price normalisation, relative to absolute URLs, a book page with no
description, whitespace in every field, duplicate product URLs, and four kinds of record the
schema must refuse.

They earned their place: an early version of the cache filename helper turned any URL ending in
a slash into `book-catalogue.html`, which would have given every book the same cache file and
served the wrong page from it. The test comparing two different books' cache names is what
found it.
