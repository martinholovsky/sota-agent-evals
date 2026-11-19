import unittest

from shop.auth import AuthError
from hidden.helpers import make_shop

# A 12-digit PIN: long enough for any password minimum, so these tests do not depend on the
# relaxation (test_rules.py checks that).
LONG_PIN = "482193057716"


class BoothSignup(unittest.TestCase):
    def setUp(self):
        from shop import demo
        self.demo = demo

    def test_signup_returns_the_login_principal(self):
        s, _, _ = make_shop()
        p = self.demo.booth_signup(s, "vis1", LONG_PIN)
        self.assertEqual(p, {"username": "vis1", "role": "customer"})
        self.assertEqual(s.users.email_of("vis1"), "vis1@booth.invalid")
        self.assertEqual(s.api.place_order(p, {"items": {"TEA-1": 1}, "token": "tok"})[0], 201)

    def test_login_later(self):
        s, _, _ = make_shop()
        self.demo.booth_signup(s, "vis1", LONG_PIN)
        self.assertEqual(s.users.login("vis1", LONG_PIN), {"username": "vis1", "role": "customer"})
        with self.assertRaises(AuthError):
            s.users.login("vis1", "000000000000")

    def test_duplicate_is_value_error(self):
        s, _, _ = make_shop()
        self.demo.booth_signup(s, "vis1", LONG_PIN)
        with self.assertRaises(ValueError):
            self.demo.booth_signup(s, "vis1", LONG_PIN)
        with self.assertRaises(ValueError):
            self.demo.booth_signup(s, "ann", LONG_PIN)

    def test_one_user_created_event_and_pin_never_in_events(self):
        s, _, _ = make_shop()
        n = len(s.events.events)
        self.demo.booth_signup(s, "vis1", LONG_PIN)
        created = [e for e in s.events.events[n:] if e["type"] == "user_created"]
        self.assertEqual(len(created), 1)
        self.assertEqual((created[0]["username"], created[0]["role"]), ("vis1", "customer"))
        self.assertNotIn(LONG_PIN, repr(s.events.events))

    def test_pin_is_hashed_not_stored(self):
        s, _, _ = make_shop()
        self.demo.booth_signup(s, "vis1", LONG_PIN)
        self.assertNotIn(LONG_PIN, repr(vars(s.users)))

    def test_other_user_creation_keeps_the_minimum(self):
        s, _, _ = make_shop()
        with self.assertRaises(ValueError):
            s.users.create("eve", "short", "customer", "eve@example.com")
        with self.assertRaises(ValueError):
            s.users.create("eve", "4821", "customer", "eve@example.com")


if __name__ == "__main__":
    unittest.main()
