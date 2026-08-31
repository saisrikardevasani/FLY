"""A9, the polite scraper. Books to Scrape, first three catalogue pages only."""

BASE_URL = "https://books.toscrape.com/"
START_URL = "https://books.toscrape.com/catalogue/page-1.html"

# A site owner reading their logs can find out who this is and where to complain.
USER_AGENT = (
    "FlyRankInternship-A9/1.0 "
    "(+https://github.com/saisrikardevasani/flyrank-w2-crud-api)"
)

# How many catalogue pages we are allowed to touch. Stage 0 decided this, not the code.
MAX_CATALOGUE_PAGES = 3
