"""Books to Scrape scraper, v2. Generated from prompt-v2.md. Not edited afterwards."""

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, ValidationError

BASE = "https://books.toscrape.com/"
START = "https://books.toscrape.com/catalogue/page-1.html"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/saisrikardevasani/flyrank-w2-crud-api)"
TIMEOUT = 10
DELAY = 0.5
MAX_PAGES = 3

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache-v2"
OUTPUT = HERE / "output-v2"

FAKE_URL = "https://books.toscrape.com/catalogue/this-book-is-not-real_0/index.html"

Rating = Literal["One", "Two", "Three", "Four", "Five"]

stats = {"fetched": 0, "cache_hits": 0}


class Book(BaseModel):
    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: Rating
    description: str | None = None
    source_page: str
    fetched_at: str


class PageError(Exception):
    pass


def cache_path(url: str) -> Path:
    name = urlparse(url).path.strip("/").replace("/", "_") or "index"
    return CACHE / f"{name}.html"


def utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url: str) -> tuple[str, str]:
    """Returns (html, fetched_at). fetched_at is when this copy arrived, not now."""
    path = cache_path(url)
    if path.exists():
        stats["cache_hits"] += 1
        text = path.read_text(encoding="utf-8")
        print(f"CACHE {url} ({len(text)} bytes)")
        return text, utc(path.stat().st_mtime)

    for attempt in range(2):
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        except requests.Timeout:
            if attempt == 0:
                time.sleep(1)
                continue
            raise PageError(f"timeout: {url}")
        except requests.RequestException as e:
            raise PageError(f"request failed: {url}: {e}")

        if resp.status_code == 200:
            break
        if 500 <= resp.status_code < 600 and attempt == 0:
            time.sleep(1)
            continue
        raise PageError(f"HTTP {resp.status_code}: {url}")
    else:
        raise PageError(f"failed after retries: {url}")

    # The header carries no charset, so requests would guess ISO-8859-1 and every price
    # would become "Â£51.77". Take the encoding the page itself declares, before caching.
    if "charset" not in resp.headers.get("Content-Type", "").lower():
        resp.encoding = resp.apparent_encoding

    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(resp.text, encoding="utf-8")
    stats["fetched"] += 1
    print(f"FETCH {url} ({len(resp.text)} bytes)")
    time.sleep(DELAY)
    return resp.text, utc(path.stat().st_mtime)


def find_books() -> list[tuple[str, str]]:
    out = []
    url = START
    pages = 0
    while url and pages < MAX_PAGES:
        pages += 1
        html, _ = get(url)
        soup = BeautifulSoup(html, "html.parser")
        for h3 in soup.select("h3"):
            a = h3.find("a")
            if isinstance(a, Tag) and a.get("href"):
                out.append((urljoin(url, str(a["href"])), url))
        nxt = soup.select_one("li.next a")
        url = urljoin(url, str(nxt["href"])) if nxt else None
    print(f"catalogue pages: {pages}, books found: {len(out)}")
    return out


def parse_book(html: str, url: str, source_page: str, fetched_at: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("div.product_main")
    if main is None:
        raise PageError(f"no product_main: {url}")

    h1 = main.find("h1")
    price = main.select_one("p.price_color")
    avail = main.select_one("p.availability")
    stars = main.select_one("p.star-rating")
    desc_tag = soup.select_one("#product_description ~ p")

    rating = ""
    if isinstance(stars, Tag):
        classes = [c for c in stars.get("class", []) if c != "star-rating"]
        rating = classes[0] if classes else ""

    return {
        "title": h1.get_text(strip=True) if h1 else "",
        "product_url": url,
        "price_text": price.get_text(strip=True) if price else "",
        "availability_text": avail.get_text(strip=True) if avail else "",
        "rating_text": rating,
        "description": desc_tag.get_text(strip=True) if desc_tag else None,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


def to_price(price_text: str) -> float:
    """Pull the number out, whatever currency symbol is in front of it."""
    match = re.search(r"\d+(?:\.\d+)?", price_text)
    if not match:
        raise ValueError(f"no number in price text: {price_text!r}")
    return float(match.group())


def main() -> None:
    start = time.time()
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    targets = find_books()
    if "--fail" in sys.argv:
        targets.append((FAKE_URL, START))

    seen = set()
    valid: list[dict] = []
    invalid: list[dict] = []
    failed: list[dict] = []

    for url, source_page in targets:
        if url in seen:
            continue
        seen.add(url)
        try:
            html, fetched_at = get(url)
            raw = parse_book(html, url, source_page, fetched_at)
        except PageError as e:
            print(f"SKIP {e}")
            failed.append({"url": url, "error": str(e)})
            continue

        try:
            raw["price_gbp"] = to_price(raw["price_text"])
            book = Book(**raw)
        except (ValidationError, ValueError) as e:
            invalid.append({"url": url, "error": str(e)})
            continue
        valid.append(book.model_dump())

    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "books.json").write_text(json.dumps(valid, indent=2, ensure_ascii=False))
    (OUTPUT / "errors.json").write_text(json.dumps(invalid, indent=2, ensure_ascii=False))

    report = {
        "started_at": started_at,
        "duration_seconds": round(time.time() - start, 2),
        "pages_fetched": stats["fetched"],
        "cache_hits": stats["cache_hits"],
        "valid_records": len(valid),
        "invalid_records": len(invalid),
        "failed_pages": len(failed),
    }
    (OUTPUT / "run-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
