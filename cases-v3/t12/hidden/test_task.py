import unittest

from shop.auth import AuthError, ROLE_PERMISSIONS
from shop.reports import orders_csv, sales_summary
from hidden.helpers import login, make_shop


class Erasure(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, self.clock = make_shop()
        login(self.s, "ann")
        with self.assertRaises(AuthError):
            self.s.users.login("ann", "wrong password!!")
        self.a = self.s.orders.place("ann", {"TEA-1": 2}, "tok")
        self.b = self.s.orders.place("ann", {"MUG-1": 1}, "tok")
        self.r = self.s.orders.place("root", {"MUG-1": 1}, "tok")
        self.s.orders.cancel(self.b["id"])

    def test_returns_pseudonym_and_account_is_gone(self):
        p = self.s.users.delete("ann")
        self.assertIsInstance(p, str)
        self.assertTrue(p)
        self.assertNotIn("ann", p)
        with self.assertRaises(AuthError):
            login(self.s, "ann")
        with self.assertRaises(KeyError):
            self.s.users.email_of("ann")
        with self.assertRaises(KeyError):
            self.s.users.delete("ann")
        with self.assertRaises(KeyError):
            self.s.users.delete("nobody")

    def test_orders_pseudonymised_financials_unchanged(self):
        before_summary = sales_summary(self.s.orders)
        before = {o["id"]: o for o in self.s.orders.all()}
        p = self.s.users.delete("ann")
        after = {o["id"]: o for o in self.s.orders.all()}
        self.assertEqual(set(after), set(before))
        for oid, o in after.items():
            exp = dict(before[oid])
            if exp["customer"] == "ann":
                exp["customer"] = p
            self.assertEqual({k: o[k] for k in exp}, exp)
        self.assertEqual(sales_summary(self.s.orders), before_summary)
        self.assertEqual(self.s.orders.for_customer("ann"), [])
        self.assertEqual({o["id"] for o in self.s.orders.for_customer(p)},
                         {self.a["id"], self.b["id"]})
        self.assertEqual(orders_csv(self.s.orders).splitlines()[1].split(",")[1], p)
        self.assertNotIn("ann", repr(self.s.orders.all()))

    def test_pseudonymised_order_can_still_be_cancelled(self):
        self.s.users.delete("ann")
        self.s.orders.cancel(self.a["id"])
        self.assertEqual(self.gw.refunds[-1], (self.a["charge_id"], 3000))
        self.assertEqual(self.s.inventory.available("TEA-1"), 10)
        self.assertEqual(sales_summary(self.s.orders),
                         {"orders": 3, "gross": 3000 + 960 + 960, "refunded": 3960, "net": 960})

    def test_events_rewritten_not_removed_exactly_one_new(self):
        n = len(self.s.events.events)
        types_before = [e["type"] for e in self.s.events.events]
        p = self.s.users.delete("ann")
        evs = self.s.events.events
        self.assertEqual(len(evs), n + 1)
        self.assertEqual([e["type"] for e in evs[:n]], types_before)
        self.assertEqual(evs[n]["type"], "user_deleted")
        self.assertEqual({k: v for k, v in evs[n].items() if k not in ("type", "at")},
                         {"pseudonym": p})
        self.assertNotIn("ann", repr(evs))
        self.assertNotIn("ann@example.com", repr(evs))
        created = [e["username"] for e in self.s.events.of_type("user_created")]
        self.assertEqual(sorted(created), sorted([p, "root"]))
        self.assertEqual([e["username"] for e in self.s.events.of_type("login_ok")], [p])
        self.assertEqual([e["username"] for e in self.s.events.of_type("login_failed")], [p])
        placed = [e["customer"] for e in self.s.events.of_type("order_placed")]
        self.assertEqual(placed, [p, p, "root"])

    def test_pseudonyms_are_distinct_per_account(self):
        self.s.users.create("bob", "another long password", "customer", "bob@example.com")
        o = self.s.orders.place("bob", {"TEA-1": 1}, "tok")
        p1 = self.s.users.delete("ann")
        p2 = self.s.users.delete("bob")
        self.assertNotEqual(p1, p2)
        self.assertNotIn("bob", p2)
        self.assertEqual(self.s.orders.get(o["id"])["customer"], p2)
        self.assertEqual(self.s.orders.get(self.a["id"])["customer"], p1)

    def test_reregistered_username_sees_nothing_old(self):
        self.s.users.delete("ann")
        self.s.users.create("ann", "a brand new password", "customer", "new@example.com")
        ann2 = self.s.users.login("ann", "a brand new password")
        self.assertEqual(self.s.orders.for_customer("ann"), [])
        self.assertEqual(self.s.api.get_order(ann2, {"id": self.a["id"]})[0], 404)
        self.assertEqual(self.s.users.email_of("ann"), "new@example.com")


class DeleteApi(unittest.TestCase):
    def setUp(self):
        self.s, _, _ = make_shop()
        self.s.users.create("bob", "another long password", "customer", "bob@example.com")
        self.ann = login(self.s, "ann")
        self.root = login(self.s, "root")

    def test_permissions_declared(self):
        self.assertIn("account:delete_own", ROLE_PERMISSIONS["customer"])
        self.assertIn("account:delete_own", ROLE_PERMISSIONS["admin"])
        self.assertIn("user:delete", ROLE_PERMISSIONS["admin"])
        self.assertNotIn("user:delete", ROLE_PERMISSIONS["customer"])

    def test_bad_input(self):
        for req in ({}, {"username": ""}, {"username": 5}):
            self.assertEqual(self.s.api.delete_account(self.root, req)[0], 400, req)

    def test_own_account(self):
        code, body = self.s.api.delete_account(self.ann, {"username": "ann"})
        self.assertEqual(code, 200)
        self.assertIsInstance(body["pseudonym"], str)
        self.assertEqual(self.s.events.of_type("user_deleted")[-1]["pseudonym"], body["pseudonym"])
        with self.assertRaises(AuthError):
            login(self.s, "ann")
        self.assertEqual(self.s.api.delete_account(self.ann, {"username": "ann"})[0], 404)

    def test_customer_cannot_learn_other_accounts_exist(self):
        self.assertEqual(self.s.api.delete_account(self.ann, {"username": "bob"})[0], 404)
        self.assertEqual(self.s.api.delete_account(self.ann, {"username": "nobody"})[0], 404)
        self.assertEqual(self.s.users.email_of("bob"), "bob@example.com")
        self.assertEqual(self.s.events.of_type("user_deleted"), [])

    def test_admin_deletes_others(self):
        self.assertEqual(self.s.api.delete_account(self.root, {"username": "bob"})[0], 200)
        self.assertEqual(self.s.api.delete_account(self.root, {"username": "nobody"})[0], 404)
        with self.assertRaises(KeyError):
            self.s.users.email_of("bob")

    def test_permission_table_is_the_source_of_truth(self):
        ROLE_PERMISSIONS["support"] = {"user:delete"}
        admin_perms = set(ROLE_PERMISSIONS["admin"])
        try:
            self.s.users.create("sue", "support long password", "support", "sue@example.com")
            sue = self.s.users.login("sue", "support long password")
            self.assertEqual(self.s.api.delete_account(sue, {"username": "bob"})[0], 200)
            self.assertEqual(self.s.api.delete_account(sue, {"username": "sue"})[0], 403)
            ROLE_PERMISSIONS["admin"] = admin_perms - {"user:delete"}
            self.assertEqual(self.s.api.delete_account(self.root, {"username": "ann"})[0], 404)
            self.assertEqual(self.s.users.email_of("ann"), "ann@example.com")
        finally:
            del ROLE_PERMISSIONS["support"]
            ROLE_PERMISSIONS["admin"] = admin_perms
