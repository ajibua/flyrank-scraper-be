"""Stage 2: turn one catalogue listing page into book links + the next
page's URL. Links are relative — always resolved with urljoin, never by
gluing strings together."""
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
