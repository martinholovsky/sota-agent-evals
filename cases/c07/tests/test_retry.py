import unittest
from src.retry import retry


class T(unittest.TestCase):
    def test_success(self):
        self.assertEqual(retry(lambda: 5, sleep=lambda s: None), 5)
