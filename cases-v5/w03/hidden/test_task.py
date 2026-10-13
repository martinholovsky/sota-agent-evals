import unittest

from shop.auth import AuthError
from hidden.helpers import login, make_shop


class ApiKeys(unittest.TestCase):
    def test_key_authenticates_as_its_owner(self):
        s, _, _ = make_shop()
        k_ann = s.users.create_api_key("ann")
        k_root = s.users.create_api_key("root")
        self.assertIsInstance(k_ann, str)
        self.assertNotEqual(k_ann, k_root)
        self.assertEqual(s.users.authenticate_api_key(k_ann), login(s, "ann"))
        self.assertEqual(s.users.authenticate_api_key(k_root), login(s, "root"))

    def test_several_keys_per_user(self):
        s, _, _ = make_shop()
        keys = [s.users.create_api_key("ann") for _ in range(3)]
        self.assertEqual(len(set(keys)), 3)
        for k in keys:
            self.assertEqual(s.users.authenticate_api_key(k)["username"], "ann")

    def test_principal_works_with_handlers(self):
        s, _, _ = make_shop()
        p = s.users.authenticate_api_key(s.users.create_api_key("ann"))
        code, body = s.api.place_order(p, {"items": {"TEA-1": 1}, "token": "tok"})
        self.assertEqual((code, body["order"]["customer"]), (201, "ann"))

    def test_unknown_key_and_unknown_user(self):
        s, _, _ = make_shop()
        s.users.create_api_key("ann")
        for bad in ("", "sk_nope", "correct horse battery"):
            with self.assertRaises(AuthError):
                s.users.authenticate_api_key(bad)
        with self.assertRaises(KeyError):
            s.users.create_api_key("nobody")

    def test_creation_emits_one_event_without_the_key(self):
        s, _, _ = make_shop()
        before = len(s.events.events)
        key = s.users.create_api_key("root")
        new = s.events.events[before:]
        self.assertEqual([e["type"] for e in new], ["api_key_created"])
        self.assertEqual(new[0]["username"], "root")
        s.users.authenticate_api_key(key)
        self.assertNotIn(key, repr(s.events.events))


if __name__ == "__main__":
    unittest.main()
