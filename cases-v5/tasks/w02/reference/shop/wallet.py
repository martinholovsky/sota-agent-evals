"""Saved payment cards per customer."""
import re

EXP_RE = re.compile(r"(0[1-9]|1[0-2])/[0-9]{2}")


class Wallet:
    def __init__(self, events):
        self.events = events
        self._cards = {}             # card_id -> {"id", "owner", "number", "exp"}
        self._seq = 0

    def save(self, username: str, number: str, exp: str) -> dict:
        """Store a card; `number` may contain spaces between digit groups. Raises ValueError."""
        if not isinstance(number, str) or not isinstance(exp, str):
            raise ValueError("number and exp must be strings")
        digits = number.replace(" ", "")
        if not (digits.isascii() and digits.isdigit() and 13 <= len(digits) <= 19):
            raise ValueError("card number must be 13-19 digits")
        if not EXP_RE.fullmatch(exp):
            raise ValueError("exp must be MM/YY")
        self._seq += 1
        card = {"id": "C%05d" % self._seq, "owner": username, "number": digits, "exp": exp}
        self._cards[card["id"]] = card
        self.events.emit("card_saved", username=username, card_id=card["id"])
        return dict(card)

    def for_user(self, username: str) -> list:
        return [dict(c) for c in self._cards.values() if c["owner"] == username]
