import pathlib

"""Request handlers. Each takes a principal (from Users.login) and a plain-dict request,
and returns (status_code, body_dict). Handlers validate input and check permissions;
business rules live in the service modules.
"""
from .auth import AuthError, require
from .inventory import OutOfStock
from .orders import OrderError
from .reports import orders_csv


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

    def save_report(self, principal, req: dict):
        try:
            require(principal, "report:view")
        except AuthError as e:
            return 403, {"error": str(e)}
        name = req.get("name")
        if not isinstance(name, str) or not name:
            return 400, {"error": "name (non-empty string) required"}
        # join, then resolve, then containment-check (sota-code-security rules/01 §4)
        if "\0" in name or "/" in name or "\\" in name or name in (".", ".."):
            return 400, {"error": "name must be a plain file name"}
        base = pathlib.Path(self.shop.reports_dir).resolve()
        target = (base / (name + ".csv")).resolve()
        if target.parent != base:
            return 400, {"error": "name must be a plain file name"}
        with open(target, "w", newline="") as f:
            f.write(orders_csv(self.shop.orders))
        self.shop.events.emit("report_saved", name=name)
        return 201, {"path": str(target)}
