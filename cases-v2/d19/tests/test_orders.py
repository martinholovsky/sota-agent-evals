import unittest
from src.inventory import Inventory
from src.orders import place_order


class T(unittest.TestCase):
    def test_ok(self):
        inv = Inventory({"a": 5})
        place_order(inv, {"a": 2})
        self.assertEqual(inv.stock, {"a": 3})
