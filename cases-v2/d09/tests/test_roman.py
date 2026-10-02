import unittest
from src.roman import to_roman


class T(unittest.TestCase):
    def test_one(self):
        self.assertEqual(to_roman(4), "IV")
