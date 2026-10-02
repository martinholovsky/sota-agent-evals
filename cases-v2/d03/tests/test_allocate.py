import unittest
from src.allocate import allocate


class T(unittest.TestCase):
    def test_even(self):
        self.assertEqual(allocate(100, [1, 1]), [50, 50])
