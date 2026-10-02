import unittest
from src.cache import memo


class H(unittest.TestCase):
    def test_bounded(self):
        @memo(3)
        def f(x):
            return x
        for i in range(100):
            f(i)
        self.assertEqual(f.cache_len(), 3)

    def test_lru_order(self):
        calls = []
        @memo(2)
        def f(x):
            calls.append(x); return x
        f(1); f(2); f(1); f(3)        # 2 is least recently used -> evicted
        f(1)
        self.assertEqual(calls, [1, 2, 3])
        f(2)
        self.assertEqual(calls, [1, 2, 3, 2])

    def test_bad_size(self):
        with self.assertRaises(ValueError):
            memo(0)
