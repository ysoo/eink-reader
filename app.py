import os
import buttons
from display import Display
from paginator import BookReader

STATE_MENU   = 0
STATE_READER = 1
STATE_TODO   = 2

# SD card paths — swap to /sd/books etc. once SD hardware is wired up
BOOKS_DIR   = '/sd/books'
TODO_PATH   = '/sd/todo.txt'
TODO_DIRTY  = '/sd/todo_dirty'

MENU_SYNC = '[ Sync ]'
MENU_TODO = '[ Todo ]'

LINE_W = 47  # matches display.py chars_per_line


def _wrap(text, width=LINE_W):
    """Split *text* into a list of lines, each at most *width* characters."""
    lines = []
    while len(text) > width:
        lines.append(text[:width])
        text = text[width:]
    lines.append(text)
    return lines


# ---------------------------------------------------------------------------
# SD card mount
# ---------------------------------------------------------------------------

def _mount_sd():
    # SD card hardware not yet wired — no-op until pins are confirmed.
    # When ready: uncomment, set correct SPI1 pins, swap BOOKS_DIR to /sd/books.
    #
    # import machine, sdcard, uos
    # spi = machine.SPI(1,
    #                   baudrate=4_000_000,
    #                   sck=machine.Pin(10),
    #                   mosi=machine.Pin(11),
    #                   miso=machine.Pin(8))
    # cs  = machine.Pin(9, machine.Pin.OUT)
    # sd  = sdcard.SDCard(spi, cs)
    # uos.mount(sd, '/sd')
    pass


# ---------------------------------------------------------------------------
# Bookmark helpers  (sidecar .mark files next to each .bin)
# ---------------------------------------------------------------------------

def _mark_path(filename):
    return BOOKS_DIR + '/' + filename.replace('.bin', '.mark')

def _load_bookmark(filename):
    path = _mark_path(filename)
    try:
        with open(path) as f:
            return int(f.read().strip())
    except:
        return 0

def _save_bookmark(filename, page):
    with open(_mark_path(filename), 'w') as f:
        f.write(str(page))


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class App:
    def __init__(self):
        try:
            _mount_sd()
        except Exception as e:
            pass  # Continue without SD — books dir will just be empty

        self.display = Display()
        self.state   = STATE_MENU
        self.books   = self._list_books()
        self.cursor  = 0

        # Reader state
        self.book      = None   # BookReader instance
        self.page_idx  = 0
        self.refresh_count = 0

        # Todo state  (only populated while STATE_TODO is active)
        self.todo_items  = None
        self.todo_cursor = 0

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        self._wifi_sync_silent()
        self.draw_menu()
        while True:
            action = buttons.check()
            if action is None:
                continue
            if self.state == STATE_MENU:
                self._handle_menu(action)
            elif self.state == STATE_READER:
                self._handle_reader(action)
            elif self.state == STATE_TODO:
                self._handle_todo(action)

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------

    def _list_books(self):
        books = []
        try:
            books = sorted(f for f in os.listdir(BOOKS_DIR) if f.endswith('.bin'))
        except:
            pass
        specials = []
        try:
            os.stat(TODO_PATH)
            specials.append(MENU_TODO)
        except:
            pass
        specials.append(MENU_SYNC)
        return books + specials

    def draw_menu(self):
        lines, _ = self._menu_lines()
        self.display.show_lines(lines, 'E-READER', None)

    def _menu_lines(self):
        lines = ['']
        if not self.books:
            lines.append('  No books found.')
            lines.append('  Upload .bin to /sd/books/')
        else:
            for i, name in enumerate(self.books):
                prefix = '> ' if i == self.cursor else '  '
                lines.append(prefix + name)
        return lines, None

    def _handle_menu(self, action):
        if action == 'KEY0_short':
            self.cursor = max(0, self.cursor - 1)
            self.draw_menu()
        elif action == 'KEY1_short':
            self.cursor = min(len(self.books) - 1, self.cursor + 1)
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
                lines = ['', 'Sync error:'] + _wrap(str(e))
                self.display.show_lines(lines, 'SYNC', None)
                import utime; utime.sleep_ms(4000)
                self.draw_menu()
        elif selected == MENU_TODO:
            self._open_todo()
        else:
            self._open_book(selected)

    # ------------------------------------------------------------------
    # Reader
    # ------------------------------------------------------------------

    def _open_book(self, filename):
        path = BOOKS_DIR + '/' + filename
        try:
            self.book = BookReader(path)
        except Exception as e:
            lines = ['', 'Cannot open:', path, str(e)]
            self.display.show_lines(lines, 'ERROR', None)
            import utime; utime.sleep_ms(4000)
            self.draw_menu()
            return
        self.page_idx = _load_bookmark(filename)
        self.state   = STATE_READER
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

        # Persist bookmark every 10 page turns and on every full refresh
        if full or self.refresh_count == 0:
            _save_bookmark(self.books[self.cursor], actual)

    def _close_book(self):
        _save_bookmark(self.books[self.cursor], self.page_idx)
        self.book.close()
        self.book  = None
        self.state = STATE_MENU
        self.display.full_refresh(*self._menu_lines())

    # ------------------------------------------------------------------
    # Todo
    # ------------------------------------------------------------------

    def _open_todo(self):
        import todo
        self.todo_items  = todo.load()
        self.todo_cursor = 0
        self.state       = STATE_TODO
        self._draw_todo(full=True)

    def _handle_todo(self, action):
        if not self.todo_items:
            if action == 'KEY1_long':
                self._close_todo()
            return
        if action == 'KEY0_short':
            self.todo_cursor = max(0, self.todo_cursor - 1)
            self._draw_todo()
        elif action == 'KEY1_short':
            self.todo_cursor = min(len(self.todo_items) - 1, self.todo_cursor + 1)
            self._draw_todo()
        elif action == 'KEY0_long':
            import todo
            self.todo_items[self.todo_cursor]['done'] ^= True
            todo.save(self.todo_items)
            self._draw_todo()
        elif action == 'KEY1_long':
            self._close_todo()

    def _draw_todo(self, full=False):
        from display import Display
        lines = ['TODO LIST', '']
        for i, item in enumerate(self.todo_items):
            check  = '[x]' if item['done'] else '[ ]'
            prefix = '>' if i == self.todo_cursor else ' '
            text   = item['text'][:43]
            lines.append('{} {} {}'.format(prefix, check, text))
        fn = self.display.full_refresh if full else self.display.show_lines
        fn(lines, 'TODO', None)

    def _close_todo(self):
        del self.todo_items
        self.todo_items = None
        self.state      = STATE_MENU
        self.books      = self._list_books()  # refresh in case sync added items
        self.display.full_refresh(*self._menu_lines())

    # ------------------------------------------------------------------
    # WiFi sync
    # ------------------------------------------------------------------

    def _wifi_sync_silent(self):
        """Sync on startup without user feedback if WiFi connects quickly."""
        try:
            self._wifi_sync(silent=True)
        except:
            pass

    def _wifi_sync(self, silent=False):
        import wifi, config, ujson, os as _os

        if not silent:
            self.display.show_lines(['', '  Connecting...'], 'SYNC', None)

        if not wifi.connect(config.WIFI_SSID, config.WIFI_PASSWORD):
            if not silent:
                self.display.show_lines(['', '  WiFi failed.'], 'SYNC', None)
                import utime; utime.sleep_ms(1500)
            return

        try:
            queue = wifi.get_json(config.SERVER_URL + '/api/queue')

            for item in queue:
                try:
                    if item['type'] == 'book':
                        dest = BOOKS_DIR + '/' + item['name']
                        if not silent:
                            self.display.show_lines(
                                ['', '  ' + item['name'][:43]], 'SYNC', None)
                        wifi.download_to_file(item['url'], dest)

                    elif item['type'] == 'todo':
                        wifi.download_to_file(item['url'], '/sd/todo_incoming.txt')
                except Exception:
                    pass  # Skip failed items; ack still clears the queue

            # Upload dirty todo before disconnecting
            try:
                _os.stat(TODO_DIRTY)
                wifi.post_file(config.SERVER_URL + '/api/todo/sync', TODO_PATH)
                _os.remove(TODO_DIRTY)
            except:
                pass

            wifi.get_json(config.SERVER_URL + '/api/queue/ack')

        finally:
            wifi.disconnect()   # always free the ~50 KB, even on error

        # Merge incoming todo after WiFi is off (no RAM pressure)
        try:
            _os.stat('/sd/todo_incoming.txt')
            import todo
            todo.merge_incoming('/sd/todo_incoming.txt', TODO_PATH)
            _os.remove('/sd/todo_incoming.txt')
        except:
            pass

        self.books = self._list_books()
        if not silent:
            self.display.full_refresh(*self._menu_lines())

    # ------------------------------------------------------------------
    # Sleep
    # ------------------------------------------------------------------

    def _sleep(self):
        self.display.show_lines(['', '', '  Sleeping...', '  Press KEY0 to wake'], None, None)
        import utime, machine
        utime.sleep_ms(2000)
        self.display.sleep()
        while buttons.KEY0.value() == 1:
            machine.lightsleep(200)
        self.display = Display()
        self.draw_menu()


app = App()
app.run()


