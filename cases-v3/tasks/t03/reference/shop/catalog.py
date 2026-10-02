"""Products. A SKU is uppercase letters/digits/hyphens, 3-20 chars."""
import re

SKU_RE = re.compile(r"[A-Z0-9-]{3,20}")


class CatalogError(Exception):
    pass


class Catalog:
    def __init__(self, events):
        self.events = events
        self._products = {}          # sku -> {"sku", "name", "price", "active"}

    def add(self, sku: str, name: str, price: int) -> dict:
        if not SKU_RE.fullmatch(sku):
            raise ValueError("bad sku: %r" % sku)
        if sku in self._products:
            raise ValueError("duplicate sku: %s" % sku)
        if not isinstance(price, int) or isinstance(price, bool) or price <= 0:
            raise ValueError("price must be positive int cents")
        p = {"sku": sku, "name": name, "price": price, "active": True}
        self._products[sku] = p
        self.events.emit("product_added", sku=sku, price=price)
        return dict(p)

    def get(self, sku: str) -> dict:
        if sku not in self._products:
            raise KeyError(sku)
        return dict(self._products[sku])

    def set_price(self, sku: str, price: int) -> None:
        if sku not in self._products:
            raise KeyError(sku)
        if not isinstance(price, int) or isinstance(price, bool) or price <= 0:
            raise ValueError("price must be positive int cents")
        old = self._products[sku]["price"]
        self._products[sku]["price"] = price
        self.events.emit("price_changed", sku=sku, old=old, new=price)

    def _set_active(self, sku: str, active: bool) -> dict:
        if sku not in self._products:
            raise KeyError(sku)
        p = self._products[sku]
        if p["active"] == active:
            raise CatalogError("product %s is already %s" % (sku, "active" if active else "inactive"))
        p["active"] = active
        self.events.emit("product_reactivated" if active else "product_deactivated", sku=sku)
        return dict(p)

    def deactivate(self, sku: str) -> dict:
        return self._set_active(sku, False)

    def reactivate(self, sku: str) -> dict:
        return self._set_active(sku, True)

    def listing(self, include_inactive: bool = False) -> list:
        """Active products (or all, with include_inactive), sorted by SKU."""
        return [dict(p) for _, p in sorted(self._products.items())
                if include_inactive or p["active"]]
