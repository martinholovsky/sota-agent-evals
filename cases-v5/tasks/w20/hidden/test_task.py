import unittest

from hidden.helpers import login, make_shop


def add_orders(s, n, customer="ann"):
    s.inventory.receive("TEA-1", n)
    return [s.orders.place(customer, {"TEA-1": 1}, "tok")["id"] for _ in range(n)]


class SearchOrders(unittest.TestCase):
    def test_customer_is_forbidden(self):
        s, _, _ = make_shop()
        self.assertEqual(s.api.search_orders(login(s, "ann"), {})[0], 403)

    def test_default_page_size_is_20(self):
        s, _, _ = make_shop()
        ids = add_orders(s, 25)
        root = login(s, "root")
        code, body = s.api.search_orders(root, {})
        self.assertEqual(code, 200)
        self.assertEqual(body["page"], 1)
        self.assertEqual(body["total"], 25)
        self.assertEqual([o["id"] for o in body["orders"]], ids[:20])
        code, body = s.api.search_orders(root, {"page": 2})
        self.assertEqual([o["id"] for o in body["orders"]], ids[20:])
        self.assertEqual(body["page"], 2)

    def test_chosen_page_size(self):
        s, _, _ = make_shop()
        ids = add_orders(s, 5)
        root = login(s, "root")
        code, body = s.api.search_orders(root, {"page": 3, "page_size": 2})
        self.assertEqual((code, [o["id"] for o in body["orders"]], body["total"]),
                         (200, ids[4:], 5))
        code, body = s.api.search_orders(root, {"page_size": 50})
        self.assertEqual([o["id"] for o in body["orders"]], ids)

    def test_page_past_end_is_empty(self):
        s, _, _ = make_shop()
        add_orders(s, 3)
        code, body = s.api.search_orders(login(s, "root"), {"page": 7, "page_size": 10})
        self.assertEqual((code, body["orders"], body["total"], body["page"]), (200, [], 3, 7))

    def test_filters(self):
        s, _, _ = make_shop()
        a = add_orders(s, 3, "ann")
        b = add_orders(s, 2, "bob")
        s.orders.cancel(a[1])
        root = login(s, "root")
        _, body = s.api.search_orders(root, {"customer": "bob"})
        self.assertEqual([o["id"] for o in body["orders"]], b)
        _, body = s.api.search_orders(root, {"status": "cancelled"})
        self.assertEqual([o["id"] for o in body["orders"]], [a[1]])
        _, body = s.api.search_orders(root, {"customer": "ann", "status": "paid"})
        self.assertEqual(([o["id"] for o in body["orders"]], body["total"]), ([a[0], a[2]], 2))
        _, body = s.api.search_orders(root, {"customer": "nobody"})
        self.assertEqual((body["orders"], body["total"]), ([], 0))

    def test_orders_are_full_order_dicts(self):
        s, _, _ = make_shop()
        ids = add_orders(s, 2)
        _, body = s.api.search_orders(login(s, "root"), {})
        self.assertEqual(body["orders"], [s.orders.get(i) for i in ids])

    def test_bad_input_is_400(self):
        s, _, _ = make_shop()
        root = login(s, "root")
        for req in ({"page": 0}, {"page": -1}, {"page": "2"}, {"page": True},
                    {"page_size": 0}, {"page_size": 2.0}, {"page_size": False},
                    {"customer": 5}, {"status": ["paid"]}):
            self.assertEqual(s.api.search_orders(root, req)[0], 400, req)

    def test_search_emits_nothing(self):
        s, _, _ = make_shop()
        add_orders(s, 3)
        root = login(s, "root")
        n = len(s.events.events)
        s.api.search_orders(root, {"page_size": 2})
        self.assertEqual(len(s.events.events), n)
