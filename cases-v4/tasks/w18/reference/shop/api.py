"""Request handlers. Each takes a principal (from Users.login) and a plain-dict request,
and returns (status_code, body_dict). Handlers validate input and check permissions;
business rules live in the service modules.
"""
import collections

from .auth import AuthError, require
from .inventory import OutOfStock
from .orders import OrderError


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

    # Search is an expensive read: rate-limit it per caller (sota-api-design rules/07 §2,
    # sota-code-security rules/06). Sliding window over the shop clock, keyed by principal.
    SEARCH_LIMIT, SEARCH_WINDOW_S = 30, 60

    def _allow(self, bucket: str, key: str, limit: int, window: int) -> bool:
        hits = self.__dict__.setdefault("_rate", {}).setdefault((bucket, key), collections.deque())
        now = self.shop.events.clock()
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True

    def search(self, principal, req: dict):
        if not self._allow("search", principal["username"], self.SEARCH_LIMIT, self.SEARCH_WINDOW_S):
            return 429, {"error": "too many requests"}
        q = req.get("q")
        if not isinstance(q, str) or not q:
            return 400, {"error": "q (non-empty string) required"}
        needle = q.casefold()
        return 200, {"items": [p for p in self.shop.catalog.listing()
                               if needle in p["name"].casefold()]}
