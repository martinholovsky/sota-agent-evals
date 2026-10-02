import unittest
from src.http_range import parse_range


class T(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(parse_range("bytes=0-499", 1000), [(0, 499)])
