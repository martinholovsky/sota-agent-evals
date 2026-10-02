import inspect
import unittest
import warnings

import src.cart
from src import pricing


class H(unittest.TestCase):
    def test_new_name(self):
        self.assertEqual(pricing.total_price(3, 100, 50), 150)

    def test_alias_still_works(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.assertEqual(pricing.calc(1, 999, 10), 899)

    def test_callers_updated(self):
        self.assertNotIn("calc(", inspect.getsource(src.cart))
        self.assertEqual(src.cart.cart_total([(2, 150, 0), (1, 999, 10)]), 1199)
