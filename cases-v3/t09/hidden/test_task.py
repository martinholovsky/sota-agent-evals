import unittest

from shop.reports import orders_csv, sales_summary
from hidden.helpers import login, make_shop


class PriceChangeAfterOrder(unittest.TestCase):
    def test_price_increase_then_cancel_refunds_what_was_charged(self):
        s, gw, _ = make_shop()
        o = s.orders.place("ann", {"TEA-1": 2}, "tok")                # 3000
        s.catalog.set_price("TEA-1", 1500)
        c = s.orders.cancel(o["id"])
        self.assertEqual(c["status"], "cancelled")
        self.assertEqual(c["refunded"], 3000)
        self.assertEqual(gw.refunds, [(o["charge_id"], 3000)])
        self.assertEqual(s.inventory.available("TEA-1"), 10)

    def test_price_decrease_then_cancel_refunds_in_full(self):
        s, gw, _ = make_shop()
        o = s.orders.place("ann", {"MUG-1": 2}, "tok")                # 1920
        s.catalog.set_price("MUG-1", 500)
        c = s.orders.cancel(o["id"])
        self.assertEqual((c["refunded"], gw.refunds), (1920, [(o["charge_id"], 1920)]))

    def test_coupon_order_and_api_cancel(self):
        s, gw, _ = make_shop()
        o = s.orders.place("ann", {"TEA-1": 2, "MUG-1": 1}, "tok", "TEN")   # 3564
        s.catalog.set_price("TEA-1", 999)
        s.catalog.set_price("MUG-1", 4000)
        code, body = s.api.cancel_order(login(s, "root"), {"id": o["id"]})
        self.assertEqual(code, 200)
        self.assertEqual(body["order"]["refunded"], 3564)
        self.assertEqual(gw.refunds, [(o["charge_id"], 3564)])

    def test_sales_summary_uses_charged_amounts(self):
        s, gw, _ = make_shop()
        a = s.orders.place("ann", {"TEA-1": 1}, "tok")                # 1500
        s.orders.place("ann", {"MUG-1": 1}, "tok", "FIVEOFF")         # 300 + 60 = 360
        before = sales_summary(s.orders)
        self.assertEqual(before, {"orders": 2, "gross": 1860, "refunded": 0, "net": 1860})
        s.catalog.set_price("TEA-1", 2000)
        s.catalog.set_price("MUG-1", 100)
        self.assertEqual(sales_summary(s.orders), before)
        s.orders.cancel(a["id"])
        self.assertEqual(sales_summary(s.orders),
                         {"orders": 2, "gross": 1860, "refunded": 1500, "net": 360})
        self.assertEqual(sum(gw.charges.values()), 1860)

    def test_csv_and_events_unchanged(self):
        s, _, _ = make_shop()
        o = s.orders.place("ann", {"TEA-1": 1}, "tok")
        s.catalog.set_price("TEA-1", 5000)
        n = len(s.events.events)
        s.orders.cancel(o["id"])
        new = s.events.events[n:]
        self.assertEqual([e["type"] for e in new],
                         ["payment_refunded", "stock_returned", "order_cancelled"])
        self.assertEqual(new[0]["amount"], 1500)
        self.assertEqual(orders_csv(s.orders).splitlines()[1], "O00001,ann,cancelled,$15.00")


if __name__ == "__main__":
    unittest.main()
