"""
Extraction only reads what's on the page — it never invents a value.
A missing description becomes None, not an empty string and not a guess.
"""
from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup


def extract_book_links(html: str, page_url: str) -> list[str]:
    """Absolute URLs of every book on one catalogue listing page."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.select("article.product_pod h3 a"):
        href = a.get("href")
        if href:
            links.append(urljoin(page_url, href))
    return links


def extract_next_page_url(html: str, page_url: str) -> str | None:
    """Follow the catalogue's own 'next' link — never hardcode page numbers."""
    soup = BeautifulSoup(html, "html.parser")
    next_a = soup.select_one("li.next a")
    if next_a and next_a.get("href"):
        return urljoin(page_url, next_a["href"])
    return None


def extract_raw_record(html: str, product_url: str, source_page: str, fetched_at: str) -> dict:
    """Pull the eight raw fields from one book detail page, untouched and
    unvalidated — normalization and schema checks happen later, in schema.py.
    """
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("div.product_main") or soup

    title_el = main.select_one("h1")
    title = title_el.get_text(strip=True) if title_el else None

    price_el = main.select_one("p.price_color")
    price_text = price_el.get_text(strip=True) if price_el else None

    avail_el = main.select_one("p.instock.availability")
    availability_text = avail_el.get_text(" ", strip=True) if avail_el else None

    rating_el = main.select_one("p.star-rating")
    rating_text = None
    if rating_el:
        classes = [c for c in rating_el.get("class", []) if c != "star-rating"]
        rating_text = classes[0] if classes else None

    description = None
    desc_heading = soup.select_one("#product_description")
    if desc_heading:
        desc_p = desc_heading.find_next_sibling("p")
        if desc_p:
            description = desc_p.get_text(strip=True)

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }
