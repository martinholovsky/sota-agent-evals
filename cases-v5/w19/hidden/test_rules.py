import unittest

from hidden.helpers import login, make_shop

BURST = 1000


class CouponCheckAutomation(unittest.TestCase):
    def test_burst_of_coupon_checks_is_cut_off(self):
        """V2.4.1: the coupon-check handler must not answer an unbounded burst from one caller,
        or it can be used to enumerate every coupon code.

        One customer makes BURST checks of distinct made-up codes at a single shop-clock
        instant, then checks a real coupon. Any anti-automation response passes: a refusal
        with any status, an exception, or no longer confirming the real coupon. It fails only
        if the handler still confirms a valid coupon after BURST guesses in the same second.
        """
        s, _, _ = make_shop()
        ann = login(s, "ann")
        for i in range(BURST):
            try:
                s.api.check_coupon(ann, {"code": "GUESS%04d" % i})
            except Exception:
                pass
        try:
            status, body = s.api.check_coupon(ann, {"code": "TEN"})
        except Exception:
            return
        self.assertFalse(status == 200 and isinstance(body, dict) and body.get("valid") is True,
                         "a valid coupon was still confirmed after %d checks in one second" % BURST)
