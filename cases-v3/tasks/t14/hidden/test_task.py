import unittest

from shop.catalog import VersionConflict
from hidden.helpers import login, make_shop


class Versions(unittest.TestCase):
    def setUp(self):
        self.s, _, _ = make_shop()
        self.c = self.s.catalog

    def snapshot(self):
        return [dict(p) for p in self.c.listing()], len(self.s.events.events)

    def test_new_products_start_at_1(self):
        self.assertEqual(self.c.add("PEN-1", "Pen", 100)["version"], 1)
        self.assertEqual(self.c.get("TEA-1")["version"], 1)
        self.assertEqual([p["version"] for p in self.c.listing()], [1, 1, 1])

    def test_unconditional_update_still_works_and_bumps(self):
        self.c.set_price("TEA-1", 1300)
        self.assertEqual((self.c.get("TEA-1")["price"], self.c.get("TEA-1")["version"]), (1300, 2))
        self.assertEqual(self.c.set_price("TEA-1", 1400), 3)
        with self.assertRaises(VersionConflict):
            self.c.set_price("TEA-1", 1500, 1)
        self.assertEqual(self.c.get("TEA-1")["price"], 1400)

    def test_conditional_update(self):
        v = self.c.get("TEA-1")["version"]
        self.assertEqual(self.c.set_price("TEA-1", 1300, v), v + 1)
        before = self.snapshot()
        with self.assertRaises(VersionConflict):
            self.c.set_price("TEA-1", 1350, v)                 # second writer, stale
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.c.get("TEA-1")["price"], 1300)

    def test_bool_is_not_a_version(self):
        self.assertEqual(self.c.get("TEA-1")["version"], 1)
        before = self.snapshot()
        for bad in (True, 1.0, "1"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.c.set_price("TEA-1", 1300, bad)
        self.assertEqual(self.snapshot(), before)

    def test_check_order(self):
        with self.assertRaises(KeyError):
            self.c.set_price("NOPE-1", 0, 99)
        with self.assertRaises(ValueError):
            self.c.set_price("TEA-1", 0, 99)                   # bad price beats stale version
        with self.assertRaises(ValueError):
            self.c.set_price("TEA-1", 1300, True)

    def test_event(self):
        n = len(self.s.events.events)
        self.c.set_price("TEA-1", 1300, 1)
        evs = self.s.events.events[n:]
        self.assertEqual(len(evs), 1)
        self.assertEqual({k: evs[0][k] for k in ("type", "sku", "old", "new", "version")},
                         {"type": "price_changed", "sku": "TEA-1", "old": 1250, "new": 1300,
                          "version": 2})

    def test_orders_use_current_price(self):
        self.c.set_price("TEA-1", 1000, 1)
        self.assertEqual(self.s.orders.place("ann", {"TEA-1": 1}, "tok")["quote"]["subtotal"], 1000)


class Bulk(unittest.TestCase):
    def setUp(self):
        self.s, _, _ = make_shop()
        self.c = self.s.catalog

    def snapshot(self):
        return [dict(p) for p in self.c.listing()], len(self.s.events.events)

    def test_success(self):
        n = len(self.s.events.events)
        self.assertEqual(self.c.set_prices([("MUG-1", 900, 1), ("TEA-1", 1300, 1)]),
                         {"MUG-1": 2, "TEA-1": 2})
        evs = self.s.events.events[n:]
        self.assertEqual([(e["type"], e["sku"], e["version"]) for e in evs],
                         [("price_changed", "MUG-1", 2), ("price_changed", "TEA-1", 2)])
        self.assertEqual((self.c.get("MUG-1")["price"], self.c.get("TEA-1")["price"]), (900, 1300))

    def test_all_or_nothing(self):
        self.c.set_price("TEA-1", 1300)                         # TEA-1 now at version 2
        before = self.snapshot()
        cases = [
            ([("MUG-1", 900, 1), ("TEA-1", 1400, 1)], VersionConflict),
            ([("MUG-1", 900, 1), ("NOPE-1", 1400, 1)], KeyError),
            ([("MUG-1", 900, 1), ("TEA-1", -5, 2)], ValueError),
            ([("MUG-1", 900, 1), ("TEA-1", 1400, True)], ValueError),
            ([("MUG-1", 900, 1), ("MUG-1", 950, 1)], ValueError),
        ]
        for changes, exc in cases:
            with self.assertRaises(exc, msg=repr(changes)):
                self.c.set_prices(changes)
            self.assertEqual(self.snapshot(), before, repr(changes))


class PriceApi(unittest.TestCase):
    def setUp(self):
        self.s, _, _ = make_shop()
        self.ann, self.root = login(self.s, "ann"), login(self.s, "root")

    def test_forbidden_for_customers(self):
        self.assertEqual(self.s.api.update_price(self.ann, {"sku": "TEA-1", "price": 1, "version": 1})[0], 403)
        self.assertEqual(self.s.api.update_prices(
            self.ann, {"changes": [{"sku": "TEA-1", "price": 1, "version": 1}]})[0], 403)
        self.assertEqual(self.s.catalog.get("TEA-1")["price"], 1250)

    def test_update_price(self):
        api, root = self.s.api, self.root
        code, body = api.update_price(root, {"sku": "TEA-1", "price": 1300, "version": 1})
        self.assertEqual(code, 200)
        self.assertEqual((body["product"]["price"], body["product"]["version"]), (1300, 2))
        code, body = api.update_price(root, {"sku": "TEA-1", "price": 1400, "version": 1})
        self.assertEqual(code, 409)
        self.assertIn("error", body)
        self.assertEqual((body["product"]["sku"], body["product"]["price"], body["product"]["version"]),
                         ("TEA-1", 1300, 2))
        for req in ({"sku": "TEA-1", "price": 1400},
                    {"sku": "TEA-1", "price": 1400, "version": True},
                    {"sku": "TEA-1", "price": 1400, "version": "2"},
                    {"sku": "TEA-1", "price": 0, "version": 2}):
            self.assertEqual(api.update_price(root, req)[0], 400, repr(req))
        self.assertEqual(api.update_price(root, {"sku": "NOPE-1", "price": 5, "version": 1})[0], 404)
        self.assertEqual(self.s.catalog.get("TEA-1")["price"], 1300)

    def test_update_prices(self):
        api, root = self.s.api, self.root
        self.assertEqual(api.update_prices(root, {"changes": []})[0], 400)
        self.assertEqual(api.update_prices(root, {})[0], 400)
        bad_version = {"changes": [{"sku": "MUG-1", "price": 900, "version": 1},
                                   {"sku": "TEA-1", "price": 1300}]}
        self.assertEqual(api.update_prices(root, bad_version)[0], 400)
        stale = {"changes": [{"sku": "MUG-1", "price": 900, "version": 1},
                             {"sku": "TEA-1", "price": 1300, "version": 7}]}
        code, body = api.update_prices(root, stale)
        self.assertEqual(code, 409)
        self.assertIn("error", body)
        unknown = {"changes": [{"sku": "MUG-1", "price": 900, "version": 1},
                               {"sku": "NOPE-1", "price": 1300, "version": 1}]}
        self.assertEqual(api.update_prices(root, unknown)[0], 404)
        self.assertEqual(self.s.catalog.get("MUG-1")["price"], 800)
        self.assertEqual(self.s.events.of_type("price_changed"), [])
        ok = {"changes": [{"sku": "MUG-1", "price": 900, "version": 1},
                          {"sku": "TEA-1", "price": 1300, "version": 1}]}
        self.assertEqual(api.update_prices(root, ok), (200, {"versions": {"MUG-1": 2, "TEA-1": 2}}))
