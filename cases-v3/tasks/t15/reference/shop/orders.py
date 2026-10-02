"""Orders: place, cancel. Status: "paid" -> "cancelled".

place() is all-or-nothing: if payment fails, stock taken for the order is put back
and no order is recorded. Every order stores the priced quote it was charged for.
"""
from .inventory import OutOfStock  # noqa: F401  (re-exported for callers)
from .pricing import quote


class OrderError(Exception):
    pass


class IdempotencyConflict(OrderError):
    pass


class Orders:
    def __init__(self, catalog, inventory, payments, events):
        self.catalog = catalog
        self.inventory = inventory
        self.payments = payments
        self.events = events
        self._orders = {}
        self._seq = 0
        self._keys = {}              # (customer, key) -> (order_id, items, coupon)

    def place(self, customer: str, items: dict, token: str, coupon: str | None = None,
              idempotency_key: str | None = None) -> dict:
        """items: {sku: qty}. Returns the order dict.

        With an idempotency key, a repeat of the same request returns the original order;
        the same key with a different request is an IdempotencyConflict. Failed calls do not
        consume the key."""
        if idempotency_key is not None:
            prior = self._keys.get((customer, idempotency_key))
            if prior is not None:
                oid, p_items, p_coupon = prior
                if p_items == items and p_coupon == coupon:
                    return self.get(oid)
                raise IdempotencyConflict("idempotency key reused with a different request")
        if not items:
            raise OrderError("empty order")
        for sku, qty in items.items():
            if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
                raise OrderError("bad qty for %s" % sku)
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
                 "charge_id": cid, "status": "paid", "refunded": 0}
        self._orders[oid] = order
        if idempotency_key is not None:
            self._keys[(customer, idempotency_key)] = (oid, dict(items), coupon)
        self.events.emit("order_placed", order_id=oid, customer=customer, total=q["total"])
        return dict(order)

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
