"""A9, the polite scraper. Books to Scrape, first three catalogue pages only."""

import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

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

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


class FetchFailed(Exception):
    """The page did not arrive. Not something to parse."""


def fetch(url: str, filename: str) -> str:
    """Return the HTML for url, from the cache when we already have a copy.

    The site should feel this script once, however many times it is restarted.
    """
    path = CACHE_DIR / filename
    if path.exists():
        html = path.read_text(encoding="utf-8")
        print(f"CACHE HIT  {url}  {path.stat().st_size} bytes")
        return html

    try:
        response = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS
        )
    except requests.RequestException as exc:
        raise FetchFailed(f"{url}: {exc}") from exc

    # Check the status before treating the body as HTML. A 404 page is not a book.
    if response.status_code != 200:
        raise FetchFailed(f"{url}: HTTP {response.status_code}")

    html = response.text
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    print(f"FETCH      {url}  {path.stat().st_size} bytes")

    # Only a real request earns a wait. A cached page never left this computer.
    time.sleep(DELAY_SECONDS)
    return html


def discover() -> list[str]:
    """Walk the catalogue's own next links and collect every book URL they offer."""
    found: list[str] = []
    page_url: str | None = START_URL
    pages = 0

    while page_url and pages < MAX_CATALOGUE_PAGES:
        pages += 1
        soup = BeautifulSoup(fetch(page_url, f"catalogue-page-{pages}.html"), "html.parser")

        for link in soup.select("article.product_pod h3 a"):
            # Relative hrefs like ../book/index.html need a base, never string glue.
            found.append(urljoin(page_url, link["href"]))

        # Let the site say where page 2 is rather than guessing the URL shape.
        next_link = soup.select_one("li.next a")
        page_url = urljoin(page_url, next_link["href"]) if next_link else None

    unique = list(dict.fromkeys(found))  # keeps first-seen order, drops repeats
    print(f"catalogue_pages={pages} discovered={len(found)} unique_urls={len(unique)}")
    return unique


if __name__ == "__main__":
    discover()
