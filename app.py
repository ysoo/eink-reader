import buttons
from display import Display
from constants import STATE_MENU, STATE_READER, STATE_TODO
from menu import MenuMixin
from reader import ReaderMixin
from todo import TodoMixin
from sync import SyncMixin


def _mount_sd():
    # SD card hardware not yet wired — no-op until pins are confirmed.
    # When ready: uncomment and set correct SPI1 pins.
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


class App(MenuMixin, ReaderMixin, TodoMixin, SyncMixin):

    def __init__(self):
        try:
            _mount_sd()
        except Exception:
            pass  # Continue without SD — books dir will just be empty

        self.display     = Display()
        self.state       = STATE_MENU
        self.books       = self._list_books()
        self.cursor      = 0
        self.menu_offset = 0

        # Reader state
        self.book          = None   # BookReader instance
        self.page_idx      = 0
        self.refresh_count = 0

        # Todo state (only populated while STATE_TODO is active)
        self.todo_items  = None
        self.todo_cursor = 0

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

    def _sleep(self):
        from ascii_art import sleepScreen
        self.display.show_lines(sleepScreen, 'Press KEY0 to wake', None)
        import utime, machine
        utime.sleep_ms(2000)
        self.display.sleep()
        while buttons.KEY0.value() == 1:
            machine.lightsleep(200)
        self.display = Display()
        self.draw_menu()

app = App()
app.run()
