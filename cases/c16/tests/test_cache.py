import unittest
from src.cache import memo


class T(unittest.TestCase):
    def test_caches(self):
        calls = []
        @memo(4)
        def f(x):
            calls.append(x); return x * 2
        f(1); f(1)
        self.assertEqual(calls, [1])
