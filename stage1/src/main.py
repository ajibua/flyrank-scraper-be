#!/usr/bin/env python3
"""Stage 1 checkpoint: run this twice. First run prints FETCH and creates
cache/page-1.html. Second run prints CACHE HIT and reads the saved file."""
from __future__ import annotations

import logging
from pathlib import Path

import requests

from fetcher import fetch

BASE_URL = "https://books.toscrape.com"
FIRST_PAGE = BASE_URL + "/catalogue/page-1.html"
ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main():
    session = requests.Session()
    html, was_cached, status = fetch(FIRST_PAGE, CACHE_DIR, session)
    if html is None:
        print(f"Fetch failed, status={status}")
        return
    print(f"Got {len(html)} bytes (cache_hit={was_cached})")


if __name__ == "__main__":
    main()
