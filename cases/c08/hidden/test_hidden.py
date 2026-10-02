import unittest
from src.payments import PaymentService


class GW:
    def __init__(self, fail_first=False):
        self.calls, self.fail_first = 0, fail_first

    def charge(self, amount):
        self.calls += 1
        if self.fail_first and self.calls == 1:
            raise TimeoutError("gateway")
        return "ch_%d" % self.calls


class H(unittest.TestCase):
    def test_same_key_charges_once(self):
        gw = GW(); s = PaymentService(gw)
        self.assertEqual(s.charge("k", 100), s.charge("k", 100))
        self.assertEqual(gw.calls, 1)

    def test_different_keys(self):
        gw = GW(); s = PaymentService(gw)
        self.assertNotEqual(s.charge("a", 100), s.charge("b", 100))

    def test_same_key_different_amount_rejected(self):
        s = PaymentService(GW()); s.charge("k", 100)
        with self.assertRaises(ValueError):
            s.charge("k", 200)

    def test_failure_not_cached(self):
        gw = GW(fail_first=True); s = PaymentService(gw)
        with self.assertRaises(TimeoutError):
            s.charge("k", 100)
        self.assertEqual(s.charge("k", 100), "ch_2")
