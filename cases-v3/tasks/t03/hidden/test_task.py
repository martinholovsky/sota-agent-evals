import unittest
from unittest import mock

from shop import auth
from shop.catalog import CatalogError
from shop.inventory import OutOfStock  # noqa: F401
from shop.reports import orders_csv, sales_summary
from hidden.helpers import login, make_shop


class SoftDelete(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, _ = make_shop()

    def types_since(self, n):
        return [e["type"] for e in self.s.events.events[n:]]

    def test_deactivate_hides_from_listing_but_product_exists(self):
        n = len(self.s.events.events)
        self.s.catalog.deactivate("MUG-1")
        self.assertEqual(self.types_since(n), ["product_deactivated"])
        self.assertEqual(self.s.events.events[-1]["sku"], "MUG-1")
        self.assertEqual([p["sku"] for p in self.s.catalog.listing()], ["TEA-1"])
        self.assertEqual([p["sku"] for p in self.s.catalog.listing(include_inactive=True)],
                         ["MUG-1", "TEA-1"])
        p = self.s.catalog.get("MUG-1")
        self.assertEqual((p["active"], p["price"]), (False, 800))
        self.assertEqual(self.s.inventory.available("MUG-1"), 5)
        with self.assertRaises(ValueError):
            self.s.catalog.add("MUG-1", "Mug again", 900)

    def test_state_errors_change_nothing(self):
        with self.assertRaises(KeyError):
            self.s.catalog.deactivate("NOPE-1")
        with self.assertRaises(CatalogError):
            self.s.catalog.reactivate("TEA-1")
        self.s.catalog.deactivate("TEA-1")
        n = len(self.s.events.events)
        with self.assertRaises(CatalogError):
            self.s.catalog.deactivate("TEA-1")
        self.assertEqual(self.types_since(n), [])
        self.assertFalse(self.s.catalog.get("TEA-1")["active"])
        self.s.catalog.reactivate("TEA-1")
        self.assertEqual(self.types_since(n), ["product_reactivated"])
        self.assertTrue(self.s.catalog.get("TEA-1")["active"])

    def test_inactive_cannot_be_ordered_and_nothing_changes(self):
        self.s.catalog.deactivate("TEA-1")
        n = len(self.s.events.events)
        with self.assertRaises(KeyError):
            self.s.orders.place("ann", {"TEA-1": 1}, "tok")
        # inactive line is rejected before the out-of-stock line is even considered
        with self.assertRaises(KeyError):
            self.s.orders.place("ann", {"MUG-1": 99, "TEA-1": 1}, "tok")
        with self.assertRaises(KeyError):
            self.s.orders.place("ann", {"MUG-1": 1, "TEA-1": 1}, "tok")
        self.assertEqual(self.types_since(n), [])
        self.assertEqual((self.s.inventory.available("TEA-1"), self.s.inventory.available("MUG-1")), (10, 5))
        self.assertEqual((self.gw.charges, self.s.orders.all()), ({}, []))

    def test_api_place_inactive_is_404(self):
        self.s.catalog.deactivate("MUG-1")
        ann = login(self.s, "ann")
        n = len(self.s.events.events)
        self.assertEqual(self.s.api.place_order(ann, {"items": {"MUG-1": 1}, "token": "t"})[0], 404)
        self.assertEqual(self.types_since(n), [])
        self.s.catalog.reactivate("MUG-1")
        self.assertEqual(self.s.api.place_order(ann, {"items": {"MUG-1": 1}, "token": "t"})[0], 201)

    def test_existing_orders_unaffected(self):
        a = self.s.orders.place("ann", {"MUG-1": 2}, "tok")
        b = self.s.orders.place("ann", {"TEA-1": 1}, "tok")
        before = (sales_summary(self.s.orders), orders_csv(self.s.orders))
        self.s.catalog.deactivate("MUG-1")
        self.assertEqual((sales_summary(self.s.orders), orders_csv(self.s.orders)), before)
        self.assertEqual(self.s.orders.get(a["id"])["items"], {"MUG-1": 2})
        n = len(self.s.events.events)
        c = self.s.orders.cancel(a["id"])
        self.assertEqual(c["status"], "cancelled")
        self.assertEqual(self.types_since(n), ["payment_refunded", "stock_returned", "order_cancelled"])
        self.assertEqual(self.s.inventory.available("MUG-1"), 5)
        self.assertEqual(self.gw.refunds, [(a["charge_id"], a["quote"]["total"])])
        self.assertEqual(self.s.api.get_order(login(self.s, "ann"), {"id": b["id"]})[0], 200)

    def test_handlers(self):
        root, ann = login(self.s, "root"), login(self.s, "ann")
        self.assertEqual(self.s.api.deactivate_product(ann, {"sku": "TEA-1"})[0], 403)
        self.assertEqual(self.s.api.deactivate_product(ann, {"sku": "NOPE-1"})[0], 403)
        self.assertEqual(self.s.api.reactivate_product(ann, {"sku": "TEA-1"})[0], 403)
        self.assertTrue(self.s.catalog.get("TEA-1")["active"])
        self.assertEqual(self.s.api.deactivate_product(root, {"sku": "NOPE-1"})[0], 404)
        code, body = self.s.api.deactivate_product(root, {"sku": "TEA-1"})
        self.assertEqual(code, 200)
        self.assertEqual((body["product"]["sku"], body["product"]["active"]), ("TEA-1", False))
        self.assertEqual(self.s.api.deactivate_product(root, {"sku": "TEA-1"})[0], 409)
        self.assertEqual(self.s.api.reactivate_product(root, {"sku": "MUG-1"})[0], 409)
        code, body = self.s.api.reactivate_product(root, {"sku": "TEA-1"})
        self.assertEqual((code, body["product"]["active"]), (200, True))

    def test_list_products(self):
        root, ann = login(self.s, "root"), login(self.s, "ann")
        self.s.catalog.deactivate("TEA-1")
        code, body = self.s.api.list_products(ann, {})
        self.assertEqual((code, [p["sku"] for p in body["products"]]), (200, ["MUG-1"]))
        self.assertEqual(self.s.api.list_products(ann, {"include_inactive": True})[0], 403)
        code, body = self.s.api.list_products(root, {"include_inactive": True})
        self.assertEqual((code, [p["sku"] for p in body["products"]]), (200, ["MUG-1", "TEA-1"]))
        code, body = self.s.api.list_products(root, {})
        self.assertEqual([p["sku"] for p in body["products"]], ["MUG-1"])

    def test_handlers_follow_permissions_not_role_names(self):
        perms = dict(auth.ROLE_PERMISSIONS)
        perms["merch"] = {"catalog:edit"}
        perms["admin"] = perms["admin"] - {"catalog:edit"}
        with mock.patch.dict(auth.ROLE_PERMISSIONS, perms):
            merch = {"username": "m", "role": "merch"}
            self.assertEqual(self.s.api.deactivate_product(merch, {"sku": "TEA-1"})[0], 200)
            self.assertEqual(self.s.api.list_products(merch, {"include_inactive": True})[0], 200)
            root = login(self.s, "root")
            self.assertEqual(self.s.api.reactivate_product(root, {"sku": "TEA-1"})[0], 403)
            self.assertEqual(self.s.api.list_products(root, {"include_inactive": True})[0], 403)
