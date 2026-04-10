# Todo list persistence for the Pico.
#
# File format  (/sd/todo.txt):
#   0|Buy groceries
#   1|Call dentist
#   0|Review PR
#
#   '0' = pending, '1' = done
#   Text is max 43 chars (leaves room for "> [ ] " prefix on 47-char display).
#   Max 60 items (enforced by the server at brain-dump time).
#
# /sd/todo_dirty is an empty flag file that signals the app to upload
# the current todo.txt on the next WiFi sync.

from constants import STATE_TODO, STATE_MENU

TODO_PATH  = '/sd/todo.txt'
MAX_ITEMS  = 60
MAX_TEXT   = 43

def load():
    """Read todo.txt and return a list of {'text': str, 'done': bool}."""
    items = []
    try:
        with open(TODO_PATH) as f:
            for raw in f:
                line = raw.strip()
                if not line or '|' not in line:
                    continue
                status, text = line.split('|', 1)
                items.append({'text': text[:MAX_TEXT], 'done': status == '1'})
    except:
        pass
    return items


def save(items):
    """Write items back to todo.txt. Set dirty=False to skip the upload flag (e.g. after a server merge)."""
    with open(TODO_PATH, 'w') as f:
        for item in items[:MAX_ITEMS]:
            flag = '1' if item['done'] else '0'
            f.write('{}|{}\n'.format(flag, item['text'][:MAX_TEXT]))


def merge_incoming(incoming_path, dest_path):
    """
    Merge a todo_incoming.txt downloaded from the server into the local todo.txt.

    Rules:
      - Server is authoritative for item text and new items.
      - Device checkmarks (done=True) are preserved for items that match by text.
    """
    # Load current local state into a lookup {text: done}
    local_state = {}
    try:
        with open(dest_path) as f:
            for raw in f:
                line = raw.strip()
                if '|' in line:
                    status, text = line.split('|', 1)
                    local_state[text.strip()] = (status == '1')
    except:
        pass

    # Build merged list: server order + text, device done-state where available
    merged = []
    try:
        with open(incoming_path) as f:
            for raw in f:
                line = raw.strip()
                if not line or '|' not in line:
                    continue
                _, text = line.split('|', 1)
                text = text.strip()[:MAX_TEXT]
                done = local_state.get(text, False)
                merged.append({'text': text, 'done': done})
    except:
        return

    save(merged)


class TodoMixin:

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
        lines = ["TODO LIST", '']
        for i, item in enumerate(self.todo_items):
            check  = '[x]' if item['done'] else '[ ]'
            prefix = '>' if i == self.todo_cursor else ' '
            lines.append('{} {} {}'.format(prefix, check, item['text'][:43]))
        fn = self.display.full_refresh if full else self.display.show_lines
        fn(lines, "YI XIAN'S TODO", None)

    def _close_todo(self):
        del self.todo_items
        self.todo_items = None
        self.state      = STATE_MENU
        self.books      = self._list_books()
        self._clamp_menu()
        self.draw_menu(full=True)
