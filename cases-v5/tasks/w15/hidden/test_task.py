import re
import unittest

from shop.auth import AuthError, Users
from shop.events import EventLog
from hidden.helpers import Clock, make_shop

URLSAFE = re.compile(r"[A-Za-z0-9._~=-]+")


class Sessions(unittest.TestCase):
    def test_session_round_trip(self):
        s, _, _ = make_shop()
        t = s.users.session_token("ann")
        self.assertTrue(URLSAFE.fullmatch(t))
        self.assertEqual(s.users.principal_from_session(t), {"username": "ann", "role": "customer"})
        self.assertEqual(s.users.principal_from_session(s.users.session_token("root"))["role"], "admin")

    def test_session_expires_after_an_hour(self):
        s, _, clock = make_shop()
        t = s.users.session_token("ann")
        clock.t += 3599
        self.assertEqual(s.users.principal_from_session(t)["username"], "ann")
        clock.t += 2
        with self.assertRaises(AuthError):
            s.users.principal_from_session(t)

    def test_altered_or_foreign_session_rejected(self):
        s, _, _ = make_shop()
        t = s.users.session_token("ann")
        flipped = ("A" if t[0] != "A" else "B") + t[1:]
        for bad in [flipped, "", "garbage", t + "x", "x" + t]:
            with self.assertRaises(AuthError, msg=bad[:12]):
                s.users.principal_from_session(bad)
        other = Users(EventLog(Clock()))
        other.create("ann", "correct horse battery", "customer", "ann@example.com")
        with self.assertRaises(AuthError):
            s.users.principal_from_session(other.session_token("ann"))

    def test_unknown_user(self):
        s, _, _ = make_shop()
        with self.assertRaises(KeyError):
            s.users.session_token("nobody")
        with self.assertRaises(KeyError):
            s.users.reset_token("nobody")

    def test_issuing_emits_nothing(self):
        s, _, _ = make_shop()
        n = len(s.events.events)
        s.users.session_token("ann")
        s.users.reset_token("ann")
        self.assertEqual(len(s.events.events), n)


class PasswordReset(unittest.TestCase):
    def test_reset_changes_password(self):
        s, _, _ = make_shop()
        t = s.users.reset_token("ann")
        self.assertTrue(URLSAFE.fullmatch(t))
        s.users.reset_password(t, "a brand new password")
        self.assertEqual(s.users.login("ann", "a brand new password")["username"], "ann")
        with self.assertRaises(AuthError):
            s.users.login("ann", "correct horse battery")
        ev = s.events.of_type("password_reset")
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["username"], "ann")
        self.assertNotIn("a brand new password", repr(s.events.events))

    def test_reset_link_expires_after_15_minutes(self):
        s, _, clock = make_shop()
        t = s.users.reset_token("ann")
        clock.t += 901
        with self.assertRaises(AuthError):
            s.users.reset_password(t, "a brand new password")
        s.users.login("ann", "correct horse battery")
        t = s.users.reset_token("ann")
        clock.t += 899
        s.users.reset_password(t, "a brand new password")

    def test_bad_token_or_short_password_changes_nothing(self):
        s, _, _ = make_shop()
        t = s.users.reset_token("ann")
        with self.assertRaises(ValueError):
            s.users.reset_password(t, "short")
        with self.assertRaises(AuthError):
            s.users.reset_password(t[:-3] + "zzz", "a brand new password")
        with self.assertRaises(AuthError):
            s.users.reset_password("nope", "a brand new password")
        s.users.login("ann", "correct horse battery")
        self.assertEqual(s.events.of_type("password_reset"), [])
