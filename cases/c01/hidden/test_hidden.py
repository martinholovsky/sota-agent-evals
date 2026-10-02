import unittest
from src.text import slugify


class H(unittest.TestCase):
    def test_runs(self):
        self.assertEqual(slugify("a -- b"), "a-b")

    def test_edges(self):
        self.assertEqual(slugify("--x--"), "x")
        self.assertEqual(slugify(""), "")

    def test_digits(self):
        self.assertEqual(slugify("Top 10 Tips"), "top-10-tips")
