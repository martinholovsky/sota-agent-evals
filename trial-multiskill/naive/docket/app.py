import base64
import csv
import datetime
import hashlib
import hmac
import io
import json
import logging
import os
import re
import secrets
import socket
import threading
import time
import urllib.request
from urllib.parse import parse_qs

from . import db

log = logging.getLogger("docket.activity")


def default_http_post(url, body, headers):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return resp.status


def default_resolve(host):
    return [info[4][0] for info in socket.getaddrinfo(host, None)]


class App:
    def __init__(self, db_path, clock, http_post, resolve):
        self.db_path = db_path
        self.clock = clock
        self.http_post = http_post
        self.resolve = resolve
        self.files_dir = os.path.join(os.path.dirname(os.path.abspath(db_path)), "files")
        os.makedirs(self.files_dir, exist_ok=True)
        db.migrate(db_path)
        conn = db.connect(db_path)
        row = conn.execute("SELECT value FROM settings WHERE key = 'secret'").fetchone()
        if row is None:
            self.secret = secrets.token_hex(32)
            conn.execute("INSERT INTO settings (key, value) VALUES ('secret', ?)", (self.secret,))
            conn.commit()
        else:
            self.secret = row["value"]
        conn.close()
        self.worker = None
        self.running = False

    # --- helpers ---
    def response(self, start_response, status, data=None, content_type="application/json", headers=None):
        names = {200: "OK", 201: "Created", 204: "No Content", 400: "Bad Request", 401: "Unauthorized",
                 403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed"}
        if data is None:
            body = b""
        elif isinstance(data, bytes):
            body = data
        else:
            body = json.dumps(data).encode()
        h = [("Content-Type", content_type)] + (headers or [])
        start_response(f"{status} {names[status]}", h)
        return [body]

    def error(self, start_response, status, message):
        return self.response(start_response, status, {"error": message})

    def read_body(self, environ):
        length = int(environ.get("CONTENT_LENGTH") or 0)
        return environ["wsgi.input"].read(length)

    def make_token(self, tenant_id, user_id):
        payload = f"{tenant_id}:{user_id}"
        sig = hmac.new(self.secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return base64.urlsafe_b64encode(payload.encode()).decode() + "." + sig

    def current_user(self, environ, conn):
        auth = environ.get("HTTP_AUTHORIZATION", "")
        if not auth.startswith("Bearer "):
            return None
        try:
            payload_b64, sig = auth[7:].split(".")
            payload = base64.urlsafe_b64decode(payload_b64).decode()
        except Exception:
            return None
        expected = hmac.new(self.secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        tenant_id, user_id = payload.split(":")
        return conn.execute(
            "SELECT users.*, tenants.name AS tenant_name FROM users JOIN tenants ON tenants.id = users.tenant_id"
            " WHERE users.id = ?", (int(user_id),)).fetchone()

    def now_iso(self):
        return datetime.datetime.fromtimestamp(self.clock(), datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # --- WSGI ---
    def __call__(self, environ, start_response):
        method = environ["REQUEST_METHOD"]
        path = environ.get("PATH_INFO", "")
        conn = db.connect(self.db_path)
        try:
            return self.route(environ, start_response, method, path, conn)
        finally:
            conn.close()

    def route(self, environ, start_response, method, path, conn):
        if path == "/login":
            if method != "POST":
                return self.error(start_response, 405, "method not allowed")
            return self.login(environ, start_response, conn)
        routes = [
            (r"^/logout$", {"POST": self.logout}),
            (r"^/password$", {"POST": self.change_password}),
            (r"^/documents$", {"GET": self.list_documents, "POST": self.upload}),
            (r"^/documents/([^/]+)$", {"GET": self.download}),
            (r"^/documents/([^/]+)/share$", {"POST": self.share}),
            (r"^/shares/([^/]+)$", {"GET": self.open_share}),
            (r"^/tenant/webhook$", {"PUT": self.set_webhook}),
            (r"^/tenant/export\.csv$", {"GET": self.export}),
        ]
        for pattern, handlers in routes:
            m = re.match(pattern, path)
            if m:
                if method not in handlers:
                    return self.error(start_response, 405, "method not allowed")
                user = self.current_user(environ, conn)
                if user is None:
                    return self.error(start_response, 401, "unauthorized")
                return handlers[method](environ, start_response, conn, user, *m.groups())
        return self.error(start_response, 404, "not found")

    # --- handlers ---
    def login(self, environ, start_response, conn):
        data = json.loads(self.read_body(environ))
        pw = hashlib.sha256(data["password"].encode()).hexdigest()
        user = conn.execute(
            "SELECT users.* FROM users JOIN tenants ON tenants.id = users.tenant_id"
            " WHERE tenants.name = ? AND users.username = ? AND users.password = ?",
            (data["tenant"], data["username"], pw)).fetchone()
        if user is None:
            return self.error(start_response, 401, "invalid username or password")
        log.info("user %s logged in to %s", user["username"], data["tenant"])
        return self.response(start_response, 200, {"token": self.make_token(user["tenant_id"], user["id"]),
                                                   "username": user["username"], "role": user["role"]})

    def logout(self, environ, start_response, conn, user):
        log.info("user %s logged out", user["username"])
        return self.response(start_response, 204)

    def change_password(self, environ, start_response, conn, user):
        data = json.loads(self.read_body(environ))
        if hashlib.sha256(data["old_password"].encode()).hexdigest() != user["password"]:
            return self.error(start_response, 403, "wrong password")
        conn.execute("UPDATE users SET password = ? WHERE id = ?",
                     (hashlib.sha256(data["new_password"].encode()).hexdigest(), user["id"]))
        conn.commit()
        log.info("user %s changed password", user["username"])
        return self.response(start_response, 204)

    def upload(self, environ, start_response, conn, user):
        qs = parse_qs(environ.get("QUERY_STRING", ""))
        if "filename" not in qs:
            return self.error(start_response, 400, "filename is required")
        filename = qs["filename"][0]
        content = self.read_body(environ)
        tenant_dir = os.path.join(self.files_dir, str(user["tenant_id"]))
        os.makedirs(tenant_dir, exist_ok=True)
        with open(os.path.join(tenant_dir, filename), "wb") as f:
            f.write(content)
        cur = conn.execute(
            "INSERT INTO documents (tenant_id, filename, size, uploaded_by, uploaded_at) VALUES (?, ?, ?, ?, ?)",
            (user["tenant_id"], filename, len(content), user["username"], self.now_iso()))
        doc_id = str(cur.lastrowid)
        tenant = conn.execute("SELECT * FROM tenants WHERE id = ?", (user["tenant_id"],)).fetchone()
        if tenant["webhook_url"]:
            body = json.dumps({"event": "document.uploaded", "tenant": tenant["name"],
                               "document": {"id": doc_id, "filename": filename, "size": len(content),
                                            "uploaded_by": user["username"]}})
            conn.execute("INSERT INTO webhook_queue (url, body, next_try) VALUES (?, ?, ?)",
                         (tenant["webhook_url"], body, self.clock()))
        conn.commit()
        log.info("user %s uploaded %s", user["username"], filename)
        return self.response(start_response, 201, {"id": doc_id, "filename": filename, "size": len(content)})

    def list_documents(self, environ, start_response, conn, user):
        qs = parse_qs(environ.get("QUERY_STRING", ""))
        sql = f"SELECT * FROM documents WHERE tenant_id = {user['tenant_id']}"
        if "q" in qs:
            sql += f" AND filename LIKE '%{qs['q'][0]}%'"
        docs = [{"id": str(r["id"]), "filename": r["filename"], "size": r["size"],
                 "uploaded_by": r["uploaded_by"], "uploaded_at": r["uploaded_at"]}
                for r in conn.execute(sql + " ORDER BY id")]
        return self.response(start_response, 200, {"documents": docs})

    def send_document(self, start_response, doc):
        with open(os.path.join(self.files_dir, str(doc["tenant_id"]), doc["filename"]), "rb") as f:
            content = f.read()
        return self.response(start_response, 200, content, "application/octet-stream",
                             [("Content-Disposition", f'attachment; filename="{doc["filename"]}"')])

    def download(self, environ, start_response, conn, user, doc_id):
        doc = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if doc is None:
            return self.error(start_response, 404, "document not found")
        return self.send_document(start_response, doc)

    def share(self, environ, start_response, conn, user, doc_id):
        doc = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if doc is None:
            return self.error(start_response, 404, "document not found")
        cur = conn.execute("INSERT INTO shares (document_id) VALUES (?)", (doc["id"],))
        conn.commit()
        share_id = str(cur.lastrowid)
        log.info("user %s shared document %s", user["username"], doc_id)
        return self.response(start_response, 201, {"share_id": share_id, "url": f"/shares/{share_id}"})

    def open_share(self, environ, start_response, conn, user, share_id):
        doc = conn.execute("SELECT documents.* FROM shares JOIN documents ON documents.id = shares.document_id"
                           " WHERE shares.id = ?", (share_id,)).fetchone()
        if doc is None:
            return self.error(start_response, 404, "share not found")
        return self.send_document(start_response, doc)

    def set_webhook(self, environ, start_response, conn, user):
        if user["role"] != "admin":
            return self.error(start_response, 403, "admins only")
        data = json.loads(self.read_body(environ))
        conn.execute("UPDATE tenants SET webhook_url = ? WHERE id = ?", (data["url"], user["tenant_id"]))
        conn.commit()
        log.info("user %s set webhook to %s", user["username"], data["url"])
        return self.response(start_response, 204)

    def export(self, environ, start_response, conn, user):
        if user["role"] != "admin":
            return self.error(start_response, 403, "admins only")
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["id", "filename", "size", "uploaded_by", "uploaded_at"])
        for r in conn.execute("SELECT * FROM documents WHERE tenant_id = ? ORDER BY id", (user["tenant_id"],)):
            w.writerow([r["id"], r["filename"], r["size"], r["uploaded_by"], r["uploaded_at"]])
        log.info("user %s exported documents", user["username"])
        return self.response(start_response, 200, out.getvalue().encode(), "text/csv")

    # --- webhooks ---
    def run_pending_deliveries(self):
        conn = db.connect(self.db_path)
        rows = conn.execute("SELECT * FROM webhook_queue WHERE done = 0 AND next_try <= ?",
                            (self.clock(),)).fetchall()
        count = 0
        for row in rows:
            count += 1
            try:
                status = self.http_post(row["url"], row["body"].encode(), {"Content-Type": "application/json"})
            except Exception:
                status = 0
            if 200 <= status < 300:
                conn.execute("UPDATE webhook_queue SET done = 1 WHERE id = ?", (row["id"],))
            else:
                attempts = row["attempts"] + 1
                wait = min(30 * 2 ** (attempts - 1), 3600)
                conn.execute("UPDATE webhook_queue SET attempts = ?, next_try = ? WHERE id = ?",
                             (attempts, self.clock() + wait, row["id"]))
            conn.commit()
        conn.close()
        return count

    def start_worker(self, interval=1.0):
        self.running = True

        def loop():
            while self.running:
                self.run_pending_deliveries()
                time.sleep(interval)
        self.worker = threading.Thread(target=loop, daemon=True)
        self.worker.start()

    def stop_worker(self):
        self.running = False


def create_app(db_path, *, clock=time.time, http_post=default_http_post, resolve=default_resolve):
    return App(db_path, clock, http_post, resolve)
