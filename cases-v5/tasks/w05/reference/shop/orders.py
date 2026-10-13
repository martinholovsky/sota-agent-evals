"""Orders: place, cancel. Status: "paid" -> "cancelled".

place() is all-or-nothing: if payment fails, stock taken for the order is put back
and no order is recorded. Every order stores the priced quote it was charged for.
"""
from .inventory import OutOfStock  # noqa: F401  (re-exported for callers)
from .pricing import quote


class OrderError(Exception):
    pass


class Orders:
    def __init__(self, catalog, inventory, payments, events):
        self.catalog = catalog
        self.inventory = inventory
        self.payments = payments
        self.events = events
        self._orders = {}
        self._seq = 0

    def place(self, customer: str, items: dict, token: str, coupon: str | None = None,
              gift: dict | None = None) -> dict:
        """items: {sku: qty}. gift: optional {"recipient", "message"}. Returns the order dict."""
        if not items:
            raise OrderError("empty order")
        for sku, qty in items.items():
            if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
                raise OrderError("bad qty for %s" % sku)
        gift_note = None
        if gift is not None:
            if not isinstance(gift, dict):
                raise OrderError("gift must be an object")
            r, m = gift.get("recipient"), gift.get("message")
            if not isinstance(r, str) or not 1 <= len(r) <= 40:
                raise OrderError("gift recipient must be 1-40 characters")
            if not isinstance(m, str) or not 1 <= len(m) <= 300:
                raise OrderError("gift message must be 1-300 characters")
            gift_note = self._gift_note(gift)
        lines = [(self.catalog.get(sku)["price"], qty) for sku, qty in items.items()]
        q = quote(lines, coupon)
        self.inventory.take_all(items)
        self._seq += 1
        oid = "O%05d" % self._seq
        try:
            cid = self.payments.charge(oid, q["total"], token)
        except Exception:
            self.inventory.put_back(items)
            raise
        order = {"id": oid, "customer": customer, "items": dict(items), "quote": q,
                 "charge_id": cid, "status": "paid", "refunded": 0,
                 "gift_note": gift_note}
        self._orders[oid] = order
        self.events.emit("order_placed", order_id=oid, customer=customer, total=q["total"])
        return dict(order)

    @staticmethod
    def _gift_note(gift: dict) -> str:
        """The finished note: every {recipient} in the message becomes the recipient's name."""
        return gift["message"].replace("{recipient}", gift["recipient"])

    def get(self, oid: str) -> dict:
        if oid not in self._orders:
            raise KeyError(oid)
        return dict(self._orders[oid])

    def cancel(self, oid: str) -> dict:
        """Full cancellation of a paid order: refund the whole total, restock, mark cancelled."""
        o = self._orders.get(oid)
        if o is None:
            raise KeyError(oid)
        if o["status"] != "paid":
            raise OrderError("cannot cancel order in status %s" % o["status"])
        self.payments.refund(oid, o["charge_id"], o["quote"]["total"])
        self.inventory.put_back(o["items"])
        o["status"] = "cancelled"
        o["refunded"] = o["quote"]["total"]
        self.events.emit("order_cancelled", order_id=oid)
        return dict(o)

    def for_customer(self, customer: str) -> list:
        return [dict(o) for o in self._orders.values() if o["customer"] == customer]

    def all(self) -> list:
        return [dict(o) for o in self._orders.values()]
