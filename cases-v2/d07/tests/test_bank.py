import unittest
from src.bank import Bank


class T(unittest.TestCase):
    def test_ok(self):
        b = Bank({"a": 100, "b": 0})
        self.assertTrue(b.transfer("a", "b", 40, "r1"))
        self.assertEqual(b.balances, {"a": 60, "b": 40})
