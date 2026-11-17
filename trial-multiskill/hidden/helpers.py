"""Test harness for the hidden Docket tests. Standard library only.

Drives the WSGI app in-process: no sockets, no real DNS, no real HTTP. Every
external effect the ticket routes through an injected callable (clock,
http_post, resolve) is replaced by a fake that records what happened.
"""
import io
import json
import logging
import os
import shutil
import tempfile
import threading
import unittest
import urllib.parse
from pathlib import Path
from wsgiref.util import setup_testing_defaults

ROOT = Path(__file__).resolve().parent.parent  # the solution under test
START_TIME = 1_700_000_000.0
PUBLIC_IP = "93.184.216.34"  # documentation-adjacent public address, never contacted


class FakeClock:
    def __init__(self, t=START_TIME):
        self.t = float(t)
        self._lock = threading.Lock()

    def __call__(self):
        with self._lock:
            return self.t

    def advance(self, seconds):
        with self._lock:
            self.t += seconds


class FakeHTTP:
    """Records every http_post call. `responder(url, body, headers, n)` decides
    the outcome (return a status or raise); default 200."""

    def __init__(self, responder=None):
        self.calls = []
        self.responder = responder
        self._lock = threading.Lock()

    def __call__(self, url, body, headers):
        with self._lock:
            n = len(self.calls)
            self.calls.append((url, bytes(body), dict(headers)))
        if self.responder is None:
            return 200
        return self.responder(url, body, headers, n)

    def calls_to(self, url):
        return [c for c in self.calls if c[0] == url]


class FakeResolver:
    """host -> list of IP strings. Unknown hosts raise OSError (NXDOMAIN)."""

    def __init__(self, table=None):
        self.table = dict(table or {})
        self.lookups = []

    def __call__(self, host):
        self.lookups.append(host)
        if host in self.table:
            return list(self.table[host])
        raise OSError(f"unknown host {host}")


class Response:
    def __init__(self, status_line, headers, body):
        self.status = int(status_line.split(" ", 1)[0])
        self.status_line = status_line
        self.header_list = list(headers)
        self.headers = {k.lower(): v for k, v in headers}
        self.body = body

    def json(self):
        return json.loads(self.body.decode("utf-8"))

    def __repr__(self):
        return f"<Response {self.status_line} {self.body[:200]!r}>"


class LazyZeros(io.RawIOBase):
    """A request body that yields zero bytes up to `limit`, then EOF, without
    allocating more than what the reader asks for. Counts bytes consumed."""

    def __init__(self, limit):
        self.remaining = limit
        self.consumed = 0

    def readable(self):
        return True

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.remaining
        n = min(n, self.remaining)
        self.remaining -= n
        self.consumed += n
        return b"\0" * n

    def readline(self, size=-1):
        return self.read(size if size and size > 0 else 65536)

    def readinto(self, b):
        data = self.read(len(b))
        b[: len(data)] = data
        return len(data)


def call_wsgi(app, method, path, *, query=None, body=b"", headers=None,
              token=None, json_body=None, input_stream=None,
              content_length=None, remote_addr="203.0.113.7"):
    """Call the WSGI app once. Exceptions from the app propagate (a crash is a
    test failure unless a test catches it on purpose)."""
    environ = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method
    environ["PATH_INFO"] = path
    environ["QUERY_STRING"] = urllib.parse.urlencode(query) if query else ""
    environ["REMOTE_ADDR"] = remote_addr
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        environ["CONTENT_TYPE"] = "application/json"
    if input_stream is None:
        input_stream = io.BytesIO(body)
        if content_length is None:
            content_length = str(len(body))
    environ["wsgi.input"] = input_stream
    environ["wsgi.errors"] = io.StringIO()
    if content_length is not None:
        environ["CONTENT_LENGTH"] = str(content_length)
    for k, v in (headers or {}).items():
        key = k.upper().replace("-", "_")
        if key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            environ[key] = v
        else:
            environ["HTTP_" + key] = v
    if token is not None:
        environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    captured = {}

    def start_response(status, response_headers, exc_info=None):
        captured["status"] = status
        captured["headers"] = response_headers
        return lambda data: captured.setdefault("written", []).append(data)

    result = app(environ, start_response)
    try:
        chunks = list(captured.get("written", []))
        for chunk in result:
            chunks.append(chunk)
    finally:
        if hasattr(result, "close"):
            result.close()
    return Response(captured["status"], captured["headers"], b"".join(chunks))


class LogCapture(logging.Handler):
    """Captures records from the `docket` logger tree and the root logger."""

    NAMES = ("", "docket", "docket.activity")

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []
        self._seen = set()
        self._saved = []

    def emit(self, record):
        if id(record) in self._seen:
            return
        self._seen.add(id(record))
        self.records.append(record)

    def __enter__(self):
        for name in self.NAMES:
            lg = logging.getLogger(name)
            self._saved.append((lg, lg.level))
            if name:
                lg.setLevel(logging.DEBUG)
            lg.addHandler(self)
        return self

    def __exit__(self, *exc):
        for lg, level in self._saved:
            lg.removeHandler(self)
            lg.setLevel(level)
        return False

    @staticmethod
    def full_text(record):
        try:
            msg = record.getMessage()
        except Exception:  # a malformed record is still evidence
            msg = str(record.msg)
        extra = {k: v for k, v in record.__dict__.items()
                 if k not in ("msg", "args", "exc_info", "stack_info")}
        parts = [msg, str(record.msg), repr(record.args), repr(extra)]
        if record.exc_info:
            parts.append(logging.Formatter().formatException(record.exc_info))
        return "\n".join(parts)

    def texts(self, start=0):
        return [self.full_text(r) for r in self.records[start:]]


class DocketCase(unittest.TestCase):
    """Fresh database, fresh fakes, two tenants with users, per test."""

    PASSWORDS = {
        "alice": "Alice-pass-0001-xyz",   # acme admin
        "bob": "Bob-pass-0002-xyz",       # acme member
        "carol": "Carol-pass-0003-xyz",   # globex admin
    }

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="docket-hidden-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.data_dir = os.path.join(self.tmp, "data")
        os.makedirs(self.data_dir)
        self.db_path = os.path.join(self.data_dir, "docket.db")
        self.clock = FakeClock()
        self.http = FakeHTTP()
        self.resolver = FakeResolver({"hooks.example.com": [PUBLIC_IP]})
        from docket import admin
        self.admin = admin
        admin.migrate(self.db_path)
        admin.create_tenant(self.db_path, "acme")
        admin.create_tenant(self.db_path, "globex")
        admin.create_user(self.db_path, "acme", "alice", self.PASSWORDS["alice"], admin=True)
        admin.create_user(self.db_path, "acme", "bob", self.PASSWORDS["bob"])
        admin.create_user(self.db_path, "globex", "carol", self.PASSWORDS["carol"], admin=True)
        from docket.app import create_app
        self.app = create_app(self.db_path, clock=self.clock, http_post=self.http,
                              resolve=self.resolver)
        self.addCleanup(self._stop_worker)

    def _stop_worker(self):
        stop = getattr(self.app, "stop_worker", None)
        if callable(stop):
            try:
                stop()
            except Exception:
                pass

    # -- thin client -------------------------------------------------------
    def req(self, method, path, **kw):
        return call_wsgi(self.app, method, path, **kw)

    def login(self, username, password=None, tenant=None):
        tenant = tenant or ("globex" if username == "carol" else "acme")
        password = password if password is not None else self.PASSWORDS[username]
        return self.req("POST", "/login",
                        json_body={"tenant": tenant, "username": username, "password": password})

    def token(self, username):
        r = self.login(username)
        self.assertEqual(r.status, 200, f"login for {username} failed: {r!r}")
        tok = r.json().get("token")
        self.assertTrue(isinstance(tok, str) and tok, f"no token in {r!r}")
        return tok

    def upload(self, token, filename, content):
        r = self.req("POST", "/documents", query={"filename": filename}, body=content, token=token)
        return r

    def upload_ok(self, token, filename, content):
        r = self.upload(token, filename, content)
        self.assertEqual(r.status, 201, f"upload of {filename!r} failed: {r!r}")
        doc = r.json()
        self.assertIsInstance(doc.get("id"), str)
        return doc

    def set_webhook(self, token, url):
        return self.req("PUT", "/tenant/webhook", json_body={"url": url}, token=token)

    def list_docs(self, token, q=None):
        r = self.req("GET", "/documents", query={"q": q} if q is not None else None, token=token)
        return r
