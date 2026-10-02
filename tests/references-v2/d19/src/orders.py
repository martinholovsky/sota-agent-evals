from src.inventory import Inventory


class OutOfStock(Exception):
    pass


def place_order(inv: Inventory, lines: dict) -> None:
    for qty in lines.values():
        if type(qty) is not int or qty <= 0:
            raise ValueError("qty must be a positive int")
    for sku, qty in lines.items():
        if inv.available(sku) < qty:
            raise OutOfStock(sku)
    for sku, qty in lines.items():
        inv.take(sku, qty)
