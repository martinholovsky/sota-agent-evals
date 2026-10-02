import unittest
from unittest import mock

from shop import auth
from shop.auth import can
from hidden.helpers import login, make_shop

PW = "support password 1"


class Support(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, _ = make_shop()
        self.s.users.create("sam", PW, "support", "sam@example.com")
        self.s.users.create("bob", "another long password", "customer", "bob@example.com")
        self.a1 = self.s.orders.place("ann", {"TEA-1": 1}, "tok")
        self.b1 = self.s.orders.place("bob", {"MUG-1": 1}, "tok")
        self.a2 = self.s.orders.place("ann", {"MUG-1": 2}, "tok")
        self.sam = self.s.users.login("sam", PW)
        self.ann = login(self.s, "ann")
        self.root = login(self.s, "root")

    def test_role_permissions(self):
        sup = {"username": "sam", "role": "support"}
        self.assertTrue(can(sup, "order:view_any"))
        for p in ("order:place", "order:cancel", "catalog:edit", "report:view", "payment:view"):
            self.assertFalse(can(sup, p), p)
        self.assertTrue(can({"role": "admin"}, "payment:view"))
        self.assertFalse(can({"role": "customer"}, "payment:view"))

    def test_support_views_any_order_without_charge_id(self):
        code, body = self.s.api.get_order(self.sam, {"id": self.b1["id"]})
        self.assertEqual(code, 200)
        self.assertNotIn("charge_id", body["order"])
        expected = {k: v for k, v in self.b1.items() if k != "charge_id"}
        self.assertEqual(body["order"], expected)

    def test_redaction_does_not_touch_stored_order(self):
        self.s.api.get_order(self.sam, {"id": self.a1["id"]})
        self.s.api.list_orders(self.sam, {})
        self.assertEqual(self.s.orders.get(self.a1["id"])["charge_id"], self.a1["charge_id"])
        code, body = self.s.api.get_order(self.root, {"id": self.a1["id"]})
        self.assertEqual((code, body["order"]["charge_id"]), (200, self.a1["charge_id"]))
        self.assertEqual(self.s.api.cancel_order(self.root, {"id": self.a1["id"]})[0], 200)
        self.assertEqual(self.gw.refunds, [(self.a1["charge_id"], 1500)])

    def test_customer_own_order_is_redacted_too(self):
        code, body = self.s.api.get_order(self.ann, {"id": self.a1["id"]})
        self.assertEqual(code, 200)
        self.assertNotIn("charge_id", body["order"])
        self.assertEqual(self.s.api.get_order(self.ann, {"id": self.b1["id"]})[0], 404)

    def test_support_cannot_act(self):
        self.assertEqual(self.s.api.cancel_order(self.sam, {"id": self.a1["id"]})[0], 403)
        self.assertEqual(self.s.api.place_order(self.sam, {"items": {"TEA-1": 1}, "token": "t"})[0], 403)
        self.assertEqual(self.s.orders.get(self.a1["id"])["status"], "paid")
        self.assertEqual(self.s.api.get_order(self.sam, {"id": "O99999"})[0], 404)

    def test_list_all_for_support_and_admin(self):
        ids = sorted([self.a1["id"], self.b1["id"], self.a2["id"]])
        code, body = self.s.api.list_orders(self.sam, {})
        self.assertEqual(code, 200)
        self.assertEqual([o["id"] for o in body["orders"]], ids)
        self.assertTrue(all("charge_id" not in o for o in body["orders"]))
        code, body = self.s.api.list_orders(self.root, {})
        self.assertEqual([o["id"] for o in body["orders"]], ids)
        self.assertTrue(all("charge_id" in o for o in body["orders"]))

    def test_list_own_for_customer(self):
        code, body = self.s.api.list_orders(self.ann, {})
        self.assertEqual(code, 200)
        self.assertEqual([o["id"] for o in body["orders"]], [self.a1["id"], self.a2["id"]])
        self.assertTrue(all("charge_id" not in o for o in body["orders"]))
        # filters narrow, never widen
        self.assertEqual(self.s.api.list_orders(self.ann, {"customer": "bob"}), (200, {"orders": []}))

    def test_filters(self):
        self.s.orders.cancel(self.a2["id"])
        code, body = self.s.api.list_orders(self.sam, {"customer": "ann"})
        self.assertEqual([o["id"] for o in body["orders"]], [self.a1["id"], self.a2["id"]])
        code, body = self.s.api.list_orders(self.sam, {"customer": "ann", "status": "cancelled"})
        self.assertEqual([o["id"] for o in body["orders"]], [self.a2["id"]])
        code, body = self.s.api.list_orders(self.ann, {"status": "paid"})
        self.assertEqual([o["id"] for o in body["orders"]], [self.a1["id"]])
        self.assertEqual(self.s.api.list_orders(self.sam, {"status": 3})[0], 400)
        self.assertEqual(self.s.api.list_orders(self.sam, {"customer": ["ann"]})[0], 400)

    def test_no_permission_is_403(self):
        nobody = {"username": "x", "role": "ghost"}
        self.assertEqual(self.s.api.list_orders(nobody, {})[0], 403)

    def test_reads_emit_no_events(self):
        n = len(self.s.events.events)
        self.s.api.get_order(self.sam, {"id": self.a1["id"]})
        self.s.api.get_order(self.ann, {"id": self.b1["id"]})
        self.s.api.list_orders(self.sam, {})
        self.s.api.list_orders(self.ann, {"customer": "bob"})
        self.assertEqual(len(self.s.events.events), n)

    def test_handlers_follow_permissions_not_role_names(self):
        perms = dict(auth.ROLE_PERMISSIONS)
        perms["auditor"] = {"order:view_any", "payment:view"}
        perms["support"] = {"order:view_own"}
        with mock.patch.dict(auth.ROLE_PERMISSIONS, perms):
            aud = {"username": "eve", "role": "auditor"}
            code, body = self.s.api.list_orders(aud, {})
            self.assertEqual((code, len(body["orders"])), (200, 3))
            self.assertTrue(all("charge_id" in o for o in body["orders"]))
            self.assertEqual(self.s.api.get_order(aud, {"id": self.b1["id"]})[0], 200)
            # support stripped of view_any: sees only its own (none), and others' orders are 404
            self.assertEqual(self.s.api.list_orders(self.sam, {}), (200, {"orders": []}))
            self.assertEqual(self.s.api.get_order(self.sam, {"id": self.b1["id"]})[0], 404)
