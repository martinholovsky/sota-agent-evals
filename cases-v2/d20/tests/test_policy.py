import unittest
from src.policy import check_password


class T(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(check_password("correct horse battery", "ann", set()), [])
