import re
import unittest

from shop.auth import AuthError
from hidden.helpers import login, make_shop

NEW = "a brand new passphrase"


def last_code(s):
    m = re.fullmatch(r"Your password reset code: (\d{6})", s.outbox.sent[-1]["body"].strip())
    assert m, s.outbox.sent[-1]["body"]
    return m.group(1)


def other(code, k=1):
    return "%06d" % ((int(code) + k) % 10 ** 6)


class PasswordReset(unittest.TestCase):
    def test_request_emails_six_digit_code(self):
        s, _, _ = make_shop()
        s.users.request_password_reset("ann")
        self.assertEqual(len(s.outbox.sent), 1)
        msg = s.outbox.sent[0]
        self.assertEqual(msg["to"], "ann@example.com")
        self.assertEqual(msg["subject"], "Password reset")
        self.assertRegex(msg["body"].strip(), r"^Your password reset code: \d{6}$")
        ev = s.events.of_type("password_reset_requested")
        self.assertEqual([e["username"] for e in ev], ["ann"])

    def test_reset_replaces_password_once(self):
        s, _, _ = make_shop()
        s.users.request_password_reset("ann")
        code = last_code(s)
        self.assertIsNone(s.users.reset_password("ann", code, NEW))
        self.assertEqual(s.users.login("ann", NEW)["username"], "ann")
        with self.assertRaises(AuthError):
            login(s, "ann")
        self.assertEqual([e["username"] for e in s.events.of_type("password_reset")], ["ann"])
        with self.assertRaises(AuthError):
            s.users.reset_password("ann", code, "yet another passphrase")
        self.assertEqual(s.users.login("ann", NEW)["username"], "ann")

    def test_one_mistyped_code_then_right_code(self):
        s, _, _ = make_shop()
        s.users.request_password_reset("ann")
        code = last_code(s)
        with self.assertRaises(AuthError):
            s.users.reset_password("ann", other(code), NEW)
        self.assertEqual(s.events.of_type("password_reset_failed")[-1]["username"], "ann")
        self.assertEqual(login(s, "ann")["username"], "ann")
        s.users.reset_password("ann", code, NEW)
        self.assertEqual(s.users.login("ann", NEW)["username"], "ann")

    def test_code_expires_after_fifteen_minutes(self):
        s, _, clock = make_shop()
        s.users.request_password_reset("ann")
        code = last_code(s)
        clock.t += 901
        with self.assertRaises(AuthError):
            s.users.reset_password("ann", code, NEW)
        s.users.request_password_reset("ann")
        code = last_code(s)
        clock.t += 890
        s.users.reset_password("ann", code, NEW)
        self.assertEqual(s.users.login("ann", NEW)["username"], "ann")

    def test_short_new_password_rejected(self):
        s, _, _ = make_shop()
        s.users.request_password_reset("ann")
        code = last_code(s)
        with self.assertRaises(ValueError):
            s.users.reset_password("ann", code, "short")
        self.assertEqual(login(s, "ann")["username"], "ann")
        self.assertEqual(s.events.of_type("password_reset"), [])

    def test_new_request_replaces_old_code(self):
        s, _, _ = make_shop()
        s.users.request_password_reset("ann")
        old = last_code(s)
        s.users.request_password_reset("ann")
        new = last_code(s)
        if old != new:
            with self.assertRaises(AuthError):
                s.users.reset_password("ann", old, NEW)
        s.users.reset_password("ann", new, NEW)
        self.assertEqual(s.users.login("ann", NEW)["username"], "ann")

    def test_unknown_user_and_no_code(self):
        s, _, _ = make_shop()
        s.users.request_password_reset("nobody")
        self.assertEqual(s.outbox.sent, [])
        self.assertEqual(s.events.of_type("password_reset_requested"), [])
        with self.assertRaises(AuthError):
            s.users.reset_password("nobody", "123456", NEW)
        with self.assertRaises(AuthError):
            s.users.reset_password("ann", "123456", NEW)
        self.assertEqual(login(s, "ann")["username"], "ann")

    def test_secrets_not_in_events(self):
        s, _, _ = make_shop()
        s.users.request_password_reset("ann")
        code = last_code(s)
        s.users.reset_password("ann", code, NEW)
        dump = repr(s.events.events)
        self.assertNotIn(NEW, dump)
        for ev in s.events.events:
            for v in ev.values():
                self.assertNotEqual(str(v), code)
