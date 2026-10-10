import csv
import io
import unittest

from hidden.helpers import make_shop
from shop import reports


def rows(text):
    return list(csv.reader(io.StringIO(text)))


class Spec(unittest.TestCase):
    def test_header_and_rows_in_listing_order(self):
        s, _, _ = make_shop()                    # MUG-1 Mug 800, TEA-1 Green tea 1250
        s.catalog.add("POT-1", "Big teapot", 3000)
        self.assertEqual(rows(reports.products_csv(s.catalog)), [
            ["sku", "name", "price"],
            ["MUG-1", "Mug", "$8.00"],
            ["POT-1", "Big teapot", "$30.00"],
            ["TEA-1", "Green tea", "$12.50"],
        ])

    def test_inactive_products_are_left_out(self):
        s, _, _ = make_shop()
        s.catalog._products["MUG-1"]["active"] = False
        self.assertEqual([r[0] for r in rows(reports.products_csv(s.catalog))], ["sku", "TEA-1"])

    def test_returns_str(self):
        s, _, _ = make_shop()
        self.assertIsInstance(reports.products_csv(s.catalog), str)
