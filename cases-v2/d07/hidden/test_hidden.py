import unittest
from src.bank import Bank, InsufficientFunds


class H(unittest.TestCase):
    def test_insufficient_changes_nothing(self):
        b = Bank({"a": 10, "b": 0})
        with self.assertRaises(InsufficientFunds):
            b.transfer("a", "b", 11, "r")
        self.assertEqual((b.balances, b.ledger), ({"a": 10, "b": 0}, []))

    def test_idempotent(self):
        b = Bank({"a": 100, "b": 0})
        self.assertTrue(b.transfer("a", "b", 10, "r"))
        self.assertFalse(b.transfer("a", "b", 10, "r"))
        self.assertEqual((b.balances["a"], len(b.ledger)), (90, 1))
        with self.assertRaises(ValueError):
            b.transfer("a", "b", 20, "r")

    def test_validation(self):
        b = Bank({"a": 100, "b": 0})
        for args in [("a", "b", 0, "x"), ("a", "b", -5, "y"), ("a", "a", 5, "z"),
                     ("a", "nope", 5, "w"), ("a", "b", 1.5, "v")]:
            with self.assertRaises(ValueError, msg=args):
                b.transfer(*args)
        self.assertEqual(b.balances, {"a": 100, "b": 0})

