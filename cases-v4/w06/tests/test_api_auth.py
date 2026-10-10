import unittest

from shop.auth import AuthError, ROLE_PERMISSIONS, can
from tests.helpers import login, make_shop


class Auth(unittest.TestCase):
    def test_login(self):
        s, _, _ = make_shop()
        self.assertEqual(login(s, "ann"), {"username": "ann", "role": "customer"})
        with self.assertRaises(AuthError):
            s.users.login("ann", "wrong password!!")
        with self.assertRaises(AuthError):
            s.users.login("nobody", "whatever whatever")

    def test_failed_login_emits_event_without_password(self):
        s, _, _ = make_shop()
        with self.assertRaises(AuthError):
            s.users.login("ann", "wrong password!!")
        ev = s.events.of_type("login_failed")[-1]
        self.assertEqual(ev["username"], "ann")
        self.assertNotIn("wrong password!!", repr(s.events.events))

    def test_permissions_are_the_source_of_truth(self):
        self.assertTrue(can({"role": "admin"}, "order:cancel"))
        self.assertFalse(can({"role": "customer"}, "order:cancel"))
        self.assertFalse(can({"role": "ghost"}, "order:place"))
        self.assertIn("order:view_own", ROLE_PERMISSIONS["customer"])


class Api(unittest.TestCase):
    def test_place_and_view_own(self):
        s, _, _ = make_shop()
        ann = login(s, "ann")
        code, body = s.api.place_order(ann, {"items": {"TEA-1": 1}, "token": "tok"})
        self.assertEqual(code, 201)
        code, body = s.api.get_order(ann, {"id": body["order"]["id"]})
        self.assertEqual(code, 200)

    def test_other_customers_order_is_404_not_403(self):
        s, _, _ = make_shop()
        s.users.create("bob", "another long password", "customer", "bob@example.com")
        o = s.orders.place("ann", {"TEA-1": 1}, "tok")
        bob = s.users.login("bob", "another long password")
        self.assertEqual(s.api.get_order(bob, {"id": o["id"]})[0], 404)
        self.assertEqual(s.api.get_order(login(s, "root"), {"id": o["id"]})[0], 200)

    def test_cancel_requires_permission(self):
        s, _, _ = make_shop()
        o = s.orders.place("ann", {"TEA-1": 1}, "tok")
        self.assertEqual(s.api.cancel_order(login(s, "ann"), {"id": o["id"]})[0], 403)
        self.assertEqual(s.api.cancel_order(login(s, "root"), {"id": o["id"]})[0], 200)

    def test_input_validation(self):
        s, _, _ = make_shop()
        ann = login(s, "ann")
        self.assertEqual(s.api.place_order(ann, {"items": "x", "token": "t"})[0], 400)
        self.assertEqual(s.api.place_order(ann, {"items": {"NOPE-1": 1}, "token": "t"})[0], 404)
        self.assertEqual(s.api.place_order(ann, {"items": {"MUG-1": 50}, "token": "t"})[0], 409)
