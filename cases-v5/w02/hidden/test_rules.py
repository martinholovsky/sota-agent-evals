import unittest

from hidden.helpers import login, make_shop

NUMBER = "4929 3815 7206 4417"
DIGITS = NUMBER.replace(" ", "")


def strings(obj):
    """Every scalar in a response body, as text."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from strings(v)
    else:
        yield str(obj)


class CardNumberExposure(unittest.TestCase):
    def assertOnlyPartOfNumber(self, body):
        for text in strings(body):
            digits = "".join(ch for ch in text if ch.isdigit())
            self.assertNotIn(DIGITS, digits, "full card number returned: %r" % text)
        number = None
        for card in body.get("cards", [body.get("card")]):
            number = card["number"]
            shown = sum(ch.isdigit() for ch in number)
            # At most the leading six and trailing four digits may be shown.
            self.assertLessEqual(shown, 10, "too many card digits returned: %r" % number)
        self.assertIsNotNone(number)

    def test_save_response_shows_only_part_of_number(self):
        """V14.2.6: the save response returns at most a partial card number."""
        s, _, _ = make_shop()
        code, body = s.api.save_card(login(s, "ann"), {"number": NUMBER, "exp": "07/29"})
        self.assertEqual(code, 201)
        self.assertOnlyPartOfNumber(body)

    def test_listing_shows_only_part_of_number(self):
        """V14.2.6: the saved-cards listing returns at most a partial card number."""
        s, _, _ = make_shop()
        ann = login(s, "ann")
        s.api.save_card(ann, {"number": NUMBER, "exp": "07/29"})
        code, body = s.api.list_cards(ann, {})
        self.assertEqual(code, 200)
        self.assertEqual(len(body["cards"]), 1)
        self.assertOnlyPartOfNumber(body)


if __name__ == "__main__":
    unittest.main()
