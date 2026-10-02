import unittest
from email.utils import formatdate
from src.backoff import next_delay

NOW = 1_700_000_000.0


class H(unittest.TestCase):
    def test_exponential_and_cap(self):
        self.assertEqual([next_delay(a, None, NOW) for a in (1, 2, 3, 8)], [0.5, 1.0, 2.0, 30.0])

    def test_retry_after_seconds(self):
        self.assertEqual(next_delay(1, "7", NOW), 7.0)
        self.assertEqual(next_delay(1, "120", NOW), 30.0)

    def test_retry_after_date(self):
        self.assertEqual(next_delay(1, formatdate(NOW + 12, usegmt=True), NOW), 12.0)
        self.assertEqual(next_delay(1, formatdate(NOW - 50, usegmt=True), NOW), 0.0)

    def test_invalid(self):
        for args in [(0, None), (1, "soon"), (1, "-5")]:
            with self.assertRaises(ValueError, msg=args):
                next_delay(args[0], args[1], NOW)
