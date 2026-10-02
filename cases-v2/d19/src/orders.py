from src.inventory import Inventory


class OutOfStock(Exception):
    pass


def place_order(inv: Inventory, lines: dict) -> None:
    """lines: {sku: qty}. qty must be a positive int, else ValueError.
    ALL-OR-NOTHING: if any sku lacks enough stock, raise OutOfStock naming that sku and
    change NO stock at all. Otherwise subtract every line."""
    for sku, qty in lines.items():
        if inv.available(sku) < qty:
            raise OutOfStock(sku)
        inv.take(sku, qty)
