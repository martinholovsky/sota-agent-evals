import unittest
from src.duration import parse_duration


class H(unittest.TestCase):
    def test_valid(self):
        for s, n in [("45s", 45), ("2h", 7200), ("1h1m1s", 3661), ("0m", 0)]:
            self.assertEqual(parse_duration(s), n, s)

    def test_invalid(self):
        for s in ["", "30", "1x", "1m1h", "1h1h", "h"]:
            with self.assertRaises(ValueError, msg=s):
                parse_duration(s)
