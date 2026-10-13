import unittest

from shop.auth import ROLE_PERMISSIONS
from hidden.helpers import login, make_shop


class CustomerLookup(unittest.TestCase):
    def setUp(self):
        self.s, _, _ = make_shop()
        self.s.users.create("bob", "another long password", "customer", "bob@example.com")
        self.a1 = self.s.orders.place("ann", {"TEA-1": 1}, "tok")
        self.s.orders.place("bob", {"MUG-1": 1}, "tok")
        self.a2 = self.s.orders.place("ann", {"MUG-1": 2}, "tok")
        self.root = login(self.s, "root")

    def test_admin_sees_account_and_orders(self):
        n = len(self.s.events.events)
        code, body = self.s.api.get_customer(self.root, {"username": "ann"})
        self.assertEqual(code, 200)
        c = body["customer"]
        self.assertEqual((c["username"], c["role"], c["email"]),
                         ("ann", "customer", "ann@example.com"))
        self.assertEqual([o["id"] for o in body["orders"]], [self.a1["id"], self.a2["id"]])
        self.assertEqual(body["orders"][0], self.s.orders.get(self.a1["id"]))
        self.assertEqual(len(self.s.events.events), n)

    def test_no_orders_and_admin_accounts(self):
        self.s.users.create("cid", "yet another password", "customer", "cid@example.com")
        code, body = self.s.api.get_customer(self.root, {"username": "cid"})
        self.assertEqual((code, body["orders"]), (200, []))
        code, body = self.s.api.get_customer(self.root, {"username": "root"})
        self.assertEqual(code, 200)
        self.assertEqual((body["customer"]["role"], body["customer"]["email"]),
                         ("admin", "root@example.com"))

    def test_permission(self):
        self.assertIn("customer:view", ROLE_PERMISSIONS["admin"])
        self.assertNotIn("customer:view", ROLE_PERMISSIONS["customer"])
        self.assertEqual(self.s.api.get_customer(login(self.s, "ann"), {"username": "ann"})[0], 403)

    def test_errors(self):
        self.assertEqual(self.s.api.get_customer(self.root, {"username": "nobody"})[0], 404)
        self.assertEqual(self.s.api.get_customer(self.root, {})[0], 400)
        self.assertEqual(self.s.api.get_customer(self.root, {"username": 5})[0], 400)
