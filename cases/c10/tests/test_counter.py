import unittest
from src.counter import Counter


class T(unittest.TestCase):
    def test_single_thread(self):
        c = Counter(); c.incr(); c.incr(2)
        self.assertEqual(c.value, 3)
