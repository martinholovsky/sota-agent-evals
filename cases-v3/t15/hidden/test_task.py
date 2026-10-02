import unittest

from shop.inventory import OutOfStock
from shop.orders import IdempotencyConflict, OrderError
from shop.payments import GatewayError
from shop.reports import sales_summary
from hidden.helpers import login, make_shop


class Keys(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, _ = make_shop()
        self.s.users.create("bob", "another long password", "customer", "bob@example.com")

    def state(self):
        return (len(self.s.events.events), len(self.gw.charges), len(self.s.orders.all()),
                self.s.inventory.available("TEA-1"), self.s.inventory.available("MUG-1"))

    def test_is_an_order_error(self):
        self.assertTrue(issubclass(IdempotencyConflict, OrderError))

    def test_replay_returns_original_and_does_nothing(self):
        o = self.s.orders.place("ann", {"TEA-1": 1, "MUG-1": 2}, "tok", "TEN", idempotency_key="k1")
        before = self.state()
        again = self.s.orders.place("ann", {"MUG-1": 2, "TEA-1": 1}, "tok_new", "TEN",
                                    idempotency_key="k1")
        self.assertEqual(again, o)
        self.assertEqual(self.state(), before)

    def test_first_placement_events_unchanged(self):
        n = len(self.s.events.events)
        self.s.orders.place("ann", {"TEA-1": 1}, "tok", idempotency_key="k1")
        self.assertEqual([e["type"] for e in self.s.events.events[n:]],
                         ["stock_taken", "payment_captured", "order_placed"])

    def test_replay_after_stock_ran_out(self):
        o = self.s.orders.place("ann", {"MUG-1": 5}, "tok", idempotency_key="k1")
        self.assertEqual(self.s.inventory.available("MUG-1"), 0)
        self.assertEqual(self.s.orders.place("ann", {"MUG-1": 5}, "tok", idempotency_key="k1")["id"],
                         o["id"])

    def test_replay_reflects_current_state(self):
        o = self.s.orders.place("ann", {"TEA-1": 1}, "tok", idempotency_key="k1")
        self.s.orders.cancel(o["id"])
        before = self.state()
        again = self.s.orders.place("ann", {"TEA-1": 1}, "tok", idempotency_key="k1")
        self.assertEqual((again["id"], again["status"]), (o["id"], "cancelled"))
        self.assertEqual(self.state(), before)

    def test_different_request_conflicts(self):
        self.s.orders.place("ann", {"TEA-1": 1}, "tok", idempotency_key="k1")
        before = self.state()
        for items, coupon in (({"TEA-1": 2}, None), ({"TEA-1": 1, "MUG-1": 1}, None),
                              ({"TEA-1": 1}, "TEN")):
            with self.assertRaises(IdempotencyConflict, msg=repr((items, coupon))):
                self.s.orders.place("ann", items, "tok", coupon, idempotency_key="k1")
        self.assertEqual(self.state(), before)

    def test_keys_are_per_customer(self):
        a = self.s.orders.place("ann", {"TEA-1": 1}, "tok", idempotency_key="k1")
        b = self.s.orders.place("bob", {"MUG-1": 1}, "tok", idempotency_key="k1")
        self.assertNotEqual(a["id"], b["id"])
        self.assertEqual(b["customer"], "bob")
        c = self.s.orders.place("bob", {"TEA-1": 1}, "tok", idempotency_key="k2")
        self.assertEqual(c["customer"], "bob")
        self.assertEqual(len(self.s.orders.all()), 3)

    def test_no_key_unchanged(self):
        a = self.s.orders.place("ann", {"TEA-1": 1}, "tok")
        b = self.s.orders.place("ann", {"TEA-1": 1}, "tok")
        self.assertNotEqual(a["id"], b["id"])

    def test_failures_do_not_consume_the_key(self):
        with self.assertRaises(GatewayError):
            self.s.orders.place("ann", {"TEA-1": 1}, "tok_declined", idempotency_key="k1")
        with self.assertRaises(OutOfStock):
            self.s.orders.place("ann", {"MUG-1": 50}, "tok", idempotency_key="k1")
        with self.assertRaises(OrderError):
            self.s.orders.place("ann", {"TEA-1": 0}, "tok", idempotency_key="k1")
        with self.assertRaises(KeyError):
            self.s.orders.place("ann", {"NOPE-1": 1}, "tok", idempotency_key="k1")
        with self.assertRaises(ValueError):
            self.s.orders.place("ann", {"TEA-1": 1}, "tok", "BOGUS", idempotency_key="k1")
        o = self.s.orders.place("ann", {"MUG-1": 1}, "tok", idempotency_key="k1")
        self.assertEqual(len(self.gw.charges), 1)
        self.assertEqual(self.s.orders.place("ann", {"MUG-1": 1}, "tok", idempotency_key="k1")["id"],
                         o["id"])
        self.assertEqual(sales_summary(self.s.orders)["orders"], 1)


class KeyApi(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, _ = make_shop()
        self.ann = login(self.s, "ann")

    def test_bad_key(self):
        for key in ("", 5, ["k"]):
            req = {"items": {"TEA-1": 1}, "token": "tok", "idempotency_key": key}
            self.assertEqual(self.s.api.place_order(self.ann, req)[0], 400, repr(key))
        self.assertEqual(self.s.orders.all(), [])

    def test_replay_and_conflict(self):
        req = {"items": {"TEA-1": 1}, "token": "tok", "idempotency_key": "abc"}
        code, body = self.s.api.place_order(self.ann, req)
        self.assertEqual(code, 201)
        code2, body2 = self.s.api.place_order(self.ann, dict(req, token="tok2"))
        self.assertEqual((code2, body2["order"]["id"]), (201, body["order"]["id"]))
        self.assertEqual(len(self.gw.charges), 1)
        code3, body3 = self.s.api.place_order(self.ann, dict(req, items={"TEA-1": 2}))
        self.assertEqual(code3, 409)
        self.assertIn("error", body3)

    def test_declined_is_402_and_retry_works(self):
        req = {"items": {"TEA-1": 1}, "token": "tok_declined", "idempotency_key": "abc"}
        code, body = self.s.api.place_order(self.ann, req)
        self.assertEqual(code, 402)
        self.assertIn("error", body)
        self.assertEqual(self.s.inventory.available("TEA-1"), 10)
        self.assertEqual(self.s.api.place_order(self.ann, dict(req, token="tok"))[0], 201)
        self.assertEqual(self.s.api.place_order(
            self.ann, {"items": {"TEA-1": 1}, "token": "tok_declined"})[0], 402)

    def test_other_statuses_unchanged(self):
        ann = self.ann
        self.assertEqual(self.s.api.place_order(ann, {"items": {"MUG-1": 50}, "token": "t",
                                                      "idempotency_key": "x"})[0], 409)
        self.assertEqual(self.s.api.place_order(ann, {"items": {"MUG-1": 0}, "token": "t",
                                                      "idempotency_key": "x"})[0], 400)
        self.assertEqual(self.s.api.place_order(ann, {"items": {"NOPE-1": 1}, "token": "t",
                                                      "idempotency_key": "x"})[0], 404)
        self.assertEqual(self.s.api.place_order(ann, {"items": {"MUG-1": 1}, "token": "t",
                                                      "idempotency_key": "x"})[0], 201)
