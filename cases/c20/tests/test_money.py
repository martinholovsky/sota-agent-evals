import unittest
from src.money import format_price
from src.report import line


class T(unittest.TestCase):
    def test_default(self):
        self.assertEqual(format_price(1234), "$12.34")
        self.assertEqual(line("tea", 250), "tea: $2.50")
