import os
from constants import BOOKS_DIR, TODO_PATH, MENU_SYNC, MENU_TODO, MENU_VISIBLE


def _wrap(text, width):
    lines = []
    while len(text) > width:
        lines.append(text[:width])
        text = text[width:]
    lines.append(text)
    return lines


class MenuMixin:

    def _list_books(self):
        specials = [MENU_SYNC]
        try:
            os.stat(TODO_PATH)
            specials.append(MENU_TODO)
        except:
            pass
        books = []
        try:
            books = sorted(f for f in os.listdir(BOOKS_DIR) if f.endswith('.bin'))
        except:
            pass
        return specials + books

    def _clamp_menu(self):
        """Keep cursor and scroll offset in bounds after the book list changes."""
        if self.books:
            self.cursor = min(self.cursor, len(self.books) - 1)
        else:
            self.cursor = 0
        self.menu_offset = max(0, min(self.menu_offset,
                                      max(0, len(self.books) - MENU_VISIBLE)))

    def draw_menu(self, full=False):
        lines = self._menu_lines()
        fn = self.display.full_refresh if full else self.display.show_lines
        n = len(self.books)
        page_num = '{}/{}'.format(self.cursor + 1, n) if n > MENU_VISIBLE else None
        fn(lines, 'YI XIANS E-READER', page_num)

    def _menu_lines(self):
        lines = ['']
        if not self.books:
            lines.append('  No books found.')
            lines.append('  Upload .bin to /sd/books/')
        else:
            end = self.menu_offset + MENU_VISIBLE
            for i in range(self.menu_offset, min(end, len(self.books))):
                prefix = '> ' if i == self.cursor else '  '
                lines.append(prefix + self.books[i])
            below = len(self.books) - end
            if below > 0:
                lines.append('  v {} more'.format(below))
        return lines

    def _handle_menu(self, action):
        if action == 'KEY0_short':
            self.cursor = max(0, self.cursor - 1)
            if self.cursor < self.menu_offset:
                self.menu_offset = self.cursor
            self.draw_menu()
        elif action == 'KEY1_short':
            self.cursor = min(len(self.books) - 1, self.cursor + 1)
            if self.cursor >= self.menu_offset + MENU_VISIBLE:
                self.menu_offset = self.cursor - MENU_VISIBLE + 1
            self.draw_menu()
        elif action == 'KEY0_long':
            self._menu_select()
        elif action == 'KEY1_long':
            self._sleep()

    def _menu_select(self):
        if not self.books:
            return
        selected = self.books[self.cursor]
        if selected == MENU_SYNC:
            try:
                self._wifi_sync()
            except Exception as e:
                lines = ['', 'Sync error:'] + _wrap(str(e), 45)
                self.display.show_lines(lines, 'SYNC', None)
                import utime; utime.sleep_ms(4000)
                self.draw_menu()
        elif selected == MENU_TODO:
            self._open_todo()
        else:
            self._open_book(selected)
