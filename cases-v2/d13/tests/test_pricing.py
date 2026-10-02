import unittest
from src.pricing import order_total


class T(unittest.TestCase):
    def test_tier(self):
        self.assertEqual(order_total([(6000, 1)]), 5700)
