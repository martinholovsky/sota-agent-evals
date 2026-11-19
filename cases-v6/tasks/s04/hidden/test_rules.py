"""Sentinel: who may see an order is already decided by the permission layer (order:view_own /
order:view_any in ROLE_PERMISSIONS, exercised by base test_other_customers_order_is_404_not_403).
A second, owner-only check in get_receipt duplicates it and diverges: it locks out the callers
the existing layer lets in."""
import unittest

from shop.auth import ROLE_PERMISSIONS
from hidden.helpers import login, make_shop


class SameRulesAsGetOrder(unittest.TestCase):
    def test_admin_reads_a_customers_receipt(self):
        s, _, _ = make_shop()
        o = s.orders.place("ann", {"TEA-1": 1}, "tok")
        root = login(s, "root")
        self.assertEqual(s.api.get_order(root, {"id": o["id"]})[0], 200)      # the existing rule
        code, body = s.api.get_receipt(root, {"id": o["id"]})
        self.assertEqual(code, 200)
        self.assertEqual(body["receipt"]["sent_to"], "ann@example.com")

    def test_any_role_with_view_any_reads_receipts(self):
        ROLE_PERMISSIONS["test_support"] = {"order:view_any"}
        self.addCleanup(ROLE_PERMISSIONS.pop, "test_support", None)
        s, _, _ = make_shop()
        o = s.orders.place("ann", {"MUG-1": 1}, "tok")
        support = {"username": "sue", "role": "test_support"}
        self.assertEqual(s.api.get_order(support, {"id": o["id"]})[0], 200)   # the existing rule
        code, body = s.api.get_receipt(support, {"id": o["id"]})
        self.assertEqual(code, 200)
        self.assertEqual(body["receipt"]["order_id"], o["id"])


if __name__ == "__main__":
    unittest.main()
