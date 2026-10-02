import unittest
from src.http_range import parse_range


class H(unittest.TestCase):
    def test_forms(self):
        self.assertEqual(parse_range("bytes=500-", 1000), [(500, 999)])
        self.assertEqual(parse_range("bytes=-200", 1000), [(800, 999)])
        self.assertEqual(parse_range("bytes=-5000", 1000), [(0, 999)])
        self.assertEqual(parse_range("bytes=900-5000", 1000), [(900, 999)])

    def test_multi_and_spaces(self):
        self.assertEqual(parse_range("bytes=0-0, -1", 10), [(0, 0), (9, 9)])

    def test_unsatisfiable(self):
        self.assertEqual(parse_range("bytes=0-1,2000-3000", 1000), [(0, 1)])
        with self.assertRaises(ValueError):
            parse_range("bytes=1000-", 1000)

    def test_invalid(self):
        for h in ["items=0-1", "bytes=5-1", "bytes=-0", "bytes=a-b", "bytes=-", "bytes=", "bytes=1"]:
            with self.assertRaises(ValueError, msg=h):
                parse_range(h, 1000)
