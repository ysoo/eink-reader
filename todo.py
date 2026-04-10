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

TODO_PATH  = '/sd/todo.txt'
DIRTY_PATH = '/sd/todo_dirty'
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
    """Write items back to todo.txt and mark the file as dirty for upload."""
    with open(TODO_PATH, 'w') as f:
        for item in items[:MAX_ITEMS]:
            flag = '1' if item['done'] else '0'
            f.write('{}|{}\n'.format(flag, item['text'][:MAX_TEXT]))
    # Touch the dirty flag so app._wifi_sync() uploads on next connect
    with open(DIRTY_PATH, 'w') as f:
        pass


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
