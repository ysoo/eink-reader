from constants import BOOKS_DIR, STATE_READER, STATE_MENU
from paginator import BookReader


def _mark_path(filename):
    return BOOKS_DIR + '/' + filename[:-4] + '.mark'

def _load_bookmark(filename):
    try:
        with open(_mark_path(filename)) as f:
            return int(f.read().strip())
    except:
        return 0

def _save_bookmark(filename, page):
    with open(_mark_path(filename), 'w') as f:
        f.write(str(page))


class ReaderMixin:

    def _open_book(self, filename):
        path = BOOKS_DIR + '/' + filename
        try:
            self.book = BookReader(path)
        except Exception as e:
            self.display.show_lines(['', 'Cannot open:', path, str(e)], 'ERROR', None)
            import utime; utime.sleep_ms(4000)
            self.draw_menu()
            return
        self.page_idx      = _load_bookmark(filename)
        self.state         = STATE_READER
        self.refresh_count = 0
        self._show_page(full=True)

    def _handle_reader(self, action):
        if action == 'KEY0_short':
            if self.page_idx > 0:
                self.page_idx -= 1
                self._show_page()
        elif action == 'KEY1_short':
            self.page_idx += 1
            self._show_page()
        elif action == 'KEY1_long':
            self._close_book()

    def _show_page(self, full=False):
        lines, actual, total = self.book.get_page(self.page_idx)
        self.page_idx = actual
        title    = self.book.title or self.books[self.cursor].replace('.bin', '')
        page_num = '{}/{}'.format(actual + 1, total)

        self.refresh_count += 1
        if full or self.refresh_count % 10 == 0:
            self.display.full_refresh(lines, title, page_num)
            self.refresh_count = 0
        else:
            self.display.show_lines(lines, title, page_num)

        if full or self.refresh_count == 0:
            _save_bookmark(self.books[self.cursor], actual)

    def _close_book(self):
        _save_bookmark(self.books[self.cursor], self.page_idx)
        self.book.close()
        self.book  = None
        self.state = STATE_MENU
        self.draw_menu(full=True)
