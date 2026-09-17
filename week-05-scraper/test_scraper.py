"""Plain asserts over the parsing and validation logic. No network, no framework.

Run it with:  .venv/bin/python test_scraper.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from main import cache_name, extract, validate  # noqa: E402
from schema import to_gbp  # noqa: E402

WHEN = "2026-08-31T00:00:00Z"
URL = "https://books.toscrape.com/catalogue/a-book_1/index.html"
PAGE = "https://books.toscrape.com/catalogue/page-1.html"

BOOK_PAGE = """
<html><body>
  <div class="product_main">
    <h1>A Light in the Attic</h1>
    <p class="price_color">£51.77</p>
    <p class="instock availability">In stock (22 available)</p>
    <p class="star-rating Three"></p>
  </div>
  <div id="product_description"><h2>Product Description</h2></div>
  <p>A poetry collection.</p>
</body></html>
"""

# Same page, but the description block was never rendered and the fields are padded
# with the whitespace a real template leaves behind.
NO_DESCRIPTION_PAGE = """
<html><body>
  <div class="product_main">
    <h1>
        Tipping the Velvet
    </h1>
    <p class="price_color">   £53.74   </p>
    <p class="instock availability">
        In stock (20 available)
    </p>
    <p class="star-rating One"></p>
  </div>
</body></html>
"""


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"  ok  {name}")


print("price normalisation")
check("£51.77 becomes 51.77", to_gbp("£51.77") == 51.77)
check("a whole pound amount still becomes a float", to_gbp("£10") == 10.0)
check("padding does not matter", to_gbp("  £53.74  ") == 53.74)
try:
    to_gbp("sold out")
    raise AssertionError("FAILED: price text with no number should raise")
except ValueError:
    print("  ok  price text with no number raises rather than guessing 0")

print("extraction")
record = extract(BOOK_PAGE, URL, PAGE, WHEN)
check("all eight keys are present", len(record) == 8)
check("title is read from the product area", record["title"] == "A Light in the Attic")
check("price text keeps its currency symbol", record["price_text"] == "£51.77")
check("the star count comes from the class", record["rating_text"] == "Three")
check("the description is the paragraph after the heading",
      record["description"] == "A poetry collection.")
check("provenance is carried on the record",
      record["source_page"] == PAGE and record["fetched_at"] == WHEN)

print("a book with no description")
sparse = extract(NO_DESCRIPTION_PAGE, URL, PAGE, WHEN)
check("a missing description is null, not invented text", sparse["description"] is None)
check("all eight keys are still present", len(sparse) == 8)
check("surrounding whitespace is stripped", sparse["title"] == "Tipping the Velvet")
check("whitespace does not break the price", sparse["price_text"] == "£53.74")

print("urls")
check("a book url becomes a cache slug",
      cache_name("https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html")
      == "book-a-light-in-the-attic_1000.html")
check("a trailing slash gives the same slug as index.html",
      cache_name("https://books.toscrape.com/catalogue/thirst_946/")
      == cache_name("https://books.toscrape.com/catalogue/thirst_946/index.html"))
check("two different books never share a cache file",
      cache_name("https://books.toscrape.com/catalogue/thirst_946/")
      != cache_name("https://books.toscrape.com/catalogue/sharp-objects_997/"))

print("validation")
good, bad = validate([record, dict(record)])
check("the same product url twice is stored once", len(good) == 1 and not bad)

good, bad = validate([{**record, "rating_text": "Eleven"}])
check("a rating outside the closed list is rejected", not good and len(bad) == 1)
check("the rejection says which field and why", "rating_text" in bad[0]["reason"])

good, bad = validate([{**record, "product_url": "../relative/path"}])
check("a relative url never reaches books.json", not good and len(bad) == 1)

good, bad = validate([{**record, "price_text": "sold out"}])
check("a price with no number is set aside with its reason",
      not good and "no number in price text" in bad[0]["reason"])

print("\nall checks passed")
