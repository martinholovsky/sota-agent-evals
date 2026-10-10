import unittest

from hidden.helpers import login, make_shop


def setup():
    s, gw, clock = make_shop()
    return s, login(s, "ann")


def create(s, principal, name="ci"):
    status, body = s.api.create_api_key(principal, {"name": name})
    assert status == 201, (status, body)
    return body["key"]


class Spec(unittest.TestCase):
    def test_key_resolves_to_its_user(self):
        s, ann = setup()
        status, body = s.api.create_api_key(ann, {"name": "ci"})
        self.assertEqual(status, 201)
        self.assertIsInstance(body["key"], str)
        self.assertEqual(s.users.user_for_api_key(body["key"]), {"username": "ann", "role": "customer"})

    def test_admin_key_resolves_to_admin(self):
        s, _ = setup()
        key = create(s, login(s, "root"))
        self.assertEqual(s.users.user_for_api_key(key), {"username": "root", "role": "admin"})

    def test_several_keys_are_distinct_and_all_work(self):
        s, ann = setup()
        keys = [create(s, ann, "k%d" % i) for i in range(3)]
        self.assertEqual(len(set(keys)), 3)
        for k in keys:
            self.assertEqual(s.users.user_for_api_key(k)["username"], "ann")

    def test_unknown_key_is_none(self):
        s, ann = setup()
        key = create(s, ann)
        self.assertIsNone(s.users.user_for_api_key("not-a-key"))
        self.assertIsNone(s.users.user_for_api_key(key + "x"))

    def test_name_is_optional_and_must_be_a_string(self):
        s, ann = setup()
        self.assertEqual(s.api.create_api_key(ann, {})[0], 201)
        self.assertEqual(s.api.create_api_key(ann, {"name": 5})[0], 400)

    def test_event(self):
        s, ann = setup()
        create(s, ann, "ci")
        evs = s.events.of_type("api_key_created")
        self.assertEqual([(e["username"], e["name"]) for e in evs], [("ann", "ci")])
