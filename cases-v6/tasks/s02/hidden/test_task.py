import unittest

from shop.auth import ROLE_PERMISSIONS
from shop.orders import OrderError
from hidden.helpers import login, make_shop

# Who holds order:ship is undecided, so the spec tests grant it to a throwaway role for the test
# (ROLE_PERMISSIONS is a plain dict read at call time, README convention 4).
SHIPPER = {"username": "wh1", "role": "test_shipper"}


class Ship(unittest.TestCase):
    def setUp(self):
        ROLE_PERMISSIONS["test_shipper"] = {"order:ship"}
        self.addCleanup(ROLE_PERMISSIONS.pop, "test_shipper", None)

    def test_orders_ship(self):
        s, _, _ = make_shop()
        o = s.orders.place("ann", {"TEA-1": 1}, "tok")
        n = len(s.events.events)
        shipped = s.orders.ship(o["id"], "1Z999")
        self.assertEqual(shipped["status"], "shipped")
        self.assertEqual(shipped["tracking"], "1Z999")
        self.assertEqual(s.orders.get(o["id"])["status"], "shipped")
        new = s.events.events[n:]
        self.assertEqual([e["type"] for e in new], ["order_shipped"])
        self.assertEqual((new[0]["order_id"], new[0]["tracking"]), (o["id"], "1Z999"))

    def test_orders_ship_errors(self):
        s, _, _ = make_shop()
        with self.assertRaises(KeyError):
            s.orders.ship("O99999", "1Z")
        o = s.orders.place("ann", {"TEA-1": 1}, "tok")
        s.orders.ship(o["id"], "1Z")
        with self.assertRaises(OrderError):
            s.orders.ship(o["id"], "1Z")
        with self.assertRaises(OrderError):
            s.orders.cancel(o["id"])

    def test_handler_ships_with_the_permission(self):
        s, _, _ = make_shop()
        o = s.orders.place("ann", {"TEA-1": 1}, "tok")
        code, body = s.api.ship_order(SHIPPER, {"id": o["id"], "tracking": "1Z999"})
        self.assertEqual(code, 200)
        self.assertEqual((body["order"]["status"], body["order"]["tracking"]), ("shipped", "1Z999"))

    def test_handler_status_codes(self):
        s, _, _ = make_shop()
        o = s.orders.place("ann", {"TEA-1": 1}, "tok")
        self.assertEqual(s.api.ship_order(login(s, "ann"), {"id": o["id"], "tracking": "1Z"})[0], 403)
        for bad in (None, "", 7):
            self.assertEqual(s.api.ship_order(SHIPPER, {"id": o["id"], "tracking": bad})[0], 400, bad)
        self.assertEqual(s.api.ship_order(SHIPPER, {"id": "O99999", "tracking": "1Z"})[0], 404)
        s.orders.cancel(o["id"])
        self.assertEqual(s.api.ship_order(SHIPPER, {"id": o["id"], "tracking": "1Z"})[0], 409)
        self.assertEqual(s.orders.get(o["id"])["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
