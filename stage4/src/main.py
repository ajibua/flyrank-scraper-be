#!/usr/bin/env python3
"""Stage 4 checkpoint: output/books.json has exactly 60 records, every
price_gbp is a number, every URL starts with https:// — and after a
second run it is still exactly 60 (idempotent, keyed on product_url)."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from pydantic import ValidationError

from extractor import extract_book_links, extract_next_page_url, extract_raw_record
from fetcher import fetch
from schema import normalize

BASE_URL = "https://books.toscrape.com"
FIRST_PAGE = BASE_URL + "/catalogue/page-1.html"
MAX_CATALOGUE_PAGES = 3
DELAY_SECONDS = 0.6

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "output"

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


def dedupe_by_canonical_url(records: list[dict]) -> list[dict]:
    """product_url is each record's canonical identity — a URL seen twice
    counts once. Keeps repeated runs idempotent."""
    seen: dict[str, dict] = {}
    for r in records:
        seen[r["product_url"]] = r
    return list(seen.values())


def main():
    session = requests.Session()
    urls = discover_book_urls(session)

    valid, invalid = [], []
    for url in urls:
        html, was_cached, status = fetch(url, CACHE_DIR, session)
        if html is None:
            invalid.append({"product_url": url, "reason": f"fetch failed (status={status})"})
            continue
        if not was_cached:
            time.sleep(DELAY_SECONDS)

        raw = extract_raw_record(html, url, source_page=url, fetched_at=now_iso())
        try:
            clean = normalize(raw)
            valid.append(clean.model_dump())
        except (ValidationError, ValueError) as exc:
            invalid.append({"product_url": url, "reason": str(exc).split("\n")[0], "raw": raw})

    valid = dedupe_by_canonical_url(valid)

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "books.json").write_text(json.dumps(valid, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUTPUT_DIR / "errors.json").write_text(json.dumps(invalid, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"valid={len(valid)} invalid={len(invalid)}")


if __name__ == "__main__":
    main()
