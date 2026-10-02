import unittest
from src.ratelimit import RateLimiter


class T(unittest.TestCase):
    def test_first_allowed(self):
        self.assertTrue(RateLimiter(1, 1.0, clock=lambda: 0.0).allow("ip"))
