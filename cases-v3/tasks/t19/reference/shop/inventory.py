"""Stock levels. Stock never goes negative.

Low-stock alerts: a SKU may have a threshold. When an operation takes available stock
from at-or-above its threshold to below it, one "stock_low" event is emitted for that
SKU after the operation completes. Receiving or returning stock never alerts.
"""


class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self, events):
        self.events = events
        self._stock = {}
        self._thresholds = {}

    def receive(self, sku: str, qty: int) -> None:
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError("qty must be a positive int")
        self._stock[sku] = self._stock.get(sku, 0) + qty
        self.events.emit("stock_received", sku=sku, qty=qty)

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def set_threshold(self, sku: str, threshold: int) -> None:
        if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 0:
            raise ValueError("threshold must be an int >= 0")
        self._thresholds[sku] = threshold
        self.events.emit("stock_threshold_set", sku=sku, threshold=threshold)

    def threshold(self, sku: str):
        return self._thresholds.get(sku)

    def levels(self, skus) -> dict:
        """Snapshot of available stock, to pass to alert_low() after an operation."""
        return {sku: self.available(sku) for sku in skus}

    def alert_low(self, before: dict) -> None:
        """Emit stock_low for each SKU (in `before` order) that went from >= to < threshold."""
        for sku, was in before.items():
            t = self._thresholds.get(sku)
            now = self.available(sku)
            if t is not None and was >= t > now:
                self.events.emit("stock_low", sku=sku, available=now, threshold=t)

    def take_all(self, lines: dict, alert: bool = True) -> None:
        """Remove every {sku: qty} or nothing (all-or-nothing).
        alert=False: the caller owns the operation and calls alert_low() when it completes."""
        for sku, qty in lines.items():
            if self.available(sku) < qty:
                raise OutOfStock(sku)
        before = self.levels(lines)
        for sku, qty in lines.items():
            self._stock[sku] -= qty
        self.events.emit("stock_taken", lines=dict(lines))
        if alert:
            self.alert_low(before)

    def put_back(self, lines: dict) -> None:
        for sku, qty in lines.items():
            self._stock[sku] = self.available(sku) + qty
        self.events.emit("stock_returned", lines=dict(lines))
