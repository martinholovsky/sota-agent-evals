"""Request handlers. Each takes a principal (from Users.login) and a plain-dict request,
and returns (status_code, body_dict). Handlers validate input and check permissions;
business rules live in the service modules.
"""
import base64
import binascii

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

    def list_products(self, principal, req: dict):
        limit, cursor = req.get("limit"), req.get("cursor")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            return 400, {"error": "limit must be a positive int"}
        start = 0
        if cursor is not None:
            try:
                start = int(base64.urlsafe_b64decode(cursor.encode("ascii")).decode())
                if start < 0:
                    raise ValueError
            except (AttributeError, TypeError, ValueError, UnicodeError, binascii.Error):
                return 400, {"error": "bad cursor"}
        rows = sorted(self.shop.catalog.listing(), key=lambda p: p["price"])   # stable
        page = rows[start:start + limit]
        nxt = None
        if start + limit < len(rows):
            nxt = base64.urlsafe_b64encode(str(start + limit).encode()).decode()
        return 200, {"items": page, "next_cursor": nxt}
