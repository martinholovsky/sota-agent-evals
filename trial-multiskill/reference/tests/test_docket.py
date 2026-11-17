"""Docket's own tests: behaviour from the ticket plus the controls we added.

In-process WSGI calls with an injected clock, http_post and resolve; no network.
"""
import csv
import io
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from wsgiref.util import setup_testing_defaults

from docket import admin, app as appmod, security, webhooks
from docket.app import create_app

ROOT = Path(__file__).resolve().parent.parent
logging.getLogger("docket").addHandler(logging.NullHandler())
logging.getLogger("docket").propagate = False


class Clock:
    def __init__(self):
        self.t = 1_700_000_000.0

    def __call__(self):
        return self.t


def call(app, method, path, *, body=b"", token=None, query="", content_length=None):
    env = {}
    setup_testing_defaults(env)
    env.update(REQUEST_METHOD=method, PATH_INFO=path, QUERY_STRING=query,
               CONTENT_LENGTH=str(len(body) if content_length is None else content_length))
    env["wsgi.input"] = io.BytesIO(body)
    if token:
        env["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    seen = {}

    def start_response(status, headers, exc_info=None):
        seen["status"] = int(status.split()[0])
        seen["headers"] = dict(headers)
    data = b"".join(app(env, start_response))
    return seen["status"], seen["headers"], data


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Cheap hashing for speed; one test below checks the production setting.
        cls._iters = security.PBKDF2_ITERATIONS
        security.PBKDF2_ITERATIONS = 1000
        security.hash_password.__kwdefaults__["iterations"] = 1000

    @classmethod
    def tearDownClass(cls):
        security.PBKDF2_ITERATIONS = cls._iters
        security.hash_password.__kwdefaults__["iterations"] = cls._iters

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.db = os.path.join(self.dir, "docket.db")
        admin.create_tenant(self.db, "acme")
        admin.create_tenant(self.db, "other")
        admin.create_user(self.db, "acme", "ann", "ann-password-1", admin=True)
        admin.create_user(self.db, "acme", "ben", "ben-password-1")
        admin.create_user(self.db, "other", "oz", "oz-password-1", admin=True)
        self.clock = Clock()
        self.posts = []
        self.status = 200
        self.dns = {"hooks.example.com": ["93.184.216.34"]}
        self.app = create_app(self.db, clock=self.clock, http_post=self._post, resolve=self._resolve)

    def _post(self, url, body, headers):
        self.posts.append((url, body, headers))
        return self.status

    def _resolve(self, host):
        return self.dns[host]

    def login(self, user, password=None, tenant="acme"):
        password = password or f"{user}-password-1"
        return call(self.app, "POST", "/login",
                    body=json.dumps({"tenant": tenant, "username": user, "password": password}).encode())

    def token(self, user, tenant="acme"):
        status, _, body = self.login(user, tenant=tenant)
        self.assertEqual(status, 200)
        return json.loads(body)["token"]

    def upload(self, token, name, data=b"x"):
        from urllib.parse import urlencode
        return call(self.app, "POST", "/documents", body=data, token=token, query=urlencode({"filename": name}))


class AuthTests(Base):
    def test_login_and_logout(self):
        tok = self.token("ann")
        self.assertEqual(call(self.app, "GET", "/documents", token=tok)[0], 200)
        self.assertEqual(call(self.app, "POST", "/logout", token=tok)[0], 204)
        self.assertEqual(call(self.app, "GET", "/documents", token=tok)[0], 401)

    def test_idle_and_absolute_expiry(self):
        tok = self.token("ann")
        self.clock.t += appmod.SESSION_IDLE_SECONDS + 1
        self.assertEqual(call(self.app, "GET", "/documents", token=tok)[0], 401)
        tok = self.token("ann")
        for _ in range(appmod.SESSION_ABSOLUTE_SECONDS // 600 + 1):
            self.clock.t += 600
            status = call(self.app, "GET", "/documents", token=tok)[0]
        self.assertEqual(status, 401)

    def test_lockout_after_repeated_failures(self):
        for _ in range(appmod.LOGIN_MAX_FAILURES):
            self.assertEqual(self.login("ben", "wrong-password")[0], 401)
        self.assertEqual(self.login("ben")[0], 429)
        self.clock.t += appmod.LOGIN_LOCK_SECONDS + 1
        self.assertEqual(self.login("ben")[0], 200)

    def test_password_change_revokes_other_sessions(self):
        a, b = self.token("ben"), self.token("ben")
        body = json.dumps({"old_password": "ben-password-1", "new_password": "ben-password-2"}).encode()
        self.assertEqual(call(self.app, "POST", "/password", body=body, token=a)[0], 204)
        self.assertEqual(call(self.app, "GET", "/documents", token=b)[0], 401)
        self.assertEqual(call(self.app, "GET", "/documents", token=a)[0], 200)

    def test_production_hash_parameters(self):
        stored = security.hash_password("pw-12345678", iterations=self._iters)
        algo, iters, salt, _ = stored.split("$")
        self.assertEqual((algo, int(iters)), ("pbkdf2_sha256", 600_000))
        self.assertTrue(security.verify_password("pw-12345678", stored))
        self.assertFalse(security.verify_password("pw-12345679", stored))


class DocumentTests(Base):
    def test_upload_list_download_share(self):
        tok = self.token("ann")
        status, _, body = self.upload(tok, "a.txt", b"hello")
        self.assertEqual(status, 201)
        doc = json.loads(body)
        status, headers, data = call(self.app, "GET", f"/documents/{doc['id']}", token=self.token("ben"))
        self.assertEqual((status, data), (200, b"hello"))
        self.assertIn('filename="a.txt"', headers["Content-Disposition"])
        status, _, body = call(self.app, "POST", f"/documents/{doc['id']}/share", token=tok)
        url = json.loads(body)["url"]
        self.assertEqual(call(self.app, "GET", url, token=self.token("ben"))[0], 200)
        self.assertEqual(call(self.app, "GET", url, token=self.token("oz", "other"))[0], 404)
        self.assertEqual(call(self.app, "GET", f"/documents/{doc['id']}", token=self.token("oz", "other"))[0], 404)

    def test_search_is_parameterised_and_literal(self):
        tok = self.token("ann")
        self.upload(tok, "100%_done.txt")
        self.upload(tok, "other.txt")
        _, _, body = call(self.app, "GET", "/documents", token=tok, query="q=%25_")
        self.assertEqual([d["filename"] for d in json.loads(body)["documents"]], ["100%_done.txt"])
        status, _, body = call(self.app, "GET", "/documents", token=tok, query="q=%27%20OR%201%3D1%20--")
        self.assertEqual((status, json.loads(body)["documents"]), (200, []))

    def test_upload_limits_and_names(self):
        tok = self.token("ann")
        status, _, _ = call(self.app, "POST", "/documents", token=tok, query="filename=big",
                            content_length=appmod.MAX_UPLOAD_BYTES + 1)
        self.assertEqual(status, 413)
        status, _, body = self.upload(tok, "../../x.txt")
        self.assertEqual(status, 201)
        self.assertEqual(json.loads(body)["filename"], ".._.._x.txt")
        self.assertEqual(sorted(os.listdir(os.path.join(self.dir, "files"))), [json.loads(body)["id"]])
        self.assertEqual(self.upload(tok, "..")[0], 400)
        status, _, body = self.upload(tok, "a\r\nb.txt")
        self.assertEqual(json.loads(body)["filename"], "ab.txt")

    def test_csv_export_neutralises_formulas(self):
        tok = self.token("ann")
        self.upload(tok, "=1+1")
        status, headers, body = call(self.app, "GET", "/tenant/export.csv", token=tok)
        self.assertEqual(status, 200)
        rows = list(csv.reader(io.StringIO(body.decode())))
        self.assertEqual(rows[1][1], "'=1+1")
        self.assertEqual(call(self.app, "GET", "/tenant/export.csv", token=self.token("ben"))[0], 403)

    def test_malformed_json_is_400_not_500(self):
        status, _, body = call(self.app, "POST", "/login", body=b"{nope")
        self.assertEqual(status, 400)
        self.assertNotIn(b"Traceback", body)


class WebhookTests(Base):
    URL = "https://hooks.example.com/in"

    def set_hook(self, url):
        return call(self.app, "PUT", "/tenant/webhook", body=json.dumps({"url": url}).encode(),
                    token=self.token("ann"))[0]

    def test_destination_policy(self):
        resolve = {"pub.test": ["93.184.216.34"], "lo.test": ["127.0.0.1"], "meta.test": ["169.254.169.254"],
                   "mapped.test": ["::ffff:10.0.0.1"]}.__getitem__
        self.assertIsNone(webhooks.destination_problem("https://pub.test/x", resolve))
        for url in ("http://lo.test/", "http://meta.test/", "http://mapped.test/", "file:///etc/passwd",
                    "http://user:pw@pub.test/", "http://127.0.0.1/", "http://[::1]/", "http://nx.test/"):
            self.assertIsNotNone(webhooks.destination_problem(url, resolve), url)

    def test_delivery_retry_and_give_up(self):
        self.assertEqual(self.set_hook(self.URL), 204)
        self.status = 500
        self.upload(self.token("ann"), "a.txt")
        for _ in range(200):
            self.app.run_pending_deliveries()
            self.clock.t += 600
        self.assertEqual(len(self.posts), appmod.WEBHOOK_MAX_ATTEMPTS)
        bodies = {p[1] for p in self.posts}
        ids = {p[2]["Webhook-Id"] for p in self.posts}
        self.assertEqual((len(bodies), len(ids)), (1, 1))

    def test_rebinding_blocked_at_send_time(self):
        self.assertEqual(self.set_hook(self.URL), 204)
        self.dns["hooks.example.com"] = ["10.0.0.1"]
        self.upload(self.token("ann"), "a.txt")
        self.assertEqual(self.app.run_pending_deliveries(), 0)
        self.assertEqual(self.posts, [])

    def test_second_worker_does_not_resend_in_flight_attempt(self):
        self.assertEqual(self.set_hook(self.URL), 204)
        results = []

        def post(url, body, headers):
            self.posts.append(url)
            if len(self.posts) == 1:
                t = threading.Thread(target=lambda: results.append(self.app.run_pending_deliveries()))
                t.start()
                t.join()
            return 200
        self.app.http_post = post
        self.upload(self.token("ann"), "a.txt")
        self.assertEqual(self.app.run_pending_deliveries(), 1)
        self.assertEqual((len(self.posts), results), (1, [0]))


class CliAndMigrationTests(unittest.TestCase):
    def test_cli_exit_codes(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        db = os.path.join(d, "c.db")

        def cli(*args, stdin=""):
            return subprocess.run([sys.executable, "-m", "docket.cli", "--db", db, *args], input=stdin,
                                  capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(cli("migrate").returncode, 0)
        self.assertEqual(cli("create-tenant", "t").returncode, 0)
        r = cli("create-tenant", "t")
        self.assertEqual(r.returncode, 1)
        self.assertIn("already exists", r.stderr)
        self.assertEqual(cli("create-user", "nope", "u", stdin="password-123\n").returncode, 1)
        self.assertEqual(cli("bogus").returncode, 2)

    def test_migrations_forward_only(self):
        from docket import db as dbmod
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        mig = d / "m"
        mig.mkdir()
        (mig / "0002_b.sql").write_text("CREATE TABLE b (x);")
        dbmod.migrate(str(d / "x.db"), mig)
        (mig / "0001_a.sql").write_text("CREATE TABLE a (x);")
        with self.assertRaises(dbmod.MigrationError):
            dbmod.migrate(str(d / "x.db"), mig)


if __name__ == "__main__":
    unittest.main()
