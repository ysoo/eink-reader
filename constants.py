# Shared constants for app.py and its mixins.

STATE_MENU   = 0
STATE_READER = 1
STATE_TODO   = 2

BOOKS_DIR    = '/sd/books'
TODO_PATH    = '/sd/todo.txt'
TODO_DIRTY   = '/sd/todo_dirty'

MENU_SYNC    = '[ Sync ]'
MENU_TODO    = '[ Todo ]'

LINE_W       = 47   # display.py chars_per_line
MENU_VISIBLE = 20   # items per scroll window (22 screen lines - 1 blank - 1 indicator)
