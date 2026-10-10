import unittest

from hidden.helpers import login, make_shop


def setup():
    s, _, _ = make_shop()                        # TEA-1 1250, MUG-1 800
    s.catalog.add("POT-1", "Teapot", 3000)
    s.catalog.add("SPN-1", "Spoon", 150)
    s.catalog.add("CUP-1", "Cup", 600)
    return s, login(s, "ann")


def all_pages(s, who, limit, max_pages=500):
    """Follow next_cursor from the first page; return the list of pages (lists of items)."""
    pages, cursor = [], None
    for _ in range(max_pages):
        status, body = s.api.list_products(who, {"limit": limit, "cursor": cursor})
        assert status == 200, (status, body)
        pages.append(body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            return pages
    raise AssertionError("next_cursor never became None after %d pages" % max_pages)


class Spec(unittest.TestCase):
    def test_pages_in_price_order_until_exhausted(self):
        s, ann = setup()
        pages = all_pages(s, ann, 2)
        self.assertEqual([[p["sku"] for p in pg] for pg in pages],
                         [["SPN-1", "CUP-1"], ["MUG-1", "TEA-1"], ["POT-1"]])
        self.assertEqual(pages[0][0], s.catalog.get("SPN-1"))

    def test_single_page_has_no_next_cursor(self):
        s, ann = setup()
        status, body = s.api.list_products(ann, {"limit": 5, "cursor": None})
        self.assertEqual(status, 200)
        self.assertEqual(len(body["items"]), 5)
        self.assertIsNone(body["next_cursor"])

    def test_first_page_without_cursor_key(self):
        s, ann = setup()
        status, body = s.api.list_products(ann, {"limit": 1})
        self.assertEqual((status, body["items"][0]["sku"]), (200, "SPN-1"))
        self.assertIsNotNone(body["next_cursor"])

    def test_admin_may_list(self):
        s, _ = setup()
        self.assertEqual(s.api.list_products(login(s, "root"), {"limit": 3})[0], 200)

    def test_bad_limit_is_400(self):
        s, ann = setup()
        for bad in (0, -1, "5", None, True):
            self.assertEqual(s.api.list_products(ann, {"limit": bad})[0], 400, bad)

    def test_foreign_cursor_is_400(self):
        s, ann = setup()
        self.assertEqual(s.api.list_products(ann, {"limit": 2, "cursor": "garbage!"})[0], 400)
