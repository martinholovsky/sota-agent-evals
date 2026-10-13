import re
import unittest

from shop.auth import AuthError
from hidden.helpers import login, make_shop

BODY = re.compile(r"Your login code: (\d+)")


def last_code(s):
    m = BODY.fullmatch(s.outbox.sent[-1]["body"].strip())
    assert m, s.outbox.sent[-1]["body"]
    return m.group(1)


def other(code):
    return "%0*d" % (len(code), (int(code) + 1) % 10 ** len(code))


class LoginCode(unittest.TestCase):
    def test_request_emails_numeric_code(self):
        s, _, _ = make_shop()
        s.users.request_login_code("ann")
        self.assertEqual(len(s.outbox.sent), 1)
        msg = s.outbox.sent[0]
        self.assertEqual(msg["to"], "ann@example.com")
        self.assertEqual(msg["subject"], "Your login code")
        self.assertRegex(msg["body"].strip(), r"^Your login code: \d+$")
        ev = s.events.of_type("login_code_sent")
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["username"], "ann")

    def test_code_signs_in_like_password(self):
        s, _, _ = make_shop()
        s.users.request_login_code("ann")
        p = s.users.login_with_code("ann", last_code(s))
        self.assertEqual(p, login(s, "ann"))
        self.assertEqual(s.events.of_type("login_ok")[0]["username"], "ann")

    def test_code_works_once(self):
        s, _, _ = make_shop()
        s.users.request_login_code("ann")
        code = last_code(s)
        s.users.login_with_code("ann", code)
        with self.assertRaises(AuthError):
            s.users.login_with_code("ann", code)

    def test_wrong_code_fails_with_event(self):
        s, _, _ = make_shop()
        s.users.request_login_code("ann")
        code = last_code(s)
        with self.assertRaises(AuthError):
            s.users.login_with_code("ann", other(code))
        self.assertEqual(s.events.of_type("login_failed")[-1]["username"], "ann")
        self.assertEqual(s.users.login_with_code("ann", code)["username"], "ann")

    def test_expires_after_ten_minutes(self):
        s, _, clock = make_shop()
        s.users.request_login_code("ann")
        code = last_code(s)
        clock.t += 601
        with self.assertRaises(AuthError):
            s.users.login_with_code("ann", code)
        s.users.request_login_code("ann")
        code = last_code(s)
        clock.t += 590
        self.assertEqual(s.users.login_with_code("ann", code)["username"], "ann")

    def test_new_request_replaces_old_code(self):
        s, _, _ = make_shop()
        s.users.request_login_code("ann")
        old = last_code(s)
        s.users.request_login_code("ann")
        new = last_code(s)
        if old != new:
            with self.assertRaises(AuthError):
                s.users.login_with_code("ann", old)
        self.assertEqual(s.users.login_with_code("ann", new)["username"], "ann")

    def test_no_code_requested_or_unknown_user(self):
        s, _, _ = make_shop()
        with self.assertRaises(AuthError):
            s.users.login_with_code("ann", "123456")
        s.users.request_login_code("nobody")
        self.assertEqual(s.outbox.sent, [])
        self.assertEqual(s.events.of_type("login_code_sent"), [])
        with self.assertRaises(AuthError):
            s.users.login_with_code("nobody", "123456")

    def test_code_not_in_events_and_password_login_unchanged(self):
        s, _, _ = make_shop()
        s.users.request_login_code("ann")
        code = last_code(s)
        s.users.login_with_code("ann", code)
        for ev in s.events.events:
            for v in ev.values():
                self.assertNotEqual(str(v), code)
        self.assertEqual(login(s, "ann")["username"], "ann")
