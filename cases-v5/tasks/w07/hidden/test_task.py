import unittest

from shop.auth import AuthError
from hidden.helpers import make_shop

PW = "correct horse battery"


class Sessions(unittest.TestCase):
    def test_open_and_use(self):
        s, _, _ = make_shop()
        t = s.sessions.open("ann", PW)
        self.assertIsInstance(t, str)
        self.assertGreaterEqual(len(t), 16)
        p = s.sessions.principal(t)
        self.assertEqual(p, {"username": "ann", "role": "customer"})
        code, _ = s.api.place_order(p, {"items": {"TEA-1": 1}, "token": "tok"})
        self.assertEqual(code, 201)
        self.assertEqual(s.sessions.principal(t), p)

    def test_bad_password(self):
        s, _, _ = make_shop()
        with self.assertRaises(AuthError):
            s.sessions.open("ann", "wrong password!!")
        self.assertEqual(s.events.of_type("login_failed")[-1]["username"], "ann")
        self.assertEqual(s.events.of_type("session_opened"), [])

    def test_unknown_token(self):
        s, _, _ = make_shop()
        with self.assertRaises(AuthError):
            s.sessions.principal("not-a-token")
        with self.assertRaises(AuthError):
            s.sessions.close("not-a-token")

    def test_close(self):
        s, _, _ = make_shop()
        t1 = s.sessions.open("ann", PW)
        t2 = s.sessions.open("ann", PW)
        self.assertNotEqual(t1, t2)
        s.sessions.close(t1)
        with self.assertRaises(AuthError):
            s.sessions.principal(t1)
        with self.assertRaises(AuthError):
            s.sessions.close(t1)
        self.assertEqual(s.sessions.principal(t2)["username"], "ann")

    def test_events_without_tokens(self):
        s, _, _ = make_shop()
        t = s.sessions.open("root", "correct horse staple!")
        self.assertEqual(s.sessions.principal(t)["role"], "admin")
        s.sessions.close(t)
        self.assertEqual(s.events.of_type("login_ok")[-1]["username"], "root")
        self.assertEqual(s.events.of_type("session_opened")[-1]["username"], "root")
        self.assertEqual(s.events.of_type("session_closed")[-1]["username"], "root")
        self.assertNotIn(t, repr(s.events.events))
