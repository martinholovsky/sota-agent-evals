import unittest
from src.duration import parse_duration


class T(unittest.TestCase):
    def test_one(self):
        self.assertEqual(parse_duration("1h30m"), 5400)
