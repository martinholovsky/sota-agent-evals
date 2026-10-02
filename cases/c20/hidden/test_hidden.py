import unittest
from src.money import format_price
from src.report import line


class H(unittest.TestCase):
    def test_existing_behaviour(self):
        self.assertEqual(format_price(-50), "-$0.50")
        self.assertEqual(format_price(5), "$0.05")
        self.assertEqual(line("x", 100), "x: $1.00")

    def test_currencies(self):
        self.assertEqual(format_price(1234, currency="USD"), "$12.34")
        self.assertEqual(format_price(1234, currency="EUR"), "€12.34")
        self.assertEqual(format_price(-50, currency="EUR"), "-€0.50")

    def test_unknown_currency(self):
        with self.assertRaises(ValueError):
            format_price(1, currency="XYZ")
