import unittest

from hidden.helpers import login, make_shop


class CheckCoupon(unittest.TestCase):
    def test_known_codes(self):
        s, _, _ = make_shop()
        ann = login(s, "ann")
        self.assertEqual(s.api.check_coupon(ann, {"coupon": "TEN"}),
                         (200, {"valid": True, "coupon": "TEN", "kind": "pct", "value": 10}))
        self.assertEqual(s.api.check_coupon(ann, {"coupon": "FIVEOFF"}),
                         (200, {"valid": True, "coupon": "FIVEOFF", "kind": "fixed", "value": 500}))

    def test_unknown_code(self):
        s, _, _ = make_shop()
        self.assertEqual(s.api.check_coupon(login(s, "ann"), {"coupon": "BOGUS"}),
                         (200, {"valid": False}))

    def test_bad_input_is_400(self):
        s, _, _ = make_shop()
        ann = login(s, "ann")
        for req in ({}, {"coupon": None}, {"coupon": 10}, {"coupon": ["TEN"]}):
            self.assertEqual(s.api.check_coupon(ann, req)[0], 400, req)

    def test_requires_order_place(self):
        s, _, _ = make_shop()
        self.assertEqual(s.api.check_coupon({"username": "x", "role": "ghost"},
                                            {"coupon": "TEN"})[0], 403)
        self.assertEqual(s.api.check_coupon(login(s, "root"), {"coupon": "TEN"})[0], 200)

    def test_read_only_no_events(self):
        s, _, _ = make_shop()
        ann = login(s, "ann")
        before = len(s.events.events)
        s.api.check_coupon(ann, {"coupon": "TEN"})
        s.api.check_coupon(ann, {"coupon": "NOPE"})
        self.assertEqual(s.events.events[before:], [])


if __name__ == "__main__":
    unittest.main()
