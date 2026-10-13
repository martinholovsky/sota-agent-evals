import unittest

from shop.inventory import OutOfStock
from shop.orders import OrderError
from shop.payments import GatewayError
from shop.reports import orders_csv, sales_summary
from tests.helpers import make_shop


class Place(unittest.TestCase):
    def test_place_charges_quote_total_and_takes_stock(self):
        s, gw, _ = make_shop()
        o = s.orders.place("ann", {"TEA-1": 2}, "tok")
        self.assertEqual(o["quote"]["total"], 3000)            # 2500 + 20% tax
        self.assertEqual(gw.charges[o["charge_id"]], 3000)
        self.assertEqual(s.inventory.available("TEA-1"), 8)
        self.assertEqual(o["status"], "paid")

    def test_all_or_nothing_on_stock(self):
        s, gw, _ = make_shop()
        with self.assertRaises(OutOfStock):
            s.orders.place("ann", {"TEA-1": 1, "MUG-1": 99}, "tok")
        self.assertEqual((s.inventory.available("TEA-1"), gw.charges), (10, {}))

    def test_payment_failure_restores_stock_and_records_nothing(self):
        s, _, _ = make_shop()
        with self.assertRaises(GatewayError):
            s.orders.place("ann", {"TEA-1": 3}, "tok_declined")
        self.assertEqual(s.inventory.available("TEA-1"), 10)
        self.assertEqual(s.orders.all(), [])

    def test_bad_qty(self):
        s, _, _ = make_shop()
        for q in (0, -1, 1.5, True):
            with self.assertRaises(OrderError):
                s.orders.place("ann", {"TEA-1": q}, "tok")


class Cancel(unittest.TestCase):
    def test_cancel_refunds_and_restocks(self):
        s, gw, _ = make_shop()
        o = s.orders.place("ann", {"MUG-1": 2}, "tok")
        c = s.orders.cancel(o["id"])
        self.assertEqual(c["status"], "cancelled")
        self.assertEqual(gw.refunds, [(o["charge_id"], o["quote"]["total"])])
        self.assertEqual(s.inventory.available("MUG-1"), 5)
        with self.assertRaises(OrderError):
            s.orders.cancel(o["id"])


class Reports(unittest.TestCase):
    def test_summary_nets_refunds(self):
        s, _, _ = make_shop()
        a = s.orders.place("ann", {"TEA-1": 1}, "tok")
        s.orders.place("ann", {"MUG-1": 1}, "tok")
        s.orders.cancel(a["id"])
        self.assertEqual(sales_summary(s.orders), {"orders": 2, "gross": 1500 + 960,
                                                   "refunded": 1500, "net": 960})

    def test_csv(self):
        s, _, _ = make_shop()
        s.orders.place("ann", {"TEA-1": 1}, "tok")
        self.assertEqual(orders_csv(s.orders).splitlines(),
                         ["id,customer,status,total", "O00001,ann,paid,$15.00"])

    def test_every_state_change_emits_one_event(self):
        s, _, _ = make_shop()
        n = len(s.events.events)
        o = s.orders.place("ann", {"TEA-1": 1}, "tok")
        types = [e["type"] for e in s.events.events[n:]]
        self.assertEqual(types, ["stock_taken", "payment_captured", "order_placed"])
        s.orders.cancel(o["id"])
        self.assertEqual([e["type"] for e in s.events.events[n + 3:]],
                         ["payment_refunded", "stock_returned", "order_cancelled"])
