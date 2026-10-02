import unittest
from src.pages import paginate


class H(unittest.TestCase):
    def test_all_items_once(self):
        items = list(range(10))
        n = paginate(items, 1, 3)["total_pages"]
        self.assertEqual(n, 4)
        got = [x for p in range(1, n + 1) for x in paginate(items, p, 3)["items"]]
        self.assertEqual(got, items)

    def test_edges(self):
        self.assertEqual(paginate([], 1, 5), {"items": [], "total_pages": 1})
        self.assertEqual(paginate([1, 2], 5, 2)["items"], [])
        for p, pp in [(0, 2), (1, 0)]:
            with self.assertRaises(ValueError):
                paginate([1], p, pp)
