"""Request handlers. Each takes a principal (from Users.login) and a plain-dict request,
and returns (status_code, body_dict). Handlers validate input and check permissions;
business rules live in the service modules.
"""
import json

from .auth import AuthError, require
from .inventory import OutOfStock
from .orders import OrderError


class Api:
    def __init__(self, shop):
        self.shop = shop
        self._webhook_ids = set()    # webhook event ids processed with a 200

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

    def payment_webhook(self, req: dict):
        """Gateway -> shop notification. Authenticated by signature, not by a principal."""
        headers, body = req.get("headers"), req.get("body")
        if not isinstance(headers, dict) or not isinstance(body, str):
            return 400, {"error": "headers (object) and body (string) required"}
        ts, sig = headers.get("Shop-Timestamp"), headers.get("Shop-Signature")
        if not isinstance(ts, str) or not isinstance(sig, str) or not ts.isascii() \
                or not ts.isdigit():
            return 400, {"error": "Shop-Timestamp and Shop-Signature headers required"}
        if not self.shop.payments.verify_webhook(ts, body, sig, self.shop.events.clock()):
            return 401, {"error": "invalid signature"}
        try:
            ev = json.loads(body)
        except ValueError:
            return 400, {"error": "body is not JSON"}
        if not isinstance(ev, dict) or not isinstance(ev.get("id"), str) \
                or not isinstance(ev.get("type"), str):
            return 400, {"error": "id and type required"}
        if ev["id"] in self._webhook_ids:
            return 409, {"error": "event already processed"}
        if ev["type"] != "charge.disputed":
            self._webhook_ids.add(ev["id"])
            return 200, {"ignored": True}
        data = ev.get("data")
        cid = data.get("charge_id") if isinstance(data, dict) else None
        if not isinstance(cid, str):
            return 400, {"error": "data.charge_id required"}
        try:
            order = self.shop.orders.by_charge(cid)
            order = self.shop.orders.dispute(order["id"], ev["id"])
        except KeyError:
            return 404, {"error": "no such charge"}
        except OrderError as e:
            return 409, {"error": str(e)}
        self._webhook_ids.add(ev["id"])
        return 200, {"order": order}
