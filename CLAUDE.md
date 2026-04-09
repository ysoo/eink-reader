# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MicroPython-based e-reader for Raspberry Pi Pico W with Waveshare 4.2" e-Paper display (400x300, epd4in2_V2 driver). Two physical buttons for navigation: KEY0 (GP15) and KEY1 (GP17).

## Hardware Constraints

**Critical RAM limitation**: 264KB total. WiFi stack consumes ~40-60KB when active.

**Never hold entire files in RAM**. All file operations must use chunked reading (≤1KB chunks recommended). This applies to:
- Book sanitization during opening
- Page rendering from text files
- Any future file upload/download features

**Display**: Built-in framebuf font is fixed 8x8 pixels, ASCII 32-126 only. Non-ASCII characters render as grey boxes.

## Architecture

### State Machine (app.py)
Two states: `STATE_MENU` (book selection) and `STATE_READER` (reading mode).
- Entry point at bottom of `app.py` (instantiates and runs `App`)
- `main.py` is minimal shim: `import app`

### Data Flow for Book Opening
1. User selects book from `/books/*.txt` (raw, potentially non-ASCII)
2. `_open_book()` creates `BookPaginator` pointing directly at `/books/filename`
3. Paginator sanitizes on-the-fly during each page read (only current 4KB chunk in RAM)
4. On close: free paginator (no temp files to clean up)

### Pagination Strategy (paginator.py)
- **Lazy offset discovery**: `_page_offsets` list grows as user navigates forward
- **Chunk-based reading**: `_read_chunk()` reads 4KB from raw book file
- **On-the-fly sanitization**: Each chunk sanitized during display (never stored)
- **Word wrapping**: `_wrap_lines()` breaks at spaces when possible
- **Byte offset tracking**: `_find_byte_offset()` maps sanitized character count back to raw file byte position, accounting for:
  - Removed non-ASCII characters
  - Smart quote replacements (1 char → 1 char)
  - Em-dash → '--' (1 char → 2 chars)
  - Ellipsis → '...' (1 char → 3 chars)
  - Multi-byte UTF-8 sequences

Important: Books are stored raw in `/books/`, sanitized only during display. No intermediate files created.

### Display Refresh Strategy (display.py)
- **Partial refresh** for page turns (fast, low ghosting)
- **Full refresh** every 10 pages + state transitions (prevents ghost accumulation)
- Footer shows book title (left) and page number (right)
- Content area calculated with margins, reserves bottom space for footer

### Button Debouncing (buttons.py)
- Buttons are pull-up (pressed = 0, released = 1)
- Debounce window: 50ms
- Long press threshold: 300ms
- `check()` is non-blocking, called in main loop

## Deployment Commands

**Prerequisites**: Python 3.x and `mpremote` installed (`pip install mpremote`)

**Upload all source files** (replace `COM3` with your port, check Device Manager on Windows):
```bash
mpremote connect COM3 fs cp app.py :app.py
mpremote connect COM3 fs cp buttons.py :buttons.py
mpremote connect COM3 fs cp display.py :display.py
mpremote connect COM3 fs cp paginator.py :paginator.py
mpremote connect COM3 fs cp main.py :main.py
mpremote connect COM3 fs cp epd4in2_V2.py :epd4in2_V2.py
```

**Create books directory**:
```bash
mpremote connect COM3 fs mkdir /books
```

**Upload a book**:
```bash
mpremote connect COM3 fs cp yourbook.txt :/books/yourbook.txt
```

**Reset to run**:
```bash
mpremote connect COM3 reset
```

**Interactive REPL** (for debugging):
```bash
mpremote connect COM3
```

**View live output**:
```bash
mpremote connect COM3 mount . exec "import main"
```

## Files on Pico

- `epd4in2_V2.py` — Waveshare driver (DO NOT MODIFY, vendor-provided)
- `display.py` — Framebuffer wrapper, manages refresh strategy
- `buttons.py` — GPIO debouncing, short/long press detection
- `paginator.py` — Lazy file-based pagination with on-the-fly sanitization
- `app.py` — State machine and entry point
- `main.py` — Bootstrap shim
- `/books/*.txt` — User book files (raw text, UTF-8, can contain non-ASCII)

## Button Mappings

**MENU state**:
- KEY0_short: cursor up
- KEY1_short: cursor down
- KEY0_long: select/open book
- KEY1_long: sleep mode

**READER state**:
- KEY0_short: previous page
- KEY1_short: next page
- KEY0_long: back to menu

## Upcoming Features

- WiFi upload mode (modal web server for .txt uploads)
- Web dashboard (upload UI + todo list management)
- microSD card support on SPI0 (expanded storage beyond Pico flash)

## Development Rules

**Memory discipline**:
- Always process files in chunks (4KB for reading, smaller for writing)
- Never create intermediate files - sanitize/process on-the-fly
- Use `del` to free large objects explicitly
- Paginator only holds: current 4KB chunk, ~10 page offsets, minimal state

**Display handling**:
- Prefer partial refresh for page turns
- Full refresh every 10 pages or state change
- Test on actual hardware (ghosting behavior differs from simulation)

**Text handling**:
- Books stored raw in `/books/`, never pre-processed
- Sanitization happens on-the-fly during pagination (per 4KB chunk)
- `_find_byte_offset()` must account for character expansion (e.g., '…' → '...')
- Non-ASCII stripped/replaced only for display, original files untouched

**Never modify** `epd4in2_V2.py` (Waveshare vendor driver).
