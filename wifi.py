# WiFi helpers for the Pico 2 W.
#
# Design rules:
#   - connect() / disconnect() bracket every sync session in app.py
#   - No data is held in RAM between calls; response bodies stream to disk
#   - disconnect() calls wlan.active(False) to free the ~50 KB WiFi stack

import network
import utime

_wlan = network.WLAN(network.STA_IF)


def connect(ssid, password, timeout_ms=15_000):
    """Activate the interface and join the network. Returns True on success."""
    _wlan.active(True)
    if _wlan.isconnected():
        return True
    _wlan.connect(ssid, password)
    deadline = utime.ticks_ms() + timeout_ms
    while not _wlan.isconnected():
        if utime.ticks_diff(deadline, utime.ticks_ms()) <= 0:
            _wlan.active(False)
            return False
        utime.sleep_ms(100)
    return True


def disconnect():
    """Deactivate the interface and free the WiFi RAM (~50 KB)."""
    _wlan.active(False)


def get_json(url):
    """GET *url* and return the parsed JSON. Only for small payloads (queue list)."""
    import urequests, ujson
    resp = urequests.get(url)
    try:
        text = resp.text
        try:
            return ujson.loads(text)
        except ValueError:
            raise ValueError('HTTP {} body: {}'.format(resp.status_code, text))
    finally:
        resp.close()


def download_to_file(url, dest_path, chunk=512):
    """Stream GET *url* to *dest_path* in *chunk*-byte pieces. Never buffers the full body."""
    import urequests
    resp = urequests.get(url)
    try:
        if resp.status_code != 200:
            raise OSError('download failed: HTTP {}'.format(resp.status_code))
        with open(dest_path, 'wb') as f:
            while True:
                data = resp.raw.read(chunk)
                if not data:
                    break
                f.write(data)
    finally:
        resp.close()


def post_file(url, src_path, chunk=512):
    """Stream POST the contents of *src_path* to *url* in *chunk*-byte pieces."""
    import urequests
    # urequests on MicroPython doesn't support streaming body directly,
    # so we read in chunks and send with Content-Length pre-set.
    import uos
    size = uos.stat(src_path)[6]
    headers = {'Content-Type': 'text/plain', 'Content-Length': str(size)}

    # Build socket manually to stream without loading the whole file.
    # Fall back to full-read if the file is small enough (< 8 KB).
    if size <= 8192:
        with open(src_path, 'rb') as f:
            body = f.read()
        resp = urequests.post(url, data=body, headers=headers)
        resp.close()
    else:
        # For larger files use chunked streaming via raw socket.
        _post_file_chunked(url, src_path, size, chunk)


def _post_file_chunked(url, src_path, size, chunk):
    """Low-level chunked POST when the file exceeds the safe full-read threshold."""
    import usocket, ussl
    # Parse URL
    proto, _, host, path = url.split('/', 3)
    port = 443 if proto == 'https:' else 80
    if ':' in host:
        host, port = host.split(':', 1)
        port = int(port)

    addr = usocket.getaddrinfo(host, port)[0][-1]
    s = usocket.socket()
    s.connect(addr)
    if proto == 'https:':
        s = ussl.wrap_socket(s, server_hostname=host)

    request = (
        'POST /{} HTTP/1.1\r\n'
        'Host: {}\r\n'
        'Content-Type: text/plain\r\n'
        'Content-Length: {}\r\n'
        'Connection: close\r\n\r\n'
    ).format(path, host, size)
    s.write(request.encode())

    with open(src_path, 'rb') as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            s.write(data)
    s.close()
