"""Request handlers. Each takes a principal (from Users.login) and a plain-dict request,
and returns (status_code, body_dict). Handlers validate input and check permissions;
business rules live in the service modules.
"""
from .auth import AuthError, require
from .inventory import OutOfStock
from .orders import OrderError
from .pricing import COUPONS


class Api:
    # Coupon guessing protection: at most MAX_COUPON_MISSES unknown codes per user per window.
    MAX_COUPON_MISSES = 10
    COUPON_WINDOW = 60           # seconds, on the shop clock

    def __init__(self, shop):
        self.shop = shop
        self._coupon_misses = {}     # username -> [miss times]

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

    def check_coupon(self, principal, req: dict):
        try:
            require(principal, "order:place")
        except AuthError as e:
            return 403, {"error": str(e)}
        code = req.get("coupon")
        if not isinstance(code, str):
            return 400, {"error": "coupon (string) required"}
        now = self.shop.events.clock()
        user = principal["username"]
        recent = [t for t in self._coupon_misses.get(user, []) if now - t < self.COUPON_WINDOW]
        self._coupon_misses[user] = recent
        if len(recent) >= self.MAX_COUPON_MISSES:
            return 429, {"error": "too many coupon attempts, try again later"}
        if code not in COUPONS:
            recent.append(now)
            return 200, {"valid": False}
        kind, value = COUPONS[code]
        return 200, {"valid": True, "coupon": code, "kind": kind, "value": value}
