import unittest
from src.csvline import parse_line


class H(unittest.TestCase):
    def test_quotes(self):
        self.assertEqual(parse_line('"a,b",c'), ["a,b", "c"])
        self.assertEqual(parse_line('"say ""hi""",x'), ['say "hi"', "x"])

    def test_empties(self):
        self.assertEqual(parse_line(""), [""])
        self.assertEqual(parse_line("a,"), ["a", ""])
        self.assertEqual(parse_line(",,"), ["", "", ""])
        self.assertEqual(parse_line('""'), [""])

    def test_verbatim_and_sep(self):
        self.assertEqual(parse_line(" a ; b ", sep=";"), [" a ", " b "])

    def test_errors(self):
        for bad in ['"open', '"a"b,c', 'x,"y']:
            with self.assertRaises(ValueError, msg=bad):
                parse_line(bad)
