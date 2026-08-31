"""A9, the polite scraper. Books to Scrape, first three catalogue pages only."""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import ValidationError

from schema import Book, normalise

BASE_URL = "https://books.toscrape.com/"
START_URL = "https://books.toscrape.com/catalogue/page-1.html"

# A site owner reading their logs can find out who this is and where to complain.
USER_AGENT = (
    "FlyRankInternship-A9/1.0 "
    "(+https://github.com/saisrikardevasani/flyrank-w2-crud-api)"
)

# How many catalogue pages we are allowed to touch. Stage 0 decided this, not the code.
MAX_CATALOGUE_PAGES = 3

# A request that never gives up is a request that hangs the whole run.
TIMEOUT_SECONDS = 10

# Sixty-three pages at human speed. The site is a sandbox, not a target.
DELAY_SECONDS = 0.5

# One retry, after a pause, and only for failures that a second try might fix.
RETRY_WAIT_SECONDS = 2

# A URL that does not exist, used to prove the run survives a broken page.
FAKE_URL = "https://books.toscrape.com/catalogue/a-book-that-does-not-exist_0/index.html"

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# Counters for the run report. A scraper that reports nothing fails silently for weeks.
STATS = {"pages_fetched": 0, "cache_hits": 0}


class FetchFailed(Exception):
    """The page did not arrive. Not something to parse."""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(url: str, filename: str) -> str:
    """Return the HTML for url, from the cache when we already have a copy.

    The site should feel this script once, however many times it is restarted.
    """
    path = CACHE_DIR / filename
    if path.exists():
        html = path.read_text(encoding="utf-8")
        STATS["cache_hits"] += 1
        print(f"CACHE HIT  {url}  {path.stat().st_size} bytes")
        return html

    response = request_with_one_retry(url)

    # The server sends "text/html" with no charset, so requests would fall back to
    # ISO-8859-1 and turn every price into "Â£51.77". The page itself declares UTF-8.
    if "charset" not in response.headers.get("content-type", "").lower():
        response.encoding = response.apparent_encoding

    html = response.text
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    STATS["pages_fetched"] += 1
    print(f"FETCH      {url}  {path.stat().st_size} bytes")

    # Only a real request earns a wait. A cached page never left this computer.
    time.sleep(DELAY_SECONDS)
    return html


def request_with_one_retry(url: str) -> requests.Response:
    """Ask twice at most, and only when a second ask could plausibly work.

    A 404 will still be missing in two seconds. A 403 means the site said no, and
    asking again is how a polite robot turns into a pest. A timeout or a 5xx is the
    server having a moment, which is worth one more try.
    """
    for attempt in (1, 2):
        try:
            response = requests.get(
                url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS
            )
        except requests.Timeout as exc:
            if attempt == 2:
                raise FetchFailed(f"{url}: timed out twice") from exc
            print(f"RETRY      {url}  timed out")
            time.sleep(RETRY_WAIT_SECONDS)
            continue
        except requests.RequestException as exc:
            raise FetchFailed(f"{url}: {exc}") from exc

        # Check the status before treating the body as HTML. A 404 page is not a book.
        if response.status_code == 200:
            return response
        if response.status_code >= 500 and attempt == 1:
            print(f"RETRY      {url}  HTTP {response.status_code}")
            time.sleep(RETRY_WAIT_SECONDS)
            continue
        raise FetchFailed(f"{url}: HTTP {response.status_code}")

    raise FetchFailed(f"{url}: gave up after two attempts")


def fetched_at(filename: str) -> str:
    """When this copy actually arrived, not when we happened to read it again."""
    when = datetime.fromtimestamp((CACHE_DIR / filename).stat().st_mtime, timezone.utc)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def cache_name(url: str) -> str:
    """books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html -> a slug."""
    return f"book-{url.rstrip('/').split('/')[-2]}.html"


def discover() -> list[tuple[str, str]]:
    """Walk the catalogue's own next links. Returns (book URL, catalogue page)."""
    found: list[tuple[str, str]] = []
    page_url: str | None = START_URL
    pages = 0

    while page_url and pages < MAX_CATALOGUE_PAGES:
        pages += 1
        soup = BeautifulSoup(fetch(page_url, f"catalogue-page-{pages}.html"), "html.parser")

        for link in soup.select("article.product_pod h3 a"):
            # Relative hrefs like ../book/index.html need a base, never string glue.
            found.append((urljoin(page_url, link["href"]), page_url))

        # Let the site say where page 2 is rather than guessing the URL shape.
        next_link = soup.select_one("li.next a")
        page_url = urljoin(page_url, next_link["href"]) if next_link else None

    unique = list(dict.fromkeys(found))
    print(f"catalogue_pages={pages} discovered={len(found)} unique_urls={len(unique)}")
    return unique


def extract(html: str, url: str, source_page: str, when: str) -> dict:
    """Turn one book page into a raw record. Every key is present, even when empty."""
    soup = BeautifulSoup(html, "html.parser")

    # Aim at the product area. "The first thing that looks like a price" betrays you
    # the day the page grows a second one.
    product = soup.select_one("div.product_main")
    if product is None:
        raise FetchFailed(f"{url}: no product area on the page")

    rating = product.select_one("p.star-rating")
    # The star count lives in the class, as in <p class="star-rating Three">.
    rating_text = rating["class"][-1] if rating else None

    # The description is the paragraph that follows the product description heading.
    # Some books have none, and an absent description is null, never invented text.
    description = soup.select_one("#product_description ~ p")

    return {
        "title": product.h1.get_text(strip=True),
        "product_url": url,
        "price_text": product.select_one("p.price_color").get_text(strip=True),
        "availability_text": product.select_one("p.availability").get_text(strip=True),
        "rating_text": rating_text,
        "description": description.get_text(strip=True) if description else None,
        "source_page": source_page,
        "fetched_at": when,
    }


def scrape(targets: list[tuple[str, str]]) -> tuple[list[dict], list[dict]]:
    """Fetch every book page. One page that breaks is logged, skipped, and survived."""
    records: list[dict] = []
    failures: list[dict] = []

    for url, source_page in targets:
        filename = cache_name(url)
        try:
            html = fetch(url, filename)
            records.append(extract(html, url, source_page, fetched_at(filename)))
        except FetchFailed as exc:
            print(f"SKIPPED    {exc}")
            failures.append({"url": url, "reason": str(exc)})

    print(f"detail_pages={len(records)} failed_pages={len(failures)}")
    return records, failures


def validate(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split the raw records into the ones safe to store and the ones that are not.

    The product URL is each record's identity, so a book seen twice is stored once.
    """
    good: dict[str, dict] = {}
    bad: list[dict] = []

    for raw in records:
        try:
            book = Book.model_validate(normalise(raw))
        except ValidationError as exc:
            # Pydantic's default text is a paragraph per problem. errors.json is meant
            # to be read, so keep one short line per bad field.
            reason = "; ".join(
                f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}"
                for err in exc.errors()
            )
            bad.append({"product_url": raw.get("product_url"), "reason": reason})
            continue
        except ValueError as exc:
            bad.append({"product_url": raw.get("product_url"), "reason": str(exc)})
            continue
        good[book.product_url] = book.model_dump()

    return list(good.values()), bad


def write(name: str, payload) -> None:
    """Write the file fresh, so a second run replaces the result instead of adding."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / name
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {path.name}")


def run(inject_failure: bool = False) -> dict:
    """One full pass: discover, fetch, validate, store, and say what happened."""
    started = time.monotonic()
    started_at = now()

    targets = discover()
    if inject_failure:
        # A deliberate broken page, on our side only. Never test failure by hammering
        # the real site.
        targets.append((FAKE_URL, START_URL))
        print(f"INJECTED   {FAKE_URL}")

    records, failures = scrape(targets)
    good, bad = validate(records)

    report = {
        "started_at": started_at,
        "duration_seconds": round(time.monotonic() - started, 2),
        "catalogue_pages": MAX_CATALOGUE_PAGES,
        "pages_fetched": STATS["pages_fetched"],
        "cache_hits": STATS["cache_hits"],
        "valid_records": len(good),
        "invalid_records": len(bad),
        "failed_pages": len(failures),
        "failures": failures,
    }

    write("books.json", good)
    write("errors.json", bad)
    write("run-report.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "failures"}, indent=2))
    return report


if __name__ == "__main__":
    run(inject_failure="--inject-failure" in sys.argv)
