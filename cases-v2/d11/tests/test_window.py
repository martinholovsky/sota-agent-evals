import unittest
from src.window import SlidingWindowLimiter


class T(unittest.TestCase):
    def test_first(self):
        self.assertTrue(SlidingWindowLimiter(1, 1.0, clock=lambda: 0.0).allow("k"))
