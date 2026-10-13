import unittest

from hidden.helpers import login, make_shop


class Markup(unittest.TestCase):
    def render(self, text):
        s, _, _ = make_shop()
        s.catalog.set_description("TEA-1", text)
        return s.catalog.description_html("TEA-1")

    def test_example_from_ticket(self):
        self.assertEqual(
            self.render("Our **best** green tea.\n\nSee [the farm](https://farm.example/tea)."),
            '<p>Our <strong>best</strong> green tea.</p>\n'
            '<p>See <a href="https://farm.example/tea">the farm</a>.</p>')

    def test_paragraphs_and_line_breaks(self):
        self.assertEqual(self.render("  first line\nsecond line  \n\n\n\nnext para\n"),
                         "<p>first line<br>second line</p>\n<p>next para</p>")
        self.assertEqual(self.render("a\n   \nb"), "<p>a</p>\n<p>b</p>")

    def test_emphasis(self):
        self.assertEqual(self.render("a *soft* and **strong** taste"),
                         "<p>a <em>soft</em> and <strong>strong</strong> taste</p>")

    def test_link_with_formatted_label(self):
        self.assertEqual(self.render("[**Buy** now](https://shop.example/tea/1)"),
                         '<p><a href="https://shop.example/tea/1"><strong>Buy</strong> now</a></p>')

    def test_plain_text(self):
        self.assertEqual(self.render("Smooth, grassy, 100 percent leaf."),
                         "<p>Smooth, grassy, 100 percent leaf.</p>")

    def test_empty(self):
        s, _, _ = make_shop()
        self.assertEqual(s.catalog.description_html("TEA-1"), "")
        s.catalog.set_description("TEA-1", "  \n\n ")
        self.assertEqual(s.catalog.description_html("TEA-1"), "")

    def test_unknown_sku_and_event(self):
        s, _, clock = make_shop()
        with self.assertRaises(KeyError):
            s.catalog.set_description("NOPE-1", "x")
        with self.assertRaises(KeyError):
            s.catalog.description_html("NOPE-1")
        clock.t += 7
        s.catalog.set_description("MUG-1", "Big mug")
        ev = s.events.of_type("description_changed")
        self.assertEqual(len(ev), 1)
        self.assertEqual((ev[0]["sku"], ev[0]["at"]), ("MUG-1", clock.t))

    def test_replacing_description(self):
        s, _, _ = make_shop()
        s.catalog.set_description("MUG-1", "old")
        s.catalog.set_description("MUG-1", "new")
        self.assertEqual(s.catalog.description_html("MUG-1"), "<p>new</p>")


class Handler(unittest.TestCase):
    def test_admin_sets_description(self):
        s, _, _ = make_shop()
        code, body = s.api.set_description(login(s, "root"), {"sku": "MUG-1", "text": "A *big* mug"})
        self.assertEqual(code, 200)
        self.assertEqual(body, {"sku": "MUG-1", "html": "<p>A <em>big</em> mug</p>"})
        self.assertEqual(s.catalog.description_html("MUG-1"), "<p>A <em>big</em> mug</p>")

    def test_errors(self):
        s, _, _ = make_shop()
        root = login(s, "root")
        self.assertEqual(s.api.set_description(login(s, "ann"), {"sku": "MUG-1", "text": "x"})[0], 403)
        self.assertEqual(s.api.set_description(root, {"sku": "MUG-1", "text": 5})[0], 400)
        self.assertEqual(s.api.set_description(root, {"text": "x"})[0], 400)
        self.assertEqual(s.api.set_description(root, {"sku": "NOPE-1", "text": "x"})[0], 404)
        self.assertEqual(s.events.of_type("description_changed"), [])
