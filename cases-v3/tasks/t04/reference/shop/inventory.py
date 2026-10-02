"""Stock levels. Stock never goes negative.

on_hand(sku) is the physical count; available(sku) is on_hand minus the quantities held
by active (unconsumed, unexpired) reservations. Expiry is computed from the clock.
"""


class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self, events):
        self.events = events
        self._stock = {}
        self._res = {}               # rid -> {"lines", "expires_at", "consumed"}
        self._rseq = 0

    def _now(self) -> int:
        return self.events.clock()

    def _active(self, r) -> bool:
        return not r["consumed"] and self._now() < r["expires_at"]

    def _held(self, sku: str, exclude=None) -> int:
        return sum(r["lines"].get(sku, 0) for rid, r in self._res.items()
                   if rid != exclude and self._active(r))

    def receive(self, sku: str, qty: int) -> None:
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError("qty must be a positive int")
        self._stock[sku] = self._stock.get(sku, 0) + qty
        self.events.emit("stock_received", sku=sku, qty=qty)

    def on_hand(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def available(self, sku: str) -> int:
        return self.on_hand(sku) - self._held(sku)

    def is_active(self, rid) -> bool:
        r = self._res.get(rid)
        return r is not None and self._active(r)

    def reservation_lines(self, rid) -> dict:
        return dict(self._res[rid]["lines"])

    def new_reservation_id(self) -> str:
        self._rseq += 1
        return "R%05d" % self._rseq

    def hold(self, rid: str, lines: dict, ttl: int) -> int:
        """Hold every {sku: qty} for ttl seconds, or nothing (all-or-nothing).
        Emits no event; the caller emits "stock_reserved". Returns expires_at."""
        for sku, qty in lines.items():
            if self.available(sku) < qty:
                raise OutOfStock(sku)
        expires_at = self._now() + ttl
        self._res[rid] = {"lines": dict(lines), "expires_at": expires_at, "consumed": False}
        return expires_at

    def unhold(self, rid: str) -> None:
        self._res.pop(rid, None)

    def take_all(self, lines: dict, reservation=None) -> None:
        """Remove every {sku: qty} or nothing (all-or-nothing). With a reservation, the
        reserved quantities count for this take, and the reservation is consumed."""
        for sku, qty in lines.items():
            if self.on_hand(sku) - self._held(sku, exclude=reservation) < qty:
                raise OutOfStock(sku)
        for sku, qty in lines.items():
            self._stock[sku] -= qty
        if reservation is None:
            self.events.emit("stock_taken", lines=dict(lines))
        else:
            self._res[reservation]["consumed"] = True
            self.events.emit("stock_taken", lines=dict(lines), reservation=reservation)

    def put_back(self, lines: dict, reservation=None) -> None:
        for sku, qty in lines.items():
            self._stock[sku] = self.on_hand(sku) + qty
        if reservation is not None:
            self._res[reservation]["consumed"] = False
        self.events.emit("stock_returned", lines=dict(lines))
