import buttons
from display import Display
from paginator import BookPaginator
import os

STATE_MENU = 0
STATE_READER = 1

class App:
    def __init__(self):
        self.display = Display()
        self.state = STATE_MENU
        self.books = self._list_books()
        self.cursor = 0
        self.book = None           # BookPaginator instance
        self.page_idx = 0
        self.refresh_count = 0

    def _list_books(self):
        try:
            return [f for f in os.listdir('/books') if f.endswith('.txt')]
        except:
            return []

    def run(self):
        self.draw_menu()
        while True:
            action = buttons.check()
            if action is None:
                continue
            if self.state == STATE_MENU:
                self._handle_menu(action)
            elif self.state == STATE_READER:
                self._handle_reader(action)

    def _handle_menu(self, action):
        if action == 'KEY0_short':
            self.cursor = max(0, self.cursor - 1)
            self.draw_menu()
        elif action == 'KEY1_short':
            self.cursor = min(len(self.books) - 1, self.cursor + 1)
            self.draw_menu()
        elif action == 'KEY0_long' and self.books:
            self._open_book(self.books[self.cursor])
        elif action == 'KEY1_long':
            self._sleep()

    def _open_book(self, filename):
        cpl = self.display.chars_per_line
        lpp = self.display.lines_per_screen
        self.book = BookPaginator('/books/' + filename, cpl, lpp)
        self.page_idx = 0
        self.state = STATE_READER
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
        elif action == 'KEY0_long':
            self._close_book()
            
    def _show_page(self, full=False):
        lines, actual_page, total = self.book.get_page(self.page_idx)
        self.page_idx = actual_page
        title = self.books[self.cursor].replace('.txt', '')
        page_num = '{}/{}'.format(actual_page + 1, total)

        self.refresh_count += 1
        if full or self.refresh_count % 10 == 0:
            self.display.full_refresh(lines, title, page_num)
            self.refresh_count = 0
        else:
            self.display.show_lines(lines, title, page_num)

    def draw_menu(self):
        lines, _ = self._menu_lines()
        self.display.show_lines(lines, 'E-READER', None)

    def _menu_lines(self):
        # remove the old title from the lines since it's now in the header
        lines = ['']
        if not self.books:
            lines.append('  No books found.')
            lines.append('  Upload .txt to /books/')
        else:
            for i, name in enumerate(self.books):
                prefix = '> ' if i == self.cursor else '  '
                lines.append(prefix + name)
        return lines, None

    def _close_book(self):
        self.book = None
        self.state = STATE_MENU
        self.display.full_refresh(*self._menu_lines())

    def _sleep(self):
        self.display.show_lines(['', '', '  Sleeping...', '  Press KEY0 to wake'], None)
        import utime
        utime.sleep_ms(2000)
        self.display.sleep()
        import machine
        while buttons.KEY0.value() == 1:
            machine.lightsleep(200)
        self.display = Display()
        self.draw_menu()

app = App()
app.run()