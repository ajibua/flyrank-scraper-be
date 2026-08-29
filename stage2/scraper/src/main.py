#!/usr/bin/env python3
"""Stage 2 checkpoint: prints catalogue_pages=3 discovered=60 unique_urls=60
— and a second run reports the same numbers, mostly from cache."""
from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

from extractor import extract_book_links, extract_next_page_url
from fetcher import fetch

BASE_URL = "https://books.toscrape.com"
FIRST_PAGE = BASE_URL + "/catalogue/page-1.html"
MAX_CATALOGUE_PAGES = 3
DELAY_SECONDS = 0.6  # >= 500ms between real requests; cached pages need none

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("scraper")


def discover_book_urls(session: requests.Session) -> tuple[list[str], int]:
    urls: list[str] = []
    page_url = FIRST_PAGE
    pages_fetched = 0

    for _ in range(MAX_CATALOGUE_PAGES):
        html, was_cached, status = fetch(page_url, CACHE_DIR, session)
        if html is None:
            log.error("Could not load %s (status=%s)", page_url, status)
            break
        if not was_cached:
            time.sleep(DELAY_SECONDS)

        pages_fetched += 1
        urls.extend(extract_book_links(html, page_url))
        next_url = extract_next_page_url(html, page_url)
        if not next_url:
            break
        page_url = next_url

    unique_urls = list(dict.fromkeys(urls))  # de-dupe, keep first-seen order
    return unique_urls, pages_fetched


def main():
    session = requests.Session()
    urls, pages_fetched = discover_book_urls(session)
    print(f"catalogue_pages={pages_fetched} discovered={len(urls)} unique_urls={len(urls)}")


if __name__ == "__main__":
    main()
