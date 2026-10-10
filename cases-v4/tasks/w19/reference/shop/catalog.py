"""Products. A SKU is uppercase letters/digits/hyphens, 3-20 chars."""
import re
import uuid

SKU_RE = re.compile(r"[A-Z0-9-]{3,20}")


class Catalog:
    def __init__(self, events):
        self.events = events
        self._products = {}          # sku -> {"sku", "name", "price", "active"}
        self.image_store = None      # object with put(name, data); set by the deployment

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

    # Upload handling (sota-code-security rules/21 §1, rules/09): the type comes from the
    # bytes, never the client's filename; size is capped; the stored name is generated here.
    MAX_IMAGE_BYTES = 10 * 1024 * 1024
    _IMAGE_MAGIC = ((b"\x89PNG\r\n\x1a\n", "png"), (b"\xff\xd8\xff", "jpg"))

    def upload_image(self, sku: str, filename: str, data: bytes) -> dict:
        if sku not in self._products:
            raise KeyError(sku)
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError("image data must be bytes")
        if len(data) > self.MAX_IMAGE_BYTES:
            raise ValueError("image too large")
        kind = next((k for magic, k in self._IMAGE_MAGIC if data.startswith(magic)), None)
        if kind is None:
            raise ValueError("only JPEG and PNG images are accepted")
        name = "%s.%s" % (uuid.uuid4().hex, kind)   # never the client's filename
        self.image_store.put(name, bytes(data))
        self._products[sku]["image"] = name
        self.events.emit("product_image_set", sku=sku, image=name)
        return dict(self._products[sku])
