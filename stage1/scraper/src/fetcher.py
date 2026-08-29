"""
Stage 1: fetch once, cache once.

Politeness basics for a single request: an honest user-agent, a timeout,
a status-code check before trusting anything, and cache-first reads so
development never re-asks the site for a page it already has.

Retry rules and the delay-between-many-requests politeness come later,
in Stage 5, once there's more than one request in flight to worry about.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import requests

USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/ajibua/backend-internship)"
TIMEOUT = 8

log = logging.getLogger("scraper.fetch")


def _cache_filename(url: str) -> str:
    """.../catalogue/page-1.html -> page-1.html"""
    parts = [p for p in url.rstrip("/").split("/") if p]
    name = parts[-1]
    if not name.endswith(".html"):
        name += ".html"
    return name


def fetch(url: str, cache_dir: Path, session: requests.Session) -> tuple[Optional[str], bool, Optional[int]]:
    """Return (html, was_cache_hit, status_code). html is None on failure."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / _cache_filename(url)

    if path.exists():
        size = path.stat().st_size
        log.info("CACHE HIT  %-70s  %d bytes", url, size)
        return path.read_text(encoding="utf-8"), True, 200

    resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    if resp.status_code != 200:
        log.error("FETCH FAIL %-70s  status=%d", url, resp.status_code)
        return None, False, resp.status_code

    path.write_text(resp.text, encoding="utf-8")
    log.info("FETCH      %-70s  %d bytes  status=200", url, len(resp.text))
    return resp.text, False, 200
