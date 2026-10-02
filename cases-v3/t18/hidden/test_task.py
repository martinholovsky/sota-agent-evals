import unittest

import shop.auth as auth
from shop.coupons import CouponUnavailable, DuplicateCoupon
from shop.inventory import OutOfStock
from shop.payments import GatewayError
from shop.pricing import quote
from hidden.helpers import login, make_shop

T0 = 1_700_000_000          # make_shop's clock starts here


class Define(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, self.clock = make_shop()

    def test_exceptions_are_not_value_errors(self):
        self.assertFalse(issubclass(CouponUnavailable, ValueError))
        self.assertFalse(issubclass(DuplicateCoupon, ValueError))

    def test_builtins_present_without_events(self):
        self.assertEqual(self.s.events.of_type("coupon_defined"), [])
        self.assertIsNone(self.s.coupons.uses_left("TEN"))
        self.assertIsNone(self.s.coupons.uses_left("FIVEOFF"))
        with self.assertRaises(KeyError):
            self.s.coupons.uses_left("NOPE")

    def test_define_and_event(self):
        self.s.coupons.define("SPRING25", "pct", 25, expires_at=T0 + 100, max_uses=3)
        evs = self.s.events.of_type("coupon_defined")
        self.assertEqual(len(evs), 1)
        e = evs[0]
        self.assertEqual((e["code"], e["kind"], e["value"], e["expires_at"], e["max_uses"]),
                         ("SPRING25", "pct", 25, T0 + 100, 3))
        self.assertEqual(self.s.coupons.uses_left("SPRING25"), 3)

    def test_invalid(self):
        bad = [("ab", "pct", 10), ("lower1", "pct", 10), ("BAD-CODE", "pct", 10),
               ("X" * 21, "pct", 10), ("OKCODE", "pct", 0), ("OKCODE", "pct", 101),
               ("OKCODE", "pct", True), ("OKCODE", "fixed", 0), ("OKCODE", "fixed", 2.5),
               ("OKCODE", "bogo", 1)]
        for args in bad:
            with self.assertRaises(ValueError, msg=repr(args)):
                self.s.coupons.define(*args)
        for kw in ({"max_uses": 0}, {"max_uses": -1}, {"max_uses": True}, {"expires_at": "soon"}):
            with self.assertRaises(ValueError, msg=repr(kw)):
                self.s.coupons.define("OKCODE", "pct", 10, **kw)
        self.assertEqual(self.s.events.of_type("coupon_defined"), [])

    def test_duplicate(self):
        self.s.coupons.define("ONCE", "fixed", 100)
        with self.assertRaises(DuplicateCoupon):
            self.s.coupons.define("ONCE", "fixed", 100)
        with self.assertRaises(DuplicateCoupon):
            self.s.coupons.define("TEN", "pct", 50)
        self.assertEqual(len(self.s.events.of_type("coupon_defined")), 1)
        # the built-in is untouched by the rejected redefinition
        self.assertEqual(self.s.orders.place("ann", {"TEA-1": 2}, "tok", "TEN")["quote"]["discount"], 250)


class Pricing(unittest.TestCase):
    def test_module_quote_unchanged(self):
        self.assertEqual(quote([(1250, 2), (800, 1)], "TEN"),
                         {"subtotal": 3300, "discount": 330, "tax": 594, "total": 3564})
        self.assertEqual(quote([(300, 1)], "FIVEOFF")["total"], 0)
        with self.assertRaises(ValueError):
            quote([(100, 1)], "BOGUS")

    def test_builtins_through_orders(self):
        s, gw, _ = make_shop()
        a = s.orders.place("ann", {"TEA-1": 2, "MUG-1": 1}, "tok", "TEN")
        self.assertEqual(a["quote"], {"subtotal": 3300, "discount": 330, "tax": 594, "total": 3564})
        b = s.orders.place("ann", {"MUG-1": 1}, "tok", "FIVEOFF")
        self.assertEqual(b["quote"], {"subtotal": 800, "discount": 500, "tax": 60, "total": 360})
        for _ in range(3):
            s.orders.place("ann", {"TEA-1": 1}, "tok", "TEN")       # unlimited
        self.assertIsNone(s.coupons.uses_left("TEN"))

    def test_defined_coupon_pricing(self):
        s, _, _ = make_shop()
        s.coupons.define("THIRD", "pct", 33)
        s.coupons.define("BIGOFF", "fixed", 5000)
        q = s.orders.place("ann", {"TEA-1": 1}, "tok", "THIRD")["quote"]
        # 33% of 1250 = 412.5 -> 413; tax 20% of 837 = 167.4 -> 167
        self.assertEqual(q, {"subtotal": 1250, "discount": 413, "tax": 167, "total": 1004})
        q = s.orders.place("ann", {"MUG-1": 1}, "tok", "BIGOFF")["quote"]
        self.assertEqual(q, {"subtotal": 800, "discount": 800, "tax": 0, "total": 0})


class Usage(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, self.clock = make_shop()

    def test_unknown_coupon_still_value_error(self):
        with self.assertRaises(ValueError):
            self.s.orders.place("ann", {"TEA-1": 1}, "tok", "NOPE")
        self.assertEqual(self.s.inventory.available("TEA-1"), 10)

    def test_expiry_boundary(self):
        self.s.coupons.define("SOON", "pct", 10, expires_at=T0 + 60)
        self.clock.t = T0 + 59
        self.assertEqual(self.s.orders.place("ann", {"TEA-1": 1}, "tok", "SOON")["coupon"], "SOON")
        self.clock.t = T0 + 60
        n = len(self.s.events.events)
        with self.assertRaises(CouponUnavailable):
            self.s.orders.place("ann", {"TEA-1": 1}, "tok", "SOON")
        self.assertEqual(self.s.events.events[n:], [])
        self.assertEqual(self.s.inventory.available("TEA-1"), 9)
        self.assertEqual(len(self.gw.charges), 1)

    def test_max_uses_and_cancel_returns_use(self):
        self.s.coupons.define("TWICE", "fixed", 100, max_uses=2)
        a = self.s.orders.place("ann", {"TEA-1": 1}, "tok", "TWICE")
        self.s.orders.place("ann", {"TEA-1": 1}, "tok", "TWICE")
        self.assertEqual(self.s.coupons.uses_left("TWICE"), 0)
        n = len(self.s.events.events)
        with self.assertRaises(CouponUnavailable):
            self.s.orders.place("ann", {"TEA-1": 1}, "tok", "TWICE")
        self.assertEqual(self.s.events.events[n:], [])
        self.assertEqual(self.s.inventory.available("TEA-1"), 8)
        self.s.orders.cancel(a["id"])
        self.assertEqual(self.s.coupons.uses_left("TWICE"), 1)
        self.s.orders.place("ann", {"TEA-1": 1}, "tok", "TWICE")
        self.assertEqual(self.s.coupons.uses_left("TWICE"), 0)

    def test_failed_orders_consume_nothing(self):
        self.s.coupons.define("ONCE", "fixed", 100, max_uses=1)
        with self.assertRaises(GatewayError):
            self.s.orders.place("ann", {"TEA-1": 1}, "tok_declined", "ONCE")
        with self.assertRaises(OutOfStock):
            self.s.orders.place("ann", {"MUG-1": 99}, "tok", "ONCE")
        with self.assertRaises(KeyError):
            self.s.orders.place("ann", {"NOPE-1": 1}, "tok", "ONCE")
        self.assertEqual(self.s.coupons.uses_left("ONCE"), 1)
        self.assertEqual(self.s.orders.all(), [])
        self.assertEqual(self.s.inventory.available("TEA-1"), 10)
        o = self.s.orders.place("ann", {"TEA-1": 1}, "tok", "ONCE")
        self.assertEqual(o["quote"]["discount"], 100)
        self.assertEqual(self.s.coupons.uses_left("ONCE"), 0)

    def test_cancel_after_expiry_returns_use(self):
        self.s.coupons.define("LATE", "pct", 10, expires_at=T0 + 10, max_uses=1)
        o = self.s.orders.place("ann", {"TEA-1": 1}, "tok", "LATE")
        self.clock.t = T0 + 500
        c = self.s.orders.cancel(o["id"])
        self.assertEqual(c["status"], "cancelled")
        self.assertEqual(self.gw.refunds, [(o["charge_id"], o["quote"]["total"])])
        self.assertEqual(self.s.coupons.uses_left("LATE"), 1)

    def test_order_and_event_fields_and_sequence(self):
        n = len(self.s.events.events)
        o = self.s.orders.place("ann", {"TEA-1": 1}, "tok", "TEN")
        self.assertEqual(o["coupon"], "TEN")
        self.assertEqual(self.s.orders.get(o["id"])["coupon"], "TEN")
        self.s.orders.cancel(o["id"])
        evs = self.s.events.events[n:]
        self.assertEqual([e["type"] for e in evs],
                         ["stock_taken", "payment_captured", "order_placed",
                          "payment_refunded", "stock_returned", "order_cancelled"])
        self.assertEqual(evs[2]["coupon"], "TEN")
        p = self.s.orders.place("ann", {"TEA-1": 1}, "tok")
        self.assertIsNone(p["coupon"])
        self.assertIsNone(self.s.events.of_type("order_placed")[-1]["coupon"])

    def test_limited_coupon_event_sequence(self):
        self.s.coupons.define("LIM", "pct", 10, max_uses=5)
        n = len(self.s.events.events)
        o = self.s.orders.place("ann", {"TEA-1": 1}, "tok", "LIM")
        self.s.orders.cancel(o["id"])
        self.assertEqual([e["type"] for e in self.s.events.events[n:]],
                         ["stock_taken", "payment_captured", "order_placed",
                          "payment_refunded", "stock_returned", "order_cancelled"])


class Api(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, self.clock = make_shop()
        self.root, self.ann = login(self.s, "root"), login(self.s, "ann")

    def test_define_codes(self):
        req = {"code": "API10", "kind": "pct", "value": 10, "max_uses": 1}
        self.assertEqual(self.s.api.define_coupon(self.ann, req)[0], 403)
        with self.assertRaises(KeyError):
            self.s.coupons.uses_left("API10")
        self.assertEqual(self.s.api.define_coupon(self.root, dict(req, value=0))[0], 400)
        self.assertEqual(self.s.api.define_coupon(self.root, dict(req, code="x"))[0], 400)
        self.assertEqual(self.s.api.define_coupon(self.root, req)[0], 201)
        self.assertEqual(self.s.api.define_coupon(self.root, req)[0], 409)
        self.assertEqual(self.s.api.define_coupon(self.root, dict(req, code="TEN"))[0], 409)
        self.assertEqual(self.s.coupons.uses_left("API10"), 1)

    def test_place_codes(self):
        self.s.coupons.define("ONCE", "fixed", 100, max_uses=1, expires_at=T0 + 100)
        place = lambda c: self.s.api.place_order(self.ann, {"items": {"TEA-1": 1}, "token": "tok",
                                                            "coupon": c})[0]
        self.assertEqual(place("NOPE"), 400)
        self.assertEqual(place("ONCE"), 201)
        self.assertEqual(place("ONCE"), 409)
        self.s.coupons.define("EXP", "fixed", 100, expires_at=T0 + 1)
        self.clock.t = T0 + 1
        self.assertEqual(place("EXP"), 409)
        self.assertEqual(place("TEN"), 201)

    def test_permission_comes_from_role_permissions(self):
        self.assertIn("coupon:edit", auth.ROLE_PERMISSIONS["admin"])
        self.assertNotIn("coupon:edit", auth.ROLE_PERMISSIONS["customer"])
        auth.ROLE_PERMISSIONS["marketing"] = {"coupon:edit"}
        try:
            mk = {"username": "meg", "role": "marketing"}
            self.assertEqual(self.s.api.define_coupon(
                mk, {"code": "MKT5", "kind": "fixed", "value": 500})[0], 201)
        finally:
            del auth.ROLE_PERMISSIONS["marketing"]


if __name__ == "__main__":
    unittest.main()
