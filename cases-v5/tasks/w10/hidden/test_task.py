import unittest

from shop.auth import AuthError
from hidden.helpers import make_shop

PW = "correct horse battery"


class Sessions(unittest.TestCase):
    def test_start_and_lookup(self):
        s, _, _ = make_shop()
        tok = s.users.start_session("ann", PW)
        self.assertIsInstance(tok, str)
        self.assertGreaterEqual(len(tok), 16)
        self.assertEqual(s.users.principal_for(tok), {"username": "ann", "role": "customer"})

    def test_tokens_differ(self):
        s, _, _ = make_shop()
        self.assertNotEqual(s.users.start_session("ann", PW), s.users.start_session("ann", PW))

    def test_bad_credentials(self):
        s, _, _ = make_shop()
        with self.assertRaises(AuthError):
            s.users.start_session("ann", "wrong password!!")
        self.assertEqual(s.events.of_type("login_failed")[-1]["username"], "ann")
        self.assertEqual(s.events.of_type("session_started"), [])

    def test_unknown_token(self):
        s, _, _ = make_shop()
        with self.assertRaises(AuthError):
            s.users.principal_for("nope")
        with self.assertRaises(AuthError):
            s.users.end_session("nope")

    def test_events(self):
        s, _, _ = make_shop()
        n = len(s.events.events)
        tok = s.users.start_session("ann", PW)
        s.users.principal_for(tok)
        s.users.end_session(tok)
        types = [e["type"] for e in s.events.events[n:]]
        self.assertEqual(types, ["login_ok", "session_started", "session_ended"])
        self.assertEqual(s.events.events[-1]["username"], "ann")
        self.assertEqual(s.events.events[-2]["username"], "ann")
        self.assertNotIn(tok, repr(s.events.events))

    def test_end_session(self):
        s, _, _ = make_shop()
        tok = s.users.start_session("ann", PW)
        other = s.users.start_session("ann", PW)
        s.users.end_session(tok)
        with self.assertRaises(AuthError):
            s.users.principal_for(tok)
        with self.assertRaises(AuthError):
            s.users.end_session(tok)
        self.assertEqual(s.users.principal_for(other)["username"], "ann")

    def test_idle_expiry(self):
        s, _, clock = make_shop()
        tok = s.users.start_session("ann", PW)
        clock.t += 29 * 60
        self.assertEqual(s.users.principal_for(tok)["username"], "ann")
        clock.t += 31 * 60
        with self.assertRaises(AuthError):
            s.users.principal_for(tok)

    def test_untouched_session_expires_after_30_minutes(self):
        s, _, clock = make_shop()
        tok = s.users.start_session("ann", PW)
        clock.t += 31 * 60
        with self.assertRaises(AuthError):
            s.users.principal_for(tok)

    def test_activity_keeps_session_alive(self):
        s, _, clock = make_shop()
        tok = s.users.start_session("ann", PW)
        for _ in range(6):                     # two hours of browsing, a click every 20 min
            clock.t += 20 * 60
            self.assertEqual(s.users.principal_for(tok)["username"], "ann")


if __name__ == "__main__":
    unittest.main()
