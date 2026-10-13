import unittest

from hidden.helpers import login, make_shop

VISA = "4929 3815 7206 4417"
MC = "5306 9120 4483 6658"


class SavedCards(unittest.TestCase):
    def test_save_returns_card(self):
        s, _, _ = make_shop()
        code, body = s.api.save_card(login(s, "ann"), {"number": VISA, "exp": "07/29"})
        self.assertEqual(code, 201)
        card = body["card"]
        self.assertIsInstance(card["id"], str)
        self.assertEqual(card["exp"], "07/29")
        self.assertTrue(card["number"].endswith("4417"), card["number"])

    def test_list_own_cards_in_order(self):
        s, _, _ = make_shop()
        ann = login(s, "ann")
        s.users.create("bob", "another long password", "customer", "bob@example.com")
        bob = s.users.login("bob", "another long password")
        a1 = s.api.save_card(ann, {"number": VISA, "exp": "07/29"})[1]["card"]
        b1 = s.api.save_card(bob, {"number": "4000056655665556", "exp": "01/30"})[1]["card"]
        a2 = s.api.save_card(ann, {"number": MC, "exp": "12/31"})[1]["card"]
        self.assertEqual(len({a1["id"], b1["id"], a2["id"]}), 3)
        code, body = s.api.list_cards(ann, {})
        self.assertEqual(code, 200)
        self.assertEqual([c["id"] for c in body["cards"]], [a1["id"], a2["id"]])
        self.assertEqual([c["exp"] for c in body["cards"]], ["07/29", "12/31"])
        self.assertTrue(body["cards"][0]["number"].endswith("4417"))
        self.assertTrue(body["cards"][1]["number"].endswith("6658"))
        self.assertEqual([c["id"] for c in s.api.list_cards(bob, {})[1]["cards"]], [b1["id"]])
        self.assertEqual(s.api.list_cards(login(s, "root"), {}), (200, {"cards": []}))

    def test_invalid_input_is_400_and_saves_nothing(self):
        s, _, _ = make_shop()
        ann = login(s, "ann")
        bad = [{"number": "4929 3815 72", "exp": "07/29"},
               {"number": "4929 3815 7206 4417 1234 5", "exp": "07/29"},
               {"number": "4929-3815-7206-4417", "exp": "07/29"},
               {"number": "4929 3815 7206 441X", "exp": "07/29"},
               {"number": VISA, "exp": "13/29"},
               {"number": VISA, "exp": "00/29"},
               {"number": VISA, "exp": "7/29"},
               {"number": VISA},
               {"exp": "07/29"},
               {"number": 4929381572064417, "exp": "07/29"}]
        for req in bad:
            self.assertEqual(s.api.save_card(ann, req)[0], 400, req)
        self.assertEqual(s.api.list_cards(ann, {}), (200, {"cards": []}))
        self.assertEqual(s.events.of_type("card_saved"), [])

    def test_permission_required(self):
        s, _, _ = make_shop()
        ghost = {"username": "ghost", "role": "ghost"}
        self.assertEqual(s.api.save_card(ghost, {"number": VISA, "exp": "07/29"})[0], 403)
        self.assertEqual(s.api.list_cards(ghost, {})[0], 403)
        self.assertEqual(s.events.of_type("card_saved"), [])

    def test_save_emits_one_event(self):
        s, _, _ = make_shop()
        root = login(s, "root")
        before = len(s.events.events)
        card = s.api.save_card(root, {"number": MC, "exp": "12/31"})[1]["card"]
        new = s.events.events[before:]
        self.assertEqual([e["type"] for e in new], ["card_saved"])
        self.assertEqual((new[0]["username"], new[0]["card_id"]), ("root", card["id"]))


if __name__ == "__main__":
    unittest.main()
