# The polite scraper — FlyRank Backend Internship, Week 5 (A9)

A small pipeline that downloads the first 3 catalogue pages of
[Books to Scrape](https://books.toscrape.com), visits all 60 book pages,
turns the messy HTML into clean, checked JSON, survives a broken page
without crashing, and ends every run with an honest report.

*(This README grows with each stage. Right now it only has Stage 0's
required section — install/run instructions, the schema, and the rest
land in the Stage 6 commit.)*

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
- **robots.txt result:** *(run `curl https://books.toscrape.com/robots.txt`
  once, by hand, and paste exactly what came back here — or write
  "no robots file found" if the request failed. Do this before Stage 1.)*

> **I will not reuse this code on another site without checking its rules
> and terms first.**
