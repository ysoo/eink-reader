def sanitize(text):
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')
    text = text.replace('\t', '    ')
    text = text.replace('\u2018', "'")
    text = text.replace('\u2019', "'")
    text = text.replace('\u201c', '"')
    text = text.replace('\u201d', '"')
    text = text.replace('\u2013', '-')
    text = text.replace('\u2014', '--')
    text = text.replace('\u2026', '...')
    out = []
    for ch in text:
        c = ord(ch)
        if ch == '\n':
            out.append(ch)
        elif 32 <= c <= 126:
            out.append(ch)
    return ''.join(out)

class BookPaginator:
    def __init__(self, filepath, chars_per_line, lines_per_page):
        self.filepath = filepath
        self.cpl = chars_per_line
        self.lpp = lines_per_page - 1
        self._page_offsets = [0]
        self._total_pages = None

    def _read_chunk(self, offset, size=4096):
        with open(self.filepath, 'rb') as f:
            f.seek(offset)
            raw = f.read(size)
        return raw.decode('utf-8', 'replace')

    def _wrap_lines(self, text, max_lines):
        lines = []
        pos = 0
        while pos < len(text) and len(lines) < max_lines:
            nl = text.find('\n', pos, pos + self.cpl + 1)
            if nl != -1 and nl - pos <= self.cpl:
                lines.append(text[pos:nl])
                pos = nl + 1
                continue
            if pos + self.cpl >= len(text):
                lines.append(text[pos:])
                pos = len(text)
                break
            segment = text[pos:pos + self.cpl]
            sp = segment.rfind(' ')
            if sp == -1:
                sp = self.cpl
            lines.append(text[pos:pos + sp])
            pos = pos + sp
            if pos < len(text) and text[pos] == ' ':
                pos += 1
        return lines, pos

    def get_page(self, page_num):
        while page_num >= len(self._page_offsets):
            if self._total_pages is not None:
                page_num = self._total_pages - 1
                break
            self._discover_next_page()

        offset = self._page_offsets[min(page_num, len(self._page_offsets) - 1)]
        raw_text = self._read_chunk(offset)
        sanitized = sanitize(raw_text)
        lines, chars_used = self._wrap_lines(sanitized, self.lpp)

        if not lines or chars_used == 0:
            self._total_pages = page_num
            return self.get_page(page_num - 1)

        total = self._total_pages if self._total_pages else '?'
        return lines, page_num, total

    def _discover_next_page(self):
        last_offset = self._page_offsets[-1]
        raw_text = self._read_chunk(last_offset)
        if not raw_text:
            self._total_pages = len(self._page_offsets) - 1
            return

        sanitized = sanitize(raw_text)
        _, chars_used = self._wrap_lines(sanitized, self.lpp)

        if chars_used == 0 or chars_used >= len(sanitized):
            self._total_pages = len(self._page_offsets)
            return

        # Map sanitized char count back to raw byte offset
        byte_offset = self._find_byte_offset(raw_text, chars_used)
        self._page_offsets.append(last_offset + byte_offset)

    def _find_byte_offset(self, raw_text, target_chars):
        """Find byte position in raw text that yields target_chars after sanitization."""
        sanitized_count = 0
        for i, ch in enumerate(raw_text):
            # Count characters that survive sanitization
            c = ord(ch)
            if ch == '\n' or (32 <= c <= 126):
                sanitized_count += 1
            elif ch in '\u2018\u2019\u201c\u201d\u2013\u2014\u2026':
                # Smart quotes/dashes become ASCII equivalents
                if ch == '\u2026':
                    sanitized_count += 3  # becomes '...'
                elif ch == '\u2014':
                    sanitized_count += 2  # becomes '--'
                else:
                    sanitized_count += 1

            if sanitized_count >= target_chars:
                # Return byte length up to and including this character
                return len(raw_text[:i+1].encode('utf-8'))

        return len(raw_text.encode('utf-8'))