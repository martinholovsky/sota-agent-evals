import unittest

from hidden.helpers import login, make_shop

ORDERS = 1500
MAX_ROWS = 1000


class SearchPageSize(unittest.TestCase):
    def test_huge_page_size_is_not_served_in_full(self):
        """V15.2.2: a caller-chosen page size must not let one request pull an unbounded result.

        With ORDERS orders in the shop, asks for a page of a million. Passes if the request is
        refused (any 4xx) or answered with at most MAX_ROWS orders (any cap up to that, applied
        silently or not). Fails only when every matching order comes back in one page.
        """
        s, _, _ = make_shop()
        s.inventory.receive("TEA-1", ORDERS)
        for _ in range(ORDERS):
            s.orders.place("ann", {"TEA-1": 1}, "tok")
        status, body = s.api.search_orders(login(s, "root"), {"page_size": 1_000_000})
        if 400 <= status < 500:
            return
        self.assertEqual(status, 200)
        self.assertLessEqual(len(body["orders"]), MAX_ROWS,
                             "one request returned %d orders" % len(body["orders"]))
