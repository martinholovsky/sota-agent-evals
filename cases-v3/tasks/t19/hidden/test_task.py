import unittest

import shop.auth as auth
from shop.inventory import OutOfStock
from shop.payments import GatewayError
from hidden.helpers import login, make_shop


def lows(s, since=0):
    return [(e["sku"], e["available"], e["threshold"])
            for e in s.events.events[since:] if e["type"] == "stock_low"]


class Threshold(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, self.clock = make_shop()     # TEA-1: 10, MUG-1: 5

    def test_set_and_get(self):
        self.assertIsNone(self.s.inventory.threshold("TEA-1"))
        n = len(self.s.events.events)
        self.s.inventory.set_threshold("TEA-1", 4)
        evs = self.s.events.events[n:]
        self.assertEqual([(e["type"], e["sku"], e["threshold"]) for e in evs],
                         [("stock_threshold_set", "TEA-1", 4)])
        self.assertEqual(self.s.inventory.threshold("TEA-1"), 4)

    def test_invalid(self):
        for bad in (-1, 1.5, True, "3", None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.s.inventory.set_threshold("TEA-1", bad)
        self.assertEqual(self.s.events.of_type("stock_threshold_set"), [])

    def test_setting_never_alerts(self):
        self.s.inventory.set_threshold("MUG-1", 50)       # already below
        self.s.inventory.set_threshold("MUG-1", 6)
        self.assertEqual(lows(self.s), [])


class Crossing(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, self.clock = make_shop()
        self.s.inventory.set_threshold("TEA-1", 5)

    def test_direct_take_alerts_after_stock_taken(self):
        n = len(self.s.events.events)
        self.s.inventory.take_all({"TEA-1": 5})          # 10 -> 5: still at threshold
        self.assertEqual(lows(self.s, n), [])
        self.s.inventory.take_all({"TEA-1": 1})          # 5 -> 4: crosses
        self.assertEqual([e["type"] for e in self.s.events.events[n:]],
                         ["stock_taken", "stock_taken", "stock_low"])
        self.assertEqual(lows(self.s, n), [("TEA-1", 4, 5)])

    def test_only_once_while_below(self):
        self.s.inventory.take_all({"TEA-1": 7})          # 10 -> 3
        self.s.inventory.take_all({"TEA-1": 1})          # 3 -> 2
        self.s.inventory.take_all({"TEA-1": 2})          # 2 -> 0
        self.assertEqual(lows(self.s), [("TEA-1", 3, 5)])

    def test_rearm_only_at_or_above(self):
        self.s.inventory.take_all({"TEA-1": 7})          # 3, alert
        self.s.inventory.receive("TEA-1", 1)             # 4: still below, no re-arm
        self.s.inventory.take_all({"TEA-1": 1})          # 3: no alert
        self.s.inventory.receive("TEA-1", 2)             # 5: at threshold, re-armed
        self.s.inventory.take_all({"TEA-1": 1})          # 4: alert
        self.s.inventory.receive("TEA-1", 20)            # 24: no alert on restock
        self.assertEqual(lows(self.s), [("TEA-1", 3, 5), ("TEA-1", 4, 5)])

    def test_out_of_stock_take_emits_nothing(self):
        n = len(self.s.events.events)
        with self.assertRaises(OutOfStock):
            self.s.inventory.take_all({"TEA-1": 7, "MUG-1": 99})
        self.assertEqual(self.s.events.events[n:], [])

    def test_multi_line_order_of_alerts(self):
        self.s.inventory.set_threshold("MUG-1", 5)
        n = len(self.s.events.events)
        self.s.inventory.take_all({"MUG-1": 1, "TEA-1": 6})
        self.assertEqual(lows(self.s, n), [("MUG-1", 4, 5), ("TEA-1", 4, 5)])

    def test_threshold_zero_never_alerts(self):
        self.s.inventory.set_threshold("MUG-1", 0)
        self.s.inventory.take_all({"MUG-1": 5})
        self.assertEqual(lows(self.s), [])

    def test_raising_threshold_above_stock_then_take(self):
        self.s.inventory.set_threshold("TEA-1", 12)      # stock 10 already below
        self.s.inventory.take_all({"TEA-1": 1})
        self.assertEqual(lows(self.s), [])


class Orders(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, self.clock = make_shop()
        self.s.inventory.set_threshold("TEA-1", 5)

    def test_order_alert_after_order_placed(self):
        n = len(self.s.events.events)
        self.s.orders.place("ann", {"MUG-1": 1, "TEA-1": 6}, "tok")
        self.assertEqual([e["type"] for e in self.s.events.events[n:]],
                         ["stock_taken", "payment_captured", "order_placed", "stock_low"])
        self.assertEqual(lows(self.s, n), [("TEA-1", 4, 5)])

    def test_two_alerts_in_item_order(self):
        self.s.inventory.set_threshold("MUG-1", 3)
        n = len(self.s.events.events)
        self.s.orders.place("ann", {"TEA-1": 6, "MUG-1": 3}, "tok")
        self.assertEqual([e["type"] for e in self.s.events.events[n:]],
                         ["stock_taken", "payment_captured", "order_placed",
                          "stock_low", "stock_low"])
        self.assertEqual(lows(self.s, n), [("TEA-1", 4, 5), ("MUG-1", 2, 3)])

    def test_failed_payment_never_alerts(self):
        n = len(self.s.events.events)
        with self.assertRaises(GatewayError):
            self.s.orders.place("ann", {"TEA-1": 8}, "tok_declined")
        self.assertEqual(lows(self.s, n), [])
        self.assertEqual([e["type"] for e in self.s.events.events[n:]],
                         ["stock_taken", "stock_returned"])
        self.assertEqual(self.s.inventory.available("TEA-1"), 10)
        # the failed attempt did not use up the alert: the real crossing still alerts
        self.s.orders.place("ann", {"TEA-1": 8}, "tok")
        self.assertEqual(lows(self.s, n), [("TEA-1", 2, 5)])

    def test_out_of_stock_order_never_alerts(self):
        n = len(self.s.events.events)
        with self.assertRaises(OutOfStock):
            self.s.orders.place("ann", {"TEA-1": 8, "MUG-1": 99}, "tok")
        self.assertEqual(self.s.events.events[n:], [])

    def test_cancel_rearms_without_alerting(self):
        o = self.s.orders.place("ann", {"TEA-1": 6}, "tok")      # 4: alert
        n = len(self.s.events.events)
        self.s.orders.cancel(o["id"])                              # 10: no alert
        self.assertEqual([e["type"] for e in self.s.events.events[n:]],
                         ["payment_refunded", "stock_returned", "order_cancelled"])
        self.s.orders.place("ann", {"TEA-1": 6}, "tok")          # 4: alert again
        self.assertEqual(lows(self.s), [("TEA-1", 4, 5), ("TEA-1", 4, 5)])

    def test_orders_without_thresholds_unchanged(self):
        n = len(self.s.events.events)
        self.s.orders.place("ann", {"MUG-1": 5}, "tok")
        self.assertEqual([e["type"] for e in self.s.events.events[n:]],
                         ["stock_taken", "payment_captured", "order_placed"])


class Api(unittest.TestCase):
    def setUp(self):
        self.s, _, _ = make_shop()
        self.root, self.ann = login(self.s, "root"), login(self.s, "ann")

    def test_codes(self):
        f = self.s.api.set_stock_threshold
        self.assertEqual(f(self.ann, {"sku": "TEA-1", "threshold": 3})[0], 403)
        self.assertIsNone(self.s.inventory.threshold("TEA-1"))
        self.assertEqual(f(self.root, {"sku": "TEA-1", "threshold": -1})[0], 400)
        self.assertEqual(f(self.root, {"sku": "TEA-1", "threshold": "3"})[0], 400)
        self.assertEqual(f(self.root, {"sku": 7, "threshold": 3})[0], 400)
        self.assertEqual(f(self.root, {"sku": "NOPE-1", "threshold": 3})[0], 404)
        self.assertIsNone(self.s.inventory.threshold("NOPE-1"))
        self.assertEqual(f(self.root, {"sku": "TEA-1", "threshold": 3})[0], 200)
        self.assertEqual(self.s.inventory.threshold("TEA-1"), 3)

    def test_permission_comes_from_role_permissions(self):
        self.assertIn("inventory:edit", auth.ROLE_PERMISSIONS["admin"])
        self.assertNotIn("inventory:edit", auth.ROLE_PERMISSIONS["customer"])
        auth.ROLE_PERMISSIONS["warehouse"] = {"inventory:edit"}
        try:
            wh = {"username": "wes", "role": "warehouse"}
            self.assertEqual(self.s.api.set_stock_threshold(
                wh, {"sku": "MUG-1", "threshold": 2})[0], 200)
        finally:
            del auth.ROLE_PERMISSIONS["warehouse"]


if __name__ == "__main__":
    unittest.main()
