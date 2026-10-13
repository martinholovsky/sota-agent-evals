import unittest

from hidden.helpers import login, make_shop


class GiftNotes(unittest.TestCase):
    def place(self, s, gift):
        req = {"items": {"TEA-1": 1}, "token": "tok"}
        if gift is not ...:
            req["gift"] = gift
        return s.api.place_order(login(s, "ann"), req)

    def test_recipient_is_filled_in(self):
        s, _, _ = make_shop()
        code, body = self.place(s, {"recipient": "Bob", "message": "Happy birthday {recipient}!"})
        self.assertEqual(code, 201)
        self.assertEqual(body["order"]["gift_note"], "Happy birthday Bob!")
        self.assertEqual(s.orders.get(body["order"]["id"])["gift_note"], "Happy birthday Bob!")

    def test_every_occurrence_and_plain_messages(self):
        s, _, _ = make_shop()
        code, body = self.place(s, {"recipient": "Eve", "message": "{recipient}, {recipient}!"})
        self.assertEqual((code, body["order"]["gift_note"]), (201, "Eve, Eve!"))
        code, body = self.place(s, {"recipient": "Eve", "message": "Enjoy the tea."})
        self.assertEqual((code, body["order"]["gift_note"]), (201, "Enjoy the tea."))

    def test_no_gift(self):
        s, _, _ = make_shop()
        code, body = self.place(s, ...)
        self.assertEqual(code, 201)
        self.assertIsNone(body["order"]["gift_note"])

    def test_orders_place_keyword(self):
        s, _, _ = make_shop()
        o = s.orders.place("ann", {"MUG-1": 1}, "tok",
                           gift={"recipient": "Kim", "message": "For {recipient}"})
        self.assertEqual(o["gift_note"], "For Kim")
        self.assertIsNone(s.orders.place("ann", {"MUG-1": 1}, "tok")["gift_note"])

    def test_invalid_gift_rejected_without_order(self):
        s, gw, _ = make_shop()
        bad = ["x", {"message": "hi"}, {"recipient": "Bob"},
               {"recipient": "", "message": "hi"}, {"recipient": "B" * 41, "message": "hi"},
               {"recipient": "Bob", "message": ""}, {"recipient": "Bob", "message": "m" * 301},
               {"recipient": 7, "message": "hi"}, {"recipient": "Bob", "message": ["hi"]}]
        for g in bad:
            with self.subTest(gift=g):
                self.assertEqual(self.place(s, g)[0], 400)
        self.assertEqual((s.orders.all(), gw.charges, s.inventory.available("TEA-1")), ([], {}, 10))

    def test_limits_inclusive(self):
        s, _, _ = make_shop()
        code, body = self.place(s, {"recipient": "B" * 40, "message": "m" * 300})
        self.assertEqual(code, 201)
        self.assertEqual(body["order"]["gift_note"], "m" * 300)
