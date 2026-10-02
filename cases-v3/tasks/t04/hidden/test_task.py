import unittest

from shop.inventory import OutOfStock
from shop.orders import OrderError
from shop.payments import GatewayError
from hidden.helpers import login, make_shop


class Reservations(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, self.clock = make_shop()
        self.s.users.create("bob", "another long password", "customer", "bob@example.com")
        self.inv = self.s.inventory

    def types_since(self, n):
        return [e["type"] for e in self.s.events.events[n:]]

    def test_reserve_holds_stock(self):
        n = len(self.s.events.events)
        r = self.s.orders.reserve("ann", {"MUG-1": 3}, 600)
        self.assertIsInstance(r["id"], str)
        self.assertEqual((r["customer"], r["items"], r["expires_at"]), ("ann", {"MUG-1": 3}, self.clock.t + 600))
        self.assertEqual(self.types_since(n), ["stock_reserved"])
        ev = self.s.events.events[-1]
        self.assertEqual((ev["reservation_id"], ev["customer"], ev["lines"], ev["expires_at"]),
                         (r["id"], "ann", {"MUG-1": 3}, self.clock.t + 600))
        self.assertEqual((self.inv.on_hand("MUG-1"), self.inv.available("MUG-1")), (5, 2))

    def test_others_cannot_take_reserved_stock(self):
        self.s.orders.reserve("ann", {"MUG-1": 4}, 600)
        with self.assertRaises(OutOfStock):
            self.s.orders.place("bob", {"MUG-1": 2}, "tok")
        self.assertEqual(self.gw.charges, {})
        self.s.orders.place("bob", {"MUG-1": 1}, "tok")
        self.assertEqual((self.inv.on_hand("MUG-1"), self.inv.available("MUG-1")), (4, 0))

    def test_reserve_all_or_nothing_and_validation(self):
        n = len(self.s.events.events)
        with self.assertRaises(OutOfStock):
            self.s.orders.reserve("ann", {"TEA-1": 1, "MUG-1": 6}, 600)
        with self.assertRaises(KeyError):
            self.s.orders.reserve("ann", {"TEA-1": 1, "NOPE-1": 1}, 600)
        with self.assertRaises(OrderError):
            self.s.orders.reserve("ann", {}, 600)
        for q in (0, -1, 1.5, True):
            with self.assertRaises(OrderError):
                self.s.orders.reserve("ann", {"TEA-1": q}, 600)
        for ttl in (0, -5, 1.5, True, "60"):
            with self.assertRaises(ValueError):
                self.s.orders.reserve("ann", {"TEA-1": 1}, ttl)
        self.assertEqual(self.types_since(n), [])
        self.assertEqual((self.inv.available("TEA-1"), self.inv.available("MUG-1")), (10, 5))
        self.s.orders.reserve("ann", {"MUG-1": 5}, 600)       # nothing was held by the failures

    def test_place_with_fully_reserved_stock(self):
        r = self.s.orders.reserve("ann", {"MUG-1": 5}, 600)
        n = len(self.s.events.events)
        o = self.s.orders.place("ann", {"MUG-1": 5}, "tok", reservation=r["id"])
        self.assertEqual(o["status"], "paid")
        self.assertEqual(self.types_since(n), ["stock_taken", "payment_captured", "order_placed"])
        self.assertEqual(self.s.events.events[n]["reservation"], r["id"])
        self.assertEqual((self.inv.on_hand("MUG-1"), self.inv.available("MUG-1")), (0, 0))
        with self.assertRaises(OrderError):                  # consumed: never usable again
            self.s.orders.place("ann", {"MUG-1": 5}, "tok", reservation=r["id"])

    def test_consumed_reservation_holds_nothing(self):
        r = self.s.orders.reserve("ann", {"TEA-1": 4}, 600)
        self.s.orders.place("ann", {"TEA-1": 4}, "tok", reservation=r["id"])
        self.assertEqual((self.inv.on_hand("TEA-1"), self.inv.available("TEA-1")), (6, 6))
        self.s.orders.place("bob", {"TEA-1": 6}, "tok")

    def test_cancel_with_live_reservations_keeps_counts_right(self):
        self.s.orders.reserve("ann", {"TEA-1": 3}, 600)
        o = self.s.orders.place("bob", {"TEA-1": 2}, "tok")
        self.assertEqual((self.inv.on_hand("TEA-1"), self.inv.available("TEA-1")), (8, 5))
        self.s.orders.cancel(o["id"])
        self.assertEqual((self.inv.on_hand("TEA-1"), self.inv.available("TEA-1")), (10, 7))

    def test_payment_failure_keeps_reservation(self):
        r = self.s.orders.reserve("ann", {"MUG-1": 5}, 600)
        with self.assertRaises(GatewayError):
            self.s.orders.place("ann", {"MUG-1": 5}, "tok_declined", reservation=r["id"])
        self.assertEqual((self.inv.on_hand("MUG-1"), self.inv.available("MUG-1")), (5, 0))
        self.assertEqual(self.s.orders.all(), [])
        with self.assertRaises(OutOfStock):
            self.s.orders.place("bob", {"MUG-1": 1}, "tok")
        o = self.s.orders.place("ann", {"MUG-1": 5}, "tok", reservation=r["id"])
        self.assertEqual(o["status"], "paid")

    def test_expiry_releases_without_event(self):
        r = self.s.orders.reserve("ann", {"MUG-1": 5}, 600)
        n = len(self.s.events.events)
        self.clock.t += 599
        self.assertEqual(self.inv.available("MUG-1"), 0)
        self.clock.t += 1                                    # clock() == expires_at: expired
        self.assertEqual(self.inv.available("MUG-1"), 5)
        self.assertEqual(self.types_since(n), [])
        with self.assertRaises(OrderError):
            self.s.orders.place("ann", {"MUG-1": 5}, "tok", reservation=r["id"])
        self.assertEqual(self.inv.on_hand("MUG-1"), 5)
        self.assertEqual(self.gw.charges, {})
        self.s.orders.place("bob", {"MUG-1": 5}, "tok")
        self.assertEqual(self.inv.available("MUG-1"), 0)

    def test_reservation_rules(self):
        r = self.s.orders.reserve("ann", {"TEA-1": 2, "MUG-1": 1}, 600)
        n = len(self.s.events.events)
        bad = [("bob", {"TEA-1": 2, "MUG-1": 1}, r["id"]),     # someone else's
               ("ann", {"TEA-1": 2}, r["id"]),                 # items differ
               ("ann", {"TEA-1": 2, "MUG-1": 2}, r["id"]),
               ("ann", {"TEA-1": 2, "MUG-1": 1}, "R-NOPE")]    # unknown
        for who, items, rid in bad:
            with self.assertRaises(OrderError, msg=(who, items, rid)):
                self.s.orders.place(who, items, "tok", reservation=rid)
        self.assertEqual(self.types_since(n), [])
        self.assertEqual((self.inv.available("TEA-1"), self.inv.available("MUG-1")), (8, 4))
        self.s.orders.place("ann", {"MUG-1": 1, "TEA-1": 2}, "tok", reservation=r["id"])
        self.assertEqual((self.inv.on_hand("TEA-1"), self.inv.on_hand("MUG-1")), (8, 4))

    def test_api(self):
        ann, root = login(self.s, "ann"), login(self.s, "root")
        bob = self.s.users.login("bob", "another long password")
        code, body = self.s.api.reserve_stock(ann, {"items": {"MUG-1": 2}, "ttl": 300})
        self.assertEqual(code, 201)
        rid = body["reservation"]["id"]
        self.assertEqual(body["reservation"]["customer"], "ann")
        self.assertEqual(self.s.api.reserve_stock(ann, {"items": {"MUG-1": 9}, "ttl": 300})[0], 409)
        self.assertEqual(self.s.api.reserve_stock(ann, {"items": {"NOPE-1": 1}, "ttl": 300})[0], 404)
        self.assertEqual(self.s.api.reserve_stock(ann, {"items": {"MUG-1": 1}, "ttl": 0})[0], 400)
        self.assertEqual(self.s.api.reserve_stock(ann, {"items": {"MUG-1": 1}})[0], 400)
        self.assertEqual(self.s.api.reserve_stock(ann, {"items": [], "ttl": 5})[0], 400)
        self.assertEqual(self.s.api.reserve_stock({"username": "g", "role": "ghost"},
                                                  {"items": {"MUG-1": 1}, "ttl": 5})[0], 403)
        req = {"items": {"MUG-1": 2}, "token": "tok", "reservation": rid}
        self.assertEqual(self.s.api.place_order(bob, req)[0], 400)
        self.assertEqual(self.s.api.place_order(ann, dict(req, reservation=7))[0], 400)
        self.assertEqual(self.s.api.place_order(ann, req)[0], 201)
        self.assertEqual(self.s.api.place_order(ann, req)[0], 400)
        self.assertEqual(self.inv.on_hand("MUG-1"), 3)
