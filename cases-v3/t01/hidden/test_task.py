import unittest

from shop.orders import OrderError
from shop.reports import sales_summary
from hidden.helpers import login, make_shop


class Refunds(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, _ = make_shop()
        self.o = self.s.orders.place("ann", {"TEA-1": 2}, "tok")      # total 3000

    def test_partial_then_full(self):
        r = self.s.orders.refund(self.o["id"], 1000)
        self.assertEqual((r["status"], r["refunded"]), ("partially_refunded", 1000))
        self.assertEqual(self.s.inventory.available("TEA-1"), 8)       # no restock
        r = self.s.orders.refund(self.o["id"], 2000)
        self.assertEqual((r["status"], r["refunded"]), ("refunded", 3000))
        self.assertEqual([a for _, a in self.gw.refunds], [1000, 2000])

    def test_limits(self):
        for bad in (0, -5, 3001, 10.0, True):
            with self.assertRaises(ValueError, msg=bad):
                self.s.orders.refund(self.o["id"], bad)
        self.s.orders.refund(self.o["id"], 3000)
        with self.assertRaises(OrderError):
            self.s.orders.refund(self.o["id"], 1)

    def test_exactly_one_order_event(self):
        n = len(self.s.events.of_type("order_refunded"))
        self.s.orders.refund(self.o["id"], 500)
        evs = self.s.events.of_type("order_refunded")[n:]
        self.assertEqual(len(evs), 1)
        self.assertEqual((evs[0]["order_id"], evs[0]["amount"]), (self.o["id"], 500))

    def test_cancel_after_partial(self):
        self.s.orders.refund(self.o["id"], 1000)
        c = self.s.orders.cancel(self.o["id"])
        self.assertEqual(c["status"], "cancelled")
        self.assertEqual([a for _, a in self.gw.refunds], [1000, 2000])
        self.assertEqual(self.s.inventory.available("TEA-1"), 10)
        self.assertEqual(c["refunded"], 3000)

    def test_reports_net(self):
        self.s.orders.refund(self.o["id"], 1000)
        self.assertEqual(sales_summary(self.s.orders)["net"], 2000)

    def test_api(self):
        req = {"id": self.o["id"], "amount": 100}
        self.assertEqual(self.s.api.refund_order(login(self.s, "ann"), req)[0], 403)
        self.assertEqual(self.s.api.refund_order(login(self.s, "root"), req)[0], 200)
        self.assertEqual(self.s.api.refund_order(login(self.s, "root"), {"id": "O99999", "amount": 1})[0], 404)
        self.assertEqual(self.s.api.refund_order(login(self.s, "root"), {"id": self.o["id"], "amount": 99999})[0], 400)
