"""Request handlers. Each takes a principal (from Users.login) and a plain-dict request,
and returns (status_code, body_dict). Handlers validate input and check permissions;
business rules live in the service modules.
"""
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

    def set_stock_threshold(self, principal, req: dict):
        try:
            require(principal, "inventory:edit")
        except AuthError as e:
            return 403, {"error": str(e)}
        sku, t = req.get("sku"), req.get("threshold")
        if not isinstance(sku, str) or not isinstance(t, int) or isinstance(t, bool) or t < 0:
            return 400, {"error": "sku (string) and threshold (int >= 0) required"}
        try:
            self.shop.catalog.get(sku)
        except KeyError:
            return 404, {"error": "unknown sku: %s" % sku}
        self.shop.inventory.set_threshold(sku, t)
        return 200, {"sku": sku, "threshold": t}

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
