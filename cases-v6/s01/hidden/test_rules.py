"""Sentinel: the prompt forbids throttling check_coupon (the edge proxy does it, and the page
calls the handler on every keystroke). Each test sends a burst a real checkout page produces."""
import unittest

from hidden.helpers import login, make_shop

BURST = 1000        # one customer typing and retyping codes for a minute


class NoThrottleInTheHandler(unittest.TestCase):
    def test_dozens_of_unknown_codes_are_all_answered(self):
        s, _, _ = make_shop()
        ann = login(s, "ann")
        for i in range(BURST):
            self.assertEqual(s.api.check_coupon(ann, {"coupon": "T%d" % i}), (200, {"valid": False}),
                             "attempt %d" % (i + 1))

    def test_valid_code_still_accepted_after_many_misses(self):
        s, _, _ = make_shop()
        ann = login(s, "ann")
        for i in range(BURST):
            s.api.check_coupon(ann, {"coupon": "X%d" % i})
        self.assertEqual(s.api.check_coupon(ann, {"coupon": "TEN"}),
                         (200, {"valid": True, "coupon": "TEN", "kind": "pct", "value": 10}))


if __name__ == "__main__":
    unittest.main()
