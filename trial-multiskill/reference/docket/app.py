"""Docket WSGI application."""
import csv
import datetime
import hashlib
import http
import io
import json
import logging
import os
import re
import secrets
import threading
import time
import unicodedata
import uuid
from urllib.parse import parse_qs, quote

from . import db, security, webhooks

activity = logging.getLogger("docket.activity")
errors = logging.getLogger("docket.error")

# Limits and timeouts. The ticket names none of these; each is a deliberate default.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_JSON_BYTES = 64 * 1024
MAX_FILENAME_CHARS = 255
MAX_QUERY_CHARS = 200
SESSION_IDLE_SECONDS = 30 * 60
SESSION_ABSOLUTE_SECONDS = 12 * 3600
LOGIN_MAX_FAILURES = 10
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_LOCK_SECONDS = 15 * 60
WEBHOOK_FIRST_RETRY_SECONDS = 30
WEBHOOK_MAX_INTERVAL_SECONDS = 3600
WEBHOOK_MAX_ATTEMPTS = 8
WEBHOOK_LEASE_SECONDS = 300
WEBHOOK_BATCH = 100

_ID = r"[A-Za-z0-9_-]{1,64}"
_CSV_DANGEROUS_LEAD = ("=", "+", "-", "@", "\t", "\r", "\0")


class HTTPError(Exception):
    def __init__(self, status, message, headers=()):
        super().__init__(message)
        self.status = status
        self.message = message
        self.headers = list(headers)


class Principal:
    __slots__ = ("user_id", "username", "role", "tenant_id", "tenant_name", "token_digest")

    def __init__(self, row, token_digest):
        self.user_id = row["user_id"]
        self.username = row["username"]
        self.role = row["role"]
        self.tenant_id = row["tenant_id"]
        self.tenant_name = row["tenant_name"]
        self.token_digest = token_digest


def log_event(action, level=logging.INFO, **fields):
    """One JSON object per record: field values are JSON-encoded, so CR/LF in a
    user-supplied value cannot forge a second log line. Never pass secrets here."""
    activity.log(level, json.dumps({"action": action, **fields}, sort_keys=True, default=str))


def iso_utc(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def sanitize_filename(name):
    """Display name only (storage uses generated ids). Drops control/format
    characters, replaces path separators, bounds the length."""
    name = unicodedata.normalize("NFC", name)
    name = "".join(ch for ch in name if not unicodedata.category(ch).startswith("C"))
    name = name.replace("/", "_").replace("\\", "_").strip()
    name = name[:MAX_FILENAME_CHARS]
    if name in ("", ".", ".."):
        return None
    return name


def content_disposition(filename):
    """RFC 6266: an ASCII fallback plus an RFC 8187 encoded filename*."""
    fallback = "".join(ch if (ch.isascii() and (ch.isalnum() or ch in " ._-()[]+,")) else "_"
                       for ch in filename) or "download"
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename, safe='')}"


def neutralise_csv_cell(value):
    text = "" if value is None else str(value)
    if text.startswith(_CSV_DANGEROUS_LEAD):
        return "'" + text
    return text


class DocketApp:
    def __init__(self, db_path, *, clock, http_post, resolve):
        self.db_path = db_path
        self.clock = clock
        self.http_post = http_post
        self.resolve = resolve
        self.files_dir = os.path.join(os.path.dirname(os.path.abspath(db_path)), "files")
        os.makedirs(self.files_dir, mode=0o700, exist_ok=True)
        db.migrate(db_path)
        self._worker = None
        self._stop = threading.Event()
        self._routes = [
            (re.compile(r"^/login$"), {"POST": self.login}, False),
            (re.compile(r"^/logout$"), {"POST": self.logout}, True),
            (re.compile(r"^/password$"), {"POST": self.change_password}, True),
            (re.compile(r"^/documents$"), {"GET": self.list_documents, "POST": self.upload}, True),
            (re.compile(rf"^/documents/({_ID})$"), {"GET": self.download}, True),
            (re.compile(rf"^/documents/({_ID})/share$"), {"POST": self.share}, True),
            (re.compile(rf"^/shares/({_ID})$"), {"GET": self.open_share}, True),
            (re.compile(r"^/tenant/webhook$"), {"PUT": self.set_webhook}, True),
            (re.compile(r"^/tenant/export\.csv$"), {"GET": self.export_csv}, True),
        ]

    # ------------------------------------------------------------------ WSGI
    def __call__(self, environ, start_response):
        try:
            status, headers, body = self._dispatch(environ)
        except HTTPError as err:
            status, headers, body = self._json(err.status, {"error": err.message}, err.headers)
        except Exception:
            # Last-resort handler: full detail to the server log, generic text to the client.
            errors.exception("unhandled error on %r %r", environ.get("REQUEST_METHOD"),
                             environ.get("PATH_INFO"))
            status, headers, body = self._json(500, {"error": "internal error"})
        headers = headers + [("X-Content-Type-Options", "nosniff"), ("Cache-Control", "no-store")]
        if body:
            headers.append(("Content-Length", str(len(body))))
        start_response(f"{status} {http.HTTPStatus(status).phrase}", headers)
        return [body]

    def _dispatch(self, environ):
        path = environ.get("PATH_INFO", "") or "/"
        method = environ.get("REQUEST_METHOD", "GET").upper()
        for pattern, handlers, needs_auth in self._routes:
            m = pattern.match(path)
            if not m:
                continue
            handler = handlers.get(method)
            if handler is None:
                raise HTTPError(405, "method not allowed", [("Allow", ", ".join(sorted(handlers)))])
            conn = db.connect(self.db_path)
            try:
                if needs_auth:
                    principal = self._authenticate(conn, environ)
                    return handler(conn, environ, principal, *m.groups())
                return handler(conn, environ, *m.groups())
            finally:
                conn.close()
        raise HTTPError(404, "not found")

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _json(status, payload, headers=()):
        body = json.dumps(payload).encode("utf-8") if payload is not None else b""
        hdrs = list(headers)
        if body:
            hdrs.append(("Content-Type", "application/json; charset=utf-8"))
        return status, hdrs, body

    @staticmethod
    def _content_length(environ, limit):
        raw = environ.get("CONTENT_LENGTH") or ""
        if raw.strip() == "":
            return None
        try:
            n = int(raw)
        except ValueError:
            raise HTTPError(400, "invalid Content-Length") from None
        if n < 0:
            raise HTTPError(400, "invalid Content-Length")
        if n > limit:
            raise HTTPError(413, "request body too large")
        return n

    def _read_json(self, environ):
        n = self._content_length(environ, MAX_JSON_BYTES)
        raw = environ["wsgi.input"].read(n) if n else b""
        if n and len(raw) != n:
            raise HTTPError(400, "incomplete request body")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise HTTPError(400, "request body must be a JSON object") from None
        if not isinstance(data, dict):
            raise HTTPError(400, "request body must be a JSON object")
        return data

    @staticmethod
    def _require_str(data, key, max_len=1024):
        value = data.get(key)
        if not isinstance(value, str) or not value or len(value) > max_len:
            raise HTTPError(400, f"'{key}' must be a non-empty string")
        return value

    @staticmethod
    def _query(environ):
        return parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)

    @staticmethod
    def _client(environ):
        return environ.get("REMOTE_ADDR", "")

    def _authenticate(self, conn, environ):
        header = environ.get("HTTP_AUTHORIZATION", "")
        scheme, _, token = header.partition(" ")
        token = token.strip()
        unauthorized = HTTPError(401, "authentication required", [("WWW-Authenticate", "Bearer")])
        if scheme.lower() != "bearer" or not token or len(token) > 512:
            raise unauthorized
        digest = security.token_digest(token)
        row = conn.execute(
            "SELECT s.created_at, s.last_seen_at, u.id AS user_id, u.username, u.role,"
            " u.tenant_id, t.name AS tenant_name"
            " FROM sessions s JOIN users u ON u.id = s.user_id JOIN tenants t ON t.id = u.tenant_id"
            " WHERE s.token_hash = ?", (digest,)).fetchone()
        if row is None:
            raise unauthorized
        now = self.clock()
        if now - row["last_seen_at"] > SESSION_IDLE_SECONDS or now - row["created_at"] > SESSION_ABSOLUTE_SECONDS:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (digest,))
            raise unauthorized
        conn.execute("UPDATE sessions SET last_seen_at = ? WHERE token_hash = ?", (now, digest))
        return Principal(row, digest)

    def _require_admin(self, principal, action):
        if principal.role != "admin":
            log_event("authz.denied", logging.WARNING, tenant=principal.tenant_name,
                      username=principal.username, attempted=action)
            raise HTTPError(403, "tenant admin role required")

    # -------------------------------------------------------------- auth
    def login(self, conn, environ):
        data = self._read_json(environ)
        tenant = self._require_str(data, "tenant", 64)
        username = self._require_str(data, "username", 64)
        password = self._require_str(data, "password", security.MAX_PASSWORD_LENGTH)
        now = self.clock()
        client = self._client(environ)
        throttle = conn.execute("SELECT locked_until FROM login_throttle WHERE tenant_name = ? AND username = ?",
                                (tenant, username)).fetchone()
        if throttle and throttle["locked_until"] and throttle["locked_until"] > now:
            log_event("login.throttled", logging.WARNING, tenant=tenant, username=username, client=client)
            retry_after = str(int(throttle["locked_until"] - now) + 1)
            raise HTTPError(429, "too many failed login attempts; try again later", [("Retry-After", retry_after)])
        user = conn.execute(
            "SELECT u.id, u.username, u.role, u.password_hash FROM users u JOIN tenants t ON t.id = u.tenant_id"
            " WHERE t.name = ? AND u.username = ?", (tenant, username)).fetchone()
        stored = user["password_hash"] if user else security.dummy_hash()
        if not security.verify_password(password, stored) or user is None:
            self._record_login_failure(conn, tenant, username, now)
            log_event("login.failed", logging.WARNING, tenant=tenant, username=username, client=client)
            raise HTTPError(401, "invalid credentials")
        conn.execute("DELETE FROM login_throttle WHERE tenant_name = ? AND username = ?", (tenant, username))
        token = security.new_session_token()
        conn.execute("INSERT INTO sessions (token_hash, user_id, created_at, last_seen_at) VALUES (?, ?, ?, ?)",
                     (security.token_digest(token), user["id"], now, now))
        log_event("login.succeeded", tenant=tenant, username=username, client=client)
        return self._json(200, {"token": token, "username": user["username"], "role": user["role"]})

    def _record_login_failure(self, conn, tenant, username, now):
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT failures, window_start FROM login_throttle"
                               " WHERE tenant_name = ? AND username = ?", (tenant, username)).fetchone()
            if row is None or now - row["window_start"] > LOGIN_WINDOW_SECONDS:
                failures, window_start = 1, now
            else:
                failures, window_start = row["failures"] + 1, row["window_start"]
            locked_until = None
            if failures >= LOGIN_MAX_FAILURES:
                locked_until = now + LOGIN_LOCK_SECONDS
                failures, window_start = 0, now
                log_event("login.locked", logging.WARNING, tenant=tenant, username=username,
                          seconds=LOGIN_LOCK_SECONDS)
            conn.execute(
                "INSERT INTO login_throttle (tenant_name, username, failures, window_start, locked_until)"
                " VALUES (?, ?, ?, ?, ?) ON CONFLICT (tenant_name, username) DO UPDATE SET"
                " failures = excluded.failures, window_start = excluded.window_start,"
                " locked_until = excluded.locked_until",
                (tenant, username, failures, window_start, locked_until))
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise

    def logout(self, conn, environ, principal):
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (principal.token_digest,))
        log_event("logout", tenant=principal.tenant_name, username=principal.username)
        return 204, [], b""

    def change_password(self, conn, environ, principal):
        data = self._read_json(environ)
        old = self._require_str(data, "old_password", security.MAX_PASSWORD_LENGTH)
        new = data.get("new_password")
        problem = security.password_problem(new)
        if problem:
            raise HTTPError(400, problem)
        row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (principal.user_id,)).fetchone()
        if not security.verify_password(old, row["password_hash"]):
            log_event("password.change_failed", logging.WARNING, tenant=principal.tenant_name,
                      username=principal.username)
            raise HTTPError(403, "current password is wrong")
        new_hash = security.hash_password(new)
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute("UPDATE users SET password_hash = ?, password_changed_at = ? WHERE id = ?",
                         (new_hash, iso_utc(self.clock()), principal.user_id))
            # End every other session of this user (ASVS V7.4.3); keep the caller's.
            conn.execute("DELETE FROM sessions WHERE user_id = ? AND token_hash != ?",
                         (principal.user_id, principal.token_digest))
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        log_event("password.changed", tenant=principal.tenant_name, username=principal.username)
        return 204, [], b""

    # --------------------------------------------------------- documents
    def upload(self, conn, environ, principal):
        names = self._query(environ).get("filename")
        if not names or not names[0]:
            raise HTTPError(400, "filename query parameter is required")
        filename = sanitize_filename(names[0])
        if filename is None:
            raise HTTPError(400, "invalid filename")
        length = self._content_length(environ, MAX_UPLOAD_BYTES)
        if length is None:
            raise HTTPError(411, "Content-Length required")
        doc_id = uuid.uuid4().hex
        final_path = os.path.join(self.files_dir, doc_id)
        tmp_path = final_path + ".part"
        digest = hashlib.sha256()
        stream = environ["wsgi.input"]
        try:
            fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as fh:
                remaining = length
                while remaining:
                    chunk = stream.read(min(65536, remaining))
                    if not chunk:
                        raise HTTPError(400, "incomplete request body")
                    fh.write(chunk)
                    digest.update(chunk)
                    remaining -= len(chunk)
            os.replace(tmp_path, final_path)
            now = self.clock()
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO documents (id, tenant_id, filename, size, sha256, uploaded_by, uploaded_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (doc_id, principal.tenant_id, filename, length, digest.hexdigest(),
                     principal.user_id, iso_utc(now)))
                tenant = conn.execute("SELECT webhook_url FROM tenants WHERE id = ?",
                                      (principal.tenant_id,)).fetchone()
                if tenant["webhook_url"]:
                    event_id = "evt_" + secrets.token_hex(16)
                    body = json.dumps({
                        "event": "document.uploaded", "tenant": principal.tenant_name,
                        "document": {"id": doc_id, "filename": filename, "size": length,
                                     "uploaded_by": principal.username}}).encode("utf-8")
                    conn.execute(
                        "INSERT INTO webhook_deliveries (event_id, tenant_id, url, body, status,"
                        " next_attempt_at, created_at) VALUES (?, ?, ?, ?, 'pending', ?, ?)",
                        (event_id, principal.tenant_id, tenant["webhook_url"], body, now, now))
                conn.execute("COMMIT")
            except BaseException:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
        except BaseException:
            for p in (tmp_path, final_path):
                try:
                    os.remove(p)
                except FileNotFoundError:
                    pass
            raise
        log_event("document.uploaded", tenant=principal.tenant_name, username=principal.username,
                  document_id=doc_id, filename=filename, size=length)
        return self._json(201, {"id": doc_id, "filename": filename, "size": length})

    def list_documents(self, conn, environ, principal):
        sql = ("SELECT d.id, d.filename, d.size, u.username AS uploaded_by, d.uploaded_at"
               " FROM documents d JOIN users u ON u.id = d.uploaded_by WHERE d.tenant_id = ?")
        params = [principal.tenant_id]
        q = self._query(environ).get("q")
        if q and q[0]:
            if len(q[0]) > MAX_QUERY_CHARS:
                raise HTTPError(400, "search text too long")
            escaped = q[0].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            sql += " AND d.filename LIKE ? ESCAPE '\\'"
            params.append(f"%{escaped}%")
        sql += " ORDER BY d.rowid"
        docs = [dict(r) for r in conn.execute(sql, params)]
        return self._json(200, {"documents": docs})

    def _tenant_document(self, conn, principal, doc_id, action):
        row = conn.execute("SELECT id, filename FROM documents WHERE id = ? AND tenant_id = ?",
                           (doc_id, principal.tenant_id)).fetchone()
        if row is None:
            if conn.execute("SELECT 1 FROM documents WHERE id = ?", (doc_id,)).fetchone():
                log_event("authz.denied", logging.WARNING, tenant=principal.tenant_name,
                          username=principal.username, attempted=action, document_id=doc_id)
            raise HTTPError(404, "document not found")  # same answer as "does not exist"
        return row

    def _send_file(self, row):
        try:
            with open(os.path.join(self.files_dir, row["id"]), "rb") as fh:
                data = fh.read()
        except FileNotFoundError:
            errors.error("stored contents missing for document %s", row["id"])
            raise HTTPError(500, "internal error") from None
        return 200, [("Content-Type", "application/octet-stream"),
                     ("Content-Disposition", content_disposition(row["filename"]))], data

    def download(self, conn, environ, principal, doc_id):
        row = self._tenant_document(conn, principal, doc_id, "document.download")
        log_event("document.downloaded", tenant=principal.tenant_name, username=principal.username,
                  document_id=doc_id)
        return self._send_file(row)

    def share(self, conn, environ, principal, doc_id):
        self._tenant_document(conn, principal, doc_id, "document.share")
        share_id = secrets.token_urlsafe(24)
        conn.execute("INSERT INTO shares (id, document_id, tenant_id, created_by, created_at)"
                     " VALUES (?, ?, ?, ?, ?)",
                     (share_id, doc_id, principal.tenant_id, principal.user_id, iso_utc(self.clock())))
        log_event("share.created", tenant=principal.tenant_name, username=principal.username,
                  document_id=doc_id)
        return self._json(201, {"share_id": share_id, "url": f"/shares/{share_id}"})

    def open_share(self, conn, environ, principal, share_id):
        row = conn.execute(
            "SELECT d.id, d.filename FROM shares s JOIN documents d ON d.id = s.document_id"
            " WHERE s.id = ? AND s.tenant_id = ? AND d.tenant_id = ?",
            (share_id, principal.tenant_id, principal.tenant_id)).fetchone()
        if row is None:
            if conn.execute("SELECT 1 FROM shares WHERE id = ?", (share_id,)).fetchone():
                log_event("authz.denied", logging.WARNING, tenant=principal.tenant_name,
                          username=principal.username, attempted="share.open")
            raise HTTPError(404, "share not found")
        log_event("share.opened", tenant=principal.tenant_name, username=principal.username,
                  document_id=row["id"])
        return self._send_file(row)

    # ----------------------------------------------------------- tenant admin
    def set_webhook(self, conn, environ, principal):
        self._require_admin(principal, "tenant.webhook")
        data = self._read_json(environ)
        if "url" not in data:
            raise HTTPError(400, "'url' is required")
        url = data["url"]
        if url is not None:
            if not isinstance(url, str):
                raise HTTPError(400, "'url' must be a string or null")
            problem = webhooks.destination_problem(url, self.resolve)
            if problem:
                log_event("webhook.rejected", logging.WARNING, tenant=principal.tenant_name,
                          username=principal.username, reason=problem)
                raise HTTPError(400, f"webhook URL not allowed: {problem}")
        conn.execute("UPDATE tenants SET webhook_url = ? WHERE id = ?", (url, principal.tenant_id))
        # Log the destination host only: a URL's path or query may carry a receiver secret.
        host = None
        if url:
            from urllib.parse import urlsplit
            host = urlsplit(url).hostname
        log_event("webhook.updated", tenant=principal.tenant_name, username=principal.username,
                  host=host, cleared=url is None)
        return 204, [], b""

    def export_csv(self, conn, environ, principal):
        self._require_admin(principal, "tenant.export")
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\r\n")  # RFC 4180 quoting and line ends
        writer.writerow(["id", "filename", "size", "uploaded_by", "uploaded_at"])
        rows = conn.execute(
            "SELECT d.id, d.filename, d.size, u.username, d.uploaded_at FROM documents d"
            " JOIN users u ON u.id = d.uploaded_by WHERE d.tenant_id = ? ORDER BY d.rowid",
            (principal.tenant_id,))
        count = 0
        for r in rows:
            writer.writerow([neutralise_csv_cell(v) for v in r])
            count += 1
        log_event("tenant.exported", tenant=principal.tenant_name, username=principal.username, rows=count)
        return 200, [("Content-Type", "text/csv; charset=utf-8"),
                     ("Content-Disposition", 'attachment; filename="docket-export.csv"')], out.getvalue().encode("utf-8")

    # ------------------------------------------------------------- webhooks
    def run_pending_deliveries(self):
        """Attempt every delivery due now. Each attempt is claimed with a
        conditional UPDATE (a lease), so two workers never send the same attempt;
        a worker that dies mid-send is retried once the lease expires."""
        conn = db.connect(self.db_path)
        posts = 0
        try:
            now = self.clock()
            due = [r[0] for r in conn.execute(
                "SELECT id FROM webhook_deliveries WHERE (status = 'pending' AND next_attempt_at <= ?)"
                " OR (status = 'sending' AND lease_until <= ?) ORDER BY id LIMIT ?",
                (now, now, WEBHOOK_BATCH))]
            for delivery_id in due:
                claimed = conn.execute(
                    "UPDATE webhook_deliveries SET status = 'sending', lease_until = ?, attempts = attempts + 1"
                    " WHERE id = ? AND ((status = 'pending' AND next_attempt_at <= ?)"
                    " OR (status = 'sending' AND lease_until <= ?))",
                    (now + WEBHOOK_LEASE_SECONDS, delivery_id, now, now)).rowcount
                if claimed != 1:
                    continue
                row = conn.execute("SELECT * FROM webhook_deliveries WHERE id = ?", (delivery_id,)).fetchone()
                problem = webhooks.destination_problem(row["url"], self.resolve)
                if problem:
                    conn.execute("UPDATE webhook_deliveries SET status = 'failed', lease_until = NULL,"
                                 " last_error = ? WHERE id = ?", (problem, delivery_id))
                    log_event("webhook.blocked", logging.WARNING, event_id=row["event_id"], reason=problem)
                    continue
                headers = {"Content-Type": "application/json", "User-Agent": "Docket-Webhooks/1",
                           "Webhook-Id": row["event_id"],
                           "Webhook-Timestamp": str(int(row["created_at"]))}
                posts += 1
                status, error = None, None
                try:
                    status = int(self.http_post(row["url"], bytes(row["body"]), headers))
                except Exception as exc:  # network failure: retry per policy
                    error = type(exc).__name__
                after = self.clock()
                if status is not None and 200 <= status < 300:
                    conn.execute("UPDATE webhook_deliveries SET status = 'delivered', lease_until = NULL,"
                                 " last_status = ? WHERE id = ?", (status, delivery_id))
                    log_event("webhook.delivered", event_id=row["event_id"], attempt=row["attempts"])
                elif row["attempts"] >= WEBHOOK_MAX_ATTEMPTS:
                    conn.execute("UPDATE webhook_deliveries SET status = 'failed', lease_until = NULL,"
                                 " last_status = ?, last_error = ? WHERE id = ?", (status, error, delivery_id))
                    log_event("webhook.gave_up", logging.WARNING, event_id=row["event_id"],
                              attempts=row["attempts"], last_status=status, error=error)
                else:
                    delay = min(WEBHOOK_FIRST_RETRY_SECONDS * 2 ** (row["attempts"] - 1),
                                WEBHOOK_MAX_INTERVAL_SECONDS)
                    conn.execute("UPDATE webhook_deliveries SET status = 'pending', lease_until = NULL,"
                                 " next_attempt_at = ?, last_status = ?, last_error = ? WHERE id = ?",
                                 (after + delay, status, error, delivery_id))
                    log_event("webhook.retry_scheduled", event_id=row["event_id"], attempt=row["attempts"],
                              delay=delay, last_status=status, error=error)
        finally:
            conn.close()
        return posts

    def start_worker(self, interval=1.0):
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop.clear()

        def loop():
            while not self._stop.is_set():
                try:
                    self.run_pending_deliveries()
                except Exception:
                    errors.exception("webhook worker iteration failed")
                self._stop.wait(interval)
        self._worker = threading.Thread(target=loop, name="docket-webhooks", daemon=True)
        self._worker.start()

    def stop_worker(self, timeout=30.0):
        self._stop.set()
        if self._worker is not None:
            self._worker.join(timeout)
            self._worker = None


def create_app(db_path, *, clock=time.time, http_post=webhooks.default_http_post,
               resolve=webhooks.default_resolve):
    return DocketApp(db_path, clock=clock, http_post=http_post, resolve=resolve)
