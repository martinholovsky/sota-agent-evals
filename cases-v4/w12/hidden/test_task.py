import unittest

from hidden.helpers import make_shop


def skus(products):
    return [p["sku"] for p in products]


class Spec(unittest.TestCase):
    def test_case_insensitive_substring(self):
        s, _, _ = make_shop()                    # TEA-1 "Green tea", MUG-1 "Mug"
        self.assertEqual(skus(s.catalog.search("TEA")), ["TEA-1"])
        self.assertEqual(skus(s.catalog.search("u")), ["MUG-1"])
        self.assertEqual(skus(s.catalog.search("een t")), ["TEA-1"])

    def test_wildcard(self):
        s, _, _ = make_shop()
        self.assertEqual(skus(s.catalog.search("gr*tea")), ["TEA-1"])
        self.assertEqual(skus(s.catalog.search("m*g")), ["MUG-1"])
        self.assertEqual(skus(s.catalog.search("green*tea")), ["TEA-1"])
        self.assertEqual(skus(s.catalog.search("*")), ["MUG-1", "TEA-1"])
        self.assertEqual(skus(s.catalog.search("tea*mug")), [])

    def test_wildcard_matches_empty_run(self):
        s, _, _ = make_shop()
        self.assertEqual(skus(s.catalog.search("mu*g")), ["MUG-1"])

    def test_results_in_listing_form_and_order(self):
        s, _, _ = make_shop()
        s.catalog.add("ATEA-1", "Black tea", 900)
        res = s.catalog.search("tea")
        self.assertEqual(skus(res), ["ATEA-1", "TEA-1"])
        self.assertEqual(res[1], s.catalog.get("TEA-1"))

    def test_no_match_is_empty(self):
        s, _, _ = make_shop()
        self.assertEqual(s.catalog.search("coffee"), [])

    def test_inactive_products_are_left_out(self):
        s, _, _ = make_shop()
        s.catalog._products["TEA-1"]["active"] = False
        self.assertEqual(s.catalog.search("tea"), [])
