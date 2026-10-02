import unittest
from src.intervals import merge


class T(unittest.TestCase):
    def test_overlap(self):
        self.assertEqual(merge([(1, 4), (2, 6)]), [(1, 6)])
