from epd4in2_V2 import EPD_4in2

CHAR_W = 8
CHAR_H = 8
PADDING = 4
LINE_H = CHAR_H + PADDING

MARGIN = 10

class Display:
    def __init__(self):
        self.epd = EPD_4in2()
        self.w = self.epd.width
        self.h = self.epd.height
        self.fb = self.epd.image1Gray

        self.content_x = MARGIN
        self.content_y = MARGIN
        self.content_w = self.w - 2 * MARGIN
        self.content_h = self.h - 2 * MARGIN - CHAR_H - 4

        self.chars_per_line = self.content_w // CHAR_W
        self.lines_per_screen = self.content_h // LINE_H

    def _draw_footer(self, left=None, right=None):
        y = self.h - CHAR_H - 2
        if left:
            self.fb.text(left, MARGIN, y, 0x00)
        if right:
            x = self.w - MARGIN - len(right) * CHAR_W
            self.fb.text(right, x, y, 0x00)

    def show_lines(self, lines, footer_left=None, footer_right=None):
        self.epd.ReadBusy()
        self.fb.fill(0xff)
        for i, line in enumerate(lines):
            if i >= self.lines_per_screen:
                break
            self.fb.text(line, self.content_x,
                         self.content_y + i * LINE_H, 0x00)
        self._draw_footer(footer_left, footer_right)
        self.epd.EPD_4IN2_V2_PartialDisplay(self.epd.buffer_1Gray)

    def full_refresh(self, lines, footer_left=None, footer_right=None):
        self.epd.ReadBusy()
        self.epd.EPD_4IN2_V2_Init()
        self.fb.fill(0xff)
        for i, line in enumerate(lines):
            if i >= self.lines_per_screen:
                break
            self.fb.text(line, self.content_x,
                         self.content_y + i * LINE_H, 0x00)
        self._draw_footer(footer_left, footer_right)
        self.epd.EPD_4IN2_V2_Display(self.epd.buffer_1Gray)

    def sleep(self):
        self.epd.Sleep()