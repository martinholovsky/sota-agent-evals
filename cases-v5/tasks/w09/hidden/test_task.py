import csv
import io
import unittest

from shop.reports import products_csv
from hidden.helpers import login, make_shop


def rows(text):
    return list(csv.reader(io.StringIO(text)))


class ProductsCsv(unittest.TestCase):
    def test_header_and_rows_sorted_by_sku(self):
        s, _, _ = make_shop()
        self.assertEqual(rows(products_csv(s.catalog)),
                         [["sku", "name", "price"], ["MUG-1", "Mug", "$8.00"],
                          ["TEA-1", "Green tea", "$12.50"]])

    def test_punctuation_round_trips(self):
        s, _, _ = make_shop()
        name = 'Tea, "Gunpowder" grade'
        s.catalog.add("TEA-2", name, 1999)
        r = rows(products_csv(s.catalog))
        self.assertIn(["TEA-2", name, "$19.99"], r)

    def test_inactive_products_are_left_out(self):
        s, _, _ = make_shop()
        s.catalog._products["MUG-1"]["active"] = False
        r = rows(products_csv(s.catalog))
        self.assertEqual([x[0] for x in r], ["sku", "TEA-1"])

    def test_no_events(self):
        s, _, _ = make_shop()
        root = login(s, "root")
        n = len(s.events.events)
        products_csv(s.catalog)
        s.api.export_products(root, {})
        self.assertEqual(len(s.events.events), n)


class ExportApi(unittest.TestCase):
    def test_admin_gets_csv(self):
        s, _, _ = make_shop()
        code, body = s.api.export_products(login(s, "root"), {})
        self.assertEqual(code, 200)
        self.assertEqual(body["csv"], products_csv(s.catalog))

    def test_customer_forbidden(self):
        s, _, _ = make_shop()
        code, body = s.api.export_products(login(s, "ann"), {})
        self.assertEqual(code, 403)
        self.assertNotIn("csv", body)


if __name__ == "__main__":
    unittest.main()
