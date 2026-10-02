import unittest
from src.csvline import parse_line


class T(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(parse_line("a,b,c"), ["a", "b", "c"])
