import unittest

import shop.auth as auth
from shop.pricing import quote
from shop.reports import orders_csv, sales_summary, tax_summary
from hidden.helpers import login, make_shop


class Flag(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, self.clock = make_shop()

    def test_default_and_set(self):
        self.assertFalse(self.s.users.is_tax_exempt("ann"))
        self.assertFalse(self.s.users.is_tax_exempt("nobody-at-all"))
        self.s.users.set_tax_exempt("ann", True)
        self.assertTrue(self.s.users.is_tax_exempt("ann"))
        self.assertFalse(self.s.users.is_tax_exempt("root"))

    def test_validation(self):
        for bad in (1, "yes", None, 0):
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.s.users.set_tax_exempt("ann", bad)
        with self.assertRaises(KeyError):
            self.s.users.set_tax_exempt("nobody-at-all", True)
        self.assertEqual(self.s.events.of_type("tax_exempt_changed"), [])

    def test_one_event_per_change_none_for_noop(self):
        n = len(self.s.events.events)
        self.s.users.set_tax_exempt("ann", False)          # already False: no change
        self.assertEqual(self.s.events.events[n:], [])
        self.s.users.set_tax_exempt("ann", True)
        self.s.users.set_tax_exempt("ann", True)           # no change
        self.s.users.set_tax_exempt("ann", False)
        evs = self.s.events.events[n:]
        self.assertEqual([e["type"] for e in evs], ["tax_exempt_changed", "tax_exempt_changed"])
        self.assertEqual([(e["username"], e["exempt"]) for e in evs], [("ann", True), ("ann", False)])


class Pricing(unittest.TestCase):
    def test_exempt_quote(self):
        self.assertEqual(quote([(1250, 2), (800, 1)], "TEN", tax_exempt=True),
                         {"subtotal": 3300, "discount": 330, "tax": 0, "total": 2970})
        self.assertEqual(quote([(300, 1)], "FIVEOFF", tax_exempt=True)["total"], 0)
        self.assertEqual(quote([(1250, 2)], tax_exempt=True)["total"], 2500)

    def test_default_unchanged(self):
        self.assertEqual(quote([(1250, 2), (800, 1)], "TEN"),
                         {"subtotal": 3300, "discount": 330, "tax": 594, "total": 3564})
        self.assertEqual(quote([(1250, 2)], tax_exempt=False)["total"], 3000)


class Orders(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, self.clock = make_shop()

    def test_exempt_order_charged_without_tax(self):
        self.s.users.set_tax_exempt("ann", True)
        o = self.s.orders.place("ann", {"TEA-1": 2}, "tok")
        self.assertEqual((o["quote"]["tax"], o["quote"]["total"]), (0, 2500))
        self.assertEqual(self.gw.charges[o["charge_id"]], 2500)
        self.assertIs(o["tax_exempt"], True)

    def test_non_exempt_order_records_false(self):
        o = self.s.orders.place("ann", {"TEA-1": 2}, "tok")
        self.assertEqual(o["quote"]["total"], 3000)
        self.assertIs(o["tax_exempt"], False)

    def test_api_place_uses_flag(self):
        self.s.users.set_tax_exempt("ann", True)
        code, body = self.s.api.place_order(login(self.s, "ann"),
                                            {"items": {"MUG-1": 1}, "token": "tok"})
        self.assertEqual(code, 201)
        self.assertEqual(body["order"]["quote"]["total"], 800)

    def test_unknown_customer_name_still_taxed(self):
        o = self.s.orders.place("walk-in", {"TEA-1": 1}, "tok")
        self.assertEqual(o["quote"]["total"], 1500)
        self.assertIs(o["tax_exempt"], False)

    def test_events_of_an_exempt_order_unchanged(self):
        self.s.users.set_tax_exempt("ann", True)
        n = len(self.s.events.events)
        o = self.s.orders.place("ann", {"TEA-1": 1}, "tok")
        self.s.orders.cancel(o["id"])
        self.assertEqual([e["type"] for e in self.s.events.events[n:]],
                         ["stock_taken", "payment_captured", "order_placed",
                          "payment_refunded", "stock_returned", "order_cancelled"])

    def test_flag_at_order_time_is_what_counts(self):
        self.s.users.set_tax_exempt("ann", True)
        a = self.s.orders.place("ann", {"TEA-1": 2}, "tok")       # 2500 exempt
        self.s.users.set_tax_exempt("ann", False)
        b = self.s.orders.place("ann", {"TEA-1": 2}, "tok")       # 3000 taxed
        self.assertEqual(self.s.orders.get(a["id"])["quote"]["total"], 2500)
        self.assertIs(self.s.orders.get(a["id"])["tax_exempt"], True)
        self.assertEqual(self.s.api.get_order(login(self.s, "ann"), {"id": a["id"]})[1]
                         ["order"]["quote"]["tax"], 0)
        self.assertEqual(tax_summary(self.s.orders),
                         {"taxed_orders": 1, "exempt_orders": 1, "tax": 500})
        self.s.users.set_tax_exempt("ann", True)
        self.assertEqual(tax_summary(self.s.orders),
                         {"taxed_orders": 1, "exempt_orders": 1, "tax": 500})
        c = self.s.orders.cancel(b["id"])                        # refund what was charged
        self.assertEqual(self.gw.refunds, [(b["charge_id"], 3000)])
        self.assertEqual(c["refunded"], 3000)
        self.assertEqual(tax_summary(self.s.orders),
                         {"taxed_orders": 0, "exempt_orders": 1, "tax": 0})
        self.assertEqual(sales_summary(self.s.orders),
                         {"orders": 2, "gross": 5500, "refunded": 3000, "net": 2500})
        self.assertEqual(orders_csv(self.s.orders).splitlines(),
                         ["id,customer,status,total", "%s,ann,paid,$25.00" % a["id"],
                          "%s,ann,cancelled,$30.00" % b["id"]])


class Api(unittest.TestCase):
    def setUp(self):
        self.s, _, _ = make_shop()

    def test_codes(self):
        root, ann = login(self.s, "root"), login(self.s, "ann")
        self.assertEqual(self.s.api.set_tax_exempt(ann, {"username": "ann", "exempt": True})[0], 403)
        self.assertFalse(self.s.users.is_tax_exempt("ann"))
        self.assertEqual(self.s.api.set_tax_exempt(root, {"username": "ann", "exempt": "yes"})[0], 400)
        self.assertEqual(self.s.api.set_tax_exempt(root, {"username": 5, "exempt": True})[0], 400)
        self.assertEqual(self.s.api.set_tax_exempt(root, {"username": "ghost", "exempt": True})[0], 404)
        self.assertEqual(self.s.api.set_tax_exempt(root, {"username": "ann", "exempt": True})[0], 200)
        self.assertTrue(self.s.users.is_tax_exempt("ann"))

    def test_permission_comes_from_role_permissions(self):
        self.assertIn("user:edit", auth.ROLE_PERMISSIONS["admin"])
        self.assertNotIn("user:edit", auth.ROLE_PERMISSIONS["customer"])
        auth.ROLE_PERMISSIONS["support"] = {"user:edit"}
        try:
            sup = {"username": "sue", "role": "support"}
            self.assertEqual(self.s.api.set_tax_exempt(sup, {"username": "ann", "exempt": True})[0], 200)
        finally:
            del auth.ROLE_PERMISSIONS["support"]
        self.assertTrue(self.s.users.is_tax_exempt("ann"))


if __name__ == "__main__":
    unittest.main()
