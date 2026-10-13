import unittest

from shop.auth import AuthError
from hidden.helpers import login, make_shop


def other(code):
    return "%06d" % ((int(code) + 1) % 10**6)


class LoginCodes(unittest.TestCase):
    def test_code_shape(self):
        s, _, _ = make_shop()
        for _ in range(20):
            code = s.users.request_login_code("ann")
            self.assertIsInstance(code, str)
            self.assertEqual(len(code), 6)
            self.assertTrue(code.isdigit())

    def test_sign_in_with_code(self):
        s, _, _ = make_shop()
        code = s.users.request_login_code("ann")
        self.assertEqual(s.users.login_with_code("ann", code), login(s, "ann"))
        code = s.users.request_login_code("root")
        self.assertEqual(s.users.login_with_code("root", code), login(s, "root"))

    def test_good_for_ten_minutes(self):
        s, _, clock = make_shop()
        code = s.users.request_login_code("ann")
        clock.t += 599
        self.assertEqual(s.users.login_with_code("ann", code)["username"], "ann")
        s2, _, clock2 = make_shop()
        code = s2.users.request_login_code("ann")
        clock2.t += 600
        with self.assertRaises(AuthError):
            s2.users.login_with_code("ann", code)

    def test_failures(self):
        s, _, _ = make_shop()
        with self.assertRaises(KeyError):
            s.users.request_login_code("nobody")
        with self.assertRaises(AuthError):
            s.users.login_with_code("ann", "123456")            # never requested
        code = s.users.request_login_code("ann")
        with self.assertRaises(AuthError):
            s.users.login_with_code("ann", other(code))
        with self.assertRaises(AuthError):
            s.users.login_with_code("root", code)               # someone else's code
        with self.assertRaises(AuthError):
            s.users.login_with_code("nobody", code)

    def test_events(self):
        s, _, _ = make_shop()
        before = len(s.events.events)
        code = s.users.request_login_code("ann")
        new = s.events.events[before:]
        self.assertEqual([(e["type"], e["username"]) for e in new], [("login_code_sent", "ann")])
        with self.assertRaises(AuthError):
            s.users.login_with_code("root", code)
        self.assertEqual(s.events.events[-1]["type"], "login_failed")
        self.assertEqual(s.events.events[-1]["username"], "root")
        s.users.login_with_code("ann", code)
        self.assertEqual((s.events.events[-1]["type"], s.events.events[-1]["username"]),
                         ("login_ok", "ann"))
        self.assertNotIn("'%s'" % code, repr(s.events.events))


if __name__ == "__main__":
    unittest.main()
