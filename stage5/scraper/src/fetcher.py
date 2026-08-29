"""
Politeness lives here, in one place, so every request — catalogue page or
book page — goes through the same rules:

  - an honest User-Agent that names this bot and links back to its repo
  - a timeout, so a slow server can't hang the run forever
  - cache-first: if we already saved this URL, read the file, don't ask again
  - on a real request: check the status code before trusting anything,
    wait at least 500ms, and retry only 5xx / timeouts (never 404 or 403 —
    those are a "no", not a glitch)
"""
from __future__ import annotations

import logging
import time
import urllib.robotparser as robotparser
from pathlib import Path
from typing import Optional

import requests

USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/ajibua/backend-internship)"
TIMEOUT = 8
DELAY_SECONDS = 0.6  # spec asks for >= 500ms between real requests
MAX_ATTEMPTS = 2      # one retry, and only for timeouts / 5xx

log = logging.getLogger("scraper.fetch")


def check_robots(base_url: str) -> str:
    """Fetch robots.txt once and return a short, human-readable summary.
    A missing file is reported as missing — it is not treated as permission.
    """
    rp = robotparser.RobotFileParser()
    rp.set_url(base_url.rstrip("/") + "/robots.txt")
    try:
        rp.read()
        allowed = rp.can_fetch(USER_AGENT, base_url + "/catalogue/page-1.html")
        return (
            f"robots.txt found at {base_url}/robots.txt — "
            f"fetching /catalogue/ is {'allowed' if allowed else 'DISALLOWED'} for our user-agent."
        )
    except Exception:
        return "no robots file found (the request itself failed) — proceeding cautiously anyway."


def _cache_filename(url: str) -> str:
    """A readable, unique-enough filename for a cached page.
    .../catalogue/page-2.html          -> page-2.html
    .../a-light-in-the-attic_1000/...  -> a-light-in-the-attic_1000.html
    """
    parts = [p for p in url.rstrip("/").split("/") if p]
    if parts[-1] == "index.html" and len(parts) >= 2:
        name = parts[-2]
    else:
        name = parts[-1]
    if not name.endswith(".html"):
        name += ".html"
    return name


def fetch(url: str, cache_dir: Path, session: requests.Session) -> tuple[Optional[str], bool, Optional[int]]:
    """Return (html, was_cache_hit, status_code). html is None on a real failure."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / _cache_filename(url)

    if path.exists():
        size = path.stat().st_size
        log.info("CACHE HIT  %-70s  %d bytes", url, size)
        return path.read_text(encoding="utf-8"), True, 200

    last_status = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        except requests.RequestException as exc:
            log.warning("FETCH FAIL %-70s  attempt %d/%d  (%s)", url, attempt, MAX_ATTEMPTS, exc)
            if attempt < MAX_ATTEMPTS:
                time.sleep(1.5 * attempt)
            continue

        last_status = resp.status_code

        if resp.status_code == 200:
            path.write_text(resp.text, encoding="utf-8")
            log.info("FETCH      %-70s  %d bytes  status=200", url, len(resp.text))
            time.sleep(DELAY_SECONDS)
            return resp.text, False, 200

        if resp.status_code in (404, 403):
            log.error("FETCH FAIL %-70s  status=%d — a permanent no, not retrying", url, resp.status_code)
            time.sleep(DELAY_SECONDS)
            return None, False, resp.status_code

        # Anything else (mostly 5xx): worth exactly one retry.
        log.warning("FETCH FAIL %-70s  status=%d  attempt %d/%d — retrying",
                    url, resp.status_code, attempt, MAX_ATTEMPTS)
        if attempt < MAX_ATTEMPTS:
            time.sleep(1.5 * attempt)

    time.sleep(DELAY_SECONDS)
    return None, False, last_status
