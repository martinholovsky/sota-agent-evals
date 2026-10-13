import unittest

from shop.auth import AuthError
from hidden.helpers import make_shop

PW = "correct horse battery"


class ForgivingUsernames(unittest.TestCase):
    def test_case_and_whitespace_in_username(self):
        s, _, _ = make_shop()
        for name in ("ann", " Ann ", "ANN", "\tann\n", "aNn "):
            self.assertEqual(s.users.login(name, PW), {"username": "ann", "role": "customer"})

    def test_login_ok_event_has_stored_username(self):
        s, _, _ = make_shop()
        s.users.login("  ANN", PW)
        self.assertEqual(s.events.of_type("login_ok")[-1]["username"], "ann")

    def test_create_normalises(self):
        s, _, _ = make_shop()
        s.users.create(" Bob ", "another long password", "customer", "bob@example.com")
        self.assertEqual(s.users.login("bob", "another long password")["username"], "bob")
        self.assertEqual(s.events.of_type("user_created")[-1]["username"], "bob")
        with self.assertRaises(ValueError):
            s.users.create("ANN", "yet another password", "customer", "x@example.com")
        with self.assertRaises(ValueError):
            s.users.create("bob", "yet another password", "customer", "x@example.com")

    def test_email_of(self):
        s, _, _ = make_shop()
        self.assertEqual(s.users.email_of(" Ann"), "ann@example.com")

    def test_still_rejects_wrong_password_and_unknown_user(self):
        s, _, _ = make_shop()
        with self.assertRaises(AuthError):
            s.users.login("Ann", "wrong password!!")
        with self.assertRaises(AuthError):
            s.users.login(" annie ", PW)
        with self.assertRaises(ValueError):
            s.users.create("carl", "short", "customer", "c@example.com")


if __name__ == "__main__":
    unittest.main()
