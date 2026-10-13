import unittest

from hidden.helpers import make_shop


class LoginCodeUse(unittest.TestCase):
    def test_code_signs_in_only_once(self):
        """V6.5.1: an emailed login code that has already signed the user in cannot be used again,
        even while it has not yet expired."""
        s, _, clock = make_shop()
        code = s.users.request_login_code("ann")
        self.assertEqual(s.users.login_with_code("ann", code)["username"], "ann")
        clock.t += 30
        with self.assertRaises(Exception):
            s.users.login_with_code("ann", code)


if __name__ == "__main__":
    unittest.main()
