import unittest
from datetime import datetime, timedelta, timezone
from src.tokens import is_expired

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


class H(unittest.TestCase):
    def test_offset(self):
        self.assertFalse(is_expired("2026-01-01T13:30:00+01:00", NOW))   # 12:30Z
        self.assertTrue(is_expired("2026-01-01T12:30:00+01:00", NOW))    # 11:30Z

    def test_z_and_naive(self):
        self.assertTrue(is_expired("2026-01-01T12:00:00Z", NOW))
        self.assertFalse(is_expired("2026-01-01T12:00:01", NOW))

    def test_now_in_other_zone(self):
        now = NOW.astimezone(timezone(timedelta(hours=-5)))
        self.assertFalse(is_expired("2026-01-01T12:00:01Z", now))
