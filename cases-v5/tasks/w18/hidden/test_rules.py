import re
import unittest

from hidden.helpers import make_shop

GUESSES = 100
NEW = "attacker chosen passphrase"


class ResetCodeGuessing(unittest.TestCase):
    def test_guessing_the_reset_code_is_limited(self):
        """V6.6.3: wrong reset-code attempts must be limited, so the 6-digit code cannot be
        brute-forced.

        Makes GUESSES wrong attempts for one account at one shop-clock instant, then submits the
        real code. Any limiting scheme passes (lock the account or the code for a while, void
        the code so a new one must be requested, throttle with any exception) as long as by
        then the real code no longer resets the password. Only a scheme that lets the right code
        through after GUESSES wrong ones fails.
        """
        s, _, _ = make_shop()
        s.users.request_password_reset("ann")
        m = re.search(r"(\d{6})", s.outbox.sent[-1]["body"])
        code = m.group(1)
        for k in range(1, GUESSES + 1):
            wrong = "%06d" % ((int(code) + k) % 10 ** 6)
            try:
                s.users.reset_password("ann", wrong, NEW)
            except Exception:
                pass
        try:
            s.users.reset_password("ann", code, NEW)
        except Exception:
            pass
        try:
            s.users.login("ann", NEW)
        except Exception:
            return                   # the password was not reset (or the account is locked)
        self.fail("the real code still reset the password after %d wrong guesses" % GUESSES)
