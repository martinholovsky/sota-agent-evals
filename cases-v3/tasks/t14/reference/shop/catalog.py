"""Products. A SKU is uppercase letters/digits/hyphens, 3-20 chars."""
import re

SKU_RE = re.compile(r"[A-Z0-9-]{3,20}")


class VersionConflict(Exception):
    pass


def _check_price(price) -> None:
    if not isinstance(price, int) or isinstance(price, bool) or price <= 0:
        raise ValueError("price must be positive int cents")


class Catalog:
    def __init__(self, events):
        self.events = events
        self._products = {}          # sku -> {"sku", "name", "price", "active", "version"}

    def add(self, sku: str, name: str, price: int) -> dict:
        if not SKU_RE.fullmatch(sku):
            raise ValueError("bad sku: %r" % sku)
        if sku in self._products:
            raise ValueError("duplicate sku: %s" % sku)
        if not isinstance(price, int) or isinstance(price, bool) or price <= 0:
            raise ValueError("price must be positive int cents")
        p = {"sku": sku, "name": name, "price": price, "active": True, "version": 1}
        self._products[sku] = p
        self.events.emit("product_added", sku=sku, price=price)
        return dict(p)

    def get(self, sku: str) -> dict:
        if sku not in self._products:
            raise KeyError(sku)
        return dict(self._products[sku])

    def _validate(self, sku, price, expected_version) -> None:
        if sku not in self._products:
            raise KeyError(sku)
        _check_price(price)
        if expected_version is not None and type(expected_version) is not int:
            raise ValueError("expected_version must be an int or None")
        current = self._products[sku]["version"]
        if expected_version is not None and expected_version != current:
            raise VersionConflict("%s is at version %d, not %d" % (sku, current, expected_version))

    def _apply(self, sku, price) -> int:
        p = self._products[sku]
        old = p["price"]
        p["price"] = price
        p["version"] += 1
        self.events.emit("price_changed", sku=sku, old=old, new=price, version=p["version"])
        return p["version"]

    def set_price(self, sku: str, price: int, expected_version: int | None = None) -> int:
        self._validate(sku, price, expected_version)
        return self._apply(sku, price)

    def set_prices(self, changes: list) -> dict:
        """[(sku, price, expected_version)] -> {sku: new_version}. All or nothing."""
        seen = set()
        for sku, price, expected in changes:
            self._validate(sku, price, expected)
            if sku in seen:
                raise ValueError("duplicate sku in batch: %s" % sku)
            seen.add(sku)
        return {sku: self._apply(sku, price) for sku, price, _ in changes}

    def listing(self) -> list:
        """Active products, sorted by SKU."""
        return [dict(p) for _, p in sorted(self._products.items()) if p["active"]]
