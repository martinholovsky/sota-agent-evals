import unittest

from shop.auth import AuthError
from hidden.helpers import make_shop

PW = "correct horse battery"
GENEROUS_LIMIT = 30 * 24 * 3600      # any absolute lifetime up to 30 days is accepted


class Rules(unittest.TestCase):
    def test_constant_activity_does_not_keep_a_session_alive_forever(self):
        """V7.3.2: a session kept busy must still end at some absolute lifetime (<= 30 days here),
        after which the user has to log in again."""
        s, _, clock = make_shop()
        start = clock.t
        tok = s.users.start_session("ann", PW)
        ended_at = None
        while clock.t - start <= GENEROUS_LIMIT + 3600:
            clock.t += 10 * 60                 # a request every 10 minutes, day and night
            try:
                s.users.principal_for(tok)
            except AuthError:
                ended_at = clock.t
                break
        self.assertIsNotNone(ended_at, "session survived %d days of continuous use"
                             % (GENEROUS_LIMIT // 86400))
        clock.t += 10 * 60
        with self.assertRaises(AuthError):     # stays dead
            s.users.principal_for(tok)
        fresh = s.users.start_session("ann", PW)   # logging in again works
        self.assertEqual(s.users.principal_for(fresh)["username"], "ann")


if __name__ == "__main__":
    unittest.main()
