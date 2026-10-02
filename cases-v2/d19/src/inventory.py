class Inventory:
    def __init__(self, stock: dict):
        self.stock = dict(stock)

    def available(self, sku: str) -> int:
        return self.stock.get(sku, 0)

    def take(self, sku: str, qty: int) -> None:
        self.stock[sku] = self.available(sku) - qty
