import base64
import hashlib
import json
import unittest
from unittest import mock

from shop import auth
from shop.auth import AuthError
from hidden.helpers import login, make_shop


class Export(unittest.TestCase):
    def setUp(self):
        self.s, _, self.clock = make_shop()
        s = self.s
        s.users.create("bob", "another long password", "customer", "bob@example.com")
        s.users.create("an", "yet another password", "customer", "an@example.com")
        self.a1 = s.orders.place("ann", {"TEA-1": 1}, "tok")
        self.b1 = s.orders.place("bob", {"MUG-1": 1}, "tok")
        self.a2 = s.orders.place("ann", {"MUG-1": 2}, "tok", "TEN")
        s.orders.place("an", {"TEA-1": 1}, "tok")
        s.orders.cancel(self.a1["id"])
        login(s, "ann")
        with self.assertRaises(AuthError):
            s.users.login("ann", "wrong password!!")
        with self.assertRaises(AuthError):
            s.users.login("annie", "wrong password!!")
        login(s, "root")

    def expected_events(self, who, oids):
        return [e for e in self.s.events.events
                if e.get("username") == who or e.get("customer") == who or e.get("order_id") in oids]

    def test_shape_and_content(self):
        before = list(self.s.events.events)
        ex = self.s.export_user_data("ann")
        self.assertEqual(set(ex), {"account", "orders", "events"})
        self.assertEqual(ex["account"], {"username": "ann", "role": "customer",
                                         "email": "ann@example.com"})
        self.assertEqual(ex["orders"], [self.s.orders.get(self.a1["id"]),
                                        self.s.orders.get(self.a2["id"])])
        oids = {self.a1["id"], self.a2["id"]}
        want = [e for e in before if e.get("username") == "ann" or e.get("customer") == "ann"
                or e.get("order_id") in oids]
        self.assertEqual(ex["events"], want)
        types = [e["type"] for e in ex["events"]]
        for t in ("user_created", "login_ok", "login_failed", "order_placed", "payment_captured",
                  "payment_refunded", "order_cancelled"):
            self.assertIn(t, types)
        self.assertNotIn("stock_taken", types)

    def test_nothing_about_other_users(self):
        ex = self.s.export_user_data("ann")
        dump = json.dumps(ex)
        for other in ('"bob"', "bob@example.com", '"an"', "an@example.com", '"root"',
                      "root@example.com", "annie", self.b1["id"]):
            self.assertNotIn(other, dump)
        ex = self.s.export_user_data("an")
        self.assertEqual([o["customer"] for o in ex["orders"]], ["an"])
        self.assertNotIn("ann@example.com", json.dumps(ex))
        self.assertTrue(all(e.get("username") != "ann" for e in ex["events"]))

    def test_no_secrets_and_json_serializable(self):
        salt = b"S" * 16
        with mock.patch("os.urandom", return_value=salt):
            self.s.users.create("carol", "carols long password", "customer", "carol@example.com")
        digest = hashlib.pbkdf2_hmac("sha256", b"carols long password", salt, 100_000)
        ex = self.s.export_user_data("carol")
        dump = json.dumps(ex)
        for secret in (salt.hex(), digest.hex(), base64.b64encode(digest).decode(),
                       base64.b64encode(salt).decode(), "carols long password", "SSSSSSSS"):
            self.assertNotIn(secret, dump)
        self.assertNotIn(repr(digest)[2:-1][:12], repr(ex))
        dump = json.dumps(self.s.export_user_data("ann"))
        self.assertNotIn("correct horse battery", dump)
        self.assertNotIn("salt", dump)
        self.assertNotIn('"hash"', dump)

    def test_export_is_a_copy(self):
        ex = self.s.export_user_data("ann")
        snapshot = json.dumps(self.s.events.events, sort_keys=True)
        ex["orders"][1]["quote"]["total"] = 0
        ex["orders"][1]["items"]["MUG-1"] = 99
        ex["orders"][1]["status"] = "x"
        for e in ex["events"]:
            e["type"] = "tampered"
            if "lines" in e:
                e["lines"].clear()
        ex["account"]["email"] = "evil@example.com"
        o = self.s.orders.get(self.a2["id"])
        self.assertEqual((o["quote"]["total"], o["items"], o["status"]),
                         (self.a2["quote"]["total"], {"MUG-1": 2}, "paid"))
        self.assertEqual(json.dumps(self.s.events.events, sort_keys=True), snapshot)
        self.assertNotIn("tampered", repr(self.s.events.events))
        self.assertEqual(self.s.users.email_of("ann"), "ann@example.com")
        self.assertEqual(self.s.export_user_data("ann")["account"]["email"], "ann@example.com")

    def test_export_event(self):
        n = len(self.s.events.events)
        ex1 = self.s.export_user_data("ann")
        new = self.s.events.events[n:]
        self.assertEqual([(e["type"], e["username"]) for e in new], [("user_data_exported", "ann")])
        self.assertNotIn("user_data_exported", [e["type"] for e in ex1["events"]])
        ex2 = self.s.export_user_data("ann")
        self.assertEqual([e["type"] for e in ex2["events"]].count("user_data_exported"), 1)
        self.assertEqual(len(ex2["events"]), len(ex1["events"]) + 1)

    def test_unknown_user(self):
        n = len(self.s.events.events)
        with self.assertRaises(KeyError):
            self.s.export_user_data("nobody")
        self.assertEqual(len(self.s.events.events), n)


class ExportApi(unittest.TestCase):
    def setUp(self):
        self.s, _, _ = make_shop()
        self.s.users.create("bob", "another long password", "customer", "bob@example.com")
        self.s.orders.place("ann", {"TEA-1": 1}, "tok")
        self.ann, self.root = login(self.s, "ann"), login(self.s, "root")

    def call(self, p, req):
        return self.s.api.export_user_data(p, req)

    def test_self_and_admin(self):
        code, body = self.call(self.ann, {"username": "ann"})
        self.assertEqual(code, 200)
        self.assertEqual(body["export"]["account"]["username"], "ann")
        code, body = self.call(self.root, {"username": "ann"})
        self.assertEqual(code, 200)
        self.assertEqual(len(body["export"]["orders"]), 1)
        self.assertEqual(self.call(self.root, {"username": "root"})[0], 200)

    def test_other_user_is_404_not_403(self):
        n = len(self.s.events.events)
        self.assertEqual(self.call(self.ann, {"username": "bob"})[0], 404)
        self.assertEqual(self.call(self.ann, {"username": "nobody"})[0], 404)
        self.assertEqual(self.call(self.root, {"username": "nobody"})[0], 404)
        self.assertEqual(len(self.s.events.events), n)

    def test_bad_input(self):
        for req in ({}, {"username": 5}, {"username": None}):
            self.assertEqual(self.call(self.ann, req)[0], 400, msg=req)

    def test_permissions_are_the_source_of_truth(self):
        self.assertIn("user:export_own", auth.ROLE_PERMISSIONS["customer"])
        self.assertNotIn("user:export_any", auth.ROLE_PERMISSIONS["customer"])
        self.assertTrue({"user:export_own", "user:export_any"} <= auth.ROLE_PERMISSIONS["admin"])
        with mock.patch.dict(auth.ROLE_PERMISSIONS, {"dpo": {"user:export_any"}}):
            self.assertEqual(self.call({"username": "dpo1", "role": "dpo"}, {"username": "ann"})[0], 200)
        with mock.patch.dict(auth.ROLE_PERMISSIONS, {"customer": {"order:place"}}):
            self.assertEqual(self.call(self.ann, {"username": "ann"})[0], 403)

    def test_existing_permissions_unchanged(self):
        self.assertEqual(self.s.api.cancel_order(self.ann, {"id": "O00001"})[0], 403)
        self.assertEqual(self.s.api.get_order(self.root, {"id": "O00001"})[0], 200)


if __name__ == "__main__":
    unittest.main()
