import unittest
from src.invoice import invoice_total


class H(unittest.TestCase):
    def test_half_up(self):
        self.assertEqual(invoice_total([("0.05", 1)], "0.5"), "0.08")      # 0.075 -> 0.08
        self.assertEqual(invoice_total([("1.005", 1)], "0"), "1.01")

    def test_float_trap(self):
        self.assertEqual(invoice_total([("0.10", 3)], "0"), "0.30")
        self.assertEqual(invoice_total([("19.99", 3), ("0.01", 1)], "0.21"), "72.58")
