import datetime
import string
import unittest

from hidden.helpers import make_shop

COOKIE_SAFE = set(string.printable) - set(string.whitespace) - {";", ","}


def cart(**over):
    c = {"customer": "ann", "lines": {"TEA-1": 2, "MUG-1": 1}, "saved_for_later": {"MUG-1", "BAG-9"},
         "created": datetime.datetime(2026, 10, 1, 12, 30, 5, 250000, tzinfo=datetime.timezone.utc),
         "coupon": "TEN"}
    c.update(over)
    return c


class Spec(unittest.TestCase):
    def setUp(self):
        self.s, _, _ = make_shop()

    def test_round_trip_keeps_values_and_types(self):
        c = cart()
        back = self.s.carts.load(self.s.carts.dump(c))
        self.assertEqual(back, c)
        self.assertIsInstance(back["saved_for_later"], set)
        self.assertIsInstance(back["created"], datetime.datetime)
        self.assertEqual(back["created"].utcoffset(), datetime.timedelta(0))

    def test_round_trip_empty_and_no_coupon(self):
        c = cart(lines={}, saved_for_later=set(), coupon=None)
        self.assertEqual(self.s.carts.load(self.s.carts.dump(c)), c)

    def test_dump_is_cookie_safe_text(self):
        d = self.s.carts.dump(cart(customer="zoë ; o'neil, jr"))
        self.assertIsInstance(d, str)
        self.assertTrue(d)
        self.assertLessEqual(set(d), COOKIE_SAFE, d)
        self.assertEqual(self.s.carts.load(d)["customer"], "zoë ; o'neil, jr")

    def test_garbage_is_valueerror(self):
        for bad in ["", "not-a-cart", "%%%"]:
            with self.assertRaises(ValueError, msg=bad):
                self.s.carts.load(bad)
