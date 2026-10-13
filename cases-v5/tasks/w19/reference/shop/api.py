"""Request handlers. Each takes a principal (from Users.login) and a plain-dict request,
and returns (status_code, body_dict). Handlers validate input and check permissions;
business rules live in the service modules.
"""
from .auth import AuthError, require
from .inventory import OutOfStock
from .orders import OrderError
from .pricing import COUPONS

COUPON_CHECKS_PER_WINDOW = 30
COUPON_WINDOW = 60          # seconds


class Api:
    def __init__(self, shop):
        self.shop = shop
        self._coupon_checks = {}     # username -> recent check times

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
            require(principal, "coupon:check")
        except AuthError as e:
            return 403, {"error": str(e)}
        if not self._allow_coupon_check(principal["username"]):
            return 429, {"error": "too many coupon checks, try again shortly"}
        code = req.get("code")
        if not isinstance(code, str) or not code:
            return 400, {"error": "code (non-empty string) required"}
        if code not in COUPONS:
            return 200, {"code": code, "valid": False}
        kind, value = COUPONS[code]
        return 200, {"code": code, "valid": True, "kind": kind, "value": value}

    def _allow_coupon_check(self, username: str) -> bool:
        """At most COUPON_CHECKS_PER_WINDOW checks per caller in any COUPON_WINDOW seconds."""
        now = self.shop.events.clock()
        recent = [t for t in self._coupon_checks.get(username, []) if now - t < COUPON_WINDOW]
        if len(recent) >= COUPON_CHECKS_PER_WINDOW:
            self._coupon_checks[username] = recent
            return False
        recent.append(now)
        self._coupon_checks[username] = recent
        return True
