"""Request handlers. Each takes a principal (from Users.login) and a plain-dict request,
and returns (status_code, body_dict). Handlers validate input and check permissions;
business rules live in the service modules.
"""
from .auth import AuthError, require
from .catalog import VersionConflict
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

    @staticmethod
    def _change(c):
        if not isinstance(c, dict) or type(c.get("version")) is not int:
            raise ValueError("each change needs sku, price and an int version")
        return c.get("sku"), c.get("price"), c["version"]

    def update_price(self, principal, req: dict):
        try:
            require(principal, "catalog:edit")
        except AuthError as e:
            return 403, {"error": str(e)}
        try:
            sku, price, version = self._change(req)
            self.shop.catalog.set_price(sku, price, version)
        except KeyError:
            return 404, {"error": "unknown sku"}
        except ValueError as e:
            return 400, {"error": str(e)}
        except VersionConflict as e:
            return 409, {"error": str(e), "product": self.shop.catalog.get(sku)}
        return 200, {"product": self.shop.catalog.get(sku)}

    def update_prices(self, principal, req: dict):
        try:
            require(principal, "catalog:edit")
        except AuthError as e:
            return 403, {"error": str(e)}
        changes = req.get("changes")
        if not isinstance(changes, list) or not changes:
            return 400, {"error": "changes (non-empty list) required"}
        try:
            versions = self.shop.catalog.set_prices([self._change(c) for c in changes])
        except KeyError:
            return 404, {"error": "unknown sku"}
        except ValueError as e:
            return 400, {"error": str(e)}
        except VersionConflict as e:
            return 409, {"error": str(e)}
        return 200, {"versions": versions}
