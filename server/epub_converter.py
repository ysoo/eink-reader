"""
epub → plain text extractor.

Reads the epub spine in order, strips HTML tags, and returns a single
sanitised string ready for the formatter pipeline.

Usage:
    from epub_converter import extract_text
    from formatter import format_book

    raw = extract_text(epub_bytes)
    bin_data = format_book(raw, title="My Book", author="Author Name")
"""

import io
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


def extract_text(epub_bytes: bytes) -> tuple[str, str, str]:
    """
    Parse an epub from raw bytes.

    Returns:
        (text, title, author) — plain text body, book title, book author.
        title and author fall back to empty strings if not found in metadata.
    """
    book = epub.read_epub(io.BytesIO(epub_bytes))

    title = _first_meta(book, "title")
    author = _first_meta(book, "creator")
    text = _extract_body(book)

    return text, title, author


def _first_meta(book: epub.EpubBook, key: str) -> str:
    values = book.get_metadata("DC", key)
    if values:
        raw = values[0][0]
        return raw.strip() if isinstance(raw, str) else ""
    return ""


def _extract_body(book: epub.EpubBook) -> str:
    """Walk the spine in order and concatenate the text of each document."""
    parts: list[str] = []

    for item_id, _ in book.spine:
        item = book.get_item_with_id(item_id)
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue

        html = item.get_content().decode("utf-8", errors="replace")
        parts.append(_html_to_text(html))

    return "\n\n".join(parts)


def _html_to_text(html: str) -> str:
    """
    Strip HTML markup and return readable plain text.

    Block-level elements (p, div, h1-h6, br, li) become newlines so that
    the formatter's reflow stage can treat them as paragraph boundaries.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Insert newlines at block boundaries before stripping tags.
    for tag in soup.find_all(["p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6"]):
        tag.insert_before("\n")
        tag.insert_after("\n")

    return soup.get_text()
