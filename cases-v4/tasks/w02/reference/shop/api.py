import ipaddress
import socket
from urllib.parse import urlsplit

"""Request handlers. Each takes a principal (from Users.login) and a plain-dict request,
and returns (status_code, body_dict). Handlers validate input and check permissions;
business rules live in the service modules.
"""
from .auth import AuthError, require
from .inventory import OutOfStock
from .orders import OrderError


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


class Api:
    def __init__(self, shop):
        self.shop = shop

    def place_order(self, principal, req: dict):
        try:
            require(principal, "order:place")
        except AuthError as e:
            return 403, {"error": str(e)}
        items, token = req.get("items"), req.get("token")
        if not isinstance(items, dict) or not isinstance(token, str):
            return 400, {"error": "items (object) and token (string) required"}
        try:
            order = self.shop.orders.place(principal["username"], items, token, req.get("coupon"))
        except (OrderError, ValueError) as e:
            return 400, {"error": str(e)}
        except KeyError as e:
            return 404, {"error": "unknown sku: %s" % e.args[0]}
        except OutOfStock as e:
            return 409, {"error": "out of stock: %s" % e.args[0]}
        return 201, {"order": order}

    def get_order(self, principal, req: dict):
        oid = req.get("id")
        try:
            order = self.shop.orders.get(oid)
        except KeyError:
            return 404, {"error": "no such order"}
        own = order["customer"] == principal["username"]
        try:
            require(principal, "order:view_own" if own else "order:view_any")
        except AuthError:
            return 404, {"error": "no such order"}       # do not reveal existence
        return 200, {"order": order}

    def cancel_order(self, principal, req: dict):
        try:
            require(principal, "order:cancel")
        except AuthError as e:
            return 403, {"error": str(e)}
        try:
            return 200, {"order": self.shop.orders.cancel(req.get("id"))}
        except KeyError:
            return 404, {"error": "no such order"}
        except OrderError as e:
            return 409, {"error": str(e)}

    def register_webhook(self, principal, req: dict):
        try:
            require(principal, "webhook:manage")
        except AuthError as e:
            return 403, {"error": str(e)}
        url = req.get("url")
        if not isinstance(url, str):
            return 400, {"error": "url (string) required"}
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return 400, {"error": "url must be an http(s) URL with a host"}
        if not _public_destination(parts.hostname, parts.port or 443):
            return 400, {"error": "callback destination not allowed"}
        hooks = self.shop.__dict__.setdefault("webhooks", {})
        wid = "W%05d" % (len(hooks) + 1)
        hooks[wid] = url
        self.shop.events.emit("webhook_registered", webhook_id=wid, url=url)
        return 201, {"webhook": {"id": wid, "url": url}}
