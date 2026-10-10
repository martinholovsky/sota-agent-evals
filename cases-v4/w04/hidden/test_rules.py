"""Rule tests: server-side page-size maximum, and a cursor that does not shift when a row is
inserted mid-scan (sota-api-design rules/01 section 4). Neither is stated in the prompt."""
import unittest

from hidden.helpers import login, make_shop
from hidden.test_task import all_pages, setup


class Pagination(unittest.TestCase):
    def test_huge_limit_is_capped_or_rejected(self):
        s, _, _ = make_shop()
        for i in range(2000):
            s.catalog.add("P-%04d" % i, "Product %d" % i, 100 + i)
        ann = login(s, "ann")
        total = len(s.catalog.listing())
        status, body = s.api.list_products(ann, {"limit": 1_000_000})
        if 400 <= status < 500:
            return                                   # rejecting the oversized limit complies
        self.assertEqual(status, 200)
        self.assertLess(len(body["items"]), total)   # one request cannot pull the whole table
        self.assertIsNotNone(body["next_cursor"])
        seen = [p["sku"] for pg in all_pages(s, ann, 1_000_000) for p in pg]
        self.assertEqual(sorted(seen), sorted(p["sku"] for p in s.catalog.listing()))

    def test_product_added_mid_scan_shifts_nothing(self):
        s, ann = setup()                          # prices 150 600 800 1250 3000
        status, body = s.api.list_products(ann, {"limit": 2, "cursor": None})
        self.assertEqual(status, 200)
        first = [p["sku"] for p in body["items"]]
        s.catalog.add("NEW-1", "Cheaper than page one", 50)    # lands before page 1
        seen, cursor = list(first), body["next_cursor"]
        for _ in range(50):
            status, body = s.api.list_products(ann, {"limit": 2, "cursor": cursor})
            self.assertEqual(status, 200)
            seen += [p["sku"] for p in body["items"]]
            cursor = body["next_cursor"]
            if cursor is None:
                break
        originals = ["SPN-1", "CUP-1", "MUG-1", "TEA-1", "POT-1"]
        dup = sorted({x for x in seen if seen.count(x) > 1})
        self.assertEqual(dup, [], "returned twice after an insert mid-scan")
        self.assertEqual([x for x in originals if x not in seen], [],
                         "skipped after an insert mid-scan")
