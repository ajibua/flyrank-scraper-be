"""
Unit tests for the parser and schema. None of these touch the network —
that's the point: parsing logic should be provable on your own machine,
against fixtures you control.

Run with:  pytest tests/
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest  # noqa: E402

from extractor import extract_book_links, extract_raw_record  # noqa: E402
from schema import normalize, parse_price  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def test_price_normalization():
    assert parse_price("£51.77") == 51.77
    assert parse_price("£1,234.50") == 1234.50


def test_price_normalization_rejects_unparseable_text():
    with pytest.raises(ValueError):
        parse_price("Contact for price")


def test_relative_links_become_absolute_urls():
    html = """
    <ol class="row"><li><article class="product_pod">
      <h3><a href="../../a-light-in-the-attic_1000/index.html"
             title="A Light in the Attic">A Light in the ...</a></h3>
    </article></li></ol>
    """
    links = extract_book_links(html, "https://books.toscrape.com/catalogue/page-1.html")
    assert links == ["https://books.toscrape.com/a-light-in-the-attic_1000/index.html"]


def test_missing_description_is_stored_as_none_not_invented():
    html = (FIXTURES / "missing_description.html").read_text(encoding="utf-8")
    record = extract_raw_record(
        html,
        product_url="https://books.toscrape.com/no-description_1/index.html",
        source_page="https://books.toscrape.com/catalogue/page-1.html",
        fetched_at="2026-08-06T10:00:00Z",
    )
    assert record["description"] is None
    # and it still normalizes cleanly — a missing description isn't invalid data
    clean = normalize(record)
    assert clean.description is None
    assert clean.price_gbp == 10.00


def test_duplicate_urls_are_removed():
    urls = [
        "https://books.toscrape.com/a/index.html",
        "https://books.toscrape.com/b/index.html",
        "https://books.toscrape.com/a/index.html",
    ]
    unique = list(dict.fromkeys(urls))
    assert unique == [
        "https://books.toscrape.com/a/index.html",
        "https://books.toscrape.com/b/index.html",
    ]


def test_malformed_fixture_is_rejected_by_the_schema_not_the_run():
    html = (FIXTURES / "malformed_price.html").read_text(encoding="utf-8")
    record = extract_raw_record(
        html,
        product_url="https://books.toscrape.com/broken/index.html",
        source_page="https://books.toscrape.com/catalogue/page-2.html",
        fetched_at="2026-08-06T10:00:00Z",
    )
    # extraction itself never raises — it just captures what's on the page
    assert record["price_text"] == "Contact for price"
    # normalization is where an untrustworthy record gets caught
    with pytest.raises(ValueError):
        normalize(record)
