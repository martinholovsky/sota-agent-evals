"""Gift cards. A card's code is a bearer credential: it never appears in events,
orders or reports; events and orders reference the card by its public id."""
import secrets


class GiftCardError(Exception):
    pass


class GiftCards:
    def __init__(self, events):
        self.events = events
        self._cards = {}             # code -> {"id", "balance"}
        self._seq = 0

    def issue(self, amount: int) -> dict:
        if type(amount) is not int or amount <= 0:
            raise ValueError("amount must be positive int cents")
        self._seq += 1
        card_id = "G%05d" % self._seq
        code = secrets.token_urlsafe(16)
        self._cards[code] = {"id": card_id, "balance": amount}
        self.events.emit("giftcard_issued", card_id=card_id, amount=amount)
        return {"id": card_id, "code": code, "balance": amount}

    def _card(self, code) -> dict:
        if not isinstance(code, str) or code not in self._cards:
            raise GiftCardError("invalid gift card")
        return self._cards[code]

    def balance(self, code: str) -> int:
        return self._card(code)["balance"]

    def usable(self, code: str) -> dict:
        """The card's id and balance; GiftCardError if unknown or empty."""
        c = self._card(code)
        if c["balance"] <= 0:
            raise GiftCardError("gift card is empty")
        return dict(c)

    def debit(self, code: str, order_id: str, amount: int) -> None:
        c = self._card(code)
        if amount > c["balance"]:
            raise GiftCardError("insufficient balance")
        c["balance"] -= amount
        self.events.emit("giftcard_charged", card_id=c["id"], order_id=order_id, amount=amount)

    def credit(self, card_id: str, order_id: str, amount: int) -> None:
        c = next(c for c in self._cards.values() if c["id"] == card_id)
        c["balance"] += amount
        self.events.emit("giftcard_refunded", card_id=card_id, order_id=order_id, amount=amount)
