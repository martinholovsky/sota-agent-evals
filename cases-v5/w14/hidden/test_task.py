import re
import unittest

from shop.cart import Cart, CartLine


def sample():
    c = Cart("ann", coupon="TEN")
    c.add("TEA-1", 2, "Happy birthday, Zoë! 🎂")
    c.add("MUG-1", 1)
    c.add("TEA-1", 1, 'with "quotes" & <brackets>')
    return c


class SavedCart(unittest.TestCase):
    def test_round_trip(self):
        c = sample()
        back = Cart.restore(c.export())
        self.assertEqual(back, c)
        self.assertIsInstance(back, Cart)
        self.assertEqual(back.lines[0], CartLine("TEA-1", 2, "Happy birthday, Zoë! 🎂"))
        self.assertEqual(back.items(), {"TEA-1": 3, "MUG-1": 1})

    def test_round_trip_empty_and_no_coupon(self):
        c = Cart("bob")
        self.assertEqual(Cart.restore(c.export()), c)
        c.add("MUG-1", 4)
        self.assertEqual(Cart.restore(c.export()), c)

    def test_export_is_url_safe(self):
        s = sample().export()
        self.assertIsInstance(s, str)
        self.assertRegex(s, re.compile(r"[A-Za-z0-9_=-]+"))
        self.assertTrue(re.fullmatch(r"[A-Za-z0-9_=-]+", s))

    def test_restored_cart_is_independent(self):
        c = sample()
        text = c.export()
        a, b = Cart.restore(text), Cart.restore(text)
        a.add("MUG-1", 1)
        self.assertEqual(b, c)

    def test_bad_strings(self):
        good = sample().export()
        for bad in ["", "hello", "!!!!", good[:-6], good[: len(good) // 2]]:
            with self.assertRaises(ValueError, msg=bad[:20]):
                Cart.restore(bad)
