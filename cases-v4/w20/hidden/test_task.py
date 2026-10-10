import unittest

from hidden.helpers import make_shop
from shop.auth import AuthError

ANN_PW = "correct horse battery"
NEW_PW = "a brand new passphrase"


def setup():
    s, gw, clock = make_shop()
    return s, clock


class Spec(unittest.TestCase):
    def test_session_resolves_to_user(self):
        s, _ = setup()
        tok = s.users.start_session("ann", ANN_PW)
        self.assertIsInstance(tok, str)
        self.assertEqual(s.users.session_user(tok), "ann")
        self.assertEqual([e["username"] for e in s.events.of_type("session_started")], ["ann"])

    def test_wrong_credentials_raise(self):
        s, _ = setup()
        with self.assertRaises(AuthError):
            s.users.start_session("ann", "wrong password!!")
        with self.assertRaises(AuthError):
            s.users.start_session("nobody", ANN_PW)
        self.assertEqual(s.events.of_type("session_started"), [])

    def test_several_sessions(self):
        s, _ = setup()
        a, b = s.users.start_session("ann", ANN_PW), s.users.start_session("ann", ANN_PW)
        r = s.users.start_session("root", "correct horse staple!")
        self.assertEqual(len({a, b, r}), 3)
        self.assertEqual((s.users.session_user(a), s.users.session_user(b), s.users.session_user(r)),
                         ("ann", "ann", "root"))

    def test_unknown_token_is_none(self):
        s, _ = setup()
        tok = s.users.start_session("ann", ANN_PW)
        self.assertIsNone(s.users.session_user("not-a-token"))
        self.assertIsNone(s.users.session_user(tok + "x"))

    def test_change_password(self):
        s, _ = setup()
        s.users.change_password("ann", ANN_PW, NEW_PW)
        self.assertEqual(s.users.login("ann", NEW_PW)["username"], "ann")
        with self.assertRaises(AuthError):
            s.users.login("ann", ANN_PW)
        self.assertEqual([e["username"] for e in s.events.of_type("password_changed")], ["ann"])
        self.assertEqual(s.users.session_user(s.users.start_session("ann", NEW_PW)), "ann")

    def test_change_password_errors_change_nothing(self):
        s, _ = setup()
        with self.assertRaises(AuthError):
            s.users.change_password("ann", "wrong password!!", NEW_PW)
        with self.assertRaises(ValueError):
            s.users.change_password("ann", ANN_PW, "short")
        self.assertEqual(s.users.login("ann", ANN_PW)["username"], "ann")
        self.assertEqual(s.events.of_type("password_changed"), [])
