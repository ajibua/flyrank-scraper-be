# The polite scraper — FlyRank Backend Internship, Week 5 (A9)

A small pipeline that downloads the first 3 catalogue pages of
[Books to Scrape](https://books.toscrape.com), visits all 60 book pages,
turns the messy HTML into clean, checked JSON, survives a broken page
without crashing, and ends every run with an honest report.

## Target classification (Stage 0)

- **Site:** `books.toscrape.com`
- **Why this site is okay to scrape:** its own homepage says it exists
  specifically as a sandbox "built for web scraping practice" — that
  sentence is the permission this assignment relies on. It is the only
  site this project touches.
- **Scope:** the first 3 catalogue pages only (60 books, ~20/page),
  followed via the site's own "next" link — never hardcoded.
- **Data collected:** per book — title, price, availability, star rating,
  description (if present), and the book's own product page as the
  record's source.
- **robots.txt result:** every run of `python src/main.py` checks
  `https://books.toscrape.com/robots.txt` first and logs the result as its
  first line of output (see `check_robots()` in `src/fetcher.py`). Paste
  that line here after your first run, e.g.:
  ```
  robots.txt found at https://books.toscrape.com/robots.txt — fetching /catalogue/ is allowed for our user-agent.
  ```
  If nothing comes back, the code treats a missing file as "no permission
  found," not as a green light, and proceeds cautiously anyway.

> **I will not reuse this code on another site without checking its rules
> and terms first.**

## Install & run

```bash
cd scraper
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt

python src/main.py                      # normal run: books.json, errors.json, run-report.json
python src/main.py --inject-broken-url  # Stage 5 checkpoint (see below)

pytest tests/                           # 6 unit tests, no network needed
```

First run fetches and caches every page (`cache/`). Every rerun after that
reads the cache instead of asking the site again — you'll see `CACHE HIT`
instead of `FETCH` in the log, and the run finishes in a couple of seconds.
Delete `cache/` to force a fresh crawl.

## What "clean, checked" means — the record schema

Every raw record is normalized and validated (`src/schema.py`, Pydantic)
before it's allowed into `output/books.json`. A record that fails goes to
`output/errors.json` instead, with a reason — it never sneaks into the
clean file.

| Field               | Type            | Notes                                   |
|---------------------|-----------------|------------------------------------------|
| `title`             | string          | required                                 |
| `product_url`       | string (URL)    | canonical identity of the record         |
| `price_gbp`         | float, `> 0`    | normalized from `price_text`             |
| `price_text`        | string          | raw value, kept alongside the clean one  |
| `availability_text` | string          | e.g. `"In stock (22 available)"`         |
| `rating`             | int, `1–5`      | normalized from `rating_text`            |
| `rating_text`       | string          | raw word, e.g. `"Three"`                 |
| `description`       | string \| null  | `null` when the page has none — never invented |
| `source_page`       | string (URL)    | provenance: which catalogue page found it |
| `fetched_at`        | string (UTC ISO 8601) | provenance: when it was fetched   |

`product_url` is each record's canonical URL — running the pipeline twice
produces the same records, not duplicates (`dedupe_by_canonical_url` in
`src/main.py`).

## Politeness rules this scraper always follows

- **Identifies itself:** every request sends
  `User-Agent: FlyRankInternshipA9/1.0 (+link to this repo)` — never a
  spoofed browser string.
- **Times out:** 8 seconds per request. No request waits forever.
- **Checks the status code first:** only `200` is treated as "here is the
  page." `404`/`403` are treated as a permanent no and are never retried;
  `5xx`/timeouts get exactly one retry with a short backoff.
- **Goes slowly:** at least 500ms between real requests to the site.
  Cached pages need no delay — they never leave your machine.
- **Caches:** every page fetched once is saved under `cache/` and read
  from disk on every later run, so development can be repeated freely
  without repeatedly asking the site for the same page.

## Surviving a broken page (Stage 5)

`python src/main.py --inject-broken-url` adds one made-up book URL to the
list on purpose before the detail-page stage runs. That URL 404s, gets
logged, and lands in `errors.json` — the other 60 good records still make
it into `books.json`, and `run-report.json` shows `"failed_pages": 1`. No
part of this project tests failure by hammering the real site; the one
broken URL is fabricated locally.

## Run report

Every run ends by writing `output/run-report.json`:

```json
{
  "started_at": "2026-08-29T12:05:38Z",
  "catalogue_pages_fetched": 3,
  "cache_hits": 0,
  "detail_pages_fetched": 60,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "duration_seconds": 85.63
}
```
*(Paste your own real `run-report.json` here after a run, replacing the
template above — that's the proof the checkpoint asks for.)*

## Why this project needed no browser

The book data is already present in the plain HTML the server sends for
each catalogue and product page — `view-source:` shows the title, price,
and rating with no JavaScript required to render them. A headless browser
(e.g. Playwright) would only add startup cost and memory for no extra
data, which is why this pipeline uses plain HTTP requests + BeautifulSoup
throughout instead.

## Ethics note

- Prefer an official API over scraping whenever one exists; this project
  only scrapes because Books to Scrape is a sandbox with no API, built
  for exactly this purpose.
- Never bypass logins, paywalls, CAPTCHAs, or an explicit block — a block
  is the site saying no, and going around it isn't politeness, it's
  ignoring the answer.
- Collect only the fields actually needed for the task, and cache
  aggressively so the site is asked for each page as few times as possible.

## One honest limitation

Cache filenames are derived from each URL's last path segment
(e.g. `a-light-in-the-attic_1000.html`), not a hash — this is readable but
would collide if the site ever had two different books sharing the same
slug. Fine for a 60-book, single-site scraper; not something I'd keep
as-is for a general-purpose crawler.

## Project layout

```
scraper/
├── src/
│   ├── main.py       # orchestrates all 7 stages, CLI entry point
│   ├── fetcher.py     # robots.txt check, caching, retries, delay
│   ├── extractor.py   # BeautifulSoup: listing links + detail-page fields
│   ├── schema.py       # Pydantic CleanBook model + normalization
│   └── report.py       # RunReport dataclass
├── tests/
│   ├── test_extractor.py
│   └── fixtures/        # small local HTML files, tested with no network
├── cache/                # gitignored HTML cache (kept in place with .gitkeep)
├── output/
│   ├── books.json        # valid, clean records
│   ├── errors.json       # rejected records + why
│   └── run-report.json   # honest numbers from the last run
├── requirements.txt
└── README.md
```
