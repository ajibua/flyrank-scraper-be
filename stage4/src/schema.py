"""
The recipe for a trustworthy record. Nothing reaches books.json without
passing through normalize() -> CleanBook first. If it can't be normalized
or doesn't fit the schema, it's a ValueError/ValidationError, and the
caller routes it to errors.json instead of storing it.
"""
from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


class CleanBook(BaseModel):
    title: str = Field(min_length=1)
    product_url: str          # canonical identity for the record
    price_gbp: float = Field(gt=0)
    price_text: str           # raw and clean values live side by side
    availability_text: str
    rating: int = Field(ge=1, le=5)
    rating_text: str
    description: str | None = None
    source_page: str
    fetched_at: str

    @field_validator("product_url", "source_page")
    @classmethod
    def must_be_absolute(cls, v: str) -> str:
        if not v.startswith("http"):
            raise ValueError(f"not an absolute URL: {v!r}")
        return v


def parse_price(price_text: str | None) -> float:
    if not price_text:
        raise ValueError("missing price_text")
    match = re.search(r"([\d,]+\.?\d*)", price_text)
    if not match:
        raise ValueError(f"unrecognized price format: {price_text!r}")
    return float(match.group(1).replace(",", ""))


def parse_rating(rating_text: str | None) -> int:
    if not rating_text or rating_text not in RATING_WORDS:
        raise ValueError(f"unrecognized rating word: {rating_text!r}")
    return RATING_WORDS[rating_text]


def normalize(raw: dict) -> CleanBook:
    """raw -> CleanBook, or raise ValueError / pydantic.ValidationError."""
    if not raw.get("title"):
        raise ValueError("missing title")

    price_gbp = parse_price(raw.get("price_text"))
    rating = parse_rating(raw.get("rating_text"))

    return CleanBook(
        title=raw["title"],
        product_url=raw["product_url"],
        price_gbp=price_gbp,
        price_text=raw["price_text"],
        availability_text=raw.get("availability_text") or "",
        rating=rating,
        rating_text=raw["rating_text"],
        description=raw.get("description"),
        source_page=raw["source_page"],
        fetched_at=raw["fetched_at"],
    )
