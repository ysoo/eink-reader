# Custom urequests for Pico 2 W.
# Shadows the built-in module to ensure HTTP/1.1 + chunked-encoding support.
# Azure Container Apps requires HTTP/1.1; the built-in sends HTTP/1.0.

import usocket
ssl = None
for _m in ('ussl', 'ssl'):
    try:
        import sys as _sys
        __import__(_m)
        ssl = _sys.modules[_m]
        break
    except ImportError:
        pass


class Response:
    def __init__(self, sock):
        self.raw = sock          # plain attribute — wifi.py uses resp.raw.read(n)
        self._content = None
        self.status_code = None
        self.headers = {}
        self.encoding = 'utf-8'

    def close(self):
        if self.raw:
            self.raw.close()
            self.raw = None

    @property
    def content(self):
        if self._content is None:
            chunked = self.headers.get('transfer-encoding', '') == 'chunked'
            if chunked:
                buf = []
                while True:
                    size = int(self.raw.readline().strip(), 16)
                    if size == 0:
                        break
                    buf.append(self.raw.read(size))
                    self.raw.readline()  # trailing \r\n
                self._content = b''.join(buf)
            else:
                self._content = self.raw.read()
            self.close()
        return self._content

    @property
    def text(self):
        return self.content.decode(self.encoding)


def request(method, url, data=None, headers=None):
    proto, _, host, path = url.split('/', 3)
    path = '/' + path
    port = 443 if proto == 'https:' else 80
    if ':' in host:
        host, port = host.rsplit(':', 1)
        port = int(port)

    ai = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)[0]
    s = usocket.socket(ai[0], ai[1], ai[2])
    try:
        s.connect(ai[-1])
        s.settimeout(45)
        if proto == 'https:':
            if ssl is None:
                raise OSError('no SSL module available for HTTPS')
            s = ssl.wrap_socket(s, server_hostname=host)

        s.write('{} {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n'.format(
            method, path, host).encode())
        if headers:
            for k, v in headers.items():
                s.write('{}: {}\r\n'.format(k, v).encode())
        if data is not None:
            s.write('Content-Length: {}\r\n'.format(len(data)).encode())
        s.write(b'\r\n')
        if data is not None:
            s.write(data)

        resp = Response(s)
        status_line = s.readline().split()
        resp.status_code = int(status_line[1])
        while True:
            line = s.readline()
            if line in (b'\r\n', b'\n', b''):
                break
            if b':' in line:
                k, v = line.decode().split(':', 1)
                resp.headers[k.strip().lower()] = v.strip()
        return resp
    except Exception:
        s.close()
        raise


def get(url, headers=None):
    return request('GET', url, headers=headers)


def post(url, data=None, headers=None):
    return request('POST', url, data=data, headers=headers)
