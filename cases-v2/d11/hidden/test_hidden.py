import unittest
from src.window import SlidingWindowLimiter


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


class H(unittest.TestCase):
    def test_limit_and_boundary(self):
        c = Clock(); r = SlidingWindowLimiter(2, 10.0, clock=c)
        self.assertEqual([r.allow("k"), r.allow("k"), r.allow("k")], [True, True, False])
        c.t = 9.999
        self.assertFalse(r.allow("k"))
        c.t = 10.0                                 # the t=0 calls stop counting exactly now
        self.assertTrue(r.allow("k"))

    def test_denied_not_recorded(self):
        c = Clock(); r = SlidingWindowLimiter(1, 10.0, clock=c)
        r.allow("k")
        for i in range(5):
            c.t = i + 0.5
            r.allow("k")
        c.t = 10.0
        self.assertTrue(r.allow("k"))

    def test_memory_bounded(self):
        c = Clock(); r = SlidingWindowLimiter(3, 1.0, clock=c)
        for i in range(1000):
            c.t = i * 0.5
            r.allow("k")
        self.assertLessEqual(r.tracked("k"), 3)

    def test_bad_args(self):
        for lim, win in [(0, 1.0), (1, 0)]:
            with self.assertRaises(ValueError):
                SlidingWindowLimiter(lim, win)
