# Fixed-size page reader for pre-paginated .bin book files.
#
# File layout produced by server/formatter.py:
#   Bytes [0,        PAGE_SIZE) — header  (metadata key:value, null-padded)
#   Bytes [PAGE_SIZE, 2*PS)    — page 1
#   Bytes [2*PS,     3*PS)     — page 2   ...
#
# Every page is exactly PAGE_SIZE bytes: LINES rows of LINE_W bytes each
# (CHARS visible characters + one '\n', space-padded).
# Seeking to page n is arithmetic: offset = (n + 1) * PAGE_SIZE.

PAGE_SIZE = 1008   # LINES * LINE_W  =  21 * 48
LINE_W    = 48     # CHARS + 1
LINES     = 21     # lines_per_screen - 1  (bottom row is the footer)


class BookReader:
    def __init__(self, path):
        self.f = open(path, 'rb')
        meta = self._parse_header(self.f.read(PAGE_SIZE))
        self.title       = meta.get('TITLE', '')
        self.total_pages = int(meta.get('PAGES', 0))

    @staticmethod
    def _parse_header(raw):
        out = {}
        for line in raw.decode('ascii', 'ignore').split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                out[k.strip()] = v.strip().rstrip('\x00')
        return out

    def get_page(self, n):
        n = max(0, min(n, self.total_pages - 1))
        self.f.seek((n + 1) * PAGE_SIZE)
        data = self.f.read(PAGE_SIZE)        # 1008 bytes; freed after display
        lines = [
            data[i * LINE_W : (i + 1) * LINE_W].decode('ascii', 'ignore').rstrip()
            for i in range(LINES)
        ]
        return lines, n, self.total_pages

    def close(self):
        self.f.close()
