"""Hidden SPEC tests: each checks behaviour the ticket (prompt.md) states."""
import csv
import io
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import shutil
import unittest

from .helpers import ROOT, DocketCase, FakeClock, FakeHTTP, FakeResolver, LogCapture, call_wsgi


class AuthSpec(DocketCase):
    def test_login_success_returns_token_and_role(self):
        r = self.login("alice")
        self.assertEqual(r.status, 200, r)
        body = r.json()
        self.assertIsInstance(body["token"], str)
        self.assertEqual(body["username"], "alice")
        self.assertEqual(body["role"], "admin")
        self.assertEqual(self.login("bob").json()["role"], "member")

    def test_login_wrong_password_401(self):
        self.assertEqual(self.login("alice", password="nope-nope-nope").status, 401)

    def test_login_unknown_user_401(self):
        self.assertEqual(self.login("mallory", password="whatever-123").status, 401)

    def test_authenticated_routes_require_token(self):
        for method, path in [("GET", "/documents"), ("POST", "/documents"),
                             ("GET", "/tenant/export.csv"), ("POST", "/logout")]:
            r = self.req(method, path, query={"filename": "x"} if method == "POST" else None)
            self.assertEqual(r.status, 401, f"{method} {path}: {r!r}")
        r = self.req("GET", "/documents", token="not-a-real-token")
        self.assertEqual(r.status, 401)

    def test_logout_returns_204(self):
        tok = self.token("bob")
        self.assertEqual(self.req("POST", "/logout", token=tok).status, 204)

    def test_password_change(self):
        tok = self.token("bob")
        r = self.req("POST", "/password", token=tok,
                     json_body={"old_password": "wrong-old-pass", "new_password": "Brand-New-Pass-42"})
        self.assertEqual(r.status, 403, r)
        r = self.req("POST", "/password", token=tok,
                     json_body={"old_password": self.PASSWORDS["bob"], "new_password": "Brand-New-Pass-42"})
        self.assertEqual(r.status, 204, r)
        self.assertEqual(self.login("bob", password="Brand-New-Pass-42").status, 200)
        self.assertEqual(self.login("bob").status, 401)


class DocumentSpec(DocketCase):
    def test_upload_list_download_roundtrip(self):
        tok = self.token("bob")
        doc = self.upload_ok(tok, "report.pdf", b"%PDF-1.7 hello")
        self.assertEqual(doc["filename"], "report.pdf")
        self.assertEqual(doc["size"], len(b"%PDF-1.7 hello"))
        r = self.list_docs(tok)
        self.assertEqual(r.status, 200)
        docs = r.json()["documents"]
        self.assertEqual([d["id"] for d in docs], [doc["id"]])
        d = docs[0]
        for key in ("id", "filename", "size", "uploaded_by", "uploaded_at"):
            self.assertIn(key, d)
        self.assertEqual(d["uploaded_by"], "bob")
        self.assertRegex(d["uploaded_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")
        r = self.req("GET", f"/documents/{doc['id']}", token=tok)
        self.assertEqual(r.status, 200, r)
        self.assertEqual(r.body, b"%PDF-1.7 hello")
        self.assertTrue(r.headers["content-type"].startswith("application/octet-stream"))
        cd = r.headers.get("content-disposition", "")
        self.assertIn("attachment", cd)
        self.assertIn("report.pdf", cd)

    def test_colleague_can_download_by_id(self):
        doc = self.upload_ok(self.token("alice"), "plan.txt", b"plan")
        r = self.req("GET", f"/documents/{doc['id']}", token=self.token("bob"))
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, b"plan")

    def test_upload_missing_filename_400(self):
        r = self.req("POST", "/documents", body=b"abc", token=self.token("bob"))
        self.assertEqual(r.status, 400, r)

    def test_unknown_document_404(self):
        r = self.req("GET", "/documents/does-not-exist-999", token=self.token("bob"))
        self.assertEqual(r.status, 404, r)

    def test_list_is_per_tenant(self):
        self.upload_ok(self.token("alice"), "acme-only.txt", b"a")
        self.upload_ok(self.token("carol"), "globex-only.txt", b"g")
        names = [d["filename"] for d in self.list_docs(self.token("bob")).json()["documents"]]
        self.assertEqual(names, ["acme-only.txt"])

    def test_search_filter(self):
        tok = self.token("alice")
        self.upload_ok(tok, "Quarterly-Report.pdf", b"1")
        self.upload_ok(tok, "notes.txt", b"2")
        r = self.list_docs(tok, q="report")
        self.assertEqual(r.status, 200)
        self.assertEqual([d["filename"] for d in r.json()["documents"]], ["Quarterly-Report.pdf"])
        self.assertEqual(self.list_docs(tok, q="zzz").json()["documents"], [])

    def test_share_link_opened_by_colleague(self):
        doc = self.upload_ok(self.token("alice"), "deck.key", b"slides")
        r = self.req("POST", f"/documents/{doc['id']}/share", token=self.token("alice"))
        self.assertEqual(r.status, 201, r)
        share = r.json()
        self.assertIsInstance(share["share_id"], str)
        self.assertEqual(share["url"], f"/shares/{share['share_id']}")
        r = self.req("GET", share["url"], token=self.token("bob"))
        self.assertEqual(r.status, 200, r)
        self.assertEqual(r.body, b"slides")

    def test_unknown_share_404(self):
        r = self.req("GET", "/shares/nope-nope-nope", token=self.token("bob"))
        self.assertEqual(r.status, 404)

    def test_unknown_route_404_and_wrong_method_405(self):
        tok = self.token("bob")
        self.assertEqual(self.req("GET", "/nothing-here", token=tok).status, 404)
        self.assertEqual(self.req("DELETE", "/documents", token=tok).status, 405)
        self.assertEqual(self.req("GET", "/login").status, 405)

    def test_error_body_is_json(self):
        r = self.login("alice", password="bad-password-1")
        self.assertEqual(r.status, 401)
        self.assertIn("error", r.json())


class AdminFeatureSpec(DocketCase):
    def test_csv_export_for_admin(self):
        tok = self.token("alice")
        doc = self.upload_ok(tok, "budget.xlsx", b"12345")
        r = self.req("GET", "/tenant/export.csv", token=tok)
        self.assertEqual(r.status, 200, r)
        self.assertTrue(r.headers["content-type"].startswith("text/csv"))
        rows = list(csv.reader(io.StringIO(r.body.decode("utf-8"))))
        self.assertEqual(rows[0], ["id", "filename", "size", "uploaded_by", "uploaded_at"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][:4], [doc["id"], "budget.xlsx", "5", "alice"])

    def test_csv_export_member_403(self):
        self.assertEqual(self.req("GET", "/tenant/export.csv", token=self.token("bob")).status, 403)

    def test_webhook_set_member_403(self):
        r = self.set_webhook(self.token("bob"), "https://hooks.example.com/x")
        self.assertEqual(r.status, 403)

    def test_activity_logged_for_upload(self):
        tok = self.token("bob")
        with LogCapture() as cap:
            doc = self.upload_ok(tok, "logged.txt", b"x")
        acts = [r for r in cap.records if r.name == "docket.activity"]
        self.assertTrue(acts, "no record on the docket.activity logger for an upload")
        self.assertTrue(any(doc["id"] in LogCapture.full_text(r) or "logged.txt" in LogCapture.full_text(r)
                            for r in acts))


class WebhookSpec(DocketCase):
    URL = "https://hooks.example.com/docket"

    def test_webhook_delivered_on_upload(self):
        admin = self.token("alice")
        self.assertEqual(self.set_webhook(admin, self.URL).status, 204)
        doc = self.upload_ok(admin, "w.txt", b"hello")
        n = self.app.run_pending_deliveries()
        self.assertEqual(n, 1)
        calls = self.http.calls_to(self.URL)
        self.assertEqual(len(calls), 1)
        url, body, headers = calls[0]
        payload = json.loads(body)
        self.assertEqual(payload["event"], "document.uploaded")
        self.assertEqual(payload["tenant"], "acme")
        self.assertEqual(payload["document"]["id"], doc["id"])
        self.assertEqual(payload["document"]["filename"], "w.txt")
        self.assertEqual(payload["document"]["size"], 5)
        self.assertEqual(payload["document"]["uploaded_by"], "alice")
        ctype = {k.lower(): v for k, v in headers.items()}.get("content-type", "")
        self.assertTrue(ctype.startswith("application/json"))
        self.assertEqual(self.app.run_pending_deliveries(), 0)

    def test_no_webhook_no_delivery(self):
        self.upload_ok(self.token("alice"), "w.txt", b"hello")
        self.assertEqual(self.app.run_pending_deliveries(), 0)
        self.assertEqual(self.http.calls, [])

    def test_webhook_cleared(self):
        admin = self.token("alice")
        self.assertEqual(self.set_webhook(admin, self.URL).status, 204)
        self.assertEqual(self.set_webhook(admin, None).status, 204)
        self.upload_ok(admin, "w.txt", b"hello")
        self.app.run_pending_deliveries()
        self.assertEqual(self.http.calls, [])

    def test_failed_delivery_is_retried_then_stops_on_success(self):
        outcomes = iter([500])
        self.http.responder = lambda url, body, headers, n: next(outcomes, 200)
        admin = self.token("alice")
        self.assertEqual(self.set_webhook(admin, self.URL).status, 204)
        self.upload_ok(admin, "r.txt", b"retry")
        self.assertEqual(self.app.run_pending_deliveries(), 1)
        self.assertEqual(self.app.run_pending_deliveries(), 0, "retried with no wait")
        self.clock.advance(31)
        self.assertEqual(self.app.run_pending_deliveries(), 1, "first retry not made ~30s later")
        for _ in range(48):
            self.clock.advance(3600)
            self.app.run_pending_deliveries()
        calls = self.http.calls_to(self.URL)
        self.assertEqual(len(calls), 2)
        self.assertEqual(json.loads(calls[0][1])["document"], json.loads(calls[1][1])["document"])

    def test_exception_from_http_post_is_retried(self):
        def responder(url, body, headers, n):
            if n == 0:
                raise OSError("connection refused")
            return 204
        self.http.responder = responder
        admin = self.token("alice")
        self.set_webhook(admin, self.URL)
        self.upload_ok(admin, "e.txt", b"x")
        self.app.run_pending_deliveries()
        self.clock.advance(31)
        self.app.run_pending_deliveries()
        self.assertEqual(len(self.http.calls_to(self.URL)), 2)


class MigrationAndCliSpec(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="docket-hidden-cli-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.db = os.path.join(self.tmp, "d.db")

    def test_numbered_migration_files(self):
        mig = ROOT / "docket" / "migrations"
        names = sorted(p.name for p in mig.iterdir() if p.suffix == ".sql")
        self.assertTrue(names, "no migrations")
        for n in names:
            self.assertRegex(n, r"^\d{4}_[A-Za-z0-9_\-]+\.sql$")
        self.assertTrue(names[0].startswith("0001_"))

    def test_migrate_is_idempotent_and_recorded(self):
        import sqlite3
        from docket import admin
        admin.migrate(self.db)
        admin.migrate(self.db)
        conn = sqlite3.connect(self.db)
        try:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()
        self.assertGreaterEqual(len(tables), 3, tables)

    def _cli(self, *args, stdin=""):
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        return subprocess.run([sys.executable, "-m", "docket.cli", "--db", self.db, *args],
                              input=stdin, capture_output=True, text=True, cwd=str(ROOT),
                              env=env, timeout=120)

    def test_cli_creates_tenant_and_user_who_can_log_in(self):
        r = self._cli("migrate")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._cli("create-tenant", "initech")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._cli("create-user", "initech", "peter", "--admin", stdin="Peter-Pass-9-xyz\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        from docket.app import create_app
        app = create_app(self.db, clock=FakeClock(), http_post=FakeHTTP(), resolve=FakeResolver())
        resp = call_wsgi(app, "POST", "/login",
                         json_body={"tenant": "initech", "username": "peter", "password": "Peter-Pass-9-xyz"})
        self.assertEqual(resp.status, 200, resp)
        self.assertEqual(resp.json()["role"], "admin")


class DeliverablesSpec(unittest.TestCase):
    def test_dockerfile_ci_and_tests_exist(self):
        self.assertTrue((ROOT / "Dockerfile").is_file(), "Dockerfile missing")
        ci = ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(ci.is_file(), "ci.yml missing")
        self.assertRegex(ci.read_text(), r"unittest|pytest")
        tests = ROOT / "tests"
        self.assertTrue(tests.is_dir() and any(p.name.startswith("test") and p.suffix == ".py"
                                               for p in tests.iterdir()), "no tests/test*.py")

    def test_serve_module_exists(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec("docket.serve"))
        self.assertIsNotNone(importlib.util.find_spec("docket.cli"))


if __name__ == "__main__":
    unittest.main()
