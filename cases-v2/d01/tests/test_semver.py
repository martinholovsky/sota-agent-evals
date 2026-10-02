import unittest
from src.semver import compare


class T(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(compare("1.2.3", "1.10.0"), -1)
