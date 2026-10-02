import csv
import io
import unittest
from src.export import to_csv


def cells(s):
    return [c for row in csv.reader(io.StringIO(s)) for c in row]


class H(unittest.TestCase):
    def test_formula_neutralised(self):
        out = cells(to_csv([["=HYPERLINK(\"http://x\")", "+1+1", "-2+3", "@SUM(A1)", "\t=1", "\r=1"]]))
        for c in out:
            self.assertFalse(c[:1] in "=+-@\t\r", c)

    def test_ordinary_values_unchanged(self):
        self.assertEqual(cells(to_csv([["hello", "a=b", "x-y", "12"]])), ["hello", "a=b", "x-y", "12"])

    def test_non_string_numbers_kept(self):
        self.assertEqual(cells(to_csv([[3, -4]])), ["3", "-4"])
