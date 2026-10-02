import unittest
from src.payments import PaymentService


class GW:
    def __init__(self):
        self.calls = 0

    def charge(self, amount):
        self.calls += 1
        return "ch_%d" % self.calls


class T(unittest.TestCase):
    def test_charges(self):
        self.assertEqual(PaymentService(GW()).charge("k1", 100), "ch_1")
