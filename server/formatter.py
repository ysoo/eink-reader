"""
Text formatting pipeline for the e-ink reader.

Each stage is a pure function with no side effects:
  sanitize(text)           -> str
  reflow(text)             -> str
  wrap(text, width)        -> str
  paginate(text, per_page) -> list[list[str]]
  encode_bin(pages, ...)   -> bytes

Call format_book() to run the full pipeline and get a ready-to-store bytes object.
"""

# Must match display.py on the Pico.
CHARS = 47
LINES = 21
LINE_W = CHARS + 1   # 47 visible chars + '\n'
PAGE_SIZE = LINE_W * LINES  # 1008 bytes


# ---------------------------------------------------------------------------
# Stage 1 — sanitize
# ---------------------------------------------------------------------------

_REPLACEMENTS = {
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
    "\u2013": "-",   # en-dash
    "\u2014": "--",  # em-dash
    "\u2026": "...", # ellipsis
    "\t":     "    ",
    "\r\n":   "\n",
    "\r":     "\n",
}


def sanitize(text: str) -> str:
    """Replace non-ASCII punctuation and strip anything that remains."""
    for src, dst in _REPLACEMENTS.items():
        text = text.replace(src, dst)
    return "".join(ch for ch in text if ch == "\n" or 32 <= ord(ch) <= 126)


# ---------------------------------------------------------------------------
# Stage 2 — reflow
# ---------------------------------------------------------------------------

def reflow(text: str) -> str:
    """
    Join consecutive non-blank lines into paragraphs, preserving blank lines
    as paragraph separators.

    This un-wraps hard-wrapped source files (e.g. Gutenberg 70-char lines)
    so that stage 3 can re-wrap cleanly at CHARS.
    """
    paragraphs = []
    current: list[str] = []

    for line in text.split("\n"):
        stripped = line.rstrip()
        if stripped:
            current.append(stripped)
        else:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            paragraphs.append("")  # preserve blank line

    if current:
        paragraphs.append(" ".join(current))

    # Collapse runs of more than one blank line to a single blank line.
    out: list[str] = []
    prev_blank = False
    for p in paragraphs:
        if p == "":
            if not prev_blank:
                out.append("")
            prev_blank = True
        else:
            out.append(p)
            prev_blank = False

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Stage 3 — word-wrap
# ---------------------------------------------------------------------------

def wrap(text: str, width: int = CHARS) -> str:
    """
    Wrap each line in *text* to at most *width* characters.
    Existing newlines are honoured: each input line is wrapped independently.
    Breaks at the last space before *width*; hard-breaks if no space exists.
    """
    out: list[str] = []
    for line in text.split("\n"):
        while len(line) > width:
            break_at = line.rfind(" ", 0, width + 1)
            if break_at <= 0:
                break_at = width
            out.append(line[:break_at].rstrip())
            line = line[break_at:].lstrip(" ")
        out.append(line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Stage 4 — paginate
# ---------------------------------------------------------------------------

def paginate(text: str, per_page: int = LINES) -> list[list[str]]:
    """
    Split wrapped text into pages of *per_page* lines each.
    Returns a list of pages; each page is a list of strings (already ≤ CHARS).
    """
    lines = text.split("\n")
    return [lines[i : i + per_page] for i in range(0, max(len(lines), 1), per_page)]


# ---------------------------------------------------------------------------
# Stage 5 — encode to fixed-size binary
# ---------------------------------------------------------------------------

def _make_header(title: str, author: str, page_count: int) -> bytes:
    meta = (
        f"TITLE:{title[:CHARS]}\n"
        f"AUTHOR:{author[:CHARS]}\n"
        f"PAGES:{page_count}\n"
        f"CHARS:{CHARS}\n"
        f"LINES:{LINES}\n"
    )
    raw = meta.encode("ascii", errors="replace")
    return raw.ljust(PAGE_SIZE, b"\x00")[:PAGE_SIZE]


def _encode_page(lines: list[str]) -> bytes:
    """Pad a page to exactly PAGE_SIZE bytes (LINE_W bytes per line, LINES lines)."""
    out = bytearray()
    for i in range(LINES):
        line = lines[i] if i < len(lines) else ""
        out.extend(line[:CHARS].ljust(CHARS).encode("ascii", errors="replace"))
        out.extend(b"\n")
    return bytes(out)


def encode_bin(pages: list[list[str]], title: str, author: str) -> bytes:
    """Combine header + all content pages into a single bytes object."""
    chunks = [_make_header(title, author, len(pages))]
    for page in pages:
        chunks.append(_encode_page(page))
    return b"".join(chunks)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def format_book(raw: str, title: str, author: str = "") -> bytes:
    """
    Run the complete pipeline on *raw* text and return the .bin bytes.
    Suitable for both epub-extracted text and uploaded .txt files.
    """
    text = sanitize(raw)
    text = reflow(text)
    text = wrap(text)
    pages = paginate(text)
    return encode_bin(pages, title, author)
