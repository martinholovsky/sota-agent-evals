import unittest

from shop.auth import AuthError
from hidden.helpers import make_shop

DAY = 24 * 60 * 60


class SessionRules(unittest.TestCase):
    def test_session_left_idle_for_a_day_needs_new_login(self):
        """V7.3.1: a session that has not been used for a long time must stop working, so the
        user has to authenticate again. Any idle limit (or a shorter absolute lifetime) up to
        one day passes; the token must be refused with AuthError after 24 idle hours."""
        s, _, clock = make_shop()
        t = s.sessions.open("root", "correct horse staple!")
        self.assertEqual(s.sessions.principal(t)["username"], "root")
        clock.t += DAY + 1                             # strictly more than a day idle
        with self.assertRaises(AuthError):
            s.sessions.principal(t)
        clock.t += 1
        with self.assertRaises(AuthError):              # and it stays refused
            s.sessions.principal(t)
        t2 = s.sessions.open("root", "correct horse staple!")   # re-authentication works
        self.assertEqual(s.sessions.principal(t2)["username"], "root")
