import unittest
from src.cart import cart_total


class T(unittest.TestCase):
    def test_total(self):
        self.assertEqual(cart_total([(2, 150, 0), (1, 999, 10)]), 1199)
