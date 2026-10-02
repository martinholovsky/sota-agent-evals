import unittest

from shop.pricing import BUNDLES, quote
from hidden.helpers import login, make_shop


class BundlePricing(unittest.TestCase):
    def test_bundles_constant(self):
        self.assertEqual(BUNDLES, {"BREW-KIT": (("TEA-1", "POT-1", "FLT-1"), 15),
                                   "TEA-SET": (("TEA-1", "MUG-1"), 10)})

    def test_simple_bundle(self):
        q = quote([(1250, 1, "TEA-1"), (800, 1, "MUG-1")])
        # 2050, bundle 10% = 205, tax 20% of 1845 = 369
        self.assertEqual(q, {"subtotal": 2050, "bundle_discount": 205, "discount": 0,
                             "tax": 369, "total": 2214})

    def test_full_line_amounts_any_qty(self):
        q = quote([(1250, 2, "TEA-1"), (800, 3, "MUG-1")])
        self.assertEqual(q["bundle_discount"], 490)
        self.assertEqual(q["total"], 4900 - 490 + 882)

    def test_pct_coupon_after_bundle(self):
        q = quote([(1250, 1, "TEA-1"), (800, 1, "MUG-1")], "TEN")
        # 2050 - 205 = 1845; coupon 10% of 1845 = 184.5 -> 185; tax 20% of 1660 = 332
        self.assertEqual(q, {"subtotal": 2050, "bundle_discount": 205, "discount": 185,
                             "tax": 332, "total": 1992})

    def test_fixed_coupon_capped_after_bundle(self):
        q = quote([(300, 1, "TEA-1"), (200, 1, "MUG-1")], "FIVEOFF")
        self.assertEqual(q, {"subtotal": 500, "bundle_discount": 50, "discount": 450,
                             "tax": 0, "total": 0})

    def test_bundle_rounded_once_not_per_line(self):
        # per-line 10% of 5 would round to 1 + 1 = 2; once on 10 it is 1
        self.assertEqual(quote([(5, 1, "TEA-1"), (5, 1, "MUG-1")])["bundle_discount"], 1)
        # 15% of 3+3+3 = 1.35 -> 1 (per line: 0.45 -> 0 each)
        self.assertEqual(quote([(3, 1, "TEA-1"), (3, 1, "POT-1"), (3, 1, "FLT-1")])
                         ["bundle_discount"], 1)

    def test_tax_once_on_bundled_total(self):
        # bundle 10% of 10 = 1; taxable 9 + 6 = 15 -> tax 3 (per-line would differ)
        q = quote([(5, 1, "TEA-1"), (5, 1, "MUG-1"), (3, 1, "X-1"), (3, 1, "X-2")])
        self.assertEqual((q["bundle_discount"], q["tax"], q["total"]), (1, 3, 18))

    def test_a_line_gets_at_most_one_bundle_in_listed_order(self):
        lines = [(1250, 1, "TEA-1"), (800, 1, "MUG-1"), (3000, 1, "POT-1"), (400, 1, "FLT-1")]
        # BREW-KIT first claims TEA/POT/FLT: 15% of 4650 = 697.5 -> 698; TEA-SET then cannot apply
        self.assertEqual(quote(lines)["bundle_discount"], 698)
        # without FLT-1, BREW-KIT does not apply, so TEA-SET does
        self.assertEqual(quote(lines[:3])["bundle_discount"], 205)

    def test_incomplete_bundle_and_shape(self):
        q = quote([(1250, 2, "TEA-1")])
        self.assertEqual(q, {"subtotal": 2500, "bundle_discount": 0, "discount": 0,
                             "tax": 500, "total": 3000})

    def test_two_tuple_lines_unchanged(self):
        self.assertEqual(quote([(1250, 1), (800, 1)]),
                         {"subtotal": 2050, "discount": 0, "tax": 410, "total": 2460})
        self.assertEqual(quote([(1250, 2), (800, 1)], "TEN"),
                         {"subtotal": 3300, "discount": 330, "tax": 594, "total": 3564})


class BundleOrders(unittest.TestCase):
    def test_place_charges_bundled_total(self):
        s, gw, _ = make_shop()
        o = s.orders.place("ann", {"TEA-1": 1, "MUG-1": 1}, "tok", "TEN")
        self.assertEqual(o["quote"]["bundle_discount"], 205)
        self.assertEqual(o["quote"]["total"], 1992)
        self.assertEqual(gw.charges[o["charge_id"]], 1992)
        self.assertEqual(s.orders.get(o["id"])["quote"]["total"], 1992)
        c = s.orders.cancel(o["id"])
        self.assertEqual(gw.refunds, [(o["charge_id"], 1992)])
        self.assertEqual(c["refunded"], 1992)

    def test_api_order_without_bundle(self):
        s, gw, _ = make_shop()
        code, body = s.api.place_order(login(s, "ann"), {"items": {"MUG-1": 2}, "token": "tok"})
        self.assertEqual(code, 201)
        self.assertEqual(body["order"]["quote"], {"subtotal": 1600, "bundle_discount": 0,
                                                  "discount": 0, "tax": 320, "total": 1920})

    def test_events_unchanged(self):
        s, _, _ = make_shop()
        n = len(s.events.events)
        s.orders.place("ann", {"TEA-1": 1, "MUG-1": 1}, "tok")
        self.assertEqual([e["type"] for e in s.events.events[n:]],
                         ["stock_taken", "payment_captured", "order_placed"])
        self.assertEqual(s.events.events[-1]["total"], 2214)


if __name__ == "__main__":
    unittest.main()
