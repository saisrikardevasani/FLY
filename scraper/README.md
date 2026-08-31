# The polite scraper (FlyRank A9)

Downloads the first three catalogue pages of Books to Scrape, visits the 60 book pages they
link to, and turns the HTML into checked JSON records. It caches every page it fetches, waits
between real requests, and finishes each run with a report of what happened.

Built stage by stage. This file grows as the stages land.

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
