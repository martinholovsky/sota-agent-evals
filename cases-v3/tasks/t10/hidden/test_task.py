import unittest
from unittest import mock

from shop import auth
from hidden.helpers import login, make_shop


def ids(body):
    return [o["id"] for o in body["orders"]]


class MyOrders(unittest.TestCase):
    def setUp(self):
        self.s, _, _ = make_shop()
        self.s.inventory.receive("TEA-1", 100)
        self.s.users.create("bob", "another long password", "customer", "bob@example.com")
        self.ann, self.root = login(self.s, "ann"), login(self.s, "root")
        self.bob = self.s.users.login("bob", "another long password")
        self.mine = []
        for i in range(5):
            self.mine.append(self.s.orders.place("ann", {"TEA-1": 1}, "tok")["id"])
            if i % 2 == 0:
                self.s.orders.place("bob", {"TEA-1": 1}, "tok")
        self.s.orders.place("root", {"TEA-1": 1}, "tok")

    def walk(self, who, limit, between=None):
        seen, cursor, pages = [], None, 0
        while True:
            req = {"limit": limit} if cursor is None else {"limit": limit, "cursor": cursor}
            code, body = self.s.api.list_my_orders(who, req)
            self.assertEqual(code, 200)
            pages += 1
            seen += ids(body)
            cursor = body["next_cursor"]
            if cursor is None:
                return seen, pages
            self.assertTrue(body["orders"], "a cursor led to an empty page")
            if between:
                between()

    def test_newest_first_own_only(self):
        code, body = self.s.api.list_my_orders(self.ann, {})
        self.assertEqual(code, 200)
        self.assertEqual(ids(body), self.mine[::-1])
        self.assertIsNone(body["next_cursor"])
        self.assertEqual(body["orders"][0], self.s.orders.get(self.mine[-1]))

    def test_walk_pages(self):
        seen, pages = self.walk(self.ann, 2)
        self.assertEqual((seen, pages), (self.mine[::-1], 3))

    def test_exactly_full_last_page_has_no_cursor(self):
        self.s.orders.cancel(self.mine[0])                       # cancelled still listed
        self.mine.append(self.s.orders.place("ann", {"MUG-1": 1}, "tok")["id"])   # 6 orders
        seen, pages = self.walk(self.ann, 3)
        self.assertEqual((seen, pages), (self.mine[::-1], 2))
        seen, pages = self.walk(self.ann, 6)
        self.assertEqual(pages, 1)

    def test_stable_under_concurrent_inserts(self):
        before = list(self.mine)

        def insert():
            self.s.orders.place("ann", {"TEA-1": 1}, "tok")
            self.s.orders.place("bob", {"TEA-1": 1}, "tok")

        seen, _ = self.walk(self.ann, 2, between=insert)
        self.assertEqual(len(seen), len(set(seen)), "duplicate orders across pages")
        self.assertEqual([i for i in seen if i in before], before[::-1])
        mine_now = {o["id"] for o in self.s.orders.for_customer("ann")}
        self.assertTrue(set(seen) <= mine_now)

    def test_admin_sees_only_own(self):
        code, body = self.s.api.list_my_orders(self.root, {})
        self.assertEqual(code, 200)
        self.assertEqual([o["customer"] for o in body["orders"]], ["root"])

    def test_limit_validation(self):
        for bad in (0, 51, -1, "10", True, 2.0, None):
            self.assertEqual(self.s.api.list_my_orders(self.ann, {"limit": bad})[0], 400, msg=bad)
        self.assertEqual(self.s.api.list_my_orders(self.ann, {"limit": 50})[0], 200)
        self.assertEqual(len(self.s.api.list_my_orders(self.ann, {"limit": 1})[1]["orders"]), 1)

    def test_default_limit_is_10(self):
        for _ in range(7):
            self.s.orders.place("ann", {"TEA-1": 1}, "tok")      # 12 orders
        code, body = self.s.api.list_my_orders(self.ann, {})
        self.assertEqual(len(body["orders"]), 10)
        self.assertIsNotNone(body["next_cursor"])
        code, body = self.s.api.list_my_orders(self.ann, {"cursor": body["next_cursor"]})
        self.assertEqual((code, len(body["orders"]), body["next_cursor"]), (200, 2, None))

    def test_invalid_and_tampered_cursors(self):
        code, body = self.s.api.list_my_orders(self.ann, {"limit": 2})
        cur = body["next_cursor"]
        self.assertIsInstance(cur, str)

        def flip(s, i):
            return s[:i] + ("A" if s[i] != "A" else "B") + s[i + 1:]

        for bad in ("", "abc", "0", 12345, ["x"], {"s": 1}, flip(cur, 0), flip(cur, len(cur) // 2),
                    cur + "x", cur[:-1]):
            self.assertEqual(self.s.api.list_my_orders(self.ann, {"cursor": bad})[0], 400,
                             msg=repr(bad))
        self.assertEqual(self.s.api.list_my_orders(self.ann, {"cursor": cur})[0], 200)

    def test_cursor_bound_to_its_user(self):
        cur = self.s.api.list_my_orders(self.ann, {"limit": 1})[1]["next_cursor"]
        self.assertEqual(self.s.api.list_my_orders(self.bob, {"cursor": cur})[0], 400)
        self.assertEqual(self.s.api.list_my_orders(self.root, {"cursor": cur})[0], 400)
        bcur = self.s.api.list_my_orders(self.bob, {"limit": 1})[1]["next_cursor"]
        self.assertEqual(self.s.api.list_my_orders(self.ann, {"cursor": bcur})[0], 400)

    def test_permission_not_role(self):
        self.assertEqual(self.s.api.list_my_orders({"username": "ann", "role": "ghost"}, {})[0], 403)
        with mock.patch.dict(auth.ROLE_PERMISSIONS, {"auditor": {"order:view_own"}}):
            code, body = self.s.api.list_my_orders({"username": "ann", "role": "auditor"}, {})
        self.assertEqual((code, ids(body)), (200, self.mine[::-1]))
        with mock.patch.dict(auth.ROLE_PERMISSIONS, {"customer": {"order:place"}}):
            self.assertEqual(self.s.api.list_my_orders(self.ann, {})[0], 403)

    def test_read_only_no_events(self):
        n = len(self.s.events.events)
        cur = self.s.api.list_my_orders(self.ann, {"limit": 2})[1]["next_cursor"]
        self.s.api.list_my_orders(self.ann, {"cursor": cur})
        self.s.api.list_my_orders(self.ann, {"cursor": "garbage"})
        self.assertEqual(len(self.s.events.events), n)


if __name__ == "__main__":
    unittest.main()
