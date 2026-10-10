"""Products. A SKU is uppercase letters/digits/hyphens, 3-20 chars."""
import re

SKU_RE = re.compile(r"[A-Z0-9-]{3,20}")


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

    def listing(self) -> list:
        """Active products, sorted by SKU."""
        return [dict(p) for _, p in sorted(self._products.items()) if p["active"]]

    def search(self, query: str) -> list:
        """Active products whose name matches `query` (`*` = any run), case-insensitive.
        Only `*` is special: every literal part goes through re.escape, so user text never
        becomes regex syntax (sota-code-security rules/01, section 10)."""
        pattern = ".*".join(re.escape(part) for part in query.split("*"))
        rx = re.compile(pattern, re.IGNORECASE)
        return [p for p in self.listing() if rx.search(p["name"])]
