import unittest

from shop.payments import GatewayError
from shop.reports import orders_csv, sales_summary
from hidden.helpers import login, make_shop

TOKEN = "tok_live_9f8e7d6c5b4a3f2e"


class NoTokenLeaks(unittest.TestCase):
    def assertNoToken(self, thing, where):
        self.assertNotIn(TOKEN, repr(thing), where)
        self.assertNotIn(TOKEN, str(thing), where)

    def test_successful_order(self):
        s, gw, _ = make_shop()
        o = s.orders.place("ann", {"TEA-1": 1}, TOKEN)
        code, body = s.api.place_order(login(s, "ann"), {"items": {"MUG-1": 1}, "token": TOKEN})
        self.assertEqual(code, 201)
        self.assertNoToken(o, "order returned by Orders.place")
        self.assertNoToken(body, "place_order response")
        self.assertNoToken(s.orders.all(), "stored orders")
        for who in ("ann", "root"):
            for oid in (o["id"], body["order"]["id"]):
                c, b = s.api.get_order(login(s, who), {"id": oid})
                self.assertEqual(c, 200)
                self.assertNoToken(b, "get_order response")
        s.orders.cancel(o["id"])
        self.assertNoToken(s.events.events, "events")
        self.assertNoToken(orders_csv(s.orders), "orders_csv")
        self.assertNoToken(sales_summary(s.orders), "sales_summary")

    def test_declined_payment(self):
        s, gw, _ = make_shop(fail_charge=True)
        with self.assertRaises(GatewayError) as cm:
            s.orders.place("ann", {"TEA-1": 3}, TOKEN)
        self.assertNoToken(cm.exception, "exception from Orders.place")
        try:                       # today the handler lets GatewayError propagate
            res = s.api.place_order(login(s, "ann"), {"items": {"TEA-1": 1}, "token": TOKEN})
        except GatewayError as e:
            self.assertNoToken(e, "exception from Api.place_order")
        else:
            self.assertNoToken(res, "place_order response")
        self.assertNoToken(s.events.events, "events")
        self.assertEqual(s.inventory.available("TEA-1"), 10)
        self.assertEqual(s.orders.all(), [])


class NothingElseRemoved(unittest.TestCase):
    def test_payment_captured_fields_kept(self):
        s, gw, _ = make_shop()
        o = s.orders.place("ann", {"TEA-1": 1}, TOKEN)
        e = s.events.of_type("payment_captured")[-1]
        self.assertEqual((e["order_id"], e["charge_id"], e["amount"]),
                         (o["id"], o["charge_id"], 1500))
        p = s.events.of_type("order_placed")[-1]
        self.assertEqual((p["order_id"], p["customer"], p["total"]), (o["id"], "ann", 1500))

    def test_failed_order_event_kept(self):
        s, gw, _ = make_shop(fail_charge=True)
        with self.assertRaises(GatewayError):
            s.orders.place("ann", {"TEA-1": 3}, TOKEN)
        failed = s.events.of_type("order_failed")
        self.assertEqual(len(failed), 1)
        self.assertEqual((failed[0]["order_id"], failed[0]["customer"]), ("O00001", "ann"))

    def test_order_fields_kept(self):
        s, gw, _ = make_shop()
        o = s.orders.place("ann", {"TEA-1": 1}, TOKEN)
        for k in ("id", "customer", "items", "quote", "charge_id", "status", "refunded"):
            self.assertIn(k, o)


if __name__ == "__main__":
    unittest.main()
