"""Request handlers. Each takes a principal (from Users.login) and a plain-dict request,
and returns (status_code, body_dict). Handlers validate input and check permissions;
business rules live in the service modules.
"""
from .auth import AuthError, require
from .inventory import OutOfStock
from .orders import OrderError

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100          # largest page one search may return


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

    def search_orders(self, principal, req: dict):
        try:
            require(principal, "order:view_any")
        except AuthError as e:
            return 403, {"error": str(e)}
        page, size = req.get("page", 1), req.get("page_size", DEFAULT_PAGE_SIZE)
        for name, val in (("page", page), ("page_size", size)):
            if not isinstance(val, int) or isinstance(val, bool) or val <= 0:
                return 400, {"error": "%s must be a positive integer" % name}
        if size > MAX_PAGE_SIZE:
            return 400, {"error": "page_size must be at most %d" % MAX_PAGE_SIZE}
        customer, status = req.get("customer"), req.get("status")
        for name, val in (("customer", customer), ("status", status)):
            if val is not None and not isinstance(val, str):
                return 400, {"error": "%s must be a string" % name}
        found = sorted((o for o in self.shop.orders.all()
                        if (customer is None or o["customer"] == customer)
                        and (status is None or o["status"] == status)),
                       key=lambda o: o["id"])
        start = (page - 1) * size
        return 200, {"orders": found[start:start + size], "page": page, "total": len(found)}
