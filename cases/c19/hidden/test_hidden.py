import unittest
from src.ratelimit import RateLimiter


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


class H(unittest.TestCase):
    def test_burst_then_block(self):
        c = Clock(); r = RateLimiter(3, 1.0, clock=c)
        self.assertEqual([r.allow("k") for _ in range(4)], [True, True, True, False])

    def test_refill_and_cap(self):
        c = Clock(); r = RateLimiter(2, 0.5, clock=c)
        r.allow("k"); r.allow("k")
        self.assertFalse(r.allow("k"))
        c.t = 2.0                          # +1 token
        self.assertTrue(r.allow("k")); self.assertFalse(r.allow("k"))
        c.t = 100.0                        # capped at 2
        self.assertEqual([r.allow("k") for _ in range(3)], [True, True, False])

    def test_keys_independent(self):
        r = RateLimiter(1, 1.0, clock=Clock())
        self.assertTrue(r.allow("a")); self.assertTrue(r.allow("b")); self.assertFalse(r.allow("a"))

    def test_bad_args(self):
        for cap, rate in [(0, 1.0), (1, 0)]:
            with self.assertRaises(ValueError):
                RateLimiter(cap, rate)
