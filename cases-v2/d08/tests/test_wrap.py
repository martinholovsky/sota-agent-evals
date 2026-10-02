import unittest
from src.wrap import wrap


class T(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(wrap("aa bb cc", 5), "aa bb\ncc")
