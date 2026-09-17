"""Turn the report object into a page, then ask a browser to print it."""

import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

REPORTS_DIR = Path(__file__).resolve().parent / "reports"

STYLE = """
  body { font-family: -apple-system, Helvetica, Arial, sans-serif; color: #1a1a1a;
         margin: 0; font-size: 11pt; }
  h1 { font-size: 22pt; margin: 0 0 4px; }
  h2 { font-size: 13pt; margin: 28px 0 8px; border-bottom: 2px solid #1a1a1a;
       padding-bottom: 4px; }
  .date { color: #666; margin: 0 0 24px; }
  .totals { display: flex; gap: 16px; margin-bottom: 8px; }
  .total { background: #f2f2f2; padding: 14px 18px; flex: 1; }
  .total .value { font-size: 20pt; font-weight: 600; }
  .total .label { color: #555; font-size: 9pt; text-transform: uppercase; }
  table { width: 100%; border-collapse: collapse; }
  th { background: #1a1a1a; color: #fff; text-align: left; padding: 7px 9px;
       font-size: 9pt; text-transform: uppercase; }
  td { padding: 7px 9px; border-bottom: 1px solid #ddd; vertical-align: top; }
  td.num, th.num { text-align: right; white-space: nowrap; }

  /* Print rules. Without these a long table breaks badly across pages: the header
     row appears once and never again, and a tall row can be sliced through the
     middle by the page edge. */
  thead { display: table-header-group; }
  tr { break-inside: avoid; }
"""


def html_for(data: dict) -> str:
    """Build the page. A report is a web page that happens to be printed."""
    today = datetime.date.today().strftime("%d %B %Y")

    top_rows = "".join(
        f"<tr><td>{b['title']}</td><td class='num'>{b['rating']}</td>"
        f"<td class='num'>£{b['price']:.2f}</td></tr>"
        for b in data["top_5_expensive"]
    )
    rating_rows = "".join(
        f"<tr><td class='num'>{r['rating']}</td><td class='num'>{r['books']}</td>"
        f"<td class='num'>£{r['average_price']:.2f}</td></tr>"
        for r in data["by_rating"]
    )
    all_rows = "".join(
        f"<tr><td>{b['title']}</td><td class='num'>{b['rating']}</td>"
        f"<td class='num'>£{b['price']:.2f}</td></tr>"
        for b in data["all_books"]
    )

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>{STYLE}</style></head><body>
  <h1>Bookstore stock report</h1>
  <p class="date">Generated {today} from {data['total_books']} scraped books</p>

  <div class="totals">
    <div class="total"><div class="label">Books in catalogue</div>
      <div class="value">{data['total_books']}</div></div>
    <div class="total"><div class="label">Average price</div>
      <div class="value">£{data['average_price']:.2f}</div></div>
  </div>

  <h2>Five most expensive</h2>
  <table><thead><tr><th>Title</th><th class="num">Rating</th>
    <th class="num">Price</th></tr></thead><tbody>{top_rows}</tbody></table>

  <h2>By star rating</h2>
  <table><thead><tr><th class="num">Rating</th><th class="num">Books</th>
    <th class="num">Average price</th></tr></thead><tbody>{rating_rows}</tbody></table>

  <h2>Every book</h2>
  <table><thead><tr><th>Title</th><th class="num">Rating</th>
    <th class="num">Price</th></tr></thead><tbody>{all_rows}</tbody></table>
</body></html>"""


def render_pdf(html: str, path: Path) -> Path:
    """You do not draw a PDF. You write a page and ask a browser to print it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        page.pdf(
            path=str(path),
            format="A4",
            print_background=True,
            margin={"top": "14mm", "bottom": "14mm", "left": "12mm", "right": "12mm"},
        )
        browser.close()
    return path


if __name__ == "__main__":
    import db

    out = render_pdf(html_for(db.get_report_data()), REPORTS_DIR / "test.pdf")
    print(f"wrote {out}")
