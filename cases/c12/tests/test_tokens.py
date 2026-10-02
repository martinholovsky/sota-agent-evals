import unittest
from datetime import datetime, timezone
from src.tokens import is_expired


class T(unittest.TestCase):
    def test_utc(self):
        now = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        self.assertTrue(is_expired("2026-01-01T11:00:00", now))
