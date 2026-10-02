import unittest
from src.inventory import Inventory
from src.orders import OutOfStock, place_order


class H(unittest.TestCase):
    def test_all_or_nothing(self):
        inv = Inventory({"a": 5, "b": 1})
        with self.assertRaisesRegex(OutOfStock, "b"):
            place_order(inv, {"a": 2, "b": 2})
        self.assertEqual(inv.stock, {"a": 5, "b": 1})

    def test_unknown_sku(self):
        inv = Inventory({"a": 5})
        with self.assertRaises(OutOfStock):
            place_order(inv, {"zzz": 1})
        self.assertEqual(inv.stock, {"a": 5})

    def test_bad_qty(self):
        inv = Inventory({"a": 5})
        for q in [0, -1, 1.5, True]:
            with self.assertRaises(ValueError, msg=q):
                place_order(inv, {"a": q})
        self.assertEqual(inv.stock, {"a": 5})

