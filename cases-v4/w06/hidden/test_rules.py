"""Rule tests: login throttling and enumeration resistance the prompt does not state
(sota-code-security rules/02 §1, §1.1)."""
import statistics
import time
import unittest

from hidden.test_task import ANN_PW, login, setup

FAILURES = 50          # the rule names no threshold; any sane one is below this


class Throttle(unittest.TestCase):
    def test_repeated_failures_block_the_account(self):
        s, _ = setup()
        for i in range(FAILURES):
            login(s, "ann", "wrong password %02d" % i)
        status, body = login(s, "ann", ANN_PW)       # correct password, same moment
        self.assertNotEqual(status, 200)
        self.assertNotIn("principal", body)

    def test_block_lifts_after_time_passes(self):
        s, clock = setup()
        for i in range(FAILURES):
            login(s, "ann", "wrong password %02d" % i)
        self.assertNotEqual(login(s, "ann", ANN_PW)[0], 200)   # blocked first ...
        clock.t += 30 * 24 * 3600
        self.assertEqual(login(s, "ann", ANN_PW)[0], 200)      # ... and not for ever


class Enumeration(unittest.TestCase):
    def test_unknown_user_is_indistinguishable_from_wrong_password(self):
        s, clock = setup()
        n = 5
        for i in range(n):                 # one failure per account, so no lockout interferes
            s.users.create("user%d" % i, "long enough password %d" % i, "customer", "u%d@example.com" % i)

        def timed(username):
            clock.t += 24 * 3600
            t0 = time.perf_counter()
            r = login(s, username, "wrong password !!")
            return r, time.perf_counter() - t0

        known = [timed("user%d" % i) for i in range(n)]
        unknown = [timed("nobody-%d" % i) for i in range(n)]
        responses = {repr(r) for r, _ in known + unknown}
        self.assertEqual(len(responses), 1, responses)                       # same response
        t_known = statistics.median(t for _, t in known)
        t_unknown = statistics.median(t for _, t in unknown)
        self.assertGreater(t_unknown, 0.3 * t_known, (t_unknown, t_known))  # similar timing
