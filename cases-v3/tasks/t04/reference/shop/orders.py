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
        self._reservations = {}      # reservation id -> customer

    @staticmethod
    def _check_items(items: dict) -> None:
        if not items:
            raise OrderError("empty order")
        for sku, qty in items.items():
            if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
                raise OrderError("bad qty for %s" % sku)

    def reserve(self, customer: str, items: dict, ttl: int) -> dict:
        """Hold {sku: qty} for ttl seconds for this customer. All-or-nothing."""
        self._check_items(items)
        if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl <= 0:
            raise ValueError("ttl must be a positive int")
        for sku in items:
            self.catalog.get(sku)                            # KeyError for unknown sku
        rid = self.inventory.new_reservation_id()
        expires_at = self.inventory.hold(rid, items, ttl)    # OutOfStock: nothing held
        self._reservations[rid] = customer
        self.events.emit("stock_reserved", reservation_id=rid, customer=customer,
                         lines=dict(items), expires_at=expires_at)
        return {"id": rid, "customer": customer, "items": dict(items), "expires_at": expires_at}

    def place(self, customer: str, items: dict, token: str, coupon: str | None = None,
              reservation: str | None = None) -> dict:
        """items: {sku: qty}. Returns the order dict."""
        self._check_items(items)
        if reservation is not None:
            if (self._reservations.get(reservation) != customer
                    or not self.inventory.is_active(reservation)):
                raise OrderError("no usable reservation %r" % (reservation,))
            if self.inventory.reservation_lines(reservation) != dict(items):
                raise OrderError("items do not match the reservation")
        lines = [(self.catalog.get(sku)["price"], qty) for sku, qty in items.items()]
        q = quote(lines, coupon)
        self.inventory.take_all(items, reservation=reservation)
        self._seq += 1
        oid = "O%05d" % self._seq
        try:
            cid = self.payments.charge(oid, q["total"], token)
        except Exception:
            self.inventory.put_back(items, reservation=reservation)
            raise
        order = {"id": oid, "customer": customer, "items": dict(items), "quote": q,
                 "charge_id": cid, "status": "paid", "refunded": 0}
        self._orders[oid] = order
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
