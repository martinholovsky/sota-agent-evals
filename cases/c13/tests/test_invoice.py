import unittest
from src.invoice import invoice_total


class T(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(invoice_total([("10.00", 1)], "0.10"), "11.00")
