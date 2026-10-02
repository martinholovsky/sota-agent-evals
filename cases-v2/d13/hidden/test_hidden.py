import unittest
from src.pricing import order_total


class H(unittest.TestCase):
    def test_tier_boundaries(self):
        self.assertEqual(order_total([(5000, 1)]), 4750)
        self.assertEqual(order_total([(10000, 1)]), 9000)
        self.assertEqual(order_total([(4999, 1)]), 4999)

    def test_coupons(self):
        self.assertEqual(order_total([(10000, 1)], "SAVE500"), 8500)
        self.assertEqual(order_total([(1001, 1)], "HALF"), 501)     # 1001 - 500 (rounded down)

    def test_floor_zero(self):
        self.assertEqual(order_total([(300, 1)], "SAVE500"), 0)

    def test_unknown_coupon(self):
        with self.assertRaises(ValueError):
            order_total([(100, 1)], "BOGUS")
