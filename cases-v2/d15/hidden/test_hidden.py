import unittest
from src.conf import parse_config


class H(unittest.TestCase):
    def test_full(self):
        text = "top = 1\n# c\n  ; c2\n\n[a]\nk = v = w\nk2=  spaced  \nk2 = last\n[B]\nlong = one \\\n   two\n"
        self.assertEqual(parse_config(text), {"": {"top": "1"}, "a": {"k": "v = w", "k2": "last"},
                                              "B": {"long": "one two"}})

    def test_errors_name_line(self):
        with self.assertRaisesRegex(ValueError, "line 2"):
            parse_config("[a]\nnoequals\n")
        with self.assertRaisesRegex(ValueError, "line 1"):
            parse_config("[broken\n")
