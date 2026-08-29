#!/usr/bin/env python3
"""Stage 3 checkpoint: prints one complete raw record (all eight keys,
even when description is null) and detail_pages=60."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from extractor import extract_book_links, extract_next_page_url, extract_raw_record
from fetcher import fetch

BASE_URL = "https://books.toscrape.com"
FIRST_PAGE = BASE_URL + "/catalogue/page-1.html"
MAX_CATALOGUE_PAGES = 3
DELAY_SECONDS = 0.6

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("scraper")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def discover_book_urls(session: requests.Session) -> list[str]:
    urls: list[str] = []
    page_url = FIRST_PAGE
    for _ in range(MAX_CATALOGUE_PAGES):
        html, was_cached, status = fetch(page_url, CACHE_DIR, session)
        if html is None:
            break
        if not was_cached:
            time.sleep(DELAY_SECONDS)
        urls.extend(extract_book_links(html, page_url))
        next_url = extract_next_page_url(html, page_url)
        if not next_url:
            break
        page_url = next_url
    return list(dict.fromkeys(urls))


def main():
    session = requests.Session()
    urls = discover_book_urls(session)

    raw_records = []
    for url in urls:
        html, was_cached, status = fetch(url, CACHE_DIR, session)
        if html is None:
            log.warning("Skipping %s (status=%s)", url, status)
            continue
        if not was_cached:
            time.sleep(DELAY_SECONDS)
        raw_records.append(extract_raw_record(html, url, source_page=url, fetched_at=now_iso()))

    print(f"detail_pages={len(raw_records)}")
    if raw_records:
        print(json.dumps(raw_records[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
