# How buttons work on the Pico:
# The pin is "pulled up" to 3.3V by default (reads 1).
# When you press the button, it connects the pin to ground (reads 0).
# So: pressed = 0, released = 1.
#
# "Debounce": a mechanical button bounces when pressed,
# sending rapid 0-1-0-1 signals. We ignore changes for
# a short window after detecting a press.

from machine import Pin
import utime

KEY0 = Pin(15, Pin.IN, Pin.PULL_UP)   # left button
KEY1 = Pin(17, Pin.IN, Pin.PULL_UP)   # right button

LONG_PRESS_MS = 300
DEBOUNCE_MS = 50

def wait_for_release(pin):
    """Block until the button is released, return how long it was held."""
    start = utime.ticks_ms()
    while pin.value() == 0:        # still pressed
        utime.sleep_ms(10)
    duration = utime.ticks_diff(utime.ticks_ms(), start)
    utime.sleep_ms(DEBOUNCE_MS)    # ignore bounce on release
    return duration

def check():
    """Call this in your main loop.
    Returns: 'KEY0_short', 'KEY0_long', 'KEY1_short', 'KEY1_long', or None
    """
    if KEY0.value() == 0:
        utime.sleep_ms(DEBOUNCE_MS)
        if KEY0.value() == 0:          # still pressed after debounce
            ms = wait_for_release(KEY0)
            return 'KEY0_long' if ms > LONG_PRESS_MS else 'KEY0_short'

    if KEY1.value() == 0:
        utime.sleep_ms(DEBOUNCE_MS)
        if KEY1.value() == 0:
            ms = wait_for_release(KEY1)
            return 'KEY1_long' if ms > LONG_PRESS_MS else 'KEY1_short'

    return None