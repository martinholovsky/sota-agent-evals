import unittest

from shop.money import fmt, parse, pct_of
from shop.pricing import quote


class Money(unittest.TestCase):
    def test_pct_round_half_up(self):
        self.assertEqual(pct_of(250, 10), 25)
        self.assertEqual(pct_of(5, 10), 1)          # 0.5 -> 1
        self.assertEqual(pct_of(4, 10), 0)

    def test_fmt_parse(self):
        self.assertEqual(fmt(1234), "$12.34")
        self.assertEqual(fmt(-50), "-$0.50")
        self.assertEqual(parse("12.3"), 1230)
        for bad in ["", "-1", "1.234", "a"]:
            with self.assertRaises(ValueError):
                parse(bad)


class Pricing(unittest.TestCase):
    def test_order_of_operations(self):
        q = quote([(1250, 2), (800, 1)], "TEN")    # 3300, -330, tax 20% of 2970 = 594
        self.assertEqual(q, {"subtotal": 3300, "discount": 330, "tax": 594, "total": 3564})

    def test_tax_once_on_total_not_per_line(self):
        # per-line rounding would give 1+1+1 = 3; once on the total: 20% of 15 = 3
        self.assertEqual(quote([(5, 1), (5, 1), (5, 1)])["tax"], 3)
        self.assertEqual(quote([(3, 1), (3, 1)])["tax"], 1)    # 20% of 6 = 1.2 -> 1

    def test_fixed_coupon_capped(self):
        self.assertEqual(quote([(300, 1)], "FIVEOFF")["total"], 0)

    def test_unknown_coupon(self):
        with self.assertRaises(ValueError):
            quote([(100, 1)], "BOGUS")
