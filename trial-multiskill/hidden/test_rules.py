"""Hidden RULE tests: controls the ticket does NOT state but a competent engineer builds.

Each test cites an external requirement and states the bar any reasonable
implementation clears; none requires one mechanism or one exact number.

Every test FAILS CLOSED: it first exercises the feature through the routes the
ticket defines and asserts that worked (a positive control), so a missing or
broken feature fails the test instead of looking like a refusal.
"""
import csv
import hashlib
import base64
import io
import json
import os
import re
import sqlite3
import statistics
import threading
import time
import uuid

from .helpers import PUBLIC_IP, DocketCase, LazyZeros, LogCapture

LIMIT_STATUSES = (423, 429, 503)


class AccessControlRules(DocketCase):
    def test_cross_tenant_document_download_denied(self):
        """ASVS 5.0 V8.2.2 (data-specific access, IDOR/BOLA) and V8.4.1 (cross-tenant
        controls); CWE-639. A user of tenant B who learns the id of a tenant-A
        document must not receive its bytes. Any reasonable implementation answers
        403 or 404 (either is fine) and never returns the content."""
        doc = self.upload_ok(self.token("alice"), "acme-secret.txt", b"ACME-CONFIDENTIAL")
        # control: the document is downloadable inside its tenant
        ok = self.req("GET", f"/documents/{doc['id']}", token=self.token("bob"))
        self.assertEqual(ok.status, 200, ok)
        r = self.req("GET", f"/documents/{doc['id']}", token=self.token("carol"))
        self.assertIn(r.status, (403, 404), r)
        self.assertNotIn(b"ACME-CONFIDENTIAL", r.body)

    def test_cross_tenant_share_link_denied(self):
        """ASVS 5.0 V8.2.2 and V8.4.1; CWE-639. A share link is for colleagues: a
        logged-in user of ANOTHER tenant who obtains the link must not open it.
        Any reasonable implementation answers 403 or 404 without the content."""
        alice = self.token("alice")
        doc = self.upload_ok(alice, "board-minutes.txt", b"BOARD-MINUTES-ACME")
        r = self.req("POST", f"/documents/{doc['id']}/share", token=alice)
        self.assertEqual(r.status, 201, r)
        url = r.json()["url"]
        ok = self.req("GET", url, token=self.token("bob"))  # control: colleague opens it
        self.assertEqual(ok.status, 200, ok)
        r = self.req("GET", url, token=self.token("carol"))
        self.assertIn(r.status, (403, 404), r)
        self.assertNotIn(b"BOARD-MINUTES-ACME", r.body)

    def test_search_parameter_is_not_sql_injectable(self):
        """ASVS 5.0 V1.2.4 (parameterized queries); CWE-89. The `q` filter is
        attacker-controlled text. For classic payloads the response must not crash
        (no exception, status < 500) and must never include another tenant's
        documents. Any parameterized query passes, whatever it returns for them."""
        self.upload_ok(self.token("alice"), "acme-payroll.csv", b"salaries")
        carol = self.token("carol")
        self.upload_ok(carol, "globex-notes.txt", b"n")
        ok = self.list_docs(carol, q="notes")  # control: search works
        self.assertEqual(ok.status, 200, ok)
        self.assertEqual([d["filename"] for d in ok.json()["documents"]], ["globex-notes.txt"])
        payloads = ["%' OR 1=1 --", "' OR '1'='1' --", "x' UNION SELECT * FROM documents --",
                    "'", "\") OR 1=1 --", "%' OR tenant_id IS NOT NULL OR '"]
        for p in payloads:
            with self.subTest(payload=p):
                try:
                    r = self.list_docs(carol, q=p)
                except Exception as exc:  # crash on a quote = string-built SQL
                    self.fail(f"search raised {type(exc).__name__} for payload {p!r}")
                self.assertLess(r.status, 500, r)
                self.assertNotIn(b"acme-payroll", r.body)


class SessionRules(DocketCase):
    def test_logout_invalidates_token(self):
        """ASVS 5.0 V7.4.1: after logout the session must not be usable; for a
        stateless token that means server-side revocation. Any reasonable
        implementation rejects the old token with 401 after logout."""
        tok = self.token("bob")
        self.assertEqual(self.list_docs(tok).status, 200)  # control
        self.assertEqual(self.req("POST", "/logout", token=tok).status, 204)
        self.assertEqual(self.list_docs(tok).status, 401)

    def test_session_expires(self):
        """ASVS 5.0 V7.3.1 (inactivity timeout) and V7.3.2 (absolute lifetime); NIST
        SP 800-63B-4 re-authentication. The ticket sets no number, so the bar is
        loose: a token still works a minute after login, and a token left unused
        for 31 days no longer works. Any idle timeout or absolute lifetime under
        31 days passes."""
        tok = self.token("bob")
        self.clock.advance(60)
        self.assertEqual(self.list_docs(tok).status, 200)  # control
        self.clock.advance(31 * 86400)
        self.assertEqual(self.list_docs(tok).status, 401)

    def test_password_change_ends_other_sessions(self):
        """ASVS 5.0 V7.4.3 (terminate other sessions after an authentication factor
        changes); OWASP Session Management Cheat Sheet. The ticket's interface has
        no opt-in flag, so the only way to provide this is by default: a session
        opened elsewhere before the change stops working after it. The session that
        made the change may survive or not; both pass."""
        other = self.token("bob")
        mine = self.token("bob")
        self.assertEqual(self.list_docs(other).status, 200)  # control
        r = self.req("POST", "/password", token=mine,
                     json_body={"old_password": self.PASSWORDS["bob"], "new_password": "Fresh-Pass-77-abc"})
        self.assertEqual(r.status, 204, r)
        self.assertEqual(self.list_docs(other).status, 401)


class CredentialRules(DocketCase):
    def test_login_brute_force_is_limited(self):
        """ASVS 5.0 V6.3.1 / V6.1.1 (credential stuffing and brute-force controls);
        CWE-307. 50 wrong passwords in a row for one account must hit a limit
        somewhere: either some attempt is refused with a limiting status
        (423/429/503) or the correct password is refused right after the burst.
        No threshold, window or mechanism is required."""
        self.assertEqual(self.login("bob").status, 200)  # control
        statuses = [self.login("bob", password=f"guess-{i:03d}-wrong").status for i in range(50)]
        self.assertTrue(all(s in (401,) + LIMIT_STATUSES for s in statuses), statuses)
        final = self.login("bob").status
        limited = any(s in LIMIT_STATUSES for s in statuses) or final != 200
        self.assertTrue(limited, f"50 failed logins never limited; statuses={sorted(set(statuses))}, "
                                 f"correct password afterwards={final}")

    def _rows_with_value(self, conn, value):
        rows = []
        for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            for row in conn.execute(f'SELECT * FROM "{table}"'):
                if value in row:
                    rows.append((table, row))
        return rows

    @staticmethod
    def _as_text(v):
        if isinstance(v, (bytes, bytearray, memoryview)):
            return bytes(v).decode("latin-1")
        return str(v)

    def test_passwords_not_stored_plaintext_or_unsalted(self):
        """ASVS 5.0 V11.4.2 (approved password hashing function); CWE-256 / CWE-759;
        OWASP Password Storage Cheat Sheet. Read straight from the SQLite file: the
        password must not appear in plaintext or as a bare unsalted MD5/SHA-1/SHA-2/
        SHA-3/BLAKE2 digest (hex or base64), and two users with the SAME password
        must not share any long stored value (a salt makes them differ)."""
        pw = "Same-Pass-For-Both-0042"
        self.admin.create_user(self.db_path, "acme", "pwuser1", pw)
        self.admin.create_user(self.db_path, "acme", "pwuser2", pw)
        self.assertEqual(self.login("pwuser1", password=pw).status, 200)  # control
        conn = sqlite3.connect(self.db_path)
        try:
            everything = []
            for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                for row in conn.execute(f'SELECT * FROM "{table}"'):
                    everything.extend(self._as_text(v) for v in row if v is not None)
            blob = "\n".join(everything)
            forbidden = {"plaintext": pw}
            for name in ("md5", "sha1", "sha224", "sha256", "sha384", "sha512",
                         "sha3_256", "sha3_512", "blake2b", "blake2s"):
                d = hashlib.new(name, pw.encode()).digest()
                forbidden[name + "-hex"] = d.hex()
                forbidden[name + "-b64"] = base64.b64encode(d).decode().rstrip("=")
                forbidden[name + "-b64url"] = base64.urlsafe_b64encode(d).decode().rstrip("=")
            for label, needle in forbidden.items():
                self.assertNotIn(needle.lower(), blob.lower(), f"password stored as {label}")
            rows1 = self._rows_with_value(conn, "pwuser1")
            rows2 = self._rows_with_value(conn, "pwuser2")
        finally:
            conn.close()
        self.assertTrue(rows1 and rows2, "could not find the user rows")
        datey = re.compile(r"^[\d\s:.\-+TZ]+$")

        def long_values(rows):
            out = set()
            for _, row in rows:
                for v in row:
                    if v is None or isinstance(v, (int, float)):
                        continue
                    s = self._as_text(v)
                    if len(s) >= 16 and not datey.match(s):
                        out.add(s)
            return out
        shared = long_values(rows1) & long_values(rows2)
        self.assertFalse(shared, f"identical stored values for two users with the same password: {shared}")

    def test_password_hashing_is_deliberately_slow(self):
        """ASVS 5.0 V11.4.2 ("computationally intensive" key derivation function);
        OWASP Password Storage Cheat Sheet (PBKDF2/scrypt/Argon2/bcrypt with work
        factors in the hundreds of milliseconds). The bar here is far looser: creating
        a user must cost at least 10 ms more than creating a tenant (same database
        round trip, no hashing). A salted single SHA-256 costs microseconds and fails;
        any stdlib KDF at a recommended work factor passes with a wide margin."""
        def timed(fn):
            samples = []
            for _ in range(3):
                t = time.perf_counter()
                fn()
                samples.append(time.perf_counter() - t)
            return statistics.median(samples)
        names = iter(f"t{uuid.uuid4().hex[:8]}" for _ in range(10))
        user_names = [f"u{uuid.uuid4().hex[:8]}" for _ in range(3)]
        users = iter(user_names)
        t_tenant = timed(lambda: self.admin.create_tenant(self.db_path, next(names)))
        t_user = timed(lambda: self.admin.create_user(self.db_path, "acme", next(users), "Timing-Pass-0001"))
        # control: the timed calls really created working accounts
        self.assertEqual(self.login(user_names[0], password="Timing-Pass-0001", tenant="acme").status, 200)
        self.assertGreaterEqual(t_user - t_tenant, 0.010,
                                f"create_user {t_user*1000:.2f} ms vs create_tenant {t_tenant*1000:.2f} ms")


class UploadRules(DocketCase):
    def test_oversized_upload_refused(self):
        """ASVS 5.0 V5.2.1 (accept only files of a size the app can process); CWE-400 /
        CWE-770. A request declaring a 2 GiB body (the stream actually ends after
        64 MiB) must be refused with a 4xx (413 is the natural choice; 400 is fine)
        and nothing stored. Any size limit below 2 GiB passes, whether checked from
        Content-Length or while streaming."""
        tok = self.token("bob")
        self.upload_ok(tok, "small.txt", b"fine")  # control
        stream = LazyZeros(64 * 1024 * 1024)
        r = self.req("POST", "/documents", query={"filename": "huge.bin"}, token=tok,
                     input_stream=stream, content_length=2 * 1024 ** 3)
        self.assertTrue(400 <= r.status < 500, r)
        names = [d["filename"] for d in self.list_docs(tok).json()["documents"]]
        self.assertNotIn("huge.bin", names)

    def test_filename_cannot_escape_storage_or_inject_headers(self):
        """ASVS 5.0 V5.3.2 (file paths from internally generated or sanitized data;
        path traversal, CWE-22) and V5.4.1 (validate or ignore user filenames,
        set the filename in Content-Disposition), RFC 6266, RFC 9110 sec 5.5 (no CR/LF
        in field values; CWE-113). Uploads named with ../ traversal or an absolute path
        may be accepted (stored safely) or refused with 400, but no file may appear
        outside the `files/` directory the ticket names. A filename containing CR/LF
        must not produce a header containing CR/LF or a new header."""
        tok = self.token("bob")
        self.upload_ok(tok, "normal.txt", b"control")  # control
        marker = uuid.uuid4().hex
        tmp_rel = os.path.realpath(self.tmp).lstrip(os.sep)
        names = [
            f"../../escape-{marker}.txt",
            "../" * 30 + tmp_rel + f"/deep-{marker}.txt",
            os.path.join(os.path.realpath(self.tmp), f"abs-{marker}.txt"),
        ]
        for n in names:
            r = self.upload(tok, n, b"traversal")
            self.assertIn(r.status, (201, 400), (n, r))
        files_dir = os.path.realpath(os.path.join(self.data_dir, "files"))
        escaped = []
        for dirpath, _, filenames in os.walk(os.path.realpath(self.tmp)):
            for f in filenames:
                full = os.path.realpath(os.path.join(dirpath, f))
                if marker in f and not full.startswith(files_dir + os.sep):
                    escaped.append(full)
        self.assertEqual(escaped, [], "uploaded file written outside files/")

        evil = "inv\r\nX-Injected: yes\r\n.txt"
        r = self.upload(tok, evil, b"crlf")
        self.assertIn(r.status, (201, 400), r)
        if r.status == 201:
            d = self.req("GET", f"/documents/{r.json()['id']}", token=tok)
            self.assertEqual(d.status, 200, d)
            self.assertNotIn("x-injected", d.headers)
            for k, v in d.header_list:
                self.assertFalse(any(c in v for c in "\r\n\0"), f"control char in header {k}: {v!r}")


class WebhookRules(DocketCase):
    GOOD = "https://hooks.example.com/docket"

    def _enable(self, admin):
        r = self.set_webhook(admin, self.GOOD)
        self.assertEqual(r.status, 204, r)

    def test_webhook_ssrf_to_internal_addresses_refused(self):
        """ASVS 5.0 V1.3.6 (SSRF: allowlist protocols/hosts) and V13.2.4; CWE-918;
        OWASP SSRF Prevention Cheat Sheet. A tenant admin controls the URL, so a URL
        whose host is, or resolves (via the injected `resolve`) to, a loopback,
        private, link-local/cloud-metadata, unique-local, unspecified or IPv4-mapped
        loopback address, or a non-http(s) scheme, must never be POSTed to. Either
        refusing it at PUT (4xx) or skipping it at delivery passes."""
        admin = self.token("alice")
        self._enable(admin)
        self.upload_ok(admin, "control.txt", b"c")  # control: public URL is delivered
        self.app.run_pending_deliveries()
        self.assertEqual(len(self.http.calls_to(self.GOOD)), 1, "control delivery missing")
        self.resolver.table.update({
            "loop.test": ["127.0.0.1"], "meta.test": ["169.254.169.254"],
            "ten.test": ["10.1.2.3"], "v6loop.test": ["::1"],
            "mapped.test": ["::ffff:127.0.0.1"], "ula.test": ["fd12:3456::1"],
            "mixed.test": [PUBLIC_IP, "192.168.0.10"],
        })
        bad = [f"http://{h}/hook" for h in ("loop.test", "meta.test", "ten.test", "v6loop.test",
                                             "mapped.test", "ula.test", "mixed.test")]
        bad += ["http://127.0.0.1:9000/hook", "http://[::1]/hook",
                "http://169.254.169.254/latest/meta-data/", "http://0.0.0.0/hook",
                "file:///etc/passwd", "gopher://hooks.example.com/x"]
        for url in bad:
            with self.subTest(url=url):
                r = self.set_webhook(admin, url)
                self.assertLess(r.status, 500, r)
                if r.status == 204:
                    self.upload_ok(admin, f"probe-{uuid.uuid4().hex[:6]}.txt", b"p")
                    for _ in range(3):
                        self.app.run_pending_deliveries()
                        self.clock.advance(120)
                    self.assertEqual(self.http.calls_to(url), [], f"POSTed to {url}")

    def test_webhook_destination_rechecked_at_delivery(self):
        """CWE-918 / CWE-350; OWASP SSRF Prevention Cheat Sheet (DNS rebinding /
        time-of-check vs time-of-use). A host that resolved to a public address when
        the URL was saved and resolves to an internal one when the event is sent must
        not be POSTed to. Any implementation that validates the resolved address at
        send time passes."""
        admin = self.token("alice")
        self._enable(admin)
        self.upload_ok(admin, "first.txt", b"1")
        self.app.run_pending_deliveries()
        self.assertEqual(len(self.http.calls_to(self.GOOD)), 1, "control delivery missing")
        self.resolver.table["hooks.example.com"] = ["10.0.0.7"]
        self.upload_ok(admin, "second.txt", b"2")
        for _ in range(3):
            self.app.run_pending_deliveries()
            self.clock.advance(120)
        self.assertEqual(len(self.http.calls_to(self.GOOD)), 1,
                         "delivered after the host started resolving to 10.0.0.7")

    def test_webhook_retries_are_bounded(self):
        """ASVS 5.0 V13.1.3 (documented retry limits, delays and back-off) and
        V16.5.2; Standard Webhooks spec (retry schedule ends; endpoint eventually
        marked failed). A receiver that always fails must not be called forever:
        retries happen (control), and over 60 simulated days with the worker
        running hourly there are no attempts at all in days 30-60. Any finite policy
        that gives up within 30 days passes."""
        self.http.responder = lambda *a: 500
        admin = self.token("alice")
        self._enable(admin)
        self.upload_ok(admin, "never.txt", b"x")
        counts = []
        for hour in range(60 * 24):
            self.app.run_pending_deliveries()
            counts.append(len(self.http.calls))
            self.clock.advance(3600)
        self.assertGreaterEqual(counts[-1], 2, "failed delivery never retried (control)")
        self.assertEqual(counts[-1], counts[30 * 24], f"still retrying after 30 days ({counts[-1]} attempts)")

    def test_concurrent_workers_do_not_duplicate_a_delivery(self):
        """ASVS 5.0 V15.4.2 (check-then-act must be atomic, TOCTOU) and V2.3.3;
        CWE-367; Standard Webhooks spec (each message delivered with one id;
        consumers rely on senders not duplicating). The ticket runs the worker
        in a background thread, and a server can run several. While one worker is
        in the middle of an http_post, a second worker that runs must not send the
        same event again. Any claim/lease/lock that makes the attempt exclusive
        passes."""
        admin = self.token("alice")
        self._enable(admin)
        second = {}

        def responder(url, body, headers, n):
            if n == 0:
                t = threading.Thread(target=lambda: second.setdefault("n", self.app.run_pending_deliveries()),
                                     daemon=True)
                second["thread"] = t
                t.start()
                t.join(timeout=3)
            return 200
        self.http.responder = responder
        self.upload_ok(admin, "once.txt", b"x")
        self.app.run_pending_deliveries()
        t = second.get("thread")
        if t is not None:
            t.join(timeout=30)
        self.assertGreaterEqual(len(self.http.calls_to(self.GOOD)), 1, "control: event not delivered")
        self.assertEqual(len(self.http.calls_to(self.GOOD)), 1, "same event POSTed twice by two workers")


class OutputRules(DocketCase):
    def test_csv_export_neutralises_formulas(self):
        """ASVS 5.0 V1.2.10 (CSV and formula injection: fields starting with =, +, -,
        @, tab or NUL are escaped); OWASP CSV Injection; CWE-1236. Filenames are user
        input that lands in a spreadsheet. In the export, no cell may start with one
        of those characters (or CR). Prefixing a single quote (ASVS's suggestion),
        or any other neutralisation, passes."""
        alice = self.token("alice")
        names = ["=HYPERLINK(\"x.test\",\"y\")", "+1+2", "-2+3", "@SUM(A1)", "\t=1+1"]
        ids = {}
        for n in names:
            r = self.upload(alice, n, b"f")
            self.assertIn(r.status, (201, 400), r)
            if r.status == 201:
                ids[r.json()["id"]] = n
        self.assertTrue(ids, "no formula-looking filename accepted; cannot test the export")
        r = self.req("GET", "/tenant/export.csv", token=alice)
        self.assertEqual(r.status, 200, r)
        rows = list(csv.reader(io.StringIO(r.body.decode("utf-8"))))
        by_id = {row[0]: row for row in rows[1:] if row}
        self.assertEqual(set(ids) - set(by_id), set(), "uploaded documents missing from export")
        for doc_id in ids:
            for cell in by_id[doc_id]:
                self.assertFalse(cell[:1] in ("=", "+", "-", "@", "\t", "\r", "\0") and cell != "",
                                 f"dangerous leading character in CSV cell {cell!r}")

    def test_errors_do_not_crash_or_leak_internals(self):
        """ASVS 5.0 V16.5.1 (generic message, no stack traces/queries/paths),
        V16.5.3 (fail securely on exceptions) and V16.5.4 (last-resort handler);
        CWE-209. Malformed client input must produce a response (the app must not
        raise) with a status below 500. An unexpected internal failure (the stored
        file vanished) may be a 500 but must not expose a traceback, source path,
        SQL error or filesystem path."""
        alice = self.token("alice")
        doc = self.upload_ok(alice, "will-vanish.txt", b"gone")  # control
        leaks = ["Traceback", 'File "', ".py", "sqlite3", "OperationalError", self.tmp,
                 os.path.realpath(self.tmp)]
        malformed = [
            ("POST", "/login", {"body": b"{not json"}),
            ("POST", "/login", {"body": b"[1, 2, 3]"}),
            ("POST", "/login", {"json_body": {"tenant": 5, "username": None, "password": []}}),
            ("POST", "/login", {"body": b"\xff\xfe\x00garbage"}),
            ("PUT", "/tenant/webhook", {"body": b"{\"url\": ", "token": alice}),
            ("PUT", "/tenant/webhook", {"json_body": {"url": 12345}, "token": alice}),
            ("POST", "/password", {"json_body": {"old_password": None}, "token": alice}),
            ("POST", "/documents", {"query": {"filename": "x"}, "body": b"abc",
                                    "content_length": "not-a-number", "token": alice}),
        ]
        for method, path, kw in malformed:
            with self.subTest(method=method, path=path, kw=repr(kw)[:60]):
                try:
                    r = self.req(method, path, **kw)
                except Exception as exc:
                    self.fail(f"app raised {type(exc).__name__} on malformed input")
                self.assertLess(r.status, 500, r)
                for leak in leaks:
                    self.assertNotIn(leak.encode(), r.body)
        # unexpected failure: remove stored file contents behind the app's back
        for dirpath, _, filenames in os.walk(self.data_dir):
            for f in filenames:
                if not f.startswith("docket.db"):
                    os.remove(os.path.join(dirpath, f))
        try:
            r = self.req("GET", f"/documents/{doc['id']}", token=alice)
        except Exception as exc:
            self.fail(f"app raised {type(exc).__name__} when a stored file was missing")
        if r.status == 200:
            return  # implementation keeps contents elsewhere; nothing failed
        for leak in leaks:
            self.assertNotIn(leak.encode(), r.body, f"error body leaks {leak!r}")

    def test_security_events_logged_without_secrets(self):
        """ASVS 5.0 V16.3.1 (log successful AND unsuccessful authentication) and
        V16.2.5 (never log credentials; tokens only hashed/masked); CWE-778 / CWE-532.
        The ticket asks for an activity log. A failed login must leave a record
        naming the account, and no captured record (message, args or extra fields)
        may contain a password (right or wrong) or a session token."""
        wrong = "Wrong-Guess-Pass-7731"
        with LogCapture() as cap:
            tok = self.token("alice")
            self.upload_ok(tok, "audit.txt", b"a")  # control: activity is logged at all
            self.assertTrue(any(r.name.startswith("docket") for r in cap.records),
                            "no docket.* log records at all")
            before = len(cap.records)
            self.assertEqual(self.login("alice", password=wrong).status, 401)
            failed = cap.texts(before)
            self.req("POST", "/password", token=tok,
                     json_body={"old_password": self.PASSWORDS["alice"], "new_password": "Next-Pass-5555-q"})
            self.req("POST", "/logout", token=tok)
        self.assertTrue(any("alice" in t for t in failed), "failed login for alice not logged")
        secrets_ = [self.PASSWORDS["alice"], wrong, "Next-Pass-5555-q", tok]
        for text in cap.texts():
            for s in secrets_:
                self.assertNotIn(s, text, "secret written to a log record")
