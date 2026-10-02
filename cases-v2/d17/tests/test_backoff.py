import unittest
from src.backoff import next_delay


class T(unittest.TestCase):
    def test_exp(self):
        self.assertEqual(next_delay(1, None, 0.0), 0.5)
