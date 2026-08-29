"""A scraper that reports nothing can fail silently for weeks. This is how
you'd notice."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RunReport:
    started_at: str
    catalogue_pages_fetched: int = 0
    cache_hits: int = 0
    detail_pages_fetched: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    failed_pages: int = 0
    duration_seconds: float = 0.0

    def write(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
