import unittest
from src.template import render


class H(unittest.TestCase):
    def test_escaped(self):
        import html, re
        raw = "<a href=\"q\">&'</a>"
        out = render("{{ x }}", {"x": raw})
        self.assertIsNone(re.search(r"[<>\"']", out), out)        # any valid entity form is fine
        self.assertIsNone(re.search(r"&(?![a-zA-Z]+;|#[0-9]+;|#x[0-9a-fA-F]+;)", out), out)
        self.assertEqual(html.unescape(out), raw)

    def test_raw(self):
        self.assertEqual(render("{{{x}}}", {"x": "<b>"}), "<b>")
        self.assertEqual(render("{{{ x }}}|{{x}}", {"x": "<b>"}), "<b>|&lt;b&gt;")

    def test_non_string_and_spaces(self):
        self.assertEqual(render("{{   n   }}", {"n": 5}), "5")

    def test_missing(self):
        with self.assertRaisesRegex(KeyError, "who"):
            render("{{ who }}", {})
