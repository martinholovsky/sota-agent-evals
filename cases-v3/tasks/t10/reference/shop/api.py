"""Request handlers. Each takes a principal (from Users.login) and a plain-dict request,
and returns (status_code, body_dict). Handlers validate input and check permissions;
business rules live in the service modules.
"""
import base64
import hashlib
import hmac
import json
import os

from .auth import AuthError, require
from .inventory import OutOfStock
from .orders import OrderError


class Api:
    def __init__(self, shop):
        self.shop = shop
        self._cursor_key = os.urandom(32)     # signs pagination cursors

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

    def _sign(self, payload: str) -> str:
        return hmac.new(self._cursor_key, payload.encode(), hashlib.sha256).hexdigest()

    def _make_cursor(self, username: str, seq: int) -> str:
        payload = base64.urlsafe_b64encode(json.dumps({"u": username, "s": seq}).encode()).decode()
        return payload + "." + self._sign(payload)

    def _read_cursor(self, username: str, cursor):
        """The sequence number a cursor points before, or None if it is not valid for `username`."""
        if not isinstance(cursor, str) or cursor.count(".") != 1:
            return None
        payload, mac = cursor.split(".")
        if not hmac.compare_digest(self._sign(payload).encode(), mac.encode("utf-8", "replace")):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload.encode()))
        if data.get("u") != username:
            return None
        return data["s"]

    def list_my_orders(self, principal, req: dict):
        try:
            require(principal, "order:view_own")
        except AuthError as e:
            return 403, {"error": str(e)}
        limit = req.get("limit", 10)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
            return 400, {"error": "limit must be an int from 1 to 50"}
        before = None
        if "cursor" in req:
            before = self._read_cursor(principal["username"], req["cursor"])
            if before is None:
                return 400, {"error": "invalid cursor"}
        orders, last, more = self.shop.orders.page_for_customer(principal["username"], before, limit)
        nxt = self._make_cursor(principal["username"], last) if more else None
        return 200, {"orders": orders, "next_cursor": nxt}
