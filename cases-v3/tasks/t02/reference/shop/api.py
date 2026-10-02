"""Request handlers. Each takes a principal (from Users.login) and a plain-dict request,
and returns (status_code, body_dict). Handlers validate input and check permissions;
business rules live in the service modules.
"""
from .auth import AuthError, can, require
from .inventory import OutOfStock
from .orders import OrderError


class Api:
    def __init__(self, shop):
        self.shop = shop

    @staticmethod
    def _redact(principal, order: dict) -> dict:
        body = dict(order)
        if not can(principal, "payment:view"):
            body.pop("charge_id", None)
        return body

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
        return 200, {"order": self._redact(principal, order)}

    def list_orders(self, principal, req: dict):
        if can(principal, "order:view_any"):
            visible = self.shop.orders.all()
        elif can(principal, "order:view_own"):
            visible = self.shop.orders.for_customer(principal["username"])
        else:
            return 403, {"error": "forbidden: order:view_own"}
        for key in ("customer", "status"):
            if key in req:
                if not isinstance(req[key], str):
                    return 400, {"error": "%s must be a string" % key}
                visible = [o for o in visible if o[key] == req[key]]
        visible.sort(key=lambda o: o["id"])
        return 200, {"orders": [self._redact(principal, o) for o in visible]}

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
