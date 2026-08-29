#!/usr/bin/env python3
"""
FlyRank Backend Internship — Week 5, A9: The polite scraper
=============================================================
Downloads the first 3 catalogue pages of https://books.toscrape.com (a
public sandbox built for scraping practice), visits all 60 book pages,
turns messy HTML into clean, checked JSON, survives a broken page without
crashing, and ends every run with an honest report.

Run:
    python src/main.py                     # normal run
    python src/main.py --inject-broken-url  # Stage 5 checkpoint: proves one
                                             # bad URL can't take the run down

Every real HTTP request is logged as one line — FETCH, CACHE HIT, or
FETCH FAIL — never the whole page. See fetcher.py for the politeness rules
(user-agent, timeout, delay, cache, retry policy) and schema.py for what
"clean, checked" means.
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import requests
from pydantic import ValidationError

from extractor import extract_book_links, extract_next_page_url, extract_raw_record
from fetcher import check_robots, fetch
from report import RunReport, now_iso
from schema import normalize

BASE_URL = "https://books.toscrape.com"
FIRST_PAGE = BASE_URL + "/catalogue/page-1.html"
MAX_CATALOGUE_PAGES = 3

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "output"

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("scraper")


def discover_book_urls(session: requests.Session) -> tuple[list[str], int, int, int]:
    """Follow the catalogue's own 'next' link for up to 3 pages.
    Returns (unique_urls, pages_fetched, cache_hits, failed_pages).
    """
    urls: list[str] = []
    page_url = FIRST_PAGE
    pages_fetched = 0
    cache_hits = 0
    failed_pages = 0

    for _ in range(MAX_CATALOGUE_PAGES):
        html, was_cached, status = fetch(page_url, CACHE_DIR, session)
        if html is None:
            log.error("Could not load catalogue page %s (status=%s) — stopping discovery here", page_url, status)
            failed_pages += 1
            break

        pages_fetched += 1
        if was_cached:
            cache_hits += 1

        urls.extend(extract_book_links(html, page_url))
        next_url = extract_next_page_url(html, page_url)
        if not next_url:
            break
        page_url = next_url

    unique_urls = list(dict.fromkeys(urls))  # de-dupe, keep first-seen order
    return unique_urls, pages_fetched, cache_hits, failed_pages


def collect_records(urls: list[str], session: requests.Session, report: RunReport) -> tuple[list[dict], list[dict]]:
    """Visit every book page, extract, normalize, validate. One bad page
    lands in `invalid` with a reason — it never stops the loop.
    """
    valid: list[dict] = []
    invalid: list[dict] = []

    for url in urls:
        html, was_cached, status = fetch(url, CACHE_DIR, session)
        if html is None:
            report.failed_pages += 1
            invalid.append({"product_url": url, "reason": f"fetch failed (status={status})"})
            continue

        report.detail_pages_fetched += 1
        if was_cached:
            report.cache_hits += 1

        raw = extract_raw_record(html, url, source_page=url, fetched_at=now_iso())
        try:
            clean = normalize(raw)
            valid.append(clean.model_dump())
            report.valid_records += 1
        except (ValidationError, ValueError) as exc:
            report.invalid_records += 1
            invalid.append({
                "product_url": url,
                "reason": str(exc).split("\n")[0],
                "raw": raw,
            })

    return valid, invalid


def dedupe_by_canonical_url(records: list[dict]) -> list[dict]:
    """product_url is each record's canonical identity — a URL seen twice
    counts once. Keeps this run idempotent."""
    seen = {}
    for r in records:
        seen[r["product_url"]] = r  # last write wins, same shape either way
    return list(seen.values())


def main():
    parser = argparse.ArgumentParser(description="Polite scraper for books.toscrape.com")
    parser.add_argument(
        "--inject-broken-url", action="store_true",
        help="add one made-up book URL on purpose, to prove a broken page can't crash the run",
    )
    args = parser.parse_args()

    started = time.monotonic()
    report = RunReport(started_at=now_iso())

    log.info(check_robots(BASE_URL))

    session = requests.Session()

    urls, pages_fetched, cache_hits, discovery_failed = discover_book_urls(session)
    report.catalogue_pages_fetched = pages_fetched
    report.cache_hits += cache_hits
    report.failed_pages += discovery_failed
    log.info("catalogue_pages=%d discovered=%d unique_urls=%d", pages_fetched, len(urls), len(urls))

    if args.inject_broken_url:
        urls.append(BASE_URL + "/catalogue/this-book-does-not-exist_00000/index.html")
        log.info("Injected one made-up URL on purpose — proving a broken page can't take the run down")

    valid_records, invalid_records = collect_records(urls, session, report)
    valid_records = dedupe_by_canonical_url(valid_records)

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "books.json").write_text(
        json.dumps(valid_records, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUTPUT_DIR / "errors.json").write_text(
        json.dumps(invalid_records, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    report.duration_seconds = round(time.monotonic() - started, 2)
    report.write(OUTPUT_DIR / "run-report.json")

    log.info("detail_pages=%d", report.detail_pages_fetched)
    if valid_records:
        log.info("Sample record:\n%s", json.dumps(valid_records[0], indent=2, ensure_ascii=False))
    log.info(
        "DONE  valid=%d invalid=%d failed_pages=%d duration=%.2fs",
        report.valid_records, report.invalid_records, report.failed_pages, report.duration_seconds,
    )


if __name__ == "__main__":
    main()
