"""Stock levels. Stock never goes negative."""


class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self, events):
        self.events = events
        self._stock = {}

    def receive(self, sku: str, qty: int) -> None:
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError("qty must be a positive int")
        self._stock[sku] = self._stock.get(sku, 0) + qty
        self.events.emit("stock_received", sku=sku, qty=qty)

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def take_all(self, lines: dict) -> None:
        """Remove every {sku: qty} or nothing (all-or-nothing)."""
        for sku, qty in lines.items():
            if self.available(sku) < qty:
                raise OutOfStock(sku)
        for sku, qty in lines.items():
            self._stock[sku] -= qty
        self.events.emit("stock_taken", lines=dict(lines))

    def put_back(self, lines: dict) -> None:
        for sku, qty in lines.items():
            self._stock[sku] = self.available(sku) + qty
        self.events.emit("stock_returned", lines=dict(lines))
