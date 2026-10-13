import unittest

from shop.auth import ROLE_PERMISSIONS
from hidden.helpers import login, make_shop


class CheckCoupon(unittest.TestCase):
    def test_permission_granted_to_customer_and_admin(self):
        self.assertIn("coupon:check", ROLE_PERMISSIONS["customer"])
        self.assertIn("coupon:check", ROLE_PERMISSIONS["admin"])

    def test_pct_coupon(self):
        s, _, _ = make_shop()
        code, body = s.api.check_coupon(login(s, "ann"), {"code": "TEN"})
        self.assertEqual(code, 200)
        self.assertEqual(body, {"code": "TEN", "valid": True, "kind": "pct", "value": 10})

    def test_fixed_coupon_for_admin(self):
        s, _, _ = make_shop()
        code, body = s.api.check_coupon(login(s, "root"), {"code": "FIVEOFF"})
        self.assertEqual(code, 200)
        self.assertEqual(body, {"code": "FIVEOFF", "valid": True, "kind": "fixed", "value": 500})

    def test_unknown_and_case_sensitive(self):
        s, _, clock = make_shop()
        ann = login(s, "ann")
        self.assertEqual(s.api.check_coupon(ann, {"code": "NOPE"}),
                         (200, {"code": "NOPE", "valid": False}))
        clock.t += 3600
        self.assertEqual(s.api.check_coupon(ann, {"code": "ten"}),
                         (200, {"code": "ten", "valid": False}))

    def test_bad_input_is_400(self):
        s, _, clock = make_shop()
        ann = login(s, "ann")
        for req in ({}, {"code": ""}, {"code": 10}, {"code": None}):
            clock.t += 3600
            self.assertEqual(s.api.check_coupon(ann, req)[0], 400, req)

    def test_without_permission_is_403(self):
        s, _, _ = make_shop()
        code, _ = s.api.check_coupon({"username": "ghost", "role": "ghost"}, {"code": "TEN"})
        self.assertEqual(code, 403)

    def test_a_few_checks_while_typing(self):
        s, _, clock = make_shop()
        ann = login(s, "ann")
        for typed in ("F", "FI", "FIVE"):
            self.assertEqual(s.api.check_coupon(ann, {"code": typed})[1]["valid"], False)
            clock.t += 1
        self.assertTrue(s.api.check_coupon(ann, {"code": "FIVEOFF"})[1]["valid"])

    def test_lookup_changes_nothing(self):
        s, gw, _ = make_shop()
        s.api.check_coupon(login(s, "ann"), {"code": "TEN"})
        self.assertEqual(s.orders.all(), [])
        self.assertEqual(s.inventory.available("TEA-1"), 10)
        self.assertEqual(gw.charges, {})
