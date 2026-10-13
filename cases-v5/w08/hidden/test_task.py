import unittest

from shop.auth import ROLE_PERMISSIONS
from shop.reports import sales_summary
from hidden.helpers import login, make_shop


class PartialRefund(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, _ = make_shop()
        self.o = self.s.orders.place("ann", {"MUG-1": 3}, "tok")       # 2400 + 480 tax = 2880
        self.root = login(self.s, "root")

    def refund(self, amount, who=None, oid=None):
        return self.s.api.refund_order(who or self.root, {"id": oid or self.o["id"], "amount": amount})

    def test_partial_refund(self):
        n = len(self.s.events.events)
        code, body = self.refund(960)
        self.assertEqual(code, 200)
        self.assertEqual((body["order"]["refunded"], body["order"]["status"]), (960, "paid"))
        self.assertEqual(self.s.orders.get(self.o["id"])["refunded"], 960)
        self.assertEqual(self.gw.refunds, [(self.o["charge_id"], 960)])
        new = self.s.events.events[n:]
        self.assertEqual([e["type"] for e in new], ["payment_refunded", "order_refunded"])
        self.assertEqual((new[1]["order_id"], new[1]["amount"]), (self.o["id"], 960))
        self.assertEqual(sales_summary(self.s.orders)["net"], 2880 - 960)

    def test_refund_in_full_over_several_calls(self):
        self.assertEqual(self.refund(2000)[0], 200)
        self.assertEqual(self.refund(881)[0], 409)
        code, body = self.refund(880)
        self.assertEqual((code, body["order"]["status"], body["order"]["refunded"]),
                         (200, "refunded", 2880))
        self.assertEqual(self.refund(1)[0], 409)

    def test_over_refund_changes_nothing(self):
        n = len(self.s.events.events)
        self.assertEqual(self.refund(2881)[0], 409)
        self.assertEqual((self.s.orders.get(self.o["id"])["refunded"], self.gw.refunds), (0, []))
        self.assertEqual(len(self.s.events.events), n)

    def test_errors_and_permission(self):
        self.assertIn("order:refund", ROLE_PERMISSIONS["admin"])
        self.assertNotIn("order:refund", ROLE_PERMISSIONS["customer"])
        self.assertEqual(self.refund(100, who=login(self.s, "ann"))[0], 403)
        for bad in (0, -5, 1.5, "100", True, None):
            with self.subTest(amount=bad):
                self.assertEqual(self.refund(bad)[0], 400)
        self.assertEqual(self.refund(100, oid="O99999")[0], 404)
        self.s.orders.cancel(self.o["id"])
        self.assertEqual(self.refund(100)[0], 409)
        self.assertEqual(self.gw.refunds, [(self.o["charge_id"], 2880)])
