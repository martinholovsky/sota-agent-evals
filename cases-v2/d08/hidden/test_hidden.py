import unittest
from src.wrap import wrap


class H(unittest.TestCase):
    def test_paragraphs(self):
        self.assertEqual(wrap("one two\nthree\n\n\n\nfour", 9), "one two\nthree\n\nfour")

    def test_long_word(self):
        self.assertEqual(wrap("abcdefghij x", 4), "abcd\nefgh\nij x")

    def test_exact_width(self):
        self.assertEqual(wrap("abcd efgh", 4), "abcd\nefgh")

    def test_trim(self):
        self.assertEqual(wrap("\n\n  hi  \n\n", 10), "hi")

    def test_invalid(self):
        with self.assertRaises(ValueError):
            wrap("x", 0)
