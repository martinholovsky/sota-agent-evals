"""Products. A SKU is uppercase letters/digits/hyphens, 3-20 chars."""
import ipaddress
import re
import socket
from urllib.parse import urlsplit

SKU_RE = re.compile(r"[A-Z0-9-]{3,20}")


METADATA_NAMES = {"metadata.google.internal", "metadata", "instance-data"}


def _is_public(ip) -> bool:
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def _public_destination(host: str, port: int) -> bool:
    """Resolve `host` and require EVERY address to be public (sota-code-security rules/01 §5)."""
    if host.lower().rstrip(".") in METADATA_NAMES:
        return False
    try:
        return _is_public(ipaddress.ip_address(host))
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError):
        return False
    addrs = {info[4][0].split("%")[0] for info in infos}
    return bool(addrs) and all(_is_public(ipaddress.ip_address(a)) for a in addrs)


class Catalog:
    def __init__(self, events):
        self.events = events
        self._products = {}          # sku -> {"sku", "name", "price", "active"}
        self._images = {}            # sku -> bytes
        self.http_get = None         # set by the deployment: http_get(url) -> bytes

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

    def set_image_from_url(self, sku: str, url: str) -> int:
        if sku not in self._products:
            raise KeyError(sku)
        if not isinstance(url, str):
            raise ValueError("url must be a string")
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError("url must be an http(s) URL with a host")
        if not _public_destination(parts.hostname, parts.port or 443):
            raise ValueError("image URL destination not allowed")
        data = self.http_get(url)
        self._images[sku] = data
        self.events.emit("product_image_set", sku=sku, size=len(data))
        return len(data)

    def image(self, sku: str):
        if sku not in self._products:
            raise KeyError(sku)
        return self._images.get(sku)
