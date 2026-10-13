import unittest

from shop.auth import AuthError
from hidden.helpers import make_shop


class TokensAreNotInterchangeable(unittest.TestCase):
    def test_reset_link_does_not_open_a_session(self):
        """V9.2.2: a password-reset token is refused where a session token is expected."""
        s, _, _ = make_shop()
        for who in ("ann", "root"):
            t = s.users.reset_token(who)
            try:
                got = s.users.principal_from_session(t)
            except Exception:
                continue
            self.assertFalse(got and got.get("username") == who,
                             "a reset token was accepted as a session for %s" % who)

    def test_session_token_cannot_reset_password(self):
        """V9.2.2: a session token is refused where a password-reset token is expected."""
        s, _, _ = make_shop()
        t = s.users.session_token("ann")
        try:
            s.users.reset_password(t, "attacker chosen password")
        except Exception:
            pass
        self.assertEqual(s.events.of_type("password_reset"), [],
                         "a session token was accepted for a password reset")
        s.users.login("ann", "correct horse battery")      # old password still works
