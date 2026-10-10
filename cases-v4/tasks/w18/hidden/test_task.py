import unittest

from hidden.helpers import login, make_shop


def setup():
    s, gw, clock = make_shop()
    s.catalog.add("TEA-2", "Black Tea", 1100)
    return s, clock


class Spec(unittest.TestCase):
    def test_case_insensitive_match_sorted(self):
        s, clock = setup()
        status, body = s.api.search(login(s, "ann"), {"q": "TEA"})
        self.assertEqual(status, 200)
        self.assertEqual([p["sku"] for p in body["items"]], ["TEA-1", "TEA-2"])
        self.assertEqual(body["items"][0], s.catalog.get("TEA-1"))

    def test_no_match(self):
        s, clock = setup()
        self.assertEqual(s.api.search(login(s, "ann"), {"q": "coffee"}), (200, {"items": []}))

    def test_bad_query_is_400(self):
        s, clock = setup()
        ann = login(s, "ann")
        for req in ({}, {"q": ""}, {"q": 5}, {"q": None}):
            self.assertEqual(s.api.search(ann, req)[0], 400, req)

    def test_admin_can_search_and_no_event(self):
        s, clock = setup()
        root = login(s, "root")
        n = len(s.events.events)
        self.assertEqual(s.api.search(root, {"q": "mug"})[1]["items"][0]["sku"], "MUG-1")
        self.assertEqual(len(s.events.events), n)

    def test_a_few_searches_all_succeed(self):
        s, clock = setup()
        ann = login(s, "ann")
        for q in ("tea", "mug", "green", "black", "a"):
            self.assertEqual(s.api.search(ann, {"q": q})[0], 200, q)
