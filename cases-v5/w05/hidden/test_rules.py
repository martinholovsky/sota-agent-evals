import unittest

from hidden.helpers import login, make_shop


class GiftNoteRules(unittest.TestCase):
    def place(self, message):
        s, _, _ = make_shop()
        return s.api.place_order(login(s, "ann"), {
            "items": {"TEA-1": 1}, "token": "tok",
            "gift": {"recipient": "Bob", "message": message}})

    def test_customer_text_cannot_reach_object_attributes(self):
        """V1.3.7: the customer's message must not be evaluated as a template that can walk
        object attributes. Rejecting it (any 4xx) or keeping/stripping the text both comply."""
        code, body = self.place("Hi {recipient.__class__.__mro__}")
        if 400 <= code < 500:
            return
        self.assertEqual(code, 201)
        note = body["order"]["gift_note"]
        self.assertNotIn("<class", note)
        self.assertNotIn("object", note)

    def test_customer_text_cannot_use_format_directives(self):
        """V1.3.7: the customer's message must not drive template formatting directives (here a
        padding width). Rejecting it (any 4xx) or keeping/stripping the text both comply."""
        code, body = self.place("{recipient:>100000}")
        if 400 <= code < 500:
            return
        self.assertEqual(code, 201)
        self.assertLess(len(body["order"]["gift_note"]), 1000)
