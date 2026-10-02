import unittest

from shop.inventory import OutOfStock
from shop.orders import OrderError, PurchaseLimitExceeded
from shop.reports import sales_summary
from hidden.helpers import login, make_shop

DAY = 86_400


class SetLimit(unittest.TestCase):
    def test_validation_and_event(self):
        s, _, _ = make_shop()
        with self.assertRaises(KeyError):
            s.catalog.set_purchase_limit("NOPE-1", 3)
        for bad in (0, -1, 1.5, True, "3"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                s.catalog.set_purchase_limit("TEA-1", bad)
        n = len(s.events.events)
        s.catalog.set_purchase_limit("TEA-1", 3)
        s.catalog.set_purchase_limit("TEA-1", None)
        new = s.events.events[n:]
        self.assertEqual([e["type"] for e in new], ["purchase_limit_set"] * 2)
        self.assertEqual([(e["sku"], e["limit"]) for e in new], [("TEA-1", 3), ("TEA-1", None)])

    def test_removed_limit_no_longer_applies(self):
        s, _, _ = make_shop()
        s.catalog.set_purchase_limit("TEA-1", 1)
        s.catalog.set_purchase_limit("TEA-1", None)
        s.orders.place("ann", {"TEA-1": 4}, "tok")


class Enforce(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, self.clock = make_shop()
        self.s.users.create("bob", "another long password", "customer", "bob@example.com")
        self.s.catalog.set_purchase_limit("TEA-1", 3)

    def assert_rejected_cleanly(self, customer, items):
        n, stock = len(self.s.events.events), self.s.inventory.available("TEA-1")
        orders, charges = len(self.s.orders.all()), dict(self.gw.charges)
        with self.assertRaises(PurchaseLimitExceeded):
            self.s.orders.place(customer, items, "tok")
        self.assertEqual(self.s.events.events[n:], [])
        self.assertEqual(self.s.inventory.available("TEA-1"), stock)
        self.assertEqual(len(self.s.orders.all()), orders)
        self.assertEqual(self.gw.charges, charges)

    def test_is_an_order_error(self):
        self.assertTrue(issubclass(PurchaseLimitExceeded, OrderError))

    def test_single_order_over_limit(self):
        self.assert_rejected_cleanly("ann", {"TEA-1": 4})
        self.s.orders.place("ann", {"TEA-1": 3}, "tok")

    def test_accumulates_within_window(self):
        self.s.orders.place("ann", {"TEA-1": 2}, "tok")
        self.clock.t += 3600
        self.s.orders.place("ann", {"TEA-1": 1}, "tok")
        self.assert_rejected_cleanly("ann", {"TEA-1": 1})

    def test_rolling_window_boundary(self):
        t0 = self.clock.t
        self.s.orders.place("ann", {"TEA-1": 3}, "tok")
        self.clock.t = t0 + DAY - 1
        self.assert_rejected_cleanly("ann", {"TEA-1": 1})
        self.clock.t = t0 + DAY
        self.s.orders.place("ann", {"TEA-1": 3}, "tok")

    def test_rolling_not_calendar(self):
        self.s.orders.place("ann", {"TEA-1": 2}, "tok")          # t0
        self.clock.t += DAY - 100
        self.s.orders.place("ann", {"TEA-1": 1}, "tok")          # t0 + DAY - 100
        self.clock.t += 200                                       # first order expired
        self.s.orders.place("ann", {"TEA-1": 2}, "tok")
        self.assert_rejected_cleanly("ann", {"TEA-1": 1})

    def test_cancelled_orders_do_not_count(self):
        o = self.s.orders.place("ann", {"TEA-1": 3}, "tok")
        self.s.orders.cancel(o["id"])
        self.s.orders.place("ann", {"TEA-1": 3}, "tok")

    def test_per_customer(self):
        self.s.orders.place("ann", {"TEA-1": 3}, "tok")
        self.s.orders.place("bob", {"TEA-1": 3}, "tok")
        self.assert_rejected_cleanly("bob", {"TEA-1": 1})

    def test_all_or_nothing_across_lines(self):
        self.s.catalog.set_purchase_limit("MUG-1", 1)
        self.assert_rejected_cleanly("ann", {"TEA-1": 1, "MUG-1": 2})
        self.assertEqual(self.s.inventory.available("MUG-1"), 5)
        self.s.orders.place("ann", {"TEA-1": 1, "MUG-1": 1}, "tok")
        self.assertEqual(sales_summary(self.s.orders)["orders"], 1)

    def test_unlimited_sku_unaffected(self):
        self.s.orders.place("ann", {"MUG-1": 5}, "tok")

    def test_limit_checked_before_stock(self):
        self.s.catalog.set_purchase_limit("MUG-1", 2)
        self.assert_rejected_cleanly("ann", {"MUG-1": 50})
        self.s.catalog.set_purchase_limit("MUG-1", 50)
        with self.assertRaises(OutOfStock):
            self.s.orders.place("ann", {"MUG-1": 6}, "tok")

    def test_failed_payment_does_not_count(self):
        from shop.payments import GatewayError
        with self.assertRaises(GatewayError):
            self.s.orders.place("ann", {"TEA-1": 3}, "tok_declined")
        self.s.orders.place("ann", {"TEA-1": 3}, "tok")


class LimitApi(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, self.clock = make_shop()
        self.ann, self.root = login(self.s, "ann"), login(self.s, "root")

    def test_place_order_409(self):
        self.s.catalog.set_purchase_limit("TEA-1", 2)
        req = {"items": {"TEA-1": 3}, "token": "tok"}
        code, body = self.s.api.place_order(self.ann, req)
        self.assertEqual(code, 409)
        self.assertIn("error", body)
        self.assertEqual(self.s.api.place_order(self.ann, {"items": {"TEA-1": 0}, "token": "t"})[0], 400)
        self.assertEqual(self.s.api.place_order(self.ann, {"items": {"TEA-1": 2}, "token": "t"})[0], 201)

    def test_set_limit_handler(self):
        self.assertEqual(self.s.api.set_purchase_limit(self.ann, {"sku": "TEA-1", "limit": 2})[0], 403)
        self.assertEqual(self.s.api.set_purchase_limit(self.root, {"sku": "NOPE-1", "limit": 2})[0], 404)
        for bad in (0, -2, True, "2", 1.5):
            self.assertEqual(self.s.api.set_purchase_limit(self.root, {"sku": "TEA-1", "limit": bad})[0],
                             400, repr(bad))
        self.assertEqual(self.s.api.set_purchase_limit(self.root, {"sku": "TEA-1", "limit": 2}),
                         (200, {"sku": "TEA-1", "limit": 2}))
        self.assertEqual(self.s.api.place_order(self.ann, {"items": {"TEA-1": 3}, "token": "t"})[0], 409)
        self.assertEqual(self.s.api.set_purchase_limit(self.root, {"sku": "TEA-1", "limit": None}),
                         (200, {"sku": "TEA-1", "limit": None}))
        self.assertEqual(self.s.api.place_order(self.ann, {"items": {"TEA-1": 3}, "token": "t"})[0], 201)
